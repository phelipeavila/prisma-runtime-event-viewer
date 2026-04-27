type Props = {
  value: string | undefined;
  onChange: (next: string | undefined) => void;
  placeholder?: string;
};

export function ContainsInput({ value, onChange, placeholder }: Props) {
  return (
    <div className="col" style={{ minWidth: 220 }}>
      <input
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value || undefined)}
        placeholder={placeholder ?? "substring (case-insensitive)"}
        autoFocus
      />
    </div>
  );
}
