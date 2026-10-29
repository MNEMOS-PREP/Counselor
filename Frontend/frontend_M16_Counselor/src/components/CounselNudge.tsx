/**
 * "Tara has something to tell you" — the way a talk reaches the student.
 *
 * Platform_Shell shows it on Today and, floating, on the notes page after an
 * interview: it asks M16 whether a talk is due (which makes one when it is),
 * says so while it is being written, and opens it when it is ready. Nothing
 * at all when there is no talk — an empty card is noise.
 */

import { createPortal } from "react-dom";
import { Link } from "react-router-dom";

import { InterviewerPhoto, candidateIdOf, useSession } from "@ai/core";

import { useCheck } from "../api";

export function CounselNudge({
  variant = "card",
  className = "",
}: {
  variant?: "card" | "float";
  /** Applied only when there is something to show, so an absent nudge leaves no gap. */
  className?: string;
}) {
  const candidateId = candidateIdOf(useSession());
  const check = useCheck(candidateId);
  const episode = check.data?.episode;
  if (!episode || episode.watched_at) return null;

  const writing = episode.status === "writing";
  const minutes = `${Math.floor(episode.seconds / 60)}:${String(episode.seconds % 60).padStart(2, "0")}`;
  const started = episode.reached !== null;
  const body = (
    <>
      <div className="relative h-14 w-14 shrink-0 overflow-hidden rounded-full ring-2 ring-brand/40">
        <InterviewerPhoto persona={episode.counselor.id} name={episode.counselor.name} fill />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-ink">
          {writing
            ? `${episode.counselor.name} is going through your interview…`
            : started
              ? `Finish your talk with ${episode.counselor.name}`
              : `${episode.counselor.name} has something to tell you`}
        </p>
        <p className="mt-0.5 text-xs text-ink-soft">
          {writing ? "Ready in a moment." : `${minutes} · what went well, what didn't, and what to do next`}
        </p>
      </div>
      {!writing && (
        <span className="shrink-0 rounded-full bg-brand px-3 py-1.5 text-xs font-semibold text-on-brand">
          {started ? "Carry on" : "Play"}
        </span>
      )}
    </>
  );

  const shell =
    variant === "float"
      ? "fixed bottom-6 right-6 z-40 w-[22rem] shadow-2xl"
      : "w-full";
  const classes = `${shell} ${className} flex items-center gap-3 rounded-2xl border border-brand-line bg-surface-raised p-3 text-left transition hover:border-brand`;

  const card = writing ? (
    <div className={classes} role="status">{body}</div>
  ) : (
    <Link to={`/counsel/${episode.id}`} className={classes}>{body}</Link>
  );
  // Floating, it belongs to the window, not to the page it is over: inside a
  // scrolling or transformed container `fixed` is measured from that box, and
  // the card was cut off at the bottom of the notes.
  return variant === "float" ? createPortal(card, document.body) : card;
}
