"""A fresh database per test run, and a fake of everything M16 reads.

The fake serves a real M06 report (`fixtures/m06_report.json`, from a live
practice interview on 2026-10-29: a strong warm-up, a hash-map answer that
broke at the follow-up, a stable-sort answer that held) — the producer's own
shape, never an invented one.
"""

from __future__ import annotations

import json
import os
import pathlib
import tempfile
from datetime import UTC, datetime, timedelta
from typing import Any

_TMP = tempfile.mkdtemp(prefix="m16-tests-")
os.environ["M16_DATABASE_URL"] = f"sqlite:///{pathlib.Path(_TMP, 'test.db').as_posix()}"

import pytest  # noqa: E402

from backend_M16_Counselor import db  # noqa: E402

FIXTURES = pathlib.Path(__file__).with_name("fixtures")
REPORT = json.loads((FIXTURES / "m06_report.json").read_text(encoding="utf-8"))
SESSION = REPORT["session_id"]
NOW = datetime(2026, 10, 29, 14, 0, tzinfo=UTC)


def student(candidate_id: str) -> dict[str, str]:
    return {"X-Role": "student", "X-Candidate-Id": candidate_id}


def interview(sid: str, ended: datetime, status: str = "ended") -> dict[str, Any]:
    return {
        "id": sid,
        "kind": "mock",
        "mode": "practice",
        "status": status,
        "requested_minutes": 15,
        "ended_at": ended.isoformat(),
    }


class FakeReader:
    """M06 and M04 as the tests need them; `None` for a module that is down."""

    def __init__(self, history: list[dict] | None = None, *, m04: bool = True) -> None:
        self.history = (
            history if history is not None else [interview(SESSION, NOW - timedelta(minutes=30))]
        )
        self.m04 = m04

    def interviews(self, candidate_id: str):
        return self.history

    def report(self, candidate_id: str, session_id: str):
        return (
            {**REPORT, "session_id": session_id}
            if any(h["id"] == session_id for h in self.history)
            else None
        )

    def profile(self, candidate_id: str):
        if not self.m04:
            return None
        return {
            "display_name": "Riya",
            "weekly_goal": 3,
            "drives": [
                {"label": "Amazon", "date": "2026-11-19", "company_id": "x", "drive_id": None}
            ],
        }

    def mastery(self, candidate_id: str):
        if not self.m04:
            return None
        return {
            "measured": [
                {"concept_id": "concept:hashing", "name": "Hashing"},
                {"concept_id": "concept:sorting", "name": "Sorting"},
                {"concept_id": "concept:thinking_aloud", "name": "Thinking Aloud"},
            ]
        }

    def trajectory(self, candidate_id: str):
        return {"series": []} if self.m04 else None


@pytest.fixture(autouse=True)
def fresh_db():
    from sqlmodel import SQLModel

    SQLModel.metadata.drop_all(db.engine)
    db.init()
    yield
