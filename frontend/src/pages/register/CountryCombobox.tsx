import { useState, useEffect, useMemo, useRef } from "react";
import { type CountryEntry } from "../../constants/countries";
import { TextFieldControl } from "../../components/TextField";
import "./CountryCombobox.css";

/** Combobox with search filtering for country / dial code selection. */
export function CountryCombobox({
  entries,
  value,
  onChange,
  displayFn,
  optionLabelFn,
  filterFn,
  id,
}: {
  entries: readonly CountryEntry[];
  value: string;
  onChange: (val: string) => void;
  displayFn: (c: CountryEntry) => string;
  /** 一覧の行の字。省けば displayFn。選んだ時に返す値は常に displayFn(c)。 */
  optionLabelFn?: (c: CountryEntry) => string;
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
    <div ref={ref} className="register-combobox">
      <TextFieldControl
        id={id}
        type="text"
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
        <ul className="register-combobox__list">
          {filtered.map((c) => (
            <li
              key={c.code + c.dial}
              className="register-combobox__option"
              onMouseDown={(e) => {
                e.preventDefault();
                onChange(displayFn(c));
                setOpen(false);
                setQuery("");
              }}
            >
              {(optionLabelFn ?? displayFn)(c)}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
