#!/usr/bin/env python3
"""Local web UI for generating a single Hindi Anki flashcard.

Flow: type a Devanagari word -> spell-check + English meaning suggested by
Claude -> confirm/edit the meaning -> pick a card style and deck -> create
the card in Anki (via AnkiConnect, so Anki must be running).

Usage:
  ../.venv/bin/python3 webui/app.py
then open http://127.0.0.1:5050
"""
import os
import sys

from flask import Flask, jsonify, render_template, request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from card_generator import (  # noqa: E402
    CardGenerationError,
    STYLES,
    check_word,
    generate_card,
    get_api_keys,
    list_decks,
)

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/decks")
def api_decks():
    try:
        return jsonify({"decks": list_decks()})
    except CardGenerationError as e:
        return jsonify({"error": str(e)}), 502


@app.route("/api/check-word", methods=["POST"])
def api_check_word():
    data = request.get_json(force=True, silent=True) or {}
    hindi = (data.get("hindi") or "").strip()

    keys = get_api_keys()
    if not keys["anthropic"]:
        return jsonify({"error": "Missing ANTHROPIC_API_KEY (set as an env var or in .env)"}), 500

    try:
        result = check_word(hindi, keys["anthropic"])
    except Exception as e:
        return jsonify({"error": f"Spell-check failed: {e}"}), 502
    return jsonify(result)


@app.route("/api/create-card", methods=["POST"])
def api_create_card():
    data = request.get_json(force=True, silent=True) or {}
    hindi = (data.get("hindi") or "").strip()
    english = (data.get("english") or "").strip()
    gender = (data.get("gender") or "").strip()
    deck = (data.get("deck") or "").strip()
    style = (data.get("style") or "").strip()
    my_example = (data.get("my_example") or "").strip()

    if not hindi:
        return jsonify({"error": "Missing Hindi word"}), 400
    if not deck:
        return jsonify({"error": "Missing deck"}), 400
    if style not in STYLES:
        return jsonify({"error": f"style must be one of {STYLES}"}), 400

    logs = []
    try:
        result = generate_card(
            hindi=hindi,
            english=english,
            gender=gender,
            deck=deck,
            style=style,
            my_example=my_example,
            log=logs.append,
        )
    except CardGenerationError as e:
        return jsonify({"error": str(e), "logs": logs}), 502

    result["logs"] = logs
    return jsonify(result)


if __name__ == "__main__":
    # 0.0.0.0 so this is also reachable from other devices (e.g. a phone) on
    # the same local network, at http://<this-machine's-LAN-IP>:5050 - never
    # expose this port beyond your local network (no auth on these routes).
    app.run(host="0.0.0.0", port=5050, debug=True)
