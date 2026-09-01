#!/usr/bin/env python3
"""Push the card template + CSS for the "Hindi gDocs" note type to Anki via
AnkiConnect. Card design/styling lives here in code (not hand-edited in the
Anki GUI) so it's versioned and reproducible.

Single card, two learning goals in one flow:
  Front - Devanagari script + phonetic pronunciation + audio together, so a
           native English speaker can map the written word straight to how
           it sounds.
  Back  - the image(s) that represent the word's meaning, plus gender when
           the word has one.

Usage:
  .venv/bin/python3 style_cards.py
"""
import json
import urllib.request

ANKI_URL = "http://127.0.0.1:8765"
MODEL = "Hindi gDocs"
CARD_NAME = "Card 1"
REMOVED_CARD_NAMES = ["Card 2"]


def anki_request(action, **params):
    payload = json.dumps({"action": action, "version": 6, "params": params}).encode()
    req = urllib.request.Request(ANKI_URL, data=payload)
    with urllib.request.urlopen(req) as resp:
        result = json.load(resp)
    if result.get("error"):
        raise RuntimeError(f"AnkiConnect error on {action}: {result['error']}")
    return result["result"]


EXAMPLE_HTML = (
    '{{#Example}}<div class="extra"><span class="extra-label">example</span>{{Example}}</div>{{/Example}}'
)

OTHER_EXTRA_FIELDS_HTML = (
    '{{#Grammar Notes}}<div class="extra"><span class="extra-label">notes</span>{{Grammar Notes}}</div>{{/Grammar Notes}}\n'
    '{{#Related Forms / Synonyms}}<div class="extra"><span class="extra-label">related</span>'
    "{{Related Forms / Synonyms}}</div>{{/Related Forms / Synonyms}}"
)

FRONT = """<div class="stage">
  <div class="hindi">{{Hindi}}</div>
  <div class="pronunciation-chip">{{Pronunciation}}</div>
  <div class="sound-wrap sound-wrap--big">{{Sound}}</div>
</div>"""

ENGLISH_REVEAL_HTML = (
    '{{#English}}<div class="reveal">'
    '<input type="checkbox" id="reveal-english" class="reveal-checkbox">'
    '<label for="reveal-english" class="reveal-button">Show English</label>'
    '<div class="reveal-content"><span class="tag tag-english">{{English}}</span></div>'
    "</div>{{/English}}"
)

BACK = f"""<div class="stage stage-reveal">
  <div class="images">{{{{image}}}}</div>
  {{{{#Gender}}}}<div class="tag-row"><span class="tag tag-gender">{{{{Gender}}}}</span></div>{{{{/Gender}}}}
  {EXAMPLE_HTML}
  {ENGLISH_REVEAL_HTML}
  {OTHER_EXTRA_FIELDS_HTML}
</div>"""

TEMPLATES = {CARD_NAME: {"Front": FRONT, "Back": BACK}}

