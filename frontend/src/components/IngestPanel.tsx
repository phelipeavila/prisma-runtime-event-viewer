import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { ingest, subscribeProgress } from "@/api/ingest";
import { TIME_PRESETS, presetRange, isoToLocal, localToIso } from "@/lib/timeRange";
import { useIngestStore } from "@/state/ingestStore";
import { useToastStore } from "@/state/toastStore";

export function IngestPanel() {
  const progress = useIngestStore((s) => s.progress);
  const setProgress = useIngestStore((s) => s.setProgress);
  const push = useToastStore((s) => s.push);
  const qc = useQueryClient();

  const initial = presetRange(24 * 60 * 60 * 1000);
  const [from, setFrom] = useState(isoToLocal(initial.from));
  const [to, setTo] = useState(isoToLocal(initial.to));
  const [chunks, setChunks] = useState(8);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    return () => {
      esRef.current?.close();
    };
  }, []);

  function applyPreset(ms: number) {
    const r = presetRange(ms);
    setFrom(isoToLocal(r.from));
    setTo(isoToLocal(r.to));
  }

  async function load() {
    if (esRef.current) esRef.current.close();
    try {
      await ingest.start({
        from: localToIso(from),
        to: localToIso(to),
        chunks,
      });
      setProgress({
        ...progress,
        status: "running",
        chunks_total: chunks,
        chunks_done: 0,
        rows_loaded: 0,
        retries: 0,
        error: null,
      });
      esRef.current = subscribeProgress(
        (p) => setProgress(p),
        () => {
          push("Load complete", "info");
          qc.invalidateQueries({ queryKey: ["events"] });
          qc.invalidateQueries({ queryKey: ["meta"] });
          qc.invalidateQueries({ queryKey: ["facets"] });
        },
        (msg) => push(`Load error: ${msg}`, "error")
      );
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      push(`Failed to start: ${msg}`, "error");
    }
  }

  const running = progress.status === "running";

  return (
    <div className="panel" style={{ marginBottom: 12 }}>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <strong>Load Audit Window</strong>
        <div className="row" style={{ gap: 4 }}>
          {TIME_PRESETS.map((p) => (
            <button key={p.label} onClick={() => applyPreset(p.ms)} disabled={running}>
              {p.label}
            </button>
          ))}
        </div>
      </div>
      <div className="row" style={{ marginTop: 12 }}>
        <label className="col">
          <span className="label">From (local)</span>
          <input
            type="datetime-local"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
            disabled={running}
          />
        </label>
        <label className="col">
          <span className="label">To (local)</span>
          <input
            type="datetime-local"
            value={to}
            onChange={(e) => setTo(e.target.value)}
            disabled={running}
          />
        </label>
        <label className="col">
          <span className="label">Parallel chunks ({chunks})</span>
          <input
            type="range"
            min={1}
            max={16}
            value={chunks}
            onChange={(e) => setChunks(parseInt(e.target.value, 10))}
            disabled={running}
          />
        </label>
        <span className="grow" />
        <button className="primary" onClick={load} disabled={running}>
          {running ? "Loading…" : "Load"}
        </button>
      </div>
      {(progress.status !== "idle" || running) && (
        <div style={{ marginTop: 12 }}>
          <ProgressBar progress={progress} />
        </div>
      )}
    </div>
  );
}

function ProgressBar({ progress }: { progress: ReturnType<typeof useIngestStore.getState>["progress"] }) {
  const pct =
    progress.chunks_total > 0
      ? Math.round((progress.chunks_done / progress.chunks_total) * 100)
      : 0;
  return (
    <div className="col">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <span className="meta">
          {progress.status} · chunks {progress.chunks_done}/{progress.chunks_total} · rows{" "}
          <strong>{progress.rows_loaded.toLocaleString()}</strong>
          {progress.retries > 0 && <> · retries {progress.retries}</>}
          {progress.error && <> · <span style={{ color: "var(--danger)" }}>{progress.error}</span></>}
        </span>
      </div>
      <div className={`progress ${progress.status === "running" && pct === 0 ? "indeterminate" : ""}`}>
        <div className="bar" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
