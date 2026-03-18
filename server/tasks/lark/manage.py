import logging
import os

from celery_app import app, celery
from connectai.lark.sdk import FeishuShareChatMessage, FeishuTextMessage
from model.schema import (
    BindUser,
    ChatGroup,
    CodeApplication,
    CodeUser,
    IMApplication,
    IMUser,
    ObjID,
    Repo,
    RepoUser,
    Team,
    TeamMember,
    db,
)
from sqlalchemy import or_
from sqlalchemy.orm import aliased
from utils.lark.chat_manual import ChatManual
from utils.lark.manage_fail import ManageFaild
from utils.lark.manage_manual import ManageManual, ManageNew, ManageSetting, ManageView
from utils.lark.manage_repo_detect import ManageRepoDetect
from utils.lark.manage_success import ManageSuccess
from utils.lark.repo_info import RepoInfo
from utils.lark.repo_manual import RepoManual

from .base import build_github_oauth_url, get_bot_by_application_id


def _get_chat_meta(bot, chat_id):
    if not chat_id:
        return "", "", {}
    try:
        result = bot.get(f"{bot.host}/open-apis/im/v1/chats/{chat_id}").json()
        data = result.get("data", {})
        # 兼容不同版本字段
        chat = data.get("chat", data) if isinstance(data, dict) else {}
        return chat.get("name", ""), chat.get("description", ""), result
    except Exception as e:
        logging.error(e)
    return "", "", {}


def _is_chat_owner_or_manager(bot, chat_id, open_id):
    if not chat_id or not open_id:
        return False

    _, _, chat_raw = _get_chat_meta(bot, chat_id)
    data = chat_raw.get("data", {}) if isinstance(chat_raw, dict) else {}
    chat = data.get("chat", data) if isinstance(data, dict) else {}

    owners = set()
    owner_candidates = [
        chat.get("owner_id"),
        chat.get("owner_open_id"),
        data.get("owner_id"),
        data.get("owner_open_id"),
    ]
    owner_obj = chat.get("owner", {})
    if isinstance(owner_obj, dict):
        owner_candidates.extend(
            [
                owner_obj.get("id"),
                owner_obj.get("open_id"),
            ]
        )
    for candidate in owner_candidates:
        if candidate:
            owners.add(candidate)

    managers = set()
    manager_candidates = [
        chat.get("user_manager_id_list"),
        chat.get("manager_id_list"),
        chat.get("admin_id_list"),
        data.get("user_manager_id_list"),
        data.get("manager_id_list"),
        data.get("admin_id_list"),
    ]
    for values in manager_candidates:
        if isinstance(values, list):
            for v in values:
                if isinstance(v, str) and v:
                    managers.add(v)
                elif isinstance(v, dict):
                    managers.update(
                        [
                            x
                            for x in [v.get("id"), v.get("open_id"), v.get("user_id")]
                            if x
                        ]
                    )

    if open_id in owners or open_id in managers:
        return True

    # 回退到成员列表做角色判断，避免群详情字段差异导致误判
    try:
        members_raw = bot.get(
            f"{bot.host}/open-apis/im/v1/chats/{chat_id}/members"
            "?member_id_type=open_id&page_size=200"
        ).json()
        items = members_raw.get("data", {}).get("items", [])
        for item in items:
            if not isinstance(item, dict):
                continue
            member_id = item.get("member_id") or item.get("open_id") or item.get("id")
            if member_id != open_id:
                continue

            if item.get("is_owner") or item.get("is_admin"):
                return True

            role = str(
                item.get("role")
                or item.get("chat_role")
                or item.get("role_type")
                or ""
            ).lower()
            if role in {"owner", "admin", "manager"}:
                return True
    except Exception as e:
        logging.error(e)

    return False


