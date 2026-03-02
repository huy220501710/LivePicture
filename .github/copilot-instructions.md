<!-- .github/copilot-instructions.md - guidance for AI coding agents working on this repo -->

# Quick Repo Orientation for AI Coding Agents

This file captures the essential, discoverable patterns and commands an AI code agent needs to be immediately productive in this repository.

- Project: Vue 3 frontend + FastAPI backend (REST + GraphQL) with Celery, Redis, RabbitMQ and multiple DB examples (Postgres, MySQL, MongoDB).
- App entrypoint: `app.main` — FastAPI app object is created there and mounted under `root_path="/api"`.

## Big-picture architecture

- Backend: `app/` contains a modular FastAPI app. REST routers live in `app/api/rest/*` and each resource usually exposes an `APIRouter` named `router` (e.g. `app/api/rest/boards/routes.py`).
- GraphQL: `app/api/graphql/*` (Strawberry-based) — included in `app.main` via `graphql_app`.
- Websockets & SSE: Websockets registered from `app/websockets` and SSE endpoints live in `app/api/rest/sse`.
- Async tasks: `app/celery` contains Celery app and tasks (`celery_app.celery_instance` and `app.celery.tasks`). There are two Celery configs in the repo (`celeryconfig-redis` and `celeryconfig-rabbitmq`).
- Data layers: `app/mysql`, `app/postgresql`, `app/mongodb` — examples for different storage backends. Primary DB used in production is PostgreSQL (see `app/config.py`).
- Caching & infra: Redis used for cache, limiter, revoke tokens, and optionally Celery broker/results. RabbitMQ also used for pub/sub and Celery (project supports both patterns).

## Key source locations (examples)

- FastAPI app: `app/main.py` (lifespan initializers, router includes, middleware, Sentry, Prometheus instrumentation).
- Routers: `app/api/rest/<resource>/routes.py` (example: `app/api/rest/pins/routes.py`).
- GraphQL: `app/api/graphql/*` (see `app/api/graphql/users/router.py`).
- Websockets: `app/websockets/*` and `app/websockets/chat.py` (registered via `register_websocket(app)`).
- Config: `app/config.py` — pydantic-settings backed by `.env`; many runtime URLs are properties (e.g. `POSTGRES_URL_ASYNC`, `REDIS_URL_CACHE`, `RABBITMQ_URL_BROKER`).
- Celery: `app/celery/celery_app.py`, tasks in `app/celery/tasks.py`, celery configs `app/celery/celeryconfig-redis.py` and `app/celery/celeryconfig-rabbitmq.py`.
- Services/Repos: `app/repositories/*` and `app/services/*` (follow service → repository pattern).

## Patterns & conventions an agent should follow

- Router convention: new REST resources should expose an `APIRouter` named `router` and be included in `app/main.py` via `app.include_router(...)`. If not included, endpoints won't be accessible.
- Lifespan/init/close: `app.main.lifespan` handles init/cleanup of Redis, Mongo, HTTPX, RabbitMQ, and DB connections. Use the same init/close helpers (e.g. `init_redis_cache`, `close_redis_cache`) when adding new resources.
- Settings: Use `app.config.settings` for configuration values; these map to `.env` variables. Use the existing `Settings` properties (e.g. `settings.POSTGRES_URL_ASYNC`) rather than constructing connection strings manually.
- Async-first: handlers, DB access, and I/O are async. Prefer `async` functions and `await` when interacting with infra.
- Background work: use Celery for heavy or long-running tasks. Tasks are defined in `app/celery/tasks.py` and scheduled in `celery_app.py` (beat schedule).

## How to run (common developer commands)

- Run the FastAPI app locally (requires env vars):
  `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
  - Note: `root_path="/api"` means the app serves under `/api` (OpenAPI available at `/api/openapi.json`).

- Run with Docker Compose (recommended for full infra):
  `docker-compose up -d` (the repo contains multiple compose files; `docker-compose.yml` is the basic one)

- Run Celery worker (uses `celery_instance`):
  `celery -A app.celery.celery_app.celery_instance worker --loglevel=info`

- Run Celery beat (scheduled tasks):
  `celery -A app.celery.celery_app.celery_instance beat --loglevel=info`

- Tests: `pytest -q` (there are unit, integration, and end-to-end tests under `tests/`).

- Lint & format checks (CI uses Ruff):
  `ruff check .` and `ruff format --check .`

## Environment & secrets

- Configuration is read from `.env` via `pydantic-settings` (`app/config.py`). Key env var prefixes and examples:
  - `DEV_MODE` — toggles dev vs production init flow in `app/main.py`.
  - `POSTGRES_*`, `TEST_POSTGRES_*` — production and test DB settings.
  - `REDIS_*`, `RABBITMQ_*`, `MYSQL_*`, `MONGO_*` — service credentials.
  - `JWT_*`, `YANDEX_STORAGE_*`, `GOOGLE_OAUTH2_*` — feature flags/integration creds.

When writing or running code, reference `app.config.settings.<NAME>` to obtain values.

## Tests, CI & special workflows

- CI: repository uses GitLab CI (`.gitlab-ci.yml`) that builds images (`Dockerfile-fastapi`, `Dockerfile-vuejs`), runs `ruff` checks, runs migrations (`alembic upgrade head`), and executes `pytest` inside a container.
- DB migrations: Alembic config and migrations are under `migrations/`. Use `alembic upgrade head` from project root when necessary.

## Integration points to be careful about

- Sentry: initialized in `app.main` — don't remove Sentry middleware blindly. Use `settings.SENTRY_DSN`.
- Prometheus: `prometheus_fastapi_instrumentator` is used in `app.main` — instrumentation is auto-exposed.
- Static files: `app.static` is mounted at `/static` (assets, templates). Frontend builds may depend on this.
- Frontend: `vuejs/` contains the Vue app. In production, frontend is served by Nginx; local dev uses the Vue dev server.

## Helpful small examples

- Add a new REST router: create `app/api/rest/myresource/routes.py` with an `APIRouter()` named `router`, then add `app.include_router(myrouter)` to `app/main.py`.
- Use settings example:
  ```py
  from app.config import settings
  db_url = settings.POSTGRES_URL_ASYNC
  ```
- Celery task call example (enqueue from code):
  ```py
  from app.celery.tasks import some_task
  some_task.delay(payload)
  ```

---
If anything above is unclear or you want me to expand a particular area (examples of router structure, typical request/response shapes, or test-running with a test DB), tell me which part and I will iterate.
