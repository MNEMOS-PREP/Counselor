"""The case file: everything a talk may say, decided by code. Pure.

Spec §6.2: *the diagnosis is computed, not generated.* A counselor that is
handed a report and asked to "give feedback" writes the paragraph every
student has already read from every chatbot. So the model is never shown a
report. It is shown facts — each one plain sentence, numbered, with the
student's own words where there are some — and every line it writes must cite
the facts it says (script.py cuts a line that does not).

What is a fact here, and where it comes from:

    name      what to call the student                    M04 profile
    session   each interview the talk covers               M06 history + report
    best      the answer that held up best, quoted        M06 report
    held      topics that held                            M06 report summary
    gap       the one thing to work on, quoted            M06 report (its own focus)
    fix       the idea behind it                          M06 write-up / strong answer
    again     a question asked before, then against now   M06 report `last_time`
    rhythm    interviews this week against the goal       M06 history + M04 goal
    away      a long gap before this interview            M06 history
    drive     the next drive and how far it is            M04 profile
    moved     topics whose estimate rose since last time  M04 trajectory
    promise   what they said yes to last talk, and did    the last episode + history
    first     this is the first talk                      M16 itself

Nothing here judges an answer: M06 and M13 already did. This file only picks
what is worth saying out of what they decided.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from ai_core.timeutil import as_utc

#: Statuses M06's report gives a question that held, and that need work —
#: worst first, so the one to work on is the clearest gap.
HELD = ("correct",)
NEEDS_WORK = ("incorrect", "partial", "unanswered")
#: How long a quote may be, in words, before it is cut at a word.
QUOTE_WORDS = 22
#: A gap before an interview worth naming, in days.
AWAY_DAYS = 5
#: How far ahead a drive is worth bringing up.
DRIVE_HORIZON_DAYS = 60

MODE_WORDS = {
    "practice": "practice",
    "mock": "mock",
    "real_drive": "real-drive",
    "final_boss": "Final Boss",
}


@dataclass
class Fact:
    id: str
    kind: str
    #: The fact as one sentence, in words a person could say.
    text: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class CaseFile:
    name: str
    facts: list[Fact]
    #: The one topic to work on: {"concept_id", "topic"}, or None.
    focus: dict[str, str] | None = None
    #: Interviews in the last seven days, and the weekly goal (0 = none set).
    this_week: int = 0
    weekly_goal: int = 0
    #: The next drive within the horizon: {"label", "date", "days"}, or None.
    drive: dict[str, Any] | None = None
    #: Topics that held, for a "go further" step when nothing needs work.
    held: list[dict[str, str]] = field(default_factory=list)

    def fact(self, kind: str) -> Fact | None:
        return next((f for f in self.facts if f.kind == kind), None)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> CaseFile:
        facts = [Fact(**f) for f in data.get("facts", [])]
        return CaseFile(**{**data, "facts": facts})


# ── words ─────────────────────────────────────────────────────────────────────


def quote(text: str, words: int = QUOTE_WORDS) -> str:
    """The student's words, cut at a word if long. Never rephrased."""
    said = re.sub(r"\s+", " ", (text or "").strip()).strip('"“”')
    parts = said.split(" ")
    if len(parts) <= words:
        return said
    return " ".join(parts[:words]).rstrip(",;:") + "…"


def short_question(text: str, words: int = 14) -> str:
    """A question, cut down to what it is about — the panel's lead-in dropped."""
    q = re.sub(r"\s+", " ", (text or "").strip())
    # "Thanks, Meera. … Next up: DSA. Why is …?" -> "Why is …?"
    sentences = re.split(r"(?<=[.!?])\s+", q)
    asked = next(
        (s for s in reversed(sentences) if s.endswith("?")), sentences[-1] if sentences else q
    )
    return quote(asked, words)


def topic_name(concept_id: str | None, names: dict[str, str]) -> str:
    if not concept_id:
        return ""
    if concept_id in names:
        return names[concept_id]
    return concept_id.split(":", 1)[-1].replace("_", " ")


def when(at: datetime | None, today: date) -> str:
    if at is None:
        return "recently"
    day = as_utc(at).date()
    if day == today:
        return "today"
    if day == today - timedelta(days=1):
        return "yesterday"
    return f"on {day.day} {day.strftime('%B')}"


def parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return as_utc(datetime.fromisoformat(str(value).replace("Z", "+00:00")))
    except ValueError:
        return None


def plural(n: int, one: str, many: str | None = None) -> str:
    return f"{n} {one if n == 1 else (many or one + 's')}"


# ── the case ──────────────────────────────────────────────────────────────────


class _Facts:
    def __init__(self) -> None:
        self.items: list[Fact] = []

    def add(self, kind: str, text: str, **data: Any) -> Fact:
        fact = Fact(id=f"F{len(self.items) + 1}", kind=kind, text=text, data=data)
        self.items.append(fact)
        return fact


