/** The shapes M16's backend returns (router.py, episodes.view). */

export type ChapterKey = "hello" | "trend" | "well" | "didnt" | "plan" | "ask" | "bye";

export interface Line {
  id: string;
  text: string;
  /** The fact, plan step or ask the line stands on (never shown; kept for trust). */
  cites: string[];
}

export interface Chapter {
  key: ChapterKey;
  title: string;
  lines: Line[];
}

export interface Step {
  id: string;
  title: string;
  why: string;
  minutes: number;
  href: string;
}

export interface AskOption {
  id: string;
  label: string;
  /** What the counselor says back when the student picks it. */
  reply: string;
}

export interface Ask {
  count: number;
  by: string;
  text: string;
  options: AskOption[];
}

export interface CounselorRef {
  id: string;
  name: string;
  /** What they are to the student: "mentor". */
  relation: string;
  /** Who they are, shown under their name. */
  role: string;
  voice_id: string;
}

export interface Counselor extends CounselorRef {
  blurb: string;
  default: boolean;
}

export interface Episode {
  id: string;
  candidate_id: string;
  status: "writing" | "ready" | "failed";
  counselor: CounselorRef;
  sessions: string[];
  created_at: string;
  ready_at: string | null;
  chapters: Chapter[];
  plan: Step[];
  ask: Ask | Record<string, never>;
  answer: string | null;
  reached: ChapterKey | null;
  watched_at: string | null;
  seconds: number;
  source: "model" | "template";
  reason: string | null;
}

export interface Check {
  due: boolean;
  until_next: number | null;
  reason: string | null;
  episode: Episode | null;
}

export type Mode = "video" | "audio" | "text";

export interface Settings {
  candidate_id: string;
  every: number;
  counselor_id: string | null;
  chosen: boolean;
  mode: Mode;
  paused: boolean;
  every_choices: number[];
}

// ── a walk through one interview's notes ──────────────────────────────────────

/** Which part of the card a line is about, so the screen can point at it. */
export type CardSection = "question" | "said" | "held" | "missed" | "idea" | "study";

export interface WalkLine extends Line {
  points_at: CardSection | null;
}

export interface WalkChapter {
  /** "intro", "q2" … (the question's number in the notes), "close". */
  key: string;
  title: string;
  lines: WalkLine[];
}

/** The notes' statuses (M06 report). */
export type NoteStatus =
  | "correct"
  | "partial"
  | "vague"
  | "incorrect"
  | "unsupported"
  | "unanswered"
  | "not_judged";

export interface OverviewCard {
  kind: "overview";
  held: number;
  work: number;
  unjudged: number;
  questions: {
    key: string;
    index: number;
    question: string;
    status: NoteStatus | null;
    status_label: string;
    topic: string;
    /** Gone through in this walk (it needs work). */
    walked: boolean;
  }[];
}

export interface QuestionCard {
  kind: "question";
  index: number;
  topic: string;
  /** A question about the student's resume: the line it asked about. */
  resume_line: string;
  status: NoteStatus | null;
  status_label: string;
  question: string;
  headline: string;
  answer: string;
  held: { point: string; evidence: string }[];
  missed: { point: string; evidence: string; fix: string }[];
  missed_title: string;
  idea: string;
  study: string[];
}

export interface CloseCard {
  kind: "close";
  focus: string;
  points: string[];
}

export type NoteCard = OverviewCard | QuestionCard | CloseCard;

export interface Walkthrough {
  id: string;
  candidate_id: string;
  session_id: string;
  status: "writing" | "ready" | "failed";
  /** While writing: what it is on ("Question 2 (2 of 3)"). */
  stage: string | null;
  /** The same, as numbers, for the progress bar. */
  progress: { at: number; of: number } | null;
  counselor: CounselorRef;
  created_at: string;
  ready_at: string | null;
  chapters: WalkChapter[];
  cards: Record<string, NoteCard>;
  /** Every explanation in the notes was written when this was. */
  notes_complete: boolean;
  reached: string | null;
  watched_at: string | null;
  seconds: number;
  source: "model" | "mixed" | "template";
  templated: string[];
  reason: string | null;
}
