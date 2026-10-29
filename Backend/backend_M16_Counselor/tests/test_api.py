"""The routes, end to end, with a fake of everything M16 reads."""

from __future__ import annotations

from datetime import timedelta

import pytest
from ai_core.testing import assert_refuses_strangers
from fastapi.testclient import TestClient

from backend_M16_Counselor import router as router_module
from backend_M16_Counselor.app import app
from backend_M16_Counselor.llm import NullLLM, set_llm

from .conftest import NOW, SESSION, FakeReader, interview, student

RIYA = "e4e03be0-a233-8ea5-8342-16e914e53d92"


@pytest.fixture
def client():
    router_module.set_reader(FakeReader())
    set_llm(NullLLM("tests run without a model"))
    with TestClient(app) as c:
        yield c
    router_module.set_reader(None)
    set_llm(None)


def test_no_route_hands_one_students_talks_to_another(client):
    assert_refuses_strangers(client, app)


def test_after_an_interview_a_talk_is_written_and_ready(client):
    got = client.post(f"/v1/counsel/candidates/{RIYA}/check", headers=student(RIYA)).json()
    assert got["due"] is True
    episode = got["episode"]
    # The background writer has run by the time TestClient returns.
    talk = client.get(f"/v1/counsel/episodes/{episode['id']}", headers=student(RIYA)).json()
    assert talk["status"] == "ready"
    assert talk["counselor"]["name"] == "Tara"  # the default, until the student picks
    assert [c["key"] for c in talk["chapters"]] == [
        "hello",
        "trend",
        "well",
        "didnt",
        "plan",
        "ask",
        "bye",
    ]
    assert talk["plan"][0]["title"] == "Practise Hashing again"
    assert talk["source"] == "template"
    assert "case" not in talk  # the case file stays on the server


def test_a_talk_not_yet_heard_is_shown_again_not_made_twice(client):
    first = client.post(f"/v1/counsel/candidates/{RIYA}/check", headers=student(RIYA)).json()
    again = client.post(f"/v1/counsel/candidates/{RIYA}/check", headers=student(RIYA)).json()
    assert again["episode"]["id"] == first["episode"]["id"]
    assert (
        len(client.get(f"/v1/counsel/candidates/{RIYA}/episodes", headers=student(RIYA)).json())
        == 1
    )


def test_every_two_waits_for_a_second_interview(client):
    client.put(f"/v1/counsel/candidates/{RIYA}/settings", json={"every": 2}, headers=student(RIYA))
    got = client.post(f"/v1/counsel/candidates/{RIYA}/check", headers=student(RIYA)).json()
    assert (got["due"], got["until_next"]) == (False, 1)
    router_module.set_reader(
        FakeReader(
            [
                interview(SESSION, NOW - timedelta(minutes=30)),
                interview("second", NOW - timedelta(hours=2)),
            ]
        )
    )
    got = client.post(f"/v1/counsel/candidates/{RIYA}/check", headers=student(RIYA)).json()
    assert got["due"] is True and set(got["episode"]["sessions"]) == {SESSION, "second"}


def test_settings_refuse_what_is_not_on_offer(client):
    assert (
        client.put(
            f"/v1/counsel/candidates/{RIYA}/settings", json={"every": 5}, headers=student(RIYA)
        ).status_code
        == 422
    )
    assert (
        client.put(
            f"/v1/counsel/candidates/{RIYA}/settings",
            json={"counselor_id": "someone"},
            headers=student(RIYA),
        ).status_code
        == 422
    )
    got = client.put(
        f"/v1/counsel/candidates/{RIYA}/settings",
        json={"counselor_id": "counsel_prakash"},
        headers=student(RIYA),
    ).json()
    assert got["chosen"] is True and got["counselor_id"] == "counsel_prakash"


def test_progress_and_the_answer_to_the_ask(client):
    episode = client.post(f"/v1/counsel/candidates/{RIYA}/check", headers=student(RIYA)).json()[
        "episode"
    ]
    url = f"/v1/counsel/episodes/{episode['id']}"
    assert (
        client.post(f"{url}/answer", json={"option": "maybe"}, headers=student(RIYA)).status_code
        == 422
    )
    assert (
        client.post(f"{url}/answer", json={"option": "yes"}, headers=student(RIYA)).json()["answer"]
        == "yes"
    )
    client.post(f"{url}/progress", json={"reached": "plan"}, headers=student(RIYA))
    client.post(
        f"{url}/progress", json={"reached": "hello"}, headers=student(RIYA)
    )  # never moves back
    done = client.post(
        f"{url}/progress", json={"reached": "bye", "finished": True}, headers=student(RIYA)
    ).json()
    assert done["reached"] == "bye" and done["watched_at"] is not None


def test_without_m06_there_is_no_talk_and_it_says_why(client):
    class Down(FakeReader):
        def interviews(self, candidate_id):  # noqa: ANN001, ANN201
            return None

    router_module.set_reader(Down())
    got = client.post(f"/v1/counsel/candidates/{RIYA}/check", headers=student(RIYA)).json()
    assert got["due"] is False and got["reason"] == "M06 is not answering"


def test_the_counselors_are_four_with_one_default(client):
    people = client.get("/v1/counsel/counselors").json()
    assert {p["relation"] for p in people} == {"elder brother", "elder sister", "mum", "dad"}
    assert sum(p["default"] for p in people) == 1
