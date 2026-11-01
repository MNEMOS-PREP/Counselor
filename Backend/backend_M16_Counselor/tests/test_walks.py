"""A walk through one interview's notes (notes.py, walk_script.py, walks.py).

Built on the real M06 report in fixtures/ — a warm-up and a stable-sort
answer that held, a hash-map answer that broke at the follow-up — so what the
walk reads is the producer's own shape, never an invented one.
"""

from __future__ import annotations

import copy
import json

import pytest
from fastapi.testclient import TestClient

from backend_M16_Counselor import counselors, notes, walk_script, walks
from backend_M16_Counselor import router as router_module
from backend_M16_Counselor.app import app
from backend_M16_Counselor.llm import LLMResult, NullLLM, set_llm
from backend_M16_Counselor.models import Walkthrough

from .conftest import NOW, REPORT, SESSION, FakeReader, student

RIYA = "e4e03be0-a233-8ea5-8342-16e914e53d92"
NAMES = {"concept:hashing": "Hashing", "concept:sorting": "Sorting"}
TARA = counselors.get("counsel_tara")


def walk(report: dict | None = None) -> notes.Walk:
    return notes.build(report or REPORT, now=NOW, name="Riya", names=NAMES)


def chapter(built: notes.Walk, key: str) -> notes.Chapter:
    return next(c for c in built.chapters if c.key == key)


class ScriptedLLM:
    """Answers each chapter with `answer(chapter_title, facts)`; counts calls."""

    def __init__(self, answer) -> None:  # noqa: ANN001
        self.answer = answer
        self.calls: list[str] = []

    @property
    def available(self) -> bool:
        return True

    def structured(self, *, job, system, user, schema):  # noqa: ANN001, ANN201
        sent = json.loads(user)
        self.calls.append(sent["chapter"])
        return self.answer(sent["chapter"], sent["facts"], len(self.calls))


def ok(lines: list[tuple[str, list[str]]]) -> LLMResult:
    return LLMResult(ok=True, data={"lines": [{"text": t, "cites": c} for t, c in lines]})


def good_lines(title: str, facts: list[dict], _n: int) -> LLMResult:
    """What a model that keeps the rules says: each line on one fact, in its words."""
    by_kind: dict[str, str] = {}
    for f in facts:
        by_kind.setdefault(f["kind"], f["id"])  # the first of each kind
    if title == "Question 2":
        return ok(
            [
                ("Question 2 was about why a hash map lookup is fast.", [by_kind["asked"]]),
                ('You said "Honestly I\'m not sure about the assumptions."', [by_kind["missed"]]),
                (
                    "The keys need to spread evenly, and the table must not fill up.",
                    [by_kind["idea"]],
                ),
            ]
        )
    return ok([("Hi Riya, let's go through it.", [by_kind["name"]])])


# ── what a walk is about ──────────────────────────────────────────────────────


def test_the_walk_goes_through_only_the_questions_that_need_work():
    built = walk()
    assert [c.key for c in built.chapters] == ["intro", "q2", "close"]
    intro = chapter(built, "intro")
    passed = built.of(intro, "passed")[0]
    assert "question 1" in passed.text and "question 3 on Sorting" in passed.text
    overview = built.cards["intro"]["questions"]
    assert [q["walked"] for q in overview] == [False, True, False]
    assert [q["status"] for q in overview] == ["correct", "incorrect", "correct"]


def test_a_question_chapter_carries_the_notes_own_words():
    built = walk()
    q2 = chapter(built, "q2")
    assert built.of(q2, "said")[0].data["quote"].startswith("Because the hash function gives you")
    missed = built.of(q2, "missed")
    assert len(missed) == 2
    assert missed[0].data["quote"] == "Honestly I'm not sure about the assumptions."
    assert "uniformly" in missed[0].data["fix"]
    assert "load factor" in built.of(q2, "idea")[0].text
    card = built.cards["q2"]
    assert card["missed_title"] == "What was missing or wrong"
    assert card["question"].startswith("Why is average-case lookup")
    # The notes' typography, made sayable: "≤" never reaches a voice.
    assert "≤" not in json.dumps(card, ensure_ascii=False)


