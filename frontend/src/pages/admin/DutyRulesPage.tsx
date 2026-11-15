/**
 * DutyRulesPage — 関税の額の決まり（invoice-create-portfolio 便B・design.md §3-6）
 *
 * - 上に今の会社の関税の条件（DAP・DDU・DDP）を読むだけで出す。変えるのは会社の決まりのページ。
 * - DDP のときだけ、ここの額が請求書に効く。DAP・DDU のときは「今は関税を請求しません」と出す。
 * - 一覧（国・送料の会社・有効期間・根拠）と、足す・直す・消す。
 * - 見る: tenant.profile.view／edit。足す・直す・消す: tenant.profile.edit。
 *
 * ルート: /management-center/duty-rules
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";
import { usePermissions } from "../../hooks/usePermissions";
import { PageLayout } from "../../components/PageLayout";
import { Button } from "../../components/Button";
import { Badge } from "../../components/Badge";
import { Callout } from "../../components/Callout";
import { Stack } from "../../components/Stack";
import { TextLink } from "../../components/TextLink";
import ConfirmModal from "../../components/ConfirmModal";
import { DataTable } from "../../components/DataTable";
import type { DataTableColumn } from "../../components/DataTable";
import { LoadingBlock, Spinner } from "../../components/loading";
import { BASE_LABEL_KEYS, DutyRuleFormModal } from "./DutyRuleFormModal";
import { DUTY_RULES_HEAD } from "./dutyRuleTypes";
import type { DutyRule, DutyRuleOptions } from "./dutyRuleTypes";

/** 窓の状態。null は閉じている。rule が null なら足す、あれば直す */
type FormState = { rule: DutyRule | null } | null;

export default function DutyRulesPage() {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();
  const canEdit = hasPermission("tenant.profile.edit");
  const rulesQuery = useApiQuery<DutyRule[]>("/admin/duty-rules");
  const optionsQuery = useApiQuery<DutyRuleOptions>("/admin/duty-rules/options");
  const invalidate = useInvalidateApi();
  const [form, setForm] = useState<FormState>(null);
  const [deleting, setDeleting] = useState<DutyRule | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const rules = rulesQuery.data ?? [];
  const options = optionsQuery.data;
  const loadFailed = rulesQuery.isError || optionsQuery.isError;
  const shownError = error ?? (loadFailed ? t("dutyRules.loadError") : null);

  const handleSaved = () => {
    setForm(null);
    void invalidate(DUTY_RULES_HEAD);
  };

  const handleDelete = async () => {
    if (deleting === null) return;
    setSaving(true);
    setError(null);
    try {
      await api.delete(`/admin/duty-rules/${deleting.id}`);
      setDeleting(null);
      void invalidate(DUTY_RULES_HEAD);
    } catch {
      setError(t("dutyRules.deleteError"));
    } finally {
      setSaving(false);
    }
  };

  const baseLabel = (base: string) => (BASE_LABEL_KEYS[base] ? t(BASE_LABEL_KEYS[base]) : base);

  const columns: DataTableColumn<DutyRule>[] = [
    { key: "country", header: t("dutyRules.country"), renderCell: (r) => r.destination_country_code },
    { key: "carrier", header: t("dutyRules.carrier"), renderCell: (r) => r.carrier ?? t("dutyRules.anyCarrier") },
    {
      key: "label",
      header: t("dutyRules.label"),
      renderCell: (r) => (
        <>
          {r.label}
          {!r.is_active && (
            <>
              {" "}
              <Badge variant="neutral" size="sm">{t("dutyRules.inactive")}</Badge>
            </>
          )}
        </>
      ),
    },
    {
      key: "period",
      header: t("dutyRules.period"),
      renderCell: (r) =>
        t("dutyRules.periodValue", { from: r.effective_from, to: r.effective_to ?? t("dutyRules.noEnd") }),
    },
    {
      key: "components",
      header: t("dutyRules.componentsTitle"),
      renderCell: (r) => (
        <Stack gap="1">
          {r.components.map((c) => (
            <span key={c.id}>
              {t("dutyRules.componentSummary", { label: c.label, rate: c.rate_pct, base: baseLabel(c.base) })}
            </span>
          ))}
        </Stack>
      ),
    },
    { key: "source", header: t("dutyRules.sourceUrl"), renderCell: (r) => r.source_url },
  ];
  if (canEdit) {
    columns.push({
      key: "actions",
      header: t("dutyRules.actions"),
      renderCell: (r) => (
        <Stack direction="row" gap="2">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => setForm({ rule: r })}
            aria-label={t("dutyRules.editAriaLabel", { name: r.label })}
          >
            {t("common.edit")}
          </Button>
          <Button
            type="button"
            variant="danger"
            size="sm"
            onClick={() => setDeleting(r)}
            aria-label={t("dutyRules.deleteAriaLabel", { name: r.label })}
          >
            {t("common.delete")}
          </Button>
        </Stack>
      ),
    });
  }

  const pending = rulesQuery.isPending || optionsQuery.isPending;
  const fetching = (rulesQuery.isFetching || optionsQuery.isFetching) && !pending;

  return (
    <PageLayout navKey="nav.dutyRules" headerLeft={fetching ? <Spinner size="sm" /> : undefined}>
      {pending && !loadFailed ? (
        <LoadingBlock />
      ) : (
        <Stack gap="4">
          {options && (
            <Callout
              variant="info"
              title={t("dutyRules.incotermsTitle", { value: options.duty_incoterms })}
            >
              <Stack gap="1">
                <span>
                  {options.duty_incoterms === "DDP" ? t("dutyRules.incotermsDdp") : t("dutyRules.incotermsNotDdp")}
                </span>
                <TextLink to="/management-center/tenant-policy">{t("dutyRules.changeTerms")}</TextLink>
              </Stack>
            </Callout>
          )}
          {shownError && <p role="alert">{shownError}</p>}
          {canEdit && options && (
            <Stack direction="row" gap="2">
              <Button type="button" variant="primary" size="md" onClick={() => setForm({ rule: null })}>
                {t("dutyRules.add")}
              </Button>
            </Stack>
          )}
          <DataTable
            columns={columns}
            data={rules}
            rowKey={(r) => String(r.id)}
            emptyState={loadFailed ? undefined : t("dutyRules.empty")}
          />
        </Stack>
      )}

      {form !== null && options && (
        <DutyRuleFormModal
          key={form.rule?.id ?? "new"}
          open
          rule={form.rule}
          options={options}
          onClose={() => setForm(null)}
          onSaved={handleSaved}
        />
      )}
      <ConfirmModal
        open={deleting !== null}
        title={t("dutyRules.deleteTitle")}
        message={t("dutyRules.deleteMessage", { name: deleting?.label ?? "" })}
        confirmLabel={t("common.delete")}
        danger
        confirmLoading={saving}
        onConfirm={() => void handleDelete()}
        onCancel={() => setDeleting(null)}
      />
    </PageLayout>
  );
}
