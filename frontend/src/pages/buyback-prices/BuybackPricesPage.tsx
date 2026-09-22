/**
 * /buyback-prices — 外部買取店の買取価格ページ
 *
 * シンソク・買取ホムラの買取価格を一覧・推移グラフで確認できる画面。
 * - 買取店フィルタ（SelectControl）・カードゲームタブ（Tabs）
 * - DataTable: shop_code / product_name / card_game / product_type / price_s/a/b / last_seen_at
 * - 行クリック → Drawer で価格推移グラフ（recharts LineChart）
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
  price_b: number | null;
  last_seen_at: string | null;
}

interface BuybackListResponse {
  items: BuybackProduct[];
  total: number;
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

type CardGame = "all" | "pokemon" | "onepiece" | "yugioh" | "dragonball" | "weiss" | "lorcana";
type ShopFilter = "all" | "shinsoku" | "homura";

const PER_PAGE = 50;

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

/* ─── コンポーネント ──────────────────────────────────────────────────── */

export default function BuybackPricesPage() {
  const { t } = useTranslation();
  const { isSuperAdmin } = useSuperAdmin();

  const [items, setItems] = useState<BuybackProduct[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [shop, setShop] = useState<ShopFilter>("all");
  const [cardGame, setCardGame] = useState<CardGame>("all");
  const [sortKey, setSortKey] = useState("price_s");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [fetching, setFetching] = useState(false);
  const [fetchMsg, setFetchMsg] = useState("");

  // Drawer / 価格推移
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<BuybackProduct | null>(null);
  const [history, setHistory] = useState<PriceHistoryResponse | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);

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

    api
      .get<BuybackListResponse>(`/buyback-prices?${params.toString()}`)
      .then((res) => {
        if (!cancelled) {
          setItems(res.items);
          setTotal(res.total);
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
  }, [page, shop, cardGame, sortKey, sortDir, t]);

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

  // ── Tabs 選択肢 ────────────────────────────────────────────────────
  const gameTabItems = [
    { key: "all" as CardGame, label: t("buybackPrices.allGames") },
    { key: "pokemon" as CardGame, label: t("buybackPrices.pokemon") },
    { key: "onepiece" as CardGame, label: t("buybackPrices.onepiece") },
    { key: "yugioh" as CardGame, label: t("buybackPrices.yugioh") },
    { key: "dragonball" as CardGame, label: t("buybackPrices.dragonball") },
    { key: "weiss" as CardGame, label: t("buybackPrices.weiss") },
    { key: "lorcana" as CardGame, label: t("buybackPrices.lorcana") },
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
      B: h.price_b,
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
                {t("buybackPrices.historyDays")} — {selectedProduct?.shop_code}
              </p>

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
                      stroke="var(--color-primary)"
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
    </PageLayout>
  );
}
