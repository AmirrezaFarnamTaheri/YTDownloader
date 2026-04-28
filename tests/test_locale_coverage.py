"""Locale coverage checks."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_non_english_locales_cover_all_english_keys():
    english = json.loads((ROOT / "locales" / "en.json").read_text(encoding="utf-8"))

    for locale_path in (ROOT / "locales").glob("*.json"):
        if locale_path.name == "en.json":
            continue

        locale_data = json.loads(locale_path.read_text(encoding="utf-8"))
        missing = sorted(set(english) - set(locale_data))

        assert missing == [], f"{locale_path.name} missing locale keys: {missing}"


def test_runtime_locale_keys_exist_in_english():
    english = json.loads((ROOT / "locales" / "en.json").read_text(encoding="utf-8"))
    required = {
        "delete",
        "info_fetched_success",
        "item_deleted",
        "load_more",
        "search_history",
        "url_copied",
    }

    assert sorted(required - set(english)) == []
