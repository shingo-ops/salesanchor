/**
 * /buyback-prices — 外部買取店の買取価格ページ
 *
 * シンソク・買取ホムラの買取価格を一覧・推移グラフで確認できる画面。
 * - 買取店フィルタ（SelectControl）・カードゲームタブ（Tabs）
 * - DataTable: shop_code / product_name / card_game / product_type / price_s/a/b / last_seen_at
 * - 行クリック → Drawer で価格推移グラフ（recharts LineChart）
 * - スーパー管理者のみ: アラート設定 Modal（CRUD）
 */
import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { api } from "../../lib/api";
import { PageLayout } from "../../components/PageLayout";
import { ContentToolbar } from "../../components/ContentToolbar";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { SelectControl } from "../../components/Select";
import { Tabs } from "../../components/Tabs";
import { Drawer } from "../../components/Drawer";
import { Button } from "../../components/Button";
import { Modal } from "../../components/Modal";
import { Card } from "../../components/Card";
import { Badge } from "../../components/Badge";
import { TextField } from "../../components/TextField";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import styles from "./BuybackPricesPage.module.css";

/* ─── 型定義 ─────────────────────────────────────────────────────────── */

interface BuybackProduct {
  shop_product_id: string;
  shop_code: string;
  product_name: string;
  card_game: string;
  product_type: string;
  price_s: number | null;
  price_a: number | null;
  price_am: number | null;
  price_b: number | null;
  price_c: number | null;
  last_seen_at: string | null;
}

interface BuybackListResponse {
  items: BuybackProduct[];
  total: number;
  counts_by_game: Record<string, number>;
}

interface PriceHistoryEntry {
  price_s: number | null;
  price_a: number | null;
  price_am: number | null;
  price_b: number | null;
  price_c: number | null;
  fetched_at: string;
}

interface PriceHistoryResponse {
  shop_product_id: string;
  product_name: string;
  shop_code: string;
  card_game: string;
  product_type: string;
  history: PriceHistoryEntry[];
}

interface AlertRule {
  id: string;
  name: string;
  card_game: string | null;
  shop_code: string | null;
  product_type: string | null;
  shop_product_id: string | null;
  direction: string;
  threshold_pct: number;
  price_grade: string;
  is_active: boolean;
  last_notified_at: string | null;
  cooldown_minutes: number;
  created_at: string;
  updated_at: string;
}

interface AlertFormState {
  name: string;
  card_game: string;
  shop_code: string;
  product_type: string;
  direction: string;
  threshold_pct: string;
  price_grade: string;
  is_active: boolean;
  cooldown_minutes: string;
}

type CardGame = "all" | "pokemon" | "onepiece" | "yugioh" | "dragonball" | "weiss" | "lorcana";
type ShopFilter = "all" | "shinsoku" | "homura";

const PER_PAGE = 50;

const INITIAL_ALERT_FORM: AlertFormState = {
  name: "",
  card_game: "",
  shop_code: "",
  product_type: "",
  direction: "down",
  threshold_pct: "5",
  price_grade: "price_s",
  is_active: true,
  cooldown_minutes: "360",
};

/* ─── ヘルパー ────────────────────────────────────────────────────────── */

