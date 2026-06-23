/**
 * 配送会社セットアップガイドページ（汎用・:carrier で切り替わる）
 *
 * - fedex → FedexEtdSetupGuide（既存ウィザード流用）
 * - 未対応 carrier → ComingSoonPage で「準備中」表示
 *
 * 新しい配送会社の追加 = GUIDE_MAP に定義を 1 件足すだけ。
 * ルート: /management-center/integrations/:carrier/setup-guide
 */

import { useNavigate, useParams } from "react-router-dom";
import { PageLayout } from "../../components/PageLayout";
import { FedexEtdSetupGuide } from "./FedexEtdSetupGuide";
import ComingSoonPage from "../coming-soon/ComingSoonPage";

type Carrier = "fedex" | "dhl" | "ups";

/** carrier → ガイド定義マップ（fedex のみ実装済み） */
const GUIDE_MAP: Partial<Record<string, true>> = {
  fedex: true,
};

const NAV_KEY: Record<string, `nav.${string}`> = {
  fedex: "nav.integrationFedex",
  dhl:   "nav.integrationDhl",
  ups:   "nav.integrationUps",
};

export default function CarrierSetupGuidePage() {
  const { carrier = "" } = useParams<{ carrier: Carrier }>();
  const navigate = useNavigate();

  if (!GUIDE_MAP[carrier]) {
    return <ComingSoonPage title={carrier.toUpperCase()} />;
  }

  return (
    <PageLayout
      navKey={NAV_KEY[carrier] ?? "nav.integrationFedex"}
      subtitleKey="carrierIntegration.subtitle"
    >
      <FedexEtdSetupGuide
        onOpenCredentialsTab={() =>
          navigate(`/management-center/integrations/${carrier}`)
        }
      />
    </PageLayout>
  );
}
