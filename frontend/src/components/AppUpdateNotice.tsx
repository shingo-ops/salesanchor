/**
 * AppUpdateNotice — 新しい版が出ているときに画面の上へ出す小さな知らせ
 *
 * 既存の金型（Callout の info と Button）の組み合わせ。新しい見た目の決まりは足さない。
 * 閉じるボタンは置かない。「更新」を押したときだけ読み込み直す（書きかけの入力を勝手に消さない）。
 * 設計: docs/handoff/app-update-notice/design.md
 */
import { useTranslation } from "react-i18next";
import { useAppUpdateCheck } from "../hooks/useAppUpdateCheck";
import { Button } from "./Button";
import { Callout } from "./Callout";
import "./AppUpdateNotice.css";

export interface AppUpdateNoticeViewProps {
  message: string;
  reloadLabel: string;
  onReload: () => void;
}

/** 見た目だけ（版の確認は持たない）。Storybook と AppUpdateNotice が使う */
export function AppUpdateNoticeView({ message, reloadLabel, onReload }: AppUpdateNoticeViewProps) {
  return (
    <div className="app-update-notice" data-testid="app-update-notice">
      <Callout variant="info" title={message}>
        <Button variant="primary" size="md" onClick={onReload}>
          {reloadLabel}
        </Button>
      </Callout>
    </div>
  );
}

export function AppUpdateNotice() {
  const { t } = useTranslation();
  const available = useAppUpdateCheck();
  if (!available) return null;
  return (
    <AppUpdateNoticeView
      message={t("appUpdate.message")}
      reloadLabel={t("appUpdate.reload")}
      onReload={() => window.location.reload()}
    />
  );
}
