/**
 * BuybackProductHistoryDrawer — 商品別価格推移 Drawer（店舗比較重ね表示）
 *
 * product_id 軸で全店舗（homura/shinsoku）の価格推移を重ねて表示する。
 * ADR-157: 買取相場ログ
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
import { SelectControl } from "../../components/Select";
import {
  type ByProductItem,
  type ProductHistoryResponse,
  type PriceHistoryEntry,
  formatChartDate,
} from "./buybackTypes";

interface MergedDataPoint {
  date: string;
  homura: number | null;
  shinsoku: number | null;
}

interface BuybackProductHistoryDrawerProps {
  open: boolean;
  item: ByProductItem | null;
  onClose: () => void;
}

function mergeHistory(
  historyMap: Record<string, PriceHistoryEntry[]>,
  selectedGrade: string,
): MergedDataPoint[] {
  const dateMap: Record<string, MergedDataPoint> = {};
  const priceKey = `price_${selectedGrade}` as keyof PriceHistoryEntry;

  const homuraEntries = historyMap["homura"] ?? [];
  const shinsokuEntries = historyMap["shinsoku"] ?? [];

  for (const entry of homuraEntries) {
    if (!entry.fetched_at) continue;
    const date = entry.fetched_at.slice(0, 10);
    if (!dateMap[date]) {
      dateMap[date] = { date, homura: null, shinsoku: null };
    }
    dateMap[date].homura = (entry[priceKey] as number) ?? null;
  }

  for (const entry of shinsokuEntries) {
    if (!entry.fetched_at) continue;
    const date = entry.fetched_at.slice(0, 10);
    if (!dateMap[date]) {
      dateMap[date] = { date, homura: null, shinsoku: null };
    }
    dateMap[date].shinsoku = (entry[priceKey] as number) ?? null;
  }

  return Object.values(dateMap).sort((a, b) => a.date.localeCompare(b.date));
}

export function BuybackProductHistoryDrawer({
  open,
  item,
  onClose,
}: BuybackProductHistoryDrawerProps) {
  const { t } = useTranslation();
  const [historyMap, setHistoryMap] = useState<Record<string, PriceHistoryEntry[]> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState<number>(30);
  const [grade, setGrade] = useState<string>("s");

  const gradeOptions = [
    { value: "s", label: t("buybackPrices.columnPriceS") },
    { value: "a", label: t("buybackPrices.columnPriceA") },
    { value: "b", label: t("buybackPrices.columnPriceB") },
  ];

  // 商品が切り替わったとき
  useEffect(() => {
    if (!item || !open) return;
    setHistoryMap(null);
    setDays(30);
    setError(null);
    setLoading(true);

    api
      .get<ProductHistoryResponse>(
        `/buyback-prices/by-product/${item.product_id}/history?days=30`,
      )
      .then((res) => setHistoryMap(res.history))
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : null;
        setError(msg ?? t("buybackPrices.loadError"));
      })
      .finally(() => setLoading(false));
  }, [item, open]);

  // 期間切り替え
  useEffect(() => {
    if (!item || !open) return;
    setHistoryMap(null);
    setError(null);
    setLoading(true);

    api
      .get<ProductHistoryResponse>(
        `/buyback-prices/by-product/${item.product_id}/history?days=${days}`,
      )
      .then((res) => setHistoryMap(res.history))
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : null;
        setError(msg ?? t("buybackPrices.loadError"));
      })
      .finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [days]);

  const chartData: MergedDataPoint[] =
    historyMap ? mergeHistory(historyMap, grade) : [];

  const periodItems = [
    { key: "7", label: t("buybackPrices.history7d") },
    { key: "30", label: t("buybackPrices.history30d") },
    { key: "90", label: t("buybackPrices.history90d") },
  ];

  const hasData = chartData.length > 0;

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={item?.name_ja ?? t("buybackPrices.byProduct.priceHistory")}
    >
      <div style={{ padding: "var(--space-3)" }}>
        {loading && (
          <p role="status">{t("common.loading")}</p>
        )}

        {!loading && error && (
          <p style={{ color: "var(--danger)", fontSize: "var(--font-sm)" }}>
            {error}
          </p>
        )}

        {!loading && !error && historyMap && (
          <>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "var(--space-3)",
                marginBottom: "var(--space-3)",
              }}
            >
              <SelectControl
                options={gradeOptions}
                value={grade}
                onChange={(e) => setGrade(e.target.value)}
                size="sm"
              />
              <Tabs
                items={periodItems}
                activeKey={String(days)}
                onChange={(k) => setDays(Number(k))}
                variant="pill"
                size="sm"
              />
            </div>

            {!hasData ? (
              <p style={{ color: "var(--text-muted)", fontSize: "var(--font-sm)" }}>
                {t("buybackPrices.byProduct.noHistory")}
              </p>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <LineChart
                  data={chartData}
                  margin={{ top: 8, right: 16, bottom: 0, left: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(v: string) => {
                      const d = new Date(v);
                      return formatChartDate(d.toISOString());
                    }}
                    tick={{ fontSize: 11, fill: "var(--text-secondary)" }}
                  />
                  <YAxis
                    tickFormatter={(v: number) => `¥${v.toLocaleString()}`}
                    tick={{ fontSize: 11, fill: "var(--text-secondary)" }}
                    width={72}
                  />
                  <Tooltip
                    formatter={(value) => [
                      `¥${Number(value ?? 0).toLocaleString()}`,
                      undefined,
                    ]}
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
                    dataKey="homura"
                    name={t("buybackPrices.byProduct.homura")}
                    stroke="var(--accent)"
                    strokeWidth={2}
                    dot={false}
                    connectNulls
                  />
                  <Line
                    type="monotone"
                    dataKey="shinsoku"
                    name={t("buybackPrices.byProduct.shinsoku")}
                    stroke="var(--info)"
                    strokeWidth={2}
                    strokeDasharray="5 3"
                    dot={false}
                    connectNulls
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </>
        )}

        {!loading && !error && !historyMap && (
          <p style={{ color: "var(--text-muted)", fontSize: "var(--font-sm)" }}>
            {t("buybackPrices.byProduct.noHistory")}
          </p>
        )}
      </div>
    </Drawer>
  );
}
