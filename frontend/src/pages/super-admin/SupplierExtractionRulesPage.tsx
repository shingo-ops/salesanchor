/**
 * SupplierExtractionRulesPage — 仕入元別 抽出ルール設定（/super-admin/supplier-extraction-rules）
 *
 * 一覧: 全仕入元をunit_ng降順で表示（DataTable）
 * 詳細: 左=原文テキスト / 右=ルール設定フォーム
 *
 * ADR-027: 全UI文字列は t("key") 経由。
 * ADR-144: 金型コンポーネントのみ使用。
 */
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import { PageLayout } from "../../components/PageLayout";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { Badge } from "../../components/Badge";
import { TextField } from "../../components/TextField";
import { Select } from "../../components/Select";
import { Textarea } from "../../components/Textarea";
import { Button } from "../../components/Button";
import { DashboardIcons, SCHEDULE_SETTINGS_ICONS } from "../../constants/icons";
import "./SupplierExtractionRulesPage.css";

// ---------------------------------------------------------------------------
// 型定義
// ---------------------------------------------------------------------------

interface SupplierOverviewItem {
  supplier_id: number;
  name: string;
  total_items: number;
  unit_ng_count: number;
  has_extraction_rules: boolean;
}

interface SupplierExtractionDetail {
  supplier_id: number;
  extraction_price_format: string | null;
  extraction_qty_format: string | null;
  extraction_order_pattern: string | null;
  extraction_default_unit: string | null;
  extraction_state_format: string | null;
  extraction_notes: string | null;
  latest_raw_text: string | null;
}

interface SupplierSourceMessage {
  id: number;
  raw_text: string;
  created_at: string;
}

type RulesFormState = {
  extraction_price_format: string;
  extraction_qty_format: string;
  extraction_order_pattern: string;
  extraction_default_unit: string;
  extraction_state_format: string;
  extraction_notes: string;
};

const emptyForm: RulesFormState = {
  extraction_price_format: "",
  extraction_qty_format: "",
  extraction_order_pattern: "",
  extraction_default_unit: "",
  extraction_state_format: "",
  extraction_notes: "",
};

function detailToForm(detail: SupplierExtractionDetail): RulesFormState {
  return {
    extraction_price_format: detail.extraction_price_format ?? "",
    extraction_qty_format: detail.extraction_qty_format ?? "",
    extraction_order_pattern: detail.extraction_order_pattern ?? "",
    extraction_default_unit: detail.extraction_default_unit ?? "",
    extraction_state_format: detail.extraction_state_format ?? "",
    extraction_notes: detail.extraction_notes ?? "",
  };
}

// ---------------------------------------------------------------------------
// メインコンポーネント
// ---------------------------------------------------------------------------

interface SupplierExtractionRulesPageProps {
  /** 解析管理ページ内に埋め込む場合 true。PageLayout ラッパーをスキップする */
  embedded?: boolean;
}

