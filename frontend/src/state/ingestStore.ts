import { create } from "zustand";
import type { IngestProgress } from "@/api/ingest";

type IngestStore = {
  progress: IngestProgress;
  setProgress: (p: IngestProgress) => void;
  reset: () => void;
};

const DEFAULT: IngestProgress = {
  status: "idle",
  rows_loaded: 0,
  chunks_total: 0,
  chunks_done: 0,
  retries: 0,
  error: null,
  started_at: null,
  finished_at: null,
  from_ts: null,
  to_ts: null,
};

export const useIngestStore = create<IngestStore>((set) => ({
  progress: { ...DEFAULT },
  setProgress: (p) => set({ progress: p }),
  reset: () => set({ progress: { ...DEFAULT } }),
}));
