# M16 — Counselor, Study Plan & Readiness Forecast

> **Master plan reference:** §42 · **Phase:** 4 · **Owner:** E3 · **Depends on:** M4 (history), M13 (comparable scores), M5 (drills) · **Feeds:** M19
> **The crown jewel: the only module that requires history, which makes it the retention engine and the switching cost.**

---

## 1. In one paragraph

Everything else in the platform measures. This one *decides what to do about it*. It reads the whole longitudinal record — mastery trajectories, break points, delivery trends, failure signatures, plan adherence, drive dates — and produces at most three actions, each grounded in a specific thing the student did on a specific day. It detects plateaus and regressions, walks the prerequisite graph to find the real bottleneck (your DP problem is a recursion problem), tells apart three failure modes that need completely different fixes (don't know it / can't say it / falls apart under pressure), forecasts a readiness date with an honest confidence band, and builds a study plan that fits the actual calendar. It is also the module most likely to be worthless if built lazily, because generic advice is instantly recognisable and instantly ignored.

---

## 2. Reverse-thinking: the user

### 2.1 The single sentence that defines success

> *"How did it know that?"*

Every design decision below serves that reaction. The opposite reaction — *"this is just ChatGPT telling me to practise more"* — is the failure state, and it's the default outcome of a lazy implementation.

### 2.2 Generic vs specific, concretely

| ❌ What kills it | ✅ What earns the sentence |
|---|---|
| "Focus on improving your DSA skills." | "Your DP is stuck because your recursion is. You broke at depth 1 on recursion in three sessions — 12 Jun, 28 Jun, 4 Jul." |
| "Work on your communication." | "You know the answers. On 6 of your last 9 technical questions you were right but took 40+ seconds to start. That reads as uncertainty even when you're correct." |
| "Practise more mock interviews." | "You've done 8 mocks and 0 aptitude sections. Zoho's first round is a 3-hour written test. That's your gap, not DSA." |
| "You're improving!" | "Your DP score went 1.8 → 2.4 → 2.9 over five weeks. At that rate you clear the bar around 20 August. Your drive is the 14th — tight but doable if you do the Tuesday and Thursday drills." |

### 2.3 The screen

```
┌────────────────────────────────────────────────────────────────┐
│  Where you are                          updated after session 9│
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  You're 3 weeks from ready for the companies you've       │  │
│  │  targeted. One thing is holding everything up.            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│  THE BOTTLENECK                                                │
│  Recursion. It's blocking DP, backtracking, and trees —        │
│  three of the five topics you're weak on. You've broken at     │
│  depth 1 on it in three sessions:                              │
│    12 Jun  "I'd just call the function again"            ▶     │
│    28 Jun  "the base case is... when it stops?"          ▶     │
│    4 Jul   "I know it recurses but I lose track"         ▶     │
│                                                                │
│  Fixing this likely moves all three at once.                   │
│  [ Start here — recursion, 40 min ]                            │
│                                                                │
│  ALSO WORTH DOING (2)                                          │
│  · Your answers are right but slow to start (avg 38s).         │
│    [ 10-min drill: buying thinking time out loud ]             │
│  · You've never done an aptitude section. Zoho's round 1       │
│    is one. [ Take one, 25 min ]                                │
│                                                                │
│  WHAT'S WORKING                                                │
│  Your project explanations went from 2.1 to 3.4. Whatever      │
│  you changed after 20 June, keep doing it.                     │
│                                                                │
│  ── Your trajectory ──────────────────────────────────────     │
│  [ chart: readiness over time with a projected band ]          │
│  Projected ready:  18–26 Aug   (drive: 14 Aug ⚠)               │
└────────────────────────────────────────────────────────────────┘
```

**Design decisions:**
- **Exactly one primary action.** The "also worth doing" list is capped at two and visually secondary.
- **Every claim quotes a date and the student's own words**, with playback. This is what produces "how did it know that".
- **"What's working" is mandatory.** A diagnosis with no positive is demoralising and — more practically — students stop opening it.
- **The forecast is a range with the drive date overlaid**, so the implication is obvious without us stating it dramatically.

