# opti_api

Django REST API for cable drum allocation and optimization.

## Purpose

This service receives sanitized cable and drum inputs, runs the current DP-based allocation engine, and returns allocation reports to the calling `host_app`.

## Current Architecture

The active API path is:

1. request payload -> Celery task
2. input normalization and validation
3. allocation scheduling
4. report building
5. API response polling

Current core modules:

- `optimizer/core/input_normalizer.py`
- `optimizer/core/dp_engine.py`
- `optimizer/core/report_builder.py`
- `optimizer/core/cable_optimizer.py`

Maintenance rule:
New optimizer features should be added through the cleaned API path above.
Do not add new feature work into the legacy `class ds` / old `drumAllocator` compatibility code inside `optimizer/core/cable_optimizer.py`.

## Local Development

1. Create or activate the virtual environment.
2. Install dependencies with `venv/bin/python -m pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and fill in local values.
4. Run Django locally on `127.0.0.1:8080`.
5. For local async behavior, use the current project settings. For deeper async testing, run Redis and Celery separately.

Important:
Use `venv/bin/python -m pip`, not `venv/bin/pip`, because `venv/bin/pip` may point to a stale virtualenv path in this repo.

## Local Endpoint Modes

- VS Code / Django debug mode: `http://127.0.0.1:8080/api/optimizer/submit/`
- VS Code / Django debug mode with host-app prefix: `http://127.0.0.1:8080/optimizer_api/api/optimizer/submit/`
- Docker + Nginx mode: `http://127.0.0.1:8080/api/optimizer/submit/`

For local debug, this repo should bind to `127.0.0.1:8080` so it matches `host_app` without requiring changes there.
Both `/api/optimizer/...` and `/optimizer_api/api/optimizer/...` are accepted.

## Verification Commands

Run the Django checks:

```bash
venv/bin/python manage.py check
```

Run the optimizer test suite:

```bash
venv/bin/python manage.py test optimizer -v 2 --noinput
```

Run the workbook baseline:

```bash
venv/bin/python manage.py run_optimizer_baseline sample_input.xlsx
```

Optional snapshot output:

```bash
venv/bin/python manage.py run_optimizer_baseline sample_input.xlsx --output artifacts/baseline/sample_input.json
```

## Docker Setup

- `optimizerAPI_docker-compose.yml` runs Django, Celery, Redis, and Nginx
- `deploy.sh` boots the local Docker stack

## Maintenance Notes

- `COLLABORATION.md` is the shared working note between Codex and AG.
- `TODO/to.md` tracks the next hygiene, platform, and feature-prep tasks.
- Minimal GitHub Actions CI now lives in `.github/workflows/ci.yml`.
- Local-only files are ignored via `.gitignore`.
- Docker build context is trimmed via `.dockerignore`.
- Line endings are normalized with `.gitattributes`.
- Editor defaults are defined in `.editorconfig`.
