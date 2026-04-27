import type { EventRow } from "@/lib/columns";

export function RowDetailDrawer({ row, onClose }: { row: EventRow; onClose: () => void }) {
  let raw: unknown = row.raw;
  if (typeof raw === "string") {
    try { raw = JSON.parse(raw); } catch { /* keep as string */ }
  }
  const text = typeof raw === "string" ? raw : JSON.stringify(raw ?? row, null, 2);
  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <div className="drawer">
        <div className="head">
          <strong>Event Detail</strong>
          <span className="meta" style={{ marginLeft: 8 }}>{row._id}</span>
          <span className="grow" />
          <button onClick={() => navigator.clipboard.writeText(text)}>Copy JSON</button>
          <button onClick={onClose}>Close</button>
        </div>
        <div className="body">{text}</div>
      </div>
    </>
  );
}
