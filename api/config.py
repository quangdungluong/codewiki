def load_language_config():
    default_config = {
        "supported_languages": {
            "en": "English",
            "vi": "Vietnamese (Tiếng Việt)",
        },
        "default": "en",
    }
    return default_config


configs = {}
configs["language_config"] = load_language_config()
