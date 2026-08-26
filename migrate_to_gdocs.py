#!/usr/bin/env python3
"""Duplicate notes from 'Hindi Vocab' into a new deck using the 'Hindi gDocs'
note type, converting legacy 'Basic' Front/Back HTML into structured fields.
Also adds a reverse ('Card 2') template to 'Hindi gDocs' so every note using
it supports both Hindi->meaning and meaning->Hindi review. The source deck is
left untouched.

Usage:
  python3 migrate_to_gdocs.py --dry-run
  python3 migrate_to_gdocs.py --dest-deck "Hindi Vocab (gDocs)"
"""
import argparse
import json
import re
import urllib.request

ANKI_URL = "http://127.0.0.1:8765"
SOURCE_DECK = "Hindi Vocab"
MODEL = "Hindi gDocs"

CARD2_FRONT = """{{#Gender}}
<div class="gender">{{Gender}}</div>
{{/Gender}}

<div class="images">{{image}}</div>"""

CARD2_BACK = """{{FrontSide}}

<hr id="answer">

<div class="hindi">{{Hindi}}</div>

{{Sound}}

<div class="pronunciation">{{Pronunciation}}</div>"""


def anki(action, **params):
    payload = json.dumps({"action": action, "version": 6, "params": params}).encode()
    req = urllib.request.Request(ANKI_URL, data=payload)
    with urllib.request.urlopen(req) as resp:
        result = json.load(resp)
    if result.get("error"):
        raise RuntimeError(f"{action} error: {result['error']}")
    return result["result"]


def ensure_reverse_card():
    templates = anki("modelTemplates", modelName=MODEL)
    if "Card 2" in templates:
        return
    anki(
        "modelTemplateAdd",
        modelName=MODEL,
        template={"Name": "Card 2", "Front": CARD2_FRONT, "Back": CARD2_BACK},
    )
    print("Added reverse 'Card 2' template to Hindi gDocs.")


def clean_text(html):
    text = html.replace("&nbsp;", " ")
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.I)
    text = re.sub(r"</?div[^>]*>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def convert_basic(fields):
    hindi = clean_text(fields["Front"]["value"])
    back = fields["Back"]["value"]
    images = "".join(re.findall(r"<img[^>]*>", back))
    sounds = re.findall(r"\[sound:[^\]]+\]", back)
    sound = sounds[0] if sounds else ""
    remainder = back
    for tag in re.findall(r"<img[^>]*>", back):
        remainder = remainder.replace(tag, "")
    for s in sounds:
        remainder = remainder.replace(s, "")
    english = clean_text(remainder)
    return {
        "Hindi": hindi,
        "English": english,
        "Gender": "",
        "Pronunciation": "",
        "Sound": sound,
        "image": images,
        "Grammar Notes": "",
        "Related Forms / Synonyms": "",
        "Example": "",
        "Frequency": "",
    }


def convert_gdocs(fields):
    return {name: data["value"] for name, data in fields.items()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dest-deck", default="Hindi Vocab (gDocs)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ensure_reverse_card()

    note_ids = anki("findNotes", query=f'deck:"{SOURCE_DECK}"')
    infos = anki("notesInfo", notes=note_ids)
    print(f"Found {len(infos)} notes in '{SOURCE_DECK}'")

    if not args.dry_run:
        anki("createDeck", deck=args.dest_deck)

    created, skipped = 0, 0
    for n in infos:
        if n["modelName"] == "Basic":
            fields = convert_basic(n["fields"])
        elif n["modelName"] == MODEL:
            fields = convert_gdocs(n["fields"])
        else:
            print(f"  skip note {n['noteId']}: unhandled model '{n['modelName']}'")
            skipped += 1
            continue

        if not fields.get("Hindi"):
            print(f"  skip note {n['noteId']}: no Hindi text after cleanup")
            skipped += 1
            continue

        if args.dry_run:
            print(
                f"  [dry-run] Hindi={fields['Hindi']!r} sound={'yes' if fields['Sound'] else 'no'} "
                f"english={fields['English'][:40]!r}"
            )
            created += 1
            continue

        note = {
            "deckName": args.dest_deck,
            "modelName": MODEL,
            "fields": fields,
            "options": {"allowDuplicate": True},
            "tags": n.get("tags", []) + ["migrated"],
        }
        anki("addNote", note=note)
        created += 1

    verb = "Would create" if args.dry_run else "Created"
    print(f"{verb} {created} notes, skipped {skipped}.")


if __name__ == "__main__":
    main()
