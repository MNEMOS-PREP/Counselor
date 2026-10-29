/**
 * M16 — Counselor · routes. `counsel` is a noun no other module's screens use.
 */

import { Route } from "react-router-dom";

import { CounselHome } from "./components/CounselHome";
import { EpisodePlayer } from "./components/EpisodePlayer";

export const m16Routes = (
  <Route key="m16">
    <Route path="/counsel" element={<CounselHome />} />
    <Route path="/counsel/:episodeId" element={<EpisodePlayer />} />
  </Route>
);
