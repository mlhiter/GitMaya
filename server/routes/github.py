import json
import os
from base64 import urlsafe_b64decode, urlsafe_b64encode
from urllib.parse import urlencode

from app import app, db
from flask import Blueprint, jsonify, make_response, redirect, request, session
from model.team import create_code_application, create_team
from model.schema import BindUser, IMApplication, ObjID, TeamMember
from tasks.github import pull_github_repo
from tasks.github.issue import on_issue, on_issue_comment
from tasks.github.organization import on_organization
from tasks.github.pull_request import on_pull_request
from tasks.github.push import on_push
from tasks.github.repo import on_fork, on_repository, on_star
from utils.auth import authenticated
from utils.github.application import verify_github_signature
from utils.github.bot import BaseGitHubApp
from utils.user import register

bp = Blueprint("github", __name__, url_prefix="/api/github")


def _encode_oauth_state(payload: dict) -> str:
    content = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return urlsafe_b64encode(content).decode("utf-8").rstrip("=")


def _decode_oauth_state(state: str) -> dict:
    padding = "=" * ((4 - len(state) % 4) % 4)
    content = urlsafe_b64decode((state + padding).encode("utf-8")).decode("utf-8")
    payload = json.loads(content)
    return payload if isinstance(payload, dict) else {}


def _send_lark_oauth_success(
    app_id: str, open_id: str, content: str = "GitHub 账号绑定成功，请回到飞书继续操作。"
) -> None:
    from tasks.lark.base import get_bot_by_application_id
    from utils.lark.manage_success import ManageSuccess

    bot, application = get_bot_by_application_id(app_id)
    if not bot or not application:
        app.logger.warning(
            f"Skip lark oauth success notify, app_id not found: app_id={app_id}"
        )
        return

    message = ManageSuccess(content=content)
    bot.send(open_id, message, receive_id_type="open_id").json()


def _send_lark_oauth_failed(app_id: str, open_id: str, content: str) -> None:
    from tasks.lark.base import get_bot_by_application_id
    from utils.lark.manage_fail import ManageFaild

    bot, application = get_bot_by_application_id(app_id)
    if not bot or not application:
        app.logger.warning(
            f"Skip lark oauth failure notify, app_id not found: app_id={app_id}"
        )
        return

    message = ManageFaild(content=content, title="🔐 GitHub 绑定失败")
    bot.send(open_id, message, receive_id_type="open_id").json()


def _bind_lark_user_to_team_member(app_id: str, open_id: str, user_id: str) -> bool:
    """Bind lark open_id to current github user inside team_member.

    This makes assignee mapping available for issue/pr cards and action callbacks.
    """
    if not app_id or not open_id or not user_id:
        return False

    application = (
        db.session.query(IMApplication)
        .filter(
            IMApplication.app_id == app_id,
            IMApplication.status.in_([0, 1]),
        )
        .first()
    )
    if not application:
        app.logger.warning(
            "Skip team_member auto-bind, IMApplication not found: app_id=%s", app_id
        )
        return False

    github_bind_user = (
        db.session.query(BindUser)
        .filter(
            BindUser.user_id == user_id,
            BindUser.platform == "github",
            BindUser.status == 0,
        )
        .first()
    )
    if not github_bind_user:
        app.logger.warning(
            "Skip team_member auto-bind, github bind user not found: user_id=%s", user_id
        )
        return False

    im_bind_user = (
        db.session.query(BindUser)
        .filter(
            BindUser.openid == open_id,
            BindUser.platform == "lark",
            BindUser.status == 0,
        )
        .first()
    )

    # Ensure an IM bind user exists even when contact sync was not executed yet.
    if not im_bind_user:
        im_bind_user = BindUser(
            id=ObjID.new_id(),
            user_id=user_id,
            platform="lark",
            application_id=application.id,
            openid=open_id,
            name=open_id,
            extra={"source": "oauth_auto_bind"},
        )
        db.session.add(im_bind_user)
        db.session.flush()
    elif not im_bind_user.application_id:
        im_bind_user.application_id = application.id

    try:
        team_member = (
            db.session.query(TeamMember)
            .filter(
                TeamMember.team_id == application.team_id,
                TeamMember.code_user_id == github_bind_user.id,
                TeamMember.status == 0,
            )
            .first()
        )

        duplicate_im_binding = (
            db.session.query(TeamMember.id)
            .filter(
                TeamMember.team_id == application.team_id,
                TeamMember.im_user_id == im_bind_user.id,
                TeamMember.status == 0,
            )
            .limit(1)
            .scalar()
        )

        if team_member:
            if duplicate_im_binding and duplicate_im_binding != team_member.id:
                app.logger.warning(
                    "Skip team_member auto-bind, im_user already bound to another member: team_id=%s open_id=%s",
                    application.team_id,
                    open_id,
                )
                db.session.rollback()
                return False
            if team_member.im_user_id != im_bind_user.id:
                team_member.im_user_id = im_bind_user.id
        else:
            if duplicate_im_binding:
                app.logger.warning(
                    "Skip team_member auto-bind, im_user already bound: team_id=%s open_id=%s",
                    application.team_id,
                    open_id,
                )
                db.session.rollback()
                return False
            db.session.add(
                TeamMember(
                    id=ObjID.new_id(),
                    team_id=application.team_id,
                    code_user_id=github_bind_user.id,
                    im_user_id=im_bind_user.id,
                )
            )

        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return True


