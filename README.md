# opti_api

Django REST API for cable drum allocation and optimization.

## Current Scope

- Accept optimized allocation jobs through an API
- Run the optimization asynchronously with Celery
- Return job status and results

## Local Setup

1. Create a virtual environment
2. Install dependencies from `requirements.txt`
3. Copy `.env.example` to `.env` and fill in local values
4. Run Django locally
5. Run Redis and Celery for async tasks

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

