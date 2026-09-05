/**
 * DiagnosticsDrawer — TCG DB データ健全性チェック
 *
 * 4つの診断キーを独立したセクションで表示する。
 * 各セクションは独立してローディング・エラー状態を管理し、
 * 1つが失敗しても他のセクションは正常表示される。
 *
 * セクション順: supplier-channels（最多参照）→ suppliers → supplier-name-dupes → orphan-messages
 *              → extraction-errors → extraction-pending → extraction-running-stale → analysis-missing
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Drawer } from "../../components/Drawer";
import { api } from "../../lib/api";

type Row = Record<string, unknown>;

interface SectionProps {
  diagKey: string;
  titleKey: string;
  open: boolean;
  highlight?: (row: Row) => boolean;
}

function DiagnosticsSection({ diagKey, titleKey, open, highlight }: SectionProps) {
  const { t } = useTranslation();
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) {
      setRows([]);
      setError("");
      return;
    }
    setLoading(true);
    setError("");
    api
      .get<{ ok: boolean; key: string; rows: Row[] }>(`/tcg/diagnostics/${diagKey}`)
      .then((res) => {
        setRows(res.rows);
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        setLoading(false);
      });
  }, [diagKey, open]);

  const headers = rows.length > 0 ? Object.keys(rows[0]) : [];

  return (
    <section style={{ marginBottom: "1.5rem" }}>
      <h3
        style={{
          fontSize: "0.8125rem",
          fontWeight: 600,
          color: "var(--color-text-sub)",
          textTransform: "uppercase",
          letterSpacing: "0.04em",
          marginBottom: "0.5rem",
        }}
      >
        {t(titleKey)}
      </h3>

      {loading && <p style={{ color: "var(--color-text-sub)" }}>{t("common.loading")}</p>}

      {!loading && error && (
        <p style={{ color: "var(--color-error)" }}>{error}</p>
      )}

      {!loading && !error && rows.length === 0 && (
        <p style={{ color: "var(--color-text-sub)", fontSize: "0.875rem" }}>
          {t("superAdmin.diagnostics.noRows")}
        </p>
      )}

      {!loading && !error && rows.length > 0 && (
        <div style={{ overflowX: "auto" }}>
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              fontSize: "0.8125rem",
            }}
          >
            <thead>
              <tr>
                {headers.map((h) => (
                  <th
                    key={h}
                    style={{
                      textAlign: "left",
                      padding: "0.25rem 0.5rem",
                      borderBottom: "1px solid var(--color-border)",
                      color: "var(--color-text-sub)",
                      fontWeight: 600,
                      whiteSpace: "nowrap",
                    }}
                  >
                    {t(`superAdmin.diagnostics.columns.${h}`, { defaultValue: h })}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => {
                const isHighlighted = highlight?.(row) ?? false;
                return (
                  <tr
                    key={i}
                    style={
                      isHighlighted
                        ? { color: "var(--color-error)", fontWeight: 500 }
                        : undefined
                    }
                  >
                    {headers.map((h) => (
                      <td
                        key={h}
                        style={{
                          padding: "0.25rem 0.5rem",
                          borderBottom: "1px solid var(--color-border)",
                        }}
                      >
                        {String(row[h] ?? "")}
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export function DiagnosticsDrawer({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const { t } = useTranslation();

  return (
    <Drawer open={open} onClose={onClose} title={t("superAdmin.diagnostics.drawerTitle")}>
      <DiagnosticsSection
        diagKey="supplier-channels"
        titleKey="superAdmin.diagnostics.sections.supplierChannels"
        open={open}
        highlight={(row) =>
          typeof row.channel_count === "number" && row.channel_count >= 2
        }
      />
      <DiagnosticsSection
        diagKey="suppliers"
        titleKey="superAdmin.diagnostics.sections.suppliers"
        open={open}
      />
      <DiagnosticsSection
        diagKey="supplier-name-dupes"
        titleKey="superAdmin.diagnostics.sections.supplierNameDupes"
        open={open}
      />
      <DiagnosticsSection
        diagKey="orphan-messages"
        titleKey="superAdmin.diagnostics.sections.orphanMessages"
        open={open}
        highlight={(row) => Number(row.null_channel_count) !== 0}
      />
      <DiagnosticsSection
        diagKey="extraction-errors"
        titleKey="superAdmin.diagnostics.sections.extractionErrors"
        open={open}
      />
      <DiagnosticsSection
        diagKey="extraction-pending"
        titleKey="superAdmin.diagnostics.sections.extractionPending"
        open={open}
      />
      <DiagnosticsSection
        diagKey="extraction-running-stale"
        titleKey="superAdmin.diagnostics.sections.extractionRunningStale"
        open={open}
        highlight={() => true}
      />
      <DiagnosticsSection
        diagKey="analysis-missing"
        titleKey="superAdmin.diagnostics.sections.analysisMissing"
        open={open}
        highlight={() => true}
      />
    </Drawer>
  );
}
