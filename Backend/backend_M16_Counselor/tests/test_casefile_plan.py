"""The facts a talk may say, and the steps and ask built from them."""

from __future__ import annotations

from datetime import timedelta

from backend_M16_Counselor import casefile, plan

from .conftest import NOW, REPORT, SESSION, FakeReader, interview


def build(reader: FakeReader | None = None, previous=None):  # noqa: ANN001, ANN201
    reader = reader or FakeReader()
    return casefile.build(
        now=NOW,
        covered=[h for h in reader.history if h["id"] == SESSION],
        reports={SESSION: REPORT},
        history=reader.history,
        profile=reader.profile("c"),
        mastery=reader.mastery("c"),
        trajectory=reader.trajectory("c"),
        previous=previous,
        counselor_name="Tara",
    )


def test_the_one_to_work_on_is_the_question_that_broke_quoting_the_student():
    case = build()
    gap = case.fact("gap")
    assert gap is not None
    assert gap.data["topic"] == "Hashing"
    assert gap.data["quote"] == "Honestly I'm not sure about the assumptions."
    assert case.focus == {"concept_id": "concept:hashing", "topic": "Hashing"}
    assert case.fact("fix") is not None  # the idea to learn, from the write-up


def test_the_best_moment_is_an_answer_that_held_in_their_own_words():
    best = build().fact("best")
    assert best is not None
    assert best.data["topic"] in ("Sorting", "Thinking Aloud")
    assert best.data["quote"]  # their words, never a paraphrase
    assert best.data["quote"].split()[0] in REPORT_WORDS()


def REPORT_WORDS() -> set[str]:  # noqa: N802 - a helper read like a constant
    words: set[str] = set()
    for q in REPORT["questions"]:
        for e in q["exchanges"]:
            if e["role"] == "candidate":
                words.update(e["text"].split())
        for s in (q.get("writeup") or {}).get("strengths") or []:
            words.update(str(s.get("evidence", "")).split())
    return words


def test_rhythm_drive_and_name_come_from_the_profile():
    case = build()
    assert case.name == "Riya"
    assert case.fact("rhythm").data == {"this_week": 1, "goal": 3}
    drive = case.fact("drive")
    assert drive.data["label"] == "Amazon" and drive.data["days"] == 21
    assert case.fact("first") is not None


def test_without_m04_the_talk_has_no_goal_drive_or_name_but_still_its_facts():
    case = build(FakeReader(m04=False))
    assert case.name == "there"
    assert case.fact("drive") is None
    assert case.fact("gap") is not None
    assert case.fact("rhythm").data == {"this_week": 1}


def test_a_long_gap_before_this_interview_is_a_fact():
    reader = FakeReader(
        [interview(SESSION, NOW - timedelta(minutes=30)), interview("old", NOW - timedelta(days=9))]
    )
    assert build(reader).fact("away").data == {"days": 8}


def test_a_promise_from_last_time_is_held_to_what_actually_happened():
    previous = {
        "answer": "yes",
        "ask": {"count": 2, "by": "2026-10-25", "text": "2 more interviews by Sunday 25 October"},
        "answered_at": (NOW - timedelta(days=6)).isoformat(),
        "created_at": (NOW - timedelta(days=6)).isoformat(),
    }
    promise = build(previous=previous).fact("promise")
    assert promise.data == {"promised": 2, "done": 1, "kept": False}
    assert "did 1" in promise.text
    assert build(previous=previous).fact("first") is None


def test_the_first_step_is_the_gap_linked_to_a_focused_mock():
    case = build()
    steps = plan.actions(case)
    assert steps[0]["title"] == "Practise Hashing again"
    assert steps[0]["href"] == "/mock?focus=concept%3Ahashing&label=Hashing"
    assert any("Amazon" in s["title"] for s in steps)  # 21 days: inside the horizon
    assert len(steps) <= 3


def test_the_ask_is_sized_to_their_own_goal():
    ask = plan.ask(build(), NOW)  # goal 3, one done this week
    assert ask["count"] == 2
    assert ask["by"] == "2026-11-01"  # this week's Sunday
    assert [o["id"] for o in ask["options"]] == ["yes", "one", "not_now"]
