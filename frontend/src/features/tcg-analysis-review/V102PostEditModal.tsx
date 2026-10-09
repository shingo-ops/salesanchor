/**
 * v102 の投稿の「Gemini の書き写し」を直す Modal（設計 §13-5 の 2）。
 * 左に原文（選んだ件の行を色付け）、右に件の表。保存前に画面でも検査し、だめな行は TextField の error で示す。
 * 部品は金型（Modal・DataTable・TextField・Button・Callout）だけ。
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { Callout } from "../../components/Callout";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { Modal } from "../../components/Modal";
import { TextField } from "../../components/TextField";
import { api, ApiError } from "../../lib/api";
import { reviewReasonLabel } from "./reviewReasonLabel";
import { ShadowSourcePane } from "./ShadowSourcePane";
import type { V102PostDetail, V102SaveResponse } from "./v102PostTypes";
import {
  TEXT_MAX_LENGTH,
  blockRangeOf,
  toSaveItems,
  validateRows,
  type EditRow,
  type LinesErrorCode,
} from "./v102PostValidation";

interface Props {
  jobId: string;
  onClose: () => void;
  /** 保存が済んだ（changed=true）あとに呼ぶ。一覧の読み直し用 */
  onSaved: () => void;
}

type Notice = { variant: "info" | "warning"; title: string } | null;