export default function SupplierExtractionRulesPage({ embedded = false }: SupplierExtractionRulesPageProps) {
  const { t } = useTranslation();
  const { isSuperAdmin, loading: authLoading } = useSuperAdmin();

  const [suppliers, setSuppliers] = useState<SupplierOverviewItem[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  const [listError, setListError] = useState("");

  const [selectedSupplier, setSelectedSupplier] = useState<{ supplier_id: number; name: string } | null>(null);
  const [detail, setDetail] = useState<SupplierExtractionDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detailError, setDetailError] = useState("");

  const [form, setForm] = useState<RulesFormState>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [savedMessage, setSavedMessage] = useState(false);

  const [messages, setMessages] = useState<SupplierSourceMessage[]>([]);
  const [messageIndex, setMessageIndex] = useState(0);

  // ---------------------------------------------------------------------------
  // 一覧取得
  // ---------------------------------------------------------------------------

  const fetchList = useCallback(async () => {
    setLoadingList(true);
    setListError("");
    try {
      const data = await api.get<SupplierOverviewItem[]>(
        "/super-admin/suppliers/extraction-overview"
      );
      // unit_ng_count 降順ソート（問題先出し）
      const sorted = [...data].sort((a, b) => b.unit_ng_count - a.unit_ng_count);
      setSuppliers(sorted);
    } catch {
      setListError(t("common.errorLoading"));
    } finally {
      setLoadingList(false);
    }
  }, [t]);

  useEffect(() => {
    if (!authLoading && isSuperAdmin) {
      void fetchList();
    }
  }, [authLoading, isSuperAdmin, fetchList]);

  // ---------------------------------------------------------------------------
  // 詳細取得
  // ---------------------------------------------------------------------------

  const fetchDetail = useCallback(async (id: number) => {
    setLoadingDetail(true);
    setDetailError("");
    try {
      const data = await api.get<SupplierExtractionDetail>(
        `/super-admin/suppliers/${id}/extraction-rules`
      );
      setDetail(data);
      setForm(detailToForm(data));
    } catch {
      setDetailError(t("common.errorLoading"));
    } finally {
      setLoadingDetail(false);
    }
  }, [t]);

  const fetchMessages = useCallback(async (id: number) => {
    try {
      const data = await api.get<{ messages: SupplierSourceMessage[]; total: number }>(
        `/super-admin/suppliers/${id}/source-messages`
      );
      setMessages(data.messages);
      setMessageIndex(0);
    } catch {
      setMessages([]);
      setMessageIndex(0);
    }
  }, []);

  const handleSelectSupplier = useCallback(
    (row: SupplierOverviewItem) => {
      setSelectedSupplier({ supplier_id: row.supplier_id, name: row.name });
      setDetail(null);
      setForm(emptyForm);
      setSavedMessage(false);
      setMessages([]);
      setMessageIndex(0);
      void fetchDetail(row.supplier_id);
      void fetchMessages(row.supplier_id);
    },
    [fetchDetail, fetchMessages]
  );

  const handleBack = useCallback(() => {
    setSelectedSupplier(null);
    setDetail(null);
    setForm(emptyForm);
    setSavedMessage(false);
    setMessages([]);
    setMessageIndex(0);
  }, []);

  // ---------------------------------------------------------------------------
  // フォーム保存
  // ---------------------------------------------------------------------------

  const handleSave = useCallback(async () => {
    if (!selectedSupplier) return;
    setSaving(true);
    setSavedMessage(false);
    try {
      const payload: Record<string, string | null> = {
        extraction_price_format: form.extraction_price_format || null,
        extraction_qty_format: form.extraction_qty_format || null,
        extraction_order_pattern: form.extraction_order_pattern || null,
        extraction_default_unit: form.extraction_default_unit || null,
        extraction_state_format: form.extraction_state_format || null,
        extraction_notes: form.extraction_notes || null,
      };
      await api.patch(
        `/super-admin/suppliers/${selectedSupplier.supplier_id}/extraction-rules`,
        payload
      );
      setSavedMessage(true);
    } finally {
      setSaving(false);
    }
  }, [selectedSupplier, form]);

  // ---------------------------------------------------------------------------
  // 権限ガード
  // ---------------------------------------------------------------------------

  if (authLoading) return null;
  if (!isSuperAdmin) {
    const forbiddenContent = <p>{t("common.forbidden")}</p>;
    return embedded ? forbiddenContent : (
      <PageLayout navKey="nav.superAdminSupplierExtractionRules">
        {forbiddenContent}
      </PageLayout>
    );
  }

  // ---------------------------------------------------------------------------
  // 一覧テーブル列定義
  // ---------------------------------------------------------------------------

  const columns: DataTableColumn<SupplierOverviewItem>[] = [
    {
      key: "name",
      header: t("supplierExtractionRules.supplierName"),
      renderCell: (row) => row.name,
    },
    {
      key: "total_items",
      header: t("supplierExtractionRules.totalItems"),
      renderCell: (row) => String(row.total_items),
    },
    {
      key: "unit_ng_count",
      header: t("supplierExtractionRules.unitNg"),
      renderCell: (row) => (
        row.unit_ng_count > 0
          ? <Badge variant="warning">{String(row.unit_ng_count)}</Badge>
          : <Badge variant="success">{String(row.unit_ng_count)}</Badge>
      ),
    },
    {
      key: "has_extraction_rules",
      header: t("supplierExtractionRules.hasRules"),
      renderCell: (row) =>
        row.has_extraction_rules ? (
          <Badge variant="info">{t("supplierExtractionRules.configured")}</Badge>
        ) : (
          <Badge variant="neutral">{t("supplierExtractionRules.notConfigured")}</Badge>
        ),
    },
  ];

  // ---------------------------------------------------------------------------
  // 詳細ビューのコンテンツ
  // ---------------------------------------------------------------------------

  const detailContent = selectedSupplier !== null ? (
    <div>
      <div className="supplier-rules-header">
        <Button
          variant="ghost"
          size="sm"
          onClick={handleBack}
        >
          ← {t("supplierExtractionRules.back")}
        </Button>
        {/* eslint-disable-next-line no-restricted-syntax */}
        <h2 className="supplier-rules-header-title">{selectedSupplier.name}</h2>
      </div>

      {detailError && <p>{detailError}</p>}
      {loadingDetail && <p>{t("common.loading")}</p>}

      {!loadingDetail && detail && (
        <div className="supplier-rules-split">
          {/* 左: 原文テキスト */}
          <div className="supplier-rules-source">
            {messages.length > 0 ? (
              <>
                <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", marginBottom: "var(--space-3)" }}>
                  <Button
                    variant="ghost"
                    size="sm"
                    iconOnly
                    aria-label={t("common.previous")}
                    onClick={() => setMessageIndex((i: number) => i - 1)}
                    disabled={messageIndex <= 0}
                  >
                    {(() => { const BackIcon = SCHEDULE_SETTINGS_ICONS.back; return <BackIcon style={{ width: "var(--icon-md)", height: "var(--icon-md)" }} />; })()}
                  </Button>
                  <span style={{ fontSize: "var(--font-sm)" }}>
                    {messageIndex + 1} / {messages.length}
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    iconOnly
                    aria-label={t("common.next")}
                    onClick={() => setMessageIndex((i: number) => i + 1)}
                    disabled={messageIndex >= messages.length - 1}
                  >
                    {(() => { const NextIcon = DashboardIcons.arrowRight; return <NextIcon style={{ width: "var(--icon-md)", height: "var(--icon-md)" }} />; })()}
                  </Button>
                </div>
                <div style={{ fontSize: "var(--font-xs)", color: "var(--color-text-muted)", marginBottom: "var(--space-2)" }}>
                  {messages[messageIndex].created_at}
                </div>
                <pre className="supplier-rules-source-pre">{messages[messageIndex].raw_text}</pre>
              </>
            ) : (
              <span className="supplier-rules-source-empty">
                {t("supplierExtractionRules.noMessages")}
              </span>
            )}
          </div>

          {/* 右: ルール設定フォーム */}
          <div className="supplier-rules-form">
            <TextField
              label={t("supplierExtractionRules.priceFormat")}
              helperText={t("supplierExtractionRules.priceFormatHelper")}
              value={form.extraction_price_format}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, extraction_price_format: e.target.value }))
              }
              fullWidth
            />

            <TextField
              label={t("supplierExtractionRules.qtyFormat")}
              helperText={t("supplierExtractionRules.qtyFormatHelper")}
              value={form.extraction_qty_format}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, extraction_qty_format: e.target.value }))
              }
              fullWidth
            />

            <Select
              label={t("supplierExtractionRules.orderPattern")}
              value={form.extraction_order_pattern}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, extraction_order_pattern: e.target.value }))
              }
              options={[
                { value: "", label: t("supplierExtractionRules.orderUnset") },
                { value: "price_at_qty", label: t("supplierExtractionRules.orderPriceAtQty") },
                { value: "qty_at_price", label: t("supplierExtractionRules.orderQtyAtPrice") },
              ]}
              fullWidth
            />

            <TextField
              label={t("supplierExtractionRules.defaultUnit")}
              helperText={t("supplierExtractionRules.defaultUnitHelper")}
              value={form.extraction_default_unit}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, extraction_default_unit: e.target.value }))
              }
              fullWidth
            />

            <TextField
              label={t("supplierExtractionRules.stateFormat")}
              helperText={t("supplierExtractionRules.stateFormatHelper")}
              value={form.extraction_state_format}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, extraction_state_format: e.target.value }))
              }
              fullWidth
            />

            <Textarea
              label={t("supplierExtractionRules.notes")}
              helperText={t("supplierExtractionRules.notesHelper")}
              value={form.extraction_notes}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, extraction_notes: e.target.value }))
              }
              rows={4}
              fullWidth
            />

            <div className="supplier-rules-form-actions">
              {savedMessage && (
                <span className="supplier-rules-saved-msg">
                  {t("supplierExtractionRules.saved")}
                </span>
              )}
              <Button
                variant="primary"
                onClick={() => void handleSave()}
                disabled={saving}
              >
                {t("supplierExtractionRules.save")}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  ) : null;

  // ---------------------------------------------------------------------------
  // 一覧ビューのコンテンツ
  // ---------------------------------------------------------------------------

  const listContent = (
    <div>
      {listError && <p>{listError}</p>}
      {loadingList ? (
        <p>{t("common.loading")}</p>
      ) : (
        <DataTable
          columns={columns}
          data={suppliers}
          rowKey={(row) => String(row.supplier_id)}
          onRowClick={handleSelectSupplier}
        />
      )}
    </div>
  );

  const pageContent = detailContent ?? listContent;

  // embedded モード: PageLayout を使わずにコンテンツのみ返す
  if (embedded) return pageContent;

  // ---------------------------------------------------------------------------
  // スタンドアロンモード（直接 URL アクセス）
  // ---------------------------------------------------------------------------

  return (
    <PageLayout navKey="nav.superAdminSupplierExtractionRules">
      {pageContent}
    </PageLayout>
  );
}
