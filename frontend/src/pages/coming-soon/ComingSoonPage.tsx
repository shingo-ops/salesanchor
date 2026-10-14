/**
 * 準備中ページ（GAS版互換のメニュー項目のうち、未実装のものに使用する汎用プレースホルダー）。
 *
 * 使い方:
 *   <Route path="/inventory" element={<ComingSoonPage title="在庫管理" description="..." />} />
 *
 * 変更履歴:
 *   2026-04-17: 初版作成
 *   2026-10-14: 第7便（PO 指摘）。戻るボタンを追加。/templates と /faq の2ルートから
 *     使われるが、戻る手段が無く行き止まりだった（スマホの「…」→テンプレートで開くと
 *     元の会話に戻れない）。直前の画面に戻る（navigate(-1)）ため、呼び出し元ルートを
 *     問わず汎用に機能する。
 */

import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { PAGE_ICONS, SCHEDULE_SETTINGS_ICONS } from "../../constants/icons";
import { Button } from "../../components/Button";
import { ICON } from "../../constants/iconSizes";

interface Props {
  title: string;
  description?: string;
}

export default function ComingSoonPage({ title, description }: Props) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const BackIcon = SCHEDULE_SETTINGS_ICONS.back;
  return (
    <div className="page">
      <div className="coming-soon-back-row">
        {/* 直前の画面に戻る。/templates・/faq のどちらから開かれても同じ挙動
            （PO 指摘・2026-10-14: 戻る手段が無い行き止まりだった） */}
        <Button variant="ghost" size="lg" onClick={() => navigate(-1)}>
          <BackIcon size={ICON.base} aria-hidden="true" />
          {t("common.back")}
        </Button>
      </div>
      <div className="coming-soon">
        <div className="coming-soon-icon" aria-hidden="true">
          <PAGE_ICONS.comingSoon size={64} />
        </div>
        {/* eslint-disable-next-line no-restricted-syntax */}
        <h2>{title}</h2>
        <p className="coming-soon-label">{t("comingSoon.label")}</p>
        {description && <p className="coming-soon-desc">{description}</p>}
        <p className="coming-soon-note">
          {t("comingSoon.note")}
        </p>
      </div>
    </div>
  );
}
