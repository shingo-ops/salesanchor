/**
 * /super-admin/fx-rate — 為替レート管理画面（SSOT）。
 *
 * - public.app_fx_rates の現在値（USD/JPY）を表示
 * - 手動更新ボタン（POST /api/v1/super-admin/fx-rate/refresh）
 * - is_super_admin=true のみアクセス可（Page 内で 403 ガード）
 *
 * 変更履歴:
 *   2026-06-28: 初版
 */
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import { PageLayout } from "../../components/PageLayout";
import { SCHEDULE_SETTINGS_ICONS } from "../../constants/icons";

interface FxRate {
  currency: string;
  rate_jpy: number;
  fetched_at: string;
  updated_at: string;
}

export default function FxRatePage() {
  const { t } = useTranslation();
  const { isSuperAdmin, loading: authLoading } = useSuperAdmin();
  const [rate, setRate] = useState<FxRate | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [fetching, setFetching] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    setFetching(true);
    setError("");
    try {
      const data = await api.get<FxRate>("/fx-rate/USD");
      setRate(data);
    } catch {
      // 404 = まだ未取得（noData 表示）。他エラーは error 表示。
      setRate(null);
    } finally {
      setFetching(false);
    }
  }, []);

  useEffect(() => {
    if (!authLoading && isSuperAdmin) {
      void load();
    }
  }, [authLoading, isSuperAdmin, load]);

  const handleRefresh = async () => {
    setError("");
    setSuccess("");
    setRefreshing(true);
    try {
      const data = await api.post<FxRate>("/super-admin/fx-rate/refresh", {});
      setRate(data);
      setSuccess(t("superAdmin.fxRate.refreshSuccess"));
    } catch {
      setError(t("superAdmin.fxRate.refreshError"));
    } finally {
      setRefreshing(false);
    }
  };

  if (authLoading) {
    return <div className="page">{t("common.loading")}</div>;
  }

  if (!isSuperAdmin) {
    return (
      <PageLayout navKey="nav.superAdminFxRate">
        <div className="error-message" role="alert">
          {t("superAdmin.accessDenied")}
        </div>
      </PageLayout>
    );
  }

  const RefreshIcon = SCHEDULE_SETTINGS_ICONS.sync;

  return (
    <PageLayout
      navKey="nav.superAdminFxRate"
      subtitleKey="superAdmin.fxRate.subtitle"
      headerAction={
        <button
          type="button"
          className="btn-primary"
          onClick={handleRefresh}
          disabled={refreshing}
          data-testid="fx-rate-refresh-btn"
        >
          <RefreshIcon size={16} aria-hidden="true" />
          {refreshing ? t("common.loading") : t("superAdmin.fxRate.refreshBtn")}
        </button>
      }
    >
      {error && (
        <div className="error-message" role="alert" data-testid="fx-rate-error">
          {error}
        </div>
      )}
      {success && (
        <div className="success-message" role="status" data-testid="fx-rate-success">
          {success}
        </div>
      )}

      {fetching ? (
        <div>{t("common.loading")}</div>
      ) : rate === null ? (
        <div className="empty-state-message" data-testid="fx-rate-no-data">
          {t("superAdmin.fxRate.noData")}
        </div>
      ) : (
        <table
          className="data-table"
          style={{ width: "100%", marginTop: "var(--space-4)" }}
          data-testid="fx-rate-table"
        >
          <thead>
            <tr>
              <th>{t("superAdmin.fxRate.currency")}</th>
              <th>{t("superAdmin.fxRate.rateJpy")}</th>
              <th>{t("superAdmin.fxRate.fetchedAt")}</th>
              <th>{t("superAdmin.fxRate.updatedAt")}</th>
            </tr>
          </thead>
          <tbody>
            <tr data-testid="fx-rate-row">
              <td>{rate.currency}</td>
              <td data-testid="fx-rate-value">
                {rate.rate_jpy != null ? (
                  <>
                    {rate.rate_jpy.toLocaleString("ja-JP", {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 4,
                    })}
                    {" "}
                    {t("common.yen")}
                  </>
                ) : "-"}
              </td>
              <td style={{ fontSize: "var(--font-sm)" }}>
                {rate.fetched_at ? `${rate.fetched_at.replace("T", " ").slice(0, 19)} UTC` : "-"}
              </td>
              <td style={{ fontSize: "var(--font-sm)" }}>
                {rate.updated_at ? `${rate.updated_at.replace("T", " ").slice(0, 19)} UTC` : "-"}
              </td>
            </tr>
          </tbody>
        </table>
      )}
    </PageLayout>
  );
}
