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
  relation: string;
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
