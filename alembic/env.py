from __future__ import with_statement
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add project path so imports work when Alembic runs from repo root
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# Import the application's metadata (SQLAlchemy Base)
try:
    from app.services.postgres_client import Base  # noqa: E402
except Exception:
    raise

target_metadata = Base.metadata


def run_migrations_offline():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        # Fallback to neutral SQLite URL for development/testing
        db_url = "sqlite:///./alembic.db"
        # Alternatively, raise an error if DATABASE_URL is required:
        # raise ValueError("DATABASE_URL environment variable is required for migrations")

    # Convert postgresql:// to postgresql+psycopg2:// if present
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    configuration = config.get_section(config.config_ini_section)
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        # Fallback to neutral SQLite URL for development/testing
        db_url = "sqlite:///./alembic.db"
        # Alternatively, raise an error if DATABASE_URL is required:
        # raise ValueError("DATABASE_URL environment variable is required for migrations")

    # Convert postgresql:// to postgresql+psycopg2:// if present
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    configuration["sqlalchemy.url"] = db_url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
