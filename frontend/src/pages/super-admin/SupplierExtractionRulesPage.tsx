/**
 * SupplierExtractionRulesPage — 仕入元別 抽出ルール設定（/super-admin/supplier-extraction-rules）
 *
 * 一覧: 全仕入元をunit_ng降順で表示（DataTable）
 * 詳細: 左=原文テキスト / 右=ルール設定フォーム
 *
 * ADR-027: 全UI文字列は t("key") 経由。
 * ADR-144: 金型コンポーネントのみ使用。
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import { PageLayout } from "../../components/PageLayout";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { Badge } from "../../components/Badge";
import { TextField } from "../../components/TextField";
import { Select, SelectControl } from "../../components/Select";
import { Textarea } from "../../components/Textarea";
import { Button } from "../../components/Button";
import { DashboardIcons, SCHEDULE_SETTINGS_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";
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
  extraction_example_text: string | null;
  latest_raw_text: string | null;
}

interface KnowledgeRule {
  id: number;
  category: string;
  pattern_type: string;
  pattern: string;
  normalized_to: string | null;
  description: string | null;
  is_active: boolean;
}

interface KnowledgeLink {
  id: number;
  supplier_id: number;
  knowledge_rule_id: number;
  category: string;
  pattern: string;
  normalized_to: string | null;
  description: string | null;
  is_active: boolean;
}

interface SupplierSourceMessage {
  id: string;
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
  extraction_example_text: string;
};

const emptyForm: RulesFormState = {
  extraction_price_format: "",
  extraction_qty_format: "",
  extraction_order_pattern: "",
  extraction_default_unit: "",
  extraction_state_format: "",
  extraction_notes: "",
  extraction_example_text: "",
};

function detailToForm(detail: SupplierExtractionDetail): RulesFormState {
  return {
    extraction_price_format: detail.extraction_price_format ?? "",
    extraction_qty_format: detail.extraction_qty_format ?? "",
    extraction_order_pattern: detail.extraction_order_pattern ?? "",
    extraction_default_unit: detail.extraction_default_unit ?? "",
    extraction_state_format: detail.extraction_state_format ?? "",
    extraction_notes: detail.extraction_notes ?? "",
    extraction_example_text: detail.extraction_example_text ?? "",
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

  const [formatTokens, setFormatTokens] = useState<string[]>([]);

  const [messages, setMessages] = useState<SupplierSourceMessage[]>([]);
  const [messageIndex, setMessageIndex] = useState(0);

  // Knowledge links state
  const [knowledgeLinks, setKnowledgeLinks] = useState<KnowledgeLink[]>([]);
  const [allKnowledgeRules, setAllKnowledgeRules] = useState<Record<string, KnowledgeRule[]>>({});
  const [knowledgeAddMode, setKnowledgeAddMode] = useState<Record<string, "none" | "select" | "create">>(
    { block_delimiter: "none", skip_condition: "none", status_keyword: "none" }
  );
  const [knowledgeSelectValue, setKnowledgeSelectValue] = useState<Record<string, string>>(
    { block_delimiter: "", skip_condition: "", status_keyword: "" }
  );
  const [knowledgeNewPattern, setKnowledgeNewPattern] = useState<Record<string, string>>(
    { block_delimiter: "", skip_condition: "", status_keyword: "" }
  );
  const [knowledgeNewNormalizedTo, setKnowledgeNewNormalizedTo] = useState<Record<string, string>>(
    { block_delimiter: "", skip_condition: "", status_keyword: "" }
  );

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

  const fetchKnowledgeLinks = useCallback(async (supplierId: number) => {
    try {
      const data = await api.get<KnowledgeLink[]>(
        `/super-admin/suppliers/${supplierId}/knowledge-links`
      );
      setKnowledgeLinks(data);
    } catch {
      setKnowledgeLinks([]);
    }
  }, []);

  const fetchAllKnowledgeRules = useCallback(async () => {
    const categories = ["block_delimiter", "skip_condition", "status_keyword"] as const;
    const results: Record<string, KnowledgeRule[]> = {};
    await Promise.all(
      categories.map(async (cat) => {
        try {
          const data = await api.get<KnowledgeRule[]>(
            `/super-admin/knowledge-rules?category=${cat}`
          );
          results[cat] = data;
        } catch {
          results[cat] = [];
        }
      })
    );
    setAllKnowledgeRules(results);
  }, []);

  const handleDeleteKnowledgeLink = useCallback(async (supplierId: number, linkId: number) => {
    try {
      await api.delete(`/super-admin/suppliers/${supplierId}/knowledge-links/${linkId}`);
      setKnowledgeLinks((prev) => prev.filter((l) => l.id !== linkId));
    } catch {
      // silent: UI stays the same
    }
  }, []);

  const handleAddKnowledgeLink = useCallback(async (supplierId: number, category: string) => {
    const ruleId = parseInt(knowledgeSelectValue[category], 10);
    if (!ruleId) return;
    try {
      const newLink = await api.post<KnowledgeLink>(
        `/super-admin/suppliers/${supplierId}/knowledge-links`,
        { knowledge_rule_id: ruleId }
      );
      setKnowledgeLinks((prev) => [...prev, newLink]);
      setKnowledgeSelectValue((prev) => ({ ...prev, [category]: "" }));
      setKnowledgeAddMode((prev) => ({ ...prev, [category]: "none" }));
    } catch {
      // silent
    }
  }, [knowledgeSelectValue]);

  const handleCreateAndLinkKnowledgeRule = useCallback(async (supplierId: number, category: string) => {
    const pattern = knowledgeNewPattern[category].trim();
    if (!pattern) return;
    try {
      const newRule = await api.post<KnowledgeRule>("/super-admin/knowledge-rules", {
        category,
        pattern,
        normalized_to: knowledgeNewNormalizedTo[category].trim() || null,
      });
      // allKnowledgeRules を更新
      setAllKnowledgeRules((prev) => ({
        ...prev,
        [category]: [...(prev[category] ?? []), newRule],
      }));
      // リンクを作成
      const newLink = await api.post<KnowledgeLink>(
        `/super-admin/suppliers/${supplierId}/knowledge-links`,
        { knowledge_rule_id: newRule.id }
      );
      setKnowledgeLinks((prev) => [...prev, newLink]);
      setKnowledgeNewPattern((prev) => ({ ...prev, [category]: "" }));
      setKnowledgeNewNormalizedTo((prev) => ({ ...prev, [category]: "" }));
      setKnowledgeAddMode((prev) => ({ ...prev, [category]: "none" }));
    } catch {
      // silent
    }
  }, [knowledgeNewPattern, knowledgeNewNormalizedTo]);

  const handleSelectSupplier = useCallback(
    (row: SupplierOverviewItem) => {
      setSelectedSupplier({ supplier_id: row.supplier_id, name: row.name });
      setDetail(null);
      setForm(emptyForm);
      setSavedMessage(false);
      setMessages([]);
      setMessageIndex(0);
      setKnowledgeLinks([]);
      setKnowledgeAddMode({ block_delimiter: "none", skip_condition: "none", status_keyword: "none" });
      void fetchDetail(row.supplier_id);
      void fetchMessages(row.supplier_id);
      void fetchKnowledgeLinks(row.supplier_id);
      void fetchAllKnowledgeRules();
    },
    [fetchDetail, fetchMessages, fetchKnowledgeLinks, fetchAllKnowledgeRules]
  );

  const handleBack = useCallback(() => {
    setSelectedSupplier(null);
    setDetail(null);
    setForm(emptyForm);
    setSavedMessage(false);
    setMessages([]);
    setMessageIndex(0);
    setFormatTokens([]);
    setKnowledgeLinks([]);
    setKnowledgeAddMode({ block_delimiter: "none", skip_condition: "none", status_keyword: "none" });
  }, []);

  // ---------------------------------------------------------------------------
  // フォーマットビルダー: detail ロード時にトークン配列を復元
  // ---------------------------------------------------------------------------

  useEffect(() => {
    if (detail?.extraction_order_pattern) {
      try {
        const parsed: unknown = JSON.parse(detail.extraction_order_pattern);
        if (Array.isArray(parsed)) {
          setFormatTokens(parsed as string[]);
        } else {
          setFormatTokens([]);
        }
      } catch {
        setFormatTokens([]);
      }
    } else {
      setFormatTokens([]);
    }
  }, [detail]);

  // ---------------------------------------------------------------------------
  // フォーマットビルダー: プレビューとパターン文字列
  // ---------------------------------------------------------------------------

  const sampleValues: Record<string, string> = useMemo(() => ({
    quantity: "30",
    unit: "BOX",
    price: "13,500",
    status: t("supplierExtractionRules.sampleStatus"),
    "@": t("supplierExtractionRules.token.at"),
    yen: t("supplierExtractionRules.token.yen"),
    yen_prefix: t("supplierExtractionRules.token.yenPrefix"),
    space: " ",
    dot: t("supplierExtractionRules.token.dot"),
    newline: "\\n",
    slash: t("supplierExtractionRules.token.slash"),
    stock_label: t("supplierExtractionRules.token.stockLabel"),
    none: "",
  }), [t]);

  const formatPreview = useMemo(
    () => formatTokens.map((tok) => sampleValues[tok] ?? tok).join(""),
    [formatTokens, sampleValues]
  );

  const formatPattern = useMemo(() => {
    const patternParts: Record<string, string> = {
      quantity: t("supplierExtractionRules.patternQuantity"),
      unit: t("supplierExtractionRules.patternUnit"),
      price: t("supplierExtractionRules.patternPrice"),
      status: t("supplierExtractionRules.patternStatus"),
      "@": t("supplierExtractionRules.token.at"),
      yen: t("supplierExtractionRules.token.yen"),
      yen_prefix: t("supplierExtractionRules.token.yenPrefix"),
      space: " ",
      dot: t("supplierExtractionRules.token.dot"),
      newline: t("supplierExtractionRules.patternNewline"),
      slash: t("supplierExtractionRules.token.slash"),
      stock_label: t("supplierExtractionRules.token.stockLabel"),
      none: "",
    };
    return formatTokens.map((tok) => patternParts[tok] ?? tok).join("");
  }, [formatTokens, t]);

  // ---------------------------------------------------------------------------
  // フォーマットビルダー: トークン操作
  // ---------------------------------------------------------------------------

  const addToken = useCallback(() => {
    setFormatTokens((prev) => [...prev, "quantity"]);
  }, []);

  const updateToken = useCallback((index: number, value: string) => {
    setFormatTokens((prev) => prev.map((tok, i) => (i === index ? value : tok)));
  }, []);

  const removeToken = useCallback((index: number) => {
    setFormatTokens((prev) => prev.filter((_, i) => i !== index));
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
        extraction_order_pattern: formatTokens.length > 0 ? JSON.stringify(formatTokens) : null,
        extraction_default_unit: form.extraction_default_unit || null,
        extraction_state_format: form.extraction_state_format || null,
        extraction_notes: form.extraction_notes || null,
        extraction_example_text: form.extraction_example_text || null,
      };
      await api.patch(
        `/super-admin/suppliers/${selectedSupplier.supplier_id}/extraction-rules`,
        payload
      );
      setSavedMessage(true);
    } finally {
      setSaving(false);
    }
  }, [selectedSupplier, form, formatTokens]);

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
  // フォーマットビルダー: トークン選択肢
  // ---------------------------------------------------------------------------

  const tokenOptions = [
    { value: "quantity", label: t("supplierExtractionRules.token.quantity") },
    { value: "unit", label: t("supplierExtractionRules.token.unit") },
    { value: "price", label: t("supplierExtractionRules.token.price") },
    { value: "status", label: t("supplierExtractionRules.token.status") },
    { value: "@", label: t("supplierExtractionRules.token.at") },
    { value: "yen", label: t("supplierExtractionRules.token.yen") },
    { value: "yen_prefix", label: t("supplierExtractionRules.token.yenPrefix") },
    { value: "space", label: t("supplierExtractionRules.token.space") },
    { value: "dot", label: t("supplierExtractionRules.token.dot") },
    { value: "newline", label: t("supplierExtractionRules.token.newline") },
    { value: "slash", label: t("supplierExtractionRules.token.slash") },
    { value: "stock_label", label: t("supplierExtractionRules.token.stockLabel") },
    { value: "none", label: t("supplierExtractionRules.token.none") },
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
                    {(() => { const BackIcon = SCHEDULE_SETTINGS_ICONS.back; return <BackIcon size={ICON.md} />; })()}
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
                    {(() => { const NextIcon = DashboardIcons.arrowRight; return <NextIcon size={ICON.md} />; })()}
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
            {/* フォーマットビルダー */}
            <div style={{ marginBottom: "var(--space-4)" }}>
              <label style={{ display: "block", fontSize: "var(--font-sm)", fontWeight: 600, marginBottom: "var(--space-2)" }}>
                {t("supplierExtractionRules.formatBuilder")}
              </label>

              {/* トークン行 */}
              <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)", alignItems: "center", marginBottom: "var(--space-2)" }}>
                {formatTokens.map((tok, index) => (
                  <div key={index} style={{ display: "flex", alignItems: "center", gap: "var(--space-1)" }}>
                    <SelectControl
                      value={tok}
                      onChange={(e) => updateToken(index, e.target.value)}
                      options={tokenOptions}
                      size="sm"
                    />
                    <Button
                      variant="ghost"
                      size="sm"
                      iconOnly
                      aria-label={t("common.delete")}
                      onClick={() => removeToken(index)}
                    >
                      {(() => { const CloseIcon = SCHEDULE_SETTINGS_ICONS.close; return <CloseIcon size={ICON.md} />; })()}
                    </Button>
                  </div>
                ))}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={addToken}
                >
                  + {t("supplierExtractionRules.addElement")}
                </Button>
              </div>

              {/* プレビュー */}
              <div style={{
                padding: "var(--space-2) var(--space-3)",
                backgroundColor: "var(--color-bg-subtle)",
                borderRadius: "var(--radius-md)",
                fontSize: "var(--font-sm)",
              }}>
                <span style={{ color: "var(--color-text-muted)", marginRight: "var(--space-2)" }}>
                  {t("supplierExtractionRules.formatPreview")}:
                </span>
                <code>{formatPreview}</code>
                {formatTokens.length > 0 && (
                  <span style={{ color: "var(--color-text-muted)", marginLeft: "var(--space-3)", fontSize: "var(--font-xs)" }}>
                    ({formatPattern})
                  </span>
                )}
              </div>
            </div>

            {/* Knowledge ルール セクション */}
            <div style={{ marginBottom: "var(--space-4)" }}>
              <label style={{ display: "block", fontSize: "var(--font-sm)", fontWeight: 600, marginBottom: "var(--space-3)" }}>
                {t("supplierExtractionRules.knowledgeSection")}
              </label>
              {(["block_delimiter", "skip_condition", "status_keyword"] as const).map((category) => {
                const labelKey = category === "block_delimiter"
                  ? "knowledgeBlockDelimiters"
                  : category === "skip_condition"
                  ? "knowledgeSkipConditions"
                  : "knowledgeStatusKeywords";
                const helperKey = (labelKey + "Helper") as `${typeof labelKey}Helper`;
                const linkedItems = knowledgeLinks.filter((l) => l.category === category);
                const linkedIds = new Set(linkedItems.map((l) => l.knowledge_rule_id));
                const availableRules = (allKnowledgeRules[category] ?? []).filter((r) => !linkedIds.has(r.id));
                const addMode = knowledgeAddMode[category];

                return (
                  <div key={category} style={{ marginBottom: "var(--space-4)", paddingBottom: "var(--space-3)", borderBottom: "1px solid var(--color-border)" }}>
                    <div style={{ fontSize: "var(--font-xs)", fontWeight: 600, color: "var(--color-text-muted)", marginBottom: "var(--space-1)" }}>
                      {t(`supplierExtractionRules.${labelKey}`)}
                    </div>
                    <div style={{ fontSize: "var(--font-xs)", color: "var(--color-text-muted)", marginBottom: "var(--space-2)" }}>
                      {t(`supplierExtractionRules.${helperKey}`)}
                    </div>

                    {/* リンク済みバッジ */}
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)", marginBottom: "var(--space-2)" }}>
                      {linkedItems.length === 0 ? (
                        <span style={{ fontSize: "var(--font-xs)", color: "var(--color-text-muted)" }}>
                          {t("supplierExtractionRules.noRulesLinked")}
                        </span>
                      ) : (
                        linkedItems.map((link) => (
                          <div key={link.id} style={{ display: "flex", alignItems: "center", gap: "var(--space-1)" }}>
                            <Badge variant="info">{link.pattern}</Badge>
                            <Button
                              variant="ghost"
                              size="sm"
                              iconOnly
                              aria-label={t("common.delete")}
                              onClick={() => void handleDeleteKnowledgeLink(selectedSupplier!.supplier_id, link.id)}
                            >
                              {(() => { const CloseIcon = SCHEDULE_SETTINGS_ICONS.close; return <CloseIcon size={ICON.sm} />; })()}
                            </Button>
                          </div>
                        ))
                      )}
                    </div>

                    {/* 追加/新規ボタンと入力 */}
                    {addMode === "none" && (
                      <div style={{ display: "flex", gap: "var(--space-2)" }}>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setKnowledgeAddMode((prev) => ({ ...prev, [category]: "select" }))}
                          disabled={availableRules.length === 0}
                        >
                          + {t("supplierExtractionRules.addRule")}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setKnowledgeAddMode((prev) => ({ ...prev, [category]: "create" }))}
                        >
                          + {t("supplierExtractionRules.createNewRule")}
                        </Button>
                      </div>
                    )}

                    {addMode === "select" && (
                      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                        <SelectControl
                          value={knowledgeSelectValue[category]}
                          onChange={(e) =>
                            setKnowledgeSelectValue((prev) => ({ ...prev, [category]: e.target.value }))
                          }
                          options={[
                            { value: "", label: "---" },
                            ...availableRules.map((r) => ({ value: String(r.id), label: r.pattern })),
                          ]}
                          size="sm"
                        />
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={() => void handleAddKnowledgeLink(selectedSupplier!.supplier_id, category)}
                          disabled={!knowledgeSelectValue[category]}
                        >
                          {t("supplierExtractionRules.addRule")}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setKnowledgeAddMode((prev) => ({ ...prev, [category]: "none" }))}
                        >
                          {t("common.cancel")}
                        </Button>
                      </div>
                    )}

                    {addMode === "create" && (
                      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
                        <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "flex-end" }}>
                          <TextField
                            label={t("supplierExtractionRules.newRulePattern")}
                            value={knowledgeNewPattern[category]}
                            onChange={(e) =>
                              setKnowledgeNewPattern((prev) => ({ ...prev, [category]: e.target.value }))
                            }
                          />
                          {category === "status_keyword" && (
                            <TextField
                              label={t("supplierExtractionRules.newRuleNormalizedTo")}
                              value={knowledgeNewNormalizedTo[category]}
                              onChange={(e) =>
                                setKnowledgeNewNormalizedTo((prev) => ({ ...prev, [category]: e.target.value }))
                              }
                            />
                          )}
                          <Button
                            variant="primary"
                            size="sm"
                            onClick={() => void handleCreateAndLinkKnowledgeRule(selectedSupplier!.supplier_id, category)}
                            disabled={!knowledgeNewPattern[category].trim()}
                          >
                            {t("supplierExtractionRules.createNewRule")}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setKnowledgeAddMode((prev) => ({ ...prev, [category]: "none" }))}
                          >
                            {t("common.cancel")}
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            <Textarea
              label={t("supplierExtractionRules.extractionInstruction")}
              value={form.extraction_notes}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, extraction_notes: e.target.value }))
              }
              rows={10}
              placeholder={t("supplierExtractionRules.extractionInstructionPlaceholder")}
              fullWidth
            />

            <Textarea
              label={t("supplierExtractionRules.exampleText")}
              value={form.extraction_example_text}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, extraction_example_text: e.target.value }))
              }
              rows={8}
              placeholder={t("supplierExtractionRules.exampleTextPlaceholder")}
              fullWidth
            />

            <details style={{ marginTop: "var(--space-4)" }}>
              <summary style={{
                cursor: "pointer",
                fontSize: "var(--font-sm)",
                color: "var(--color-text-muted)",
                marginBottom: "var(--space-3)",
                userSelect: "none",
              }}>
                {t("supplierExtractionRules.advancedSettings")}
              </summary>
              <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)", paddingTop: "var(--space-3)" }}>
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
              </div>
            </details>

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
