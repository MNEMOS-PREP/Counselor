"""M16 routes — the talk after the report card.

Every route sits behind `enforce_access` on the ROUTER (access.py), so none can
be written without it. The noun is `counsel`: Platform_Shell routes one origin
by the first segment after /v1, and `candidates` is M04's.

    GET  /v1/counsel/counselors                        the four people
    GET  /v1/counsel/candidates/{cid}/settings         who, how often, how
    PUT  /v1/counsel/candidates/{cid}/settings
    POST /v1/counsel/candidates/{cid}/check            a talk to watch, or how
                                                       many interviews to the next
    GET  /v1/counsel/candidates/{cid}/episodes         every talk, newest first
    GET  /v1/counsel/episodes/{id}                     one talk
    POST /v1/counsel/episodes/{id}/progress            how far it was heard
    POST /v1/counsel/episodes/{id}/answer              the answer to the ask
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Annotated, Literal

from ai_core.timeutil import as_utc, utcnow
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, desc, select

from . import config, counselors, db, episodes
from .access import enforce_access
from .llm import get_llm
from .models import Episode
from .script import KEYS
from .upstreams import Reader, Upstreams

router = APIRouter(prefix="/v1/counsel", tags=["counsel"], dependencies=[Depends(enforce_access)])
SessionDep = Annotated[Session, Depends(db.get_session)]

#: A talk still "writing" after this long lost its writer (a restart): write it again.
STALE_WRITING = timedelta(seconds=90)

_reader: Reader | None = None


def get_reader() -> Reader:
    global _reader
    if _reader is None:
        _reader = Upstreams()
    return _reader


def set_reader(reader: Reader | None) -> None:
    """Replace what talks read from. For tests, and for nothing else."""
    global _reader
    _reader = reader


def _write_later(episode_id: uuid.UUID) -> None:
    with Session(db.engine) as session:
        episodes.write(session, get_reader(), get_llm(), episode_id)


def _resume_if_lost(episode: Episode, tasks: BackgroundTasks) -> None:
    if episode.status == "writing" and utcnow() - as_utc(episode.created_at) > STALE_WRITING:
        tasks.add_task(_write_later, episode.id)


def _episode(session: Session, episode_id: uuid.UUID) -> Episode:
    found = session.get(Episode, episode_id)
    if found is None:
        raise HTTPException(status_code=404, detail="No such talk.")
    return found


# ── who, and how ─────────────────────────────────────────────────────────────


@router.get("/counselors")
def list_counselors() -> list[dict]:
    """The people a student can talk to — every face AI-generated, labelled so."""
    default = counselors.default_id()
    return [
        {
            "id": c.id,
            "name": c.name,
            "relation": c.relation,
            "blurb": c.blurb,
            "voice_id": c.voice_id,
            "default": c.id == default,
        }
        for c in counselors.all_counselors()
    ]


class SettingsIn(BaseModel):
    every: int | None = Field(
        default=None, description="A talk after every N interviews: 1, 2 or 3."
    )
    counselor_id: str | None = None
    mode: Literal["video", "audio", "text"] | None = None
    paused: bool | None = None


@router.get("/candidates/{candidate_id}/settings")
def get_settings(candidate_id: str, session: SessionDep) -> dict:
    return episodes.settings_view(episodes.settings_for(session, candidate_id))


@router.put("/candidates/{candidate_id}/settings")
def put_settings(
    candidate_id: str, body: SettingsIn, session: SessionDep, tasks: BackgroundTasks
) -> dict:
    settings = episodes.settings_for(session, candidate_id)
    rewrite: uuid.UUID | None = None
    if body.every is not None:
        if body.every not in config.EVERY_CHOICES:
            raise HTTPException(
                status_code=422, detail="A talk comes after every 1, 2 or 3 interviews."
            )
        settings.every = body.every
    if body.counselor_id is not None:
        if body.counselor_id not in {c.id for c in counselors.all_counselors()}:
            raise HTTPException(status_code=422, detail="No such counselor.")
        settings.counselor_id = body.counselor_id
        # A talk not yet heard is said by whoever the student just picked.
        shown = episodes.waiting(session, candidate_id)
        if shown is not None and shown.reached is None and shown.counselor_id != body.counselor_id:
            shown.counselor_id = body.counselor_id
            if shown.status == "ready":
                shown.status = "writing"  # their words, in the new person's manner
            rewrite = shown.id
            session.add(shown)
    if body.mode is not None:
        settings.mode = body.mode
    if body.paused is not None:
        settings.paused = body.paused
    settings.updated_at = utcnow()
    session.add(settings)
    session.commit()
    session.refresh(settings)
    if rewrite is not None:
        tasks.add_task(_write_later, rewrite)
    return episodes.settings_view(settings)


# ── the talk ─────────────────────────────────────────────────────────────────


@router.post("/candidates/{candidate_id}/check")
def check(candidate_id: str, session: SessionDep, tasks: BackgroundTasks) -> dict:
    """Called when a student finishes an interview and when Today opens."""
    got = episodes.check(session, get_reader(), candidate_id)
    episode = got["episode"]
    if episode is not None and episode.status == "writing":
        if episode.created_at and utcnow() - as_utc(episode.created_at) < timedelta(seconds=2):
            tasks.add_task(_write_later, episode.id)  # just made: write it now
        else:
            _resume_if_lost(episode, tasks)
    return {
        "due": got["due"],
        "until_next": got["until_next"],
        "reason": got["reason"],
        "episode": episodes.view(episode) if episode is not None else None,
    }


@router.get("/candidates/{candidate_id}/episodes")
def list_episodes(candidate_id: str, session: SessionDep) -> list[dict]:
    rows = session.exec(
        select(Episode)
        .where(Episode.candidate_id == candidate_id, Episode.status != "failed")
        .order_by(desc(Episode.created_at))
        .limit(30)
    ).all()
    return [episodes.view(e) for e in rows]


@router.get("/episodes/{episode_id}")
def get_episode(episode_id: uuid.UUID, session: SessionDep, tasks: BackgroundTasks) -> dict:
    episode = _episode(session, episode_id)
    _resume_if_lost(episode, tasks)
    return episodes.view(episode)


class ProgressIn(BaseModel):
    reached: str
    finished: bool = False


@router.post("/episodes/{episode_id}/progress")
def progress(episode_id: uuid.UUID, body: ProgressIn, session: SessionDep) -> dict:
    episode = _episode(session, episode_id)
    if body.reached not in KEYS:
        raise HTTPException(status_code=422, detail="No such chapter.")
    if episode.reached is None or KEYS.index(body.reached) > KEYS.index(episode.reached):
        episode.reached = body.reached
    if body.finished and episode.watched_at is None:
        episode.watched_at = utcnow()
    session.add(episode)
    session.commit()
    session.refresh(episode)
    return episodes.view(episode)


class AnswerIn(BaseModel):
    option: str


@router.post("/episodes/{episode_id}/answer")
def answer(episode_id: uuid.UUID, body: AnswerIn, session: SessionDep) -> dict:
    episode = _episode(session, episode_id)
    offered = {o["id"] for o in (episode.ask or {}).get("options", [])}
    if body.option not in offered:
        raise HTTPException(status_code=422, detail="That isn't one of the answers on offer.")
    episode.answer, episode.answered_at = body.option, utcnow()
    session.add(episode)
    session.commit()
    session.refresh(episode)
    return episodes.view(episode)
