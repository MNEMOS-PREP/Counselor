/**
 * M16 — Counselor · API client.
 *
 * One hook per backend endpoint, and no hook without one. A talk is written
 * in the background after an interview, so `useEpisode` polls while it says
 * "writing" and stops the moment it is ready.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@ai/core";

import type { Check, Counselor, Episode, Settings, Walkthrough } from "./types";

const C = "/v1/counsel";

export const m16Keys = {
  counselors: ["m16", "counselors"] as const,
  settings: (cid: string) => ["m16", "settings", cid] as const,
  check: (cid: string) => ["m16", "check", cid] as const,
  episodes: (cid: string) => ["m16", "episodes", cid] as const,
  episode: (id: string) => ["m16", "episode", id] as const,
  walk: (sessionId: string, counselorId: string) => ["m16", "walk", sessionId, counselorId] as const,
};

export function useCounselors() {
  return useQuery({
    queryKey: m16Keys.counselors,
    queryFn: () => api.get<Counselor[]>(`${C}/counselors`),
    staleTime: Infinity,
  });
}

export function useSettings(candidateId: string | null) {
  return useQuery({
    queryKey: m16Keys.settings(candidateId ?? ""),
    queryFn: () => api.get<Settings>(`${C}/candidates/${candidateId}/settings`),
    enabled: !!candidateId,
  });
}

export function useSaveSettings(candidateId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<Pick<Settings, "every" | "counselor_id" | "mode" | "paused">>) =>
      api.put<Settings>(`${C}/candidates/${candidateId}/settings`, body),
    onSuccess: (saved) => {
      qc.setQueryData(m16Keys.settings(saved.candidate_id), saved);
      // A talk not yet heard is rewritten in the newly chosen voice.
      void qc.invalidateQueries({ queryKey: ["m16", "episode"] });
      void qc.invalidateQueries({ queryKey: m16Keys.check(saved.candidate_id) });
    },
  });
}

/** A talk to watch, or how many interviews until the next one. Makes the
 *  talk when it is due, so call it where a student lands after interviews. */
export function useCheck(candidateId: string | null, enabled = true) {
  return useQuery({
    queryKey: m16Keys.check(candidateId ?? ""),
    queryFn: () => api.post<Check>(`${C}/candidates/${candidateId}/check`),
    enabled: !!candidateId && enabled,
    refetchInterval: (query) => (query.state.data?.episode?.status === "writing" ? 2500 : false),
    refetchOnWindowFocus: true,
  });
}

export function useEpisodes(candidateId: string | null) {
  return useQuery({
    queryKey: m16Keys.episodes(candidateId ?? ""),
    queryFn: () => api.get<Episode[]>(`${C}/candidates/${candidateId}/episodes`),
    enabled: !!candidateId,
  });
}

export function useEpisode(id: string | undefined) {
  return useQuery({
    queryKey: m16Keys.episode(id ?? ""),
    queryFn: () => api.get<Episode>(`${C}/episodes/${id}`),
    enabled: !!id,
    refetchInterval: (query) => (query.state.data?.status === "writing" ? 2000 : false),
  });
}

export function useProgress(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { reached: string; finished?: boolean }) =>
      api.post<Episode>(`${C}/episodes/${id}/progress`, body),
    onSuccess: (episode) => {
      qc.setQueryData(m16Keys.episode(id), episode);
      if (episode.watched_at) {
        void qc.invalidateQueries({ queryKey: m16Keys.check(episode.candidate_id) });
        void qc.invalidateQueries({ queryKey: m16Keys.episodes(episode.candidate_id) });
      }
    },
  });
}

export function useAnswer(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (option: string) => api.post<Episode>(`${C}/episodes/${id}/answer`, { option }),
    onSuccess: (episode) => qc.setQueryData(m16Keys.episode(id), episode),
  });
}

/** "Go through my notes with me": the walk through one interview's notes in
 *  the chosen mentor's voice. The POST opens the one already made or starts
 *  writing one (minutes: it waits for the notes, then one question at a time),
 *  so it is polled while it says "writing". Keyed by mentor, because another
 *  mentor's walk is another walk. */
export function useWalkthrough(candidateId: string | null, sessionId: string | undefined, counselorId: string | undefined) {
  return useQuery({
    queryKey: m16Keys.walk(sessionId ?? "", counselorId ?? ""),
    queryFn: () =>
      api.post<Walkthrough>(`${C}/candidates/${candidateId}/walkthroughs`, { session_id: sessionId }),
    enabled: !!candidateId && !!sessionId && !!counselorId,
    refetchInterval: (query) => (query.state.data?.status === "writing" ? 3000 : false),
    staleTime: Infinity,
  });
}

export function useWalkProgress(walk: Walkthrough) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { reached: string; finished?: boolean }) =>
      api.post<Walkthrough>(`${C}/walkthroughs/${walk.id}/progress`, body),
    onSuccess: (saved) => qc.setQueryData(m16Keys.walk(saved.session_id, saved.counselor.id), saved),
  });
}
