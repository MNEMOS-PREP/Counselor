/**
 * The pieces a talk and a walk are both made of: the page's frame, the stage
 * with the mentor's face on it, the overlay, the buttons under it.
 */

import { type ReactNode, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Icon, InterviewerPhoto, TalkingHead } from "@ai/core";

import type { CounselorRef, Mode } from "../types";

export function Frame({
  counselor,
  back,
  subtitle,
  mode,
  onMode,
  children,
}: {
  counselor: CounselorRef;
  /** Where the arrow goes back to. */
  back: { to: string; label: string };
  subtitle: string;
  mode?: Mode;
  onMode?: (m: Mode) => void;
  children: ReactNode;
}) {
  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link to={back.to} className="rounded-lg p-1.5 text-ink-soft hover:bg-surface-sunken" aria-label={back.label}>
            <Icon name="arrowLeft" size={18} />
          </Link>
          <div>
            <h1 className="text-lg font-semibold text-ink">
              {counselor.name} <span className="font-normal text-ink-soft">· your mentor</span>
            </h1>
            <p className="text-xs text-ink-faint">{subtitle}</p>
          </div>
        </div>
        {mode && onMode && (
          <div className="flex rounded-xl border border-line bg-surface p-0.5 text-sm" role="group" aria-label="How to have the talk">
            {(["video", "audio", "text"] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => onMode(m)}
                aria-pressed={mode === m}
                className={`rounded-lg px-3 py-1 capitalize ${mode === m ? "bg-surface-raised font-medium text-ink shadow-sm" : "text-ink-soft"}`}
              >
                {m === "text" ? "Read" : m === "audio" ? "Listen" : "Watch"}
              </button>
            ))}
          </div>
        )}
      </div>
      {children}
    </div>
  );
}

export function Stage({
  counselor,
  speaking,
  expression,
  mode,
  listening = false,
  children,
}: {
  counselor: CounselorRef;
  speaking: boolean;
  expression: () => Record<string, number> | null;
  mode: Mode;
  listening?: boolean;
  children?: ReactNode;
}) {
  const photo = <InterviewerPhoto persona={counselor.id} name={counselor.name} fill backdrop />;
  return (
    <div className="relative aspect-video w-full overflow-hidden rounded-2xl bg-neutral-950 shadow-xl ring-1 ring-black/20">
      {mode === "video" ? (
        <TalkingHead
          persona={counselor.id}
          name={counselor.name}
          speaking={speaking}
          expression={expression}
          listening={listening}
          fallback={photo}
          className="absolute inset-0 h-full w-full"
        />
      ) : mode === "audio" ? (
        <div className="absolute inset-0 grid place-items-center">
          <div className={`h-40 w-40 overflow-hidden rounded-full ring-4 transition ${speaking ? "ring-brand" : "ring-white/10"}`}>
            {photo}
          </div>
        </div>
      ) : (
        <div className="absolute inset-0 opacity-40">{photo}</div>
      )}
      {children}
    </div>
  );
}

export function Overlay({ children }: { children: ReactNode }) {
  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/55 px-6 text-center backdrop-blur-[2px]">
      {children}
    </div>
  );
}

/** The words being said, over the bottom of the stage. */
export function Subtitle({ text }: { text: string }) {
  return (
    <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/85 via-black/50 to-transparent px-8 pb-6 pt-16">
      <p className="mx-auto max-w-3xl text-center text-xl leading-snug text-white [text-wrap:balance]" aria-live="polite">
        {text}
      </p>
    </div>
  );
}

export function Control({ onClick, label, children }: { onClick: () => void; label: string; children: ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-surface px-3 py-1.5 text-sm text-ink hover:bg-surface-sunken"
    >
      {children}
    </button>
  );
}

export function Centre({ children }: { children: ReactNode }) {
  return <div className="flex min-h-[60vh] flex-col items-center justify-center">{children}</div>;
}

export function PlayGlyph() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
      <path d="M3 1.8v10.4a.6.6 0 0 0 .9.5l8.6-5.2a.6.6 0 0 0 0-1L3.9 1.3a.6.6 0 0 0-.9.5Z" fill="currentColor" />
    </svg>
  );
}

