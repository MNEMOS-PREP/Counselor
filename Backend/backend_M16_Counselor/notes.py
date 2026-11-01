"""One interview's notes as a walk: the facts each chapter may say, and what
the screen shows beside the face. Pure.

The talk (casefile.py) picks three things out of a report — the best answer,
the one gap, the idea behind it. A walk goes through the questions the student
underperformed on, one by one, in the notes' order — what a senior does when
you hand them your notes and say "go through the ones I got wrong" (the user,
2026-10-31: "not necessarily the entire feedback, but at least where I
underperformed"). What held is said once, in the intro, and listed on screen.
With nothing to work on, the walk takes the answers that held but could be
stronger; with none of those either, it is the intro and the close.

    intro    how it went overall, and what held      the report's statuses
    q1…qN    one chapter per question that needs work (by its number in the notes):
               asked     what was asked, in a phrase
               verdict   the notes' status and their one-line explanation
               said      the student's first answer, quoted
               held      what held, with their words      the write-up's strengths
               missed    what was missing or wrong, with their words and the fix
               stronger  for an answer that held: what would make it stronger
               idea      the idea behind the right answer the write-up's correction
               study     what to practise                  the write-up's next steps
               hints     hints taken
               corrected a mistake they put right
    close    the pattern: the one to work on first, a mistake that came back,
             a correction they made, how it was said

The same rule as the talk: M06 judged each answer and its write-up explained
it, checked against the student's own words; this file only cuts the notes
into facts a line can cite. And the screen beside the face shows the notes as
M06 wrote them (`cards`), never the model's retelling — the student can
always see what the counselor is talking about.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from ai_core.timeutil import as_utc

from .casefile import MODE_WORDS, Fact, _Facts, parse_time, plural, quote, short_question, when

#: The notes' statuses (M06 report `_status`): held, and needs work in the
#: order the one to work on first is chosen — a wrong idea before a missing one.
HELD = ("correct",)
NEEDS_WORK = ("incorrect", "partial", "vague", "unsupported", "unanswered")
#: Not talked about: never asked, or no status at all.
SKIPPED = (None, "not_reached")
#: How much of the notes a chapter carries — a walk, not a reading of the page.
MAX_HELD = 2
MAX_MISSED = 3
MAX_STUDY = 2
#: The student's first answer on the card, in words.
ANSWER_WORDS = 70
#: The idea, in characters: two or three sentences.
IDEA_CHARS = 420

#: Which part of the card a fact is about, so the screen can point at it
#: while the line citing it is said.
SECTION = {
    "asked": "question",
    "verdict": "question",
    "said": "said",
    "held": "held",
    "missed": "missed",
    "stronger": "missed",
    "idea": "idea",
    "study": "study",
}
#: When a line stands on several parts, the one it points at — the most
#: specific first.
POINTING = ("missed", "idea", "study", "held", "said", "question")


@dataclass
class Chapter:
    key: str
    title: str
    #: The question's number in the notes (1-based); None for intro and close.
    index: int | None = None
    #: intro · work · held · close — how the chapter is written.
    kind: str = ""
    #: The facts this chapter may cite.
    facts: list[str] = field(default_factory=list)


@dataclass
class Walk:
    name: str
    facts: list[Fact]
    chapters: list[Chapter]
    #: Chapter key -> the card shown beside the face.
    cards: dict[str, dict[str, Any]]
    #: Whether every explanation in the notes was written.
    complete: bool = True

    def fact(self, fact_id: str) -> Fact | None:
        return next((f for f in self.facts if f.id == fact_id), None)

    def of(self, chapter: Chapter, kind: str) -> list[Fact]:
        return [f for f in self.facts if f.id in chapter.facts and f.kind == kind]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def build(
    report: dict[str, Any],
    *,
    now: datetime,
    name: str,
    names: dict[str, str] | None = None,
) -> Walk:
    """The walk through one report. `names` maps concept ids to the names M04
    gives them, for a question whose report has no topic."""
    names = names or {}
    today = as_utc(now).date()
    facts = _Facts()
    chapters: list[Chapter] = []
    cards: dict[str, dict[str, Any]] = {}

    name_fact = facts.add(
        "name",
        f"The student is called {name}." if name else "The student's name is not known.",
        name=name,
    )
    asked = [
        (i + 1, q)
        for i, q in enumerate(report.get("questions") or [])
        if q.get("status") not in SKIPPED
    ]
    held = [q for _, q in asked if q.get("status") in HELD]
    work = [q for _, q in asked if q.get("status") in NEEDS_WORK]
    # Where they underperformed; with none, the answers that held but could
    # be stronger — a walk through answers with nothing to add is a reading.
    walked = [(i, q) for i, q in asked if q.get("status") in NEEDS_WORK] or [
        (i, q) for i, q in asked if q.get("status") in HELD and _could_be_stronger(q)
    ]
    walked_ids = {i for i, _ in walked}

    # ── intro: the interview, and how it went ─────────────────────────────────
    ended = parse_time(report.get("ended_at"))
    mode = MODE_WORDS.get(str(report.get("mode") or ""), "practice")
    used = report.get("minutes_used")
    minutes = f" in {round(used)} minutes" if isinstance(used, int | float) and used >= 1 else ""
    session = facts.add(
        "session",
        f"{when(ended, today).capitalize()}, a {mode} interview: "
        f"{plural(len(asked), 'question')}{minutes}.",
        questions=len(asked),
        mode=mode,
    )
    unjudged = len(asked) - len(held) - len(work)
    tally_text = (
        f"Of the {plural(len(asked), 'question')}, {len(held)} held up "
        f"and {len(work)} {'needs' if len(work) == 1 else 'need'} work."
    )
    if unjudged:
        tally_text += f" {unjudged} could not be judged."
    tally = facts.add("tally", tally_text, held=len(held), work=len(work), unjudged=unjudged)
    intro = [name_fact.id, session.id, tally.id]
    passed = [(i, q) for i, q in asked if q.get("status") in HELD and i not in walked_ids]
    if passed:
        listed = ", ".join(
            f"question {i}" + (f" on {_about(q, names)}" if _about(q, names) else "")
            for i, q in passed
        )
        intro.append(
            facts.add("passed", f"Held up, so not gone through: {listed}.", listed=listed).id
        )
    if walked:
        numbers = ", ".join(str(i) for i, _ in walked)
        one = len(walked) == 1
        which = ("needs work" if one else "need work") if work else ("held but could be stronger")
        intro.append(
            facts.add(
                "walking",
                f"Going through question{'' if one else 's'} {numbers}: "
                f"the {'one that' if one else 'ones that'} {which}.",
                numbers=numbers,
                one=one,
                which=which,
            ).id
        )
    chapters.append(Chapter("intro", "Before we start", kind="intro", facts=intro))
    cards["intro"] = {
        "kind": "overview",
        "held": len(held),
        "work": len(work),
        "unjudged": unjudged,
        "questions": [
            {
                "key": f"q{index}",
                "index": index,
                "question": short_question(q.get("question", ""), 16),
                "status": q.get("status"),
                "status_label": q.get("status_label") or "",
                "topic": _topic(q, names) or ("Your resume" if _resume_line(q) else ""),
                "walked": index in walked_ids,
            }
            for index, q in asked
        ],
    }

    # ── one chapter per question ──────────────────────────────────────────────
    complete = not any(
        not q.get("writeup") and q.get("status") not in ("unanswered", "not_judged")
        for _, q in walked
    )
    for index, q in walked:
        key = f"q{index}"
        kind = "held" if q.get("status") in HELD else "work"
        writeup = q.get("writeup") or {}
        topic = _topic(q, names)
        label = q.get("status_label") or "Not judged"
        explained = _plain(writeup.get("headline") or q.get("status_detail") or "")
        answer = _first_answer(q)
        held_points = _held(q, writeup)
        missed_points = _missed(q, writeup, kind)
        idea = study = None
        if kind == "work":
            idea = _sentences(
                writeup.get("correction")
                or writeup.get("model_answer")
                or q.get("one_strong_answer")
                or "",
                IDEA_CHARS,
            )
            study = [_sentence(s) for s in (writeup.get("next_steps") or q.get("study") or [])]
        ids = [name_fact.id]

        def add(fact_kind: str, text: str, **data: Any) -> None:
            ids.append(facts.add(fact_kind, _plain(text), chapter=key, **data).id)  # noqa: B023

        # The question is the interviewer's words, so it is not in quotation
        # marks: a quote in a fact is the student's own (walk_script holds a
        # line's quotes to them). Their resume line is theirs.
        asked_q = short_question(q.get("question", ""), 32)
        line = _resume_line(q)
        if line:
            text = (
                f'Question {index} was about a line on their resume, "{line}". It asked: {asked_q}'
            )
        else:
            text = f"Question {index}{f' on {topic}' if topic else ''} asked: {asked_q}"
        add("asked", text, question=asked_q, topic=topic, resume=line)
        add(
            "verdict",
            f"The notes say: {label}." + (f" {explained}" if explained else ""),
            label=label,
            explained=explained,
        )
        if answer:
            add("said", f'They first said: "{quote(answer, 30)}"', quote=quote(answer, 30))
        for point in held_points:
            text = f"What held: {_sentence(point['point'])}"
            if point["evidence"]:
                text += f' They said: "{quote(point["evidence"])}"'
            add("held", text, point=point["point"], quote=quote(point["evidence"]))
        lead = "To make it stronger" if kind == "held" else "Missing or wrong"
        for point in missed_points:
            text = f"{lead}: {_sentence(point['point'])}" if point["point"] else f"{lead}:"
            if point["evidence"]:
                text += f' They said: "{quote(point["evidence"])}"'
            if point["fix"]:
                text += f" The fix: {_sentence(point['fix'])}"
            add(
                "stronger" if kind == "held" else "missed",
                text,
                point=point["point"],
                quote=quote(point["evidence"]),
                fix=point["fix"],
            )
        if idea:
            add("idea", f"The idea behind the right answer: {idea}", idea=idea)
        for step in (study or [])[:MAX_STUDY]:
            add("study", f"To practise: {step}", step=step)
        hints = int(q.get("hints_used") or 0)
        if hints:
            add("hints", f"They took {plural(hints, 'hint')} on it.", hints=hints)
        if q.get("corrected") == "self":
            add("corrected", "They noticed a mistake and corrected it themselves.")
        elif q.get("corrected") == "prompted":
            add("corrected", "They got it right after the interviewer pushed back.")

        chapters.append(Chapter(key, f"Question {index}", index=index, kind=kind, facts=ids))
        cards[key] = {
            "kind": "question",
            "index": index,
            "topic": topic,
            "resume_line": _resume_line(q),
            "status": q.get("status"),
            "status_label": label,
            "question": _plain(q.get("question", "")),
            "headline": explained,
            "answer": _plain(quote(answer, ANSWER_WORDS)) if answer else "",
            "held": held_points,
            "missed": missed_points,
            "missed_title": (
                "To make it even stronger" if kind == "held" else "What was missing or wrong"
            ),
            "idea": idea or "",
            "study": (study or [])[:MAX_STUDY],
        }

    # ── close: the pattern across the questions ───────────────────────────────
    summary = report.get("summary") or {}
    ids = [name_fact.id, tally.id]
    first = _first_to_work_on(work)
    if first is not None:
        topic = _about(first, names) or "the question you found hardest"
        made = facts.add("focus", f"The one to work on first: {topic}.", topic=topic)
        ids.append(made.id)
    shown: list[str] = []
    for repeated in (summary.get("repeated_misconceptions") or [])[:1]:
        said = _sentence(repeated)
        ids.append(
            facts.add("repeat", f"A mistake that came up more than once: {said}", said=said).id
        )
        shown.append(f"A mistake that came up more than once: {said}")
    corrected = [str(c) for c in (summary.get("corrected") or [])[:3]]
    if corrected:
        listed = ", ".join(corrected)
        ids.append(
            facts.add(
                "corrected", f"They corrected themselves along the way: {listed}.", listed=listed
            ).id
        )
        shown.append(f"You corrected yourself along the way: {listed}.")
    for delivery in (summary.get("communication") or [])[:1]:
        said = _sentence(delivery)
        ids.append(facts.add("delivery", f"On how it was said: {said}", said=said).id)
        shown.append(f"How you said it: {said}")
    chapters.append(Chapter("close", "To finish", kind="close", facts=ids))
    cards["close"] = {
        "kind": "close",
        "focus": (_about(first, names) or "") if first is not None else "",
        "points": [_plain(p) for p in shown],
    }

    if report.get("writeups") == "pending":
        complete = False
    return Walk(name=name, facts=facts.items, chapters=chapters, cards=cards, complete=complete)


# ── reading the notes ─────────────────────────────────────────────────────────


def _resume_line(q: dict[str, Any]) -> str:
    """A resume question's line (M06 gives a claim's line as its `topic`)."""
    if str(q.get("concept_id") or "").startswith("claim:"):
        return _plain(q.get("topic") or "")
    return ""


def _about(q: dict[str, Any], names: dict[str, str]) -> str:
    """What a question was about, said in a sentence: its topic, or the
    resume line it asked about."""
    line = _resume_line(q)
    return f'your resume line "{line}"' if line else _topic(q, names)


def _topic(q: dict[str, Any], names: dict[str, str]) -> str:
    concept = str(q.get("concept_id") or "")
    # A resume question's "concept" is the claim it is about, and its "topic"
    # the claim's line — neither is a topic (`_resume_line`).
    if concept.startswith("claim:"):
        return ""
    if q.get("topic"):
        return str(q["topic"])
    if not concept:
        return ""
    return names.get(concept) or concept.split(":", 1)[-1].replace("_", " ")


def _could_be_stronger(q: dict[str, Any]) -> bool:
    return any(g.get("point") for g in (q.get("writeup") or {}).get("gaps") or [])


def _held(q: dict[str, Any], writeup: dict[str, Any]) -> list[dict[str, str]]:
    """What held, with the student's words: the write-up's strengths, else
    the interview's own short list."""
    strengths = [s for s in writeup.get("strengths") or [] if s.get("point")]
    if strengths:
        return [
            {"point": _plain(s["point"]), "evidence": _plain(s.get("evidence") or "")}
            for s in strengths[:MAX_HELD]
        ]
    return [{"point": _plain(p), "evidence": ""} for p in (q.get("went_well") or [])[:MAX_HELD]]


