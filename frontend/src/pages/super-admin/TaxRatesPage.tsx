/**
 * /super-admin/settings/tax-rates — 消費税率の画面（ADR-1061 便2-2a。design.md §3-4 tax_rates・§3-4d）。
 *
 * - public.tax_rates の一覧（適用日の新しい順）と、行の追加・まだ始まっていない行の削除
 * - 足せるのは「明日以降で、いちばん新しい行より後の日付」（表が空のときだけ過去の日付も可。判定は API）
 * - 削除のボタンは、適用日がサーバーの今日（日本時間）より後の行にだけ出す
 * - is_super_admin=true のみ（Page 内で 403 ガード。API 側も require_super_admin）
 */
import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../../lib/api";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import { PageLayout } from "../../components/PageLayout";
import { ContentToolbar } from "../../components/ContentToolbar";
import { Button } from "../../components/Button";
import { DataTable } from "../../components/DataTable";
import type { DataTableColumn } from "../../components/DataTable";
import { EmptyState } from "../../components/EmptyState";
import { Stack } from "../../components/Stack";
import { TextField } from "../../components/TextField";
import ConfirmModal from "../../components/ConfirmModal";
import { LoadingBlock } from "../../components/loading";

interface TaxRate {
  id: number;
  rate_percent: string;
  effective_from: string;
  created_at: string;
}

interface TaxRateList {
  rates: TaxRate[];
  today: string;
}

export default function TaxRatesPage() {
  const { t } = useTranslation();
  const { isSuperAdmin, loading: authLoading } = useSuperAdmin();
  const [data, setData] = useState<TaxRateList | null>(null);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [ratePercent, setRatePercent] = useState("");
  const [effectiveFrom, setEffectiveFrom] = useState("");
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<TaxRate | null>(null);
  const [deleting, setDeleting] = useState(false);

  const errorText = useCallback(
    (err: unknown): string => {
      if (err instanceof ApiError) {
        if (err.responseDetail === "tax_rate.effective_from_invalid") return t("superAdmin.taxRates.errorDateInvalid");
        if (err.responseDetail === "tax_rate.effective_from_taken") return t("superAdmin.taxRates.errorDateTaken");
        if (err.responseDetail === "tax_rate.not_deletable") return t("superAdmin.taxRates.errorNotDeletable");
        if (err.responseDetail === "tax_rate.not_found") return t("superAdmin.taxRates.errorNotFound");
        if (err.status === 422) return t("superAdmin.taxRates.errorInput");
      }
      return t("superAdmin.taxRates.errorGeneric");
    },
    [t],
  );

  const load = useCallback(async () => {
    setFetching(true);
    try {
      setData(await api.get<TaxRateList>("/super-admin/tax-rates"));
    } catch (err) {
      setError(errorText(err));
    } finally {
      setFetching(false);
    }
  }, [errorText]);

  useEffect(() => {
    if (!authLoading && isSuperAdmin) {
      void load();
    }
  }, [authLoading, isSuperAdmin, load]);

  const handleAdd = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setSaving(true);
    try {
      await api.post<TaxRate>("/super-admin/tax-rates", {
        rate_percent: ratePercent,
        effective_from: effectiveFrom,
      });
      setRatePercent("");
      setEffectiveFrom("");
      setSuccess(t("superAdmin.taxRates.addSuccess"));
      await load();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setError("");
    setSuccess("");
    setDeleting(true);
    try {
      await api.delete(`/super-admin/tax-rates/${deleteTarget.id}`);
      setSuccess(t("superAdmin.taxRates.deleteSuccess"));
      setDeleteTarget(null);
      await load();
    } catch (err) {
      setDeleteTarget(null);
      setError(errorText(err));
    } finally {
      setDeleting(false);
    }
  };

  if (authLoading) {
    return <LoadingBlock />;
  }

  if (!isSuperAdmin) {
    return (
      <PageLayout navKey="nav.superAdminTaxRates">
        <div className="error-message" role="alert">
          {t("superAdmin.accessDenied")}
        </div>
      </PageLayout>
    );
  }

  const today = data?.today ?? "";
  const columns: DataTableColumn<TaxRate>[] = [
    { key: "effective_from", header: t("superAdmin.taxRates.effectiveFrom") },
    {
      key: "rate_percent",
      header: t("superAdmin.taxRates.ratePercent"),
      align: "right",
      renderCell: (row) => t("superAdmin.taxRates.ratePercentValue", { rate: row.rate_percent }),
    },
    {
      key: "actions",
      header: t("superAdmin.taxRates.actions"),
      renderCell: (row) =>
        row.effective_from > today ? (
          <Button
            variant="danger"
            size="sm"
            type="button"
            onClick={() => setDeleteTarget(row)}
            data-testid={`tax-rate-delete-${row.id}`}
          >
            {t("superAdmin.taxRates.deleteBtn")}
          </Button>
        ) : null,
    },
  ];

  return (
    <PageLayout navKey="nav.superAdminTaxRates" subtitleKey="superAdmin.taxRates.subtitle">
      <form onSubmit={handleAdd} data-testid="tax-rate-form">
        <ContentToolbar
          left={
            <Stack direction="row" gap="3">
              <TextField
                label={t("superAdmin.taxRates.ratePercent")}
                type="number"
                step="0.01"
                min="0"
                max="100"
                size="sm"
                required
                value={ratePercent}
                onChange={(e) => setRatePercent(e.target.value)}
              />
              <TextField
                label={t("superAdmin.taxRates.effectiveFrom")}
                type="date"
                size="sm"
                required
                value={effectiveFrom}
                onChange={(e) => setEffectiveFrom(e.target.value)}
              />
            </Stack>
          }
          right={
            <Button
              variant="primary"
              size="sm"
              layoutClassName="field-h-md"
              type="submit"
              loading={saving}
              disabled={saving}
              data-testid="tax-rate-add-btn"
            >
              {t("superAdmin.taxRates.addBtn")}
            </Button>
          }
        />
      </form>
      {error && (
        <div className="error-message" role="alert" data-testid="tax-rate-error">
          {error}
        </div>
      )}
      {success && (
        <div className="success-message" role="status" data-testid="tax-rate-success">
          {success}
        </div>
      )}
      {fetching && data === null ? (
        <LoadingBlock />
      ) : (
        <DataTable<TaxRate>
          columns={columns}
          data={data?.rates ?? []}
          rowKey={(row) => String(row.id)}
          rowTestId={(row) => `tax-rate-row-${row.id}`}
          emptyState={<EmptyState title={t("superAdmin.taxRates.noData")} size="compact" />}
        />
      )}
      <ConfirmModal
        open={deleteTarget !== null}
        title={t("superAdmin.taxRates.deleteConfirmTitle")}
        message={t("superAdmin.taxRates.deleteConfirmMessage", {
          date: deleteTarget?.effective_from ?? "",
          rate: deleteTarget?.rate_percent ?? "",
        })}
        confirmLabel={t("superAdmin.taxRates.deleteBtn")}
        danger
        confirmLoading={deleting}
        onConfirm={() => void handleDelete()}
        onCancel={() => setDeleteTarget(null)}
      />
    </PageLayout>
  );
}
