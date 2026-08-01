import type {
  AnalysisResult,
  ExportFormat,
  ExportResult,
  GenerateRequest,
  ImportResult,
  JobProgress,
} from "../types";

declare global {
  interface Window {
    aiDjEditStudio?: { backendBaseUrl: string };
  }
}

const BASE_URL = window.aiDjEditStudio?.backendBaseUrl ?? "http://127.0.0.1:8742";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, init);
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

/** Builds a playable/downloadable URL for a path returned by the backend
 * (relative to that session's working directory, e.g. "stems/vocals.wav"
 * or "edits/<edit_id>/preview.wav"). */
export function fileUrl(sessionId: string, relativePath: string): string {
  return `${BASE_URL}/sessions/${sessionId}/${relativePath.replace(/^\/+/, "")}`;
}

export function importFile(file: File): Promise<ImportResult> {
  const form = new FormData();
  form.append("file", file);
  return request<ImportResult>("/import", { method: "POST", body: form });
}

export function getAnalysis(sessionId: string, force = false): Promise<AnalysisResult> {
  return request<AnalysisResult>(`/analysis/${sessionId}${force ? "?force=true" : ""}`);
}

export function startSeparation(sessionId: string): Promise<{ job_id: string; cached: boolean }> {
  return request(`/separation/${sessionId}`, { method: "POST" });
}

export function startGenerate(req: GenerateRequest): Promise<{ job_id: string }> {
  return request("/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
}

export function exportEdit(
  sessionId: string,
  editId: string,
  formats: ExportFormat[]
): Promise<ExportResult> {
  return request("/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, edit_id: editId, formats }),
  });
}

/** Subscribes to live progress for a job over WebSocket. Returns an
 * unsubscribe function. */
export function subscribeJob(jobId: string, onUpdate: (progress: JobProgress) => void): () => void {
  const wsUrl = `${BASE_URL.replace(/^http/, "ws")}/jobs/${jobId}/ws`;
  const ws = new WebSocket(wsUrl);
  ws.onmessage = (event) => {
    onUpdate(JSON.parse(event.data as string) as JobProgress);
  };
  return () => ws.close();
}
