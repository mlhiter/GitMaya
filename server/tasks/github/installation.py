from app import app
from celery_app import celery
from model.team import upsert_team_and_code_application_by_installation
from tasks.github.github import pull_github_repo
from utils.github.bot import BaseGitHubApp


def _extract_installation_id(data: dict | None) -> str | None:
    installation = (data or {}).get("installation") or {}
    installation_id = installation.get("id")
    if installation_id is None:
        return None
    return str(installation_id)


def _extract_sender_github_user_id(data: dict | None) -> str | None:
    sender = (data or {}).get("sender") or {}
    sender_id = sender.get("id")
    if sender_id is None:
        return None
    return str(sender_id)


def _sync_installation(installation_id: str, sender_github_user_id: str | None) -> list:
    github_app = BaseGitHubApp(installation_id)
    app_info = github_app.get_installation_info()
    if not app_info:
        app.logger.error(
            "Failed to get installation info from GitHub App API: installation_id=%s",
            installation_id,
        )
        return []

    account = app_info.get("account") or {}
    if account.get("type") == "User":
        app.logger.info(
            "Skip installation sync for user account: installation_id=%s",
            installation_id,
        )
        return []

    team, code_application = upsert_team_and_code_application_by_installation(
        app_info=app_info,
        installation_id=installation_id,
        installer_github_user_id=sender_github_user_id,
    )

    task = pull_github_repo.delay(
        org_name=team.name,
        installation_id=installation_id,
        application_id=code_application.id,
        team_id=team.id,
    )

    return [task.id]


@celery.task()
def on_installation(event_dict: dict | None) -> list:
    action = ((event_dict or {}).get("action") or "").lower()
    installation_id = _extract_installation_id(event_dict)
    if not installation_id:
        app.logger.warning("Skip installation webhook, no installation.id")
        return []

    match action:
        case "created" | "new_permissions_accepted" | "unsuspend":
            return _sync_installation(
                installation_id=installation_id,
                sender_github_user_id=_extract_sender_github_user_id(event_dict),
            )
        case "deleted" | "suspend":
            app.logger.info(
                "Skip installation webhook action: action=%s installation_id=%s",
                action,
                installation_id,
            )
            return []
        case _:
            app.logger.info(
                "Unhandled installation action: action=%s installation_id=%s",
                action,
                installation_id,
            )
            return []


@celery.task()
def on_installation_repositories(event_dict: dict | None) -> list:
    installation_id = _extract_installation_id(event_dict)
    if not installation_id:
        app.logger.warning("Skip installation_repositories webhook, no installation.id")
        return []

    return _sync_installation(
        installation_id=installation_id,
        sender_github_user_id=_extract_sender_github_user_id(event_dict),
    )
