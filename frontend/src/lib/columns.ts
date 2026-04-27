import type { ColumnDef } from "@tanstack/react-table";

export type EventRow = {
  _id: string;
  time: string | null;
  raw: unknown;
} & Record<string, unknown>;

type Col = ColumnDef<EventRow> & { id: string; header: string };

export const columns: Col[] = [
  // Identity
  { id: "_id",              accessorKey: "_id",              header: "ID",              size: 220 },
  { id: "time",             accessorKey: "time",             header: "Time",            size: 180 },

  // Severity / outcome
  { id: "severity",         accessorKey: "severity",         header: "Severity",        size: 80 },
  { id: "effect",           accessorKey: "effect",           header: "Effect",          size: 80 },
  { id: "type",             accessorKey: "type",             header: "Type",            size: 100 },
  { id: "attack_type",      accessorKey: "attack_type",      header: "Attack",          size: 140 },
  { id: "attack_techniques",accessorKey: "attack_techniques",header: "Techniques",      size: 180 },
  { id: "rule_name",        accessorKey: "rule_name",        header: "Rule",            size: 160 },
  { id: "msg",              accessorKey: "msg",              header: "Message",         size: 360 },
  { id: "err",              accessorKey: "err",              header: "Error",           size: 200 },
  { id: "count",            accessorKey: "count",            header: "Count",           size: 70 },

  // Kubernetes / cluster
  { id: "namespace",        accessorKey: "namespace",        header: "Namespace",       size: 120 },
  { id: "cluster",          accessorKey: "cluster",          header: "Cluster",         size: 120 },
  { id: "collections",      accessorKey: "collections",      header: "Collections",     size: 180 },

  // Container / image
  { id: "container_name",   accessorKey: "container_name",   header: "Container",       size: 160 },
  { id: "container_id",     accessorKey: "container_id",     header: "Container ID",    size: 180 },
  { id: "image_name",       accessorKey: "image_name",       header: "Image",           size: 220 },
  { id: "image_id",         accessorKey: "image_id",         header: "Image ID",        size: 180 },
  { id: "profile_id",       accessorKey: "profile_id",       header: "Profile ID",      size: 180 },
  { id: "label",            accessorKey: "label",            header: "Label",           size: 160 },
  { id: "labels_json",      accessorKey: "labels_json",      header: "Labels (JSON)",   size: 220 },
  { id: "is_container",     accessorKey: "is_container",     header: "Is Container",    size: 100 },

  // Host
  { id: "hostname",         accessorKey: "hostname",         header: "Host",            size: 140 },
  { id: "fqdn",             accessorKey: "fqdn",             header: "FQDN",            size: 180 },
  { id: "os",               accessorKey: "os",               header: "OS",              size: 120 },
  { id: "vm_id",            accessorKey: "vm_id",            header: "VM ID",           size: 160 },

  // Cloud / org
  { id: "provider",         accessorKey: "provider",         header: "Provider",        size: 100 },
  { id: "account_id",       accessorKey: "account_id",       header: "Account ID",      size: 160 },
  { id: "region",           accessorKey: "region",           header: "Region",          size: 100 },
  { id: "resource_id",      accessorKey: "resource_id",      header: "Resource ID",     size: 200 },
  { id: "version",          accessorKey: "version",          header: "Version",         size: 100 },

  // Process
  { id: "user_name",        accessorKey: "user_name",        header: "User",            size: 120 },
  { id: "interactive",      accessorKey: "interactive",      header: "Interactive",     size: 100 },
  { id: "pid",              accessorKey: "pid",              header: "PID",             size: 80 },
  { id: "process_path",     accessorKey: "process_path",     header: "Process Path",    size: 240 },
  { id: "command",          accessorKey: "command",          header: "Command",         size: 280 },

  // File
  { id: "filepath",         accessorKey: "filepath",         header: "File Path",       size: 240 },
  { id: "md5",              accessorKey: "md5",              header: "MD5",             size: 220 },

  // Network
  { id: "ip",               accessorKey: "ip",               header: "IP",              size: 140 },
  { id: "port",             accessorKey: "port",             header: "Port",            size: 70 },
  { id: "country",          accessorKey: "country",          header: "Country",         size: 100 },
  { id: "domain",           accessorKey: "domain",           header: "Domain",          size: 200 },

  // Serverless / Fargate (often empty for Kubernetes-only tenants)
  { id: "app",              accessorKey: "app",              header: "App",             size: 140 },
  { id: "app_id",           accessorKey: "app_id",           header: "App ID",          size: 160 },
  { id: "function_name",    accessorKey: "function_name",    header: "Function",        size: 160 },
  { id: "function_id",      accessorKey: "function_id",      header: "Function ID",     size: 180 },
  { id: "request_id",       accessorKey: "request_id",       header: "Request ID",      size: 180 },
  { id: "runtime",          accessorKey: "runtime",          header: "Runtime",         size: 120 },

  // Misc
  { id: "wildfire_url",     accessorKey: "wildfire_url",     header: "WildFire URL",    size: 240 },
];

// Curated default-visible set. Everything else is hidden by default but toggleable.
export const DEFAULT_VISIBLE: Record<string, boolean> = Object.fromEntries(
  columns.map((c) => [c.id, false])
);
[
  "time",
  "severity",
  "effect",
  "type",
  "attack_type",
  "rule_name",
  "namespace",
  "cluster",
  "container_name",
  "image_name",
  "hostname",
  "msg",
].forEach((id) => {
  DEFAULT_VISIBLE[id] = true;
});

// Logical groups for the column picker UI.
export const COLUMN_GROUPS: { label: string; ids: string[] }[] = [
  { label: "Identity",     ids: ["_id", "time"] },
  { label: "Severity",     ids: ["severity", "effect", "type", "attack_type", "attack_techniques", "rule_name", "msg", "err", "count"] },
  { label: "Kubernetes",   ids: ["namespace", "cluster", "collections"] },
  { label: "Container",    ids: ["container_name", "container_id", "image_name", "image_id", "profile_id", "label", "labels_json", "is_container"] },
  { label: "Host",         ids: ["hostname", "fqdn", "os", "vm_id"] },
  { label: "Cloud",        ids: ["provider", "account_id", "region", "resource_id", "version"] },
  { label: "Process",      ids: ["user_name", "interactive", "pid", "process_path", "command"] },
  { label: "File",         ids: ["filepath", "md5"] },
  { label: "Network",      ids: ["ip", "port", "country", "domain"] },
  { label: "Serverless",   ids: ["app", "app_id", "function_name", "function_id", "request_id", "runtime"] },
  { label: "Misc",         ids: ["wildfire_url"] },
];
