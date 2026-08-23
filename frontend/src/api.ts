import type { EvalRunDetail, EvalRunSummary, Manual, QueryResult } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init);
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) message = body.detail;
    } catch {
      // ignore body parse errors
    }
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

export function listManuals(): Promise<Manual[]> {
  return request<Manual[]>("/manuals");
}

export async function uploadManual(file: File, title?: string): Promise<Manual> {
  const form = new FormData();
  form.append("file", file);
  if (title) form.append("title", title);
  return request<Manual>("/manuals", { method: "POST", body: form });
}

export function deleteManual(manualId: string): Promise<{ deleted: boolean }> {
  return request(`/manuals/${manualId}`, { method: "DELETE" });
}

export function pageImageUrl(manualId: string, page: number): string {
  return `/api/manuals/${manualId}/pages/${page}`;
}

export function queryManual(
  manualId: string,
  question: string,
  topK?: number
): Promise<QueryResult> {
  return request<QueryResult>("/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ manual_id: manualId, question, top_k: topK }),
  });
}

export function listEvalRuns(): Promise<EvalRunSummary[]> {
  return request<EvalRunSummary[]>("/eval/runs");
}

export function getEvalRun(runId: string): Promise<EvalRunDetail> {
  return request<EvalRunDetail>(`/eval/runs/${runId}`);
}
