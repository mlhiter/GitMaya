import os
import re
import time
from argparse import ArgumentError

from app import app
from connectai.lark.oauth import Server as OauthServerBase
from connectai.lark.sdk import Bot, MarketBot
from connectai.lark.webhook import LarkServer as LarkServerBase
from flask import session
from tasks.lark import get_bot_by_application_id, get_contact_by_lark_application
from utils.lark.parser import GitMayaLarkParser
from utils.lark.post_message import post_content_to_markdown


def get_bot(app_id):
    with app.app_context():
        bot, _ = get_bot_by_application_id(app_id)
        return bot


class LarkServer(LarkServerBase):
    def get_bot(self, app_id):
        return get_bot(app_id)


class OauthServer(OauthServerBase):
    def get_bot(self, app_id):
        return get_bot(app_id)


hook = LarkServer(prefix="/api/feishu/hook")
oauth = OauthServer(prefix="/api/feishu/oauth")
parser = GitMayaLarkParser()
_BOT_PROFILE_CACHE = {}
_BOT_PROFILE_CACHE_TTL_SECONDS = 600


def _normalize_mention_name(value):
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", "", value).strip().lower()


def _extract_event_message(raw_message):
    if not isinstance(raw_message, dict):
        return {}
    event = raw_message.get("event")
    if not isinstance(event, dict):
        return {}
    message = event.get("message")
    return message if isinstance(message, dict) else {}


def _extract_leading_mention_and_rest(text):
    if not isinstance(text, str):
        return "", "", ""

    candidate = text.replace("\u3000", " ").lstrip()
    if not candidate:
        return "", "", ""

    mention_tag = re.match(r"^<at\b([^>]*)>(.*?)</at>\s*", candidate)
    if mention_tag:
        attrs = mention_tag.group(1) or ""
        mention_name = (mention_tag.group(2) or "").strip()
        mention_id_match = re.search(r'user_id=[\"\']([^\"\']+)[\"\']', attrs)
        mention_id = mention_id_match.group(1).strip() if mention_id_match else ""
        rest = candidate[mention_tag.end() :].lstrip()
        return mention_id, mention_name, rest

    parts = candidate.split(None, 1)
    first = parts[0] if parts else ""
    rest = parts[1].lstrip() if len(parts) > 1 else ""
    if first.startswith("@") and len(first) > 1:
        return "", first[1:], rest
    if first.startswith("ou_") or first.startswith("on_"):
        return first, "", rest
    return "", "", candidate


def _resolve_mentioned_user(mention_id, mention_name, raw_message):
    message = _extract_event_message(raw_message)
    mentions = message.get("mentions", [])
    if not isinstance(mentions, list):
        mentions = []

    normalized_mention_name = _normalize_mention_name(mention_name)
    for mention in mentions:
        if not isinstance(mention, dict):
            continue
        mention_ident = mention.get("id", {})
        if not isinstance(mention_ident, dict):
            mention_ident = {}

        open_id = mention_ident.get("open_id", "")
        user_id = mention_ident.get("user_id", "")
        name = mention.get("name", "")
        key = mention.get("key", "")
        if mention_id and mention_id in {open_id, user_id, key}:
            return open_id, name
        if normalized_mention_name and normalized_mention_name == _normalize_mention_name(
            name
        ):
            return open_id, name

    return "", mention_name


def _extract_bot_profile_fields(payload):
    names = set()
    open_ids = set()
    if not isinstance(payload, dict):
        return names, open_ids

    def collect_from_mapping(mapping):
        if not isinstance(mapping, dict):
            return

        for key in ["open_id", "bot_open_id"]:
            value = mapping.get(key)
            if isinstance(value, str) and value.startswith("ou_"):
                open_ids.add(value)

        for key in [
            "name",
            "app_name",
            "bot_name",
            "display_name",
            "app_display_name",
        ]:
            value = mapping.get(key)
            normalized = _normalize_mention_name(value)
            if normalized:
                names.add(normalized)

        for key in ["i18n_name", "i18n_names", "name_i18n", "app_name_i18n"]:
            value = mapping.get(key)
            if isinstance(value, dict):
                for item in value.values():
                    normalized = _normalize_mention_name(item)
                    if normalized:
                        names.add(normalized)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        normalized = _normalize_mention_name(item)
                        if normalized:
                            names.add(normalized)
                    elif isinstance(item, dict):
                        for sub_item in item.values():
                            normalized = _normalize_mention_name(sub_item)
                            if normalized:
                                names.add(normalized)

    collect_from_mapping(payload)
    collect_from_mapping(payload.get("bot"))
    collect_from_mapping(payload.get("app"))
    return names, open_ids