function formatPrice(price: number | null): string {
  if (price === null || price === undefined) return "—";
  return `¥${price.toLocaleString()}`;
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

function formatChartDate(iso: string): string {
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

/* ─── AlertRuleForm サブコンポーネント ────────────────────────────────── */

interface AlertRuleFormProps {
  onSave: (form: AlertFormState) => Promise<void>;
  onCancel: () => void;
  t: (key: string) => string;
}

function AlertRuleForm({ onSave, onCancel, t }: AlertRuleFormProps) {
  const [form, setForm] = useState<AlertFormState>(INITIAL_ALERT_FORM);
  const [saving, setSaving] = useState(false);

  const set = (field: keyof AlertFormState, value: string | boolean) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await onSave(form);
    } finally {
      setSaving(false);
    }
  };

  const directionOptions = [
    { value: "down", label: t("buybackPrices.alertDirectionDown") },
    { value: "up", label: t("buybackPrices.alertDirectionUp") },
    { value: "both", label: t("buybackPrices.alertDirectionBoth") },
  ];

  const gradeOptions = [
    { value: "price_s", label: "S" },
    { value: "price_a", label: "A" },
    { value: "price_am", label: "A-" },
    { value: "price_b", label: "B" },
    { value: "price_c", label: "C" },
  ];

  const gameOptions = [
    { value: "", label: t("buybackPrices.allGames") },
    { value: "pokemon", label: t("buybackPrices.pokemon") },
    { value: "onepiece", label: t("buybackPrices.onepiece") },
    { value: "yugioh", label: t("buybackPrices.yugioh") },
    { value: "dragonball", label: t("buybackPrices.dragonball") },
    { value: "weiss", label: t("buybackPrices.weiss") },
    { value: "lorcana", label: t("buybackPrices.lorcana") },
  ];

  const shopOptions = [
    { value: "", label: t("buybackPrices.allShops") },
    { value: "shinsoku", label: t("buybackPrices.shinsoku") },
    { value: "homura", label: t("buybackPrices.homura") },
  ];

  return (
    <Card variant="container">
      <form onSubmit={handleSubmit}>
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
          <TextField
            label={t("buybackPrices.alertName")}
            value={form.name}
            onChange={(e) => set("name", e.target.value)}
            required
            size="sm"
            fullWidth
          />

          <div style={{ display: "flex", gap: "var(--space-3)", flexWrap: "wrap" }}>
            <div style={{ flex: "1 1 160px" }}>
              <label style={{ display: "block", fontSize: "var(--font-size-sm)", color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}>
                {t("buybackPrices.alertDirection")}
              </label>
              <SelectControl
                options={directionOptions}
                value={form.direction}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => set("direction", e.target.value)}
                size="sm"
              />
            </div>

            <div style={{ flex: "1 1 120px" }}>
              <TextField
                label={t("buybackPrices.alertThreshold")}
                type="number"
                value={form.threshold_pct}
                onChange={(e) => set("threshold_pct", e.target.value)}
                min="0"
                max="100"
                step="0.1"
                required
                size="sm"
                fullWidth
              />
            </div>

            <div style={{ flex: "1 1 120px" }}>
              <label style={{ display: "block", fontSize: "var(--font-size-sm)", color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}>
                {t("buybackPrices.alertGrade")}
              </label>
              <SelectControl
                options={gradeOptions}
                value={form.price_grade}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => set("price_grade", e.target.value)}
                size="sm"
              />
            </div>
          </div>

          <div style={{ display: "flex", gap: "var(--space-3)", flexWrap: "wrap" }}>
            <div style={{ flex: "1 1 160px" }}>
              <label style={{ display: "block", fontSize: "var(--font-size-sm)", color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}>
                {t("buybackPrices.alertCardGame")}
              </label>
              <SelectControl
                options={gameOptions}
                value={form.card_game}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => set("card_game", e.target.value)}
                size="sm"
              />
            </div>

            <div style={{ flex: "1 1 160px" }}>
              <label style={{ display: "block", fontSize: "var(--font-size-sm)", color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}>
                {t("buybackPrices.alertShop")}
              </label>
              <SelectControl
                options={shopOptions}
                value={form.shop_code}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => set("shop_code", e.target.value)}
                size="sm"
              />
            </div>

            <div style={{ flex: "1 1 120px" }}>
              <TextField
                label={t("buybackPrices.alertCooldown")}
                type="number"
                value={form.cooldown_minutes}
                onChange={(e) => set("cooldown_minutes", e.target.value)}
                min="1"
                required
                size="sm"
                fullWidth
              />
            </div>
          </div>

          <div style={{ display: "flex", gap: "var(--space-2)", justifyContent: "flex-end" }}>
            <Button type="button" variant="ghost" size="sm" onClick={onCancel}>
              {t("buybackPrices.alertCancel")}
            </Button>
            <Button type="submit" variant="primary" size="sm" disabled={saving}>
              {t("buybackPrices.alertSave")}
            </Button>
          </div>
        </div>
      </form>
    </Card>
  );
}

/* ─── コンポーネント ──────────────────────────────────────────────────── */

