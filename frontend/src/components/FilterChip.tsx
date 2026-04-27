import { useEffect, useRef, useState } from "react";

import { columnByField } from "@/lib/filterCatalog";
import { isAtomActive } from "@/lib/filterAtom";
import { OPS, type OpId, opsForType } from "@/lib/filterOps";
import type { FilterAtom } from "@/lib/filterSchema";
import { usePopoverAnchor } from "@/lib/usePopoverAnchor";
import { useFiltersStore } from "@/state/filtersStore";

import { ContainsInput } from "@/components/filters/ContainsInput";
import { FacetCheckboxList } from "@/components/filters/FacetCheckboxList";
import { MultiTagInput } from "@/components/filters/MultiTagInput";

type Props = {
  atom: FilterAtom;
  autoOpen?: boolean;
  onClose?: () => void;
};

// While the popover is open, the chip keeps a local draft of (op, value).
// All edits write to the draft only — the store atom (and therefore the table
// query) doesn't change until the user closes the popover (Done or click-outside),
// at which point we commit the draft via `updateAtom`.
export function FilterChip({ atom, autoOpen, onClose }: Props) {
  const updateAtom = useFiltersStore((s) => s.updateAtom);
  const removeAtom = useFiltersStore((s) => s.removeAtom);

  const [open, setOpen] = useState(!!autoOpen);
  const [draftOp, setDraftOp] = useState<OpId>(atom.op);
  const [draftValue, setDraftValue] = useState<unknown>(atom.value);

  const ref = useRef<HTMLDivElement | null>(null);
  const { setTrigger, side } = usePopoverAnchor<HTMLDivElement>(open, 320);

  // Latest draft refs so the unmount/close commit always uses fresh values.
  const draftRef = useRef({ op: draftOp, value: draftValue });
  useEffect(() => {
    draftRef.current = { op: draftOp, value: draftValue };
  }, [draftOp, draftValue]);

  // Commit the draft to the store. Called when the popover closes.
  function commit() {
    const { op, value } = draftRef.current;
    if (op !== atom.op || !sameValue(value, atom.value)) {
      updateAtom(atom.id, { op, value });
    }
  }

  function closePopover() {
    if (!open) return;
    commit();
    setOpen(false);
    onClose?.();
  }

  // Reset the draft to the (possibly updated) atom whenever the popover opens.
  useEffect(() => {
    if (open) {
      setDraftOp(atom.op);
      setDraftValue(atom.value);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // Click-outside closes the popover and commits.
  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        closePopover();
      }
    }
    if (open) document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // Commit on unmount if the popover was still open.
  useEffect(() => {
    return () => {
      if (open) commit();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const def = columnByField(atom.field);
  if (!def) return null;

  const ops = opsForType(def.type);

  function changeOp(nextOp: OpId) {
    const prev = OPS[draftOp];
    const next = OPS[nextOp];
    setDraftOp(nextOp);
    if (prev.valueKind !== next.valueKind) {
      setDraftValue(undefined);
    }
  }

  // The chip pill always shows the committed atom — the visible UI stays in
  // sync with the table's results.
  const committedOpDef = OPS[atom.op];
  const summary = summarize(atom);
  const active = isAtomActive(atom);

  return (
    <div
      className="filter-chip"
      ref={(el) => {
        ref.current = el;
        setTrigger(el);
      }}
    >
      <button
        type="button"
        className={`chip-pill ${active ? "active" : ""}`}
        onClick={() => (open ? closePopover() : setOpen(true))}
        title={`${def.label} ${committedOpDef.label} ${summary}`}
      >
        <span className="chip-label">{def.label}</span>
        <span className="chip-value">
          {committedOpDef.label}
          {committedOpDef.valueKind !== "none" ? ` ${summary}` : ""}
        </span>
      </button>
      <button
        type="button"
        className="chip-remove"
        onClick={() => removeAtom(atom.id)}
        title="Remove filter"
        aria-label={`Remove ${def.label} filter`}
      >
        ×
      </button>
      {open && (
        <div className={`chip-popover anchor-${side}`}>
          <div className="chip-popover-head">
            <strong>{def.label}</strong>
            <select
              value={draftOp}
              onChange={(e) => changeOp(e.target.value as OpId)}
              style={{ marginLeft: 8 }}
            >
              {ops.map((o) => (
                <option key={o.id} value={o.id}>{o.label}</option>
              ))}
            </select>
            <span className="grow" />
            <button onClick={closePopover}>Done</button>
          </div>
          <div className="chip-popover-body">
            <ValueEditor
              field={atom.field}
              op={draftOp}
              value={draftValue}
              onChange={setDraftValue}
            />
          </div>
        </div>
      )}
    </div>
  );
}

function ValueEditor({
  field,
  op,
  value,
  onChange,
}: {
  field: string;
  op: OpId;
  value: unknown;
  onChange: (next: unknown) => void;
}) {
  const def = columnByField(field);
  if (!def) return null;
  const opDef = OPS[op];

  if (opDef.valueKind === "none") {
    return (
      <div className="meta" style={{ fontSize: 12 }}>
        No value needed for this operator.
      </div>
    );
  }

  if (opDef.valueKind === "many") {
    const values = (value as string[] | undefined) ?? [];
    if (def.facetField) {
      return (
        <FacetCheckboxList
          field={def.facetField}
          selected={values}
          onChange={(v) => onChange(v.length ? v : undefined)}
        />
      );
    }
    return (
      <MultiTagInput
        values={values}
        onChange={(v) => onChange(v.length ? v : undefined)}
      />
    );
  }

  if (opDef.valueKind === "range") {
    const v = (value as { min?: number; max?: number } | undefined) ?? {};
    return (
      <div className="col" style={{ gap: 6, minWidth: 220 }}>
        <label className="row" style={{ gap: 6 }}>
          <span className="label" style={{ width: 36 }}>min</span>
          <input
            type="number"
            value={v.min ?? ""}
            onChange={(e) =>
              onChange({
                ...v,
                min: e.target.value === "" ? undefined : Number(e.target.value),
              })
            }
            style={{ flex: 1 }}
          />
        </label>
        <label className="row" style={{ gap: 6 }}>
          <span className="label" style={{ width: 36 }}>max</span>
          <input
            type="number"
            value={v.max ?? ""}
            onChange={(e) =>
              onChange({
                ...v,
                max: e.target.value === "" ? undefined : Number(e.target.value),
              })
            }
            style={{ flex: 1 }}
          />
        </label>
      </div>
    );
  }

  // valueKind === "one"
  if (def.type === "number") {
    const n = value as number | undefined;
    return (
      <input
        autoFocus
        type="number"
        value={n ?? ""}
        onChange={(e) =>
          onChange(e.target.value === "" ? undefined : Number(e.target.value))
        }
        style={{ minWidth: 220 }}
      />
    );
  }
  return (
    <ContainsInput
      value={value as string | undefined}
      onChange={(v) => onChange(v || undefined)}
      placeholder={
        op === "contains" || op === "not_contains"
          ? "substring (case-insensitive)"
          : op === "starts_with"
          ? "prefix"
          : op === "ends_with"
          ? "suffix"
          : "value"
      }
    />
  );
}

function sameValue(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) return false;
    for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return false;
    return true;
  }
  if (
    a && b &&
    typeof a === "object" && typeof b === "object" &&
    "min" in a && "min" in b
  ) {
    const ar = a as { min?: number; max?: number };
    const br = b as { min?: number; max?: number };
    return ar.min === br.min && ar.max === br.max;
  }
  return false;
}

function summarize(atom: FilterAtom): string {
  const op = OPS[atom.op];
  if (!op || op.valueKind === "none") return "";
  const v = atom.value;
  if (op.valueKind === "many") {
    const arr = (v as string[] | undefined) ?? [];
    if (arr.length === 0) return "—";
    if (arr.length === 1) return arr[0];
    if (arr.length <= 3) return arr.join(", ");
    return `${arr.slice(0, 2).join(", ")} +${arr.length - 2}`;
  }
  if (op.valueKind === "range") {
    const r = (v as { min?: number; max?: number } | undefined) ?? {};
    if (r.min !== undefined && r.max !== undefined) return `${r.min} – ${r.max}`;
    if (r.min !== undefined) return `≥ ${r.min}`;
    if (r.max !== undefined) return `≤ ${r.max}`;
    return "—";
  }
  if (v === undefined || v === null || v === "") return "—";
  if (typeof v === "string") return `"${v}"`;
  return String(v);
}
