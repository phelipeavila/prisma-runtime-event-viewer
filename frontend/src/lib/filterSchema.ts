// New atom-based filter shape.
//
// `atoms` carries the per-column filter conditions; `from`/`to` are the
// time-range filters (set by the ingest panel) and `sort`/`reverse`/`page`/
// `page_size` are the table state. Everything is sent verbatim to the backend.
import type { OpId } from "@/lib/filterOps";

export type FilterAtom = {
  id: string;        // local unique id (UI tracking)
  field: string;     // backend column name
  op: OpId;
  value?: unknown;   // string | string[] | number | { min?: number; max?: number }
};

export type Filters = {
  atoms: FilterAtom[];
  from?: string;
  to?: string;
  sort?: string;
  reverse?: boolean;
  page?: number;
  page_size?: number;
};
