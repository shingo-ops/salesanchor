/**
 * CommissionsPage — 報酬管理ページ（区切り4 / ADR-021 改修）。
 *
 * order_commissions を担当者別・月次で集計表示する。旧 OrdersTable の
 * 「報酬」列を分離した専用ビュー。レート設定は引き続き報酬設定ページ
 * （/commission-settings）で行う（本ページは閲覧専用）。
 *
 * データ取得:
 *   - GET /commissions/monthly?year=&month= — by_staff / by_role / total
 *     権限は orders.view 流用（commissions.view 未定義のため）。
 */

import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { PageLayout } from "../../components/PageLayout";

type RoleKey = "sales" | "order" | "ship" | "purchase" | "trouble";

interface MonthlyByStaff {
  staff_id: number | null;
  staff_name: string | null;
  total: number;
}

interface MonthlyByRole {
  role: string;
  total: number;
}

interface MonthlySummaryDto {
  year: number;
  month: number;
  by_staff: MonthlyByStaff[];
  by_role: MonthlyByRole[];
  total: number;
}

const fmt = (n: number) =>
  n.toLocaleString("ja-JP", { style: "currency", currency: "JPY" });

export default function CommissionsPage() {
  const { t } = useTranslation();

  // 月選択の初期値は JST 業務日基準（CommissionSettingsPage と同方式）。
  const nowJst = new Date(
    new Date().toLocaleString("en-US", { timeZone: "Asia/Tokyo" }),
  );
  const [year, setYear] = useState(nowJst.getFullYear());
  const [month, setMonth] = useState(nowJst.getMonth() + 1);
  const [monthly, setMonthly] = useState<MonthlySummaryDto | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const ROLE_LABELS: Record<RoleKey, string> = {
    sales: t("commissions.role_sales"),
    order: t("commissions.role_order"),
    ship: t("commissions.role_ship"),
    purchase: t("commissions.role_purchase"),
    trouble: t("commissions.role_trouble"),
  };

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const dto = await api.get<MonthlySummaryDto>(
          `/commissions/monthly?year=${year}&month=${month}`,
        );
        if (!cancelled) setMonthly(dto);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : t("common.fetchError"));
          setMonthly(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [year, month, t]);

  return (
    <PageLayout navKey="nav.commissions" subtitleKey="commissions.listSubtitle">
      {error && <div className="error-message">{error}</div>}

      <fieldset>
        <legend>{t("commissions.monthlyLegend")}</legend>
        <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "center" }}>
          <label>
            {t("commissions.year")}:
            <input
              type="number"
              value={year}
              min={2000}
              max={2999}
              onChange={(e) => setYear(Number(e.target.value))}
              style={{ width: "var(--input-width-year)", marginLeft: "var(--space-2)" }}
              data-testid="commissions-year"
            />
          </label>
          <label>
            {t("commissions.month")}:
            <input
              type="number"
              value={month}
              min={1}
              max={12}
              onChange={(e) => setMonth(Number(e.target.value))}
              style={{ width: "var(--input-width-month)", marginLeft: "var(--space-2)" }}
              data-testid="commissions-month"
            />
          </label>
        </div>

        {loading ? (
          <div className="loading" style={{ marginTop: "var(--space-4)" }}>
            {t("common.loading")}
          </div>
        ) : monthly ? (
          <div style={{ marginTop: "var(--space-4)" }}>
            <p data-testid="commissions-total">
              {t("commissions.total")}: <strong>{fmt(monthly.total)}</strong>
            </p>

            <h4>{t("commissions.byStaff")}</h4>
            <table className="data-table" data-testid="commissions-by-staff">
              <thead>
                <tr>
                  <th>{t("commissions.colRole")}</th>
                  <th>{t("commissions.total")}</th>
                </tr>
              </thead>
              <tbody>
                {monthly.by_staff.length === 0 && (
                  <tr><td colSpan={2} className="empty">{t("commissions.noData")}</td></tr>
                )}
                {monthly.by_staff.map((it) => (
                  <tr key={`${it.staff_id ?? "null"}`}>
                    <td>{it.staff_name ?? t("commissions.unassigned")}</td>
                    <td>{fmt(it.total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <h4>{t("commissions.byRole")}</h4>
            <table className="data-table" data-testid="commissions-by-role">
              <thead>
                <tr>
                  <th>{t("commissions.colRole")}</th>
                  <th>{t("commissions.total")}</th>
                </tr>
              </thead>
              <tbody>
                {monthly.by_role.length === 0 && (
                  <tr><td colSpan={2} className="empty">{t("commissions.noData")}</td></tr>
                )}
                {monthly.by_role.map((it) => (
                  <tr key={it.role}>
                    <td>{ROLE_LABELS[it.role as RoleKey] ?? it.role}</td>
                    <td>{fmt(it.total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-muted" style={{ marginTop: "var(--space-4)" }}>
            {t("commissions.monthlyError")}
          </p>
        )}
      </fieldset>
    </PageLayout>
  );
}
