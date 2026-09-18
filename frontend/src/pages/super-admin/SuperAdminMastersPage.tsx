/**
 * /super-admin/masters — マスタ管理ページ（商品マスタ + 仕入元マスタ タブ）。
 *
 * Sprint 2: SaaS管理者向けに商品マスタと仕入元マスタを1ページで管理する。
 * 仕入元マスタは LINE 解析用（tenant_id IS NULL）のみを表示・管理する。
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import { Tabs } from "../../components/Tabs";
import ProductMastersTab from "./ProductMastersTab";
import SuppliersAdminTab from "./SuppliersAdminTab";

type TabKey = "products" | "suppliers";

export default function SuperAdminMastersPage() {
  const { t } = useTranslation();
  const { isSuperAdmin } = useSuperAdmin();
  const [activeTab, setActiveTab] = useState<TabKey>("products");

  if (!isSuperAdmin) {
    return (
      <div className="page-container">
        <p className="error-message">{t("superAdmin.accessDenied")}</p>
      </div>
    );
  }

  const tabItems = [
    { key: "products" as TabKey, label: t("superAdmin.masters.productTab") },
    { key: "suppliers" as TabKey, label: t("superAdmin.masters.supplierTab") },
  ];

  return (
    <div className="page-container">
      <h1 className="page-title">{t("superAdmin.masters.title")}</h1>
      <Tabs
        items={tabItems}
        activeKey={activeTab}
        onChange={setActiveTab}
        variant="underline"
        size="md"
      />
      <div style={{ marginTop: "var(--space-4)" }}>
        {activeTab === "products" && <ProductMastersTab />}
        {activeTab === "suppliers" && <SuppliersAdminTab />}
      </div>
    </div>
  );
}
