import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../lib/api";

export interface CountryOption {
  code: string;
  name: string;
  dial_code: string;
  is_active: boolean;
}

interface CountryComboboxProps {
  id: string;
  value: string;
  onChange: (value: string) => void;
  onCommit?: () => void;
  placeholder?: string;
  disabled?: boolean;
  required?: boolean;
}

export function CountryCombobox({
  id,
  value,
  onChange,
  onCommit,
  placeholder,
  disabled = false,
  required = false,
}: CountryComboboxProps) {
  const { t } = useTranslation();
  const ref = useRef<HTMLDivElement>(null);
  const [countries, setCountries] = useState<CountryOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    api.get<CountryOption[]>("/countries")
      .then((rows) => {
        if (mounted) setCountries(rows.filter((row) => row.is_active));
      })
      .catch(() => {
        if (mounted) setCountries([]);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    function handleClick(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const selected = useMemo(
    () => countries.find((country) => country.code === value) ?? null,
    [countries, value],
  );

  const filtered = useMemo(() => {
    if (!query.trim()) return countries;
    const q = query.trim().toLowerCase();
    return countries.filter((country) =>
      country.code.toLowerCase().includes(q) ||
      country.name.toLowerCase().includes(q) ||
      country.dial_code.toLowerCase().includes(q)
    );
  }, [countries, query]);

  const displayValue = open
    ? query
    : selected
      ? `${selected.name} (${selected.code})`
      : value;

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <div style={{ position: "relative" }}>
        <input
          id={id}
          className="input"
          type="text"
          disabled={disabled}
          required={required}
          value={displayValue}
          placeholder={placeholder ?? t("common.search")}
          autoComplete="off"
          aria-expanded={open}
          aria-autocomplete="list"
          onFocus={() => {
            if (disabled) return;
            setOpen(true);
            setQuery(selected ? selected.name : "");
          }}
          onChange={(e) => {
            if (disabled) return;
            setOpen(true);
            setQuery(e.target.value);
          }}
          onBlur={() => {
            if (!disabled) {
              setOpen(false);
              setQuery("");
            }
          }}
        />
        {!disabled && value && (
          <button
            type="button"
            aria-label={t("common.clear", { defaultValue: "Clear" })}
            onClick={() => {
              onChange("");
              onCommit?.();
              setQuery("");
              setOpen(false);
            }}
            style={{
              position: "absolute",
              right: "var(--space-2)",
              top: "50%",
              transform: "translateY(-50%)",
              border: 0,
              background: "transparent",
              color: "var(--text-secondary)",
              cursor: "pointer",
              padding: 0,
            }}
          >
            ×
          </button>
        )}
      </div>

      {open && !disabled && (
        <div
          role="listbox"
          aria-busy={loading}
          style={{
            position: "absolute",
            zIndex: "var(--z-dropdown)",
            background: "var(--bg-surface)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-sm)",
            boxShadow: "var(--shadow-lg)",
            width: "100%",
            maxHeight: "240px",
            overflowY: "auto",
            marginTop: "var(--space-1)",
          }}
        >
          {loading ? (
            <div style={{ padding: "var(--space-3)", color: "var(--text-secondary)" }}>
              {t("common.loading")}
            </div>
          ) : filtered.length === 0 ? (
            <div style={{ padding: "var(--space-3)", color: "var(--text-secondary)" }}>
              {t("common.noResults", { defaultValue: "No results" })}
            </div>
          ) : (
            filtered.map((country) => (
              <button
                key={country.code}
                type="button"
                role="option"
                aria-selected={country.code === value}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => {
                  onChange(country.code);
                  onCommit?.();
                  setOpen(false);
                  setQuery("");
                }}
                style={{
                  display: "block",
                  width: "100%",
                  textAlign: "left",
                  padding: "var(--space-2) var(--space-3)",
                  border: 0,
                  background: country.code === value ? "var(--bg-muted)" : "transparent",
                  color: "var(--text-primary)",
                  cursor: "pointer",
                }}
              >
                <strong>{country.name}</strong>
                <span style={{ marginLeft: "var(--space-2)", color: "var(--text-secondary)" }}>
                  {country.code} · {country.dial_code}
                </span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
