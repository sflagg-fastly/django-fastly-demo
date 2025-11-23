from django.conf import settings

DEFAULTS = {
    "API_URL": "https://api.fastly.com",
    "ENABLE_LOGGING": True,
}


def get_setting(name: str):
    user_settings = getattr(settings, "FASTLY", {})
    if name in user_settings:
        return user_settings[name]
    return DEFAULTS.get(name)
