/**
 * DistributionTargetList — 配信先一覧テーブル + 個別配信実行
 *
 * 表示項目:
 *   クライアント名 / シートID（省略）/ タブ名 / 有効 / 最終配信日時 / 件数 / 最終結果 / 操作
 *
 * 操作:
 *   編集: DistributionTargetForm ドロワーを開く
 *   無効化: DELETE API（論理削除）→ is_active = false
 *   有効化: PUT API（is_active: true） ← 無効行の編集で対応
 *   配信: POST /tcg/distribution/run/{target_id}（確認ダイアログ付き）
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { SCHEDULE_POPOVER_ICONS, INBOX_ACTION_ICONS, Check, Warning } from "../../constants/icons";
import type { DistributionTarget, RunResult } from "./distributionApi";
import { deleteTarget, runDistributionTarget } from "./distributionApi";
import { DistributionTargetForm } from "./DistributionTargetForm";

interface Props {
  targets: DistributionTarget[];
  onRefresh: () => void;
}

interface ConfirmState {
  type: "disable" | "run";
  target: DistributionTarget;
}

export function DistributionTargetList({ targets, onRefresh }: Props) {
  const { t } = useTranslation();
  const [editTarget, setEditTarget] = useState<DistributionTarget | null | false>(false);
  const [confirm, setConfirm] = useState<ConfirmState | null>(null);
  const [running, setRunning] = useState<string | null>(null);
  const [runResults, setRunResults] = useState<Record<string, RunResult>>({});
  const [actionError, setActionError] = useState("");

  const handleDisable = async (target: DistributionTarget) => {
    setConfirm(null);
    setActionError("");
    try {
      await deleteTarget(target.id);
      onRefresh();
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : String(e));
    }
  };

  const handleRun = async (target: DistributionTarget) => {
    setConfirm(null);
    setRunning(target.id);
    setActionError("");
    try {
      const result = await runDistributionTarget(target.id);
      setRunResults((prev) => ({ ...prev, [target.id]: result }));
      onRefresh();
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(null);
    }
  };

  if (targets.length === 0) {
    return (
      <div className="dist-empty">
        {t("distributionTarget.list.empty")}
      </div>
    );
  }

  return (
    <>
      {actionError && (
        <p style={{ color: "var(--color-error)", fontSize: "var(--font-sm)", marginBottom: "var(--space-2)" }}>
          {t("common.error")}: {actionError}
        </p>
      )}

      <div className="dist-table-wrap">
        <table className="dist-table">
          <thead>
            <tr>
              <th>{t("distributionTarget.list.colName")}</th>
              <th>{t("distributionTarget.list.colSheetId")}</th>
              <th>{t("distributionTarget.list.colSheetName")}</th>
              <th>{t("distributionTarget.list.colStatus")}</th>
              <th>{t("distributionTarget.list.colLastAt")}</th>
              <th>{t("distributionTarget.list.colLastCount")}</th>
              <th>{t("distributionTarget.list.colLastResult")}</th>
              <th>{t("common.actions")}</th>
            </tr>
          </thead>
          <tbody>
            {targets.map((target) => {
              const runResult = runResults[target.id];
              return (
                <tr key={target.id} className={target.is_active ? "" : "dist-row--inactive"}>
                  <td>{target.name}</td>
                  <td>
                    <span className="dist-sheet-id" title={target.spreadsheet_id}>
                      {target.spreadsheet_id.slice(0, 12)}…
                    </span>
                  </td>
                  <td>{target.sheet_name}</td>
                  <td>
                    <span className={`dist-badge ${target.is_active ? "dist-badge--active" : "dist-badge--inactive"}`}>
                      {target.is_active
                        ? t("distributionTarget.list.statusActive")
                        : t("distributionTarget.list.statusInactive")}
                    </span>
                  </td>
                  <td style={{ fontSize: "var(--font-xs)", color: "var(--text-secondary)", whiteSpace: "nowrap" }}>
                    {target.last_distributed_at
                      ? new Date(target.last_distributed_at).toLocaleString("ja-JP", {
                          month: "2-digit",
                          day: "2-digit",
                          hour: "2-digit",
                          minute: "2-digit",
                        })
                      : "—"}
                  </td>
                  <td style={{ fontSize: "var(--font-sm)", textAlign: "right" }}>
                    {target.last_distributed_count !== null
                      ? target.last_distributed_count.toLocaleString()
                      : "—"}
                  </td>
                  <td>
                    {runResult ? (
                      <>
                        {runResult.results.map((r) => (
                          <div key={r.target_id} className="dist-result--ok">
                            <Check size={12} aria-hidden="true" />
                            {" "}{r.rows_written.toLocaleString()}{t("distributionTarget.preview.rowsWritten")}
                          </div>
                        ))}
                        {runResult.errors.map((e, i) => (
                          <div key={i} className="dist-result--error" title={e.error}>
                            {e.error}
                          </div>
                        ))}
                      </>
                    ) : target.last_result ? (
                      target.last_result === "ok" ? (
                        <span className="dist-result--ok">ok</span>
                      ) : (
                        <span className="dist-result--error" title={target.last_result}>
                          {target.last_result}
                        </span>
                      )
                    ) : (
                      <span style={{ color: "var(--text-secondary)", fontSize: "var(--font-xs)" }}>—</span>
                    )}
                  </td>
                  <td>
                    <div className="dist-actions">
                      <button
                        type="button"
                        className="dist-btn dist-btn--ghost"
                        onClick={() => setEditTarget(target)}
                        title={t("common.edit")}
                        aria-label={`${t("common.edit")}: ${target.name}`}
                      >
                        <SCHEDULE_POPOVER_ICONS.edit size={14} aria-hidden="true" />
                        {t("common.edit")}
                      </button>

                      {target.is_active && (
                        <>
                          <button
                            type="button"
                            className="dist-btn dist-btn--primary"
                            onClick={() => setConfirm({ type: "run", target })}
                            disabled={running === target.id}
                            title={t("distributionTarget.list.runBtn")}
                            aria-label={`${t("distributionTarget.list.runBtn")}: ${target.name}`}
                          >
                            <INBOX_ACTION_ICONS.send size={14} aria-hidden="true" />
                            {running === target.id
                              ? t("distributionTarget.preview.running")
                              : t("distributionTarget.list.runBtn")}
                          </button>

                          <button
                            type="button"
                            className="dist-btn dist-btn--danger"
                            onClick={() => setConfirm({ type: "disable", target })}
                            title={t("distributionTarget.list.disableBtn")}
                            aria-label={`${t("distributionTarget.list.disableBtn")}: ${target.name}`}
                          >
                            {t("distributionTarget.list.disableBtn")}
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* 確認ダイアログ */}
      {confirm && (
        <div
          className="dist-dialog-backdrop"
          onClick={() => setConfirm(null)}
        >
          <div className="dist-dialog" onClick={(e) => e.stopPropagation()}>
            {confirm.type === "run" ? (
              <>
                <h4>{t("distributionTarget.list.confirmRunTitle")}</h4>
                <div className="dist-dialog-body">
                  <p>
                    {t("distributionTarget.list.confirmRunBody", {
                      name: confirm.target.name,
                    })}
                  </p>
                </div>
                <div className="dist-dialog-footer">
                  <button
                    type="button"
                    className="dist-btn dist-btn--ghost"
                    onClick={() => setConfirm(null)}
                  >
                    {t("common.cancel")}
                  </button>
                  <button
                    type="button"
                    className="dist-btn dist-btn--primary"
                    onClick={() => handleRun(confirm.target)}
                  >
                    {t("distributionTarget.list.runBtn")}
                  </button>
                </div>
              </>
            ) : (
              <>
                <h4>{t("distributionTarget.list.confirmDisableTitle")}</h4>
                <div className="dist-dialog-body">
                  <p>
                    {t("distributionTarget.list.confirmDisableBody", {
                      name: confirm.target.name,
                    })}
                  </p>
                </div>
                <div className="dist-dialog-footer">
                  <button
                    type="button"
                    className="dist-btn dist-btn--ghost"
                    onClick={() => setConfirm(null)}
                  >
                    {t("common.cancel")}
                  </button>
                  <button
                    type="button"
                    className="dist-btn dist-btn--danger"
                    onClick={() => handleDisable(confirm.target)}
                  >
                    {t("distributionTarget.list.disableBtn")}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* 編集ドロワー */}
      {editTarget !== false && (
        <DistributionTargetForm
          target={editTarget}
          onClose={() => setEditTarget(false)}
          onSaved={() => {
            setEditTarget(false);
            onRefresh();
          }}
        />
      )}
    </>
  );
}
