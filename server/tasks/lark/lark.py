import logging

from celery_app import app, celery
from model.schema import (
    BindUser,
    ChatGroup,
    CodeApplication,
    IMApplication,
    ObjID,
    Repo,
    Team,
    User,
    db,
)
from sqlalchemy import func, or_
from utils.lark.manage_manual import ManageManual

from .base import get_bot_by_application_id


def get_contact_by_bot_and_department(bot, department_id):
    page_token, page_size = "", 50
    while True:
        url = f"{bot.host}/open-apis/contact/v3/users/find_by_department?page_token={page_token}&page_size={page_size}&department_id={department_id}"
        result = bot.get(url).json()
        for department_user_info in result.get("data", {}).get("items", []):
            yield department_user_info
        has_more = result.get("data", {}).get("has_more")
        if not has_more:
            break
        page_token = result.get("data", {}).get("page_token", "")


def get_child_departments(bot, department_id):
    """Get all direct child departments of a department."""
    page_token, page_size = "", 50
    while True:
        url = (
            f"{bot.host}/open-apis/contact/v3/departments/{department_id}/children"
            f"?page_token={page_token}&page_size={page_size}&department_id_type=open_department_id"
        )
        result = bot.get(url).json()
        items = result.get("data", {}).get("items", []) or []
        for item in items:
            child_id = item.get("open_department_id")
            if child_id:
                yield child_id
        has_more = result.get("data", {}).get("has_more")
        if not has_more:
            break
        page_token = result.get("data", {}).get("page_token", "")


def get_all_scoped_departments(bot, root_department_ids):
    """Traverse scoped departments recursively (BFS) and return all department ids."""
    queue = list(root_department_ids or [])
    seen = set()
    idx = 0
    while idx < len(queue):
        current = queue[idx]
        idx += 1
        if not current or current in seen:
            continue
        seen.add(current)
        yield current
        for child_id in get_child_departments(bot, current):
            if child_id not in seen:
                queue.append(child_id)


def get_contact_by_bot(bot):
    page_token, page_size = "", 100
    seen_open_ids = set()
    while True:
        url = f"{bot.host}/open-apis/contact/v3/scopes?page_token={page_token}&page_size={page_size}"
        result = bot.get(url).json()
        scope_data = result.get("data", {}) or {}
        scoped_department_ids = list(
            get_all_scoped_departments(bot, scope_data.get("department_ids", []))
        )

        for open_id in scope_data.get("user_ids", []):
            if not open_id or open_id in seen_open_ids:
                continue
            # https://open.feishu.cn/open-apis/contact/v3/users/:user_id
            user_info_url = (
                f"{bot.host}/open-apis/contact/v3/users/{open_id}?user_id_type=open_id"
            )
            user_info = bot.get(user_info_url).json()
            if user_info.get("data", {}).get("user"):
                seen_open_ids.add(open_id)
                yield user_info.get("data", {}).get("user")
            else:
                app.logger.error("can not get user_info %r", user_info)

        for department_id in scoped_department_ids:
            for department_user_info in get_contact_by_bot_and_department(
                bot, department_id
            ):
                open_id = department_user_info.get("open_id")
                if not open_id or open_id in seen_open_ids:
                    continue
                seen_open_ids.add(open_id)
                yield department_user_info

        has_more = scope_data.get("has_more")
        if not has_more:
            break
        page_token = scope_data.get("page_token", "")


@celery.task()
def get_contact_by_lark_application(application_id):
    """
    1. 按application_id找到application
    2. 获取所有能用当前应用的人员
    3. 尝试创建bind_user + user
    4. 标记已经拉取过应用人员
    """
    user_ids = []
    bot, application = get_bot_by_application_id(application_id)
    if application:
        try:
            for item in get_contact_by_bot(bot):
                user_name = item.get("name")
                user_open_id = item.get("open_id")
                user_union_id = item.get("union_id")
                user_avatar = (item.get("avatar") or {}).get("avatar_origin")
                user_email = item.get("email")

                # add bind_user and user
                bind_user_id = (
                    db.session.query(BindUser.id)
                    .filter(
                        BindUser.openid == user_open_id,
                        BindUser.status == 0,
                    )
                    .limit(1)
                    .scalar()
                )
                bind_user = (
                    db.session.query(BindUser)
                    .filter(
                        BindUser.id == bind_user_id,
                        BindUser.status == 0,
                    )
                    .first()
                    if bind_user_id
                    else None
                )

                # Existing lark bind user: keep profile fresh and repair historical placeholder values.
                if bind_user:
                    updated = False
                    if bind_user.application_id != application_id:
                        bind_user.application_id = application_id
                        updated = True
                    if user_union_id and bind_user.unionid != user_union_id:
                        bind_user.unionid = user_union_id
                        updated = True
                    if user_name and bind_user.name != user_name:
                        bind_user.name = user_name
                        updated = True
                    if user_email and bind_user.email != user_email:
                        bind_user.email = user_email
                        updated = True
                    if user_avatar and bind_user.avatar != user_avatar:
                        bind_user.avatar = user_avatar
                        updated = True
                    if updated:
                        db.session.commit()
                    continue

                user_id = (
                    db.session.query(User.id)
                    .filter(
                        User.unionid == user_union_id,
                        User.status == 0,
                    )
                    .limit(1)
                    .scalar()
                )
                if not user_id:
                    user_id = ObjID.new_id()
                    user = User(
                        id=user_id,
                        unionid=user_union_id,
                        name=user_name,
                        avatar=user_avatar,
                        email=user_email,
                    )
                    db.session.add(user)
                    db.session.flush()

                bind_user_id = ObjID.new_id()
                bind_user = BindUser(
                    id=bind_user_id,
                    user_id=user_id,
                    platform="lark",
                    application_id=application_id,
                    unionid=user_union_id,
                    openid=user_open_id,
                    email=user_email,
                    name=user_name,
                    avatar=user_avatar,
                    extra=item,
                )
                db.session.add(bind_user)
                db.session.commit()
                user_ids.append(bind_user_id)
            db.session.query(IMApplication).filter(
                IMApplication.id == application.id,
            ).update(dict(status=1))
            db.session.commit()
        except Exception as e:
            # can not get contacts
            app.logger.exception(e)

    return user_ids


@celery.task()
def get_contact_for_all_lark_application():
    for application in db.session.query(IMApplication).filter(
        IMApplication.status == 0,
    ):
        user_ids = get_contact_by_lark_application(application.id)
        app.logger.info(
            "success to get_contact_fo_lark_application %r %r",
            application.id,
            len(user_ids),
        )