def _missed(q: dict[str, Any], writeup: dict[str, Any], kind: str) -> list[dict[str, str]]:
    """What was missing or wrong (or, for an answer that held, what would make
    it stronger), with the student's words and the fix: the write-up's gaps,
    else what the interview recorded going wrong."""
    gaps = [g for g in writeup.get("gaps") or [] if g.get("point")]
    if gaps:
        return [
            {
                "point": _plain(g["point"]),
                # An answer that held is not quoted back as a failing.
                "evidence": _plain(g.get("evidence") or "") if kind == "work" else "",
                "fix": _plain(g.get("fix") or ""),
            }
            for g in gaps[:MAX_MISSED]
        ]
    if kind != "work":
        return []
    return [
        {"point": _plain(w.get("why") or ""), "evidence": _plain(w.get("said") or ""), "fix": ""}
        for w in (q.get("went_wrong") or [])[:MAX_MISSED]
        if w.get("why") or w.get("said")
    ]


def _first_answer(q: dict[str, Any]) -> str:
    """The student's first answer to the question as asked — a practice retry
    is shown in the notes but is never the answer that was judged."""
    for exchange in q.get("exchanges") or []:
        if (
            exchange.get("role") == "candidate"
            and not exchange.get("retry")
            and exchange.get("text")
        ):
            return str(exchange["text"])
    return ""


def _first_to_work_on(work: list[dict[str, Any]]) -> dict[str, Any] | None:
    for status in NEEDS_WORK:
        found = [q for q in work if q.get("status") == status]
        found.sort(key=lambda q: bool(q.get("scored")), reverse=True)
        if found:
            return found[0]
    return None


#: Typography the notes carry and a voice reads badly (the write-ups come from
#: a model, which loves a non-breaking hyphen).
_PLAIN = str.maketrans({"‑": "-", "‐": "-", " ": " ", "≤": "at most ", "≥": "at least "})


def _plain(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").translate(_PLAIN)).strip()


def _sentence(text: str) -> str:
    """A phrase as a sentence: plain, and ending in a full stop."""
    said = _plain(text).rstrip()
    return said if said.endswith((".", "?", "!")) else f"{said}."


def _sentences(text: str, limit: int) -> str:
    """Whole sentences, up to `limit` characters — never cut mid-sentence."""
    out = ""
    for s in re.split(r"(?<=[.!?])\s+", _plain(text)):
        if out and len(out) + len(s) + 1 > limit:
            break
        out = f"{out} {s}".strip()
    return out
