export type TimePreset = { label: string; ms: number };

export const TIME_PRESETS: TimePreset[] = [
  { label: "Last 1h", ms: 60 * 60 * 1000 },
  { label: "Last 6h", ms: 6 * 60 * 60 * 1000 },
  { label: "Last 24h", ms: 24 * 60 * 60 * 1000 },
  { label: "Last 7d", ms: 7 * 24 * 60 * 60 * 1000 },
  { label: "Last 30d", ms: 30 * 24 * 60 * 60 * 1000 },
];

export function presetRange(ms: number): { from: string; to: string } {
  const now = new Date();
  const from = new Date(now.getTime() - ms);
  return { from: from.toISOString(), to: now.toISOString() };
}

export function localToIso(local: string): string {
  // local is "YYYY-MM-DDTHH:MM" from datetime-local input
  return new Date(local).toISOString();
}

export function isoToLocal(iso: string): string {
  const d = new Date(iso);
  const tz = d.getTimezoneOffset();
  const local = new Date(d.getTime() - tz * 60_000);
  return local.toISOString().slice(0, 16);
}
