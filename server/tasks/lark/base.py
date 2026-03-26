import json
import logging
import os
from functools import wraps
from urllib.parse import urlencode

from connectai.lark.sdk import Bot
from model.schema import ChatGroup, IMApplication, Issue, ObjID, PullRequest, Repo, db
from sqlalchemy import or_
from utils.constant import GitHubPermissionError
from utils.redis import RedisStorage


def get_chat_group_by_chat_id(chat_id, app_id=None):
    query = db.session.query(ChatGroup).filter(
        ChatGroup.chat_id == chat_id,
        ChatGroup.status == 0,
    )
    if app_id:
        im_application_id = (
            db.session.query(IMApplication.id)
            .filter(
                or_(
                    IMApplication.app_id == app_id,
                    IMApplication.id == app_id,
                ),
                IMApplication.status.in_([0, 1]),
            )
            .limit(1)
            .scalar()
        )
        if im_application_id:
            query = query.filter(ChatGroup.im_application_id == im_application_id)

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


def build_github_oauth_url(host, app_id=None, open_id=None):
    base_url = f"{host}/api/github/oauth"
    if app_id and open_id:
        return f"{base_url}?{urlencode({'app_id': app_id, 'open_id': open_id})}"
    return base_url


def get_bot_by_application_id(app_id):
    application = (
        db.session.query(IMApplication)
        .filter(
            or_(
                IMApplication.app_id == app_id,
                IMApplication.id == app_id,
            )
        )
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
                try:
                    from .manage import send_manage_fail_message

                    app_id, message_id, content, raw_message = args[-4:]
                    host = os.environ.get("DOMAIN")
                    open_id = (
                        raw_message.get("event", {})
                        .get("sender", {})
                        .get("sender_id", {})
                        .get("open_id")
                    )
                    oauth_url = build_github_oauth_url(host, app_id, open_id)
                    send_manage_fail_message(
                        f"[请点击绑定 GitHub 账号后重试]({oauth_url})",
                        app_id,
                        message_id,
                        content,
                        raw_message,
                    )
                except Exception as e:
                    logging.error(e)
            except Exception as e:
                raise e

        return wrapper

    return decorate
