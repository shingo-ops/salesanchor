import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../lib/api";

export interface ChannelMasterOption {
  id: number;
  platform: string;
  display_name: string;
  connection_type: "auto" | "manual";
  is_active: boolean;
}

interface ChannelTypeComboboxProps {
  id: string;
  value: string;
  onChange: (value: string) => void;
  onCommit?: () => void;
  placeholder?: string;
  disabled?: boolean;
  required?: boolean;
}

export function ChannelTypeCombobox({
  id,
  value,
  onChange,
  onCommit,
  placeholder,
  disabled = false,
  required = false,
}: ChannelTypeComboboxProps) {
  const { t } = useTranslation();
  const ref = useRef<HTMLDivElement>(null);
  const [channels, setChannels] = useState<ChannelMasterOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    api.get<ChannelMasterOption[]>("/channel-masters")
      .then((rows) => {
        if (mounted) setChannels(rows.filter((row) => row.is_active));
      })
      .catch(() => {
        if (mounted) setChannels([]);
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
    () => channels.find((channel) => channel.platform === value) ?? null,
    [channels, value],
  );

  const filtered = useMemo(() => {
    if (!query.trim()) return channels;
    const q = query.trim().toLowerCase();
    return channels.filter((channel) =>
      channel.platform.toLowerCase().includes(q) ||
      channel.display_name.toLowerCase().includes(q) ||
      channel.connection_type.toLowerCase().includes(q)
    );
  }, [channels, query]);

  const displayValue = open
    ? query
    : selected
      ? `${selected.display_name} (${selected.platform})`
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
            setQuery(selected ? selected.display_name : "");
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
            filtered.map((channel) => (
              <button
                key={channel.platform}
                type="button"
                role="option"
                aria-selected={channel.platform === value}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => {
                  onChange(channel.platform);
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
                  background: channel.platform === value ? "var(--bg-muted)" : "transparent",
                  color: "var(--text-primary)",
                  cursor: "pointer",
                }}
              >
                <strong>{channel.display_name}</strong>
                <span style={{ marginLeft: "var(--space-2)", color: "var(--text-secondary)" }}>
                  {channel.platform} · {channel.connection_type}
                </span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
