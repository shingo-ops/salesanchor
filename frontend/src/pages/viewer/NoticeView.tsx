/** ④ 案内（準備中・停止中・期限切れ・読み込み失敗） */
import { useTranslation } from "react-i18next";
import type { TFunction } from "i18next";
import { Button } from "../../components/Button";
import { EmptyState } from "../../components/EmptyState";
import type { ViewerNoticeKind } from "./types";

interface NoticeViewProps {
  kind: ViewerNoticeKind;
  onLogout: () => void;
}

function noticeText(t: TFunction, kind: ViewerNoticeKind): { title: string; description: string } {
  switch (kind) {
    case "preparing":
      return { title: t("viewer.notice.preparing.title"), description: t("viewer.notice.preparing.description") };
    case "suspended":
      return { title: t("viewer.notice.suspended.title"), description: t("viewer.notice.suspended.description") };
    case "expired":
      return { title: t("viewer.notice.expired.title"), description: t("viewer.notice.expired.description") };
    default:
      return { title: t("viewer.notice.error.title"), description: t("viewer.notice.error.description") };
  }
}

export function NoticeView({ kind, onLogout }: NoticeViewProps) {
  const { t } = useTranslation();
  const text = noticeText(t, kind);
  return (
    <div className="viewer-center" data-testid={`viewer-notice-${kind}`}>
      <EmptyState
        title={text.title}
        description={text.description}
        action={
          <Button variant="secondary" onClick={onLogout} data-testid="viewer-notice-logout">
            {t("viewer.logout")}
          </Button>
        }
      />
    </div>
  );
}
