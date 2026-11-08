import os
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def database_url() -> str:
    url = os.environ.get("DATABASE_URL", "sqlite:///./pol-local.db")
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url.removeprefix("postgres://")
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


@lru_cache(maxsize=1)
def engine():
    url = database_url()
    return create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False} if url.startswith("sqlite:") else {},
    )


def session():
    # Schema is created by Alembic, never implicitly during a public request.
    with Session(engine()) as db:
        yield db