### 2.4 The tone rules

| Situation | Wrong | Right |
|---|---|---|
| Far from ready, drive in 3 days | "You are not ready." | "Three days is tight for the full gap. Here's the highest-leverage thing you can do tonight, and here's what to do if this one doesn't land." |
| Plateau for 4 weeks | "You've stopped improving." | "Your scores have been flat for four weeks. Usually that means the practice has stopped being hard enough — let's change what you're doing, not how much." |
| Rejected from a drive | "Better luck next time!" | "That's a rough one. When you're ready — not now — there are two things from that interview worth looking at. No rush." |
| Doing well | "Great job!" | "You've cleared the bar for 4 of your 6 target companies. The remaining two want system design, which you haven't practised." |

**No toxic positivity, no cruelty.** The register is a good senior who respects you enough to be straight.

### 2.5 The nudge (this is where retention actually happens)

A weekly message, and it must be worth opening:

```
  Sunday, 7 p.m.

  Two things this week.

  You said you'd do the recursion drill on Tuesday. You didn't —
  no judgement, but it's still the thing blocking DP.

  Also: Cognizant opened on the portal, drive on the 28th. Their
  round 1 is aptitude-heavy and you haven't done one yet.

  20 minutes tonight would move both.
  [ Recursion drill ]  [ Aptitude section ]
```

Specific, short, two actions maximum, and it references a commitment *they* made. Frequency is capped and user-controlled, and it goes quiet automatically when the student is clearly active.

---

## 3. Reverse-thinking: the developer

### 3.1 The seven traps

**Trap 1 — Handing the whole history to a model and asking for advice.** You get fluent, generic, unfalsifiable coaching that references nothing. *Counter: the diagnosis is **computed** (changepoint detection, graph walks, threshold rules); the model only phrases what the computation found, and every claim carries an evidence reference (§6.2).*

**Trap 2 — Comparing scores across rubric versions.** Every "you improved 30%" becomes fiction the moment the rubric changes. *Counter: version-scoped queries + batch re-score, inherited from M13/M4 (§6.7).*

**Trap 3 — Firing plateau/regression alerts on noise.** Three sessions is not a trend. A false "you're getting worse" is actively harmful. *Counter: minimum evidence thresholds + changepoint detection with a significance requirement + a cooldown between alerts of the same type (§6.3).*

**Trap 4 — Confusing three different problems.** "Weak at DP" could be: doesn't know it, knows it but can't articulate it, or knows it until the clock starts. Same symptom, three completely different interventions. *Counter: explicit cross-modal diagnosis (§6.4). This is the module's highest-value logic.*

**Trap 5 — Forecasting without honesty.** Extrapolating a line through 4 points and printing a date is fortune-telling. *Counter: Bayesian hierarchical model with partial pooling, always rendered as a range, and **suppressed entirely** until validated against real outcomes (§6.6).*

**Trap 6 — Plans that ignore the calendar.** A 6-week plan for a student whose drive is in 9 days is worse than useless. *Counter: backward planning from the drive date, with an explicit triage mode when time is short (§6.5).*

**Trap 7 — Advice that ignores whether the last advice was taken.** Repeating an ignored recommendation makes the system look deaf. *Counter: adherence is a first-class input; unmet commitments are named, and repeated non-adherence changes the *kind* of suggestion, not just the volume.*

### 3.2 The non-obvious hard parts

