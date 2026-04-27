import { encodeFilters, triggerDownload } from "@/lib/download";
import type { Filters } from "@/lib/filterSchema";

export const exportApi = {
  native: (filters: Filters) =>
    triggerDownload(`/api/export/native?filters=${encodeFilters(filters)}`),
  cache: (filters: Filters) =>
    triggerDownload(`/api/export/cache?filters=${encodeFilters(filters)}`),
};