export function V102PostEditModal({ jobId, onClose, onSaved }: Props) {
  const { t } = useTranslation();
  const [detail, setDetail] = useState<V102PostDetail | null>(null);
  const [rows, setRows] = useState<EditRow[]>([]);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);
  const [showErrors, setShowErrors] = useState(false);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);
  const newRowCounter = useRef(0);

  const joinReasons = useCallback(
    (details: { code: string }[]) => details.map((d) => reviewReasonLabel(t, d.code)).join(t("reviewReason.separator")),
    [t],
  );

  const load = useCallback(async () => {
    try {
      const result = await api.get<V102PostDetail>(`/tcg/v102/posts/${jobId}`);
      setDetail(result);
      setRows(
        result.items.map((item) => ({
          key: item.id,
          id: item.id,
          linesText: item.source_lines.join(","),
          price: item.raw_price ?? "",
          quantity: item.raw_quantity ?? "",
          reasonsText: joinReasons(item.review_reason_details),
        })),
      );
      setSelectedKey((current) => current ?? result.items[0]?.id ?? null);
      setLoadFailed(false);
    } catch {
      setLoadFailed(true);
    }
  }, [jobId, joinReasons]);

  useEffect(() => {
    void load();
  }, [load]);

  const lineCount = detail?.lines.length ?? 0;
  const validation = useMemo(() => validateRows(rows, lineCount), [rows, lineCount]);
  const rawText = useMemo(() => (detail?.lines ?? []).map((line) => line.text).join("\n"), [detail]);
  const blockRange = blockRangeOf(rows.find((row) => row.key === selectedKey), lineCount);

  const updateRow = (key: string, patch: Partial<EditRow>) => {
    setRows((current) => current.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  };
  const removeRow = (key: string) => setRows((current) => current.filter((row) => row.key !== key));
  const addRow = () => {
    newRowCounter.current += 1;
    const key = `new-${newRowCounter.current}`;
    setRows((current) => [...current, { key, id: null, linesText: "", price: "", quantity: "", reasonsText: "" }]);
    setSelectedKey(key);
  };

  const linesErrorText = (code: LinesErrorCode | null): string | undefined => {
    if (!showErrors || code === null) return undefined;
    return t(`v102Posts.errors.lines.${code}`, { max: lineCount });
  };
  const textErrorText = (hasError: boolean): string | undefined =>
    showErrors && hasError ? t("v102Posts.errors.textTooLong", { max: TEXT_MAX_LENGTH }) : undefined;

  const handleSave = async () => {
    setNotice(null);
    if (!detail) return;
    if (!validation.isValid) {
      setShowErrors(true);
      return;
    }
    setSaving(true);
    try {
      const result = await api.put<V102SaveResponse>(`/tcg/v102/posts/${jobId}/items`, {
        source_message_id: detail.source_message_id,
        items: toSaveItems(rows, lineCount),
      });
      if (result.changed) {
        setNotice({ variant: "info", title: t("v102Posts.saved") });
        setShowErrors(false);
        await load();
        onSaved();
      } else {
        setNotice({ variant: "info", title: t("v102Posts.unchanged") });
      }
    } catch (error: unknown) {
      const message = error instanceof ApiError && error.status === 422 ? error.message : t("v102Posts.saveFailed");
      setNotice({ variant: "warning", title: message });
    } finally {
      setSaving(false);
    }
  };

  const columns: DataTableColumn<EditRow>[] = [
    {
      key: "lines",
      header: t("v102Posts.columns.lines"),
      renderCell: (row, rowKey) => (
        <TextField
          size="sm"
          inputMode="numeric"
          placeholder={t("v102Posts.linesPlaceholder")}
          aria-label={t("v102Posts.columns.lines")}
          value={row.linesText}
          error={linesErrorText(validation.rowErrors[rowKey]?.lines ?? null)}
          onFocus={() => setSelectedKey(row.key)}
          onChange={(e) => updateRow(row.key, { linesText: e.target.value })}
        />
      ),
    },
    {
      key: "price",
      header: t("v102Posts.columns.price"),
      renderCell: (row, rowKey) => (
        <TextField
          size="sm"
          aria-label={t("v102Posts.columns.price")}
          value={row.price}
          error={textErrorText(validation.rowErrors[rowKey]?.price ?? false)}
          onFocus={() => setSelectedKey(row.key)}
          onChange={(e) => updateRow(row.key, { price: e.target.value })}
        />
      ),
    },
    {
      key: "quantity",
      header: t("v102Posts.columns.quantity"),
      renderCell: (row, rowKey) => (
        <TextField
          size="sm"
          aria-label={t("v102Posts.columns.quantity")}
          value={row.quantity}
          error={textErrorText(validation.rowErrors[rowKey]?.quantity ?? false)}
          onFocus={() => setSelectedKey(row.key)}
          onChange={(e) => updateRow(row.key, { quantity: e.target.value })}
        />
      ),
    },
    { key: "reasons", header: t("v102Posts.columns.reasons"), renderCell: (row) => row.reasonsText || "—" },
    {
      key: "remove",
      header: t("v102Posts.columns.remove"),
      renderCell: (row) => (
        <Button variant="danger" size="sm" onClick={() => removeRow(row.key)}>
          {t("v102Posts.remove")}
        </Button>
      ),
    },
  ];

  const footer = (
    <>
      <Button variant="secondary" onClick={onClose} disabled={saving}>
        {t("v102Posts.cancel")}
      </Button>
      <Button variant="primary" onClick={() => void handleSave()} loading={saving} disabled={saving || !detail}>
        {t("v102Posts.save")}
      </Button>
    </>
  );

  return (
    <Modal open onClose={onClose} title={t("v102Posts.modalTitle")} size="xl" footer={footer}>
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
        {loadFailed && <Callout variant="warning" title={t("common.fetchError")} />}
        {notice && <Callout variant={notice.variant} title={notice.title} />}
        {showErrors && validation.hasNoRows && <Callout variant="warning" title={t("v102Posts.errors.noItems")} />}
        {detail && detail.job_review_reason_details.length > 0 && (
          <p>{t("v102Posts.jobReasons", { reasons: joinReasons(detail.job_review_reason_details) })}</p>
        )}
        {detail && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: "var(--space-3)", alignItems: "start" }}>
            <ShadowSourcePane rawText={rawText} blockRange={blockRange} />
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
              <DataTable columns={columns} data={rows} rowKey={(row) => row.key} emptyState={t("v102Posts.noRows")} density="compact" />
              <div>
                <Button variant="secondary" size="sm" onClick={addRow}>
                  {t("v102Posts.addItem")}
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
