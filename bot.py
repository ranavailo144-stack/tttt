import os
import json

SETTINGS_FILE = "settings.json"


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)
                data.setdefault("custom_emoji_id", "")
                return data
        except Exception:
            pass

    return {
        "api_key": "",
        "custom_emoji_id": ""
    }


def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as file:
        json.dump(settings, file, ensure_ascii=False, indent=2)


settings = load_settings()
