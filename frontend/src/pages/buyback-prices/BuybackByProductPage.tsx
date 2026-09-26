/**
 * BuybackByProductPage — 自社商品マスタ軸の買取価格一覧
 *
 * 商品マスタを軸に homura/shinsoku の最新買取価格を横並び比較。
 * categoryタブで切り替え、発売日の新しい順に表示。
 * 行クリック → BuybackProductHistoryDrawer（product_id で店舗比較価格推移）
 */
import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { ContentToolbar } from "../../components/ContentToolbar";
import { Tabs } from "../../components/Tabs";
import { TextField } from "../../components/TextField";
import { SelectControl } from "../../components/Select";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import {
  type ByProductItem,
  type ByProductResponse,
  PER_PAGE,
  formatPrice,
  formatDate,
} from "./buybackTypes";
import { BuybackProductHistoryDrawer } from "./BuybackProductHistoryDrawer";
import styles from "./BuybackPricesPage.module.css";

export function BuybackByProductPage() {
  const { t } = useTranslation();

  const [items, setItems] = useState<ByProductItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState<string>("all");
  const [countsByCategory, setCountsByCategory] = useState<Record<string, number>>({});
  const [categoryNames, setCategoryNames] = useState<Record<string, string>>({});
  const [search, setSearch] = useState("");
  const [swingDays, setSwingDays] = useState<string>("");
  const [minSwing, setMinSwing] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Drawer
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState<ByProductItem | null>(null);

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
    if (search) params.set("q", encodeURIComponent(search));
    if (swingDays) params.set("swing_days", swingDays);
    if (minSwing) params.set("min_swing", minSwing);

    api
      .get<ByProductResponse>(`/buyback-prices/by-product?${params.toString()}`)
      .then((res) => {
        if (!cancelled) {
          setItems(res.items);
          setTotal(res.total);
          setCountsByCategory(res.counts_by_category ?? {});
          setCategoryNames(res.category_names ?? {});
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
  }, [page, category, search, swingDays, minSwing, t]);

  const handleCategoryChange = (key: string) => {
    setCategory(key);
    setPage(1);
  };

  const handleRowClick = (row: ByProductItem) => {
    setSelectedItem(row);
    setDrawerOpen(true);
  };

  // カテゴリタブ（0件は非表示）
  const allCount = (Object.values(countsByCategory) as number[]).reduce((a, b) => a + b, 0);
  const categoryTabItems = [
    { key: "all", label: t("buybackPrices.allGames"), count: allCount },
    ...Object.entries(countsByCategory)
      .filter(([, cnt]) => cnt > 0)
      .map(([key, cnt]) => ({
        key,
        label: categoryNames[key] ?? key,
        count: cnt,
      })),
  ];

  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE));
  const hasNextPage = page < totalPages;

  const columns: DataTableColumn<ByProductItem>[] = [
    {
      key: "mark",
      header: t("buybackPrices.byProduct.columnMark"),
      width: "100px",
      renderCell: (row) => (
        <span style={{ fontSize: "var(--font-sm)", color: "var(--text-muted)" }}>
          {row.mark ?? "—"}
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
      key: "best_price",
      header: t("buybackPrices.byProduct.columnBestPrice"),
      width: "130px",
      renderCell: (row) => (
        <>
          {row.best_price ? (
            <span className={styles.priceCell}>{`¥${row.best_price.toLocaleString()}`}</span>
          ) : (
            <span style={{ color: "var(--text-muted)" }}>—</span>
          )}
          {row.best_shop && (
            <span style={{ fontSize: "var(--font-xs)", color: "var(--text-muted)", marginLeft: "var(--space-1)" }}>
              {row.best_shop === "homura" ? t("buybackPrices.shopHomura") : t("buybackPrices.shopShinsoku")}
            </span>
          )}
        </>
      ),
    },
    {
      key: "yesterday_diff",
      header: t("buybackPrices.byProduct.columnYesterdayDiff"),
      width: "100px",
      renderCell: (row) => {
        if (row.yesterday_diff == null) {
          return <span style={{ color: "var(--text-muted)" }}>—</span>;
        }
        const color =
          row.yesterday_diff > 0
            ? "var(--success)"
            : row.yesterday_diff < 0
            ? "var(--danger)"
            : "var(--text-muted)";
        const prefix = row.yesterday_diff > 0 ? "+" : "";
        return (
          <span style={{ color }}>{`${prefix}¥${row.yesterday_diff.toLocaleString()}`}</span>
        );
      },
    },
    ...(swingDays ? [{
      key: "swing_s",
      header: t("buybackPrices.swingColumn"),
      width: "90px",
      renderCell: (row: ByProductItem) => {
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
    } as DataTableColumn<ByProductItem>] : []),
  ];

  return (
    <>
      <ContentToolbar
        left={
          <>
            <TextField
              type="search"
              placeholder={t("buybackPrices.searchPlaceholder")}
              value={search}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => { setSearch(e.target.value); setPage(1); }}
              size="sm"
              className={styles.searchField}
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
          </>
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
      {!loading && !error && items.length === 0 && (
        <p className={styles.statusMsg}>{t("buybackPrices.byProduct.noLinkedData")}</p>
      )}

      {!error && items.length > 0 && (
        <div className={styles.buybackFilterGroup}>
          <Tabs
            items={categoryTabItems}
            activeKey={category}
            onChange={handleCategoryChange}
            variant="underline"
            size="sm"
          />
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
            className={styles.buybackFilterGroupTable}
          />
        </div>
      )}

      <BuybackProductHistoryDrawer
        open={drawerOpen}
        item={selectedItem}
        onClose={() => setDrawerOpen(false)}
      />
    </>
  );
}
