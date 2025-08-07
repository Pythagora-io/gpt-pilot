import json
import os
from typing import Optional

_translations = {}
_current_locale = "en"

def load_translations(locale: str):
    """Loads translation strings for the given locale."""
    global _translations
    locale_file = os.path.join(os.path.dirname(__file__), f"{locale}.json")
    if os.path.exists(locale_file):
        with open(locale_file, "r", encoding="utf-8") as f:
            _translations = json.load(f)
    else:
        _translations = {}

def set_locale(locale: str):
    """Sets the current locale."""
    global _current_locale
    _current_locale = locale
    load_translations(locale)

def get_locale() -> str:
    """Returns the current locale."""
    return _current_locale

def _(key: str, **kwargs) -> str:
    """
    Translates the given key.

    :param key: The key to translate.
    :param kwargs: The arguments to format the string with.
    :return: The translated string.
    """
    if not _translations:
        load_translations(_current_locale)

    return _translations.get(key, key).format(**kwargs)
