"""The words of a talk: written by the model, held to the case file by code.

The episode is seven short chapters — the shape a good senior's talk after a
report card takes, and the one the student can skip around in:

    hello   a hook that proves they looked: the best moment, quoted
    trend   how it's going: rhythm, the drive, the promise kept or not
    well    what held up, in the student's own words
    didnt   the one thing that didn't, honest and fixable
    plan    the steps, in order, each with its time
    ask     the one commitment (the buttons answer it)
    bye     specific encouragement, in the counselor's own sign-off

**The rules every line is held to** (spec §2.4, and M06's notes rule — the
code decides what is true, the model only says it):

1. It cites at least one fact, plan step or the ask, and all of them exist.
2. Every number in it appears in what it cites. No invented counts, dates or
   scores — the platform shows no score until it is calibrated.
3. No empty praise ("great job", "amazing"), no cruelty ("you're not
   ready"), no comparison with other students, no guilt.
4. It is short enough to say in one breath (a long line is cut).

A line that breaks a rule is dropped, not repaired; a chapter left with no
line is filled from the template, which writes the same facts plainly in the
counselor's greeting and sign-off. So the model can make a talk warmer and
more personal, but it can never make it less true.
"""

from __future__ import annotations

import json
import re
from typing import Any

from .casefile import CaseFile
from .counselors import Counselor
from .llm import JOB_SCRIPT, LLM

CHAPTERS: tuple[tuple[str, str], ...] = (
    ("hello", "Hello"),
    ("trend", "How it's going"),
    ("well", "What went well"),
    ("didnt", "What didn't"),
    ("plan", "The plan"),
    ("ask", "Your call"),
    ("bye", "Until next time"),
)
KEYS = tuple(key for key, _ in CHAPTERS)
#: The most characters one spoken line may have.
MAX_LINE = 260
#: Words that are praise without content, cruelty, or a comparison (§2.4).
BANNED = re.compile(
    r"\b(great job|good job|amazing|awesome|fantastic|keep it up|proud of how smart|"
    r"you'?re not ready|you are not ready|not good enough|lazy|disappoint\w*|"
    r"other students|your classmates|out of 10|/10|percent|score of|"
    # A forecast nobody computed (spec §6.7: readiness is a range with
    # evidence, or nothing): no promises about how it will turn out.
    r"you'?ll be ready|you will be ready|you'?ll crack|you will crack|you'?ll clear|"
    r"you will clear|you'?ll get (?:the|an|that) (?:job|offer)|guarante\w*)\b",
    re.I,
)
#: Typography a voice reads badly, and what it is said as.
SPOKEN = str.maketrans(
    {"‑": "-", "‐": "-", "’": "'", "‘": "'", "“": '"', "”": '"', "—": ", ", "–": ", ", " ": " "}
)
NUMBER = re.compile(r"\d+(?:\.\d+)?")

SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["chapters"],
    "properties": {
        "chapters": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["key", "lines"],
                "properties": {
                    "key": {"type": "string", "enum": list(KEYS)},
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
                    },
                },
            },
        }
    },
}

