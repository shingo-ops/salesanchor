/**
 * ADR-1058 段2: 解析ダッシュボードの「AI の担当」タブ（design.md §6）。
 * 仕事の一覧は持たない（GET の行をそのまま出す）。切り替えは switchable の行だけ。
 * Modal は1つだけ開き、中を「選ぶ」→「確かめる」の2段で替える（ConfirmModal は使わない）。
 */
import { useCallback, useEffect, useState } from "react";
import i18n from "../../../i18n";
import { api } from "../../../lib/api";
import { Badge } from "../../../components/Badge";
import { Button } from "../../../components/Button";
import { Card } from "../../../components/Card";
import { DataTable } from "../../../components/DataTable";
import type { DataTableColumn } from "../../../components/DataTable";
import { Modal } from "../../../components/Modal";
import { Select } from "../../../components/Select";
import { LoadingBlock } from "../../../components/loading";
import { formatFetchedAtJst } from "./LlmUsageSection";

interface AiChoice {
  choice_id: number;
  provider: string;
  model: string;
}

interface AiJob {
  job_key: string;
  provider: string;
  model: string;
  choice_id: number;
  choices: AiChoice[];
  login_ok: boolean;
  login_reason: string | null;
  last_ok_at: string | null;
  count_24h: number;
  failed_24h: number;
  last_error_code: string | null;
  last_error_at: string | null;
  login_refreshed_at: string | null;
  switchable: boolean;
}

interface AiJobsResponse {
  jobs: AiJob[];
}

interface AiProviderModel {
  provider: string;
  model: string;
}

interface AiJobHistoryItem {
  job_key: string;
  old: AiProviderModel | null;
  new: AiProviderModel;
  changed_by_name: string | null;
  changed_by_id: number | null;
  changed_at: string;
}

interface AiJobHistoryResponse {
  items: AiJobHistoryItem[];
}

type TFn = (key: string, options?: Record<string, unknown>) => string;

export interface AiJobsSectionProps {
  t: TFn;
}

// 値ごとの言葉（キーの有無は AiJobsSection.test.tsx で ja・en とも確かめる）
export function jobLabel(jobKey: string, t: TFn): string {
  return t(`analysisRules.dashboard.aiJobs.job.${jobKey}`, { defaultValue: jobKey });
}

export function providerLabel(provider: string, t: TFn): string {
  return t(`analysisRules.dashboard.aiJobs.provider.${provider}`, { defaultValue: provider });
}

export function errorCodeLabel(code: string, t: TFn): string {
  return t(`analysisRules.dashboard.aiJobs.errorCode.${code}`, { defaultValue: code });
}

export function loginReasonLabel(reason: string, t: TFn): string {
  return t(`analysisRules.dashboard.aiJobs.loginReason.${reason}`, { defaultValue: reason });
}

function choiceLabel(c: AiProviderModel, t: TFn): string {
  return t("analysisRules.dashboard.aiJobs.choiceLabel", { provider: providerLabel(c.provider, t), model: c.model });
}

function formatAt(iso: string | null, t: TFn): string {
  return iso ? formatFetchedAtJst(iso, i18n.language) : t("analysisRules.dashboard.aiJobs.none");
}

function changedByLabel(item: AiJobHistoryItem, t: TFn): string {
  if (item.changed_by_name) return item.changed_by_name;
  if (item.changed_by_id != null) return t("analysisRules.dashboard.aiJobs.userId", { id: item.changed_by_id });
  return t("analysisRules.dashboard.aiJobs.unknownUser");
}

