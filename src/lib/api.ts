/**
 * api.ts — Centralised API client for the Turing frontend.
 *
 * All fetch calls should use `apiUrl()` to build endpoints so that
 * deploying to staging/production only requires setting the
 * NEXT_PUBLIC_API_URL environment variable.
 */

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

/** Convenience helper: join base URL with a path segment. */
export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

// ---------------------------------------------------------------------------
// Runs
// ---------------------------------------------------------------------------

export interface RunResponse {
  id: string;
  status: "PENDING" | "RUNNING" | "COMPLETE" | "FAILED";
  input_file: string;
  input_type: string;
  created_at: string;
  updated_at: string;
  causal_graph: unknown | null;
  top_bridges: unknown[] | null;
  error_message: string | null;
}

/**
 * POST /api/runs/
 * Creates a new run record in the database and returns its ID.
 */
export async function createRun(
  inputFile: string,
  inputType: "csv" | "text"
): Promise<RunResponse> {
  const res = await fetch(apiUrl("/api/runs/"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ input_file: inputFile, input_type: inputType }),
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Failed to create run: ${res.status} — ${detail}`);
  }

  return res.json() as Promise<RunResponse>;
}

/**
 * POST /api/runs/{runId}/layer1/upload
 * Uploads the raw dataset file and kicks off the Layer 1 background pipeline.
 */
export async function uploadDataset(runId: string, file: File): Promise<void> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(apiUrl(`/api/runs/${runId}/layer1/upload`), {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Upload failed: ${res.status} — ${detail}`);
  }
}

/**
 * GET /api/runs/
 * Lists the most recent runs (newest first).
 */
export async function listRuns(limit = 20): Promise<RunResponse[]> {
  const res = await fetch(apiUrl(`/api/runs/?limit=${limit}`), {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`Failed to list runs: ${res.status}`);
  }

  return res.json() as Promise<RunResponse[]>;
}

// ---------------------------------------------------------------------------
// System health & version
// ---------------------------------------------------------------------------

export type HealthStatus = "online" | "offline" | "checking";

export interface EngineInfo {
  status: string;
  service: string;
  version: string;
}

/**
 * GET /health
 * Returns true when the backend responds with {"status":"healthy"}.
 * Uses AbortSignal so a dead backend resolves quickly (3 s timeout).
 */
export async function fetchHealth(): Promise<boolean> {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 3000);
    const res = await fetch(apiUrl("/health"), {
      cache: "no-store",
      signal: controller.signal,
    });
    clearTimeout(timer);
    return res.ok;
  } catch {
    return false;
  }
}

/**
 * GET /
 * Returns engine metadata including the authoritative version string.
 * Falls back to null if the backend is unreachable.
 */
export async function fetchEngineInfo(): Promise<EngineInfo | null> {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 3000);
    const res = await fetch(apiUrl("/"), {
      cache: "no-store",
      signal: controller.signal,
    });
    clearTimeout(timer);
    if (!res.ok) return null;
    return res.json() as Promise<EngineInfo>;
  } catch {
    return null;
  }
}
