/**
 * "Go through my notes with me" — the mentor, beside the notes, one question
 * at a time.
 *
 * The talk names the one thing to fix; this goes through every question the
 * student underperformed on (the user, 2026-10-31: "not necessarily the
 * entire feedback, but at least where I underperformed"). The face is on the
 * left; on the right is that question's part of the notes, as M06 wrote it —
 * the question, what they said, what held, what was missing, the idea, what
 * to practise — and the part being talked about lights up while the line
 * about it is said, the way someone beside you points at the page.
 *
 * It is written when asked for, and that takes minutes (it waits for the
 * notes' explanations, then writes each question on its own); the student
 * said they don't mind, so the page says what it is on while it waits.
 */

import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";

import { Icon, Spinner, candidateIdOf, prepareLines, useInterviewerVoice, useSession } from "@ai/core";

import { useSaveSettings, useSettings, useWalkProgress, useWalkthrough } from "../api";
import type {
  CardSection,
  CloseCard,
  Mode,
  NoteCard,
  NoteStatus,
  OverviewCard,
  QuestionCard,
  WalkChapter,
  WalkLine,
  Walkthrough,
} from "../types";
import { CounselorPicker } from "./CounselorPicker";
import { useNarration } from "./narration";
import { Centre, Control, Frame, Overlay, PauseGlyph, PlayGlyph, Preparing, Stage, Subtitle, clock } from "./stage";

type Phase = "cover" | "playing" | "paused" | "done";

/** The notes page's own colours for a status (M06 `notes.ts` STATUS_META),
 *  so an answer looks the same beside the face as on the page. */
const STATUS: Record<NoteStatus, { badge: string; accent: string }> = {
  correct: { badge: "border-confirmed-line bg-confirmed-soft text-confirmed", accent: "border-l-confirmed" },
  partial: { badge: "border-reported-line bg-reported-soft text-reported", accent: "border-l-reported" },
  vague: { badge: "border-agreement-line bg-agreement-soft text-agreement", accent: "border-l-agreement" },
  incorrect: { badge: "border-contested-line bg-contested-soft text-contested", accent: "border-l-contested" },
  unsupported: { badge: "border-reported-line bg-reported-soft text-reported", accent: "border-l-reported" },
  unanswered: { badge: "border-line-strong bg-surface-sunken text-ink-soft", accent: "border-l-line-strong" },
  not_judged: { badge: "border-line bg-surface-sunken text-ink-faint", accent: "border-l-line" },
};

/** The writer's stage ("Question 2 (3 of 5)") in the student's words. */
function stepWords(stage: string | null): string | null {
  if (!stage) return null;
  const title = stage.replace(/\s*\(\d+ of \d+\)$/, "");
  if (/^Question \d+: waiting/.test(title)) return "Taking a short pause: the model asked us to slow down";
  if (title.startsWith("Question ")) return `Working on ${title.toLowerCase()}`;
  if (title === "Before we start") return "Getting the overview ready";
  if (title === "To finish") return "Wrapping up";
  return title;
}

export function NotesWalkthrough() {
  const { sessionId } = useParams();
  const session = useSession();
  const candidateId = candidateIdOf(session);
  const settings = useSettings(candidateId);
  const chosen = settings.data?.chosen ? (settings.data.counselor_id ?? undefined) : undefined;
  const walk = useWalkthrough(candidateId, sessionId, chosen);
  const back = { to: `/mock/${sessionId}`, label: "Back to your notes" };

  if (settings.isLoading) return <Centre><Spinner label="Opening your notes" /></Centre>;
  if (settings.data && !settings.data.chosen) {
    return <CounselorPicker candidateId={candidateId} studentName={session?.name ?? ""} />;
  }
  if (walk.isLoading || !walk.data) {
    if (walk.isError) {
      return (
        <Centre>
          <p className="text-ink-soft">Your notes could not be opened for this.</p>
          <Link to={back.to} className="mt-3 text-brand underline">{back.label}</Link>
        </Centre>
      );
    }
    return <Centre><Spinner label="Opening your notes" /></Centre>;
  }
  const w = walk.data;
  if (w.status === "failed") {
    return (
      <Centre>
        <p className="text-ink-soft">{w.counselor.name} couldn't go through these notes: {w.reason}.</p>
        <Link to={back.to} className="mt-3 text-brand underline">{back.label}</Link>
      </Centre>
    );
  }
  if (w.status === "writing") {
    return (
      <Frame counselor={w.counselor} back={back} subtitle="Going through your notes">
        <div className="mx-auto max-w-4xl">
          <Preparing
            counselor={w.counselor}
            step={stepWords(w.stage)}
            progress={w.progress}
            note={`This takes a few minutes: ${w.counselor.name} reads each answer you found hard and works out how to explain it. You can leave this page and come back.`}
          />
        </div>
      </Frame>
    );
  }
  return (
    <Player
      key={`${w.id}:${w.counselor.id}`}
      walk={w}
      back={back}
      mode={settings.data?.mode ?? "video"}
      candidateId={candidateId}
    />
  );
}

