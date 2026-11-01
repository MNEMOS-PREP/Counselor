"""Tables. Three: what a student chose, the talks they were given, and the
walks through one interview's notes they asked for.

An episode keeps the case file it was written from beside the script, so any
sentence the counselor said can be traced to the fact it stood on — the same
rule as M06's notes: the code decides what is true, the model only says it.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from ai_core.timeutil import utcnow
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class CounselSettings(SQLModel, table=True):
    """One row per student: who talks to them, how often, and how."""

    __tablename__ = "m16_settings"

    candidate_id: str = Field(primary_key=True)
    #: A talk after every N interviews (1, 2 or 3). 1 unless the student says.
    every: int = 1
    #: The counselor the student picked; None until they pick one.
    counselor_id: str | None = None
    #: video · audio · text — how the student wants the talk.
    mode: str = "video"
    #: The student switched the talks off. Settings and history stay.
    paused: bool = False
    updated_at: datetime = Field(default_factory=utcnow)


class Episode(SQLModel, table=True):
    """One talk: written once, from the interviews it covers."""

    __tablename__ = "m16_episode"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    candidate_id: str = Field(index=True)
    counselor_id: str
    #: The interviews this talk is about, newest first.
    sessions: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    #: writing · ready · failed
    status: str = "writing"
    created_at: datetime = Field(default_factory=utcnow)
    ready_at: datetime | None = None
    #: The facts the script was written from (casefile.CaseFile).
    case: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    #: The chapters, each a list of lines that cite their facts.
    script: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    #: At most three things to do, each with how long it takes and a link.
    plan: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    #: The one commitment the talk asks for, and the answers on offer.
    ask: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    #: What the student said to the ask (the option's id), and when.
    answer: str | None = None
    answered_at: datetime | None = None
    #: The furthest chapter heard, and when the talk was heard to the end.
    reached: str | None = None
    watched_at: datetime | None = None
    #: model · template — who wrote the words (the facts are always the code's).
    source: str = "template"
    #: Why it is a template, or why it failed, in a sentence.
    reason: str | None = None


class Walkthrough(SQLModel, table=True):
    """One walk through one interview's notes, question by question — written
    once, when the student asks for it, in the voice of whoever they chose."""

    __tablename__ = "m16_walkthrough"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    candidate_id: str = Field(index=True)
    #: The interview whose notes these are.
    session_id: str = Field(index=True)
    counselor_id: str
    #: writing · ready · failed
    status: str = "writing"
    #: While writing: what it is on, in a few words ("Question 2 of 5").
    stage: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    #: The writer's last sign of life. A walk takes minutes to write, so
    #: "still writing" is judged by this, never by when it was made.
    beat_at: datetime = Field(default_factory=utcnow)
    ready_at: datetime | None = None
    #: The facts the words were written from (notes.Walk).
    case: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    #: The chapters — intro, q1…qN, close — each a list of lines citing facts.
    script: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    #: Chapter key -> what the screen shows beside the face: the notes as
    #: M06 wrote them, never the model's words.
    cards: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    #: Whether every explanation in the notes was written when this was.
    notes_complete: bool = True
    reached: str | None = None
    watched_at: datetime | None = None
    #: model · mixed · template — who wrote the words (the facts are always the code's).
    source: str = "template"
    #: The chapters said from the template, because the model's lines were cut or never came.
    templated: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    reason: str | None = None