@celery.task()
def send_welcome_message(app_id, event_id, event, message, *args, **kwargs):
    bot, application = get_bot_by_application_id(app_id)
    if application:
        team = (
            db.session.query(Team)
            .filter(
                Team.id == application.team_id,
                Team.status == 0,
            )
            .first()
        )
        if team:
            # p2p_chat_create v1.0
            open_id = message["event"]["operator"].get("open_id", None)
            github_user = (
                db.session.query(CodeUser)
                .join(
                    TeamMember,
                    TeamMember.code_user_id == CodeUser.id,
                )
                .join(
                    IMUser,
                    IMUser.id == TeamMember.im_user_id,
                )
                .filter(
                    IMUser.openid == open_id,
                    TeamMember.team_id == team.id,
                )
                .first()
            )
            if not github_user or not github_user.access_token:
                host = os.environ.get("DOMAIN")
                oauth_url = build_github_oauth_url(host, app_id, open_id)
                message = ManageFaild(
                    content=f"[请点击绑定 GitHub 账号]({oauth_url})",
                    title="🎉 欢迎使用 GitMaya！",
                )
                bot.send(open_id, message).json()
            repos = (
                db.session.query(Repo)
                .join(
                    CodeApplication,
                    Repo.application_id == CodeApplication.id,
                )
                .join(Team, CodeApplication.team_id == team.id)
                .filter(
                    Team.id == team.id,
                    Repo.status == 0,
                )
                .order_by(
                    Repo.modified.desc(),
                )
                # .limit(20)  # 这里先不限制长度，看看飞书那边展示情况
                .all()
            )
            message = ManageManual(
                org_name=team.name,
                repos=[(repo.id, repo.name) for repo in repos],
                team_id=team.id,
            )
            # 这里不是回复，而是直接创建消息
            return bot.send(open_id, message).json()
    return False


@celery.task()
def send_manage_manual(app_id, message_id, *args, **kwargs):
    bot, application = get_bot_by_application_id(app_id)
    if application:
        team = (
            db.session.query(Team)
            .filter(
                Team.id == application.team_id,
                Team.status == 0,
            )
            .first()
        )
        if team:
            repos = (
                db.session.query(Repo)
                .join(
                    CodeApplication,
                    Repo.application_id == CodeApplication.id,
                )
                .join(Team, CodeApplication.team_id == team.id)
                .filter(
                    Team.id == team.id,
                    Repo.status == 0,
                )
                .order_by(
                    Repo.modified.desc(),
                )
                # .limit(20)  # 这里先不限制长度，看看飞书那边展示情况
                .all()
            )
            message = ManageManual(
                org_name=team.name,
                repos=[(repo.id, repo.name) for repo in repos],
                team_id=team.id,
            )
            return bot.reply(message_id, message).json()
    return False


@celery.task()
def send_manage_new_message(app_id, message_id, *args, **kwargs):
    bot, _ = get_bot_by_application_id(app_id)
    message = ManageNew()
    return bot.reply(message_id, message).json()


@celery.task()
def send_manage_setting_message(app_id, message_id, *args, **kwargs):
    bot, _ = get_bot_by_application_id(app_id)
    message = ManageSetting()
    return bot.reply(message_id, message).json()


@celery.task()
def send_manage_view_message(app_id, message_id, *args, **kwargs):
    bot, application = get_bot_by_application_id(app_id)
    if application:
        team = (
            db.session.query(Team)
            .filter(
                Team.id == application.team_id,
                Team.status == 0,
            )
            .first()
        )
        if team:
            message = ManageView(org_name=team.name)
            return bot.reply(message_id, message).json()
    return False


@celery.task()
def send_detect_repo(
    repo_id, app_id, open_id="", topics: list = [], visibility: str = "private"
):
    """send new repo card message to user.

    Args:
        repo_id: repo.id.
        app_id: IMApplication.app_id.
        open_id: BindUser.open_id.
    """
    repo = (
        db.session.query(Repo)
        .filter(
            Repo.id == repo_id,
        )
        .first()
    )
    if repo:
        bot, application = get_bot_by_application_id(app_id)
        team = (
            db.session.query(Team)
            .filter(
                Team.id == application.team_id,
            )
            .first()
        )
        message = ManageRepoDetect(
            # TODO 这里需要使用team.name + repo_name拼接url
            repo_url=f"https://github.com/{team.name}/{repo.name}",
            repo_name=repo.name,
            repo_description=repo.description,
            repo_topic=topics,
            visibility=visibility,
            homepage=repo.extra.get("homepage", None),
        )
        return bot.send(
            open_id,
            message,
            receive_id_type="open_id",
        ).json()
    return False


@celery.task()
def send_manage_fail_message(
    content, app_id, message_id, data, raw_message, *args, bot=None, **kwargs
):
    """send new repo card message to user.

    Args:
        app_id: IMApplication.app_id.
        message_id: lark message id.
        content: error message
    """
    if not bot:
        bot, _ = get_bot_by_application_id(app_id)
    message = ManageFaild(content=content)
    chat_type = (
        raw_message.get("event", {}).get("message", {}).get("chat_type")
        if isinstance(raw_message, dict)
        else None
    )
    if chat_type == "group" and message_id:
        return bot.reply(message_id, message).json()
    open_id = raw_message["event"]["sender"]["sender_id"].get("open_id", None)
    if open_id:
        return bot.send(open_id, message).json()
    if message_id:
        return bot.reply(message_id, message).json()
    return False


