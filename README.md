# opti_api

Django REST API for cable drum allocation and optimization.

## Current Scope

- Accept optimized allocation jobs through an API
- Run the optimization asynchronously with Celery
- Return job status and results

## Local Setup

1. Create a virtual environment
2. Install dependencies with `venv/bin/python -m pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in local values
4. Run Django locally
5. Run Redis and Celery for async tasks

### Baseline Runner

Use the management command below to baseline the current optimizer against the sample workbook before deeper refactors:

```bash
venv/bin/python manage.py run_optimizer_baseline "sample_input.xlsx"
```

Optional snapshot output:

```bash
venv/bin/python manage.py run_optimizer_baseline "sample_input.xlsx" --output artifacts/baseline/sample_input.json
```

### Local Endpoint Modes

- VS Code / Django debug mode: `http://127.0.0.1:8080/api/optimizer/submit/`
- VS Code / Django debug mode with host-app prefix: `http://127.0.0.1:8080/optimizer_api/api/optimizer/submit/`
- Docker + Nginx mode: `http://127.0.0.1:8080/api/optimizer/submit/`

For local debug, this repo should bind to `127.0.0.1:8080` so it matches `host_app` without requiring changes there.
Both `/api/optimizer/...` and `/optimizer_api/api/optimizer/...` are accepted.

## Docker Setup

- `optimizerAPI_docker-compose.yml` runs Django, Celery, Redis, and Nginx
- `deploy.sh` boots the local Docker stack

## Repo Hygiene

- Local-only files are ignored via `.gitignore`
- Docker build context is trimmed via `.dockerignore`
- Line endings are normalized with `.gitattributes`
- Editor defaults are defined in `.editorconfig`

## Collaboration

- Use `COLLABORATION.md` for shared notes between Codex and AG
