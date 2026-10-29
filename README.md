# M16 — Counselor

> **Someone who talks to you after your report card.** An elder brother or sister, a mum or a dad — your choice — who goes through how it went, names the one thing to fix, gives you a plan, and holds you to it next time. Honest, never harsh; warm, never flattering.
>
> Spec: [plan_in_depth/M16_Counselor.md](plan_in_depth/M16_Counselor.md) · Ports: API `8116`, web `5216` ([PORTS.txt](PORTS.txt))

```bash
git clone https://github.com/MNEMOS-PREP/Counselor
cd Counselor/Backend
python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m pytest          # no network, no API key
cd ../Frontend && npm install && cd ..
start_counselor.bat                     # API on :8116, the talks on :5216/counsel
```

## What a student gets

After every 1, 2 or 3 interviews (theirs to choose; 1 unless they say), a **talk**: a short episode, watched like a video. One face — a 3D head made from an AI-generated portrait, lip-synced to its own voice through M11 — and seven chapters:

| Chapter | What is said |
|---|---|
| Hello | a hook that proves they looked: the best moment, quoted |
| How it's going | interviews this week against *their own* goal, the next drive, last talk's promise — kept or not |
| What went well | what held up, in the student's own words |
| What didn't | the one thing to fix, quoted, honest and fixable |
| The plan | at most three steps, each with its minutes and a **Start** button into a focused mock |
| Your call | one commitment — "2 more interviews by Sunday?" — answered with a tap; the counselor says something back |
| Until next time | the counselor's own sign-off |

It starts on a cover (the face, "has something to tell you", how long), so audio begins on the student's click; every line is made by M11 while the cover is up, so nothing waits once it plays. Watch, listen or read. Today shows "Kabir has something to tell you" until it is heard, and the card floats over the notes once an interview has ended.

## The rules a talk is held to

**The code decides what is true; the model only says it** — M06's notes rule, and spec §6.2 ("the diagnosis is computed, not generated"):

1. `casefile.py` turns the interview reports (M06), the profile, mastery and trajectory (M04) and the last talk into numbered **facts**, each one plain sentence, with the student's own words where there are some.
2. `plan.py` picks at most three steps and the one ask from those facts — sized to the student's own weekly goal, never ours.
3. `script.py` has the model write the talk in the counselor's manner, and **cuts** every line that: cites no fact or one that does not exist; says a number not in what it cites; praises without content, is cruel, compares with other students, or promises an outcome nobody computed ("you'll be ready for Amazon"). A chapter left empty is filled from a template that says the same facts plainly.
4. Without a model, the whole talk is that template — same facts, same plan, same ask.

## Layout

```
Backend/backend_M16_Counselor/
  counselors.json   the four people (data): manner, greeting, sign-off, voice
  casefile.py       the facts (pure)
  plan.py           the steps and the ask (pure)
  script.py         the words, and the rules they are held to
  episodes.py       when a talk is due, and writing one
  upstreams.py      M06 and M04, read on the student's behalf
  router.py         /v1/counsel/...
  access.py         identity on the router (ai_core.guard)
Frontend/frontend_M16_Counselor/src/
  components/EpisodePlayer.tsx   the talk
  components/CounselorPicker.tsx who you'd like to talk to
  components/CounselHome.tsx     /counsel: the talk waiting, settings, talks so far
  components/CounselNudge.tsx    "… has something to tell you" (Today, notes)
```
