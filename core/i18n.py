import os
import json
from flask import session, request, current_app


class I18nManager:
    _translations = {}
    _default_lang = "ko"

    @classmethod
    def load_translations(cls):
        i18n_dir = os.path.join(current_app.root_path, "i18n")
        if not os.path.exists(i18n_dir):
            return

        for filename in os.listdir(i18n_dir):
            if filename.endswith(".json"):
                lang = filename.split(".")[0]
                with open(os.path.join(i18n_dir, filename), "r", encoding="utf-8") as f:
                    cls._translations[lang] = json.load(f)

    @classmethod
    def get_lang(cls):
        lang = session.get("lang")
        if not lang:
            accept_lang = request.headers.get("Accept-Language", "")
            if "en" in accept_lang.lower():
                lang = "en"
            else:
                lang = cls._default_lang
        return lang

    @classmethod
    def get_text(cls, key, default=None):
        lang = cls.get_lang()
        translations = cls._translations.get(
            lang, cls._translations.get(cls._default_lang, {})
        )
        return translations.get(key, default or key)


def _(key, default=None):
    return I18nManager.get_text(key, default)