@bp.route("/install", methods=["GET"])
@authenticated
def github_install():
    """Install GitHub App.

    Redirect to GitHub App installation page.
    """
    installation_id = request.args.get("installation_id", None)
    if installation_id is None:
        return redirect(
            f"https://github.com/apps/{(os.environ.get('GITHUB_APP_NAME')).replace(' ', '-')}/installations/new"
        )

    github_app = BaseGitHubApp(installation_id)

    try:
        app_info = github_app.get_installation_info()

        if app_info is None:
            app.logger.error("Failed to get installation info.")
            raise Exception("Failed to get installation info.")

        # 判断安装者的身份是用户还是组织
        app_type = app_info["account"]["type"]
        if app_type == "User":
            app.logger.error("User is not allowed to install.")
            raise Exception("User is not allowed to install.")

        team = create_team(app_info, contact_id=session.get("contact_id"))
        code_application = create_code_application(team.id, installation_id)

        # if app_info == "organization":
        # 在后台任务中拉取仓库
        task = pull_github_repo.delay(
            org_name=app_info["account"]["login"],
            installation_id=installation_id,
            application_id=code_application.id,
            team_id=team.id,
        )

        message = dict(
            status=True,
            event="installation",
            data=app_info,
            team_id=team.id,
            task_id=task.id,
            app_type=app_type,
        )

    except Exception as e:
        # 返回错误信息
        app.logger.error(e)
        app_info = str(e)
        message = dict(
            status=False,
            event="installation",
            data=app_info,
            team_id=None,
            task_id=None,
            app_type=app_type,
        )

    return make_response(
        """
<script>
try {
  window.opener.postMessage("""
        + json.dumps(message)
        + """, '*')
  setTimeout(() => window.close(), 3000)
} catch(e) {
  console.error(e)
  location.replace('/api/account')
}
</script>
                                     """,
        {"Content-Type": "text/html"},
    )