SYSTEM = """You are {name}, talking to {student} the way their {relation} would, after an interview practice. You are an AI counselor with a generated face; you never claim to be a real person and you never invent things that happened to you.

How {name} talks: {manner}

You write a short talk, spoken aloud, in seven chapters, in this order:
- hello: one or two lines. Open with something specific from the case file that proves you looked (the best moment, quoted), not a generic greeting.
- trend: one or two lines on how it's going: their rhythm against their own weekly goal, the next drive, and the promise from last time if there is one (kept or not, without guilt).
- well: one or two lines on what held up, quoting their own words where the case file has them.
- didnt: one or two lines on the one thing to work on, quoting their words. Honest, never harsh, framed as fixable. Do not teach the whole topic; name the idea in a phrase.
- plan: walk through the plan steps in order, one line each, saying how long each takes.
- ask: one line asking for exactly this commitment: "{ask}". Ask it as a question.
- bye: one line, specific encouragement that fits {name}, then their sign-off.

Rules — a line that breaks one is deleted:
1. Every line lists in "cites" the ids it stands on: fact ids (F1, F2, ...), plan ids (P1, P2, P3) or "ask". Say nothing that is not in what you cite.
2. Every number you say must appear in what you cite. Never invent a count, a date, a score or a percentage. There are no scores to give.
3. No empty praise ("great job", "amazing", "keep it up"), no cruelty ("you're not ready"), no comparing them with other students, no guilt.
4. Spoken English: short sentences, plain words, at most two sentences and about 30 words a line. No lists, no symbols, no emoji, no markdown.
5. Call the student {student}. Talk to them ("you"), not about them.
Total: 9 to 14 lines."""


def write(
    llm: LLM, case: CaseFile, counselor: Counselor, steps: list[dict], ask: dict
) -> tuple[dict, str, str | None]:
    """The script, who wrote it ("model" or "template") and, for a template,
    why. Never raises."""
    template = template_script(case, counselor, steps, ask)
    if not llm.available:
        return template, "template", "no language model is configured"
    system = SYSTEM.format(
        name=counselor.name,
        relation=counselor.relation,
        manner=counselor.manner,
        student=case.name,
        ask=ask["text"],
    )
    user = json.dumps(
        {
            "student": case.name,
            "facts": [{"id": f.id, "kind": f.kind, "text": f.text} for f in case.facts],
            "plan": [{"id": s["id"], "step": s["title"], "minutes": s["minutes"]} for s in steps],
            "ask": ask["text"],
            "chapters": list(KEYS),
        },
        ensure_ascii=False,
    )
    result = llm.structured(job=JOB_SCRIPT, system=system, user=user, schema=SCHEMA)
    if not result.ok or not result.data:
        return template, "template", f"the model did not answer ({result.reason})"
    script, kept, dropped = held_to(result.data, case, steps, ask, template)
    if kept == 0:
        return template, "template", f"every line the model wrote broke a rule ({dropped} dropped)"
    script["dropped"] = dropped
    return script, "model", None


def held_to(
    raw: dict, case: CaseFile, steps: list[dict], ask: dict, template: dict
) -> tuple[dict, int, int]:
    """The model's chapters with every rule-breaking line removed, in the
    canonical order, empty chapters filled from the template.

    Returns (script, lines kept, lines dropped)."""
    sources = {f.id: f.text for f in case.facts}
    sources.update({s["id"]: f"{s['title']} {s['minutes']} minutes {s['why']}" for s in steps})
    sources["ask"] = ask["text"]
    by_key: dict[str, list[dict]] = {key: [] for key in KEYS}
    kept = dropped = 0
    for chapter in raw.get("chapters") or []:
        key = chapter.get("key")
        if key not in by_key:
            continue
        for line in chapter.get("lines") or []:
            raw_text = str(line.get("text") or "").translate(SPOKEN)
            text = re.sub(r"\s+", " ", raw_text).replace(" ,", ",").strip()
            cites = [str(c) for c in line.get("cites") or []]
            if _breaks_rules(text, cites, sources):
                dropped += 1
                continue
            by_key[key].append({"text": text, "cites": cites})
            kept += 1
    filled = {c["key"]: c["lines"] for c in template["chapters"]}
    chapters = []
    for key, title in CHAPTERS:
        lines = by_key[key] or filled.get(key, [])
        if key == "ask" and not any(_asks(line["text"], ask) for line in lines):
            # The buttons answer this line: it must actually ask it.
            lines = filled["ask"]
        chapters.append({"key": key, "title": title, "lines": _numbered(key, lines)})
    return {"chapters": chapters}, kept, dropped


