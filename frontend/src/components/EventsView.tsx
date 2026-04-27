import { IngestPanel } from "@/components/IngestPanel";
import { EventsTable } from "@/components/EventsTable";

export function EventsView() {
  return (
    <div style={{ flex: 1, padding: 12, display: "flex", flexDirection: "column", overflow: "hidden" }}>
      <IngestPanel />
      <EventsTable />
    </div>
  );
}
