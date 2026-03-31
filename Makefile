.PHONY: build build-proxy push push-gitmaya push-proxy startup check-dev-env check-api-port dev dev-api dev-worker dev-web

VENV ?= .venv
BACKEND_DIR ?= server
FRONTEND_DIR ?= website
REDIS_CONTAINER ?= gitmaya-redis
REDIS_PORT ?= 6379
API_BIND_HOST ?= 0.0.0.0
API_PORT ?= 8888

GUNICORN_ARGS ?= --worker-class=gevent --workers 1 --bind $(API_BIND_HOST):$(API_PORT) -t 600 --keep-alive 60 --log-level=info server:app
CELERY_ARGS ?= -A tasks.celery worker -l INFO -c 2

build:
	@echo "Building..."
	docker build -t connectai/gitmaya -f deploy/Dockerfile .
	@echo "Done."

build-proxy:
	@echo "Building proxy..."
	git submodule update --init && docker build -t connectai/gitmaya-proxy -f deploy/Dockerfile.proxy .
	@echo "Done."

push: push-gitmaya push-proxy

push-gitmaya:
	@echo "Push Image..."
	docker push connectai/gitmaya
	@echo "Done."

push-proxy:
	@echo "Push Image..."
	docker push connectai/gitmaya-proxy
	@echo "Done."

startup:
	@echo "Deploy..."
	[ -f deploy/.env ] || cp deploy/.env.example deploy/.env
	cd deploy && docker-compose up -d
	@echo "Waiting Mysql Server..."
	sleep 3
	@echo "Init Database..."
	cd deploy && docker-compose exec gitmaya flask --app model.schema:app create
	@echo "Done."

check-dev-env:
	@test -x $(VENV)/bin/celery || (echo "Missing $(VENV)/bin/celery. Run: pdm install"; exit 1)
	@test -x $(VENV)/bin/gunicorn || (echo "Missing $(VENV)/bin/gunicorn. Run: pdm install"; exit 1)
	@command -v pnpm >/dev/null 2>&1 || (echo "Missing pnpm. Install pnpm first."; exit 1)
	@test -d $(FRONTEND_DIR) || (echo "Missing $(FRONTEND_DIR) directory."; exit 1)

check-api-port:
	@if lsof -nP -iTCP:$(API_PORT) -sTCP:LISTEN >/dev/null 2>&1; then \
		echo "Port $(API_PORT) is already in use."; \
		lsof -nP -iTCP:$(API_PORT) -sTCP:LISTEN; \
		echo "Use a different port: make dev API_PORT=8890"; \
		exit 1; \
	fi

dev-worker:
	cd $(BACKEND_DIR) && ../$(VENV)/bin/celery $(CELERY_ARGS)

dev-api:
	cd $(BACKEND_DIR) && ../$(VENV)/bin/gunicorn $(GUNICORN_ARGS)

dev-web:
	cd $(FRONTEND_DIR) && pnpm dev

dev: check-dev-env check-api-port
	@command -v docker >/dev/null 2>&1 || (echo "Missing docker. Start Redis manually at 127.0.0.1:$(REDIS_PORT)."; exit 1)
	@docker start $(REDIS_CONTAINER) >/dev/null 2>&1 || docker run -d --name $(REDIS_CONTAINER) -p $(REDIS_PORT):6379 redis:alpine >/dev/null
	@echo "Redis is ready at 127.0.0.1:$(REDIS_PORT)"
	@echo "Starting local dev stack: celery + gunicorn + frontend"
	@(cd $(BACKEND_DIR) && ../$(VENV)/bin/celery $(CELERY_ARGS)) & celery_pid=$$!; \
	(cd $(BACKEND_DIR) && ../$(VENV)/bin/gunicorn $(GUNICORN_ARGS)) & api_pid=$$!; \
	(cd $(FRONTEND_DIR) && pnpm dev) & web_pid=$$!; \
	trap 'echo ""; echo "Stopping local dev stack..."; kill $$celery_pid $$api_pid $$web_pid 2>/dev/null || true' INT TERM EXIT; \
	wait $$celery_pid $$api_pid $$web_pid
