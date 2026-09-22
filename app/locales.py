"""Language negotiation for shareable UI URLs (Korean uses /kr)."""
LANGUAGE_PATHS = {"zh": "zh", "kr": "ko", "en": "en", "ja": "ja", "fr": "fr", "es": "es", "ru": "ru", "vi": "vi", "mn": "mn", "ar": "ar", "th": "th", "id": "id"}
UI_PATHS = {language: path for path, language in LANGUAGE_PATHS.items()}

def resolve_language_path(saved: str | None, accept_language: str) -> str:
    if saved in UI_PATHS:
        return UI_PATHS[saved]
    preferences = []
    for index, item in enumerate(accept_language.split(',')):
        parts = item.strip().lower().split(';')
        language = parts[0].replace('_', '-').split('-')[0]
        quality = 1.0
        try:
            for parameter in parts[1:]:
                if parameter.strip().startswith('q='):
                    quality = float(parameter.strip()[2:])
        except ValueError:
            continue
        if 0 < quality <= 1 and language in UI_PATHS:
            preferences.append((-quality, index, UI_PATHS[language]))
    return min(preferences)[2] if preferences else 'zh'
