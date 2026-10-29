"""Who is asking — on `ai_core.guard`, declared once on the ROUTER.

A talk is about one student's interviews, their words quoted back to them.
Ways a route here names a student:

    /counsel/candidates/{candidate_id}/…   the path — the shared guard
    /counsel/episodes/{episode_id}/…       a talk, which belongs to a student:
                                           resolved below, then `may_see` asked

Upstream calls forward the student's identity (`upstreams.py`), so M06 and M04
decide again, by their own rule, what M16 may read.
"""

from __future__ import annotations

import uuid

from ai_core.guard import candidate_guard
from ai_core.identity import Principal
from fastapi import Depends, Request
from sqlmodel import Session

from .db import get_session
from .models import Episode


def episode_owner(db: Session, episode_id: str) -> str | None:
    try:
        found = db.get(Episode, uuid.UUID(str(episode_id)))
    except ValueError:
        return None
    return found.candidate_id if found else None


def enforce_access(request: Request, db: Session = Depends(get_session)) -> Principal | None:
    """`candidate_guard`, with talk ids resolved to their student."""
    return candidate_guard({"episode_id": lambda eid: episode_owner(db, eid)})(request)


__all__ = ["enforce_access", "episode_owner"]
