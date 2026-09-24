/**
 * BuybackByProductPage — 自社商品マスタ軸の買取価格一覧
 *
 * 商品マスタを軸に homura/shinsoku の最新買取価格を横並び比較。
 * categoryタブで切り替え、発売日の新しい順に表示。
 * 行クリック → BuybackPriceHistoryDrawer（shop_product_id で価格推移）
 */
import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { Tabs } from "../../components/Tabs";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import {
  type ByProductItem,
  type ByProductResponse,
  type BuybackProduct,
  PER_PAGE,
  formatPrice,
  formatDate,
} from "./buybackTypes";
import { BuybackPriceHistoryDrawer } from "./BuybackPriceHistoryDrawer";
import styles from "./BuybackPricesPage.module.css";

const CATEGORY_LABELS: Record<string, string> = {
  pokemon: "buybackPrices.pokemon",
  onepiece: "buybackPrices.onepiece",
  yugioh: "buybackPrices.yugioh",
  dragonball: "buybackPrices.dragonball",
  weiss: "buybackPrices.weiss",
  lorcana: "buybackPrices.lorcana",
};

/** ByProductItem → BuybackProduct（shop側 Drawer 用）に変換 */
function toDrawerProduct(row: ByProductItem, shopCode: "homura" | "shinsoku"): BuybackProduct | null {
  const shopProductId =
    shopCode === "homura" ? row.homura_shop_product_id : row.shinsoku_shop_product_id;
  if (!shopProductId) return null;
  return {
    shop_product_id: shopProductId,
    shop_code: shopCode,
    product_name: shopCode === "homura"
      ? (row.homura_product_name ?? row.name_ja)
      : (row.shinsoku_product_name ?? row.name_ja),
    card_game: row.category,
    product_type: "",
    price_s: shopCode === "homura" ? row.homura_price_s : row.shinsoku_price_s,
    price_a: shopCode === "homura" ? row.homura_price_a : row.shinsoku_price_a,
    price_am: null,
    price_b: shopCode === "homura" ? row.homura_price_b : row.shinsoku_price_b,
    price_c: null,
    last_seen_at: null,
    product_code: row.product_code,
    product_name_ja: row.name_ja,
    match_status: "manual",
  };
}