CSS = """.card {
  font-family: -apple-system, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  font-size: 20px;
  text-align: center;
  color: #3B2E33;
  background: #EDEEF3;
  margin: 0;
  padding: 20px 14px 32px;
}

.stage {
  max-width: 440px;
  margin: 0 auto;
  background: #FFFFFF;
  border-radius: 24px;
  padding: 28px 20px 24px;
  box-shadow: 0 10px 30px rgba(208, 99, 124, 0.16);
  border: 1px solid #F5DDE0;
}

.hindi {
  font-family: "Noto Sans Devanagari", "Mangal", sans-serif;
  font-weight: 700;
  color: #3B2E33;
  line-height: 1.25;
  font-size: clamp(46px, 15vw, 72px);
  margin: 6px 0 10px;
}

.pronunciation-chip {
  display: inline-block;
  background: transparent;
  color: #A9808A;
  font-weight: 500;
  letter-spacing: 0.02em;
  font-size: clamp(14px, 4vw, 18px);
  padding: 0;
  border-radius: 0;
  margin: 0 0 18px;
  box-shadow: none;
}

.sound-wrap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #F5DDE0;
  border-radius: 999px;
  padding: 10px 22px;
  margin: 4px 0 14px;
}
.sound-wrap--big {
  padding: 16px 26px;
  transform: scale(1.1);
  margin: 8px 0 16px;
}

.tag-row {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 8px;
  margin: 6px 0 14px;
}
.tag {
  font-size: 14px;
  font-weight: 600;
  padding: 6px 14px;
  border-radius: 999px;
}
.tag-english {
  background: #EDEEF3;
  color: #3B2E33;
}
.tag-gender {
  background: #EABEC3;
  color: #5A2430;
}

.images {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
  margin-bottom: 16px;
}
.images img {
  width: 108px;
  height: 108px;
  object-fit: cover;
  border-radius: 16px;
  border: 2px solid #F5DDE0;
}
.images img:first-child {
  width: 100%;
  max-width: 320px;
  height: 200px;
}

.reveal {
  margin: 4px 0 14px;
}
.reveal-checkbox {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}
.reveal-button {
  display: inline-block;
  cursor: pointer;
  background: #FFFFFF;
  color: #D0637C;
  font-weight: 700;
  font-size: 14px;
  letter-spacing: 0.02em;
  padding: 8px 20px;
  border-radius: 999px;
  border: 2px solid #D0637C;
}
.reveal-content {
  display: none;
  margin-top: 10px;
}
.reveal-checkbox:checked ~ .reveal-button {
  display: none;
}
.reveal-checkbox:checked ~ .reveal-content {
  display: block;
}

.extra {
  text-align: left;
  font-size: 14px;
  color: #6B4750;
  background: #EDEEF3;
  border-radius: 12px;
  padding: 8px 12px;
  margin-top: 8px;
}
.extra-label {
  display: block;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #DD868C;
  margin-bottom: 2px;
}

.night_mode .card, .card.night_mode { background: #1F171A; color: #F3E4E7; }
.night_mode .stage { background: #2B2024; border-color: #4A2E36; box-shadow: 0 10px 30px rgba(0,0,0,0.4); }
.night_mode .hindi { color: #F3E4E7; }
.night_mode .pronunciation-chip { color: #B98E97; }
.night_mode .sound-wrap { background: #4A2E36; }
.night_mode .tag-english { background: #382A2E; color: #F3E4E7; }
.night_mode .reveal-button { background: #2B2024; color: #EABEC3; border-color: #EABEC3; }
.night_mode .tag-gender { background: #5A2430; color: #F5DDE0; }
.night_mode .extra { background: #241A1D; color: #D9B7BE; }
.night_mode .images img { border-color: #4A2E36; }
"""

# "Hindi gDocs (New Claude Deck)" is a clone used by decks like "Fluent
# Forever Hindi Deck" that adds a "write your own example" scratchpad to the
# back template. It shares the same class names as the base model's CSS, so
# we push it the same CSS plus its own scratchpad rules (template is left
# untouched - it has the extra scratchpad markup/script the base lacks).
CLONE_MODEL = "Hindi gDocs (New Claude Deck)"
CLONE_CSS_EXTRA = """
.scratchpad {
  text-align: left;
  font-size: 14px;
  color: #6B4750;
  background: #EDEEF3;
  border-radius: 12px;
  padding: 8px 12px;
  margin-top: 8px;
}
.scratchpad-input {
  width: 100%;
  box-sizing: border-box;
  margin-top: 4px;
  border: 1px solid #F5DDE0;
  border-radius: 10px;
  padding: 8px 10px;
  font-family: inherit;
  font-size: 14px;
  color: #3B2E33;
  background: #FFFFFF;
  resize: vertical;
  -webkit-user-select: text;
  user-select: text;
  -webkit-touch-callout: default;
  touch-action: manipulation;
  pointer-events: auto;
}
.scratchpad-input:focus {
  outline: none;
  border-color: #D0637C;
}
.night_mode .scratchpad { background: #241A1D; color: #D9B7BE; }
.night_mode .scratchpad-input { background: #2B2024; color: #F3E4E7; border-color: #4A2E36; }
"""


def main():
    anki_request(
        "updateModelTemplates",
        model={"name": MODEL, "templates": TEMPLATES},
    )
    anki_request(
        "updateModelStyling",
        model={"name": MODEL, "css": CSS},
    )

    existing = anki_request("modelTemplates", modelName=MODEL)
    for name in REMOVED_CARD_NAMES:
        if name in existing:
            anki_request("modelTemplateRemove", modelName=MODEL, templateName=name)
            print(f'Removed unused card template "{name}".')

    print(f'Updated card templates + styling for model "{MODEL}".')

    anki_request(
        "updateModelStyling",
        model={"name": CLONE_MODEL, "css": CSS + CLONE_CSS_EXTRA},
    )
    print(f'Updated styling for model "{CLONE_MODEL}" (template left untouched).')


if __name__ == "__main__":
    main()