@celery.task()
def send_manage_success_message(
    content, app_id, message_id, data, raw_message, *args, bot=None, **kwargs
):
    """send new repo card message to user.

    Args:
        app_id: IMApplication.app_id.
        message_id: lark message id.
        content: success message
    """
    if not bot:
        bot, _ = get_bot_by_application_id(app_id)
    message = ManageSuccess(content=content)
    chat_type = (
        raw_message.get("event", {}).get("message", {}).get("chat_type")
        if isinstance(raw_message, dict)
        else None
    )
    if chat_type == "group" and message_id:
        return bot.reply(message_id, message).json()
    open_id = raw_message["event"]["sender"]["sender_id"].get("open_id", None)
    if open_id:
        return bot.send(open_id, message).json()
    if message_id:
        return bot.reply(message_id, message).json()
    return False


@celery.task()
def create_chat_group_for_repo(
    repo_url, chat_name, app_id, message_id, *args, **kwargs
):
    """
    user input:
    /match repo_url chat_name

    Args:
        repo_url: repo_url.
        chat_name: chat_name.
        app_id: IMApplication.app_id.
        message_id: lark message id.
    """
    bot, application = get_bot_by_application_id(app_id)
    if not application:
        return send_manage_fail_message(
            "找不到对应的应用", app_id, message_id, *args, bot=bot, **kwargs
        )
    team = (
        db.session.query(Team)
        .filter(
            Team.id == application.team_id,
        )
        .first()
    )
    if not team:
        return send_manage_fail_message(
            "找不到对应的项目", app_id, message_id, *args, bot=bot, **kwargs
        )

    # TODO
    repo_name = repo_url.split("/").pop()
    repo = (
        db.session.query(Repo)
        .join(
            CodeApplication,
            Repo.application_id == CodeApplication.id,
        )
        .filter(
            CodeApplication.team_id == team.id,
            Repo.name == repo_name,
        )
        .first()
    )
    if not repo:
        return send_manage_fail_message(
            "找不到对应的项目", app_id, message_id, *args, bot=bot, **kwargs
        )

    raw_message = args[1] if len(args) > 1 and isinstance(args[1], dict) else {}
    event = raw_message.get("event", {})
    event_message = event.get("message", {})
    chat_type = event_message.get("chat_type")
    chat_id = event_message.get("chat_id", "")
    sender_open_id = event.get("sender", {}).get("sender_id", {}).get("open_id", "")

    # 在群里执行 `/match <repo_url>`：直接把当前群绑定到仓库
    if chat_type == "group" and not chat_name:
        allow_bind = _is_chat_owner_or_manager(bot, chat_id, sender_open_id)
        if not allow_bind:
            return send_manage_fail_message(
                "只有群管理员/群主可以在群里执行 /match 绑定仓库",
                app_id,
                message_id,
                *args,
                bot=bot,
                **kwargs,
            )

        if not chat_id:
            return send_manage_fail_message(
                "无法识别当前群，请稍后重试",
                app_id,
                message_id,
                *args,
                bot=bot,
                **kwargs,
            )

        current_chat_group = (
            db.session.query(ChatGroup)
            .filter(
                ChatGroup.im_application_id == application.id,
                ChatGroup.chat_id == chat_id,
                ChatGroup.status == 0,
            )
            .first()
        )
        if not current_chat_group:
            current_chat_name, current_chat_desc, chat_extra = _get_chat_meta(bot, chat_id)
            current_chat_group = ChatGroup(
                id=ObjID.new_id(),
                im_application_id=application.id,
                chat_id=chat_id,
                name=current_chat_name or "项目群",
                description=current_chat_desc or "",
                extra=chat_extra,
            )
            db.session.add(current_chat_group)
            db.session.flush()

        if repo.chat_group_id != current_chat_group.id:
            db.session.query(Repo).filter(Repo.id == repo.id).update(
                dict(chat_group_id=current_chat_group.id)
            )
            db.session.commit()

        bind_result = send_repo_to_chat_group(repo.id, app_id, chat_id)
        if not isinstance(bind_result, list):
            bind_result = [bind_result]

        content = (
            f"已将当前群「{current_chat_group.name}」绑定到仓库 "
            f"https://github.com/{team.name}/{repo.name}"
        )
        return bind_result + [
            send_manage_success_message(
                content,
                app_id,
                message_id,
                *args,
                bot=bot,
                **kwargs,
            )
        ]

    chat_group = (
        db.session.query(ChatGroup)
        .filter(
            ChatGroup.id == repo.chat_group_id,
            ChatGroup.status == 0,
        )
        .first()
    )
    if chat_group:
        try:
            message = FeishuShareChatMessage(chat_id=chat_group.chat_id)
            raw_message = args[1]
            open_id = raw_message["event"]["sender"]["sender_id"].get("open_id", None)
            bot.send(open_id, message).json()
        except Exception as e:
            logging.error(e)
        return send_manage_fail_message(
            "不允许重复创建项目群", app_id, message_id, *args, bot=bot, **kwargs
        )

    # 先查询当前项目成员列表
    CodeUser = aliased(BindUser)
    IMUser = aliased(BindUser)
    # user_id_list 使用这个项目绑定的人的列表，同时属于当前repo
    user_id_list = [
        openid
        for openid, in db.session.query(IMUser.openid)
        .join(
            TeamMember,
            TeamMember.im_user_id == IMUser.id,
        )
        .join(CodeUser, TeamMember.code_user_id == CodeUser.id)
        .join(
            RepoUser,
            RepoUser.bind_user_id == CodeUser.id,
        )
        .filter(
            TeamMember.team_id == team.id,
            RepoUser.repo_id == repo.id,
        )
    ]
    # 把user_id_list中的每个user_id查User表，获取每个人的名字
    user_name_list = [
        name
        for name, in db.session.query(IMUser.name)
        .filter(
            IMUser.openid.in_(user_id_list),
        )
        .distinct()
    ]
    try:
        chat_id = args[1]["event"]["message"]["chat_id"]
    except Exception as e:
        chat_id = ""

    # 如果有已经存在的项目群，尝试直接绑定这个群，将当前项目人员拉进群
    exists_chat_group = (
        db.session.query(ChatGroup)
        .filter(
            ChatGroup.im_application_id == application.id,
            or_(
                ChatGroup.name == chat_name if chat_name else False,
                # 现在支持在群聊里面使用match，尝试从chat_id获取名字
                ChatGroup.chat_id == chat_id,
            ),
        )
        .first()
    )
    if exists_chat_group:
        db.session.query(Repo).filter(Repo.id == repo.id).update(
            dict(chat_group_id=exists_chat_group.id)
        )
        db.session.commit()
        chat_id = exists_chat_group.chat_id
        chat_group_members_url = f"{bot.host}/open-apis/im/v1/chats/{chat_id}/members"
        result = bot.post(
            chat_group_members_url,
            json={"id_list": user_id_list},
        ).json()
        logging.debug("add members %r to chat_id %r", user_id_list, chat_id)
        invite_message = (
            f"2. 成功拉取「 {'、'.join(user_name_list)} 」进入「{exists_chat_group.name}」群"
            if len(user_name_list) > 0
            else "2. 未获取相关绑定成员, 请检查成员是否绑定"
        )

        content = "\n".join(
            [
                f"1. 成功绑定名为「{chat_name if chat_name else exists_chat_group.name}」的项目群",
                invite_message,
            ]
        )
        # 这里可以再触发一个异步任务给群发卡片，不过为了保存结果，就同步调用
        result = send_repo_to_chat_group(repo.id, app_id, chat_id) + [
            send_manage_success_message(
                content, app_id, message_id, *args, bot=bot, **kwargs
            )
        ]
        return result

    # 持有相同uuid的请求10小时内只可成功创建1个群聊
    chat_group_url = f"{bot.host}/open-apis/im/v1/chats?uuid={repo.id}"
    # TODO 这里是一个可以配置的模板
    name = chat_name or f"{repo.name} 项目群"
    description = f"{repo.description}"
    # TODO 当前先使用发消息的人，后面查找这个项目的所有者...
    try:
        # parser.parse_args(text, bot.app_id, message_id, content, *args, **kwargs)
        owner_id = args[1]["event"]["sender"]["sender_id"]["open_id"]
    except Exception as e:
        logging.error(e)
        # card event
        owner_id = args[0]["open_id"]

    if owner_id not in user_id_list:
        user_id_list += [owner_id]

    result = bot.post(
        chat_group_url,
        json={
            "name": name,
            "description": description,
            "edit_permission": "all_members",  # TODO all_members/only_owner
            "set_bot_manager": True,  # 设置创建群的机器人为管理员
            "owner_id": owner_id,
            "user_id_list": user_id_list,
        },
    ).json()
    chat_id = result.get("data", {}).get("chat_id")
    if not chat_id:
        content = f"创建项目群失败: \n\n{result.get('msg')}"
        return send_manage_fail_message(
            content, app_id, message_id, *args, bot=bot, **kwargs
        )

    chat_group_id = ObjID.new_id()
    chat_group = ChatGroup(
        id=chat_group_id,
        im_application_id=application.id,
        chat_id=chat_id,
        name=name,
        description=description,
        extra=result,
    )
    db.session.add(chat_group)
    # 创建群组之后，更新repo.chat_group_id
    db.session.query(Repo).filter(Repo.id == repo.id).update(
        dict(chat_group_id=chat_group_id)
    )
    db.session.commit()
    """
    创建项目群之后，需要发两条消息：
    1. 给操作的用户发成功的消息
    2. 给群发送repo 卡片消息，并pin
    """
    invite_message = (
        f"2. 成功拉取「 {'、'.join(user_name_list)} 」进入「{name}」群"
        if len(user_name_list) > 0
        else "2. 未获取相关绑定成员, 请检查成员是否绑定"
    )

    content = "\n".join(
        [
            f"1. 成功创建名为「{name}」的新项目群",
            # TODO 这里需要给人发邀请???创建群的时候，可以直接拉群...
            invite_message,
        ]
    )
    # 这里可以再触发一个异步任务给群发卡片，不过为了保存结果，就同步调用
    result = send_repo_to_chat_group(repo.id, app_id, chat_id) + [
        send_manage_success_message(
            content, app_id, message_id, *args, bot=bot, **kwargs
        )
    ]
    return result


