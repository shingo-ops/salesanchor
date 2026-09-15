/**
 * DistributionWorkspace — 配信対象のプレビュー、配信先一覧、登録フォームを共有する内容領域。
 *
 * PageLayout と権限判定は呼び出しページが担う。認可済みの親だけがマウントすることで、
 * 初回の配信先・プレビュー取得もその親でのみ実行される。
 */
import { forwardRef, useCallback, useEffect, useImperativeHandle, useState } from "react";
import { useTranslation } from "react-i18next";
import { NAV_ICONS } from "../../constants/icons";
import { DistributionPreview } from "./DistributionPreview";
import { DistributionTargetList } from "./DistributionTargetList";
import { DistributionTargetForm } from "./DistributionTargetForm";
import { listTargets } from "./distributionApi";
import type { DistributionTarget } from "./distributionApi";
import "./distribution.css";

export interface DistributionWorkspaceHandle {
  openNewTargetForm: () => void;
}

interface DistributionWorkspaceProps {
  /** 総合ページでは配信先の新規登録を内容領域から開始できる。 */
  showNewTargetAction?: boolean;
}

export const DistributionWorkspace = forwardRef<DistributionWorkspaceHandle, DistributionWorkspaceProps>(
  function DistributionWorkspace({ showNewTargetAction = true }, ref) {
    const { t } = useTranslation();
    const [targets, setTargets] = useState<DistributionTarget[]>([]);
    const [loadError, setLoadError] = useState("");
    const [showNewForm, setShowNewForm] = useState(false);

    const loadTargets = useCallback(() => {
      setLoadError("");
      listTargets()
        .then(setTargets)
        .catch((e: unknown) => setLoadError(e instanceof Error ? e.message : String(e)));
    }, []);

    useEffect(() => {
      loadTargets();
    }, [loadTargets]);

    useImperativeHandle(ref, () => ({
      openNewTargetForm: () => setShowNewForm(true),
    }), []);

    return (
      <>
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          {showNewTargetAction && (
            <div>
              <button
                type="button"
                className="dist-btn dist-btn--primary"
                onClick={() => setShowNewForm(true)}
                aria-label={t("distributionTarget.page.newBtn")}
              >
                <NAV_ICONS.add size={16} aria-hidden="true" />
                {t("distributionTarget.page.newBtn")}
              </button>
            </div>
          )}

          <DistributionPreview onRefreshTargets={loadTargets} />

          <p style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>
            {t("pmgWorkflow.distributionCurrentResponse")}
          </p>

          <p style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>
            {t("pmgWorkflow.distributionLatestSavedRecord")}
          </p>
          {loadError ? (
            <p style={{ color: "var(--color-error)", fontSize: "var(--font-sm)" }}>
              {t("common.fetchError")}: {loadError}
            </p>
          ) : (
            <DistributionTargetList targets={targets} onRefresh={loadTargets} />
          )}
        </div>

        {showNewForm && (
          <DistributionTargetForm
            target={null}
            onClose={() => setShowNewForm(false)}
            onSaved={() => {
              setShowNewForm(false);
              loadTargets();
            }}
          />
        )}
      </>
    );
  },
);
