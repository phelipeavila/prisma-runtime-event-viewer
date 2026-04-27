// Filterable column catalog. Each entry maps a backend column name (`field`) to
// a data type. The chip UI uses the type to decide which operators are available
// (see filterOps.ts) and which value editor to render. `facetField` enables the
// facet checkbox value picker for `is_one_of`/`is_not_one_of`.
import type { ColumnType, OpId } from "@/lib/filterOps";
import { DEFAULT_OP_FOR_TYPE } from "@/lib/filterOps";

export type ColumnDef = {
  field: string;        // actual backend column name (also id in the UI)
  label: string;
  group: string;
  type: ColumnType;
  facetField?: string;  // backend facet field; defaults to field when faceted
};

// `facet: true` means the column has facet counts available from
// /api/events/facets (i.e. it is in the backend FACET_WHITELIST).
function col(
  field: string,
  label: string,
  group: string,
  type: ColumnType,
  facet: boolean = false,
  facetField?: string,
): ColumnDef {
  const def: ColumnDef = { field, label, group, type };
  if (facet) def.facetField = facetField ?? field;
  return def;
}

export const COLUMN_DEFS: ColumnDef[] = [
  // Severity / outcome
  col("type",              "Type",              "Severity", "string", true),
  col("effect",            "Effect",            "Severity", "string", true),
  col("severity",          "Severity",          "Severity", "string", true),
  col("attack_type",       "Attack Type",       "Severity", "string", true),
  col("attack_techniques", "Attack Techniques", "Severity", "array"),
  col("rule_name",         "Rule",              "Severity", "string", true),
  col("msg",               "Message",           "Severity", "string"),
  col("err",               "Error",             "Severity", "string"),
  col("count",             "Count",             "Severity", "number"),

  // Kubernetes
  col("namespace",   "Namespace",   "Kubernetes", "string", true),
  col("cluster",     "Cluster",     "Kubernetes", "string", true),
  col("collections", "Collections", "Kubernetes", "array"),

  // Container / image
  col("container_name", "Container",     "Container", "string", true),
  col("container_id",   "Container ID",  "Container", "string", true),
  col("image_name",     "Image",         "Container", "string", true),
  col("image_id",       "Image ID",      "Container", "string", true),
  col("profile_id",     "Profile ID",    "Container", "string", true),
  col("label",          "Label",         "Container", "string", true),
  col("labels_json",    "Labels JSON",   "Container", "string"),
  col("is_container",   "Is Container",  "Container", "bool"),

  // Host
  col("hostname", "Host",  "Host", "string", true),
  col("fqdn",     "FQDN",  "Host", "string", true),
  col("os",       "OS",    "Host", "string", true),
  col("vm_id",    "VM ID", "Host", "string", true),

  // Cloud
  col("provider",    "Provider",    "Cloud", "string", true),
  col("account_id",  "Account ID",  "Cloud", "string", true),
  col("region",      "Region",      "Cloud", "string", true),
  col("resource_id", "Resource ID", "Cloud", "string", true),
  col("version",     "Version",     "Cloud", "string", true),

  // Process
  col("user_name",    "User",         "Process", "string", true),
  col("interactive",  "Interactive",  "Process", "bool"),
  col("pid",          "PID",          "Process", "number"),
  col("process_path", "Process Path", "Process", "string", true),
  col("command",      "Command",      "Process", "string"),

  // File
  col("filepath", "File Path", "File", "string"),
  col("md5",      "MD5",       "File", "string"),

  // Network
  col("ip",      "IP",      "Network", "string", true),
  col("port",    "Port",    "Network", "number"),
  col("country", "Country", "Network", "string", true),
  col("domain",  "Domain",  "Network", "string", true),

  // Serverless
  col("app",           "App",          "Serverless", "string", true),
  col("app_id",        "App ID",       "Serverless", "string", true),
  col("function_name", "Function",     "Serverless", "string", true),
  col("function_id",   "Function ID",  "Serverless", "string", true),
  col("request_id",    "Request ID",   "Serverless", "string", true),
  col("runtime",       "Runtime",      "Serverless", "string", true),

  // Misc
  col("wildfire_url", "WildFire URL", "Misc", "string"),
  col("_id",          "Audit ID",     "Misc", "string"),
];

export const COLUMN_BY_FIELD: Map<string, ColumnDef> =
  new Map(COLUMN_DEFS.map((c) => [c.field, c]));

export function columnByField(field: string): ColumnDef | undefined {
  return COLUMN_BY_FIELD.get(field);
}

export function defaultOpForColumn(c: ColumnDef): OpId {
  return DEFAULT_OP_FOR_TYPE[c.type];
}
