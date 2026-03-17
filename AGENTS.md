# Repository Guidelines

## Project Structure & Module Organization
- `server/` contains the Python backend.
- `server/server.py` is the Flask entrypoint; `server/app.py` configures Flask, CORS, and SQLAlchemy.
- `server/routes/` defines HTTP endpoints (`github.py`, `lark.py`, `team.py`, `user.py`).
- `server/model/` holds SQLAlchemy models and DB bootstrap CLI (`schema.py`).
- `server/tasks/` and `server/celery_app.py` contain Celery workers and async task logic.
- `server/utils/` contains integration helpers (GitHub/Lark/auth/redis utilities).
- `deploy/` contains Docker, Compose, Nginx proxy, and `.env.example`.
- `website/` is a Git submodule (`GitMaya-Frontend`); initialize when needed.

## Build, Test, and Development Commands
- `pdm install` installs Python dependencies (preferred workflow).
- `eval $(pdm venv activate)` activates the PDM virtual environment.
- `pip install -r requirements.txt` is the fallback dependency path.
- `pre-commit run --all-files` runs formatting and quality hooks (CI baseline).
- `cd server && gunicorn --worker-class=gevent --workers 1 --bind 0.0.0.0:8888 -t 600 --keep-alive 60 --log-level=info server:app` runs API locally.
- `cd server && celery -A tasks.celery worker -l INFO -c 2` starts worker processes.
- `make build` / `make build-proxy` build Docker images; `make startup` boots Compose and initializes DB.

## Coding Style & Naming Conventions
- Follow Python 3.10+ conventions with 4-space indentation.
- Use `snake_case` for modules/functions/variables, `PascalCase` for classes, and concise route/task names by domain.
- Keep imports ordered and formatting compliant with `isort` + `black` (configured in `.pre-commit-config.yaml`).

## Testing Guidelines
- There is no committed `tests/` suite yet; CI currently enforces pre-commit checks.
- For new features, add focused tests under `tests/` using `test_<behavior>.py` naming.
- For backend changes, include at least one route/task-level validation path and document manual verification steps in PRs.

## Commit & Pull Request Guidelines
- Recent history favors short, imperative commit subjects like `fix import`, `hotfix os import`, `update readme`.
- Keep commits single-purpose and easy to review.
- PRs should include: problem statement, change summary, verification steps, and related issue/PR links.
- Call out config/schema impacts explicitly and attach screenshots/log snippets when behavior is user-facing.

## Security & Configuration Tips
- Never commit secrets; use `deploy/.env.example` as the template for local `.env`.
- Validate GitHub App, Redis, MySQL, and Celery env vars before running services.
- Never execute database write operations unless the user explicitly asks for a database modification.
