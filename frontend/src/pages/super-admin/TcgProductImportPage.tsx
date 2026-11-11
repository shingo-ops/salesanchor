import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { PageLayout } from "../../components/PageLayout";
import { HeaderButton } from "../../components/HeaderButton";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import { TcgProductImportPanel } from "../../features/tcg-product-import/TcgProductImportPanel";
import { LoadingBlock } from "../../components/loading";
import { settingsMasterPath } from "./settings/settingsNav";

export default function TcgProductImportPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { isSuperAdmin, loading } = useSuperAdmin();
  return <PageLayout titleText={t("productCsv.importTitle")}>
    {loading ? <LoadingBlock /> : !isSuperAdmin ? <p role="alert">{t("productCsv.denied")}</p> : <TcgProductImportPanel onDone={() => navigate(settingsMasterPath("product-master"))} />}
    {!loading && !isSuperAdmin && <HeaderButton variant="secondary" onClick={() => navigate(settingsMasterPath("product-master"))}>{t("productCsv.back")}</HeaderButton>}
  </PageLayout>;
}