def test_with_nothing_to_work_on_it_takes_the_answers_that_could_be_stronger():
    report = copy.deepcopy(REPORT)
    hashing = report["questions"][1]
    hashing.update(status="correct", status_label="Correct", went_wrong=[])
    hashing["writeup"]["gaps"] = []
    report["questions"][0]["writeup"]["gaps"] = [
        {"point": "Name the trade-off you chose", "evidence": "", "fix": "Say what it cost."}
    ]
    built = walk(report)
    assert [c.key for c in built.chapters] == ["intro", "q1", "close"]
    assert built.cards["q1"]["missed_title"] == "To make it even stronger"
    assert built.of(chapter(built, "q1"), "stronger")
    assert not built.of(chapter(built, "q1"), "idea")  # nothing to correct


def test_a_question_never_asked_is_not_talked_about():
    report = copy.deepcopy(REPORT)
    report["questions"][1]["status"] = "not_reached"
    built = walk(report)
    assert [q["index"] for q in built.cards["intro"]["questions"]] == [1, 3]


# ── the words, held to the notes ──────────────────────────────────────────────


def test_the_template_says_every_chapter_and_cites_only_its_own_facts():
    built = walk()
    script = walk_script.template_script(built, TARA)
    assert [c["key"] for c in script["chapters"]] == ["intro", "q2", "close"]
    for said, planned in zip(script["chapters"], built.chapters, strict=True):
        assert said["lines"], said["key"]
        for line in said["lines"]:
            assert line["cites"] and set(line["cites"]) <= set(planned.facts)
    q2 = " ".join(line["text"] for line in script["chapters"][1]["lines"])
    assert q2.startswith("Question 2, on Hashing.")
    assert '"Honestly I\'m not sure about the assumptions."' in q2
    assert script["chapters"][2]["lines"][-1]["text"].startswith("You've got this, Riya")


def test_a_line_citing_another_chapters_fact_or_misquoting_them_is_cut():
    built = walk()
    q2 = chapter(built, "q2")
    sources = {f.id: f.text for f in built.facts if f.id in q2.facts}
    asked = built.of(q2, "asked")[0].id
    missed = built.of(q2, "missed")[0].id
    tally = built.of(chapter(built, "intro"), "tally")[0].id
    kept, dropped = walk_script.held_to(
        {
            "lines": [
                {"text": "That was question 2.", "cites": [asked]},
                {"text": "Two of three held up.", "cites": [tally]},  # not this chapter's
                {"text": 'You said "it just needs a perfect hash".', "cites": [missed]},
                {"text": 'You said "not sure about the assumptions".', "cites": [missed]},
            ]
        },
        q2,
        sources,
    )
    assert [line["text"] for line in kept] == [
        "That was question 2.",
        'You said "not sure about the assumptions".',
    ]
    assert dropped == 2


def test_a_good_model_walk_is_kept_and_says_where_each_line_points():
    llm = ScriptedLLM(good_lines)
    script, source, reason, templated = walk_script.write(llm, walk(), TARA)
    assert (source, reason, templated) == ("model", None, [])
    assert llm.calls == ["Before we start", "Question 2", "To finish"]  # one at a time, in order
    q2 = script["chapters"][1]["lines"]
    assert q2[1]["text"] == 'You said "Honestly I\'m not sure about the assumptions."'


def test_a_chapter_that_never_says_what_fell_short_is_said_from_the_template():
    def pleasantries(title, facts, n):  # noqa: ANN001, ANN202
        asked = next((f["id"] for f in facts if f["kind"] == "asked"), facts[0]["id"])
        return ok([("Let's look at this one together.", [asked])])

    llm = ScriptedLLM(pleasantries)
    _, source, reason, templated = walk_script.write(llm, walk(), TARA, sleep=lambda _s: None)
    assert source == "mixed" and templated == ["q2"]
    assert "did not hold" in reason
    assert llm.calls.count("Question 2") == walk_script.ATTEMPTS


def test_a_rate_limit_is_waited_out_then_the_chapter_is_written():
    waited: list[float] = []

    def limited(title, facts, n):  # noqa: ANN001, ANN202
        if n == 1:
            return LLMResult(ok=False, reason="HTTP 429: Rate limit… Please try again in 2.5s.")
        return good_lines(title, facts, n)

    _, source, _, _ = walk_script.write(ScriptedLLM(limited), walk(), TARA, sleep=waited.append)
    assert source == "model" and waited == [3.5]


