import { useState } from "react";

import { exportApi } from "@/api/export";
import { selectActiveFilters } from "@/lib/filterAtom";
import { usePopoverAnchor } from "@/lib/usePopoverAnchor";
import { useFiltersStore } from "@/state/filtersStore";

export function ExportButton() {
  const filters = useFiltersStore((s) => s.filters);
  const submittedFilters = selectActiveFilters(filters);
  const [open, setOpen] = useState(false);
  const { setTrigger, side } = usePopoverAnchor<HTMLDivElement>(open, 240);

  return (
    <div
      className="split-button"
      ref={setTrigger}
      onMouseLeave={() => setOpen(false)}
    >
      <button onClick={() => setOpen((v) => !v)}>Export CSV ▾</button>
      {open && (
        <div className={`menu anchor-${side}`}>
          <button
            onClick={() => {
              exportApi.native(submittedFilters);
              setOpen(false);
            }}
            title="Stream Prisma's /download endpoint with current filters. Substring filters not honored."
          >
            Native (from Prisma)
          </button>
          <button
            onClick={() => {
              exportApi.cache(submittedFilters);
              setOpen(false);
            }}
            title="Export current cached + filtered rows from DuckDB"
          >
            From cache (current filters)
          </button>
        </div>
      )}
    </div>
  );
}
