"""The rules every spoken line is held to (script.py)."""

from __future__ import annotations

from backend_M16_Counselor import counselors, plan, script
from backend_M16_Counselor.llm import LLMResult, NullLLM

from .conftest import NOW
from .test_casefile_plan import build


class FakeLLM:
    def __init__(self, data: dict | None) -> None:
        self.data = data

    @property
    def available(self) -> bool:
        return True

    def structured(self, *, job, system, user, schema):  # noqa: ANN001, ANN201
        return LLMResult(
            ok=self.data is not None, data=self.data, reason=None if self.data else "down"
        )


def parts():  # noqa: ANN201
    case = build()
    steps = plan.actions(case)
    return case, steps, plan.ask(case, NOW), counselors.get("counsel_kabir")


def test_the_template_has_every_chapter_and_every_line_cites_what_exists():
    case, steps, ask, kabir = parts()
    talk = script.template_script(case, kabir, steps, ask)
    assert [c["key"] for c in talk["chapters"]] == list(script.KEYS)
    known = {f.id for f in case.facts} | {s["id"] for s in steps} | {"ask"}
    for chapter in talk["chapters"]:
        assert chapter["lines"], chapter["key"]
        for line in chapter["lines"]:
            assert line["cites"] and set(line["cites"]) <= known
    assert "Riya" in talk["chapters"][0]["lines"][0]["text"]  # Kabir's own greeting


def test_a_line_with_an_invented_number_praise_or_no_citation_is_cut():
    case, steps, ask, kabir = parts()
    gap = case.fact("gap").id
    raw = {
        "chapters": [
            {
                "key": "hello",
                "lines": [{"text": "Riya, you did 5 interviews this week!", "cites": ["F1"]}],
            },
            {"key": "well", "lines": [{"text": "Great job on everything.", "cites": ["F1"]}]},
            {
                "key": "didnt",
                "lines": [
                    {
                        "text": "Hashing is the one. You said you weren't sure about the assumptions.",
                        "cites": [gap],
                    },
                    {"text": "And your aptitude is weak too.", "cites": []},
                    {"text": "Load factor matters.", "cites": ["F99"]},
                ],
            },
            {
                "key": "ask",
                "lines": [{"text": "Will you do 2 more interviews by Sunday?", "cites": ["ask"]}],
            },
        ]
    }
    template = script.template_script(case, kabir, steps, ask)
    talk, kept, dropped = script.held_to(raw, case, steps, ask, template)
    assert (kept, dropped) == (2, 4)
    by_key = {c["key"]: c for c in talk["chapters"]}
    assert [line["text"] for line in by_key["didnt"]["lines"]] == [
        "Hashing is the one. You said you weren't sure about the assumptions."
    ]
    # Chapters whose lines were all cut are the template's.
    assert (
        by_key["hello"]["lines"]
        == next(c for c in template["chapters"] if c["key"] == "hello")["lines"]
    )
    assert by_key["ask"]["lines"][0]["text"] == "Will you do 2 more interviews by Sunday?"


def test_an_ask_line_that_does_not_ask_is_replaced_by_the_one_that_does():
    case, steps, ask, kabir = parts()
    raw = {
        "chapters": [
            {"key": "ask", "lines": [{"text": "Practise when you can.", "cites": ["ask"]}]}
        ]
    }
    talk, _, _ = script.held_to(
        raw, case, steps, ask, script.template_script(case, kabir, steps, ask)
    )
    ask_line = next(c for c in talk["chapters"] if c["key"] == "ask")["lines"][0]["text"]
    assert ask_line.endswith("?") and "2 more interviews" in ask_line


def test_without_a_model_the_talk_is_the_template_and_says_why():
    case, steps, ask, kabir = parts()
    talk, source, reason = script.write(NullLLM("no key"), case, kabir, steps, ask)
    assert source == "template" and reason == "no language model is configured"
    assert len(talk["chapters"]) == len(script.KEYS)


def test_a_model_that_breaks_every_rule_falls_back_whole():
    case, steps, ask, kabir = parts()
    bad = {"chapters": [{"key": "hello", "lines": [{"text": "Amazing!", "cites": ["F1"]}]}]}
    _, source, reason = script.write(FakeLLM(bad), case, kabir, steps, ask)
    assert source == "template" and "broke a rule" in reason


def test_a_good_model_talk_is_kept_in_the_canonical_order():
    case, steps, ask, kabir = parts()
    best, gap = case.fact("best").id, case.fact("gap").id
    good = {
        "chapters": [
            {"key": "bye", "lines": [{"text": "Go get it done, Riya.", "cites": ["F1"]}]},
            {
                "key": "hello",
                "lines": [
                    {"text": "Riya, that sorting answer was the real thing.", "cites": [best]}
                ],
            },
            {"key": "didnt", "lines": [{"text": "Hashing is the one to fix.", "cites": [gap]}]},
            {
                "key": "ask",
                "lines": [{"text": "So, 2 more interviews by Sunday?", "cites": ["ask"]}],
            },
        ]
    }
    talk, source, _ = script.write(FakeLLM(good), case, kabir, steps, ask)
    assert source == "model"
    assert [c["key"] for c in talk["chapters"]] == list(script.KEYS)
    assert (
        talk["chapters"][0]["lines"][0]["text"] == "Riya, that sorting answer was the real thing."
    )


def test_a_promise_about_how_it_will_turn_out_is_cut():
    case, steps, ask, kabir = parts()
    gap = case.fact("gap").id
    raw = {
        "chapters": [
            {
                "key": "bye",
                "lines": [
                    {"text": "Keep going and you'll be ready for Amazon.", "cites": ["F1"]},
                    {"text": "Hashing first, then the rest.", "cites": [gap]},
                ],
            }
        ]
    }
    talk, kept, dropped = script.held_to(
        raw, case, steps, ask, script.template_script(case, kabir, steps, ask)
    )
    assert (kept, dropped) == (1, 1)


def test_typography_a_voice_reads_badly_is_said_plainly():
    case, steps, ask, kabir = parts()
    gap = case.fact("gap").id
    raw = {
        "chapters": [
            {
                "key": "didnt",
                "lines": [
                    {"text": "Your walk‑through on hashing — that’s the one.", "cites": [gap]},
                ],
            }
        ]
    }
    talk, _, _ = script.held_to(
        raw, case, steps, ask, script.template_script(case, kabir, steps, ask)
    )
    line = next(c for c in talk["chapters"] if c["key"] == "didnt")["lines"][0]["text"]
    assert line == "Your walk-through on hashing, that's the one."
