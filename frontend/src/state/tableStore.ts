import { create } from "zustand";
import { persist } from "zustand/middleware";

import { DEFAULT_VISIBLE, columns } from "@/lib/columns";

const DEFAULT_ORDER: string[] = columns.map((c) => c.id);

type TableStore = {
  columnVisibility: Record<string, boolean>;
  columnOrder: string[];
  setVisibility: (next: Record<string, boolean>) => void;
  toggle: (id: string) => void;
  setAll: (visible: boolean) => void;
  resetVisibility: () => void;
  setColumnOrder: (next: string[]) => void;
  moveColumn: (fromId: string, toId: string) => void;
  resetOrder: () => void;
};

export const useTableStore = create<TableStore>()(
  persist(
    (set, get) => ({
      columnVisibility: { ...DEFAULT_VISIBLE },
      columnOrder: [...DEFAULT_ORDER],
      setVisibility: (next) => set({ columnVisibility: next }),
      toggle: (id) =>
        set((s) => ({
          columnVisibility: { ...s.columnVisibility, [id]: !s.columnVisibility[id] },
        })),
      setAll: (visible) => {
        const next: Record<string, boolean> = {};
        for (const k of Object.keys(get().columnVisibility)) next[k] = visible;
        set({ columnVisibility: next });
      },
      resetVisibility: () => set({ columnVisibility: { ...DEFAULT_VISIBLE } }),
      setColumnOrder: (next) => set({ columnOrder: next }),
      moveColumn: (fromId, toId) =>
        set((s) => {
          if (fromId === toId) return s;
          const order = [...s.columnOrder];
          const fromIdx = order.indexOf(fromId);
          const toIdx = order.indexOf(toId);
          if (fromIdx < 0 || toIdx < 0) return s;
          order.splice(fromIdx, 1);
          order.splice(toIdx, 0, fromId);
          return { columnOrder: order };
        }),
      resetOrder: () => set({ columnOrder: [...DEFAULT_ORDER] }),
    }),
    {
      name: "runtime-event-viewer.tableState",
      version: 1,
      migrate: (persisted: any) => {
        if (persisted && !Array.isArray(persisted.columnOrder)) {
          persisted.columnOrder = [...DEFAULT_ORDER];
        }
        return persisted;
      },
    }
  )
);
