"""A walk through one interview's notes: starting one, writing it, showing it.

**Asked for, not due.** A talk comes after every N interviews; a walk comes
when the student presses "go through my notes" — on the notes page, or at the
end of a talk. One per interview per mentor: asking again opens the same walk,
and picking another mentor makes theirs.

**Writing waits for the notes.** M06 writes each answer's explanation after
the interview (`writeups: pending` until it has), and a walk without them
would have nothing to explain. So the writer checks every WRITEUPS_POLL_S, for
at most WRITEUPS_WAIT_S, then writes from what is there and says so. Then one
chapter at a time (walk_script.py). It takes minutes, and the student was
told it might; `stage` says what it is on, and `beat_at` that it is alive —
a walk whose writer went quiet (a restart) is written again, never one that
is merely slow.
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from ai_core.timeutil import as_utc, utcnow
from sqlmodel import Session, desc, select

from . import config, counselors, episodes, notes, walk_script
from .llm import LLM
from .models import Walkthrough
from .upstreams import Reader

log = logging.getLogger("uvicorn.error")

#: No sign of life from the writer for this long: it is gone (a restart).
#: Longer than any one step can take — a model call's timeout and a
#: rate-limit wait (walk_script.RATE_WAIT_MAX) back to back.
SILENT = timedelta(minutes=4)
#: M06's statuses for an interview that is over — ended, or cut short; both
#: have notes (M06 report: "it exists for every session that has one").
FINAL = ("ended", "aborted")


def start(db: Session, candidate_id: str, session_id: str) -> Walkthrough:
    """The walk through these notes in the chosen mentor's voice: the one
    already made (or being made), else a new one to write."""
    settings = episodes.settings_for(db, candidate_id)
    counselor = counselors.get(settings.counselor_id)
    found = db.exec(
        select(Walkthrough)
        .where(
            Walkthrough.candidate_id == candidate_id,
            Walkthrough.session_id == session_id,
            Walkthrough.counselor_id == counselor.id,
            Walkthrough.status != "failed",
        )
        .order_by(desc(Walkthrough.created_at))
    ).first()
    if found is not None:
        return found
    walk = Walkthrough(candidate_id=candidate_id, session_id=session_id, counselor_id=counselor.id)
    db.add(walk)
    db.commit()
    db.refresh(walk)
    return walk


def lost(walk: Walkthrough, now: datetime | None = None) -> bool:
    """Being written, and the writer has gone quiet."""
    return walk.status == "writing" and (now or utcnow()) - as_utc(walk.beat_at) > SILENT


def write(
    db: Session,
    reader: Reader,
    llm: LLM,
    walk_id: uuid.UUID,
    *,
    now: datetime | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> Walkthrough | None:
    """Write a walk. Never raises: a failure is a status and a reason."""
    walk = db.get(Walkthrough, walk_id)
    if walk is None or walk.status != "writing":
        return walk
    try:
        _write(db, reader, llm, walk, now or utcnow(), sleep)
    except Exception as exc:  # noqa: BLE001 - a broken walk must say so, not hang
        log.exception("M16: writing walk %s failed", walk.id)
        walk.status, walk.reason = "failed", f"{type(exc).__name__}: {exc}"[:300]
    walk.stage = None
    db.add(walk)
    db.commit()
    db.refresh(walk)
    return walk


def _beat(db: Session, walk: Walkthrough, stage: str) -> None:
    walk.stage, walk.beat_at = stage, utcnow()
    db.add(walk)
    db.commit()


def _write(
    db: Session,
    reader: Reader,
    llm: LLM,
    walk: Walkthrough,
    now: datetime,
    sleep: Callable[[float], None],
) -> None:
    cid = walk.candidate_id
    _beat(db, walk, "Reading your notes")
    report = reader.report(cid, walk.session_id)
    waited = 0.0
    while report is not None and report.get("writeups") == "pending":
        if waited >= config.WRITEUPS_WAIT_S:
            break
        _beat(db, walk, "Waiting for your notes to finish")
        sleep(config.WRITEUPS_POLL_S)
        waited += config.WRITEUPS_POLL_S
        report = reader.report(cid, walk.session_id) or report
    if report is None:
        walk.status, walk.reason = "failed", "these notes could not be read"
        return
    if report.get("status") not in FINAL:
        walk.status, walk.reason = "failed", "this interview has not ended yet"
        return

    profile = reader.profile(cid) or {}
    mastery = reader.mastery(cid) or {}
    names = {
        m["concept_id"]: m["name"]
        for m in mastery.get("measured", [])
        if m.get("concept_id") and m.get("name")
    }
    name = (profile.get("display_name") or "").strip()
    built = notes.build(report, now=now, name=name, names=names)
    if not built.cards["intro"]["questions"]:
        walk.status, walk.reason = "failed", "nothing was asked in this interview"
        return
    counselor = counselors.get(walk.counselor_id)
    words, source, reason, templated = walk_script.write(
        llm, built, counselor, beat=lambda stage: _beat(db, walk, stage), sleep=sleep
    )
    walk.case = built.as_dict()
    walk.cards = built.cards
    walk.script = words
    walk.notes_complete = built.complete
    walk.source, walk.reason, walk.templated = source, reason, templated
    walk.status, walk.ready_at = "ready", utcnow()


def view(walk: Walkthrough) -> dict[str, Any]:
    """What a student's browser is given: the walk, the cards beside it, and
    for each line which part of the card it is about — never the facts."""
    counselor = counselors.get(walk.counselor_id)
    kinds = {f["id"]: f["kind"] for f in (walk.case or {}).get("facts", [])}
    chapters = []
    for chapter in (walk.script or {}).get("chapters", []):
        lines = []
        for line in chapter["lines"]:
            sections = {
                notes.SECTION[kinds[c]] for c in line["cites"] if kinds.get(c) in notes.SECTION
            }
            # A line on what was missing usually quotes the answer too: it
            # points at the most specific part it stands on.
            points = next((s for s in notes.POINTING if s in sections), None)
            lines.append({**line, "points_at": points})
        chapters.append({**chapter, "lines": lines})
    words = sum(len(line["text"].split()) for c in chapters for line in c["lines"])
    return {
        "id": str(walk.id),
        "candidate_id": walk.candidate_id,
        "session_id": walk.session_id,
        "status": walk.status,
        "stage": walk.stage if walk.status == "writing" else None,
        # "Question 2 (3 of 5)" as numbers, for the progress bar while it writes.
        "progress": _progress(walk.stage) if walk.status == "writing" else None,
        "counselor": {
            "id": counselor.id,
            "name": counselor.name,
            "relation": counselor.relation,
            "role": counselor.role,
            "voice_id": counselor.voice_id,
        },
        "created_at": walk.created_at,
        "ready_at": walk.ready_at,
        "chapters": chapters,
        "cards": walk.cards or {},
        "notes_complete": walk.notes_complete,
        "reached": walk.reached,
        "watched_at": walk.watched_at,
        # About 150 words a minute, spoken.
        "seconds": round(words / 2.5),
        "source": walk.source,
        "templated": walk.templated,
        "reason": walk.reason if walk.status == "failed" else None,
    }


def _progress(stage: str | None) -> dict[str, int] | None:
    found = re.search(r"\((\d+) of (\d+)\)", stage or "")
    return {"at": int(found.group(1)), "of": int(found.group(2))} if found else None
