/**
 * AppUpdateNotice — 新しい版が出ているときに画面の上へ出す小さな知らせ
 *
 * 既存の知らせ（Toast の .sa-toast）と同じ形の白いカード＋金型 Button（ghost）の組み合わせ。新しい見た目の決まりは足さない。
 * 閉じるボタンは置かない。「更新」を押したときだけ読み込み直す（書きかけの入力を勝手に消さない）。
 * 設計: docs/handoff/app-update-notice/design.md
 */
import { useTranslation } from "react-i18next";
import { useAppUpdateCheck } from "../hooks/useAppUpdateCheck";
import { SCHEDULE_SETTINGS_ICONS } from "../constants/icons";
import { Button } from "./Button";
import "./AppUpdateNotice.css";

export interface AppUpdateNoticeViewProps {
  message: string;
  reloadLabel: string;
  onReload: () => void;
}

const RefreshIcon = SCHEDULE_SETTINGS_ICONS.sync;

/** 見た目だけ（版の確認は持たない）。Storybook と AppUpdateNotice が使う */
export function AppUpdateNoticeView({ message, reloadLabel, onReload }: AppUpdateNoticeViewProps) {
  return (
    <div className="app-update-notice" data-testid="app-update-notice" role="status" aria-live="polite">
      <span className="app-update-notice__icon" aria-hidden="true">
        <RefreshIcon className="app-update-notice__icon-svg" aria-hidden="true" />
      </span>
      <span className="app-update-notice__message">{message}</span>
      <Button variant="ghost" size="md" onClick={onReload}>
        {reloadLabel}
      </Button>
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