export default function BuybackPricesPage() {
  const { t } = useTranslation();
  const { isSuperAdmin } = useSuperAdmin();

  const [items, setItems] = useState<BuybackProduct[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [shop, setShop] = useState<ShopFilter>("all");
  const [cardGame, setCardGame] = useState<CardGame>("all");
  const [productType, setProductType] = useState<string>("");
  const [sortKey, setSortKey] = useState("price_s");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [countsByGame, setCountsByGame] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [fetching, setFetching] = useState(false);
  const [fetchMsg, setFetchMsg] = useState("");

  // Drawer / 価格推移
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<BuybackProduct | null>(null);
  const [history, setHistory] = useState<PriceHistoryResponse | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyDays, setHistoryDays] = useState<number>(30);

  // Alert rules state
  const [alertsOpen, setAlertsOpen] = useState(false);
  const [alertRules, setAlertRules] = useState<AlertRule[]>([]);
  const [alertLoading, setAlertLoading] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);

  // ── データ取得 ──────────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");

    const offset = (page - 1) * PER_PAGE;
    const params = new URLSearchParams({
      limit: String(PER_PAGE),
      offset: String(offset),
      sort: sortKey,
      order: sortDir,
    });
    if (shop !== "all") params.set("shop", shop);
    if (cardGame !== "all") params.set("card_game", cardGame);
    if (productType) params.append("product_type", productType);

    api
      .get<BuybackListResponse>(`/buyback-prices?${params.toString()}`)
      .then((res) => {
        if (!cancelled) {
          setItems(res.items);
          setTotal(res.total);
          setCountsByGame(res.counts_by_game ?? {});
        }
      })
      .catch(() => {
        if (!cancelled) setError(t("buybackPrices.loadError"));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [page, shop, cardGame, productType, sortKey, sortDir, t]);

  // フィルタ変更時はページをリセット
  const handleShopChange = (value: ShopFilter) => {
    setShop(value);
    setPage(1);
  };
  const handleCardGameChange = (key: CardGame) => {
    setCardGame(key);
    setPage(1);
  };

  // ── 行クリック: Drawer + 価格推移取得 ────────────────────────────
  const handleRowClick = (row: BuybackProduct) => {
    setSelectedProduct(row);
    setDrawerOpen(true);
    setHistory(null);
    setHistoryDays(30);
    setHistoryLoading(true);

    api
      .get<PriceHistoryResponse>(
        `/buyback-prices/${row.shop_product_id}/history?days=30`,
      )
      .then(setHistory)
      .catch(() => {
        /* 履歴取得失敗はサイレント。グラフ空表示 */
      })
      .finally(() => setHistoryLoading(false));
  };

  // ── 期間切り替え: 選択中の商品で再取得 ───────────────────────────
  useEffect(() => {
    if (!selectedProduct || !drawerOpen) return;
    setHistory(null);
    setHistoryLoading(true);

    api
      .get<PriceHistoryResponse>(
        `/buyback-prices/${selectedProduct.shop_product_id}/history?days=${historyDays}`,
      )
      .then(setHistory)
      .catch(() => {
        /* 履歴取得失敗はサイレント。グラフ空表示 */
      })
      .finally(() => setHistoryLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [historyDays]);

  // ── 手動取得 ───────────────────────────────────────────────────────
  const handleManualFetch = async () => {
    setFetching(true);
    setFetchMsg("");
    try {
      await api.post("/buyback-prices/trigger", {});
      setFetchMsg(t("buybackPrices.fetchStarted"));
    } catch {
      setFetchMsg(t("buybackPrices.fetchFailed"));
    } finally {
      setFetching(false);
    }
  };

  // ── ソート ────────────────────────────────────────────────────────
  const handleSort = (key: string, dir: "asc" | "desc") => {
    setSortKey(key);
    setSortDir(dir);
    setPage(1);
  };

  // ── アラートルール CRUD ──────────────────────────────────────────
  const fetchAlertRules = async () => {
    setAlertLoading(true);
    try {
      const res = await api.get("/buyback-alerts");
      setAlertRules(res.items);
    } catch { /* ignore */ }
    setAlertLoading(false);
  };

  const createAlertRule = async (form: AlertFormState) => {
    await api.post("/buyback-alerts", {
      name: form.name,
      card_game: form.card_game || null,
      shop_code: form.shop_code || null,
      product_type: form.product_type || null,
      direction: form.direction,
      threshold_pct: parseFloat(form.threshold_pct),
      price_grade: form.price_grade,
      is_active: form.is_active,
      cooldown_minutes: parseInt(form.cooldown_minutes, 10),
    });
    await fetchAlertRules();
    setShowCreateForm(false);
  };

  const toggleAlertRule = async (rule: AlertRule) => {
    await api.put(`/buyback-alerts/${rule.id}`, {
      ...rule,
      is_active: !rule.is_active,
    });
    await fetchAlertRules();
  };

  const deleteAlertRule = async (id: string) => {
    await api.delete(`/buyback-alerts/${id}`);
    await fetchAlertRules();
  };

  // ── テーブル列定義 ─────────────────────────────────────────────────
  const columns: DataTableColumn<BuybackProduct>[] = [
    {
      key: "shop_code",
      header: t("buybackPrices.columnShop"),
      width: "100px",
      renderCell: (row) => (
        <span className={styles.shopBadge} data-shop={row.shop_code}>
          {row.shop_code === "shinsoku" ? t("buybackPrices.shinsoku") : t("buybackPrices.homura")}
        </span>
      ),
    },
    {
      key: "product_name",
      header: t("buybackPrices.columnName"),
    },
    {
      key: "card_game",
      header: t("buybackPrices.columnGame"),
      width: "120px",
      renderCell: (row) => t(`buybackPrices.${row.card_game}`) ?? row.card_game,
    },
    {
      key: "product_type",
      header: t("buybackPrices.columnType"),
      width: "100px",
    },
    {
      key: "price_s",
      header: t("buybackPrices.columnPriceS"),
      width: "90px",
      sortable: true,
      renderCell: (row) => (
        <span className={styles.priceCell}>{formatPrice(row.price_s)}</span>
      ),
    },
    {
      key: "price_a",
      header: t("buybackPrices.columnPriceA"),
      width: "90px",
      sortable: true,
      renderCell: (row) => (
        <span className={styles.priceCell}>{formatPrice(row.price_a)}</span>
      ),
    },
    {
      key: "price_b",
      header: t("buybackPrices.columnPriceB"),
      width: "90px",
      sortable: true,
      renderCell: (row) => (
        <span className={styles.priceCell}>{formatPrice(row.price_b)}</span>
      ),
    },
    {
      key: "last_seen_at",
      header: t("buybackPrices.columnLastSeen"),
      width: "110px",
      renderCell: (row) => (
        <span className={styles.dateCell}>{formatDate(row.last_seen_at)}</span>
      ),
    },
  ];

  // ── SelectControl 選択肢 ───────────────────────────────────────────
  const shopOptions = [
    { value: "all", label: t("buybackPrices.allShops") },
    { value: "shinsoku", label: t("buybackPrices.shinsoku") },
    { value: "homura", label: t("buybackPrices.homura") },
  ];

  const productTypeOptions = [
    { value: "", label: t("buybackPrices.allTypes") },
    { value: "BOX", label: "BOX" },
    { value: "PACK", label: t("buybackPrices.typePack") },
    { value: "CARTON", label: t("buybackPrices.typeCarton") },
    { value: "BOX_SHRINK", label: t("buybackPrices.typeShrink") },
    { value: "BOX_NO_SHRINK", label: t("buybackPrices.typeNoShrink") },
    { value: "SPECIAL_SET", label: t("buybackPrices.typeSpecialSet") },
  ];

  // ── Tabs 選択肢 ────────────────────────────────────────────────────
  const CARD_GAMES = [
    { key: "pokemon" as CardGame, label: t("buybackPrices.pokemon") },
    { key: "onepiece" as CardGame, label: t("buybackPrices.onepiece") },
    { key: "yugioh" as CardGame, label: t("buybackPrices.yugioh") },
    { key: "dragonball" as CardGame, label: t("buybackPrices.dragonball") },
    { key: "weiss" as CardGame, label: t("buybackPrices.weiss") },
    { key: "lorcana" as CardGame, label: t("buybackPrices.lorcana") },
  ];
  const allCount = (Object.values(countsByGame) as number[]).reduce((a, b) => a + b, 0);
  const gameTabItems = [
    { key: "all" as CardGame, label: t("buybackPrices.allGames"), count: allCount },
    ...CARD_GAMES
      .filter((g) => (countsByGame[g.key] ?? 0) > 0)
      .map((g) => ({ ...g, count: countsByGame[g.key] ?? 0 })),
  ];

  // ── 期間タブ ────────────────────────────────────────────────────
  const periodItems = [
    { key: "7", label: t("buybackPrices.history7d") },
    { key: "30", label: t("buybackPrices.history30d") },
    { key: "90", label: t("buybackPrices.history90d") },
  ];

  // ── ページネーション ───────────────────────────────────────────────
  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE));
  const hasNextPage = page < totalPages;

  // ── 価格推移グラフ用データ ─────────────────────────────────────────
  const chartData =
    history?.history.map((h: PriceHistoryEntry) => ({
      date: formatChartDate(h.fetched_at),
      S: h.price_s,
      A: h.price_a,
      AM: h.price_am,
      B: h.price_b,
      C: h.price_c,
    })) ?? [];

  return (
    <PageLayout navKey="nav.buybackPrices" subtitleKey="buybackPrices.subtitle">
      <ContentToolbar
        left={
          <>
            <SelectControl
              options={shopOptions}
              value={shop}
              placeholder={t("buybackPrices.shopFilter")}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => handleShopChange(e.target.value as ShopFilter)}
            />
            <SelectControl
              options={productTypeOptions}
              value={productType}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => { setProductType(e.target.value); setPage(1); }}
              size="sm"
            />
            <Tabs
              items={gameTabItems}
              activeKey={cardGame}
              onChange={handleCardGameChange}
              variant="pill"
              size="sm"
            />
          </>
        }
        right={
          isSuperAdmin ? (
            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
              {fetchMsg && <span className={styles.statusMsg}>{fetchMsg}</span>}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => { setAlertsOpen(true); fetchAlertRules(); }}
              >
                {t("buybackPrices.alertSettings")}
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={handleManualFetch}
                disabled={fetching}
              >
                {fetching ? "..." : t("buybackPrices.fetchNow")}
              </Button>
            </div>
          ) : undefined
        }
      />

      {loading && (
        <p role="status" className={styles.statusMsg}>
          {t("common.loading")}
        </p>
      )}
      {!loading && error && (
        <p role="alert" className={styles.errorMsg}>
          {error}
        </p>
      )}

      {!error && (
        <DataTable
          columns={columns}
          data={items}
          rowKey={(row) => row.shop_product_id}
          sortKey={sortKey}
          sortDir={sortDir}
          onSort={handleSort}
          onRowClick={handleRowClick}
          emptyState={<span>{t("buybackPrices.noData")}</span>}
          page={page}
          hasNextPage={hasNextPage}
          onPageChange={setPage}
          prevPageLabel={t("common.prevPage")}
          nextPageLabel={t("common.nextPage")}
          pageInfo={<span>{page} / {totalPages}</span>}
          density="compact"
        />
      )}

      {/* ── 価格推移 Drawer ──────────────────────────────────────── */}
      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title={selectedProduct?.product_name ?? t("buybackPrices.priceHistory")}
      >
        <div className={styles.drawerBody}>
          {historyLoading && (
            <p role="status">{t("common.loading")}</p>
          )}

          {!historyLoading && history && (
            <>
              <p className={styles.historyMeta}>
                {t("buybackPrices.historyDays", { days: historyDays })} — {selectedProduct?.shop_code}
              </p>

              <div style={{ marginBottom: "var(--space-3)" }}>
                <Tabs
                  items={periodItems}
                  activeKey={String(historyDays)}
                  onChange={(k) => setHistoryDays(Number(k))}
                  variant="pill"
                  size="sm"
                />
              </div>

              {chartData.length === 0 ? (
                <p className={styles.noHistory}>{t("buybackPrices.noData")}</p>
              ) : (
                <ResponsiveContainer width="100%" height={280}>
                  <LineChart
                    data={chartData}
                    margin={{ top: 8, right: 16, bottom: 0, left: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 11, fill: "var(--text-secondary)" }}
                    />
                    <YAxis
                      tickFormatter={(v: number) => `¥${v.toLocaleString()}`}
                      tick={{ fontSize: 11, fill: "var(--text-secondary)" }}
                      width={70}
                    />
                    <Tooltip
                      formatter={(value) => [`¥${Number(value ?? 0).toLocaleString()}`, undefined]}
                      contentStyle={{
                        background: "var(--bg-card)",
                        border: "1px solid var(--border)",
                        borderRadius: "var(--radius-sm)",
                        fontSize: "12px",
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: "12px" }} />
                    <Line
                      type="monotone"
                      dataKey="S"
                      name={t("buybackPrices.columnPriceS")}
                      stroke="var(--accent)"
                      strokeWidth={2}
                      dot={false}
                      connectNulls
                    />
                    <Line
                      type="monotone"
                      dataKey="A"
                      name={t("buybackPrices.columnPriceA")}
                      stroke="var(--color-success)"
                      strokeWidth={2}
                      dot={false}
                      connectNulls
                    />
                    <Line
                      type="monotone"
                      dataKey="B"
                      name={t("buybackPrices.columnPriceB")}
                      stroke="var(--color-warning)"
                      strokeWidth={2}
                      dot={false}
                      connectNulls
                    />
                    <Line
                      type="monotone"
                      dataKey="AM"
                      name={t("buybackPrices.columnPriceAM")}
                      stroke="var(--info)"
                      strokeWidth={2}
                      dot={false}
                      connectNulls
                    />
                    <Line
                      type="monotone"
                      dataKey="C"
                      name={t("buybackPrices.columnPriceC")}
                      stroke="var(--color-error)"
                      strokeWidth={2}
                      dot={false}
                      connectNulls
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </>
          )}

          {!historyLoading && !history && (
            <p className={styles.noHistory}>{t("buybackPrices.noData")}</p>
          )}
        </div>
      </Drawer>

      {/* ── アラート設定 Modal ────────────────────────────────────── */}
      <Modal
        open={alertsOpen}
        onClose={() => { setAlertsOpen(false); setShowCreateForm(false); }}
        title={t("buybackPrices.alertSettings")}
        size="lg"
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          {!showCreateForm && (
            <Button variant="secondary" size="sm" onClick={() => setShowCreateForm(true)}>
              {t("buybackPrices.alertCreate")}
            </Button>
          )}

          {showCreateForm && (
            <AlertRuleForm
              onSave={createAlertRule}
              onCancel={() => setShowCreateForm(false)}
              t={t}
            />
          )}

          {alertLoading ? (
            <p style={{ color: "var(--text-secondary)" }}>{t("buybackPrices.loading")}</p>
          ) : alertRules.length === 0 ? (
            <p style={{ color: "var(--text-muted)" }}>{t("buybackPrices.alertNoRules")}</p>
          ) : (
            alertRules.map((rule) => (
              <Card key={rule.id} variant="container">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "var(--space-2)" }}>
                  <div>
                    <strong>{rule.name}</strong>
                    <p style={{ color: "var(--text-secondary)", fontSize: "var(--font-size-sm)", margin: 0 }}>
                      {rule.direction === "down"
                        ? t("buybackPrices.alertDirectionDown")
                        : rule.direction === "up"
                          ? t("buybackPrices.alertDirectionUp")
                          : t("buybackPrices.alertDirectionBoth")}
                      {" "}{rule.threshold_pct}% | {rule.price_grade}
                      {rule.card_game && ` | ${rule.card_game}`}
                      {rule.shop_code && ` | ${rule.shop_code}`}
                    </p>
                  </div>
                  <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "center", flexShrink: 0 }}>
                    <Badge variant={rule.is_active ? "success" : "neutral"} size="sm">
                      {rule.is_active ? t("buybackPrices.alertActive") : t("buybackPrices.alertInactive")}
                    </Badge>
                    <Button variant="ghost" size="sm" onClick={() => toggleAlertRule(rule)}>
                      {rule.is_active ? t("buybackPrices.alertDisable") : t("buybackPrices.alertEnable")}
                    </Button>
                    <Button variant="danger" size="sm" onClick={() => deleteAlertRule(rule.id)}>
                      {t("buybackPrices.alertDelete")}
                    </Button>
                  </div>
                </div>
              </Card>
            ))
          )}
        </div>
      </Modal>
    </PageLayout>
  );
}
