/**
 * Who would you like to talk to? — asked once, before the first talk.
 *
 * Four people, each a face (AI-generated, labelled so) and a voice. "Hear"
 * plays a line in their own voice, because a counselor is chosen by how they
 * sound as much as by how they look. The choice changes the manner of every
 * talk; it never changes the facts in one.
 */

import { useState } from "react";

import { InterviewerPhoto, Spinner, useInterviewerVoice } from "@ai/core";

import { useCounselors, useSaveSettings } from "../api";

export function CounselorPicker({
  candidateId,
  studentName,
  current,
  onChosen,
}: {
  candidateId: string | null;
  studentName: string;
  current?: string;
  onChosen?: () => void;
}) {
  const counselors = useCounselors();
  const save = useSaveSettings(candidateId);
  // Each sample names its own speaker (personaId on the part), so one voice
  // hook can say all four.
  const voice = useInterviewerVoice(null);
  const [picked, setPicked] = useState<string | null>(current ?? null);
  const first = studentName.trim().split(/\s+/)[0] || "there";

  if (counselors.isLoading) return <Spinner label="Loading" />;
  const people = counselors.data ?? [];

  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-10">
      <p className="text-sm font-medium uppercase tracking-wider text-brand">Before your first talk</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink">Who would you like to talk to?</h1>
      <p className="mt-2 max-w-2xl text-ink-soft">
        After your interviews, one person goes through how it went, what to work on, and what to do next. Pick the
        one you'd listen to. You can change them any time.
      </p>
      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {people.map((p) => {
          const chosen = picked === p.id;
          return (
            <div
              key={p.id}
              className={`flex flex-col overflow-hidden rounded-2xl border bg-surface-raised transition ${
                chosen ? "border-brand ring-2 ring-brand/30" : "border-line"
              }`}
            >
              <button type="button" onClick={() => setPicked(p.id)} className="relative aspect-[4/5] w-full bg-neutral-900" aria-pressed={chosen}>
                <InterviewerPhoto persona={p.id} name={p.name} fill />
                <span className="absolute right-2 top-2 rounded bg-black/60 px-1.5 py-0.5 text-[10px] font-semibold text-white">AI</span>
              </button>
              <div className="flex flex-1 flex-col p-4">
                <p className="font-semibold text-ink">
                  {p.name} <span className="font-normal text-ink-soft">· {p.relation}</span>
                </p>
                <p className="mt-1 flex-1 text-sm text-ink-soft">{p.blurb}</p>
                <div className="mt-3 flex gap-2">
                  <button
                    type="button"
                    onClick={() =>
                      voice.speak(
                        [{ text: `Hi ${first}. I'm ${p.name}. Let's look at how your interviews are going.`, personaId: p.id, voiceId: p.voice_id, id: p.id }],
                        `sample:${p.id}`,
                      )
                    }
                    className="rounded-lg border border-line px-2.5 py-1 text-xs text-ink hover:bg-surface-sunken"
                  >
                    {voice.speakingKey === `sample:${p.id}` ? "Playing…" : "Hear"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setPicked(p.id)}
                    className={`rounded-lg px-2.5 py-1 text-xs font-medium ${chosen ? "bg-brand text-on-brand" : "border border-line text-ink hover:bg-surface-sunken"}`}
                  >
                    {chosen ? "Chosen" : "Choose"}
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
      <div className="mt-8 flex items-center gap-4">
        <button
          type="button"
          disabled={!picked || save.isPending}
          onClick={() => picked && save.mutate({ counselor_id: picked }, { onSuccess: () => onChosen?.() })}
          className="rounded-xl bg-brand px-5 py-2.5 text-sm font-semibold text-on-brand hover:bg-brand-hover disabled:opacity-50"
        >
          {save.isPending ? "Saving…" : `Talk to ${people.find((p) => p.id === picked)?.name ?? "them"}`}
        </button>
        <p className="text-xs text-ink-faint">Every face here is AI-generated. None is a real person.</p>
      </div>
    </div>
  );
}