def test_the_daily_limit_stops_asking_and_the_rest_is_said_plainly():
    llm = ScriptedLLM(
        lambda *_: LLMResult(ok=False, reason="HTTP 429: tokens per day … try again in 19m57s")
    )
    _, source, reason, templated = walk_script.write(llm, walk(), TARA, sleep=lambda _s: None)
    assert source == "template" and templated == ["intro", "q2", "close"]
    assert len(llm.calls) == 1 and "daily limit" in reason


@pytest.mark.parametrize(
    ("reason", "wait"),
    [
        ("HTTP 429: … Please try again in 7.66s", 7.66),
        ("HTTP 429: … try again in 1m3.5s", 63.5),
        ("HTTP 429: busy", 20.0),
        ("timeout after 60s", None),
    ],
)
def test_how_long_a_rate_limit_asks_to_wait(reason, wait):
    assert walk_script.rate_wait(reason) == wait


# ── writing one ───────────────────────────────────────────────────────────────


class SlowNotes(FakeReader):
    """M06 still writing the explanations for the first two looks."""

    def __init__(self) -> None:
        super().__init__()
        self.looks = 0

    def report(self, candidate_id: str, session_id: str):
        self.looks += 1
        got = super().report(candidate_id, session_id)
        return {**got, "writeups": "pending"} if self.looks <= 2 else got


def test_the_writer_waits_for_the_notes_to_be_written(fresh_db):
    from sqlmodel import Session

    from backend_M16_Counselor import db

    reader, slept = SlowNotes(), []
    with Session(db.engine) as session:
        made = walks.start(session, RIYA, SESSION)
        done = walks.write(session, reader, NullLLM("off"), made.id, now=NOW, sleep=slept.append)
        assert done.status == "ready" and done.notes_complete
        assert reader.looks == 3 and len(slept) == 2
        assert done.stage is None


# ── the routes ────────────────────────────────────────────────────────────────


@pytest.fixture
def client():
    router_module.set_reader(FakeReader())
    set_llm(NullLLM("tests run without a model"))
    with TestClient(app) as c:
        yield c
    router_module.set_reader(None)
    set_llm(None)


def test_go_through_my_notes_writes_a_walk_and_asking_again_opens_it(client):
    url = f"/v1/counsel/candidates/{RIYA}/walkthroughs"
    first = client.post(url, json={"session_id": SESSION}, headers=student(RIYA)).json()
    # The background writer has run by the time TestClient returns.
    got = client.get(f"/v1/counsel/walkthroughs/{first['id']}", headers=student(RIYA)).json()
    assert got["status"] == "ready" and got["source"] == "template"
    assert [c["key"] for c in got["chapters"]] == ["intro", "q2", "close"]
    assert got["counselor"]["relation"] == "mentor"
    assert got["cards"]["q2"]["status"] == "incorrect"
    assert "case" not in got  # the facts stay on the server
    points = [line["points_at"] for line in got["chapters"][1]["lines"]]
    assert "missed" in points and "idea" in points
    again = client.post(url, json={"session_id": SESSION}, headers=student(RIYA)).json()
    assert again["id"] == first["id"]


def test_another_mentor_makes_their_own_walk(client):
    url = f"/v1/counsel/candidates/{RIYA}/walkthroughs"
    tara = client.post(url, json={"session_id": SESSION}, headers=student(RIYA)).json()
    client.put(
        f"/v1/counsel/candidates/{RIYA}/settings",
        json={"counselor_id": "counsel_kabir"},
        headers=student(RIYA),
    )
    kabir = client.post(url, json={"session_id": SESSION}, headers=student(RIYA)).json()
    assert kabir["id"] != tara["id"] and kabir["counselor"]["name"] == "Kabir"


def test_a_walk_is_its_students_alone(client):
    url = f"/v1/counsel/candidates/{RIYA}/walkthroughs"
    made = client.post(url, json={"session_id": SESSION}, headers=student(RIYA)).json()
    other = "11111111-2222-3333-4444-555555555555"
    got = client.get(f"/v1/counsel/walkthroughs/{made['id']}", headers=student(other))
    assert got.status_code == 403


