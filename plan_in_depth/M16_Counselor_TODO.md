# M16 — TODO · Counselor, Study Plan & Readiness Forecast

> **Completion: 0%** — 0 of 19 functional requirements met. **No repository.** The spec is written and, for several modules, reviewed; nothing is built. The requirement count is the spec's own, so this is a measure of scope ahead rather than of progress behind.
>
> _Method: `(met + ½ × partial) ÷ total`, counted from the spec, 2026-08-28. One measure applied the same way to all nineteen modules so they compare; it counts requirements, not screens or gates._

Task list for taking **M16 — Counselor, Study Plan & Readiness Forecast** to 100% of [M16_Counselor.md](M16_Counselor.md).

> **This is the branch that holds the plan.** The `todo` branch carries the
> spec and this list and nothing else, so the module's own history stays
> about its code. Sync it here when something lands.

> **Read this first when starting a session on M16.** It is the running state of
> the module: what is done, what is next, and what is deliberately deferred.
> Update it as things land — a stale list is worse than no list, because the
> next session trusts it.

- **Repo:** `Counselor`

Legend: ✅ done · 🟡 partly done · ⬜ not started

---

## 0. Ideas and scouting

Things worth building that did not come from the spec — usually from reading
somebody else's implementation. **New ideas go at the top of this section.**

The rule we keep arriving at: borrow a **technique**, not a **component**. The
platform's contracts — character offsets, per-fact provenance, permanent
evidence — are more demanding than general-purpose tools assume, so integration
usually costs more than reimplementing the one idea we actually wanted.

_Nothing scouted for this module yet._

---

## 1. Where the module stands

| | |
|---|---|
| Status | **Not started.** No code exists — no backend, no frontend, no tests. |
| Spec | Written, and the source of every row below. |
| Scope | 19 functional requirements (14 of them P0), 12 acceptance metrics (4 release-blocking), 15 edge cases. |

Everything below is ⬜ because nothing is built. That is the honest state and
it is worth writing down rather than leaving three sections saying
_To fill in._ — the point of this list is that the next session can start from
it instead of re-reading a six-hundred-line spec.

---

## 2. Functional requirements

Spec §4, verbatim. This is the authoritative list.

| FR | | Priority |
|---|---|---|
| FR-16.1 | ⬜ Compute diagnosis deterministically; model only phrases it | P0 |
| FR-16.2 | ⬜ Every claim carries an evidence reference (session, turn, quote) | P0 |
| FR-16.3 | ⬜ At most 3 actions; exactly 1 primary | P0 |
| FR-16.4 | ⬜ Always include a "what's working" element | P0 |
| FR-16.5 | ⬜ Plateau and regression detection with minimum-evidence gates | P0 |
| FR-16.6 | ⬜ Prerequisite bottleneck identification with a foundational floor | P0 |
| FR-16.7 | ⬜ Cross-modal diagnosis: knowledge vs articulation vs composure | P0 |
| FR-16.8 | ⬜ Adherence tracking; unmet commitments named without judgement | P0 |
| FR-16.9 | ⬜ Study plan backward-planned from drive dates | P0 |
| FR-16.10 | ⬜ Triage mode when time-to-drive is short | P0 |
| FR-16.11 | ⬜ Spaced repetition via FSRS, injected as real interview questions | P1 |
| FR-16.12 | ⬜ Interleaved rather than blocked practice, with an explanation | P1 |
| FR-16.13 | ⬜ Readiness forecast as a range with a confidence band | P1 |
| FR-16.14 | ⬜ Suppress the forecast until validated against outcomes | P0 |
| FR-16.15 | ⬜ Weekly nudge, capped, user-controlled, silent when active | P1 |
| FR-16.16 | ⬜ Rejection-recovery mode with a delay before analysis | P1 |
| FR-16.17 | ⬜ Never diagnose mental health; escalate to institute counselling | P0 |
| FR-16.18 | ⬜ Version-scoped longitudinal comparisons | P0 |
| FR-16.19 | ⬜ Honest low-data state (n < 5 sessions) | P0 |

---

## 3. Acceptance gates

Spec §13. A **[GATE]** is release-blocking; the rest are tracked.

