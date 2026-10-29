/**
 * /counsel — the talk waiting, who gives them, how often, and the talks so far.
 */

import { Link } from "react-router-dom";

import { InterviewerPhoto, PageHeader, Spinner, candidateIdOf, useSession } from "@ai/core";

import { useCheck, useCounselors, useEpisodes, useSaveSettings, useSettings } from "../api";
import type { Mode } from "../types";
import { CounselNudge } from "./CounselNudge";
import { CounselorPicker } from "./CounselorPicker";

export function CounselHome() {
  const session = useSession();
  const candidateId = candidateIdOf(session);
  const settings = useSettings(candidateId);
  const check = useCheck(candidateId);
  const episodes = useEpisodes(candidateId);
  const counselors = useCounselors();
  const save = useSaveSettings(candidateId);

  if (!candidateId) {
    return <p className="p-8 text-ink-soft">Talks are for students. Sign in as a student to see yours.</p>;
  }
  if (settings.isLoading) return <div className="p-8"><Spinner label="Loading" /></div>;
  if (settings.data && !settings.data.chosen) {
    return <CounselorPicker candidateId={candidateId} studentName={session?.name ?? ""} />;
  }
  const s = settings.data;
  const me = counselors.data?.find((c) => c.id === s?.counselor_id);
  const untilNext = check.data?.until_next;

  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-6">
      <PageHeader
        eyebrow="Your counselor"
        title={me ? `Talks with ${me.name}` : "Your talks"}
        subtitle="A short talk after your interviews: what went well, what didn't, and what to do next."
      />

      <div className="mt-6 space-y-3">
        <CounselNudge />
        {!check.data?.episode && untilNext != null && (
          <p className="rounded-2xl border border-line bg-surface-raised p-4 text-sm text-ink-soft">
            Your next talk comes after {untilNext === 1 ? "your next interview" : `${untilNext} more interviews`}.{" "}
            <Link to="/practice" className="text-brand underline">Start one</Link>
          </p>
        )}
        {s?.paused && <p className="text-sm text-ink-soft">Talks are paused. Turn them back on below.</p>}
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <section>
          <h2 className="text-sm font-semibold text-ink">Talks so far</h2>
          {episodes.data?.length ? (
            <ul className="mt-3 divide-y divide-line rounded-2xl border border-line bg-surface-raised">
              {episodes.data.map((e) => (
                <li key={e.id}>
                  <Link to={`/counsel/${e.id}`} className="flex items-center gap-3 p-3 hover:bg-surface-sunken">
                    <div className="relative h-10 w-10 shrink-0 overflow-hidden rounded-full">
                      <InterviewerPhoto persona={e.counselor.id} name={e.counselor.name} fill />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-ink">
                        {e.counselor.name} · {e.sessions.length > 1 ? `${e.sessions.length} interviews` : "1 interview"}
                      </p>
                      <p className="text-xs text-ink-soft">
                        {new Date(e.created_at).toLocaleDateString(undefined, { day: "numeric", month: "long" })}
                        {" · "}
                        {e.watched_at ? "heard" : e.reached ? "started" : "not heard yet"}
                        {e.answer ? ` · you said ${e.answer === "not_now" ? "not this week" : e.answer === "one" ? "one" : "yes"}` : ""}
                      </p>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-ink-soft">No talks yet. The first comes after your next interview.</p>
          )}
        </section>

        <aside className="space-y-5 rounded-2xl border border-line bg-surface-raised p-5">
          <div>
            <h2 className="text-sm font-semibold text-ink">Who talks to you</h2>
            <div className="mt-3 grid grid-cols-2 gap-2">
              {counselors.data?.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => save.mutate({ counselor_id: c.id })}
                  aria-pressed={c.id === s?.counselor_id}
                  className={`overflow-hidden rounded-xl border text-center ${c.id === s?.counselor_id ? "border-brand ring-2 ring-brand/30" : "border-line"}`}
                  title={`${c.name}, ${c.relation}`}
                >
                  <div className="relative aspect-[4/3] bg-neutral-900">
                    <InterviewerPhoto persona={c.id} name={c.name} fill />
                  </div>
                  <p className="px-2 pt-1.5 text-sm font-medium text-ink">{c.name}</p>
                  <p className="px-2 pb-1.5 text-xs text-ink-soft">{c.relation}</p>
                </button>
              ))}
            </div>
          </div>
          <div>
            <h2 className="text-sm font-semibold text-ink">How often</h2>
            <div className="mt-2 flex gap-2" role="group" aria-label="A talk after every N interviews">
              {(s?.every_choices ?? [1, 2, 3]).map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => save.mutate({ every: n })}
                  aria-pressed={s?.every === n}
                  className={`flex-1 rounded-lg border px-2 py-1.5 text-sm ${s?.every === n ? "border-brand bg-brand-soft text-ink" : "border-line text-ink-soft"}`}
                >
                  {n === 1 ? "Every interview" : `Every ${n}`}
                </button>
              ))}
            </div>
          </div>
          <div>
            <h2 className="text-sm font-semibold text-ink">How</h2>
            <div className="mt-2 flex gap-2" role="group" aria-label="How to have the talk">
              {(["video", "audio", "text"] as Mode[]).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => save.mutate({ mode: m })}
                  aria-pressed={s?.mode === m}
                  className={`flex-1 rounded-lg border px-2 py-1.5 text-sm ${s?.mode === m ? "border-brand bg-brand-soft text-ink" : "border-line text-ink-soft"}`}
                >
                  {m === "video" ? "Watch" : m === "audio" ? "Listen" : "Read"}
                </button>
              ))}
            </div>
          </div>
          <label className="flex items-center justify-between gap-3 text-sm text-ink">
            Pause the talks
            <input type="checkbox" checked={!!s?.paused} onChange={(e) => save.mutate({ paused: e.target.checked })} />
          </label>
        </aside>
      </div>
    </div>
  );
}