1. **You need ~5 sessions before anything here works.** Design the n<5 state deliberately: the Counselor should say "I need a bit more to see a pattern — here's what I'd check next" rather than fabricating a diagnosis.
2. **Adherence data is sparse and biased.** Students do things outside the platform. Never assume non-adherence means idleness; ask ("did you work on this elsewhere?") rather than accuse.
3. **The bottleneck walk can return something useless.** If the earliest unmastered prerequisite is "variables", the advice is insulting. Cap the walk at concepts above a foundational threshold and sanity-check the output.
4. **Emotional safety has hard edges.** A student who writes something distressing in a free-text field must be met with a human path, not a chatbot. This needs to be designed before launch, not after an incident.
5. **The bandit needs volume.** Contextual bandits over "which advice works" need hundreds of observations before they beat a sensible heuristic. Ship the heuristic; log for the bandit; switch when the data justifies it.

---

## 4. Functional requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-16.1 | Compute diagnosis deterministically; model only phrases it | P0 |
| FR-16.2 | Every claim carries an evidence reference (session, turn, quote) | P0 |
| FR-16.3 | At most 3 actions; exactly 1 primary | P0 |
| FR-16.4 | Always include a "what's working" element | P0 |
| FR-16.5 | Plateau and regression detection with minimum-evidence gates | P0 |
| FR-16.6 | Prerequisite bottleneck identification with a foundational floor | P0 |
| FR-16.7 | Cross-modal diagnosis: knowledge vs articulation vs composure | P0 |
| FR-16.8 | Adherence tracking; unmet commitments named without judgement | P0 |
| FR-16.9 | Study plan backward-planned from drive dates | P0 |
| FR-16.10 | Triage mode when time-to-drive is short | P0 |
| FR-16.11 | Spaced repetition via FSRS, injected as real interview questions | P1 |
| FR-16.12 | Interleaved rather than blocked practice, with an explanation | P1 |
| FR-16.13 | Readiness forecast as a range with a confidence band | P1 |
| FR-16.14 | Suppress the forecast until validated against outcomes | P0 |
| FR-16.15 | Weekly nudge, capped, user-controlled, silent when active | P1 |
| FR-16.16 | Rejection-recovery mode with a delay before analysis | P1 |
| FR-16.17 | Never diagnose mental health; escalate to institute counselling | P0 |
| FR-16.18 | Version-scoped longitudinal comparisons | P0 |
| FR-16.19 | Honest low-data state (n < 5 sessions) | P0 |

---

## 5. Data contracts

```python
class TrajectoryPoint(BaseModel):
    concept_id: str
    session_id: UUID
    at: datetime
    score: float
    rubric_version: str
    n_items: int

class Trend(BaseModel):
    concept_id: str
    slope: float                   # per week
    r2: float
    n_points: int
    changepoints: list[Changepoint]
    state: Literal["improving","plateau","regressing","insufficient_data","volatile"]
    confidence: float

class Changepoint(BaseModel):
    at: datetime
    direction: Literal["up","down"]
    magnitude: float
    p_value: float
    possible_cause: str | None     # "you changed how you answer project questions"

class Bottleneck(BaseModel):
    concept_id: str
    blocks: list[str]              # concept_ids downstream that are weak
    blocks_count: int
    mastery: float | None
    evidence: list[EvidenceRef]    # break points, quoted
    estimated_hours_to_close: float

class DiagnosisKind(BaseModel):
    kind: Literal["knowledge_gap","articulation_gap","composure_gap",
                  "coverage_gap","strategy_gap","plateau","regression"]
    concept_ids: list[str]
    evidence: list[EvidenceRef]
    confidence: float
    reasoning_trace: str           # HOW we concluded this — internal, auditable

class Action(BaseModel):
    id: UUID
    rank: Literal["primary","secondary"]
    title: str                     # "Start here — recursion, 40 min"
    why: str                       # grounded, with evidence
    evidence: list[EvidenceRef]
    deep_link: str                 # runs something; NEVER "study more"
    estimated_minutes: int
    addresses: list[str]           # diagnosis kinds
    generated_at: datetime

class Diagnosis(BaseModel):
    id: UUID
    candidate_id: UUID
    kinds: list[DiagnosisKind]
    bottleneck: Bottleneck | None
    whats_working: PositiveFinding
    actions: list[Action]          # ≤3, exactly one primary
    data_sufficiency: Literal["rich","adequate","thin","insufficient"]
    generated_at: datetime

class PlanItem(BaseModel):
    id: UUID
    concept_ids: list[str]
    kind: Literal["drill","mock","oa_section","reading","gd","review"]
    deep_link: str
    estimated_minutes: int
    due_at: datetime
    scheduled_because: str         # "prerequisite of DP" / "spaced review"
    status: Literal["pending","done","skipped","overdue"]
    completed_at: datetime | None

class StudyPlan(BaseModel):
    id: UUID
    candidate_id: UUID
    horizon_days: int
    target_drives: list[DriveTarget]
    items: list[PlanItem]
    weekly_minutes_available: int  # student-stated
    mode: Literal["build","triage","maintain"]
    adherence_rate: float
    generated_at: datetime

class ReadinessForecast(BaseModel):
    candidate_id: UUID
    target: str                    # company or archetype
    current: float
    bar: float
    ready_date_p50: date | None
    ready_date_p10: date | None
    ready_date_p90: date | None
    displayable: bool              # FR-16.14 gate
    suppression_reason: str | None
    model_version: str
```