def _breaks_rules(text: str, cites: list[str], sources: dict[str, str]) -> bool:
    if not text or len(text) > MAX_LINE or not cites:
        return True
    if any(c not in sources for c in cites):
        return True
    if BANNED.search(text):
        return True
    cited = " ".join(sources[c] for c in cites)
    return any(n not in cited for n in NUMBER.findall(text))


def _asks(text: str, ask: dict) -> bool:
    return (
        text.rstrip().endswith("?")
        and str(ask["count"]) in text
        or (ask["count"] == 1 and text.rstrip().endswith("?") and "one" in text.lower())
    )


def _numbered(key: str, lines: list[dict]) -> list[dict]:
    return [{"id": f"{key}-{i + 1}", **line} for i, line in enumerate(lines)]


# ── the template: the same facts, said plainly ────────────────────────────────


def template_script(case: CaseFile, counselor: Counselor, steps: list[dict], ask: dict) -> dict:
    """A talk written by rule from the facts, in the counselor's own greeting
    and sign-off. What plays when there is no model, and what fills a chapter
    the model's lines were all cut from."""
    f = case.fact
    name = case.name
    lines: dict[str, list[tuple[str, list[str]]]] = {key: [] for key in KEYS}
    lines["hello"].append((counselor.greet.format(name=name), [f("name").id]))
    best = f("best")
    if best and best.data.get("quote"):
        lines["hello"].append(
            (f'One line of yours stuck with me: "{best.data["quote"]}"', [best.id])
        )

    rhythm = f("rhythm")
    if rhythm:
        done, goal = rhythm.data.get("this_week", 0), rhythm.data.get("goal")
        said = f"That's {done} {'interview' if done == 1 else 'interviews'} this week"
        lines["trend"].append(
            (f"{said}, and your goal is {goal}." if goal else f"{said}.", [rhythm.id])
        )
    promise = f("promise")
    if promise:
        text = (
            "Last time you said you'd practise, and you did. That matters."
            if promise.data.get("kept")
            else f"Last time you said {promise.data.get('promised')}, and you did {promise.data.get('done')}. That's alright, let's reset."
        )
        lines["trend"].append((text, [promise.id]))
    drive = f("drive")
    if drive:
        lines["trend"].append(
            (f"{drive.data['label']} is {drive.data['days']} days away.", [drive.id])
        )

    held = f("held")
    if best and best.data.get("topic"):
        lines["well"].append(
            (f"Your answer on {best.data['topic']} held up when they pushed.", [best.id])
        )
    elif held:
        lines["well"].append((f"What held up: {', '.join(held.data['topics'])}.", [held.id]))
    else:
        lines["well"].append(
            ("You showed up and finished it. That's the part most people skip.", [f("name").id])
        )

    gap = f("gap")
    if gap:
        said = gap.data.get("quote")
        lines["didnt"].append((f"The one to fix is {gap.data['topic']}.", [gap.id]))
        if said:
            lines["didnt"].append(
                (f'You said, "{said}" Honest. Now let\'s make sure you know it.', [gap.id])
            )
    else:
        lines["didnt"].append(
            ("Nothing broke this time, so the next one should ask you harder.", [f("name").id])
        )

    for i, step in enumerate(steps):
        lead = ("First", "Then", "And")[min(i, 2)]
        lines["plan"].append(
            (f"{lead}, {step['title'].lower()}. About {step['minutes']} minutes.", [step["id"]])
        )
    if not steps:
        lines["plan"].append(("Pick one topic and do one more interview on it.", [f("name").id]))

    lines["ask"].append((f"So, can you do {ask['text']}?", ["ask"]))
    lines["bye"].append((counselor.signoff.format(name=name), [f("name").id]))

    return {
        "chapters": [
            {
                "key": key,
                "title": title,
                "lines": _numbered(key, [{"text": t, "cites": c} for t, c in lines[key]]),
            }
            for key, title in CHAPTERS
        ]
    }
