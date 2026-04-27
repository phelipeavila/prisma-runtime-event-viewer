import { useEffect, useMemo, useRef, useState } from "react";

import { COLUMN_DEFS, type ColumnDef } from "@/lib/filterCatalog";
import { usePopoverAnchor } from "@/lib/usePopoverAnchor";

type Props = {
  onPick: (def: ColumnDef) => void;
};

export function AddFilterMenu({ onPick }: Props) {
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState("");
  const ref = useRef<HTMLDivElement | null>(null);
  const { setTrigger, side } = usePopoverAnchor<HTMLDivElement>(open, 320);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    if (open) document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [open]);

  const grouped = useMemo(() => {
    const lower = filter.trim().toLowerCase();
    const groups = new Map<string, ColumnDef[]>();
    for (const d of COLUMN_DEFS) {
      if (lower) {
        const hay = `${d.label} ${d.field} ${d.group}`.toLowerCase();
        if (!hay.includes(lower)) continue;
      }
      const arr = groups.get(d.group) || [];
      arr.push(d);
      groups.set(d.group, arr);
    }
    return Array.from(groups.entries());
  }, [filter]);

  return (
    <div
      className="split-button"
      ref={(el) => {
        ref.current = el;
        setTrigger(el);
      }}
    >
      <button onClick={() => setOpen((v) => !v)}>+ Add filter</button>
      {open && (
        <div
          className={`menu anchor-${side}`}
          style={{ minWidth: 320, maxHeight: 420, overflow: "auto", padding: 8 }}
        >
          <input
            autoFocus
            placeholder="Find a column…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            style={{ width: "100%", marginBottom: 8 }}
          />
          {grouped.length === 0 && <div className="meta" style={{ fontSize: 12 }}>No matches</div>}
          {grouped.map(([group, defs]) => (
            <div key={group} style={{ marginBottom: 6 }}>
              <div className="label" style={{ padding: "4px 4px 2px" }}>{group}</div>
              {defs.map((d) => (
                <button
                  key={d.field}
                  onClick={() => {
                    onPick(d);
                    setOpen(false);
                  }}
                  style={{
                    width: "100%",
                    textAlign: "left",
                    background: "transparent",
                    border: "none",
                    padding: "4px 6px",
                    borderRadius: 4,
                    fontSize: 13,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                  }}
                >
                  <span style={{ flex: 1 }}>{d.label}</span>
                  <span className="meta" style={{ fontSize: 11 }}>{d.type}</span>
                </button>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
