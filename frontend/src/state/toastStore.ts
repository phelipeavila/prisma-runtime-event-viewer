import { create } from "zustand";

export type Toast = { id: number; message: string; level: "info" | "error" };

type ToastStore = {
  toasts: Toast[];
  push: (message: string, level?: Toast["level"]) => void;
  dismiss: (id: number) => void;
};

let nextId = 1;

export const useToastStore = create<ToastStore>((set) => ({
  toasts: [],
  push: (message, level = "info") => {
    const id = nextId++;
    set((s) => ({ toasts: [...s.toasts, { id, message, level }] }));
    setTimeout(() => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })), 5000);
  },
  dismiss: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));
