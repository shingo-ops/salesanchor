import { useState, useEffect, useMemo, useRef } from "react";
import { type CountryEntry } from "../../constants/countries";

/** Combobox with search filtering for country / dial code selection. */
export function CountryCombobox({
  entries,
  value,
  onChange,
  displayFn,
  filterFn,
  id,
}: {
  entries: readonly CountryEntry[];
  value: string;
  onChange: (val: string) => void;
  displayFn: (c: CountryEntry) => string;
  filterFn: (c: CountryEntry, q: string) => boolean;
  id: string;
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const filtered = useMemo(
    () => (query ? entries.filter((c) => filterFn(c, query.toLowerCase())) : entries),
    [entries, query, filterFn],
  );

  const selectedDisplay = useMemo(() => {
    const found = entries.find((c) => displayFn(c) === value || c.code === value || c.dial === value);
    return found ? displayFn(found) : value;
  }, [entries, value, displayFn]);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <input
        id={id}
        type="text"
        className="input"
        value={open ? query : selectedDisplay}
        onChange={(e) => {
          setQuery(e.target.value);
          if (!open) setOpen(true);
        }}
        onFocus={() => {
          setOpen(true);
          setQuery("");
        }}
        autoComplete="off"
      />
      {open && filtered.length > 0 && (
        <ul
          style={{
            position: "absolute",
            zIndex: 10,
            background: "var(--bg-surface)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-sm)",
            maxHeight: "200px",
            overflow: "auto",
            width: "100%",
            margin: 0,
            padding: 0,
            listStyle: "none",
          }}
        >
          {filtered.map((c) => (
            <li
              key={c.code + c.dial}
              style={{
                padding: "var(--spacing-2) var(--spacing-3)",
                cursor: "pointer",
              }}
              onMouseDown={(e) => {
                e.preventDefault();
                onChange(displayFn(c));
                setOpen(false);
                setQuery("");
              }}
            >
              {displayFn(c)}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
