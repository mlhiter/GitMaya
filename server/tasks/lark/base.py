import json
import logging
import os
from functools import wraps
from urllib.parse import urlencode

from connectai.lark.sdk import Bot
from model.schema import (
    ChatGroup,
    CodeApplication,
    IMApplication,
    Issue,
    ObjID,
    PullRequest,
    Repo,
    Team,
    db,
)
from sqlalchemy import or_
from utils.constant import GitHubPermissionError
from utils.redis import RedisStorage

_MISSING_GITHUB_AUTH_ERRORS = {
    "Failed to get bind user.",
    "Failed to get access token.",
}


def get_scoped_im_application_ids(app_id):
    return [
        item
        for item, in db.session.query(IMApplication.id)
        .filter(
            or_(
                IMApplication.app_id == app_id,
                IMApplication.id == app_id,
            ),
            IMApplication.status.in_([0, 1]),
        )
        .all()
    ]


def get_chat_group_by_chat_id(chat_id, app_id=None):
    query = db.session.query(ChatGroup).filter(
        ChatGroup.chat_id == chat_id,
        ChatGroup.status == 0,
    )
    if app_id:
        im_application_ids = get_scoped_im_application_ids(app_id)
        if not im_application_ids:
            return None
        query = query.filter(ChatGroup.im_application_id.in_(im_application_ids))

    return query.order_by(ChatGroup.modified.desc()).first()


def get_repo_name_by_repo_id(repo_id):
    repo = get_repo_by_repo_id(repo_id)
    return repo.name


def get_repo_by_repo_id(repo_id):
    repo = (
        db.session.query(Repo)
        .filter(
            Repo.id == repo_id,
            Repo.status == 0,
        )
        .first()
    )
    return repo


def get_team_by_repo(repo):
    if not repo:
        return None

    code_application = (
        db.session.query(CodeApplication)
        .filter(
            CodeApplication.id == repo.application_id,
            CodeApplication.status.in_([0, 1]),
        )
        .first()
    )
    if not code_application:
        return None

    return (
        db.session.query(Team)
        .filter(
            Team.id == code_application.team_id,
            Team.status == 0,
        )
        .first()
    )


def build_github_oauth_url(host, app_id=None, open_id=None):
    base_url = f"{host}/api/github/oauth"
    if app_id and open_id:
        return f"{base_url}?{urlencode({'app_id': app_id, 'open_id': open_id})}"
    return base_url


def _extract_lark_sender_open_id(raw_message):
    if not isinstance(raw_message, dict):
        return None
    return (
        raw_message.get("event", {})
        .get("sender", {})
        .get("sender_id", {})
        .get("open_id")
    )


def _resolve_action_label(func_name: str) -> str:
    return "评论" if "comment" in func_name else "操作"


def _build_rebind_tip_content(app_id: str, open_id: str | None, action_label: str) -> str:
    mention_prefix = f"<at id={open_id}></at> " if open_id else ""
    host = os.environ.get("DOMAIN")
    if host:
        oauth_url = build_github_oauth_url(host, app_id, open_id)
        bind_tip = f"[请点击绑定 GitHub 账号后重试]({oauth_url})"
    else:
        bind_tip = "请在飞书输入 /bind 绑定 GitHub 账号后重试。"

    return (
        f"{mention_prefix}{action_label}失败：当前用户未完成 GitHub 授权或授权已过期。\n"
        f"{bind_tip}"
    )


def _send_github_rebind_tip(func_name: str, args):
    if len(args) < 4:
        return False
    from .manage import send_manage_fail_message

    app_id, message_id, content, raw_message = args[-4:]
    open_id = _extract_lark_sender_open_id(raw_message)
    action_label = _resolve_action_label(func_name)
    send_manage_fail_message(
        _build_rebind_tip_content(app_id, open_id, action_label),
        app_id,
        message_id,
        content,
        raw_message,
    )
    return True


def get_bot_by_application_id(app_id):
    application = (
        db.session.query(IMApplication)
        .filter(
            or_(
                IMApplication.app_id == app_id,
                IMApplication.id == app_id,
            ),
            IMApplication.status.in_([0, 1]),
        )
        .order_by(IMApplication.modified.desc())
        .first()
    )
    if application:
        return (
            Bot(
                app_id=application.app_id,
                app_secret=application.app_secret,
                encrypt_key=application.extra.get("encrypt_key"),
                verification_token=application.extra.get("verification_token"),
                storage=RedisStorage(),
            ),
            application,
        )
    return None, None


def get_git_object_by_message_id(message_id):
    """
    根据message_id区分Repo、Issue、PullRequest对象

    参数：
    message_id：消息ID

    返回值：
    repo：Repo对象，如果存在
    issue：Issue对象，如果存在
    pr：PullRequest对象，如果存在
    """
    issue = (
        db.session.query(Issue)
        .filter(
            Issue.message_id == message_id,
        )
        .first()
    )
    if issue:
        return None, issue, None
    pr = (
        db.session.query(PullRequest)
        .filter(
            PullRequest.message_id == message_id,
        )
        .first()
    )
    if pr:
        return None, None, pr
    repo = (
        db.session.query(Repo)
        .filter(
            Repo.message_id == message_id,
        )
        .first()
    )
    if repo:
        return repo, None, None

    return None, None, None


def with_authenticated_github():
    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            """
            1. 这个装饰器用来统一处理错误消息
            2. github rest api调用出错的时候抛出异常
            3. 这个装饰器捕获特定的异常，给操作者特定的报错消息
            """
            try:
                return func(*args, **kwargs)
            except GitHubPermissionError as e:
                logging.warning("GitHub permission error in %s: %s", func.__name__, e)
                try:
                    _send_github_rebind_tip(func.__name__, args)
                except Exception as inner_error:
                    logging.error(inner_error)
                return None
            except Exception as e:
                if str(e) in _MISSING_GITHUB_AUTH_ERRORS:
                    logging.warning("GitHub auth missing in %s: %s", func.__name__, e)
                    try:
                        _send_github_rebind_tip(func.__name__, args)
                    except Exception as inner_error:
                        logging.error(inner_error)
                    return None
                raise

        return wrapper

    return decorate
