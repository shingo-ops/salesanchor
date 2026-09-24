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
import { api } from "../../lib/api";
import { PageLayout } from "../../components/PageLayout";
import { ContentToolbar } from "../../components/ContentToolbar";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { SelectControl } from "../../components/Select";
import { TextField } from "../../components/TextField";
import { Tabs } from "../../components/Tabs";
import { Button } from "../../components/Button";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import { Badge } from "../../components/Badge";
import {
  type BuybackProduct,
  type BuybackListResponse,
  type CardGame,
  type ShopFilter,
  PER_PAGE,
  formatPrice,
  formatDate,
} from "./buybackTypes";
import { BuybackPriceHistoryDrawer } from "./BuybackPriceHistoryDrawer";
import { BuybackAlertModal } from "./BuybackAlertModal";
import { BuybackPendingReviewModal } from "./BuybackPendingReviewModal";
import { BuybackByProductPage } from "./BuybackByProductPage";
import styles from "./BuybackPricesPage.module.css";

type ViewMode = "shop" | "product";

export default function BuybackPricesPage() {
  const { t } = useTranslation();
  const { isSuperAdmin } = useSuperAdmin();

  const [viewMode, setViewMode] = useState<ViewMode>("shop");

  const [items, setItems] = useState<BuybackProduct[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [shop, setShop] = useState<ShopFilter>("all");
  const [cardGame, setCardGame] = useState<CardGame>("all");
  const [productType, setProductType] = useState<string>("");
  const [search, setSearch] = useState("");
  const [swingDays, setSwingDays] = useState<string>("");
  const [minSwing, setMinSwing] = useState<string>("");
  const [sortKey, setSortKey] = useState("price_s");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [countsByGame, setCountsByGame] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [fetching, setFetching] = useState(false);
  const [fetchMsg, setFetchMsg] = useState("");

  // Drawer
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<BuybackProduct | null>(null);

  // Alert Modal
  const [alertsOpen, setAlertsOpen] = useState(false);

  // Pending Review Modal
  const [reviewOpen, setReviewOpen] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);

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
    if (search) params.set("q", encodeURIComponent(search));
    if (swingDays) params.set("swing_days", swingDays);
    if (minSwing) params.set("min_swing", minSwing);

    api
      .get<BuybackListResponse>(`/buyback-prices?${params.toString()}`)
      .then((res) => {
        if (!cancelled) {
          setItems(res.items);
          setTotal(res.total);
          setCountsByGame(res.counts_by_game ?? {});
          const count = res.items.filter((item) => item.match_status === "pending_review").length;
          setPendingCount(count);
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
  }, [page, shop, cardGame, productType, search, swingDays, minSwing, sortKey, sortDir, t]);

  const handleShopChange = (value: ShopFilter) => {
    setShop(value);
    setPage(1);
  };
  const handleCardGameChange = (key: CardGame) => {
    setCardGame(key);
    setPage(1);
  };

  const handleRowClick = (row: BuybackProduct) => {
    setSelectedProduct(row);
    setDrawerOpen(true);
  };

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
      key: "product_name_ja",
      header: t("buybackPrices.columnLinkedProduct"),
      width: "180px",
      renderCell: (row: BuybackProduct) => {
        if (row.match_status === "pending_review") {
          return <Badge variant="warning" size="sm">{t("buybackPrices.pendingReview")}</Badge>;
        }
        if (row.product_code && row.product_name_ja) {
          return (
            <span style={{ fontSize: "var(--font-sm)" }}>
              <Badge variant="success" size="sm" dot>{row.product_code}</Badge>
              {" "}{row.product_name_ja}
            </span>
          );
        }
        return <span style={{ color: "var(--text-muted)", fontSize: "var(--font-sm)" }}>—</span>;
      },
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
    ...(swingDays ? [{
      key: "swing_s",
      header: t("buybackPrices.swingColumn"),
      width: "90px",
      renderCell: (row: BuybackProduct) => {
        const v = row.swing_s;
        if (v === null || v === undefined) {
          return <span style={{ color: "var(--text-muted)" }}>{t("buybackPrices.noSwingData")}</span>;
        }
        const color = v > 0 ? "var(--danger)" : "var(--text-muted)";
        return (
          <span className={styles.priceCell} style={{ color }}>
            {v > 0 ? "+" : ""}{formatPrice(v)}
          </span>
        );
      },
    } as DataTableColumn<BuybackProduct>] : []),
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

  // ── ページネーション ───────────────────────────────────────────────
  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE));
  const hasNextPage = page < totalPages;

  return (
    <PageLayout navKey="nav.buybackPrices" subtitleKey="buybackPrices.subtitle">
      <ContentToolbar
        left={
          <>
            <Button
              variant={viewMode === "shop" ? "primary" : "outline"}
              size="sm"
              onClick={() => setViewMode("shop")}
            >
              {t("buybackPrices.byShop")}
            </Button>
            <Button
              variant={viewMode === "product" ? "primary" : "outline"}
              size="sm"
              onClick={() => setViewMode("product")}
            >
              {t("buybackPrices.byProduct.label")}
            </Button>
            {viewMode === "shop" && (
              <>
                <TextField
                  type="search"
                  placeholder={t("buybackPrices.searchPlaceholder")}
                  value={search}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => { setSearch(e.target.value); setPage(1); }}
                  size="sm"
                />
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
                <SelectControl
                  options={[
                    { value: "", label: t("buybackPrices.swingPeriodAll") },
                    { value: "7", label: t("buybackPrices.swingDays7") },
                    { value: "30", label: t("buybackPrices.swingDays30") },
                    { value: "90", label: t("buybackPrices.swingDays90") },
                  ]}
                  value={swingDays}
                  onChange={(e: React.ChangeEvent<HTMLSelectElement>) => { setSwingDays(e.target.value); setMinSwing(""); setPage(1); }}
                  size="sm"
                />
                {swingDays && (
                  <SelectControl
                    options={[
                      { value: "", label: t("buybackPrices.swingMinAll") },
                      { value: "1000", label: "¥1,000+" },
                      { value: "5000", label: "¥5,000+" },
                      { value: "10000", label: "¥10,000+" },
                    ]}
                    value={minSwing}
                    onChange={(e: React.ChangeEvent<HTMLSelectElement>) => { setMinSwing(e.target.value); setPage(1); }}
                    size="sm"
                  />
                )}
                <Tabs
                  items={gameTabItems}
                  activeKey={cardGame}
                  onChange={handleCardGameChange}
                  variant="pill"
                  size="sm"
                />
              </>
            )}
          </>
        }
        right={
          isSuperAdmin ? (
            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
              {fetchMsg && <span className={styles.statusMsg}>{fetchMsg}</span>}
              {pendingCount > 0 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setReviewOpen(true)}
                >
                  {t("buybackPrices.pendingReviewBtn", { count: pendingCount })}
                </Button>
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setAlertsOpen(true)}
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

      {viewMode === "product" ? (
        <BuybackByProductPage />
      ) : (
        <>
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

          <BuybackPriceHistoryDrawer
            open={drawerOpen}
            product={selectedProduct}
            onClose={() => setDrawerOpen(false)}
          />
        </>
      )}

      <BuybackAlertModal
        open={alertsOpen}
        onClose={() => setAlertsOpen(false)}
      />

      <BuybackPendingReviewModal
        open={reviewOpen}
        onClose={() => {
          setReviewOpen(false);
          setPage(1);
        }}
      />
    </PageLayout>
  );
}
