import { api } from "./client";
import type { IngestProgress } from "./ingest";

export type Meta = {
  authenticated: boolean;
  console_url: string | null;
  expires_at: string | null;
  ingest: IngestProgress;
  row_count: number;
  time_bounds: { min: string | null; max: string | null };
  last_filters: object | null;
};

export const meta = {
  get: () => api.get<Meta>("/api/meta"),
};
