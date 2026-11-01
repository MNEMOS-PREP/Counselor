/**
 * Saying a chapter, and knowing when it has been heard — the talk's player
 * and the walk's share it.
 *
 * The voice goes quiet between two sentences of one line when the next is
 * still being made (its `speakingKey` clears whenever the track runs dry).
 * So a chapter is over only when its LAST line has been heard and the voice
 * is then quiet; a gap before that is waited out, for at most GRACE_MS. With
 * no voice (Read, or voice off) the words get their reading time instead.
 */

import { useCallback, useEffect, useRef } from "react";

import type { InterviewerVoice, SpokenPart } from "@ai/core";

const PAUSE_AFTER_MS = 450;
/** The longest a chapter waits for a sentence still being made before it moves on. */
const GRACE_MS = 20_000;

export interface SaidLine {
  id: string;
  text: string;
}

export function useNarration({
  voice,
  speaker,
  silent,
}: {
  voice: InterviewerVoice;
  /** Who says it: their persona id and voice. */
  speaker: { id: string; voice_id: string };
  /** Words on screen only: no voice is asked to speak. */
  silent: boolean;
}) {
  const saying = useRef<string | null>(null);
  const heard = useRef(false);
  const lastPart = useRef<string | null>(null);
  const lastHeard = useRef(false);
  const grace = useRef<number | null>(null);
  const fallbackTimer = useRef<number | null>(null);
  /** Told when a chapter (by the key it was said under) was heard to its end.
   *  A ref, set by the player each render: it reads the chapter being played,
   *  so timers and the voice's effect call the latest one, never the one from
   *  when they were set. */
  const onFinished = useRef<(key: string) => void>(() => undefined);
  // The hook hands back a new object each render: speak through the latest.
  const latest = useRef(voice);
  latest.current = voice;

  const parts = useCallback(
    (lines: SaidLine[]): SpokenPart[] =>
      lines.map((l) => ({
        text: l.text,
        personaId: speaker.id,
        voiceId: speaker.voice_id,
        id: l.id,
        pauseAfterMs: PAUSE_AFTER_MS,
      })),
    [speaker.id, speaker.voice_id],
  );

  const clearTimers = useCallback(() => {
    if (grace.current) window.clearTimeout(grace.current);
    if (fallbackTimer.current) window.clearTimeout(fallbackTimer.current);
    grace.current = null;
    fallbackTimer.current = null;
  }, []);

  const end = useCallback((key: string) => {
    if (saying.current !== key) return;
    saying.current = null;
    onFinished.current(key);
  }, []);

  const say = useCallback(
    (key: string, lines: SaidLine[]) => {
      saying.current = key;
      heard.current = false;
      lastPart.current = lines[lines.length - 1]?.id ?? null;
      lastHeard.current = false;
      clearTimers();
      const voice = latest.current;
      if (!silent && voice.enabled && voice.supported) {
        voice.speak(parts(lines), key);
      } else {
        // No voice: give the words their reading time, then move on.
        const words = lines.reduce((n, l) => n + l.text.split(/\s+/).length, 0);
        fallbackTimer.current = window.setTimeout(() => end(key), Math.max(2500, words * 330));
      }
    },
    [silent, parts, clearTimers, end],
  );

  /** Stop without ending: a stop is not an ending, and the next chapter must not start. */
  const halt = useCallback(() => {
    saying.current = null;
    clearTimers();
  }, [clearTimers]);

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
      if (lastHeard.current) end(key);
      else if (!grace.current) {
        // A sentence still being made: wait for it, but never for ever.
        grace.current = window.setTimeout(() => {
          grace.current = null;
          end(key);
        }, GRACE_MS);
      }
    }
  }, [voice.speakingKey, voice.speakingPart, end]);

  return { say, halt, parts, onFinished };
}
