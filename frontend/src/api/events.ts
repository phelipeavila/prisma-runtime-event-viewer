import { api } from "./client";
import type { EventRow } from "@/lib/columns";
import type { Filters } from "@/lib/filterSchema";

export type QueryResponse = {
  rows: EventRow[];
  page: number;
  page_size: number;
  total: number;
};

export type FacetResponse = {
  field: string;
  values: { value: string; count: number }[];
  distinct: number;
};

export const events = {
  query: (filters: Filters) => api.post<QueryResponse>("/api/events/query", filters),
  facets: (field: string) => api.get<FacetResponse>(`/api/events/facets?field=${encodeURIComponent(field)}`),
};