---

## 6. The pipeline in minute detail

### 6.1 Inputs
Full mastery posteriors + trajectories (M4) · per-session evaluations with evidence (M13) · delivery trends (M12) · failure signatures (M4 §30.4) · break-point history · plan adherence · target companies and their bars (M15) · drive calendar · student-stated available hours.

### 6.2 The diagnosis is computed, not generated

```python
def diagnose(candidate) -> Diagnosis:
    trends      = compute_trends(candidate)              # §6.3
    bottleneck  = find_bottleneck(candidate)             # §6.4a
    kinds       = []
    kinds += detect_knowledge_gaps(candidate, trends)
    kinds += detect_articulation_gaps(candidate)         # §6.4b
    kinds += detect_composure_gaps(candidate)            # §6.4c
    kinds += detect_coverage_gaps(candidate)             # never did an OA, etc.
    kinds += detect_strategy_gaps(candidate)             # from M10 time analysis
    kinds += [k for k in trend_alerts(trends)]           # plateau / regression

    kinds = rank_by_leverage(kinds)                      # §6.4d
    positive = find_whats_working(trends)                # REQUIRED

    actions = [action_for(k) for k in kinds[:3]]
    # ONLY NOW does a model get involved: phrasing, not deciding
    return phrase(Diagnosis(kinds=kinds, bottleneck=bottleneck,
                            whats_working=positive, actions=actions))
```

The `phrase()` step receives the computed findings **plus the evidence quotes** and produces the student-facing wording. It is explicitly instructed that it may not add findings, and a post-check asserts every sentence maps to a finding. Same fact-link discipline as M15.

### 6.3 Trend, plateau, and regression detection

```python
# Minimum evidence before ANY trend claim
if n_points < 4 or span_days < 14: return "insufficient_data"

# Fit the learning curve (power law of practice)
#   score ≈ a - b · n^(-c)
fit = curve_fit(power_law, n_practice, scores)
slope_recent = derivative at the last point

# Changepoints
cps = pelt_changepoints(scores, penalty=tuned_on_holdout)
significant = [cp for cp in cps if p_value(cp) < 0.05 and |magnitude| > 0.4]

state = "regressing" if any significant down-changepoint in the last 21 days
        "plateau"    if |slope_recent| < 0.05/week AND practice_volume ≥ 3
                        sessions in the window AND span ≥ 28 days
        "volatile"   if residual variance > threshold (don't call a trend)
        "improving"  if slope_recent > 0.1/week
```

**Alert cooldown:** the same alert type fires at most once per 21 days per concept. Nagging destroys credibility.

**Plateau requires practice volume.** A student who did nothing for a month has not plateaued — they've been busy. The copy differs: *"You haven't practised DP since June — worth a refresh"* vs *"You've practised DP four times and the score hasn't moved — let's change the approach."*

