import { OPS } from "@/lib/filterOps";
import type { FilterAtom, Filters } from "@/lib/filterSchema";

// An atom is "active" when its operator is fully specified:
//   - none-valued ops (is_empty, is_true, ...) are always active
//   - many-valued ops require a non-empty array
//   - range ops require at least min or max
//   - one-valued ops require a non-empty value
export function isAtomActive(atom: FilterAtom): boolean {
  const op = OPS[atom.op];
  if (!op) return false;
  if (op.valueKind === "none") return true;
  const v = atom.value;
  if (v === undefined || v === null || v === "") return false;
  if (Array.isArray(v) && v.length === 0) return false;
  if (op.valueKind === "range") {
    const r = v as { min?: number; max?: number };
    return r.min !== undefined || r.max !== undefined;
  }
  return true;
}

// Returns a copy of `filters` with only the active atoms — safe to send to
// the backend. Sort/page/page_size/from/to pass through untouched.
export function selectActiveFilters(filters: Filters): Filters {
  return { ...filters, atoms: filters.atoms.filter(isAtomActive) };
}