def test_how_far_a_walk_was_heard(client):
    url = f"/v1/counsel/candidates/{RIYA}/walkthroughs"
    made = client.post(url, json={"session_id": SESSION}, headers=student(RIYA)).json()
    progress = f"/v1/counsel/walkthroughs/{made['id']}/progress"
    wrong = client.post(progress, json={"reached": "plan"}, headers=student(RIYA))
    assert wrong.status_code == 422
    client.post(progress, json={"reached": "q2"}, headers=student(RIYA))
    client.post(progress, json={"reached": "intro"}, headers=student(RIYA))  # never backwards
    done = client.post(
        progress, json={"reached": "close", "finished": True}, headers=student(RIYA)
    ).json()
    assert done["reached"] == "close" and done["watched_at"]


def test_notes_that_cannot_be_read_fail_and_say_why(client):
    router_module.set_reader(FakeReader([]))  # M06 has no such interview for them
    url = f"/v1/counsel/candidates/{RIYA}/walkthroughs"
    made = client.post(url, json={"session_id": SESSION}, headers=student(RIYA)).json()
    got = client.get(f"/v1/counsel/walkthroughs/{made['id']}", headers=student(RIYA)).json()
    assert got["status"] == "failed" and "could not be read" in got["reason"]


def test_a_walk_whose_writer_went_quiet_is_written_again():
    from datetime import timedelta

    quiet = Walkthrough(
        candidate_id=RIYA, session_id=SESSION, counselor_id="counsel_tara", stage="Question 2"
    )
    quiet.beat_at = NOW - walks.SILENT - timedelta(seconds=1)
    assert walks.lost(quiet, NOW)
    quiet.beat_at = NOW - timedelta(minutes=1)
    assert not walks.lost(quiet, NOW)


# ── what a live walk got wrong (2026-10-31) ───────────────────────────────────


def test_with_no_name_the_mentor_uses_none():
    built = notes.build(REPORT, now=NOW, name="")
    script = walk_script.template_script(built, TARA)
    said = " ".join(line["text"] for c in script["chapters"] for line in c["lines"])
    assert "there" not in said.lower().split() and ", ." not in said
    assert said.rstrip().endswith("I'll check in after the next one.")
    assert counselors.named("{name}, let's sit down.", "") == "Let's sit down."
    assert counselors.named("Go get it done, {name}.", "") == "Go get it done."


def test_a_label_from_the_notes_is_not_quoted_as_the_students_words():
    built = walk()
    q2 = chapter(built, "q2")
    sources = {f.id: f.text for f in built.facts if f.id in q2.facts}
    verdict = built.of(q2, "verdict")[0].id
    asked = built.of(q2, "asked")[0].id
    assert walk_script.misquotes('The notes say "Incorrect in a follow-up".', [verdict], sources)
    assert walk_script.misquotes('It asked "why is average-case lookup".', [asked], sources)


def test_a_resume_question_is_about_its_line_not_a_topic():
    report = copy.deepcopy(REPORT)
    hashing = report["questions"][1]
    hashing.update(concept_id="claim:abc", topic="Built a hostel complaint API with Django…")
    built = walk(report)
    asked = built.of(chapter(built, "q2"), "asked")[0]
    assert 'a line on their resume, "Built a hostel complaint API with Django…"' in asked.text
    assert built.cards["q2"]["topic"] == "" and built.cards["q2"]["resume_line"]
    focus = built.of(chapter(built, "close"), "focus")[0]
    assert focus.data["topic"].startswith('your resume line "Built a hostel')
    # Their resume is their own words: a line may quote it.
    sources = {f.id: f.text for f in built.facts}
    assert not walk_script.misquotes(
        'Your line "Built a hostel complaint API"', [asked.id], sources
    )


def test_a_line_on_what_was_missing_points_at_what_was_missing(client):
    url = f"/v1/counsel/candidates/{RIYA}/walkthroughs"
    made = client.post(url, json={"session_id": SESSION}, headers=student(RIYA)).json()
    got = client.get(f"/v1/counsel/walkthroughs/{made['id']}", headers=student(RIYA)).json()
    for line in got["chapters"][1]["lines"]:
        if line["text"].startswith("Where it fell short"):
            assert line["points_at"] == "missed"
