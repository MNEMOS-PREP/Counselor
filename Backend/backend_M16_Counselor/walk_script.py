"""The words of a walk through the notes: one model call per chapter, each
line held to that chapter's facts by code.

**One call per chapter, not one for the walk** (the talk's way). A walk
explains — what was missing, and the idea behind the right answer — and a
model asked for every chapter at once writes the last questions thinner than
the first. One chapter at a time it has only that question's facts in front of
it, so it cannot borrow another's; and a chapter whose lines are all cut falls
back on its own, not the walk. The student asked for it and waits for it, and
said they don't mind the wait (2026-10-31).

**The calls go one after another, never at once.** Groq's limits are per
minute; bursting past them is the thing not to do. A 429 is waited out for as
long as the answer asks, up to `RATE_WAIT_MAX`; a longer wait is the daily
limit, and the rest of the walk is said from the template.

**The rules are the talk's** (`script.breaks_rules`: cites, numbers, no empty
praise or cruelty or forecasts, one breath), **plus two.** A line cites only
its own chapter's facts. And a quote is the student's words or nothing:
whatever a line puts in quotation marks must be inside a quotation in what it
cites — and the facts quote only the student (their answers, their resume),
never the interviewer or the notes' labels. A live walk put "Skipped" in
quotation marks as if the student had said it (2026-10-31).
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from typing import Any

from .counselors import Counselor, address, named
from .llm import JOB_WALK, LLM
from .notes import Chapter, Walk
from .script import MAX_LINE, SPOKEN, breaks_rules

#: Tries per chapter, and the longest a rate limit is waited out.
ATTEMPTS = 3
RATE_WAIT_MAX = 90.0
#: "Please try again in 7.66s" / "in 1m3.5s" / "in 19m57s" (Groq's 429).
TRY_AGAIN = re.compile(r"try again in (?:(\d+)m)?(\d+(?:\.\d+)?)s", re.I)
QUOTED = re.compile(r'"([^"]+)"')

SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["lines"],
    "properties": {
        "lines": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["text", "cites"],
                "properties": {
                    "text": {"type": "string"},
                    "cites": {"type": "array", "items": {"type": "string"}},
                },
            },
        }
    },
}

SYSTEM = """You are {name}, sitting beside {student} and going through their interview notes with them, the way a good mentor would. You are an AI mentor with a generated face; you never claim to be a real person and you never invent things that happened to you.

How {name} talks: {manner}

The notes are on the screen beside you. You are talking them through, not reading them out. You only go through the questions {student} underperformed on; the ones that held up are mentioned once, at the start.

{part}

Rules — a line that breaks one is deleted:
1. Every line lists in "cites" the fact ids it stands on (F1, F2, ...). Cite only the facts you are given. Say nothing that is not in what you cite.
2. Every number you say must appear in what you cite. Never invent a count, a date, a score or a percentage. There are no scores to give.
3. Anything in quotation marks must be the student's words exactly as a fact gives them. Otherwise, use no quotation marks.
4. No empty praise ("great job", "amazing", "keep it up"), no cruelty ("you're not ready"), no comparing them with other students, no guilt, no promises about how a real interview will go.
5. Spoken English: short sentences, plain words, at most two sentences and about 30 words a line. No lists, no symbols, no emoji, no markdown.
6. {address} Talk to them ("you"), not about them."""

PART = {
    "intro": """This is the opening, before the first question. Write 2 or 3 lines: hello; that you have been through their notes; how it went overall; which questions held up (only name them, you will not go through those); and which you will go through now.""",
    "work": """This is question {index}, one {student} underperformed on. Write 4 to 7 lines, in this order:
1. What was asked, in a phrase. Do not read the whole question out.
2. If part of the answer was right, say so in one line, quoting them.
3. What they said that fell short, quoted, and what was missing or wrong in it. Honest and specific, never harsh.
4. The idea behind the right answer, explained simply, the way you would explain it across a table: what it is and why it matters. Your own words, but only what the facts say. Take two lines if it needs them.
5. One line on what to practise, if a fact gives it.""",
    "held": """This is question {index}. It held up, but could be stronger. Write 2 or 3 lines: what was asked, in a phrase; what they got right, quoting them if a fact has their words; and what would make it even stronger.""",
    "close": """This is the end, after the last question. Write 2 or 3 lines: the one to work on first, and anything else the facts give (a mistake that came back, a correction they made, how they said it); then end with {name}'s own sign-off, in these words: "{signoff}".""",
}