def build(
    *,
    now: datetime,
    covered: list[dict[str, Any]],
    reports: dict[str, dict[str, Any]],
    history: list[dict[str, Any]],
    profile: dict[str, Any] | None,
    mastery: dict[str, Any] | None,
    trajectory: dict[str, Any] | None,
    previous: dict[str, Any] | None,
    counselor_name: str,
) -> CaseFile:
    """The facts for one talk.

    `covered` are the interviews this talk is about (M06 summaries, newest
    first) and `reports` their reports by id; `history` is every interview
    the student has had; `previous` is the last talk (models.Episode as a
    dict) or None.
    """
    today = as_utc(now).date()
    facts = _Facts()
    profile = profile or {}
    names = {
        m["concept_id"]: m["name"]
        for m in (mastery or {}).get("measured", [])
        if m.get("concept_id") and m.get("name")
    }

    name = (profile.get("display_name") or "").strip() or "there"
    facts.add("name", f"The student is called {name}.", name=name)

    if previous is None:
        facts.add("first", f"This is the first talk the student has had with {counselor_name}.")

    # Each interview the talk covers.
    questions: list[tuple[str, dict[str, Any]]] = []
    for item in covered:
        sid = str(item.get("id"))
        report = reports.get(sid) or {}
        qs = [
            q for q in report.get("questions", []) if q.get("status") not in (None, "not_reached")
        ]
        questions += [(sid, q) for q in qs]
        ended = parse_time(item.get("ended_at"))
        used = report.get("minutes_used")
        planned = report.get("minutes_planned") or item.get("requested_minutes")
        mode = MODE_WORDS.get(str(item.get("mode") or report.get("mode") or ""), "practice")
        minutes = f" in {round(used)} minutes" if isinstance(used, int | float) else ""
        plan_note = f" ({planned} planned)" if planned and isinstance(used, int | float) else ""
        facts.add(
            "session",
            f"{when(ended, today).capitalize()}, a {mode} interview: "
            f"{plural(len(qs), 'question')}{minutes}{plan_note}.",
            session_id=sid,
            questions=len(qs),
            mode=mode,
        )

    # The best answer: it held, it went deepest, and it was scored if any was.
    held = [(sid, q) for sid, q in questions if q.get("status") in HELD]
    held.sort(
        key=lambda p: (bool(p[1].get("scored")), p[1].get("depth_reached") or 0), reverse=True
    )
    if held:
        _, q = held[0]
        said = _their_words(q)
        deeper = " through the follow-up" if (q.get("depth_reached") or 0) >= 1 else ""
        topic = topic_name(q.get("concept_id"), names)
        text = f'On "{short_question(q.get("question", ""))}", the answer held up{deeper}.'
        if said:
            text += f' They said: "{quote(said)}"'
        facts.add("best", text, topic=topic, quote=quote(said) if said else "")

    held_topics = _unique(topic_name(q.get("concept_id"), names) or "" for _, q in held)
    if held_topics:
        facts.add("held", f"What held up: {', '.join(held_topics)}.", topics=held_topics)

    # The one to work on: M06's own focus first, then the worst status.
    gap_q = _gap(questions)
    focus = None
    if gap_q is not None:
        topic = topic_name(gap_q.get("concept_id"), names) or "this topic"
        focus = {"concept_id": gap_q.get("concept_id") or "", "topic": topic}
        wrong = (gap_q.get("went_wrong") or [{}])[0]
        said = wrong.get("said") or ""
        why = (wrong.get("why") or gap_q.get("status_detail") or "").rstrip(".")
        asked = short_question(gap_q.get("question", ""))
        text = f'The one to work on is {topic}. On "{asked}", the feedback was: {why}.'
        if said:
            text += f' They said: "{quote(said)}"'
        facts.add(
            "gap", text, topic=topic, quote=quote(said) if said else "", status=gap_q.get("status")
        )
        idea = _the_idea(gap_q)
        if idea:
            facts.add("fix", f"The idea to learn: {idea}", topic=topic)

    for _, q in questions:
        if q.get("last_time"):
            about = topic_name(q.get("concept_id"), names) or "this"
            facts.add("again", f"Asked before about {about}: {q['last_time'].rstrip('.')}.")
            break

    # Rhythm: interviews in the last seven days against the goal.
    ended_all = sorted(
        (
            t
            for t in (parse_time(h.get("ended_at")) for h in history if h.get("status") == "ended")
            if t
        ),
        reverse=True,
    )
    week_ago = as_utc(now) - timedelta(days=7)
    this_week = sum(1 for t in ended_all if t >= week_ago)
    goal = int(profile.get("weekly_goal") or 0)
    if goal:
        facts.add(
            "rhythm",
            f"{plural(this_week, 'interview')} in the last seven days; "
            f"their own goal is {goal} a week.",
            this_week=this_week,
            goal=goal,
        )
    else:
        facts.add(
            "rhythm",
            f"{plural(this_week, 'interview')} in the last seven days.",
            this_week=this_week,
        )
    facts.add(
        "total", f"{plural(len(ended_all), 'interview')} so far, in all.", total=len(ended_all)
    )

    # A long gap before the interviews this talk covers.
    covered_ids = {str(c.get("id")) for c in covered}
    before = [
        parse_time(h.get("ended_at"))
        for h in history
        if h.get("status") == "ended" and str(h.get("id")) not in covered_ids
    ]
    before = sorted((t for t in before if t), reverse=True)
    newest = max((t for t in (parse_time(c.get("ended_at")) for c in covered) if t), default=None)
    if before and newest:
        gap_days = (newest - before[0]).days
        if gap_days >= AWAY_DAYS:
            facts.add(
                "away",
                f"Before this, their last interview was {gap_days} days earlier.",
                days=gap_days,
            )

    # The next drive.
    drive = None
    for d in sorted(profile.get("drives") or [], key=lambda d: str(d.get("date") or "")):
        try:
            day = date.fromisoformat(str(d.get("date")))
        except ValueError:
            continue
        days = (day - today).days
        if 0 <= days <= DRIVE_HORIZON_DAYS:
            label = str(d.get("label") or "the drive")
            drive = {"label": label, "date": day.isoformat(), "days": days}
            facts.add(
                "drive",
                f"The {label} drive is {plural(days, 'day')} away, "
                f"on {day.day} {day.strftime('%B')}.",
                **drive,
            )
            break

    # What moved: topics whose estimate rose between their last two points.
    moved = []
    for series in (trajectory or {}).get("series", []):
        points = series.get("points") or []
        if len(points) >= 2 and points[-1].get("theta", 0) > points[-2].get("theta", 0) + 0.2:
            moved.append(series.get("name") or topic_name(series.get("concept_id"), names))
    moved = _unique(moved)
    if moved:
        facts.add(
            "moved", f"Moved up since the time before: {', '.join(moved[:3])}.", topics=moved[:3]
        )

    # What they said yes to last time, and whether they did it.
    if previous and previous.get("answer") in ("yes", "one") and previous.get("ask"):
        ask = previous["ask"]
        promised = 1 if previous["answer"] == "one" else int(ask.get("count") or 1)
        since = parse_time(previous.get("answered_at") or previous.get("created_at"))
        done = sum(1 for t in ended_all if since and t > since)
        kept = "and they did" if done >= promised else f"and they did {done}"
        facts.add(
            "promise",
            f"Last talk they said yes to {plural(promised, 'interview')} before "
            f"{_day(ask.get('by'))}, {kept}.",
            promised=promised,
            done=done,
            kept=done >= promised,
        )

    return CaseFile(
        name=name,
        facts=facts.items,
        focus=focus,
        this_week=this_week,
        weekly_goal=goal,
        drive=drive,
        held=[{"topic": t} for t in held_topics],
    )