function Player({
  walk,
  back,
  mode: initialMode,
  candidateId,
}: {
  walk: Walkthrough;
  back: { to: string; label: string };
  mode: Mode;
  candidateId: string | null;
}) {
  const voice = useInterviewerVoice(walk.counselor.voice_id, { personaId: walk.counselor.id });
  const progress = useWalkProgress(walk);
  const saveSettings = useSaveSettings(candidateId);
  const [mode, setMode] = useState<Mode>(initialMode);
  const [phase, setPhase] = useState<Phase>("cover");
  const [at, setAt] = useState(0);
  const [showTranscript, setShowTranscript] = useState(mode === "text");
  const chapters = walk.chapters;
  const chapter = chapters[at];
  const narration = useNarration({ voice, speaker: walk.counselor, silent: mode === "text" });
  const { say, parts } = narration;

  // Have M11 make every line while the cover is up, so nothing waits later.
  useEffect(() => {
    if (mode === "text") return;
    void prepareLines(
      chapters.map((c) => ({ id: `${walk.id}:${c.key}`, parts: parts(c.lines) })),
      "next",
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [walk.id, mode]);

  // Leaving the page stops the voice, and nothing else does.
  const stopVoice = useRef(voice.stop);
  stopVoice.current = voice.stop;
  useEffect(() => () => stopVoice.current("leave"), []);

  const playChapter = useCallback(
    (index: number) => {
      const c = chapters[index];
      if (!c) return;
      setAt(index);
      setPhase("playing");
      say(`${walk.id}:${c.key}`, c.lines);
    },
    [chapters, walk.id, say],
  );

  narration.onFinished.current = (key: string) => {
    const c = chapters[at];
    if (!c || key !== `${walk.id}:${c.key}`) return;
    const last = at === chapters.length - 1;
    progress.mutate({ reached: c.key, finished: last });
    if (last) setPhase("done");
    else playChapter(at + 1);
  };

  const jump = (index: number) => {
    voice.stop("pause");
    playChapter(index);
  };

  const pause = () => {
    narration.halt();
    voice.stop("pause");
    setPhase("paused");
  };

  const switchMode = (next: Mode) => {
    setMode(next);
    saveSettings.mutate({ mode: next });
    if (next === "text") {
      pause();
      setShowTranscript(true);
    }
  };

  // The line being heard, and so the part of the card it is about. Between
  // two lines the voice is quiet while the next is still being made: the last
  // line heard in this chapter stays up (and lit) — a live look had the
  // subtitle jump back to the chapter's first line in every gap.
  const heard = useMemo(
    () => chapter?.lines.find((l) => l.id === voice.speakingPart) ?? null,
    [chapter, voice.speakingPart],
  );
  const lastHeard = useRef<{ key: string; line: WalkLine } | null>(null);
  if (heard && chapter) lastHeard.current = { key: chapter.key, line: heard };
  const line = heard ?? (lastHeard.current?.key === chapter?.key ? lastHeard.current.line : null);
  const speakingLine = line?.text ?? (phase === "playing" || phase === "paused" ? chapter?.lines[0]?.text : null) ?? null;
  const pointing = phase === "playing" ? (line?.points_at ?? null) : null;
  const speaking = voice.speakingKey !== null;
  const card = walk.cards[phase === "cover" ? "intro" : (chapter?.key ?? "intro")];
  const walked = chapters.filter((c) => c.key.startsWith("q")).length;
  const resumeAt = walk.reached && walk.reached !== "close" ? Math.max(0, chapters.findIndex((c) => c.key === walk.reached)) : 0;

  return (
    <Frame
      counselor={walk.counselor}
      back={back}
      subtitle="Going through your notes"
      mode={mode}
      onMode={switchMode}
    >
      <div className="grid gap-6 lg:grid-cols-[minmax(0,11fr)_minmax(0,9fr)]">
        <div className="min-w-0">
          <Stage counselor={walk.counselor} speaking={speaking} expression={voice.expression} mode={mode}>
            {phase === "cover" && (
              <Overlay>
                <p className="text-sm uppercase tracking-wider text-white/60">Your notes</p>
                <p className="mt-2 text-2xl font-semibold text-white">
                  {walked
                    ? `${walk.counselor.name} will take you through ${walked === 1 ? "the question" : `the ${walked} questions`} you found hardest`
                    : `${walk.counselor.name} went through your notes`}
                </p>
                <button
                  type="button"
                  onClick={() => playChapter(resumeAt)}
                  className="mt-6 inline-flex items-center gap-3 rounded-full bg-white px-6 py-3 text-base font-semibold text-black shadow-lg transition hover:scale-[1.02]"
                  aria-label={`Play, ${clock(walk.seconds)}`}
                >
                  <PlayGlyph /> {resumeAt > 0 ? "Carry on" : "Play"} · {clock(walk.seconds)}
                </button>
                {!walk.notes_complete && (
                  <p className="mt-3 max-w-md text-xs text-white/60">
                    Some explanations in your notes weren't written yet, so parts of this go by what the interview
                    recorded.
                  </p>
                )}
                {mode !== "text" && !voice.enabled && (
                  <p className="mt-3 text-xs text-white/60">Voice is off in your settings; the words will show on screen.</p>
                )}
              </Overlay>
            )}
            {phase !== "cover" && speakingLine && mode !== "text" && <Subtitle text={speakingLine} />}
            {phase === "done" && (
              <Overlay>
                <p className="text-2xl font-semibold text-white">That's your notes.</p>
                <p className="mt-2 text-white/70">The one to start with is on the right.</p>
                <div className="mt-5 flex flex-wrap justify-center gap-3">
                  <Link to="/mock" className="rounded-full bg-white px-5 py-2.5 text-sm font-semibold text-black shadow-lg">
                    Practise again
                  </Link>
                  <Link to={back.to} className="rounded-full border border-white/40 px-5 py-2.5 text-sm font-medium text-white">
                    {back.label}
                  </Link>
                </div>
                <button type="button" onClick={() => playChapter(0)} className="mt-4 text-sm text-white/80 underline">
                  Watch again
                </button>
              </Overlay>
            )}
          </Stage>

          <ChapterRail chapters={chapters} at={at} phase={phase} onJump={jump} />

          <div className="mt-3 flex flex-wrap items-center gap-2">
            {phase === "playing" ? (
              <Control onClick={pause} label="Pause"><PauseGlyph /> Pause</Control>
            ) : phase === "paused" ? (
              <Control onClick={() => playChapter(at)} label="Resume"><PlayGlyph /> Resume</Control>
            ) : null}
            {phase !== "cover" && at > 0 && (
              <Control onClick={() => jump(at - 1)} label="Previous">
                <Icon name="arrowLeft" size={14} /> Back
              </Control>
            )}
            {phase !== "cover" && at < chapters.length - 1 && (
              <Control onClick={() => jump(at + 1)} label="Next">
                Next <Icon name="arrowRight" size={14} />
              </Control>
            )}
            <Control onClick={() => setShowTranscript((v) => !v)} label="Show the words">
              <Icon name="document" size={14} /> {showTranscript ? "Hide" : "Read"} it
            </Control>
          </div>

          {showTranscript && <Transcript chapters={chapters} at={phase === "cover" ? -1 : at} />}
          <p className="mt-4 text-xs leading-relaxed text-ink-faint">
            {walk.counselor.name} is an AI mentor with a generated face. Everything said here comes from your interview
            notes{walk.source === "template" ? ", in plain words" : walk.source === "mixed" ? ", some of it in plain words" : ""};
            what you see on the right is the notes themselves.
          </p>
        </div>

        <aside className="min-w-0">
          {card && (
            <NoteCardView
              card={card}
              pointing={pointing}
              onOpen={(key) => {
                const index = chapters.findIndex((c) => c.key === key);
                if (index >= 0) jump(index);
              }}
            />
          )}
        </aside>
      </div>
    </Frame>
  );
}

// ── the notes beside the face ─────────────────────────────────────────────────

function NoteCardView({
  card,
  pointing,
  onOpen,
}: {
  card: NoteCard;
  pointing: CardSection | null;
  onOpen: (key: string) => void;
}) {
  const box = useRef<HTMLDivElement>(null);
  // Bring the part being talked about into view — inside the card, never by
  // scrolling the page away from the face.
  useEffect(() => {
    const container = box.current;
    const target = pointing ? container?.querySelector<HTMLElement>(`[data-section="${pointing}"]`) : null;
    if (!container || !target) return;
    const top = target.offsetTop - container.offsetTop - 12;
    const bottom = top + target.offsetHeight + 24;
    if (top < container.scrollTop || bottom > container.scrollTop + container.clientHeight) {
      container.scrollTo({ top, behavior: "smooth" });
    }
  }, [pointing, card]);

  return (
    <div
      ref={box}
      className="rounded-2xl border border-line bg-surface-raised p-5 lg:sticky lg:top-4 lg:max-h-[calc(100vh-8rem)] lg:overflow-y-auto"
    >
      {card.kind === "overview" ? (
        <Overview card={card} onOpen={onOpen} />
      ) : card.kind === "question" ? (
        <Question card={card} pointing={pointing} />
      ) : (
        <Close card={card} />
      )}
    </div>
  );
}

function StatusBadge({ status, label }: { status: NoteStatus | null; label: string }) {
  if (!status || !label) return null;
  return (
    <span className={`inline-flex rounded-full border px-2 py-0.5 text-2xs font-semibold ${STATUS[status]?.badge ?? STATUS.not_judged.badge}`}>
      {label}
    </span>
  );
}

function Overview({ card, onOpen }: { card: OverviewCard; onOpen: (key: string) => void }) {
  return (
    <>
      <p className="text-2xs font-semibold uppercase tracking-wider text-ink-faint">Your notes</p>
      <h2 className="mt-1 text-lg font-semibold text-ink">
        {card.held} held up · {card.work} to go through
      </h2>
      <ol className="mt-4 space-y-2">
        {card.questions.map((q) => {
          const row = (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-2xs uppercase tracking-wide text-ink-faint">Question {q.index}</span>
                {q.topic && <span className="text-2xs text-ink-faint">· {q.topic}</span>}
                <span className="ml-auto"><StatusBadge status={q.status} label={q.status_label} /></span>
              </div>
              <p className={`mt-1 text-sm leading-snug ${q.walked ? "text-ink" : "text-ink-soft"}`}>{q.question}</p>
            </>
          );
          return (
            <li key={q.key}>
              {q.walked ? (
                <button
                  type="button"
                  onClick={() => onOpen(q.key)}
                  className={`w-full rounded-xl border border-l-4 border-line bg-surface p-3 text-left transition hover:border-brand-line ${STATUS[q.status ?? "not_judged"]?.accent ?? ""}`}
                >
                  {row}
                  <span className="mt-1.5 block text-2xs font-medium text-brand">We'll go through this one</span>
                </button>
              ) : (
                <div className="rounded-xl border border-line bg-surface/60 p-3 opacity-80">{row}</div>
              )}
            </li>
          );
        })}
      </ol>
    </>
  );
}

function Question({ card, pointing }: { card: QuestionCard; pointing: CardSection | null }) {
  return (
    <article className={`border-l-4 pl-4 ${STATUS[card.status ?? "not_judged"]?.accent ?? "border-l-line"}`}>
      <Part section="question" pointing={pointing}>
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={card.status} label={card.status_label} />
          <span className="text-2xs uppercase tracking-wide text-ink-faint">Question {card.index}</span>
          {card.topic && <span className="text-2xs text-ink-faint">· {card.topic}</span>}
          {card.resume_line && <span className="text-2xs text-ink-faint">· From your resume</span>}
        </div>
        {card.resume_line && <p className="mt-2 text-xs italic text-ink-soft">“{card.resume_line}”</p>}
        <h2 className="mt-2 text-base font-semibold leading-snug text-ink">{card.question}</h2>
        {card.headline && <p className="mt-1.5 text-sm leading-relaxed text-ink-soft">{card.headline}</p>}
      </Part>

      {card.answer && (
        <Part section="said" pointing={pointing} title="You said">
          <blockquote className="border-l-2 border-line-strong pl-3 text-sm italic leading-relaxed text-ink-soft">
            “{card.answer}”
          </blockquote>
        </Part>
      )}

      {card.held.length > 0 && (
        <Part section="held" pointing={pointing} title="What held">
          <ul className="space-y-1.5">
            {card.held.map((h) => (
              <li key={h.point} className="text-sm leading-relaxed text-ink">
                <span className="mr-1.5 text-confirmed">✓</span>
                {h.point}
              </li>
            ))}
          </ul>
        </Part>
      )}

      {card.missed.length > 0 && (
        <Part section="missed" pointing={pointing} title={card.missed_title}>
          <ul className="space-y-3">
            {card.missed.map((m) => (
              <li key={m.point + m.evidence} className="text-sm leading-relaxed">
                {m.point && <p className="text-ink">{m.point}</p>}
                {m.evidence && <p className="mt-0.5 italic text-ink-soft">You said: “{m.evidence}”</p>}
                {m.fix && <p className="mt-0.5 text-ink-soft"><span className="font-medium text-ink">Fix:</span> {m.fix}</p>}
              </li>
            ))}
          </ul>
        </Part>
      )}

      {card.idea && (
        <Part section="idea" pointing={pointing} title="The idea">
          <p className="text-sm leading-relaxed text-ink">{card.idea}</p>
        </Part>
      )}

      {card.study.length > 0 && (
        <Part section="study" pointing={pointing} title="To practise">
          <ul className="list-disc space-y-1 pl-5">
            {card.study.map((s) => (
              <li key={s} className="text-sm leading-relaxed text-ink">{s}</li>
            ))}
          </ul>
        </Part>
      )}
    </article>
  );
}

function Close({ card }: { card: CloseCard }) {
  return (
    <>
      <p className="text-2xs font-semibold uppercase tracking-wider text-ink-faint">To finish</p>
      {card.focus && (
        <h2 className="mt-1 text-lg font-semibold text-ink">The one to work on first: {card.focus}</h2>
      )}
      {card.points.length > 0 && (
        <ul className="mt-3 space-y-2">
          {card.points.map((p) => (
            <li key={p} className="text-sm leading-relaxed text-ink-soft">{p}</li>
          ))}
        </ul>
      )}
      <Link
        to="/mock"
        className="mt-5 inline-flex rounded-lg bg-brand px-3.5 py-2 text-sm font-semibold text-on-brand hover:bg-brand-hover"
      >
        Practise again
      </Link>
    </>
  );
}

/** One part of the card; lit while the line about it is being said. */
function Part({
  section,
  pointing,
  title,
  children,
}: {
  section: CardSection;
  pointing: CardSection | null;
  title?: string;
  children: ReactNode;
}) {
  const lit = pointing === section;
  return (
    <section
      data-section={section}
      className={`mt-4 rounded-xl p-2 transition-colors duration-300 first:mt-0 ${lit ? "bg-brand-soft ring-2 ring-brand/40" : ""}`}
    >
      {title && <h3 className="mb-1.5 text-2xs font-semibold uppercase tracking-wider text-ink-faint">{title}</h3>}
      {children}
    </section>
  );
}

// ── around the stage ──────────────────────────────────────────────────────────

function ChapterRail({
  chapters,
  at,
  phase,
  onJump,
}: {
  chapters: WalkChapter[];
  at: number;
  phase: Phase;
  onJump: (i: number) => void;
}) {
  return (
    <ol
      className="mt-4 grid gap-1.5"
      style={{ gridTemplateColumns: `repeat(${chapters.length}, minmax(0, 1fr))` }}
      aria-label="Chapters"
    >
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

function Transcript({ chapters, at }: { chapters: WalkChapter[]; at: number }) {
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
