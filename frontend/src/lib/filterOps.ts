// Operator catalog and per-column-type operator metadata.
//
// Single source of truth for the filter chip UI and the JSON payload sent to
// the backend. Each operator has a stable id, a human label, and a `valueKind`
// describing what kind of value editor it needs:
//   - "none"  → no value (e.g. is_empty)
//   - "one"   → a single string/number
//   - "many"  → a list of strings (multi-tag / facet checkbox list)
//   - "range" → a numeric range (min, max)

export type ColumnType = "string" | "number" | "bool" | "array" | "datetime";

export type ValueKind = "none" | "one" | "many" | "range";

export type OpId =
  // string + datetime
  | "is_one_of"
  | "is_not_one_of"
  | "equals"
  | "not_equals"
  | "contains"
  | "not_contains"
  | "starts_with"
  | "ends_with"
  | "is_empty"
  | "is_not_empty"
  // array
  | "contains_any"
  | "contains_all"
  | "not_contains_any"
  // number
  | "eq"
  | "neq"
  | "lt"
  | "lte"
  | "gt"
  | "gte"
  | "between"
  // bool
  | "is_true"
  | "is_false";

export type OpDef = {
  id: OpId;
  label: string;
  valueKind: ValueKind;
};

export const OPS: Record<OpId, OpDef> = {
  is_one_of:        { id: "is_one_of",        label: "is one of",         valueKind: "many"  },
  is_not_one_of:    { id: "is_not_one_of",    label: "is not one of",     valueKind: "many"  },
  equals:           { id: "equals",           label: "equals",            valueKind: "one"   },
  not_equals:       { id: "not_equals",       label: "does not equal",    valueKind: "one"   },
  contains:         { id: "contains",         label: "contains",          valueKind: "one"   },
  not_contains:     { id: "not_contains",     label: "does not contain",  valueKind: "one"   },
  starts_with:      { id: "starts_with",      label: "starts with",       valueKind: "one"   },
  ends_with:        { id: "ends_with",        label: "ends with",         valueKind: "one"   },
  is_empty:         { id: "is_empty",         label: "is empty",          valueKind: "none"  },
  is_not_empty:     { id: "is_not_empty",     label: "is not empty",      valueKind: "none"  },
  contains_any:     { id: "contains_any",     label: "contains any of",   valueKind: "many"  },
  contains_all:     { id: "contains_all",     label: "contains all of",   valueKind: "many"  },
  not_contains_any: { id: "not_contains_any", label: "does not contain",  valueKind: "many"  },
  eq:               { id: "eq",               label: "=",                 valueKind: "one"   },
  neq:              { id: "neq",              label: "≠",                 valueKind: "one"   },
  lt:               { id: "lt",               label: "<",                 valueKind: "one"   },
  lte:              { id: "lte",              label: "≤",                 valueKind: "one"   },
  gt:               { id: "gt",               label: ">",                 valueKind: "one"   },
  gte:              { id: "gte",              label: "≥",                 valueKind: "one"   },
  between:          { id: "between",          label: "between",           valueKind: "range" },
  is_true:          { id: "is_true",          label: "is true",           valueKind: "none"  },
  is_false:         { id: "is_false",         label: "is false",          valueKind: "none"  },
};

export const OPS_FOR_TYPE: Record<ColumnType, OpId[]> = {
  string: [
    "is_one_of",
    "is_not_one_of",
    "equals",
    "not_equals",
    "contains",
    "not_contains",
    "starts_with",
    "ends_with",
    "is_empty",
    "is_not_empty",
  ],
  array: [
    "contains_any",
    "contains_all",
    "not_contains_any",
    "is_empty",
    "is_not_empty",
  ],
  number: [
    "eq",
    "neq",
    "lt",
    "lte",
    "gt",
    "gte",
    "between",
    "is_empty",
    "is_not_empty",
  ],
  bool: ["is_true", "is_false"],
  datetime: ["is_empty", "is_not_empty"],
};

export const DEFAULT_OP_FOR_TYPE: Record<ColumnType, OpId> = {
  string: "is_one_of",
  array: "contains_any",
  number: "eq",
  bool: "is_true",
  datetime: "is_not_empty",
};

export function opsForType(t: ColumnType): OpDef[] {
  return OPS_FOR_TYPE[t].map((id) => OPS[id]);
}
