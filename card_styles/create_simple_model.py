#!/usr/bin/env python3
"""Create/update the "Simple Hindi Flashcard" Anki note type via AnkiConnect.
Same color palette/typography as "Hindi Vocabulary" (Devanagari emphasized,
phonetic pronunciation de-emphasized), but with no SerpApi image search step:
no image gallery, no Grammar Notes / Related Forms / Frequency fields.

Front - Devanagari + phonetic pronunciation + audio.
Back  - Gender (if any), an AI-generated example sentence, a personal
         scratchpad for the learner's own example, and an English reveal
         button.

Card design/styling lives here in code (not hand-edited in the Anki GUI) so
it's versioned and reproducible, same as style_cards.py.

Usage:
  .venv/bin/python3 create_simple_model.py
"""
import json
import urllib.request

ANKI_URL = "http://127.0.0.1:8765"
MODEL = "Simple Hindi Flashcard"
FIELDS = ["Hindi", "English", "Gender", "Pronunciation", "Sound", "Example", "My Example"]
CARD_NAME = "Card 1"


def anki_request(action, **params):
    payload = json.dumps({"action": action, "version": 6, "params": params}).encode()
    req = urllib.request.Request(ANKI_URL, data=payload)
    with urllib.request.urlopen(req) as resp:
        result = json.load(resp)
    if result.get("error"):
        raise RuntimeError(f"AnkiConnect error on {action}: {result['error']}")
    return result["result"]


FRONT = """<div class="stage">
  <div class="hindi">{{Hindi}}</div>
  <div class="pronunciation-chip">{{Pronunciation}}</div>
  <div class="sound-wrap sound-wrap--big">{{Sound}}</div>
</div>"""

BACK = """<div class="stage stage-reveal">
  {{#Gender}}<div class="tag-row"><span class="tag tag-gender">{{Gender}}</span></div>{{/Gender}}
  {{#Example}}<div class="extra"><span class="extra-label">example</span>{{Example}}</div>{{/Example}}
  {{#My Example}}<div class="extra"><span class="extra-label">my example</span>{{My Example}}</div>{{/My Example}}
  <div class="scratchpad" data-key="{{Hindi}}|{{English}}">
    <span class="extra-label">your example</span>
    <textarea class="scratchpad-input" rows="3" placeholder="Write your own example using this word..."></textarea>
  </div>
  <script>
  (function() {
    var boxes = document.querySelectorAll(".scratchpad");
    for (var i = 0; i < boxes.length; i++) {
      (function(box) {
        var key = "hindiScratchpad:" + box.dataset.key;
        var ta = box.querySelector("textarea");
        var saved = localStorage.getItem(key);
        if (saved) ta.value = saved;
        ta.addEventListener("input", function() {
          localStorage.setItem(key, ta.value);
        });
        // Some Anki mobile clients bind a card-wide tap/gesture handler
        // (e.g. tap-to-show-answer) on document/body in the bubble phase.
        // Stop these events from reaching it so focus + typing on the
        // textarea itself isn't hijacked.
        ["pointerdown", "touchstart", "mousedown", "click"].forEach(function(evt) {
          ta.addEventListener(evt, function(e) { e.stopPropagation(); });
        });
      })(boxes[i]);
    }
  })();
  </script>

  {{#English}}<div class="reveal"><input type="checkbox" id="reveal-english" class="reveal-checkbox"><label for="reveal-english" class="reveal-button">Show English</label><div class="reveal-content"><span class="tag tag-english">{{English}}</span></div></div>{{/English}}
</div>"""

# Same palette/typography as "Hindi Vocabulary" (see style_cards.py), minus
# the .images rules - this note type never renders an image gallery.
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

.night_mode .card, .card.night_mode { background: #1F171A; color: #F3E4E7; }
.night_mode .stage { background: #2B2024; border-color: #4A2E36; box-shadow: 0 10px 30px rgba(0,0,0,0.4); }
.night_mode .hindi { color: #F3E4E7; }
.night_mode .pronunciation-chip { color: #B98E97; }
.night_mode .sound-wrap { background: #4A2E36; }
.night_mode .tag-english { background: #382A2E; color: #F3E4E7; }
.night_mode .reveal-button { background: #2B2024; color: #EABEC3; border-color: #EABEC3; }
.night_mode .tag-gender { background: #5A2430; color: #F5DDE0; }
.night_mode .extra { background: #241A1D; color: #D9B7BE; }
.night_mode .scratchpad { background: #241A1D; color: #D9B7BE; }
.night_mode .scratchpad-input { background: #2B2024; color: #F3E4E7; border-color: #4A2E36; }
"""


def main():
    existing_models = anki_request("modelNames")
    if MODEL not in existing_models:
        anki_request(
            "createModel",
            modelName=MODEL,
            inOrderFields=FIELDS,
            css=CSS,
            cardTemplates=[{"Name": CARD_NAME, "Front": FRONT, "Back": BACK}],
        )
        print(f'Created model "{MODEL}".')
    else:
        fields = anki_request("modelFieldNames", modelName=MODEL)
        if "My Example" not in fields:
            params = {"modelName": MODEL, "fieldName": "My Example"}
            if "Example" in fields:
                params["index"] = fields.index("Example") + 1
            anki_request("modelFieldAdd", **params)
            print(f'  Added field "My Example" to model "{MODEL}".')
        anki_request(
            "updateModelTemplates",
            model={"name": MODEL, "templates": {CARD_NAME: {"Front": FRONT, "Back": BACK}}},
        )
        anki_request("updateModelStyling", model={"name": MODEL, "css": CSS})
        print(f'Model "{MODEL}" already existed - updated its template + styling.')


if __name__ == "__main__":
    main()