export function BuybackByProductPage() {
  const { t } = useTranslation();

  const [items, setItems] = useState<ByProductItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState<string>("all");
  const [countsByCategory, setCountsByCategory] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Drawer
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerProduct, setDrawerProduct] = useState<BuybackProduct | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");

    const offset = (page - 1) * PER_PAGE;
    const params = new URLSearchParams({
      limit: String(PER_PAGE),
      offset: String(offset),
    });
    if (category !== "all") params.set("category", category);

    api
      .get<ByProductResponse>(`/buyback-prices/by-product?${params.toString()}`)
      .then((res) => {
        if (!cancelled) {
          setItems(res.items);
          setTotal(res.total);
          setCountsByCategory(res.counts_by_category ?? {});
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
  }, [page, category, t]);

  const handleCategoryChange = (key: string) => {
    setCategory(key);
    setPage(1);
  };

  const handleRowClick = (row: ByProductItem) => {
    // homura 優先でDrawerを開く
    const product =
      toDrawerProduct(row, "homura") ?? toDrawerProduct(row, "shinsoku");
    if (product) {
      setDrawerProduct(product);
      setDrawerOpen(true);
    }
  };

  const handleHomuraCellClick = (e: React.MouseEvent, row: ByProductItem) => {
    e.stopPropagation();
    const product = toDrawerProduct(row, "homura");
    if (product) {
      setDrawerProduct(product);
      setDrawerOpen(true);
    }
  };

  const handleShinsokuCellClick = (e: React.MouseEvent, row: ByProductItem) => {
    e.stopPropagation();
    const product = toDrawerProduct(row, "shinsoku");
    if (product) {
      setDrawerProduct(product);
      setDrawerOpen(true);
    }
  };

  // カテゴリタブ（0件は非表示）
  const allCount = (Object.values(countsByCategory) as number[]).reduce((a, b) => a + b, 0);
  const categoryTabItems = [
    { key: "all", label: t("buybackPrices.allGames"), count: allCount },
    ...Object.entries(countsByCategory)
      .filter(([, cnt]) => cnt > 0)
      .map(([key, cnt]) => ({
        key,
        label: CATEGORY_LABELS[key] ? t(CATEGORY_LABELS[key]) : key,
        count: cnt,
      })),
  ];

  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE));
  const hasNextPage = page < totalPages;

  const columns: DataTableColumn<ByProductItem>[] = [
    {
      key: "product_code",
      header: t("buybackPrices.byProduct.columnProductCode"),
      width: "120px",
      renderCell: (row) => (
        <span style={{ fontSize: "var(--font-sm)", color: "var(--text-muted)" }}>
          {row.product_code}
        </span>
      ),
    },
    {
      key: "name_ja",
      header: t("buybackPrices.byProduct.columnProductName"),
      renderCell: (row) => (
        <span style={{ fontSize: "var(--font-sm)" }}>{row.name_ja}</span>
      ),
    },
    {
      key: "release_date",
      header: t("buybackPrices.byProduct.columnReleaseDate"),
      width: "100px",
      renderCell: (row) => (
        <span className={styles.dateCell}>{formatDate(row.release_date)}</span>
      ),
    },
    {
      key: "homura_price_s",
      header: t("buybackPrices.byProduct.columnHomuraS"),
      width: "100px",
      renderCell: (row) =>
        row.homura_shop_product_id ? (
          <button
            type="button"
            className={styles.priceCell}
            onClick={(e) => handleHomuraCellClick(e, row)}
            style={{ background: "none", border: "none", cursor: "pointer", padding: 0 }}
          >
            {formatPrice(row.homura_price_s)}
          </button>
        ) : (
          <span style={{ color: "var(--text-muted)" }}>—</span>
        ),
    },
    {
      key: "shinsoku_price_s",
      header: t("buybackPrices.byProduct.columnShinsokuS"),
      width: "100px",
      renderCell: (row) =>
        row.shinsoku_shop_product_id ? (
          <button
            type="button"
            className={styles.priceCell}
            onClick={(e) => handleShinsokuCellClick(e, row)}
            style={{ background: "none", border: "none", cursor: "pointer", padding: 0 }}
          >
            {formatPrice(row.shinsoku_price_s)}
          </button>
        ) : (
          <span style={{ color: "var(--text-muted)" }}>—</span>
        ),
    },
    {
      key: "diff",
      header: t("buybackPrices.byProduct.columnDiff"),
      width: "90px",
      renderCell: (row) => {
        const h = row.homura_price_s;
        const s = row.shinsoku_price_s;
        if (h === null || s === null) {
          return <span style={{ color: "var(--text-muted)" }}>—</span>;
        }
        const diff = h - s;
        const color = diff > 0
          ? "var(--color-success)"
          : diff < 0
          ? "var(--color-danger)"
          : "var(--text-muted)";
        return (
          <span className={styles.priceCell} style={{ color }}>
            {diff > 0 ? "+" : ""}{formatPrice(diff)}
          </span>
        );
      },
    },
  ];

  return (
    <>
      <div style={{ padding: "var(--space-3) 0" }}>
        <Tabs
          items={categoryTabItems}
          activeKey={category}
          onChange={handleCategoryChange}
          variant="pill"
          size="sm"
        />
      </div>

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
      {!loading && !error && items.length === 0 && (
        <p className={styles.statusMsg}>{t("buybackPrices.byProduct.noLinkedData")}</p>
      )}

      {!error && items.length > 0 && (
        <DataTable
          columns={columns}
          data={items}
          rowKey={(row) => String(row.product_id)}
          onRowClick={handleRowClick}
          emptyState={<span>{t("buybackPrices.byProduct.noLinkedData")}</span>}
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
        product={drawerProduct}
        onClose={() => setDrawerOpen(false)}
      />
    </>
  );
}
