/**
 * The talk — watched like a short video someone made for you.
 *
 * One face, large (the counselor's 3D head, lip-synced to their own voice,
 * `@ai/core` TalkingHead + M11), the words under it as they are said, and
 * seven chapters the student can move between. It starts on a cover — the
 * face, "has something to tell you", how long — because audio needs the
 * student's own click, and because a video you choose to play is one you
 * watch. Every line is made by M11 while the cover is up (`prepareLines`), so
 * nothing waits once it plays.
 *
 * The ask is the one thing that stops the talk: the counselor asks, the
 * buttons answer, the counselor says something back, and then signs off.
 */

import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";

import {
  Icon,
  InterviewerPhoto,
  Spinner,
  TalkingHead,
  candidateIdOf,
  prepareLines,
  useInterviewerVoice,
  useSession,
} from "@ai/core";

import { useAnswer, useEpisode, useProgress, useSaveSettings, useSettings } from "../api";
import type { AskOption, Chapter, ChapterKey, Episode, Mode } from "../types";
import { CounselorPicker } from "./CounselorPicker";

type Phase = "cover" | "playing" | "paused" | "asking" | "replying" | "done";

const PAUSE_AFTER_MS = 450;
/** The longest a chapter waits for a sentence still being made before it moves on. */
const GRACE_MS = 20_000;

export function EpisodePlayer() {
  const { episodeId } = useParams();
  const session = useSession();
  const candidateId = candidateIdOf(session);
  const episode = useEpisode(episodeId);
  const settings = useSettings(candidateId);

  if (episode.isLoading || settings.isLoading) return <Centre><Spinner label="Opening your talk" /></Centre>;
  if (episode.isError || !episode.data) {
    return (
      <Centre>
        <p className="text-ink-soft">This talk could not be opened.</p>
        <Link to="/counsel" className="mt-3 text-brand underline">Back to your talks</Link>
      </Centre>
    );
  }
  const ep = episode.data;
  if (settings.data && !settings.data.chosen && ep.reached === null) {
    return <CounselorPicker candidateId={candidateId} studentName={session?.name ?? ""} current={ep.counselor.id} />;
  }
  if (ep.status === "writing") {
    return (
      <Frame ep={ep}>
        <Stage ep={ep} speaking={false} expression={() => null} mode="audio">
          <Overlay>
            <Spinner label={`${ep.counselor.name} is going through your interview`} />
            <p className="mt-3 text-sm text-white/70">Usually under half a minute.</p>
          </Overlay>
        </Stage>
      </Frame>
    );
  }
  if (ep.status === "failed") {
    return (
      <Centre>
        <p className="text-ink-soft">This talk could not be written: {ep.reason}</p>
        <Link to="/counsel" className="mt-3 text-brand underline">Back to your talks</Link>
      </Centre>
    );
  }
  return <Player key={`${ep.id}:${ep.counselor.id}`} ep={ep} mode={settings.data?.mode ?? "video"} candidateId={candidateId} />;
}