| AC | | Target |
|---|---|---|
| AC-16.1 **[GATE]** | ⬜ Every diagnosis claim maps to a computed finding with evidence | 100% |
| AC-16.2 **[GATE]** | ⬜ No forecast date shown before validation | render-time gate |
| AC-16.3 **[GATE]** | ⬜ No clinical/mental-health language | tone audit, zero tolerance |
| AC-16.4 **[GATE]** | ⬜ Actions ≤ 3, exactly 1 primary | 100% |
| AC-16.5 | ⬜ Golden-diagnosis accuracy | ≥ 13/15 |
| AC-16.6 | ⬜ Faculty "would a mentor say this" rating | ≥ 4.0/5 |
| AC-16.7 | ⬜ Plateau/regression false-positive rate (manual review) | < 10% |
| AC-16.8 | ⬜ Plan adherence (items completed within 7 days of due) | ≥ 45% |
| AC-16.9 | ⬜ Students who act on the primary action within 48 h | ≥ 35% |
| AC-16.10 | ⬜ Weekly nudge open rate | ≥ 40% |
| AC-16.11 | ⬜ Return rate at 14 days (with Counselor vs without, A/B) | +15 points |
| AC-16.12 | ⬜ Forecast calibration (Phase 4): actual vs predicted ready date | within the p10–p90 band ≥ 80% |

---

## 4. Edge cases

Spec §12. Listed in full, because several are one afternoon each and are the
difference between a demo and a product.

| EC | | Expected behaviour |
|---|---|---|
| EC-16.1 | ⬜ Fewer than 5 sessions | `insufficient` state; broad diagnostic suggested; no trends claimed |
| EC-16.2 | ⬜ All scores flat but only 3 sessions | No plateau claim (min evidence not met) |
| EC-16.3 | ⬜ Student improves everywhere | "What's working" leads; actions become stretch/ceiling-finding |
| EC-16.4 | ⬜ Rubric version changed mid-history | Comparisons version-scoped; chart marks the boundary; re-scored where possible |
| EC-16.5 | ⬜ No drive dates known | Horizon defaults to 42 days, `build` mode |
| EC-16.6 | ⬜ Drive tomorrow | Triage: format familiarity + confidence priming only. **No new content.** |
| EC-16.7 | ⬜ Student ignores every plan item for 3 weeks | Ask, don't nag: "Is the plan wrong, or is life busy? Both are fine — want a lighter one?" |
| EC-16.8 | ⬜ Student says they practised elsewhere | Recorded; adherence adjusted; suggest a quick re-test to update the graph |
| EC-16.9 | ⬜ Bottleneck walk returns a foundational concept | Suppressed; next-best bottleneck used |
| EC-16.10 | ⬜ Two bottlenecks equally weighted | Pick the one with fewer estimated hours; mention the other exists |
| EC-16.11 | ⬜ Distress detected in free text | §6.8 path; no diagnosis, no escalation without consent |
| EC-16.12 | ⬜ Rejection recorded | 48-hour quiet, then gentle specificity |
| EC-16.13 | ⬜ Student disputes the diagnosis | Recorded; a re-test scheduled to resolve it with data |
| EC-16.14 | ⬜ Forecast says ready *after* the drive | Stated plainly with what's achievable, never softened into false hope |
| EC-16.15 | ⬜ Student has 6 target companies with different bars | Per-target readiness; the plan optimises for the nearest drive first |

---

## 5. Data model

Spec §5 declares 10 types. None exist.

| Type | | |
|---|---|---|
| `TrajectoryPoint` | ⬜ | Not written |
| `Trend` | ⬜ | Not written |
| `Changepoint` | ⬜ | Not written |
| `Bottleneck` | ⬜ | Not written |
| `DiagnosisKind` | ⬜ | Not written |
| `Action` | ⬜ | Not written |
| `Diagnosis` | ⬜ | Not written |
| `PlanItem` | ⬜ | Not written |
| `StudyPlan` | ⬜ | Not written |
| `ReadinessForecast` | ⬜ | Not written |

---

## 6. Deferred — inter-module

Not gaps in this module. Each needs a module that is not built or not wired
yet, and each is listed so it is not mistaken for an oversight.

The spec names **M10, M12, M13, M15, M17, M19**. Until those are wired, anything
depending on them is blocked rather than unstarted, and the distinction
matters: one is work waiting to be done and the other is work that cannot
begin.

---

## 7. First moves

When work begins, the order that has worked on M01 and M02:

1. **The manifest and the ports.** `module.json` with `depends_on` declaring
   every upstream as OPTIONAL, each with an `on_missing` sentence a student
   can act on. Rule 2: a missing dependency narrows scope, never quality, and
   never silently.
2. **Identity before endpoints.** Router-level `enforce_access` on
   `ai_core.identity`, so no route can be written without it. A per-route
   check is the one somebody omits on the sixteenth endpoint, and the
   sixteenth endpoint is the one that leaks.
3. **The P0 that carries the module's name**, not the easiest one.
4. **Contract gates from the first commit** — every route has a client, every
   hook has a screen, every response field is declared on the frontend. M01
   shipped ten routes nobody could reach before these existed.
5. **A golden corpus before the third extraction fix**, not after. On M02 it
   found four real bugs within an hour of existing.

