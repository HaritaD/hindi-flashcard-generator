#!/usr/bin/env python3
"""CLI entry point: generate a single Anki flashcard from a Devanagari word.

Usage:
  .venv/bin/python3 main.py --hindi "किताब" --english "book" --gender "F" \\
      --style images --deck "Fluent Forever Hindi Deck"

  .venv/bin/python3 main.py --hindi "किताब" --style simple --deck "Claude Cards"

--style is "images" (Google-Images gallery, default) or "simple" (no image
search/gallery - Devanagari + audio + pronunciation + example sentence only).
English/Gender are optional context for the AI generation steps; omit
--pronunciation to have Claude generate it.
"""
import argparse
import sys

from card_generator import DEFAULT_DECK, STYLE_IMAGES, STYLES, CardGenerationError, generate_card


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--hindi", required=True, help="Devanagari word")
    parser.add_argument("--style", choices=STYLES, default=STYLE_IMAGES, help="card style (default: images)")
    parser.add_argument("--deck", default=DEFAULT_DECK, help="Anki deck to add the card to")
    parser.add_argument("--english", default="", help="English meaning (optional)")
    parser.add_argument("--gender", default="", help="grammatical gender, e.g. M/F (optional)")
    parser.add_argument("--pronunciation", default="", help="override the AI-generated pronunciation")
    parser.add_argument(
        "--my-example",
        default="",
        dest="my_example",
        help="your own example sentence (e.g. from a show), shown alongside the AI-generated one",
    )
    parser.add_argument(
        "--images",
        type=int,
        default=7,
        help="max number of images to attach when --style=images (default: 7)",
    )
    args = parser.parse_args()

    try:
        result = generate_card(
            hindi=args.hindi,
            english=args.english,
            gender=args.gender,
            deck=args.deck,
            style=args.style,
            pronunciation=args.pronunciation,
            my_example=args.my_example,
            num_images=args.images,
            log=lambda msg: print(f"  ({msg})"),
        )
    except CardGenerationError as e:
        sys.exit(str(e))

    if result["status"] == "skipped":
        print(f"Skipped: {result['message']}")
    else:
        print(result["message"])


if __name__ == "__main__":
    main()
