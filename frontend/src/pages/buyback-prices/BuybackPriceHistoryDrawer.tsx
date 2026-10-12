/**
 * BuybackPriceHistoryDrawer — 買取価格推移 Drawer
 */
import { useEffect, useState } from "react";
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
import { Drawer } from "../../components/Drawer";
import { Tabs } from "../../components/Tabs";
import {
  type BuybackProduct,
  type PriceHistoryResponse,
  type PriceHistoryEntry,
  formatChartDate,
} from "./buybackTypes";
import styles from "./BuybackPricesPage.module.css";

interface BuybackPriceHistoryDrawerProps {
  open: boolean;
  product: BuybackProduct | null;
  onClose: () => void;
}

export function BuybackPriceHistoryDrawer({
  open,
  product,
  onClose,
}: BuybackPriceHistoryDrawerProps) {
  const { t } = useTranslation();
  const [history, setHistory] = useState<PriceHistoryResponse | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyDays, setHistoryDays] = useState<number>(30);

  // 商品が切り替わったとき
  useEffect(() => {
    if (!product || !open) return;
    setHistory(null);
    setHistoryDays(30);
    setHistoryLoading(true);

    api
      .get<PriceHistoryResponse>(
        `/buyback-prices/${product.shop_product_id}/history?days=30`,
      )
      .then(setHistory)
      .catch(() => { /* サイレント */ })
      .finally(() => setHistoryLoading(false));
  }, [product, open]);

  // 期間切り替え
  useEffect(() => {
    if (!product || !open) return;
    setHistory(null);
    setHistoryLoading(true);

    api
      .get<PriceHistoryResponse>(
        `/buyback-prices/${product.shop_product_id}/history?days=${historyDays}`,
      )
      .then(setHistory)
      .catch(() => { /* サイレント */ })
      .finally(() => setHistoryLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [historyDays]);

  const chartData =
    history?.history.map((h: PriceHistoryEntry) => ({
      date: formatChartDate(h.fetched_at),
      S: h.price_s,
      A: h.price_a,
      AM: h.price_am,
      B: h.price_b,
      C: h.price_c,
    })) ?? [];

  const periodItems = [
    { key: "7", label: t("buybackPrices.history7d") },
    { key: "30", label: t("buybackPrices.history30d") },
    { key: "90", label: t("buybackPrices.history90d") },
  ];

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={product?.product_name ?? t("buybackPrices.priceHistory")}
    >
      <div className={styles.drawerBody}>
        {historyLoading && (
          <p role="status">{t("common.loading")}</p>
        )}

        {!historyLoading && history && (
          <>
            <p className={styles.historyMeta}>
              {t("buybackPrices.historyDays", { days: historyDays })} — {product?.shop_code}
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
  );
}
