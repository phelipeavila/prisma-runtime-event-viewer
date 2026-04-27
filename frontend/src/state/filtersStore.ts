import { create } from "zustand";

import { COLUMN_BY_FIELD, defaultOpForColumn } from "@/lib/filterCatalog";
import type { FilterAtom, Filters } from "@/lib/filterSchema";
import type { OpId } from "@/lib/filterOps";

type FiltersStore = {
  filters: Filters;
  setFilters: (next: Filters | ((prev: Filters) => Filters)) => void;
  setSort: (sort: string, reverse?: boolean) => void;
  setPage: (page: number) => void;
  setPageSize: (size: number) => void;
  setTimeRange: (from?: string, to?: string) => void;
  addAtom: (field: string, op?: OpId, value?: unknown) => string; // returns id
  updateAtom: (id: string, patch: Partial<FilterAtom>) => void;
  removeAtom: (id: string) => void;
  reset: () => void;
};

let counter = 0;
function newId(): string {
  counter += 1;
  return `atom_${Date.now().toString(36)}_${counter.toString(36)}`;
}

const DEFAULT_FILTERS: Filters = {
  atoms: [],
  sort: "time",
  reverse: true,
  page: 0,
  page_size: 100,
};

export const useFiltersStore = create<FiltersStore>((set) => ({
  filters: { ...DEFAULT_FILTERS, atoms: [] },

  setFilters: (next) =>
    set((s) => ({ filters: typeof next === "function" ? next(s.filters) : next })),

  setSort: (sort, reverse) =>
    set((s) => ({ filters: { ...s.filters, sort, reverse: reverse ?? s.filters.reverse, page: 0 } })),

  setPage: (page) =>
    set((s) => ({ filters: { ...s.filters, page } })),

  setPageSize: (size) =>
    set((s) => ({ filters: { ...s.filters, page_size: size, page: 0 } })),

  setTimeRange: (from, to) =>
    set((s) => ({ filters: { ...s.filters, from, to, page: 0 } })),

  addAtom: (field, op, value) => {
    const def = COLUMN_BY_FIELD.get(field);
    if (!def) return "";
    const id = newId();
    set((s) => ({
      filters: {
        ...s.filters,
        page: 0,
        atoms: [
          ...s.filters.atoms,
          { id, field, op: op ?? defaultOpForColumn(def), value },
        ],
      },
    }));
    return id;
  },

  updateAtom: (id, patch) =>
    set((s) => ({
      filters: {
        ...s.filters,
        page: 0,
        atoms: s.filters.atoms.map((a) => (a.id === id ? { ...a, ...patch } : a)),
      },
    })),

  removeAtom: (id) =>
    set((s) => ({
      filters: {
        ...s.filters,
        page: 0,
        atoms: s.filters.atoms.filter((a) => a.id !== id),
      },
    })),

  reset: () =>
    set(() => ({ filters: { ...DEFAULT_FILTERS, atoms: [] } })),
}));