def write(
    llm: LLM,
    walk: Walk,
    counselor: Counselor,
    *,
    beat: Callable[[str], None] = lambda _stage: None,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[dict, str, str | None, list[str]]:
    """The walk's words, who wrote them (model · mixed · template), why any
    chapter is a template, and which. Never raises. `beat` is told what it is
    on before each chapter, so a walk taking minutes is seen to be alive."""
    template = template_script(walk, counselor)
    by_key = {c["key"]: c["lines"] for c in template["chapters"]}
    keys = [c.key for c in walk.chapters]
    if not llm.available:
        return template, "template", "no language model is configured", keys

    chapters, templated, reasons = [], [], []
    stopped: str | None = None
    for n, chapter in enumerate(walk.chapters, start=1):
        beat(f"{chapter.title} ({n} of {len(walk.chapters)})")
        lines: list[dict] = []
        if stopped is None:
            lines, why = _chapter(llm, walk, counselor, chapter, beat=beat, sleep=sleep)
            if why and why.startswith("daily limit"):
                stopped = why
            if why:
                reasons.append(f"{chapter.title}: {why}")
        else:
            reasons.append(f"{chapter.title}: {stopped}")
        if not lines:
            templated.append(chapter.key)
            lines = by_key[chapter.key]
        chapters.append(
            {"key": chapter.key, "title": chapter.title, "lines": _numbered(chapter.key, lines)}
        )

    source = "model" if not templated else "template" if len(templated) == len(keys) else "mixed"
    return (
        {"chapters": chapters},
        source,
        ("; ".join(reasons) or None) if templated else None,
        templated,
    )


def _chapter(
    llm: LLM,
    walk: Walk,
    counselor: Counselor,
    chapter: Chapter,
    *,
    beat: Callable[[str], None],
    sleep: Callable[[float], None],
) -> tuple[list[dict], str | None]:
    """One chapter's lines from the model, held to its facts — or [] and why."""
    facts = [f for f in walk.facts if f.id in chapter.facts]
    student = walk.name or "the student"
    part = PART[chapter.kind].format(
        index=chapter.index,
        student=student,
        name=counselor.name,
        signoff=named(counselor.signoff, walk.name),
    )
    system = SYSTEM.format(
        name=counselor.name,
        manner=counselor.manner,
        student=student,
        address=address(walk.name),
        part=part,
    )
    user = json.dumps(
        {
            "student": walk.name or None,
            "chapter": chapter.title,
            "facts": [{"id": f.id, "kind": f.kind, "text": f.text} for f in facts],
        },
        ensure_ascii=False,
    )
    why: str | None = None
    for attempt in range(1, ATTEMPTS + 1):
        result = llm.structured(job=JOB_WALK, system=system, user=user, schema=SCHEMA)
        if result.ok and result.data:
            lines, dropped = held_to(result.data, chapter, {f.id: f.text for f in facts})
            if covers(lines, chapter, walk):
                return lines, None
            why = f"the model's lines did not hold ({dropped} cut)"
            continue
        why = result.reason or "no answer"
        wait = rate_wait(why)
        if wait is None:
            continue
        if wait > RATE_WAIT_MAX:
            return [], "daily limit reached; the rest is said plainly"
        if attempt < ATTEMPTS:
            beat(f"{chapter.title}: waiting {round(wait)} s for the model")
            sleep(wait + 1)
    return [], why


def held_to(raw: dict, chapter: Chapter, sources: dict[str, str]) -> tuple[list[dict], int]:
    """The model's lines for one chapter with every rule-breaking line removed.
    Returns (lines kept, lines dropped)."""
    kept: list[dict] = []
    dropped = 0
    for line in raw.get("lines") or []:
        text = re.sub(r"\s+", " ", str(line.get("text") or "").translate(SPOKEN))
        text = text.replace(" ,", ",").strip()
        cites = [str(c) for c in line.get("cites") or []]
        if breaks_rules(text, cites, sources) or misquotes(text, cites, sources):
            dropped += 1
            continue
        kept.append({"text": text, "cites": cites})
    return kept, dropped


def misquotes(text: str, cites: list[str], sources: dict[str, str]) -> bool:
    """Whether the line puts in quotation marks anything that is not inside a
    quotation of the student in what it cites."""
    theirs = [_words(q) for c in cites for q in QUOTED.findall(sources.get(c, ""))]
    for span in QUOTED.findall(text):
        said = _words(span)
        if said and not any(f" {said} " in f" {q} " for q in theirs):
            return True
    return False


def covers(lines: list[dict], chapter: Chapter, walk: Walk) -> bool:
    """A chapter about a question that needs work must say what fell short or
    the idea behind the right answer — a chapter of pleasantries is not a walk."""
    if not lines:
        return False
    if chapter.kind != "work":
        return True
    needed = {f.id for f in walk.facts if f.id in chapter.facts and f.kind in ("missed", "idea")}
    if not needed:
        return True
    return any(set(line["cites"]) & needed for line in lines)


def rate_wait(reason: str) -> float | None:
    """Seconds to wait out a rate limit, from the 429's own words; None when
    the failure was not a rate limit."""
    if "429" not in reason:
        return None
    found = TRY_AGAIN.search(reason)
    if found is None:
        return 20.0
    return int(found.group(1) or 0) * 60 + float(found.group(2))


def _words(text: str) -> str:
    """Lower-case words only, for comparing a quote with what was said."""
    plain = text.translate(SPOKEN).replace("’", "'").lower()
    return " ".join(re.findall(r"[a-z0-9']+", plain))


def _numbered(key: str, lines: list[dict]) -> list[dict]:
    return [
        {"id": f"{key}-{i + 1}", "text": line["text"], "cites": line["cites"]}
        for i, line in enumerate(lines)
    ]


# ── the template: the same facts, said plainly ────────────────────────────────


def template_script(walk: Walk, counselor: Counselor) -> dict:
    """A walk written by rule from the facts, in the mentor's own greeting and
    sign-off. What plays when there is no model, and what fills a chapter the
    model's lines were all cut from."""
    chapters = []
    for chapter in walk.chapters:
        said: list[tuple[str, list[str]]] = []
        if chapter.kind == "intro":
            said = _intro(walk, chapter, counselor)
        elif chapter.kind == "close":
            said = _close(walk, chapter, counselor)
        else:
            said = _question(walk, chapter)
        chapters.append(
            {
                "key": chapter.key,
                "title": chapter.title,
                "lines": _numbered(
                    chapter.key, [{"text": _spoken(t), "cites": c} for t, c in said if t]
                ),
            }
        )
    return {"chapters": chapters}


def _intro(walk: Walk, chapter: Chapter, counselor: Counselor) -> list[tuple[str, list[str]]]:
    name = walk.of(chapter, "name")[0]
    hello = _first_sentence(named(counselor.greet, walk.name))
    out = [(f"{hello} I've been through your notes.", [name.id])]
    tally = walk.of(chapter, "tally")[0]
    held, work = tally.data["held"], tally.data["work"]
    asked = held + work + tally.data["unjudged"]
    out.append(
        (
            f"Of the {asked} {'question' if asked == 1 else 'questions'}, {held} held up "
            f"and {work} {'needs' if work == 1 else 'need'} work.",
            [tally.id],
        )
    )
    for passed in walk.of(chapter, "passed"):
        listed = passed.data["listed"]
        out.append(
            (f"{listed[0].upper()}{listed[1:]}: those held, so we'll leave them.", [passed.id])
        )
    for walking in walk.of(chapter, "walking"):
        one = walking.data["one"]
        out.append(
            (
                f"Let's go through question{'' if one else 's'} {walking.data['numbers']}, "
                f"the {'one that' if one else 'ones that'} {walking.data['which']}.",
                [walking.id],
            )
        )
    if not walk.of(chapter, "walking"):
        out.append(("Nothing needs going through this time.", [tally.id]))
    return out


def _question(walk: Walk, chapter: Chapter) -> list[tuple[str, list[str]]]:
    out: list[tuple[str, list[str]]] = []
    asked = walk.of(chapter, "asked")[0]
    topic, line = asked.data.get("topic"), asked.data.get("resume")
    about = f', about your resume line "{line}"' if line else f", on {topic}" if topic else ""
    out.append((f"Question {chapter.index}{about}. {asked.data['question']}", [asked.id]))
    verdict = walk.of(chapter, "verdict")[0]
    if chapter.kind == "held":
        held = walk.of(chapter, "held")
        if held and held[0].data.get("quote"):
            out.append((f'This one held up. You said: "{held[0].data["quote"]}"', [held[0].id]))
        else:
            out.append(("This one held up.", [verdict.id]))
        for point in walk.of(chapter, "stronger")[:1]:
            out.append((f"To make it even stronger: {_lower(point.data['point'])}.", [point.id]))
            if point.data.get("fix"):
                out.append((point.data["fix"], [point.id]))
        return out

    out.append((f"The notes say: {verdict.data['label']}.", [verdict.id]))
    if verdict.data.get("explained"):
        out.append((verdict.data["explained"], [verdict.id]))
    for point in walk.of(chapter, "missed")[:2]:
        if point.data.get("point"):
            out.append((f"Where it fell short: {_lower(point.data['point'])}.", [point.id]))
        if point.data.get("quote"):
            out.append((f'You said: "{point.data["quote"]}"', [point.id]))
        if point.data.get("fix"):
            out.append((point.data["fix"], [point.id]))
    for idea in walk.of(chapter, "idea"):
        sentences = _split(idea.data["idea"])
        out.append((f"Here's the idea. {sentences[0]}", [idea.id]))
        out += [(s, [idea.id]) for s in sentences[1:]]
    for step in walk.of(chapter, "study")[:1]:
        out.append((f"To practise: {_lower(step.data['step'])}", [step.id]))
    for fact in walk.of(chapter, "corrected"):
        out.append(
            (fact.text.replace("They ", "You ", 1).replace("themselves", "yourself"), [fact.id])
        )
    return out


def _close(walk: Walk, chapter: Chapter, counselor: Counselor) -> list[tuple[str, list[str]]]:
    out: list[tuple[str, list[str]]] = []
    for focus in walk.of(chapter, "focus"):
        out.append((f"If you work on one thing first, make it {focus.data['topic']}.", [focus.id]))
    for repeat in walk.of(chapter, "repeat"):
        out.append(
            (f"One mistake came up more than once: {_lower(repeat.data['said'])}", [repeat.id])
        )
    for fixed in walk.of(chapter, "corrected"):
        out.append(
            (
                f"You corrected yourself along the way, on {fixed.data['listed']}. Keep doing that.",
                [fixed.id],
            )
        )
    for delivery in walk.of(chapter, "delivery"):
        out.append((f"On how you said it: {_lower(delivery.data['said'])}", [delivery.id]))
    name = walk.of(chapter, "name")[0]
    out.append((named(counselor.signoff, walk.name), [name.id]))
    return out


def _spoken(text: str) -> str:
    return re.sub(r"\s+", " ", text.translate(SPOKEN)).replace(" ,", ",").strip()


def _split(text: str) -> list[str]:
    """Sentences grouped into lines a subtitle can hold."""
    lines: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
        if lines and len(lines[-1]) + len(sentence) + 1 <= MAX_LINE // 2:
            lines[-1] = f"{lines[-1]} {sentence}"
        else:
            lines.append(sentence)
    return [line for line in lines if line]


def _first_sentence(text: str) -> str:
    return re.split(r"(?<=[.!?])\s+", text.strip())[0]


def _lower(text: str) -> str:
    """A sentence used inside another: its first letter lower-cased, unless it
    starts with an acronym ("DP", "O(1)")."""
    text = text.strip()
    if len(text) > 1 and text[1].isupper():
        return text
    return text[:1].lower() + text[1:]
