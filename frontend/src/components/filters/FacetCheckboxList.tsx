import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { events as eventsApi } from "@/api/events";

type Props = {
  field: string;
  selected: string[];
  onChange: (next: string[]) => void;
};

/**
 * Facet-backed checkbox list with a search filter. Used inside chip popovers.
 * Falls back to a plain message if the facet returns no values.
 */
export function FacetCheckboxList({ field, selected, onChange }: Props) {
  const [filter, setFilter] = useState("");
  const { data, isLoading, error } = useQuery({
    queryKey: ["facets", field],
    queryFn: () => eventsApi.facets(field),
  });

  function toggle(v: string) {
    if (selected.includes(v)) onChange(selected.filter((x) => x !== v));
    else onChange([...selected, v]);
  }

  const lower = filter.trim().toLowerCase();
  const all = data?.values ?? [];
  const values = lower ? all.filter((v) => v.value.toLowerCase().includes(lower)) : all;

  return (
    <div className="col" style={{ minWidth: 220 }}>
      <input
        autoFocus
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        placeholder="Filter values…"
      />
      <div
        style={{
          maxHeight: 220,
          overflow: "auto",
          padding: 4,
          background: "var(--panel-2)",
          border: "1px solid var(--border)",
          borderRadius: 6,
        }}
      >
        {isLoading && <div className="meta" style={{ fontSize: 12 }}>loading…</div>}
        {error && (
          <div className="meta" style={{ fontSize: 12, color: "var(--danger)" }}>
            {error instanceof Error ? error.message : "Failed to load values"}
          </div>
        )}
        {!isLoading && !error && values.length === 0 && (
          <div className="meta" style={{ fontSize: 12 }}>
            {all.length === 0 ? "No values in cache" : "No matches"}
          </div>
        )}
        {values.map((v) => (
          <label
            key={v.value}
            style={{ display: "flex", gap: 6, fontSize: 12, padding: "2px 4px" }}
          >
            <input
              type="checkbox"
              checked={selected.includes(v.value)}
              onChange={() => toggle(v.value)}
            />
            <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {v.value}
            </span>
            <span className="meta">{v.count}</span>
          </label>
        ))}
      </div>
      {selected.length > 0 && (
        <button onClick={() => onChange([])} style={{ alignSelf: "flex-start" }}>
          Clear ({selected.length})
        </button>
      )}
    </div>
  );
}