### 6.4 The four diagnostic engines

**(a) Bottleneck walk**
```sql
-- from M4 §30.8, with a foundational floor
WHERE concept.level != 'foundational'          -- don't tell them to learn variables
  AND blocks_count >= 2                        -- must actually unblock something
  AND (mastery IS NULL OR mastery < 0.45)
ORDER BY blocks_count DESC, mastery ASC
```
Sanity check: if the top bottleneck has `blocks_count < 2`, report no bottleneck rather than a weak one.

**(b) Articulation gap — knows it but can't say it**
```
signals (need ≥2):
  hint_lift high        : one hint moves them from wrong to right ≥60% of the time
  break_depth deep      : reaches L3+ before failing (understands, loses the thread)
  delivery poor         : structure score low, ramble detector firing, TTFT high
  code-vs-talk gap      : coding correctness high, verbal explanation score low
→ intervention: M17 communication drills, NOT more DSA
```
This diagnosis is enormously valuable and almost nobody makes it. A student told to "practise more DP" when their DP is fine but unspeakable will practise for a month and not improve.

**(c) Composure gap — falls apart under pressure**
```
fragility = mean_score(practice mode, matched difficulty)
          - mean_score(final_boss / real_drive mode, matched difficulty)
signals: fragility > 0.8 levels
         TTFT increases > 60% under timer
         disfluency rate increases > 50% under timer
         accuracy drops on items they solved untimed
→ intervention: graded exposure — timed drills at increasing pressure,
                NOT more content
```

**(d) Leverage ranking**
```
leverage = (concepts_unblocked × weight_in_target_roles)
         / estimated_hours_to_close
         × urgency(days_to_nearest_drive)
         × (1 - recently_recommended_and_ignored × 0.5)
```
The last factor prevents repeating ignored advice at full volume; instead the *kind* of suggestion changes (a 10-minute drill instead of a 40-minute one, or a different framing).

### 6.5 Study plan generation

```
1. Horizon = min(next drive date, 42 days)
2. Mode:
     days_to_drive > 21   → build   (fix root causes)
     7–21                 → focused (bottleneck + format familiarity)
     < 7                  → triage  (highest-EV only; explicitly say so)
3. Capacity = student-stated weekly minutes (asked once, adjustable)
4. Order by prerequisite topology, then leverage
5. INTERLEAVE: no more than 2 consecutive items on the same concept —
   with a one-line explanation, because it feels random otherwise:
   "I'm mixing topics on purpose — it's harder now and sticks better."
6. Inject FSRS reviews (§6.6) as real interview questions, not flashcards
7. Backward-schedule from the drive: format familiarity in the final 3 days,
   never new content
8. Every item is a DEEP LINK that runs something
```

**Triage mode copy is different and it matters:**
> *"Your drive is in 4 days. We're not fixing recursion properly in 4 days, so we're not going to try. Here's the highest-value thing: their round 1 is aptitude, you've never done one, and that's where people get cut. Do two sections. Then one mock in their format. That's it."*

Honest, decisive, and far more useful than a 6-week plan compressed into 4 days.

### 6.6 Spaced repetition (FSRS)
State per `(candidate, concept)`: `{stability, difficulty, due_at}`. Updated on every scored observation. Reviews are injected into the *next mock* as genuine interview questions — retrieval practice in the target format, not flashcards. Chosen over SM-2 because FSRS fits real review data better and has a clean open implementation.

### 6.7 Readiness forecast

```
Bayesian hierarchical growth model:
  score_ij ~ Normal(a_i - b_i · n_ij^(-c), σ)
  a_i, b_i, c ~ population priors (partial pooling across the cohort)
  → a student with 4 sessions borrows strength from the cohort instead of
    extrapolating nonsense from 4 points

ready_date = first date where P(score ≥ bar) > 0.5, given planned practice volume
report p10 / p50 / p90 as a RANGE
```

