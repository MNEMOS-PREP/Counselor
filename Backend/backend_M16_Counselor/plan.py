"""What to do next, and the one thing a talk asks for. Pure.

Spec §2.3: *exactly one primary action*, and at most two more. Each is a
thing the student can start from the talk itself — a link into a focused
mock (`/mock?focus=<concept>&label=<topic>`, the link M06's notes already use
for "Practise X again") — with how long it takes, so "tonight, fifteen
minutes" is a plan and "work on hashing" is not.

The ask is the commitment the next talk holds them to (spec §2.5: the nudge
"references a commitment *they* made"). It is sized to their own weekly goal,
never to ours: the interviews still to do this week to meet it, at least one.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import quote

from ai_core.timeutil import as_utc

from .casefile import CaseFile, plural

#: How long one practice step takes, as said to the student.
FOCUSED_MINUTES = 15
INTERVIEW_MINUTES = 15
#: A drive this close changes the second step to practising for it.
DRIVE_SOON_DAYS = 30


def actions(case: CaseFile) -> list[dict[str, Any]]:
    """At most three steps, the first the one that matters most."""
    steps: list[dict[str, Any]] = []
    gap = case.fact("gap")
    if case.focus and gap:
        topic = case.focus["topic"]
        steps.append(
            {
                "id": "P1",
                "title": f"Practise {topic} again",
                "why": f"It's the one that didn't hold ({gap.id}).",
                "minutes": FOCUSED_MINUTES,
                "href": _focused(case.focus["concept_id"], topic),
                "facts": [gap.id],
            }
        )
    elif case.held:
        # Nothing needs work: go further where it held (a harder follow-up).
        topic = case.held[0]["topic"]
        held = case.fact("held")
        steps.append(
            {
                "id": "P1",
                "title": f"Go deeper on {topic}",
                "why": "It held - the next one asks harder.",
                "minutes": FOCUSED_MINUTES,
                "href": "/practice",
                "facts": [held.id] if held else [],
            }
        )
    drive = case.fact("drive")
    if case.drive and case.drive["days"] <= DRIVE_SOON_DAYS and drive:
        steps.append(
            {
                "id": f"P{len(steps) + 1}",
                "title": f"An interview in {case.drive['label']}'s format",
                "why": f"{plural(case.drive['days'], 'day')} to go.",
                "minutes": INTERVIEW_MINUTES,
                "href": "/practice",
                "facts": [drive.id],
            }
        )
    held = case.fact("held")
    if case.focus and case.held and held and len(steps) < 3:
        # The gap comes first; where it held, the next one asks harder.
        topic = case.held[0]["topic"]
        steps.append(
            {
                "id": f"P{len(steps) + 1}",
                "title": f"Go deeper on {topic}",
                "why": "It held - the next one asks harder.",
                "minutes": FOCUSED_MINUTES,
                "href": "/practice",
                "facts": [held.id],
            }
        )
    # How many interviews this week is the ask's to say (ask()), not a step's:
    # the same number twice reads as nagging. Only a talk with nothing else
    # to suggest makes it a step.
    rhythm = case.fact("rhythm")
    if rhythm and not steps:
        steps.append(
            {
                "id": "P1",
                "title": "One more interview this week",
                "why": "To keep your own weekly goal."
                if case.weekly_goal
                else "To keep the rhythm.",
                "minutes": INTERVIEW_MINUTES,
                "href": "/practice",
                "facts": [rhythm.id],
            }
        )
    return steps[:3]


def ask(case: CaseFile, now: datetime) -> dict[str, Any]:
    """The one commitment, and the answers on offer."""
    count = max(case.weekly_goal - case.this_week, 1) if case.weekly_goal else 1
    count = min(count, 3)
    by = _next_sunday(as_utc(now).date())
    by_text = f"{by.strftime('%A')} {by.day} {by.strftime('%B')}"
    # What the counselor says back, so the answer is heard (written by rule:
    # an acknowledgement has no facts in it to get wrong).
    day = by.strftime("%A")
    options = [
        {
            "id": "yes",
            "label": f"Yes, {plural(count, 'interview')} by {day}",
            "reply": f"Deal. I'll ask you how it went after {day}.",
        }
    ]
    if count > 1:
        options.append(
            {"id": "one", "label": "Make it one", "reply": "One it is. Make that one count."}
        )
    options.append(
        {
            "id": "not_now",
            "label": "Not this week",
            "reply": "Fair enough. Rest well, and we'll pick it up next week.",
        }
    )
    return {
        "count": count,
        "by": by.isoformat(),
        "text": f"{plural(count, 'more interview')} by {by_text}",
        "options": options,
    }


def _focused(concept_id: str, topic: str) -> str:
    if not concept_id:
        return "/practice"
    return f"/mock?focus={quote(concept_id)}&label={quote(topic)}"


def _next_sunday(today: date) -> date:
    """This week's Sunday, or next week's if today is Sunday already."""
    days = (6 - today.weekday()) % 7 or 7
    return today + timedelta(days=days)