def _get_bot_profile(bot):
    app_id = getattr(bot, "app_id", "")
    if not app_id:
        return set(), set()

    now = time.time()
    cache = _BOT_PROFILE_CACHE.get(app_id)
    if cache and cache["expired_at"] > now:
        return cache["names"], cache["open_ids"]

    names = set()
    open_ids = set()
    profile_urls = [
        f"{bot.host}/open-apis/bot/v3/info",
        f"{bot.host}/open-apis/application/v6/app",
    ]
    for url in profile_urls:
        try:
            result = bot.get(url).json()
        except Exception as e:
            app.logger.debug(
                "failed to fetch bot profile, app_id=%s url=%s error=%r", app_id, url, e
            )
            continue
        if isinstance(result, dict) and result.get("code", 0) not in [0, None]:
            continue
        payload = result.get("data", result) if isinstance(result, dict) else result
        profile_names, profile_open_ids = _extract_bot_profile_fields(payload)
        names.update(profile_names)
        open_ids.update(profile_open_ids)

    env_bot_name = _normalize_mention_name(os.environ.get("LARK_BOT_NAME", ""))
    if env_bot_name:
        names.add(env_bot_name)
    names.add("gitmaya")

    _BOT_PROFILE_CACHE[app_id] = {
        "names": names,
        "open_ids": open_ids,
        "expired_at": now + _BOT_PROFILE_CACHE_TTL_SECONDS,
    }
    return names, open_ids


def _is_command_for_current_bot(text, raw_message, bot):
    message = _extract_event_message(raw_message)
    chat_type = message.get("chat_type")

    if chat_type != "group":
        return True

    mention_id, mention_name, rest = _extract_leading_mention_and_rest(text)
    if not isinstance(rest, str):
        rest = ""
    if not rest.startswith("/"):
        return False
    if not mention_id and not mention_name:
        # 群聊命令必须显式 @机器人，避免误触发
        return False

    mentioned_open_id, mentioned_name = _resolve_mentioned_user(
        mention_id, mention_name, raw_message
    )
    bot_names, bot_open_ids = _get_bot_profile(bot)

    if mentioned_open_id and mentioned_open_id in bot_open_ids:
        return True
    normalized_name = _normalize_mention_name(mentioned_name)
    if normalized_name and normalized_name in bot_names:
        return True
    return False


def _handle_message_text(bot, message_id, content, message, text, **kwargs):
    try:
        if _is_command_for_current_bot(text, message, bot):
            parser.parse_args(text, bot.app_id, message_id, content, message, **kwargs)
        else:
            parser.on_comment(text, bot.app_id, message_id, content, message, **kwargs)
    except ArgumentError:
        parser.on_comment(text, bot.app_id, message_id, content, message, **kwargs)
    except Exception as e:
        app.logger.exception(e)


@hook.on_bot_event(event_type="card:action")
def on_card_action(bot, token, data, message, *args, **kwargs):
    # TODO 将action中的按钮，或者选择的东西，重新组织成 command 继续走parser的逻辑
    if "action" in data and "command" in data["action"].get("value", {}):
        command = data["action"]["value"]["command"]
        suffix = data["action"]["value"].get("suffix")
        # 将选择的直接拼接到后面
        if suffix == "$option" and "option" in data["action"]:
            command = command + data["action"]["option"]
        try:
            parser.parse_args(
                command,
                bot.app_id,
                data["open_message_id"],
                data,
                message,
                **kwargs,
            )
        except Exception as e:
            app.logger.exception(e)
    else:
        app.logger.error("unkown card_action %r", (bot, token, data, message, *args))


@hook.on_bot_message(message_type="post")
def on_post_message(bot, message_id, content, message, *args, **kwargs):
    text, title = post_content_to_markdown(content, False)
    content["text"] = text
    _handle_message_text(bot, message_id, content, message, text, **kwargs)


@hook.on_bot_message(message_type="text")
def on_text_message(bot, message_id, content, message, *args, **kwargs):
    text = content["text"]
    # print("reply_text", message_id, text)
    # bot.reply_text(message_id, "reply: " + text)
    _handle_message_text(bot, message_id, content, message, text, **kwargs)


@hook.on_bot_event(event_type="p2p_chat_create")
def on_bot_event(bot, event_id, event, message, *args, **kwargs):
    parser.on_welcome(bot.app_id, event_id, event, message, **kwargs)


@oauth.on_bot_event(event_type="oauth:user_info")
def on_oauth_user_info(bot, event_id, user_info, *args, **kwargs):
    # oauth user_info
    print("oauth", user_info)
    # TODO save bind user
    session["user_id"] = user_info["union_id"]
    session.permanent = True
    # TODO ISV application
    if isinstance(bot, MarketBot):
        with app.app_context():
            task = get_contact_by_lark_application.delay(bot.app_id)
            app.logger.info("try get_contact_by_lark_application %r", bot.app_id)
    return user_info


app.register_blueprint(oauth.get_blueprint())
app.register_blueprint(hook.get_blueprint())
