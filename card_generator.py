#!/usr/bin/env python3
"""Core logic for generating a Hindi vocab Anki card from a single Devanagari
word: word validation/spell-check + English gloss via Claude, an optional
pool of candidate images via SerpApi (Google Images) with Claude picking the
most relevant ones, audio pronunciation via Forvo (falling back to gTTS),
a phonetic pronunciation
guide via Claude, and an example sentence via Claude. Inserts a note into
Anki via AnkiConnect.

Used by both main.py (CLI) and webui/app.py (local web UI).
"""
import base64
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

import anthropic
from gtts import gTTS

ANKI_URL = "http://127.0.0.1:8765"
DEFAULT_DECK = "Claude Cards"

STYLE_IMAGES = "images"
STYLE_SIMPLE = "simple"
STYLES = (STYLE_IMAGES, STYLE_SIMPLE)

MODEL_IMAGES = "Hindi gDocs"
MODEL_SIMPLE = "Simple Hindi Flashcard"
# Deck-specific note type overrides for the "images" style (e.g. decks with
# extra template features not shared by the default "Hindi gDocs" note type).
DECK_MODEL_OVERRIDES = {
    "New Claude Deck": "Hindi gDocs (New Claude Deck)",
    "Fluent Forever Hindi Deck": "Hindi gDocs (New Claude Deck)",
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TMP_DIR = "/tmp/hindi_anki_images"
IMAGE_CANDIDATE_POOL = 15
ENGLISH_CANDIDATE_POOL = 6
DEFAULT_NUM_IMAGES = 7
MAX_IMAGE_BYTES = 5 * 1024 * 1024

PROMPTS_DIR = os.path.join(SCRIPT_DIR, "prompts")
PRONUNCIATION_PROMPT_PATH = os.path.join(PROMPTS_DIR, "pheonetic_pronounciation_prompt.md")
IMAGE_SEARCH_PROMPT_PATH = os.path.join(PROMPTS_DIR, "google_image_search_prompt.md")
EXAMPLE_SENTENCE_PROMPT_PATH = os.path.join(PROMPTS_DIR, "example_sentence_prompt.md")
SPELLCHECK_PROMPT_PATH = os.path.join(PROMPTS_DIR, "spellcheck_prompt.md")

# A single Devanagari "word": the core block plus zero-width joiner/non-joiner
# (used in some conjuncts) and no spaces - callers should reject multi-word input.
DEVANAGARI_WORD_RE = re.compile(r"^[ऀ-ॿ‌‍]+$")


class CardGenerationError(Exception):
    pass


def load_env(path=None):
    path = path or os.path.join(SCRIPT_DIR, ".env")
    env = {}
    if not os.path.exists(path):
        return env
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def get_api_keys():
    env = load_env()
    keys = {
        "serpapi": os.environ.get("SERPAPI_KEY") or env.get("SERPAPI_KEY"),
        "forvo": os.environ.get("FORVO_API_KEY") or env.get("FORVO_API_KEY"),
        "anthropic": os.environ.get("ANTHROPIC_API_KEY") or env.get("ANTHROPIC_API_KEY"),
    }
    return keys


def anki_request(action, **params):
    payload = json.dumps({"action": action, "version": 6, "params": params}).encode()
    req = urllib.request.Request(ANKI_URL, data=payload)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.load(resp)
    except urllib.error.URLError as e:
        raise CardGenerationError(
            f"Couldn't reach Anki ({ANKI_URL}). Is Anki running with AnkiConnect installed? ({e})"
        ) from None
    if result.get("error"):
        raise CardGenerationError(f"AnkiConnect error on {action}: {result['error']}")
    return result["result"]


def list_decks():
    return sorted(anki_request("deckNames"))


def anthropic_client(api_key):
    # Explicit timeout/retries: the SDK defaults can leave a stalled request
    # (and its retries) hanging far longer than is useful here.
    return anthropic.Anthropic(api_key=api_key, timeout=60.0, max_retries=2)


def _load_prompt(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _claude_text(client, prompt, max_tokens):
    response = client.messages.create(
        model="claude-opus-5",
        max_tokens=max_tokens,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": prompt}],
    )
    return next((b.text for b in response.content if b.type == "text"), "").strip()


def check_word(hindi, anthropic_key):
    """Validate a single Devanagari word: script check, then spell-check +
    English gloss via Claude. Returns a dict:
      {
        "input": str, "valid_script": bool, "script_error": str|None,
        "recognized": bool, "corrected": str, "changed": bool,
        "english": str, "note": str,
      }
    """
    hindi = (hindi or "").strip()
    result = {
        "input": hindi,
        "valid_script": False,
        "script_error": None,
        "recognized": False,
        "corrected": hindi,
        "changed": False,
        "english": "",
        "note": "",
    }
    if not hindi:
        result["script_error"] = "Please enter a word."
        return result
    if " " in hindi or "\t" in hindi:
        result["script_error"] = "Please enter a single word, not a phrase."
        return result
    if not DEVANAGARI_WORD_RE.match(hindi):
        result["script_error"] = "That doesn't look like Devanagari script. Please type a Hindi word."
        return result
    result["valid_script"] = True

    template = _load_prompt(SPELLCHECK_PROMPT_PATH)
    prompt = template.replace("{{WORD}}", hindi)
    client = anthropic_client(anthropic_key)
    text = _claude_text(client, prompt, max_tokens=250)

    fields = {"valid": "", "corrected": "", "english": "", "note": ""}
    for line in text.splitlines():
        line = line.strip()
        for key in ("Valid", "Corrected", "English", "Note"):
            if line.lower().startswith(f"{key.lower()}:"):
                fields[key.lower()] = line.split(":", 1)[1].strip()

    result["recognized"] = fields["valid"].lower().startswith("y")
    corrected = fields["corrected"] or hindi
    result["corrected"] = corrected
    result["changed"] = corrected != hindi
    result["english"] = fields["english"]
    result["note"] = fields["note"]
    return result


def search_images(search_query, api_key, num=3):
    query = urllib.parse.urlencode(
        {
            "engine": "google_images",
            "q": search_query,
            "api_key": api_key,
            "safe": "active",
        }
    )
    url = f"https://serpapi.com/search.json?{query}"
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise CardGenerationError(f"SerpApi HTTP {e.code}: {body}") from None
    if "error" in data:
        raise CardGenerationError(f"SerpApi error: {data['error']}")
    results = data.get("images_results", [])
    return [item["original"] for item in results[:num] if "original" in item]


def generate_image_search_query(word, english, api_key):
    template = _load_prompt(IMAGE_SEARCH_PROMPT_PATH)
    prompt = template.replace("{{WORD}}", word).replace("{{ENGLISH}}", english or "(not provided)")
    client = anthropic_client(api_key)
    return _claude_text(client, prompt, max_tokens=150) or word


def download_file(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = resp.read()
    with open(dest, "wb") as f:
        f.write(data)


def guess_media_type(path):
    with open(path, "rb") as f:
        header = f.read(12)
    if header.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if header.startswith(b"\x89PNG"):
        return "image/png"
    if header[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image/webp"
    return None


def select_best_images(word, english, paths, api_key, keep=5):
    usable = [p for p in paths if guess_media_type(p) and os.path.getsize(p) <= MAX_IMAGE_BYTES]
    if len(usable) <= keep:
        return usable

    client = anthropic_client(api_key)
    blocks = []
    for i, path in enumerate(usable):
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        blocks.append({"type": "text", "text": f"Image {i}:"})
        blocks.append(
            {
                "type": "image",
                "source": {"type": "base64", "media_type": guess_media_type(path), "data": b64},
            }
        )
    meaning = f' (meaning: "{english}")' if english else ""
    blocks.append(
        {
            "type": "text",
            "text": (
                f'These are candidate images from a Google Images search meant to illustrate the '
                f'Hindi word "{word}"{meaning}, for a vocabulary flashcard. The goal is for a '
                f"learner to look at the image and intuitively grasp what the word means, purely "
                f"from the visual — so strongly prefer real, clear photographs of the actual "
                f"concept over anything else. Reject: text overlays, captions, watermarks, logos, "
                f"dictionary/definition graphics, icons or clipart, screenshots, memes, unrelated "
                f"subjects, and low-quality/blurry photos. Pick the {keep} images that most "
                f"clearly and unambiguously depict this word's meaning. Reply with ONLY a "
                f'comma-separated list of the chosen image numbers, most representative first '
                f'(e.g. "3,0,7,1,5"), nothing else.'
            ),
        }
    )
    try:
        response = client.messages.create(
            model="claude-opus-5",
            max_tokens=200,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": blocks}],
        )
    except anthropic.APIError as e:
        return usable[:keep], f"image selection failed, falling back to first {keep} candidates: {e}"
    text = next((b.text for b in response.content if b.type == "text"), "")

    indices = []
    for tok in text.replace(" ", "").split(","):
        if tok.isdigit() and int(tok) < len(usable):
            indices.append(int(tok))

    if not indices:
        return usable[:keep], None

    seen = set()
    ordered = []
    for idx in indices:
        if idx not in seen:
            seen.add(idx)
            ordered.append(usable[idx])
        if len(ordered) >= keep:
            break
    return ordered, None


def generate_tts_mp3(word, dest):
    gTTS(word, lang="hi").save(dest)


def find_forvo_mp3_url(word, api_key):
    query = urllib.parse.quote(word)
    url = (
        f"https://apifree.forvo.com/key/{api_key}/format/json/"
        f"action/word-pronunciations/word/{query}/language/hi"
    )
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.load(resp)
    items = data.get("items", [])
    if not items:
        return None
    best = max(items, key=lambda it: (it.get("num_positive_votes", 0), it.get("rate", 0)))
    return best["pathmp3"]


def get_pronunciation(word, api_key):
    template = _load_prompt(PRONUNCIATION_PROMPT_PATH)
    prompt = template.replace("{{WORD}}", word)
    client = anthropic_client(api_key)
    text = _claude_text(client, prompt, max_tokens=300)
    for line in text.splitlines():
        line = line.strip()
        if line.lower().startswith("pronunciation:"):
            return line.split(":", 1)[1].strip()
    return text


def generate_example_sentence(word, english, api_key):
    template = _load_prompt(EXAMPLE_SENTENCE_PROMPT_PATH)
    prompt = template.replace("{{WORD}}", word).replace("{{ENGLISH}}", english or "(not provided)")
    client = anthropic_client(api_key)
    return _claude_text(client, prompt, max_tokens=200)


def generate_card(
    hindi,
    english="",
    gender="",
    deck=DEFAULT_DECK,
    style=STYLE_IMAGES,
    pronunciation="",
    my_example="",
    num_images=DEFAULT_NUM_IMAGES,
    log=None,
):
    """Generate and insert one Anki note. `style` is "images" (full pipeline:
    Google-Images search + Claude picks the best photos) or "simple" (no
    image search/gallery). An AI-generated example sentence ("Example"
    field) is always produced; `my_example`, if given (e.g. a line the
    learner just heard on a show), is stored separately in a "My Example"
    field shown alongside it - it never replaces the AI one. `log(msg)` is
    called with progress messages. Returns a dict: {"status":
    "added"|"skipped"|"error", "note_id": int|None, "message": str,
    "fields": dict}.
    """
    if style not in STYLES:
        raise CardGenerationError(f"Unknown style {style!r}, expected one of {STYLES}")
    log = log or (lambda msg: None)

    keys = get_api_keys()
    if style == STYLE_IMAGES and not keys["serpapi"]:
        raise CardGenerationError("Missing SERPAPI_KEY (set as an env var or in .env)")
    if not keys["anthropic"]:
        raise CardGenerationError("Missing ANTHROPIC_API_KEY (set as an env var or in .env)")
    anthropic_key = keys["anthropic"]

    anki_request("createDeck", deck=deck)

    existing = anki_request("findNotes", query=f'deck:"{deck}" Hindi:"{hindi}"')
    if existing:
        return {
            "status": "skipped",
            "note_id": existing[0],
            "message": f"'{hindi}' already exists in {deck} (note {existing[0]})",
            "fields": {},
        }

    os.makedirs(TMP_DIR, exist_ok=True)

    img_tags = []
    if style == STYLE_IMAGES:
        search_query = generate_image_search_query(hindi, english, anthropic_key)
        log(f"Devanagari image search query: '{search_query}'")
        image_urls = search_images(search_query, keys["serpapi"], num=IMAGE_CANDIDATE_POOL)

        candidate_paths = []
        for i, url in enumerate(image_urls):
            fname = f"hindi_cand_{i}_{abs(hash(hindi))}.jpg"
            local_path = os.path.join(TMP_DIR, fname)
            try:
                download_file(url, local_path)
                candidate_paths.append(local_path)
            except Exception as e:
                log(f"skipped a candidate image: {e}")

        # Also pull in a smaller pool of English-language results, so a few
        # more literally-obvious photos are available alongside the
        # Devanagari ones - which stay the majority of candidates.
        if english:
            log(f"English image search query: '{english}'")
            english_image_urls = search_images(english, keys["serpapi"], num=ENGLISH_CANDIDATE_POOL)
            for i, url in enumerate(english_image_urls):
                fname = f"english_cand_{i}_{abs(hash(hindi))}.jpg"
                local_path = os.path.join(TMP_DIR, fname)
                try:
                    download_file(url, local_path)
                    candidate_paths.append(local_path)
                except Exception as e:
                    log(f"skipped an English candidate image: {e}")
        else:
            log("no English meaning provided, skipping English image search")

        chosen_paths = []
        if candidate_paths:
            chosen_paths, warning = select_best_images(
                hindi, english, candidate_paths, anthropic_key, keep=num_images
            )
            if warning:
                log(warning)

        for path in chosen_paths:
            fname = os.path.basename(path)
            try:
                with open(path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                anki_request("storeMediaFile", filename=fname, data=b64)
                img_tags.append(f'<img src="{fname}">')
            except Exception as e:
                log(f"skipped an image: {e}")

    # Audio: a native Forvo recording when one exists (and a key is
    # configured), otherwise synthesize it with gTTS.
    sound_tag = ""
    audio_source = None
    fname = f"hindi_sound_{abs(hash(hindi))}.mp3"
    local_path = os.path.join(TMP_DIR, fname)
    if keys["forvo"]:
        try:
            mp3_url = find_forvo_mp3_url(hindi, keys["forvo"])
            if mp3_url:
                download_file(mp3_url, local_path)
                audio_source = "forvo"
            else:
                log(f"no Forvo pronunciation found for '{hindi}', using gTTS")
        except Exception as e:
            log(f"Forvo lookup failed ({e}), using gTTS")
    if not audio_source:
        try:
            generate_tts_mp3(hindi, local_path)
            audio_source = "gtts"
        except Exception as e:
            log(f"gTTS failed: {e}")
    if audio_source:
        try:
            with open(local_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            anki_request("storeMediaFile", filename=fname, data=b64)
            sound_tag = f"[sound:{fname}]"
        except Exception as e:
            log(f"failed to store audio in Anki: {e}")
            audio_source = None
    if not sound_tag:
        log("no audio available, leaving Sound blank")

    pronunciation = pronunciation or get_pronunciation(hindi, anthropic_key)
    example = generate_example_sentence(hindi, english, anthropic_key)

    fields = {
        "Hindi": hindi,
        "English": english,
        "Gender": gender,
        "Pronunciation": pronunciation,
        "Sound": sound_tag,
        "Example": example,
        "My Example": my_example,
    }
    if style == STYLE_IMAGES:
        fields["image"] = "".join(img_tags)

    tags = ["auto-generated"]
    if audio_source:
        tags.append(f"audio-{audio_source}")
    else:
        tags.append("audio-missing")

    if style == STYLE_IMAGES:
        model_name = DECK_MODEL_OVERRIDES.get(deck, MODEL_IMAGES)
    else:
        model_name = MODEL_SIMPLE

    note = {
        "deckName": deck,
        "modelName": model_name,
        "fields": fields,
        "options": {"allowDuplicate": True},
        "tags": tags,
    }
    note_id = anki_request("addNote", note=note)
    message = (
        f"Added note {note_id} for '{hindi}' ({pronunciation}) "
        f"with {len(img_tags)} image(s), sound={audio_source or 'no'}, "
        f"example={'yes' if example else 'no'}"
    )
    return {"status": "added", "note_id": note_id, "message": message, "fields": fields}
