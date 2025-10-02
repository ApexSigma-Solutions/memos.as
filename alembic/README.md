This folder contains Alembic migrations for the memos.as service.

Usage:
- Ensure `alembic` is installed in the project's environment (we add it to pyproject.toml).
- Set DATABASE_URL env var (or rely on docker-compose provided DATABASE_URL).
- From the repo root run (inside container or using poetry):
  poetry run alembic -c services/memos.as/alembic.ini upgrade head

The env.py imports `app.services.postgres_client.Base` to obtain the metadata for autogenerate.
