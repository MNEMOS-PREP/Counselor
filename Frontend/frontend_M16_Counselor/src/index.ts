/**
 * M16 — Counselor · public surface.
 *
 * Anything not exported here is private to this module. Platform_Shell mounts
 * `m16Routes` (/counsel), shows `CounselNudge` on Today, and `NotesCounsel`
 * over an ended interview's notes (the talk when due, and "go through these
 * notes with me").
 */

export { m16Routes } from "./routes";
export { CounselNudge } from "./components/CounselNudge";
export { NotesCounsel } from "./components/NotesCounsel";
export { useCheck } from "./api";
export type { Check, Episode, Settings, Walkthrough } from "./types";
