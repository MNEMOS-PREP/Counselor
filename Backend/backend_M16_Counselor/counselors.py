"""The mentors a student can talk to — read from `counselors.json`."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache

from . import config


@dataclass(frozen=True)
class Counselor:
    id: str
    name: str
    #: What they are to the student — "mentor". The prompt says it.
    relation: str
    #: Who they are, shown under their name ("Engineer, placed three years ago").
    role: str
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


def named(text: str, name: str) -> str:
    """A greeting or sign-off with the student's name in it — or, when the
    name is not known, without it: never "You've got this, there."."""
    if name:
        return text.format(name=name)
    said = re.sub(r",\s*\{name\}", "", text)
    said = re.sub(r"^\{name\}[,.]?\s*", "", said)
    said = said.replace(" {name}", "").replace("{name}", "")
    return said[:1].upper() + said[1:]


def address(name: str) -> str:
    """How a script writer is told to address the student."""
    if name:
        return f"Call the student {name}."
    return 'Their name is not known: use no name at all (never "there", never "student").'