**Display gate (FR-16.14):**
```
displayable = (n_sessions ≥ 6)
            AND (rubric versions compatible across the window)
            AND (forecast_validated == True)   # Phase 4, against real outcomes
```
Until validated, the chart is labelled **"practice trajectory"** and no date is shown. We do not ship a prediction we have not measured. When validation lands (Paper 3 / pilot), the label changes and the date appears.

### 6.8 Emotional safety [design this before launch]

```
Free-text inputs (dispute notes, reflections, chat with the Counselor) pass a
distress classifier (cheap tier + keyword safety net).

On trigger:
  → the Counselor does NOT attempt support beyond warmth and acknowledgement
  → it surfaces: institute counselling contact, a student helpline, and
    "would you like me to pause reminders for a while?"
  → it NEVER uses clinical language, never diagnoses, never says
    "you seem depressed"
  → nothing is escalated to staff without the student's explicit choice
  → the event is logged as a counter only (no content) for safety review
```
Reviewed and signed off by the faculty advisor before the pilot. This is not optional and it is not a Phase-4 item.

**Rejection-recovery mode:** when a `rejected` outcome is recorded, the Counselor goes quiet for 48 hours. Then:
> *"About the Zoho drive — whenever you want, there are two things from that interview worth looking at. No rush, and it doesn't change anything about where you're headed."*

Delay, then specificity, then agency. Not a same-day post-mortem.

### 6.9 The bandit (later)
Log `(context, action, adherence, measured_improvement)` from day one. Once ≥500 tuples exist, LinUCB over action features selects among equally-ranked actions. Until then, the heuristic in §6.4d decides. **Logging from day one is the requirement; the bandit itself is optional.**

---

## 7. API surface

```
GET  /v1/counselor/{candidate_id}/diagnosis        latest, with evidence
POST /v1/counselor/{candidate_id}/diagnose         force regeneration
GET  /v1/counselor/{candidate_id}/trends?concept=
GET  /v1/counselor/{candidate_id}/bottlenecks
GET  /v1/plans/current
POST /v1/plans                                     {horizon, capacity, targets}
PATCH /v1/plans/items/{id}                         mark done/skipped
POST /v1/plans/items/{id}/snooze
GET  /v1/readiness/{candidate_id}?target=
GET  /v1/reviews/due                               FSRS queue
POST /v1/counselor/{candidate_id}/reflect          free-text check-in
GET  /v1/nudges/settings   PATCH /v1/nudges/settings
```

---

## 8. UI specification

**Components:** `DiagnosisCard` · `BottleneckCard` (with evidence quotes + playback) · `ActionCard` (primary vs secondary styling) · `WhatsWorkingCard` · `TrajectoryChart` (with rubric-version markers and a projection band) · `PlanCalendar` · `PlanItem` (with "why this?" expander) · `AdherenceStrip` · `NudgeSettings` · `TriageBanner` · `SupportCard`

**States:**

| State | Treatment |
|---|---|
| `insufficient` (< 5 sessions) | "I need a couple more sessions to see your pattern. Here's what I'd check next: [broad diagnostic mock]" — honest, with a useful action |
| `thin` | One action only; no forecast; explicit "based on 5 sessions" |
| `triage` | Amber banner, reduced plan, different copy register |
| Forecast unvalidated | Chart labelled "practice trajectory", no date |
| Regression detected | Neutral framing + a specific check, never alarm |

**Evidence playback everywhere.** Every quoted moment has a ▶ that plays 8 seconds of their own audio. This is the mechanism that makes the whole module credible.

**"Why this?" on every plan item** — one sentence, e.g. *"prerequisite of DP, which you're weak on"* or *"spaced review — you last got this right 18 days ago"*. Without it, a plan feels arbitrary and adherence collapses.

**Accessibility:** the trajectory chart has a data table; all audio clips have transcripts; the diagnosis is fully readable as linear text.

---

## 9. Edge cases