def _their_words(q: dict[str, Any]) -> str:
    """The student's best sentence about a question: what M06 quoted, else
    their first answer."""
    for point in (q.get("writeup") or {}).get("strengths") or []:
        if point.get("evidence"):
            return str(point["evidence"])
    for exchange in q.get("exchanges") or []:
        if exchange.get("role") == "candidate" and exchange.get("text"):
            return str(exchange["text"])
    return ""


def _gap(questions: list[tuple[str, dict[str, Any]]]) -> dict[str, Any] | None:
    worst = None
    for status in NEEDS_WORK:
        found = [q for _, q in questions if q.get("status") == status]
        # A scored question before an unscored one: its judgement is surer.
        found.sort(key=lambda q: bool(q.get("scored")), reverse=True)
        if found:
            worst = found[0]
            break
    return worst


def _the_idea(q: dict[str, Any]) -> str:
    """The right idea in a sentence or two: the write-up's correction, else
    the start of the strong answer."""
    writeup = q.get("writeup") or {}
    idea = writeup.get("correction") or q.get("one_strong_answer") or ""
    sentences = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", idea).strip())
    out = ""
    for s in sentences:
        if len(out) + len(s) > 260:
            break
        out = f"{out} {s}".strip()
    return out


def _unique(items) -> list[str]:  # noqa: ANN001
    seen: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.append(item)
    return seen


def _day(value: Any) -> str:
    try:
        day = date.fromisoformat(str(value))
    except ValueError:
        return "the day they chose"
    return f"{day.strftime('%A')} {day.day} {day.strftime('%B')}"
