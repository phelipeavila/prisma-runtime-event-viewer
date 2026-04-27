import { api } from "./client";

export type IngestProgress = {
  status: "idle" | "running" | "done" | "error";
  rows_loaded: number;
  chunks_total: number;
  chunks_done: number;
  retries: number;
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
  from_ts: string | null;
  to_ts: string | null;
};

export const ingest = {
  start: (body: { from: string; to: string; chunks?: number; filters?: object }) =>
    api.post<{ status: string; chunks_total: number }>("/api/ingest", body),
  cancel: () => api.post<{ cancelled: boolean }>("/api/ingest/cancel"),
};

export function subscribeProgress(
  onProgress: (p: IngestProgress) => void,
  onDone: () => void,
  onError: (msg: string) => void
): EventSource {
  const es = new EventSource("/api/ingest/stream");
  es.addEventListener("progress", (e) => {
    try {
      onProgress(JSON.parse((e as MessageEvent).data));
    } catch {
      /* ignore */
    }
  });
  es.addEventListener("done", (e) => {
    try {
      onProgress(JSON.parse((e as MessageEvent).data));
    } catch {
      /* ignore */
    }
    onDone();
    es.close();
  });
  es.addEventListener("error", (e) => {
    try {
      const data = (e as MessageEvent).data;
      if (data) {
        const p = JSON.parse(data);
        onProgress(p);
        if (p.status === "error") {
          onError(p.error || "Ingest error");
          es.close();
          return;
        }
      }
    } catch {
      /* ignore */
    }
  });
  return es;
}
