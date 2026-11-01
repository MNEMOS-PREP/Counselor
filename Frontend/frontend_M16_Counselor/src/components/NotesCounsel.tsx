/**
 * The mentor, floating over an ended interview's notes: the talk when one is
 * due (`CounselNudge`), and always "go through these notes with me", which
 * opens the walk through the questions that need work.
 *
 * It can be folded down to the mentor's face, so it never sits on the notes
 * a student is reading; the face opens it again.
 */

import { useState } from "react";
import { createPortal } from "react-dom";
import { Link } from "react-router-dom";

import { InterviewerPhoto, candidateIdOf, useSession } from "@ai/core";

import { useCounselors, useSettings } from "../api";
import { CounselNudge } from "./CounselNudge";

export function NotesCounsel({ sessionId }: { sessionId: string }) {
  const candidateId = candidateIdOf(useSession());
  const settings = useSettings(candidateId);
  const counselors = useCounselors();
  const [folded, setFolded] = useState(false);
  const who =
    counselors.data?.find((c) => c.id === settings.data?.counselor_id) ?? counselors.data?.find((c) => c.default);
  if (!who) return null;

  const face = (size: string) => (
    <div className={`relative ${size} shrink-0 overflow-hidden rounded-full ring-2 ring-brand/40`}>
      <InterviewerPhoto persona={who.id} name={who.name} fill />
    </div>
  );

  // Floating, it belongs to the window, not to the page it is over (a
  // transformed container measures `fixed` from itself).
  return createPortal(
    folded ? (
      <button
        type="button"
        onClick={() => setFolded(false)}
        className="fixed bottom-6 right-6 z-40 rounded-full shadow-2xl"
        aria-label={`Go through these notes with ${who.name}`}
        title={`Go through these notes with ${who.name}`}
      >
        {face("h-14 w-14")}
      </button>
    ) : (
      <div className="fixed bottom-6 right-6 z-40 flex w-[22rem] flex-col gap-2">
        <CounselNudge className="shadow-2xl" />
        <div className="relative rounded-2xl border border-brand-line bg-surface-raised shadow-2xl">
          <Link
            to={`/counsel/notes/${sessionId}`}
            className="flex items-center gap-3 rounded-2xl p-3 pr-9 text-left transition hover:bg-surface-sunken/40"
          >
            {face("h-14 w-14")}
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-ink">Go through these notes with {who.name}</p>
              <p className="mt-0.5 text-xs text-ink-soft">The questions you found hardest, one at a time</p>
            </div>
          </Link>
          <button
            type="button"
            onClick={() => setFolded(true)}
            className="absolute right-2 top-2 rounded-md px-1.5 text-ink-faint hover:bg-surface-sunken hover:text-ink"
            aria-label="Fold away"
          >
            ×
          </button>
        </div>
      </div>
    ),
    document.body,
  );
}