| ID | Case | Behaviour |
|---|---|---|
| EC-16.1 | Fewer than 5 sessions | `insufficient` state; broad diagnostic suggested; no trends claimed |
| EC-16.2 | All scores flat but only 3 sessions | No plateau claim (min evidence not met) |
| EC-16.3 | Student improves everywhere | "What's working" leads; actions become stretch/ceiling-finding |
| EC-16.4 | Rubric version changed mid-history | Comparisons version-scoped; chart marks the boundary; re-scored where possible |
| EC-16.5 | No drive dates known | Horizon defaults to 42 days, `build` mode |
| EC-16.6 | Drive tomorrow | Triage: format familiarity + confidence priming only. **No new content.** |
| EC-16.7 | Student ignores every plan item for 3 weeks | Ask, don't nag: "Is the plan wrong, or is life busy? Both are fine — want a lighter one?" |
| EC-16.8 | Student says they practised elsewhere | Recorded; adherence adjusted; suggest a quick re-test to update the graph |
| EC-16.9 | Bottleneck walk returns a foundational concept | Suppressed; next-best bottleneck used |
| EC-16.10 | Two bottlenecks equally weighted | Pick the one with fewer estimated hours; mention the other exists |
| EC-16.11 | Distress detected in free text | §6.8 path; no diagnosis, no escalation without consent |
| EC-16.12 | Rejection recorded | 48-hour quiet, then gentle specificity |
| EC-16.13 | Student disputes the diagnosis | Recorded; a re-test scheduled to resolve it with data |
| EC-16.14 | Forecast says ready *after* the drive | Stated plainly with what's achievable, never softened into false hope |
| EC-16.15 | Student has 6 target companies with different bars | Per-target readiness; the plan optimises for the nearest drive first |

---

## 10. Failure modes & fallbacks

| Failure | Fallback | User sees |
|---|---|---|
| Trend fitting fails | Report raw last-3-session direction only | Coarser trend language |
| Bottleneck query fails | Rank by mastery × weight instead of graph position | A weaker but valid recommendation |
| Phrasing model fails | Render the computed findings as a structured list | Less warm, fully accurate |
| Forecast model fails | Suppress the forecast block | "Trajectory shown; no date estimate right now" |
| FSRS state corrupt | Rebuild from observations | Nothing |
| Evidence artifact expired | Claim retained with "evidence no longer available" | Honest note instead of a broken ▶ |

Note the phrasing fallback: **the computation is the product; the prose is the polish.** If the model is down, the module still works.

---

## 11. Performance & cost budget

| Operation | p95 | Cost |
|---|---|---|
| Trend computation (all concepts) | 600 ms | — |
| Bottleneck walk | 150 ms | — |
| Diagnosis engines (deterministic) | 400 ms | — |
| Phrasing (frontier tier — judgement matters) | 12 s | ₹1.4 |
| Plan generation | 3 s | ₹0.5 |
| Weekly nudge composition | 4 s | ₹0.3 |
| Forecast fit (batch, nightly, cohort-wide) | 4 min | — |
| **Per diagnosis** | **~16 s** | **≈ ₹2** |

Runs post-session and weekly, not per turn. Cheap relative to its retention value.

---

## 12. Test plan

**Unit** — plateau detection on synthetic series (flat-with-practice = plateau; flat-without = not) · changepoint significance · bottleneck foundational floor · leverage ranking · triage-mode switching at day thresholds · adherence-aware down-weighting.

**Golden diagnoses** — 15 synthetic student histories with known ground-truth problems (a pure articulation-gap student, a pure composure-gap student, a plateau student, a coverage-gap student…). Assert the correct `DiagnosisKind` is top-ranked for each. **This is the module's core correctness test** and it catches the "everything looks like a knowledge gap" failure.

**Grounding check [GATE]** — for 50 generated diagnoses, assert every sentence maps to a computed finding and every quoted evidence resolves. Zero tolerance.