@celery.task()
def send_repo_to_chat_group(repo_id, app_id, chat_id=""):
    """send new repo card message to user.

    Args:
        repo_id: repo.id.
        app_id: IMApplication.app_id.
        chat_id: ChatGroup.chat_id.
    """
    repo = (
        db.session.query(Repo)
        .filter(
            Repo.id == repo_id,
        )
        .first()
    )
    if repo:
        bot, application = get_bot_by_application_id(app_id)
        team = (
            db.session.query(Team)
            .filter(
                Team.id == application.team_id,
            )
            .first()
        )
        repo_url = f"https://github.com/{team.name}/{repo.name}"
        message = RepoInfo(
            repo_url=repo_url,
            repo_name=repo.name,
            repo_description=repo.description,
            repo_topic=repo.extra.get("topics", []),
            homepage=repo.extra.get("homepage", None),
            open_issues_count=repo.extra.get("open_issues_count", 0),
            stargazers_count=repo.extra.get("stargazers_count", 0),
            forks_count=repo.extra.get("forks_count", 0),
            visibility="私有仓库" if repo.extra.get("private") else "公开仓库",
            updated=repo.extra.get("updated_at", ""),
        )
        result = bot.send(
            chat_id,
            message,
            receive_id_type="chat_id",
        ).json()
        message_id = result.get("data", {}).get("message_id")
        if message_id:
            # save message_id
            repo.message_id = message_id
            db.session.commit()
            pin_url = f"{bot.host}/open-apis/im/v1/pins"
            pin_result = bot.post(pin_url, json={"message_id": message_id}).json()
            logging.info("debug pin_result %r", pin_result)
            first_message_result = bot.reply(
                message_id,
                # 第一条话题消息，直接放repo_url
                FeishuTextMessage(f'<at user_id="all">所有人</at>\n{repo_url}'),
                reply_in_thread=True,
            ).json()
            logging.info("debug first_message_result %r", first_message_result)

            # 向群内发送 chat manual
            message = ChatManual(
                repo_url=f"https://github.com/{team.name}/{repo.name}",
                repo_name=repo.name,
                actions=[],  # TODO 获取actions
            )

            man_result = bot.send(
                chat_id,
                message,
                receive_id_type="chat_id",
            ).json()
        else:
            logging.error("debug result %r", result)
            return False

        # 一共有3个result需要存到imaction里面
        return [result, pin_result, first_message_result, man_result]
    return False
