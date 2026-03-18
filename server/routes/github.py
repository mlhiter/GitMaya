import json
import os
from base64 import urlsafe_b64decode, urlsafe_b64encode
from urllib.parse import urlencode

from app import app
from flask import Blueprint, jsonify, make_response, redirect, request, session
from model.team import create_code_application, create_team
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


def _send_lark_oauth_success(app_id: str, open_id: str) -> None:
    from tasks.lark.base import get_bot_by_application_id
    from utils.lark.manage_success import ManageSuccess

    bot, application = get_bot_by_application_id(app_id)
    if not bot or not application:
        app.logger.warning(
            f"Skip lark oauth success notify, app_id not found: app_id={app_id}"
        )
        return

    message = ManageSuccess(content="GitHub 账号绑定成功，请回到飞书继续操作。")
    bot.send(open_id, message, receive_id_type="open_id").json()


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
    # if user_id is None:
    #     return jsonify({"message": "Failed to register."}), 500

    # 保存用户注册状态
    if user_id:
        session["user_id"] = user_id
        # 默认是会话级别的session，关闭浏览器直接就失效了
        session.permanent = True
        state = request.args.get("state")
        if state:
            try:
                payload = _decode_oauth_state(state)
                app_id = payload.get("app_id")
                open_id = payload.get("open_id")
                if app_id and open_id:
                    _send_lark_oauth_success(app_id, open_id)
            except Exception as e:
                app.logger.warning(f"Failed to send lark oauth success message: {e}")

    return make_response(
        """
<script>
try {
  window.opener.postMessage("""
        + json.dumps(dict(event="oauth", data={"user_id": user_id}))
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
