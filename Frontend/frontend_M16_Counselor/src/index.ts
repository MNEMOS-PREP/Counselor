/**
 * M16 — Counselor · public surface.
 *
 * Anything not exported here is private to this module. Platform_Shell mounts
 * `m16Routes` (/counsel) and shows `CounselNudge` on Today and after an
 * interview.
 */

export { m16Routes } from "./routes";
export { CounselNudge } from "./components/CounselNudge";
export { useCheck } from "./api";
export type { Check, Episode, Settings } from "./types";
