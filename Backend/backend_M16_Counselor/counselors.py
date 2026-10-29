"""The people a student can talk to — read from `counselors.json`."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache

from . import config


@dataclass(frozen=True)
class Counselor:
    id: str
    name: str
    relation: str
    voice_id: str
    blurb: str
    manner: str
    greet: str
    signoff: str


@lru_cache(maxsize=1)
def _load() -> tuple[str, dict[str, Counselor]]:
    data = json.loads(config.COUNSELORS_FILE.read_text(encoding="utf-8"))
    people = {c["id"]: Counselor(**c) for c in data["counselors"]}
    if data["default"] not in people:
        raise ValueError(f"counselors.json: the default {data['default']!r} is not a counselor")
    return data["default"], people


def all_counselors() -> list[Counselor]:
    return list(_load()[1].values())


def default_id() -> str:
    return _load()[0]


def get(counselor_id: str | None) -> Counselor:
    """The counselor by id, or the default for an unknown or missing one."""
    default, people = _load()
    return people.get(counselor_id or "", people[default])
