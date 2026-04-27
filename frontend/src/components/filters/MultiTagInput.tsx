import { useState } from "react";

export function MultiTagInput({
  values,
  onChange,
  placeholder,
}: {
  values: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
}) {
  const [draft, setDraft] = useState("");

  function add(v: string) {
    const trimmed = v.trim();
    if (!trimmed || values.includes(trimmed)) return;
    onChange([...values, trimmed]);
    setDraft("");
  }
  function removeAt(i: number) {
    onChange(values.filter((_, idx) => idx !== i));
  }

  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: 4,
        padding: 4,
        border: "1px solid var(--border)",
        borderRadius: 6,
        background: "var(--panel-2)",
      }}
    >
      {values.map((v, i) => (
        <span
          key={`${v}-${i}`}
          className="tag"
          style={{ display: "inline-flex", alignItems: "center", gap: 4 }}
        >
          {v}
          <button
            type="button"
            onClick={() => removeAt(i)}
            style={{ padding: "0 4px", background: "transparent", border: "none", color: "inherit" }}
          >
            ×
          </button>
        </span>
      ))}
      <input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === ",") {
            e.preventDefault();
            add(draft);
          } else if (e.key === "Backspace" && draft === "" && values.length > 0) {
            removeAt(values.length - 1);
          }
        }}
        onBlur={() => draft && add(draft)}
        placeholder={placeholder ?? "type and press Enter"}
        style={{
          flex: 1,
          minWidth: 80,
          background: "transparent",
          border: "none",
          padding: "2px 4px",
        }}
      />
    </div>
  );
}