**Human review** — a faculty member reads 20 diagnoses and rates "would a good mentor say this?" on 1–5. **Target ≥ 4.0.** Run once per phase.

**Tone audit** — a second reviewer checks the same 20 for: toxic positivity, judgement, vagueness, and any clinical language. Any clinical language is a P0.

**Manual QA** (12 min): create a test student with a seeded articulation-gap history → confirm the diagnosis names articulation, not knowledge → check every quote plays → mark a plan item skipped and confirm next week's nudge references it → seed a rejection and confirm the 48-hour quiet.

---

## 13. Metrics & acceptance gates

| ID | Metric | Target |
|---|---|---|
| AC-16.1 **[GATE]** | Every diagnosis claim maps to a computed finding with evidence | 100% |
| AC-16.2 **[GATE]** | No forecast date shown before validation | render-time gate |
| AC-16.3 **[GATE]** | No clinical/mental-health language | tone audit, zero tolerance |
| AC-16.4 **[GATE]** | Actions ≤ 3, exactly 1 primary | 100% |
| AC-16.5 | Golden-diagnosis accuracy | ≥ 13/15 |
| AC-16.6 | Faculty "would a mentor say this" rating | ≥ 4.0/5 |
| AC-16.7 | Plateau/regression false-positive rate (manual review) | < 10% |
| AC-16.8 | Plan adherence (items completed within 7 days of due) | ≥ 45% |
| AC-16.9 | Students who act on the primary action within 48 h | ≥ 35% |
| AC-16.10 | Weekly nudge open rate | ≥ 40% |
| AC-16.11 | Return rate at 14 days (with Counselor vs without, A/B) | +15 points |
| AC-16.12 | Forecast calibration (Phase 4): actual vs predicted ready date | within the p10–p90 band ≥ 80% |

**AC-16.11 is the business case for this module.** If the Counselor doesn't move retention, it isn't the crown jewel and the plan is wrong.

---

## 14. Build order

| Day | Task |
|---|---|
| 1 | Trajectory queries (version-scoped) + trend fitting |
| 2 | Changepoint detection + plateau/regression rules + cooldowns |
| 3 | Bottleneck walk + foundational floor + sanity checks |
| 4 | Articulation-gap detector |
| 5 | Composure-gap (fragility) detector |
| 6 | Coverage + strategy gap detectors |
| 7 | Leverage ranking + adherence weighting |
| 8 | "What's working" finder |
| 9 | Phrasing step + grounding validation + structured fallback |
| 10 | Plan generation: topology, interleaving, backward scheduling |
| 11 | Triage mode + copy variants |
| 12 | FSRS integration + review injection into mocks |
| 13 | Diagnosis UI with evidence playback + plan calendar + "why this?" |
| 14 | Nudges, rejection-recovery, safety path, golden diagnoses, faculty review |
| *(Phase 4)* | Hierarchical forecast model + validation against outcomes |

---

## 15. Open decisions

1. **How often does the Counselor speak?** Currently: after every session (brief) + weekly (full). Risk of fatigue. Proposal: **after every session only if something changed materially**, plus weekly. Make frequency a user setting from day one.
2. **Do we ever tell a student they're unlikely to clear a specific company?** It's the most useful and most dangerous thing we could say. Proposal: **never as a verdict**; state the gap and the time required, and let them decide. Explicitly discuss this with the placement cell — they may have a view.
3. **Should the placement cell see individual diagnoses?** Strong recommendation: **no by default.** Aggregate weak-area data yes; individual "this student has a composure problem" is a career-affecting label. Individual access only with student consent, logged.
4. **Bandit or heuristic?** Ship the heuristic, log for the bandit, switch only with ≥500 tuples and a demonstrated improvement. Do not build the bandit in Phase 4 just because it sounds good.
5. **Who signs off the distress-handling flow?** Must be the faculty advisor plus, ideally, the institute's counselling service. Schedule this conversation in Month 8, not Month 11.
