"""The database: SQLite locally (WAL, so a talk being written never blocks a
read), Postgres through `M16_DATABASE_URL` like every module."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from . import config


def make_engine(url: str | None = None):
    url = url or config.DATABASE_URL
    sqlite = url.startswith("sqlite")
    engine = create_engine(url, connect_args={"check_same_thread": False} if sqlite else {})
    if sqlite:

        @event.listens_for(engine, "connect")
        def _pragmas(dbapi, _record):  # noqa: ANN001
            cursor = dbapi.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()

    return engine


engine = make_engine()


def init(target=None) -> None:
    """Create the tables. Idempotent."""
    from . import models  # noqa: F401 - registers the tables

    SQLModel.metadata.create_all(target or engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