function Player({ ep, mode: initialMode, candidateId }: { ep: Episode; mode: Mode; candidateId: string | null }) {
  const voice = useInterviewerVoice(ep.counselor.voice_id, { personaId: ep.counselor.id });
  const progress = useProgress(ep.id);
  const answer = useAnswer(ep.id);
  const saveSettings = useSaveSettings(candidateId);
  const [mode, setMode] = useState<Mode>(initialMode);
  const [phase, setPhase] = useState<Phase>("cover");
  const [at, setAt] = useState(0);
  const [reply, setReply] = useState<AskOption | null>(null);
  const [showTranscript, setShowTranscript] = useState(mode === "text");
  const chapters = ep.chapters;
  const chapter = chapters[at];
  const options = "options" in ep.ask ? ep.ask.options : [];
  const answered = options.find((o) => o.id === ep.answer) ?? null;

  const parts = useCallback(
    (lines: { id: string; text: string }[]) =>
      lines.map((l) => ({
        text: l.text,
        personaId: ep.counselor.id,
        voiceId: ep.counselor.voice_id,
        id: l.id,
        pauseAfterMs: PAUSE_AFTER_MS,
      })),
    [ep.counselor.id, ep.counselor.voice_id],
  );

  // Have M11 make every line while the cover is up, so nothing waits later.
  useEffect(() => {
    if (mode === "text") return;
    const lines = chapters.map((c) => ({ id: `${ep.id}:${c.key}`, parts: parts(c.lines) }));
    const replies = options
      .filter((o) => o.reply)
      .map((o) => ({ id: `${ep.id}:reply:${o.id}`, parts: parts([{ id: `reply-${o.id}`, text: o.reply }]) }));
    void prepareLines([...lines, ...replies], "next");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ep.id, mode]);

  // The hook hands back a new object each render: hold `stop` in a ref, so
  // leaving the page stops the voice and nothing else does.
  const stopVoice = useRef(voice.stop);
  stopVoice.current = voice.stop;
  useEffect(() => () => stopVoice.current("leave"), []);

  // ── what is being said, and when it ends ────────────────────────────────────
  const saying = useRef<string | null>(null);
  const heard = useRef(false);
  // The voice goes quiet between two sentences of one line when the next is
  // still being made (its `speakingKey` clears whenever the track runs dry).
  // So a chapter is over only when its LAST line has been heard and the voice
  // is then quiet; a gap before that is waited out, for at most GRACE_MS.
  const lastPart = useRef<string | null>(null);
  const lastHeard = useRef(false);
  const grace = useRef<number | null>(null);
  const fallbackTimer = useRef<number | null>(null);
  // `finished` reads the chapter being played, so timers and the voice's
  // effect call the latest one, never the one from when they were set.
  const onFinished = useRef<(key: string) => void>(() => undefined);

  const say = useCallback(
    (key: string, lines: { id: string; text: string }[]) => {
      saying.current = key;
      heard.current = false;
      lastPart.current = lines[lines.length - 1]?.id ?? null;
      lastHeard.current = false;
      if (grace.current) window.clearTimeout(grace.current);
      if (fallbackTimer.current) window.clearTimeout(fallbackTimer.current);
      if (mode !== "text" && voice.enabled && voice.supported) {
        voice.speak(parts(lines), key);
      } else {
        // No voice: give the words their reading time, then move on.
        const words = lines.reduce((n, l) => n + l.text.split(/\s+/).length, 0);
        fallbackTimer.current = window.setTimeout(() => onFinished.current(key), Math.max(2500, words * 330));
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [mode, voice.enabled, voice.supported, parts],
  );

  const playChapter = useCallback(
    (index: number) => {
      const c = chapters[index];
      if (!c) return;
      setAt(index);
      setPhase("playing");
      setReply(null);
      say(`${ep.id}:${c.key}`, c.lines);
    },
    [chapters, ep.id, say],
  );

  const finished = useCallback(
    (key: string) => {
      if (saying.current !== key) return;
      saying.current = null;
      if (key.includes(":reply:")) {
        playChapter(at + 1);
        return;
      }
      const c = chapters[at];
      if (!c) return;
      const last = at === chapters.length - 1;
      progress.mutate({ reached: c.key, finished: last });
      if (c.key === "ask" && options.length) {
        if (answered) playChapter(at + 1);
        else setPhase("asking");
        return;
      }
      if (last) setPhase("done");
      else playChapter(at + 1);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [at, chapters, options.length, answered, playChapter],
  );

  onFinished.current = finished;

  // The voice says what is being heard (speakingKey, speakingPart) and when
  // it has gone quiet; the chapter ends after its last line, not at a gap.
  useEffect(() => {
    const key = saying.current;
    if (!key) return;
    if (voice.speakingPart && voice.speakingPart === lastPart.current) lastHeard.current = true;
    if (voice.speakingKey === key) {
      heard.current = true;
      if (grace.current) window.clearTimeout(grace.current);
      grace.current = null;
      return;
    }
    if (heard.current && voice.speakingKey === null) {
      if (lastHeard.current) onFinished.current(key);
      else if (!grace.current) {
        // A sentence still being made: wait for it, but never for ever.
        grace.current = window.setTimeout(() => {
          grace.current = null;
          onFinished.current(key);
        }, GRACE_MS);
      }
    }
  }, [voice.speakingKey, voice.speakingPart]);

  const pause = () => {
    saying.current = null; // a stop is not an ending: the next chapter must not start
    voice.stop("pause");
    if (fallbackTimer.current) window.clearTimeout(fallbackTimer.current);
    if (grace.current) window.clearTimeout(grace.current);
    grace.current = null;
    setPhase("paused");
  };

  const choose = (option: AskOption) => {
    answer.mutate(option.id);
    if (!option.reply) {
      playChapter(at + 1); // nothing to say back: on to the sign-off
      return;
    }
    setReply(option);
    setPhase("replying");
    say(`${ep.id}:reply:${option.id}`, [{ id: `reply-${option.id}`, text: option.reply }]);
  };

  const switchMode = (next: Mode) => {
    setMode(next);
    saveSettings.mutate({ mode: next });
    if (next === "text") {
      pause();
      setShowTranscript(true);
    }
  };

  const speakingLine = useMemo(() => {
    if (reply) return reply.reply;
    const all = chapters.flatMap((c) => c.lines);
    const now = all.find((l) => l.id === voice.speakingPart);
    return now?.text ?? (phase === "playing" || phase === "paused" ? chapter?.lines[0]?.text : null) ?? null;
  }, [voice.speakingPart, chapters, chapter, phase, reply]);

  const minutes = `${Math.floor(ep.seconds / 60)}:${String(ep.seconds % 60).padStart(2, "0")}`;
  const speaking = voice.speakingKey !== null;
  const planIndex = chapters.findIndex((c) => c.key === "plan");
  const askIndex = chapters.findIndex((c) => c.key === "ask");
  // Reached this time (the chapter being played), or an earlier time (`reached`).
  const askShown =
    (phase !== "cover" && askIndex >= 0 && at >= askIndex) ||
    (ep.reached !== null && askIndex >= 0 && chapters.findIndex((c) => c.key === ep.reached) >= askIndex);

  return (
    <Frame ep={ep} mode={mode} onMode={switchMode}>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="min-w-0">
          <Stage ep={ep} speaking={speaking} expression={voice.expression} mode={mode} listening={phase === "asking"}>
            {phase === "cover" && (
              <Overlay>
                <p className="text-sm uppercase tracking-wider text-white/60">About your last {ep.sessions.length > 1 ? `${ep.sessions.length} interviews` : "interview"}</p>
                <p className="mt-2 text-2xl font-semibold text-white">{ep.counselor.name} has something to tell you</p>
                <button
                  type="button"
                  onClick={() => playChapter(ep.reached && ep.reached !== "bye" ? Math.max(0, chapters.findIndex((c) => c.key === ep.reached)) : 0)}
                  className="mt-6 inline-flex items-center gap-3 rounded-full bg-white px-6 py-3 text-base font-semibold text-black shadow-lg transition hover:scale-[1.02]"
                  aria-label={`Play the talk, ${minutes}`}
                >
                  <PlayGlyph /> {ep.reached && ep.reached !== "bye" ? "Carry on" : "Play"} · {minutes}
                </button>
                {mode !== "text" && !voice.enabled && (
                  <p className="mt-3 text-xs text-white/60">Voice is off in your settings; the words will show on screen.</p>
                )}
              </Overlay>
            )}
            {phase !== "cover" && speakingLine && mode !== "text" && (
              <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/85 via-black/50 to-transparent px-8 pb-6 pt-16">
                <p className="mx-auto max-w-3xl text-center text-xl leading-snug text-white [text-wrap:balance]" aria-live="polite">
                  {speakingLine}
                </p>
              </div>
            )}
            {phase === "done" && (
              <Overlay>
                <p className="text-2xl font-semibold text-white">That's the talk.</p>
                <p className="mt-2 text-white/70">Your plan is on the right. Start with the first one.</p>
                <button type="button" onClick={() => playChapter(0)} className="mt-5 text-sm text-white/80 underline">
                  Watch again
                </button>
              </Overlay>
            )}
          </Stage>

          <ChapterRail chapters={chapters} at={at} phase={phase} onJump={(i) => { voice.stop("pause"); playChapter(i); }} />

          <div className="mt-3 flex flex-wrap items-center gap-2">
            {phase === "playing" || phase === "replying" ? (
              <Control onClick={pause} label="Pause"><PauseGlyph /> Pause</Control>
            ) : phase === "paused" ? (
              <Control onClick={() => playChapter(at)} label="Resume"><PlayGlyph /> Resume</Control>
            ) : null}
            {phase !== "cover" && at > 0 && (
              <Control onClick={() => { voice.stop("pause"); playChapter(at - 1); }} label="Previous chapter">
                <Icon name="arrowLeft" size={14} /> Back
              </Control>
            )}
            {phase !== "cover" && at < chapters.length - 1 && phase !== "asking" && (
              <Control onClick={() => { voice.stop("pause"); playChapter(at + 1); }} label="Next chapter">
                Next <Icon name="arrowRight" size={14} />
              </Control>
            )}
            {planIndex >= 0 && at < planIndex && (
              <Control onClick={() => { voice.stop("pause"); playChapter(planIndex); }} label="Skip to the plan">
                Skip to the plan
              </Control>
            )}
            <Control onClick={() => setShowTranscript((v) => !v)} label="Show the words">
              <Icon name="document" size={14} /> {showTranscript ? "Hide" : "Read"} the talk
            </Control>
          </div>

          {showTranscript && <Transcript chapters={chapters} at={phase === "cover" ? -1 : at} />}
        </div>

        <aside className="space-y-4">
          <Plan ep={ep} highlight={chapter?.key === "plan" && phase !== "cover"} />
          {/* The ask is the counselor's to make: shown when they make it (or
              once it was answered), never as a spoiler beside the cover. */}
          {options.length > 0 && (askShown || answered || reply) && (
            <section className="rounded-2xl border border-line bg-surface-raised p-4">
              <h2 className="text-sm font-semibold text-ink">Your call</h2>
              <p className="mt-1 text-sm text-ink-soft">{ep.counselor.name} asked: {ep.ask && "text" in ep.ask ? ep.ask.text : ""}?</p>
              <div className="mt-3 flex flex-col gap-2">
                {options.map((o) => {
                  const picked = (reply?.id ?? answered?.id) === o.id;
                  return (
                    <button
                      key={o.id}
                      type="button"
                      onClick={() => choose(o)}
                      disabled={phase !== "asking" && !(phase === "done" || phase === "paused")}
                      className={`rounded-xl border px-3 py-2 text-left text-sm transition ${
                        picked ? "border-brand bg-brand-soft text-ink" : "border-line bg-surface hover:border-brand-line"
                      } ${phase === "asking" ? "ring-2 ring-brand/40" : ""} disabled:opacity-60`}
                    >
                      {o.label}
                      {picked && <span className="ml-2 text-xs text-ink-soft">your answer</span>}
                    </button>
                  );
                })}
              </div>
              {phase === "asking" && <p className="mt-2 text-xs text-ink-soft">{ep.counselor.name} is waiting for your answer.</p>}
            </section>
          )}
          <p className="text-xs leading-relaxed text-ink-faint">
            {ep.counselor.name} is an AI counselor with a generated face. Every sentence in this talk comes from your
            own interview notes and your goals{ep.source === "template" ? ", in plain words" : ""}.
          </p>
        </aside>
      </div>
    </Frame>
  );
}

// ── pieces ────────────────────────────────────────────────────────────────────

function Frame({ ep, mode, onMode, children }: { ep: Episode; mode?: Mode; onMode?: (m: Mode) => void; children: ReactNode }) {
  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link to="/counsel" className="rounded-lg p-1.5 text-ink-soft hover:bg-surface-sunken" aria-label="Back to your talks">
            <Icon name="arrowLeft" size={18} />
          </Link>
          <div>
            <h1 className="text-lg font-semibold text-ink">
              {ep.counselor.name} <span className="font-normal text-ink-soft">· your {ep.counselor.relation}</span>
            </h1>
            <p className="text-xs text-ink-faint">{new Date(ep.created_at).toLocaleDateString(undefined, { day: "numeric", month: "long" })}</p>
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

function Stage({
  ep,
  speaking,
  expression,
  mode,
  listening = false,
  children,
}: {
  ep: Episode;
  speaking: boolean;
  expression: () => Record<string, number> | null;
  mode: Mode;
  listening?: boolean;
  children?: ReactNode;
}) {
  const photo = <InterviewerPhoto persona={ep.counselor.id} name={ep.counselor.name} fill backdrop />;
  return (
    <div className="relative aspect-video w-full overflow-hidden rounded-2xl bg-neutral-950 shadow-xl ring-1 ring-black/20">
      {mode === "video" ? (
        <TalkingHead
          persona={ep.counselor.id}
          name={ep.counselor.name}
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

function Overlay({ children }: { children: ReactNode }) {
  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/55 px-6 text-center backdrop-blur-[2px]">
      {children}
    </div>
  );
}

function ChapterRail({ chapters, at, phase, onJump }: { chapters: Chapter[]; at: number; phase: Phase; onJump: (i: number) => void }) {
  return (
    <ol className="mt-4 grid grid-cols-7 gap-1.5" aria-label="Chapters">
      {chapters.map((c, i) => {
        const done = phase !== "cover" && (i < at || phase === "done");
        const now = phase !== "cover" && phase !== "done" && i === at;
        return (
          <li key={c.key}>
            <button type="button" onClick={() => onJump(i)} className="group w-full text-left" aria-current={now ? "step" : undefined}>
              <span className={`block h-1.5 rounded-full transition ${now ? "bg-brand" : done ? "bg-brand/50" : "bg-line"}`} />
              <span className={`mt-1.5 block truncate text-xs ${now ? "font-medium text-ink" : "text-ink-soft group-hover:text-ink"}`}>{c.title}</span>
            </button>
          </li>
        );
      })}
    </ol>
  );
}

function Plan({ ep, highlight }: { ep: Episode; highlight: boolean }) {
  return (
    <section className={`rounded-2xl border bg-surface-raised p-4 transition ${highlight ? "border-brand ring-2 ring-brand/30" : "border-line"}`}>
      <h2 className="text-sm font-semibold text-ink">Your plan</h2>
      <ol className="mt-3 space-y-2">
        {ep.plan.map((s, i) => (
          <li key={s.id} className="rounded-xl border border-line bg-surface p-3">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm font-medium text-ink">
                  <span className="mr-1.5 text-ink-faint">{i + 1}.</span>
                  {s.title}
                </p>
                <p className="mt-0.5 text-xs text-ink-soft">{s.minutes} min · {s.why.replace(/\s*\(F\d+\)/g, "")}</p>
              </div>
              <Link to={s.href} className="shrink-0 rounded-lg bg-brand px-2.5 py-1 text-xs font-medium text-on-brand hover:bg-brand-hover">
                Start
              </Link>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

function Transcript({ chapters, at }: { chapters: Chapter[]; at: number }) {
  return (
    <div className="mt-5 space-y-4 rounded-2xl border border-line bg-surface-raised p-5">
      {chapters.map((c, i) => (
        <section key={c.key} className={i === at ? "" : "opacity-80"}>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-faint">{c.title}</h3>
          {c.lines.map((l) => (
            <p key={l.id} className="mt-1 text-[0.95rem] leading-relaxed text-ink">{l.text}</p>
          ))}
        </section>
      ))}
    </div>
  );
}

function Control({ onClick, label, children }: { onClick: () => void; label: string; children: ReactNode }) {
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

function Centre({ children }: { children: ReactNode }) {
  return <div className="flex min-h-[60vh] flex-col items-center justify-center">{children}</div>;
}

function PlayGlyph() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
      <path d="M3 1.8v10.4a.6.6 0 0 0 .9.5l8.6-5.2a.6.6 0 0 0 0-1L3.9 1.3a.6.6 0 0 0-.9.5Z" fill="currentColor" />
    </svg>
  );
}

function PauseGlyph() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
      <rect x="2.5" y="1.5" width="3.2" height="11" rx="0.8" fill="currentColor" />
      <rect x="8.3" y="1.5" width="3.2" height="11" rx="0.8" fill="currentColor" />
    </svg>
  );
}

export type { ChapterKey };
