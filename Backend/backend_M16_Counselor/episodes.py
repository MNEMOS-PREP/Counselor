"""When a talk is due, and writing one.

**Due.** A talk comes after every N finished interviews — 1, 2 or 3, the
student's choice, 1 unless they say. The interviews counted are the ones that
ended after the last talk was made (or all of them, before the first), so a
student back after a week with three interviews gets ONE talk about the three,
not three talks. A talk that is ready and not yet heard is the one shown; no
second is made on top of it.

**Writing.** Made in the background the moment it is due — while the student
reads their notes — so by the time they press play it is there: the facts
(casefile), the steps and the ask (plan), then the words (script). Every
upstream is optional: without M04 the talk has no goal, drive or trend in it;
without M06 there is nothing to talk about, and no talk is made.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from ai_core.timeutil import as_utc, utcnow
from sqlmodel import Session, desc, select

from . import casefile, config, counselors, plan, script
from .llm import LLM
from .models import CounselSettings, Episode
from .upstreams import Reader

log = logging.getLogger("uvicorn.error")


def settings_for(db: Session, candidate_id: str) -> CounselSettings:
    found = db.get(CounselSettings, candidate_id)
    if found is not None:
        return found
    fresh = CounselSettings(candidate_id=candidate_id)
    db.add(fresh)
    db.commit()
    db.refresh(fresh)
    return fresh


def latest(db: Session, candidate_id: str) -> Episode | None:
    return db.exec(
        select(Episode)
        .where(Episode.candidate_id == candidate_id)
        .order_by(desc(Episode.created_at))
    ).first()


def waiting(db: Session, candidate_id: str) -> Episode | None:
    """A talk made and not yet heard to the end — the one to show."""
    last = latest(db, candidate_id)
    if last is not None and last.status in ("writing", "ready") and last.watched_at is None:
        return last
    return None


def new_interviews(history: list[dict[str, Any]], since: datetime | None) -> list[dict[str, Any]]:
    """Interviews that ended after `since`, newest first."""
    ended = [h for h in history if h.get("status") == "ended" and h.get("ended_at")]
    fresh = [
        h for h in ended if since is None or casefile.parse_time(h["ended_at"]) > as_utc(since)
    ]
    return sorted(fresh, key=lambda h: str(h["ended_at"]), reverse=True)


def check(db: Session, reader: Reader, candidate_id: str) -> dict[str, Any]:
    """What the student should see now: a talk to watch, or how many
    interviews until the next one. Makes the talk when it is due."""
    settings = settings_for(db, candidate_id)
    shown = waiting(db, candidate_id)
    if shown is not None:
        return {"due": True, "episode": shown, "until_next": 0, "reason": None}
    if settings.paused:
        return {"due": False, "episode": None, "until_next": None, "reason": "paused"}
    history = reader.interviews(candidate_id)
    if history is None:
        return {"due": False, "episode": None, "until_next": None, "reason": "M06 is not answering"}
    # Counted from the last talk that was made; a failed one gave nothing, so
    # its interviews are still owed one.
    last = db.exec(
        select(Episode)
        .where(Episode.candidate_id == candidate_id, Episode.status != "failed")
        .order_by(desc(Episode.created_at))
    ).first()
    fresh = new_interviews(history, last.created_at if last else None)
    if len(fresh) < settings.every:
        return {
            "due": False,
            "episode": None,
            "until_next": settings.every - len(fresh),
            "reason": None,
        }
    episode = Episode(
        candidate_id=candidate_id,
        counselor_id=counselors.get(settings.counselor_id).id,
        sessions=[str(h["id"]) for h in fresh],
    )
    db.add(episode)
    db.commit()
    db.refresh(episode)
    return {"due": True, "episode": episode, "until_next": 0, "reason": None}


def write(
    db: Session, reader: Reader, llm: LLM, episode_id: uuid.UUID, now: datetime | None = None
) -> Episode | None:
    """Write a talk that is due. Never raises: a failure is a status and a reason."""
    episode = db.get(Episode, episode_id)
    if episode is None or episode.status != "writing":
        return episode
    now = now or utcnow()
    try:
        _write(db, reader, llm, episode, now)
    except Exception as exc:  # noqa: BLE001 - a broken talk must say so, not hang
        log.exception("M16: writing talk %s failed", episode.id)
        episode.status, episode.reason = "failed", f"{type(exc).__name__}: {exc}"[:300]
    db.add(episode)
    db.commit()
    db.refresh(episode)
    return episode


def _write(db: Session, reader: Reader, llm: LLM, episode: Episode, now: datetime) -> None:
    cid = episode.candidate_id
    history = reader.interviews(cid) or []
    by_id = {str(h["id"]): h for h in history}
    covered = [by_id[s] for s in episode.sessions if s in by_id]
    reports = {s: r for s in episode.sessions if (r := reader.report(cid, s)) is not None}
    if not reports:
        episode.status, episode.reason = "failed", "no report could be read for these interviews"
        return
    previous = db.exec(
        select(Episode)
        .where(Episode.candidate_id == cid, Episode.id != episode.id, Episode.status == "ready")
        .order_by(desc(Episode.created_at))
    ).first()
    counselor = counselors.get(episode.counselor_id)
    case = casefile.build(
        now=now,
        covered=covered,
        reports=reports,
        history=history,
        profile=reader.profile(cid),
        mastery=reader.mastery(cid),
        trajectory=reader.trajectory(cid),
        previous=previous.model_dump(mode="json") if previous else None,
        counselor_name=counselor.name,
    )
    steps = plan.actions(case)
    ask = plan.ask(case, now)
    words, source, reason = script.write(llm, case, counselor, steps, ask)
    episode.case = case.as_dict()
    episode.plan = steps
    episode.ask = ask
    episode.script = words
    episode.source, episode.reason = source, reason
    episode.status, episode.ready_at = "ready", utcnow()


def view(episode: Episode) -> dict[str, Any]:
    """What a student's browser is given: the talk, never the case file's
    internals beyond the facts the lines cite."""
    counselor = counselors.get(episode.counselor_id)
    chapters = episode.script.get("chapters", []) if episode.script else []
    words = sum(len(line["text"].split()) for c in chapters for line in c["lines"])
    return {
        "id": str(episode.id),
        "candidate_id": episode.candidate_id,
        "status": episode.status,
        "counselor": {
            "id": counselor.id,
            "name": counselor.name,
            "relation": counselor.relation,
            "voice_id": counselor.voice_id,
        },
        "sessions": episode.sessions,
        "created_at": episode.created_at,
        "ready_at": episode.ready_at,
        "chapters": chapters,
        "plan": [
            {k: s[k] for k in ("id", "title", "why", "minutes", "href")} for s in episode.plan
        ],
        "ask": episode.ask,
        "answer": episode.answer,
        "reached": episode.reached,
        "watched_at": episode.watched_at,
        # About 150 words a minute, spoken.
        "seconds": round(words / 2.5),
        "source": episode.source,
        "reason": episode.reason if episode.status == "failed" else None,
    }


def settings_view(settings: CounselSettings) -> dict[str, Any]:
    return {
        "candidate_id": settings.candidate_id,
        "every": settings.every,
        "counselor_id": settings.counselor_id,
        "chosen": settings.counselor_id is not None,
        "mode": settings.mode,
        "paused": settings.paused,
        "every_choices": list(config.EVERY_CHOICES),
    }
