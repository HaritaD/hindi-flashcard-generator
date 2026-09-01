# hindi-anki-flashcard-generator

Inspired by *Fluent Forever* by Gabriel Wyner. This tool generates Anki flashcards for Hindi
vocabulary that pair Devanagari script directly with native audio, real photographs, and personal
context — skipping English translations wherever possible so the brain learns to map sound to
meaning the way it would learn a first language, rather than through translation.

## Goals

1. **Map sound → meaning for the most frequently used words in Hindi** (Audio → Image), built from
   four ingredients on every card:
   - **Structure** — the Devanagari script
   - **Sound** — native audio pronunciation (Forvo)
   - **Concept** — real photographs standing in for the word's meaning, with no English caption
   - **Personal Connection** — a sandbox text box for the learner's own example sentence
2. **Develop proper pronunciation habits for learners unfamiliar with IPA** (Devanagari spelling →
   correct phonetic pronunciation), without ever requiring the learner to learn IPA. The priority
   is pronouncing the word correctly, not decoding the Devanagari script letter-by-letter.

## Card Design

Mobile-first. Devanagari is emphasized as the primary focal point; the phonetic pronunciation is
de-emphasized so the learner reads the script first and only glances at the pronunciation second,
to self-check rather than to read.

### Front

1. Devanagari spelling — emphasized
2. English phonetic pronunciation/spelling — de-emphasized (AI-generated)
3. Audio pronunciation (Forvo)

### Back

1. A gallery of images depicting the word's meaning, chosen to be as relevant to the learner as
   possible (search query AI-generated, up to 7 images)
2. Gender, if applicable
3. An example sentence, generated to be as relevant to the learner as possible (AI-generated)
4. A sandbox text input for the learner to write their own example sentence (user-generated)
5. An "English word" reveal button — the learner has to actively press it to see the translation

### Color Palette

`#EDEEF3` `#F5DDE0` `#EABEC3` `#DD868C` `#D0637C`

Card templates and CSS live in `style_cards.py` and are pushed to Anki via AnkiConnect rather than
hand-edited in the Anki GUI, so the design is versioned and reproducible.

## AI Generation

Each AI-generated field is driven by a prompt template in `prompts/`, filled in with the target
word and sent to Claude. All three assume the learner is a first-generation Indian-American, born
and raised in the US, 16 or older — conversational in Hindi but not fluent in reading it.

### Phonetic pronunciation — `prompts/pheonetic_pronounciation_prompt.md`

- Consistent, minimal format: hyphenated syllables, stressed syllable in CAPS, no IPA, no
  diacritics, no linguistic terminology.
- Reuses a common English word/spelling when one genuinely sounds the same (फूल → fool).
- Only adds a short parenthetical clarification when the word is commonly mispronounced by English
  speakers (aspirated "th"/"dh", the ड़/ढ़ flap, or nasalization) — never for anything else; vowel
  length, stress, and schwa deletion are handled by the spelling itself, with no note needed.

### Image search query — `prompts/google_image_search_prompt.md`

- Never includes the English translation — the query is entirely in Devanagari, so the learner has
  to infer the word's meaning purely from the photos, not a caption.
- Pairs the target word with 4-7 concrete, photographable anchor words spread across at least 3
  different categories (food, family, nature, school/objects, home, vehicles, activities, animals,
  clothing, expressions), explicitly guarding against defaulting to food for every word.
- For abstract words/qualities (अच्छा, नया, सुंदर), leans on category-spread anchors so the
  learner triangulates the meaning from the pattern repeating across several different photos,
  rather than reading any single image.

### Example sentence — `prompts/example_sentence_prompt.md`

- One short, natural sentence in the kind of everyday register heard at home, at a family
  gathering, or texting a cousin.
- Every other word in the sentence besides the target word is assumed already familiar (basic
  heritage-Hindi vocabulary), so the surrounding context gives the learner a second chance to infer
  the target word's meaning.
- The target word is wrapped in `<b>` tags so it stands out on the card.

## Setup

1. Install [Anki](https://apps.ankiweb.net/) and the
   [AnkiConnect](https://ankiweb.net/shared/info/2055492159) add-on, and leave Anki running while
   generating cards.
2. `python3 -m venv .venv && .venv/bin/pip install anthropic`
3. Create a `.env` file in the repo root:

   ```
   SERPAPI_KEY=...
   FORVO_API_KEY=...
   ANTHROPIC_API_KEY=...
   ```

## Usage

Push the card template + styling to Anki (run once, or again whenever `style_cards.py` changes):

```
.venv/bin/python3 style_cards.py
```

Add a single card from a Devanagari word:

```
.venv/bin/python3 add_card.py --hindi "किताब" --english "book" --gender "F" --deck "Fluent Forever Hindi Deck"
```

- `--english` and `--gender` are optional context for the AI generation steps; omit
  `--pronunciation` to have Claude generate it.
- Cards are skipped automatically if the Devanagari word already exists in the target deck.
- `words.txt` is the running, frequency-ordered word list (`Devanagari — English gloss`) this
  project draws from; work through it a batch at a time.
- Some decks use a note-type clone with an added personal-example scratchpad field instead of the
  base `Hindi gDocs` type — see `DECK_MODEL_OVERRIDES` in `add_card.py` before adding a new deck.

## Files

| File | Purpose |
|---|---|
| `add_card.py` | Generates and inserts one flashcard: image search + selection, Forvo audio, pronunciation, example sentence |
| `style_cards.py` | Pushes card template HTML + CSS to Anki (versioned card design) |
| `migrate_to_gdocs.py` | One-off migration of legacy notes into the `Hindi gDocs` note type |
| `prompts/` | Prompt templates for pronunciation, image search queries, and example sentences |
| `words.txt` | Source word list (Devanagari — English), frequency-ordered |