export function PauseGlyph() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
      <rect x="2.5" y="1.5" width="3.2" height="11" rx="0.8" fill="currentColor" />
      <rect x="8.3" y="1.5" width="3.2" height="11" rx="0.8" fill="currentColor" />
    </svg>
  );
}

/** "1:05" — how long a talk or a walk takes, said the way a video says it. */
export function clock(seconds: number): string {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

/**
 * "Your feedback is being prepared — stay tuned." What a student sees while a
 * talk or a walk is written: the mentor's face with a slow halo, a page being
 * written, what is being worked on now, and how far along it is. A walk takes
 * minutes, so the wait should look like work being done for them — and it
 * is: every step it names is one the writer really takes. Still under
 * `prefers-reduced-motion`: every animation is `motion-safe:`.
 */
export function Preparing({
  counselor,
  step,
  progress,
  note,
}: {
  counselor: CounselorRef;
  /** What the writer is on, in the student's words. */
  step?: string | null;
  /** How far along, when the writer can say. */
  progress?: { at: number; of: number } | null;
  /** One line under it all: how long, or that they can leave. */
  note?: string;
}) {
  const doing = [
    `${counselor.name} is reading what you said`,
    "Finding where each answer slipped",
    "Working out the idea behind the right answer",
    `Putting it the way ${counselor.name} would say it`,
  ];
  const [shown, setShown] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => setShown((i) => (i + 1) % 4), 3200);
    return () => window.clearInterval(timer);
  }, []);
  // Never 0 % (it has started) and never 100 % (it is not done).
  const done = progress ? Math.min(92, Math.max(8, ((progress.at - 0.5) / progress.of) * 100)) : null;

  return (
    <div className="relative aspect-video w-full overflow-hidden rounded-2xl bg-neutral-950 shadow-xl ring-1 ring-black/20">
      <div aria-hidden className="absolute -left-24 top-1/4 h-72 w-72 rounded-full bg-brand/25 blur-3xl motion-safe:animate-pulse" />
      <div
        aria-hidden
        className="absolute -right-16 bottom-0 h-56 w-56 rounded-full bg-brand/15 blur-3xl motion-safe:animate-pulse [animation-delay:1.2s]"
      />
      <div className="relative flex h-full flex-col items-center justify-center px-6 text-center" role="status">
        <div className="relative h-24 w-24">
          <span aria-hidden className="absolute inset-0 rounded-full bg-brand/40 motion-safe:animate-ping [animation-duration:2.4s]" />
          <div className="relative h-24 w-24 overflow-hidden rounded-full ring-4 ring-brand/60">
            <InterviewerPhoto persona={counselor.id} name={counselor.name} fill />
          </div>
        </div>
        <p className="mt-6 text-2xl font-semibold tracking-tight text-white">Your feedback is being prepared</p>
        <p className="mt-1 text-white/70">Stay tuned — {counselor.name} is going through your notes.</p>

        {/* A page being written. */}
        <div aria-hidden className="mt-5 w-64 space-y-2">
          {[94, 76, 88, 58].map((width, k) => (
            <div
              key={width}
              className="h-1.5 rounded-full bg-white/15 motion-safe:animate-pulse"
              style={{ width: `${width}%`, animationDelay: `${k * 220}ms` }}
            />
          ))}
        </div>

        <div className="mt-5 w-72">
          <div className="h-1 overflow-hidden rounded-full bg-white/10">
            <div
              className={`h-full rounded-full bg-brand transition-[width] duration-700 ${done === null ? "w-1/4 motion-safe:animate-pulse" : ""}`}
              style={done === null ? undefined : { width: `${done}%` }}
            />
          </div>
          {step && <p className="mt-2 text-xs font-medium text-white/75">{step}</p>}
        </div>

        <p className="mt-3 flex items-center gap-2 text-sm text-white/85" aria-live="polite">
          {doing[shown]}
          <span aria-hidden className="inline-flex gap-1">
            {[0, 1, 2].map((k) => (
              <span
                key={k}
                className="h-1.5 w-1.5 rounded-full bg-white/70 motion-safe:animate-bounce"
                style={{ animationDelay: `${k * 150}ms` }}
              />
            ))}
          </span>
        </p>
        {note && <p className="mt-4 max-w-md text-xs text-white/55">{note}</p>}
      </div>
    </div>
  );
}
