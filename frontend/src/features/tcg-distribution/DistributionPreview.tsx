/**
 * DistributionPreview — 配信候補件数・除外内訳・配信実行ボタン
 *
 * GET /tcg/distribution/preview の結果を表示する。
 * 全件配信ボタンを押すと確認ダイアログを経て POST /tcg/distribution/run を呼ぶ。
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { INBOX_ACTION_ICONS, NAV_ICONS, Check, Warning } from "../../constants/icons";
import type { PreviewData, RunResult } from "./distributionApi";
import { runDistributionAll } from "./distributionApi";

interface Props {
  /** 一覧のリフレッシュを親に通知する */
  onRefreshTargets: () => void;
}

export function DistributionPreview({ onRefreshTargets }: Props) {
  const { t } = useTranslation();
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [loadError, setLoadError] = useState("");
  const [showConfirm, setShowConfirm] = useState(false);
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState<RunResult | null>(null);
  const [runError, setRunError] = useState("");

  const loadPreview = () => {
    setLoadError("");
    api.get<PreviewData>("/tcg/distribution/preview")
      .then(setPreview)
      .catch((e: unknown) => setLoadError(e instanceof Error ? e.message : String(e)));
  };

  useEffect(() => { loadPreview(); }, []);

  const handleRunAll = async () => {
    setShowConfirm(false);
    setRunning(true);
    setRunResult(null);
    setRunError("");
    try {
      const result = await runDistributionAll();
      setRunResult(result);
      onRefreshTargets();
      loadPreview();
    } catch (e: unknown) {
      setRunError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  };

  if (loadError) {
    return (
      <div className="dist-preview-card">
        <p style={{ color: "var(--color-error)", fontSize: "var(--font-sm)" }}>
          {t("common.fetchError")}: {loadError}
        </p>
      </div>
    );
  }

  if (!preview) {
    return (
      <div className="dist-preview-card">
        <p style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>
          {t("common.loading")}
        </p>
      </div>
    );
  }

  const { exclusion } = preview;
  const totalExcluded =
    exclusion.flag_series +
    exclusion.pid_unresolved_only +
    exclusion.unit_unresolved_only +
    exclusion.both_unresolved +
    exclusion.price_unresolved;

  return (
    <>
      <div className="dist-preview-card">
        <div className="dist-preview-header">
          <div>
            <div className="dist-preview-count">
              {preview.output_count.toLocaleString()}
              <span>{t("distributionTarget.preview.candidateUnit")}</span>
            </div>
            {totalExcluded > 0 && (
              <div className="dist-preview-exclusion">
                {exclusion.flag_series > 0 && (
                  <span className="dist-preview-exclusion-item">
                    {t("distributionTarget.preview.excFlag")}: {exclusion.flag_series}
                  </span>
                )}
                {exclusion.pid_unresolved_only > 0 && (
                  <span className="dist-preview-exclusion-item">
                    {t("distributionTarget.preview.excPid")}: {exclusion.pid_unresolved_only}
                  </span>
                )}
                {exclusion.unit_unresolved_only > 0 && (
                  <span className="dist-preview-exclusion-item">
                    {t("distributionTarget.preview.excUnit")}: {exclusion.unit_unresolved_only}
                  </span>
                )}
                {exclusion.both_unresolved > 0 && (
                  <span className="dist-preview-exclusion-item">
                    {t("distributionTarget.preview.excBoth")}: {exclusion.both_unresolved}
                  </span>
                )}
                {exclusion.price_unresolved > 0 && (
                  <span className="dist-preview-exclusion-item">
                    {t("distributionTarget.preview.excPrice")}: {exclusion.price_unresolved}
                  </span>
                )}
              </div>
            )}
          </div>
          <button
            type="button"
            className="dist-btn dist-btn--primary"
            onClick={() => setShowConfirm(true)}
            disabled={running || preview.output_count === 0}
            aria-label={t("distributionTarget.preview.runAllLabel")}
          >
            <INBOX_ACTION_ICONS.send size={16} aria-hidden="true" />
            {running ? t("distributionTarget.preview.running") : t("distributionTarget.preview.runAll")}
          </button>
        </div>

        {runResult && (
          <div className="dist-run-result">
            <div className="dist-run-result-title">{t("distributionTarget.preview.resultTitle")}</div>
            {runResult.results.map((r) => (
              <div key={r.target_id} className="dist-run-result-item dist-run-result-item--ok">
                <Check size={16} aria-hidden="true" />
                {r.target_name}: {r.rows_written.toLocaleString()}{t("distributionTarget.preview.rowsWritten")}
              </div>
            ))}
            {runResult.errors.map((e, i) => (
              <div key={i} className="dist-run-result-item dist-run-result-item--error">
                <Warning size={16} aria-hidden="true" />
                {e.target_name ?? e.target_id ?? t("common.error")}: {e.error}
              </div>
            ))}
          </div>
        )}

        {runError && (
          <p style={{ color: "var(--color-error)", fontSize: "var(--font-sm)" }}>
            {t("common.error")}: {runError}
          </p>
        )}
      </div>

      {/* 全件配信確認ダイアログ */}
      {showConfirm && (
        <div
          className="dist-dialog-backdrop"
          onClick={() => setShowConfirm(false)}
        >
          <div className="dist-dialog" onClick={(e) => e.stopPropagation()}>
            <h4>{t("distributionTarget.preview.confirmTitle")}</h4>
            <div className="dist-dialog-body">
              <p>
                {t("distributionTarget.preview.confirmBody", {
                  count: preview.output_count.toLocaleString(),
                })}
              </p>
            </div>
            <div className="dist-dialog-footer">
              <button
                type="button"
                className="dist-btn dist-btn--ghost"
                onClick={() => setShowConfirm(false)}
              >
                {t("common.cancel")}
              </button>
              <button
                type="button"
                className="dist-btn dist-btn--primary"
                onClick={handleRunAll}
              >
                {t("distributionTarget.preview.runAll")}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
