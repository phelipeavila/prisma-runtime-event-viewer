import { useEffect, useMemo, useRef, useState } from "react";

import { COLUMN_GROUPS, columns } from "@/lib/columns";
import { usePopoverAnchor } from "@/lib/usePopoverAnchor";
import { useTableStore } from "@/state/tableStore";

type Tab = "visibility" | "order";

export function ColumnPicker() {
  const visibility = useTableStore((s) => s.columnVisibility);
  const order = useTableStore((s) => s.columnOrder);
  const toggle = useTableStore((s) => s.toggle);
  const setAll = useTableStore((s) => s.setAll);
  const reset = useTableStore((s) => s.resetVisibility);
  const moveColumn = useTableStore((s) => s.moveColumn);
  const resetOrder = useTableStore((s) => s.resetOrder);

  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<Tab>("visibility");
  const [filter, setFilter] = useState("");
  const ref = useRef<HTMLDivElement | null>(null);
  const { setTrigger, side } = usePopoverAnchor<HTMLDivElement>(open, 360);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    if (open) document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [open]);

  const headerById = useMemo(() => {
    const m = new Map<string, string>();
    for (const c of columns) m.set(c.id, c.header);
    return m;
  }, []);

  const visibleCount = Object.values(visibility).filter(Boolean).length;
  const totalCount = columns.length;

  return (
    <div
      className="split-button"
      ref={(el) => {
        ref.current = el;
        setTrigger(el);
      }}
    >
      <button onClick={() => setOpen((v) => !v)}>
        Columns ({visibleCount}/{totalCount}) ▾
      </button>
      {open && (
        <div
          className={`menu anchor-${side}`}
          style={{ minWidth: 360, maxHeight: 480, overflow: "auto", padding: 8 }}
        >
          <div className="row" style={{ gap: 4, marginBottom: 8 }}>
            <button
              className={tab === "visibility" ? "primary" : ""}
              onClick={() => setTab("visibility")}
            >
              Visibility
            </button>
            <button
              className={tab === "order" ? "primary" : ""}
              onClick={() => setTab("order")}
            >
              Order
            </button>
            <span className="grow" />
            {tab === "visibility" ? (
              <>
                <button onClick={() => setAll(true)} title="Show all">All</button>
                <button onClick={() => setAll(false)} title="Hide all">None</button>
                <button onClick={reset} title="Reset to defaults">Reset</button>
              </>
            ) : (
              <button onClick={resetOrder} title="Reset to default order">Reset</button>
            )}
          </div>

          {tab === "visibility" ? (
            <VisibilityList
              filter={filter}
              setFilter={setFilter}
              visibility={visibility}
              toggle={toggle}
              headerById={headerById}
            />
          ) : (
            <OrderList
              order={order}
              visibility={visibility}
              moveColumn={moveColumn}
              headerById={headerById}
            />
          )}
        </div>
      )}
    </div>
  );
}

function VisibilityList({
  filter,
  setFilter,
  visibility,
  toggle,
  headerById,
}: {
  filter: string;
  setFilter: (v: string) => void;
  visibility: Record<string, boolean>;
  toggle: (id: string) => void;
  headerById: Map<string, string>;
}) {
  const lower = filter.trim().toLowerCase();
  return (
    <>
      <input
        autoFocus
        placeholder="Filter…"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        style={{ width: "100%", marginBottom: 8 }}
      />
      {COLUMN_GROUPS.map((group) => {
        const ids = group.ids.filter((id) => {
          if (!lower) return true;
          const label = (headerById.get(id) || id).toLowerCase();
          return label.includes(lower) || id.includes(lower);
        });
        if (ids.length === 0) return null;
        return (
          <div key={group.label} style={{ marginBottom: 6 }}>
            <div className="label" style={{ padding: "4px 4px 2px" }}>{group.label}</div>
            {ids.map((id) => (
              <label
                key={id}
                style={{
                  display: "flex",
                  gap: 6,
                  padding: "3px 6px",
                  fontSize: 13,
                  cursor: "pointer",
                  borderRadius: 4,
                }}
              >
                <input
                  type="checkbox"
                  checked={!!visibility[id]}
                  onChange={() => toggle(id)}
                />
                <span style={{ flex: 1 }}>{headerById.get(id) || id}</span>
                <span className="meta" style={{ fontSize: 11 }}>{id}</span>
              </label>
            ))}
          </div>
        );
      })}
    </>
  );
}

function OrderList({
  order,
  visibility,
  moveColumn,
  headerById,
}: {
  order: string[];
  visibility: Record<string, boolean>;
  moveColumn: (fromId: string, toId: string) => void;
  headerById: Map<string, string>;
}) {
  const [dragId, setDragId] = useState<string | null>(null);
  const [overId, setOverId] = useState<string | null>(null);

  return (
    <>
      <div className="meta" style={{ fontSize: 11, padding: "0 4px 8px" }}>
        Drag to reorder. Hidden columns are shown faded — they'll keep their
        position if you make them visible later.
      </div>
      <div>
        {order.map((id) => {
          const visible = !!visibility[id];
          const isOver = overId === id && dragId !== id;
          return (
            <div
              key={id}
              draggable
              onDragStart={(e) => {
                setDragId(id);
                e.dataTransfer.effectAllowed = "move";
                e.dataTransfer.setData("text/plain", id);
              }}
              onDragOver={(e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = "move";
                if (overId !== id) setOverId(id);
              }}
              onDragLeave={() => {
                if (overId === id) setOverId(null);
              }}
              onDrop={(e) => {
                e.preventDefault();
                const from = e.dataTransfer.getData("text/plain") || dragId;
                if (from && from !== id) moveColumn(from, id);
                setDragId(null);
                setOverId(null);
              }}
              onDragEnd={() => {
                setDragId(null);
                setOverId(null);
              }}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "5px 6px",
                marginBottom: 1,
                fontSize: 13,
                background: isOver ? "rgba(88,166,255,0.15)" : "transparent",
                borderTop: isOver ? "1px solid var(--accent)" : "1px solid transparent",
                borderRadius: 4,
                cursor: "grab",
                opacity: visible ? 1 : 0.45,
                userSelect: "none",
              }}
            >
              <span className="meta" style={{ cursor: "grab", fontFamily: "monospace" }}>
                ⋮⋮
              </span>
              <span style={{ flex: 1 }}>{headerById.get(id) || id}</span>
              <span className="meta" style={{ fontSize: 11 }}>
                {visible ? "" : "hidden"}
              </span>
            </div>
          );
        })}
      </div>
    </>
  );
}
