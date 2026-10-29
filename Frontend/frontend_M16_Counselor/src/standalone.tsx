/**
 * M16 running alone on :5216.
 *
 * Same routes and components as the shell mounts — this file only supplies the
 * providers the shell would otherwise own.
 */

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { SEEDED_CANDIDATE_ID, ensureSession } from "@ai/core";

import { m16Routes } from "./routes";
// One stylesheet, on purpose: theme.css imports @ai/core/styles.css itself.
import "./ui/theme.css";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false } },
});

// Standalone, a talk is a student's: with nobody signed in, the demo student.
// NOT in `routes.tsx`: inside Platform_Shell the session is whoever signed in.
ensureSession({ role: "student", subject: SEEDED_CANDIDATE_ID, name: "Demo student" });

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {m16Routes}
          <Route path="*" element={<Navigate to="/counsel" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
