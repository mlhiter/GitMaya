import logging
from typing import Callable


UNRESOLVED_LARK_LABEL = "未同步飞书姓名"
_LARK_ID_PREFIXES = ("ou_", "on_")


def is_unresolved_lark_name(value: str | None) -> bool:
    if not value:
        return True
    return value.strip().startswith(_LARK_ID_PREFIXES)


def _get_field(user, field: str):
    if isinstance(user, dict):
        return user.get(field)
    return getattr(user, field, None)


def get_lark_display_name(
    user,
    bot_factory: Callable[[str | None], object | None] | None = None,
    cache: dict[str, str] | None = None,
) -> str:
    name = _get_field(user, "name")
    if not is_unresolved_lark_name(name):
        return name.strip()

    open_id = _get_field(user, "openid")
    if open_id:
        if cache is not None and open_id in cache:
            return cache[open_id]

        bot = bot_factory(_get_field(user, "application_id")) if bot_factory else None
        if bot:
            try:
                result = bot.get(
                    f"{bot.host}/open-apis/contact/v3/users/{open_id}?user_id_type=open_id"
                ).json()
                api_user = (result.get("data") or {}).get("user") or {}
                api_name = api_user.get("name") or api_user.get("en_name")
                if not is_unresolved_lark_name(api_name):
                    display_name = api_name.strip()
                    if cache is not None:
                        cache[open_id] = display_name
                    return display_name
            except Exception as e:
                logging.warning("Failed to resolve lark user display name: %r", e)

    email = _get_field(user, "email")
    if email:
        return email.strip()
    return UNRESOLVED_LARK_LABEL
