import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type SortingState,
} from "@tanstack/react-table";

import { events as eventsApi } from "@/api/events";
import { columns, type EventRow } from "@/lib/columns";
import { selectActiveFilters } from "@/lib/filterAtom";
import { useFiltersStore } from "@/state/filtersStore";
import { useTableStore } from "@/state/tableStore";
import { AddFilterMenu } from "@/components/AddFilterMenu";
import { ColumnPicker } from "@/components/ColumnPicker";
import { ExportButton } from "@/components/ExportButton";
import { FilterChip } from "@/components/FilterChip";
import { RowDetailDrawer } from "@/components/RowDetailDrawer";

export function EventsTable() {
  const filters = useFiltersStore((s) => s.filters);
  const setSort = useFiltersStore((s) => s.setSort);
  const setPage = useFiltersStore((s) => s.setPage);
  const setPageSize = useFiltersStore((s) => s.setPageSize);
  const addAtom = useFiltersStore((s) => s.addAtom);
  const reset = useFiltersStore((s) => s.reset);

  const columnVisibility = useTableStore((s) => s.columnVisibility);
  const setVisibility = useTableStore((s) => s.setVisibility);
  const columnOrder = useTableStore((s) => s.columnOrder);
  const setColumnOrder = useTableStore((s) => s.setColumnOrder);

  const [selected, setSelected] = useState<EventRow | null>(null);
  const [pendingChipId, setPendingChipId] = useState<string | null>(null);

  // Debounce filter changes — typing inside a chip popover triggers many updates.
  const [debouncedFilters, setDebouncedFilters] = useState(filters);
  useEffect(() => {
    const t = setTimeout(() => setDebouncedFilters(filters), 200);
    return () => clearTimeout(t);
  }, [filters]);

  // Strip incomplete (value-less) atoms before submitting to the backend.
  const submittedFilters = useMemo(
    () => selectActiveFilters(debouncedFilters),
    [debouncedFilters]
  );

  const { data, isFetching, error } = useQuery({
    queryKey: ["events", submittedFilters],
    queryFn: () => eventsApi.query(submittedFilters),
    placeholderData: (prev) => prev,
  });

  const sorting: SortingState = useMemo(
    () => [{ id: filters.sort ?? "time", desc: filters.reverse ?? true }],
    [filters.sort, filters.reverse]
  );

  const table = useReactTable({
    data: data?.rows ?? [],
    columns,
    state: { sorting, columnVisibility, columnOrder },
    onSortingChange: (updater) => {
      const next = typeof updater === "function" ? updater(sorting) : updater;
      const s = next[0];
      if (s) setSort(s.id, s.desc);
    },
    onColumnVisibilityChange: (updater) => {
      const next =
        typeof updater === "function" ? updater(columnVisibility) : updater;
      setVisibility(next);
    },
    onColumnOrderChange: (updater) => {
      const next = typeof updater === "function" ? updater(columnOrder) : updater;
      setColumnOrder(next);
    },
    manualSorting: true,
    manualPagination: true,
    enableSortingRemoval: false,
    getCoreRowModel: getCoreRowModel(),
  });

  const total = data?.total ?? 0;
  const page = filters.page ?? 0;
  const pageSize = filters.page_size ?? 100;
  const lastPage = Math.max(0, Math.ceil(total / pageSize) - 1);

  return (
    <>
      {/* Toolbar above the table: Add filter + Reset live next to Columns,
          page size, paging, and Export. */}
      <div className="row" style={{ marginBottom: 8, gap: 6, flexWrap: "wrap", alignItems: "center" }}>
        <AddFilterMenu
          onPick={(def) => {
            const id = addAtom(def.field);
            if (id) setPendingChipId(id);
          }}
        />
        <button onClick={reset} title="Reset all filters">Reset all</button>
        <span className="grow" />
        <span style={{ color: "var(--muted)", fontSize: 12 }}>
          {total.toLocaleString()} matching · page {page + 1} / {lastPage + 1}
          {isFetching && " · loading…"}
        </span>
        <ColumnPicker />
        <label className="row" style={{ gap: 4 }}>
          <span className="label">Page size</span>
          <select
            value={pageSize}
            onChange={(e) => setPageSize(parseInt(e.target.value, 10))}
          >
            {[50, 100, 200, 500, 1000].map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </label>
        <button onClick={() => setPage(Math.max(0, page - 1))} disabled={page === 0}>
          ‹ Prev
        </button>
        <button
          onClick={() => setPage(Math.min(lastPage, page + 1))}
          disabled={page >= lastPage}
        >
          Next ›
        </button>
        <ExportButton />
      </div>

      {/* Chip list — sits just below the toolbar, above the table. */}
      <div
        className="row"
        style={{ marginBottom: 8, gap: 6, alignItems: "center", flexWrap: "wrap" }}
      >
        {filters.atoms.length === 0 ? (
          <span className="meta" style={{ fontSize: 12 }}>
            No filters. Use “+ Add filter” to filter any column.
          </span>
        ) : (
          filters.atoms.map((atom) => (
            <FilterChip
              key={atom.id}
              atom={atom}
              autoOpen={pendingChipId === atom.id}
              onClose={() => {
                if (pendingChipId === atom.id) setPendingChipId(null);
              }}
            />
          ))
        )}
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((h) => (
                  <th
                    key={h.id}
                    onClick={h.column.getToggleSortingHandler()}
                    style={{ width: h.getSize() }}
                  >
                    {flexRender(h.column.columnDef.header, h.getContext())}
                    {h.column.getIsSorted() === "asc" && " ▲"}
                    {h.column.getIsSorted() === "desc" && " ▼"}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id} onClick={() => setSelected(row.original)}>
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} style={{ width: cell.column.getSize() }}>
                    {renderCell(cell.column.id, cell.getValue())}
                  </td>
                ))}
              </tr>
            ))}
            {table.getRowModel().rows.length === 0 && (
              <tr>
                <td
                  colSpan={table.getVisibleLeafColumns().length}
                  style={{
                    textAlign: "center",
                    padding: 32,
                    color: error ? "var(--danger)" : "var(--muted)",
                  }}
                >
                  {error
                    ? `Query failed: ${error instanceof Error ? error.message : String(error)}`
                    : total === 0
                    ? "No events. Load a time window above."
                    : "No matches for current filters."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {selected && <RowDetailDrawer row={selected} onClose={() => setSelected(null)} />}
    </>
  );
}

function renderCell(columnId: string, value: unknown): React.ReactNode {
  if (value === null || value === undefined || value === "") return "";
  if (columnId === "severity" || columnId === "effect") {
    const v = String(value).toLowerCase();
    return <span className={`tag ${v}`}>{String(value)}</span>;
  }
  if (columnId === "time") {
    try {
      return new Date(String(value)).toLocaleString();
    } catch {
      return String(value);
    }
  }
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