export function AiJobsSection({ t }: AiJobsSectionProps) {
  const [jobs, setJobs] = useState<AiJob[]>([]);
  const [history, setHistory] = useState<AiJobHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<AiJob | null>(null);
  const [step, setStep] = useState<"select" | "confirm">("select");
  const [selected, setSelected] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      api.get<AiJobsResponse>("/super-admin/ai-jobs"),
      api.get<AiJobHistoryResponse>("/super-admin/ai-jobs/history?limit=50"),
    ])
      .then(([jobsRes, historyRes]) => {
        setJobs(jobsRes.jobs);
        setHistory(historyRes.items);
      })
      .catch(() => setError(t("analysisRules.dashboard.fetchError")))
      .finally(() => setLoading(false));
  }, [t]);

  useEffect(() => {
    load();
  }, [load]);

  const openChange = (job: AiJob) => {
    setEditing(job);
    setStep("select");
    setSelected(String(job.choice_id));
    setSaveError(null);
  };

  const close = () => {
    if (saving) return;
    setEditing(null);
  };

  const save = () => {
    if (!editing) return;
    setSaving(true);
    setSaveError(null);
    api
      .put<AiJob>(`/super-admin/ai-jobs/${editing.job_key}`, { choice_id: Number(selected) })
      .then(() => {
        setEditing(null);
        load();
      })
      .catch(() => setSaveError(t("analysisRules.dashboard.aiJobs.saveError")))
      .finally(() => setSaving(false));
  };

  if (loading) return <LoadingBlock />;
  if (error) return <p className="analysis-dashboard-error">{error}</p>;

  const jobColumns: DataTableColumn<AiJob>[] = [
    { key: "job_key", header: t("analysisRules.dashboard.aiJobs.colJob"), ellipsis: true, renderCell: (row) => jobLabel(row.job_key, t) },
    {
      key: "model",
      header: t("analysisRules.dashboard.aiJobs.colAiModel"),
      ellipsis: true,
      renderCell: (row) => choiceLabel({ provider: row.provider, model: row.model }, t),
    },
    {
      key: "login_ok",
      header: t("analysisRules.dashboard.aiJobs.colLogin"),
      ellipsis: true,
      renderCell: (row) =>
        row.login_ok ? (
          <Badge variant="success" size="sm">{t("analysisRules.dashboard.aiJobs.loginOk")}</Badge>
        ) : (
          <Badge variant="danger" size="sm">
            {row.login_reason ? loginReasonLabel(row.login_reason, t) : t("analysisRules.dashboard.aiJobs.loginNg")}
          </Badge>
        ),
    },
    {
      key: "switchable",
      header: t("analysisRules.dashboard.aiJobs.colAction"),
      ellipsis: true,
      renderCell: (row) =>
        row.switchable ? (
          <Button variant="secondary" size="sm" onClick={() => openChange(row)}>
            {t("analysisRules.dashboard.aiJobs.change")}
          </Button>
        ) : (
          t("analysisRules.dashboard.aiJobs.notSwitchable")
        ),
    },
    { key: "last_ok_at", header: t("analysisRules.dashboard.aiJobs.colLastOk"), ellipsis: true, renderCell: (row) => formatAt(row.last_ok_at, t) },
    {
      key: "count_24h",
      header: t("analysisRules.dashboard.aiJobs.col24h"),
      align: "right",
      ellipsis: true,
      renderCell: (row) => t("analysisRules.dashboard.aiJobs.count24h", { count: row.count_24h, failed: row.failed_24h }),
    },
    {
      key: "last_error_code",
      header: t("analysisRules.dashboard.aiJobs.colLastError"),
      ellipsis: true,
      renderCell: (row) =>
        row.last_error_code
          ? t("analysisRules.dashboard.aiJobs.lastErrorWithAt", {
              reason: errorCodeLabel(row.last_error_code, t),
              at: formatAt(row.last_error_at, t),
            })
          : t("analysisRules.dashboard.aiJobs.none"),
    },
    {
      key: "login_refreshed_at",
      header: t("analysisRules.dashboard.aiJobs.colLoginRefreshed"),
      ellipsis: true,
      renderCell: (row) => formatAt(row.login_refreshed_at, t),
    },
  ];

  const historyColumns: DataTableColumn<AiJobHistoryItem>[] = [
    { key: "changed_at", header: t("analysisRules.dashboard.aiJobs.colChangedAt"), renderCell: (row) => formatAt(row.changed_at, t) },
    { key: "job_key", header: t("analysisRules.dashboard.aiJobs.colJob"), renderCell: (row) => jobLabel(row.job_key, t) },
    {
      key: "new",
      header: t("analysisRules.dashboard.aiJobs.colFromTo"),
      renderCell: (row) =>
        t("analysisRules.dashboard.aiJobs.fromTo", {
          from: row.old ? choiceLabel(row.old, t) : t("analysisRules.dashboard.aiJobs.none"),
          to: choiceLabel(row.new, t),
        }),
    },
    { key: "changed_by_name", header: t("analysisRules.dashboard.aiJobs.colChangedBy"), renderCell: (row) => changedByLabel(row, t) },
  ];

  const current = editing?.choices.find((c) => c.choice_id === editing.choice_id) ?? null;
  const target = editing?.choices.find((c) => String(c.choice_id) === selected) ?? null;

  return (
    <div className="analysis-dashboard-existing-section">
      <Card variant="container">
        <div className="analysis-dashboard-section-title">{t("analysisRules.dashboard.aiJobs.title")}</div>
        <DataTable columns={jobColumns} data={jobs} rowKey={(row) => row.job_key} emptyState={t("analysisRules.dashboard.aiJobs.none")} />
      </Card>
      <Card variant="container">
        <div className="analysis-dashboard-section-title">{t("analysisRules.dashboard.aiJobs.historyTitle")}</div>
        <DataTable
          columns={historyColumns}
          data={history}
          rowKey={(row) => `${row.job_key}:${row.changed_at}`}
          emptyState={t("analysisRules.dashboard.aiJobs.noHistory")}
        />
      </Card>
      <Modal
        open={editing !== null}
        onClose={close}
        title={editing ? t("analysisRules.dashboard.aiJobs.modalTitle", { job: jobLabel(editing.job_key, t) }) : ""}
        footer={
          step === "select" ? (
            <>
              <Button variant="secondary" onClick={close}>
                {t("analysisRules.dashboard.aiJobs.cancel")}
              </Button>
              <Button variant="primary" onClick={() => setStep("confirm")}>
                {t("analysisRules.dashboard.aiJobs.next")}
              </Button>
            </>
          ) : (
            <>
              <Button variant="secondary" onClick={() => setStep("select")} disabled={saving}>
                {t("analysisRules.dashboard.aiJobs.back")}
              </Button>
              <Button variant="primary" onClick={save} loading={saving}>
                {t("analysisRules.dashboard.aiJobs.change")}
              </Button>
            </>
          )
        }
      >
        {editing && step === "select" && (
          <Select
            label={t("analysisRules.dashboard.aiJobs.selectLabel")}
            options={editing.choices.map((c) => ({ value: String(c.choice_id), label: choiceLabel(c, t) }))}
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            fullWidth
          />
        )}
        {editing && step === "confirm" && current && target && (
          <p>
            {t("analysisRules.dashboard.aiJobs.confirmText", {
              job: jobLabel(editing.job_key, t),
              from: choiceLabel(current, t),
              to: choiceLabel(target, t),
            })}
          </p>
        )}
        {saveError && <p className="analysis-dashboard-error">{saveError}</p>}
      </Modal>
    </div>
  );
}
