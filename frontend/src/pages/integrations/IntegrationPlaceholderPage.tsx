/**
 * API 連携プレースホルダーページ
 *
 * 管理センター > API 連携 配下の各サービス（Google Drive / FedEx / DHL /
 * UPS / ヤマト / 佐川）の暫定画面。中央に「現在作成中」とだけ表示する白紙。
 * 各サービスの実装が決まり次第、個別ページに差し替える。
 *
 * 変更履歴:
 *   2026-06-05: 初版作成（API 連携メニュー追加に伴うプレースホルダー）
 */

import { useTranslation } from "react-i18next";

export default function IntegrationPlaceholderPage() {
  const { t } = useTranslation();
  return (
    <div className="integration-placeholder">
      <p>{t("apiIntegration.inProgress")}</p>
    </div>
  );
}