@bp.route("/oauth", methods=["GET"])
def github_register():
    """GitHub OAuth register.

    If not `code`, redirect to GitHub OAuth page.
    If `code`, register by code.
    """
    code = request.args.get("code", None)

    if code is None:
        params = {"client_id": os.environ.get("GITHUB_CLIENT_ID")}
        app_id = request.args.get("app_id")
        open_id = request.args.get("open_id")
        if app_id and open_id:
            params["state"] = _encode_oauth_state(
                {
                    "app_id": app_id,
                    "open_id": open_id,
                }
            )
        return redirect(
            f"https://github.com/login/oauth/authorize?{urlencode(params)}"
        )

    # 通过 code 注册；如果 user 已经存在，则一样会返回 user_id
    user_id = register(code)
    state = request.args.get("state")
    if user_id:
        # 保存用户注册状态
        session["user_id"] = user_id
        # 默认是会话级别的session，关闭浏览器直接就失效了
        session.permanent = True

        if state:
            try:
                payload = _decode_oauth_state(state)
                app_id = payload.get("app_id")
                open_id = payload.get("open_id")
                if app_id and open_id:
                    bind_ok = _bind_lark_user_to_team_member(app_id, open_id, user_id)
                    success_text = (
                        "GitHub 账号绑定成功，并已关联飞书成员。请回到群里继续操作。"
                        if bind_ok
                        else "GitHub 账号绑定成功，但团队成员映射未完成。请联系团队管理员在成员页绑定后重试。"
                    )
                    _send_lark_oauth_success(app_id, open_id, success_text)
            except Exception as e:
                app.logger.warning(f"Failed to send lark oauth success message: {e}")
    elif state:
        # 来自飞书绑定流程，注册失败时给出明确回执，避免用户无感知失败
        try:
            payload = _decode_oauth_state(state)
            app_id = payload.get("app_id")
            open_id = payload.get("open_id")
            if app_id and open_id:
                _send_lark_oauth_failed(
                    app_id,
                    open_id,
                    "GitHub 登录失败或授权码已过期，请在飞书里重新执行 /bind 并重试。",
                )
        except Exception as e:
            app.logger.warning(f"Failed to send lark oauth failure message: {e}")

    return make_response(
        """
<script>
try {
  window.opener.postMessage("""
        + json.dumps(
            dict(
                event="oauth",
                data={
                    "user_id": user_id,
                    "ok": bool(user_id),
                    "error": None if user_id else "oauth_failed",
                },
            )
        )
        + """, '*')
  setTimeout(() => window.close(), 3000)
} catch(e) {
  console.error(e)
  """
        + (
            "location.replace('/api/account')"
            if user_id
            else "document.body.innerText='GitHub 登录失败，请返回飞书执行 /bind 后重试。'"
        )
        + """
}
</script>
                                     """,
        {"Content-Type": "text/html"},
    )


@bp.route("/hook", methods=["POST"])
@verify_github_signature(os.environ.get("GITHUB_WEBHOOK_SECRET"))
def github_hook():
    """Receive GitHub webhook."""

    x_github_event = request.headers.get("x-github-event", None).lower()

    app.logger.info(x_github_event)

    match x_github_event:
        case "repository":
            task = on_repository.delay(request.json)
            return jsonify({"code": 0, "message": "ok", "task_id": task.id})
        case "issues":
            task = on_issue.delay(request.json)
            return jsonify({"code": 0, "message": "ok", "task_id": task.id})
        case "issue_comment":
            task = on_issue_comment.delay(request.json)
            return jsonify({"code": 0, "message": "ok", "task_id": task.id})
        case "pull_request":
            task = on_pull_request.delay(request.json)
            return jsonify({"code": 0, "message": "ok", "task_id": task.id})
        case "organization":
            task = on_organization.delay(request.json)
            return jsonify({"code": 0, "message": "ok", "task_id": task.id})
        case "push":
            task = on_push.delay(request.json)
            return jsonify({"code": 0, "message": "ok", "task_id": task.id})
        case "star":
            task = on_star.delay(request.json)
            return jsonify({"code": 0, "message": "ok", "task_id": task.id})
        case "fork":
            task = on_fork.delay(request.json)
            return jsonify({"code": 0, "message": "ok", "task_id": task.id})
        case _:
            app.logger.info(f"Unhandled GitHub webhook event: {x_github_event}")
            return jsonify({"code": -1, "message": "Unhandled GitHub webhook event."})

    return jsonify({"code": 0, "message": "ok"})


app.register_blueprint(bp)
