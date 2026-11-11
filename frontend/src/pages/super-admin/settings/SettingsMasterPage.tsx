/**
 * /super-admin/settings/masters/:key — 全体設定の中のマスタ画面（LINE解析から移動した11件）。
 * key → Panel の対応表はこのファイルの1か所だけに持つ。項目の正本は settingsNav.ts。
 */
import type { ComponentType } from "react";
import { Navigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { PageLayout } from "../../../components/PageLayout";
import { ProductMasterPanel } from "../components/ProductMasterPanel";
import { ProductCategoriesMasterPanel } from "../components/ProductCategoriesMasterPanel";
import { ProductKindsMasterPanel } from "../components/ProductKindsMasterPanel";
import { TypeMasterPanel } from "../components/TypeMasterPanel";
import { ProductLinesMasterPanel } from "../components/ProductLinesMasterPanel";
import { ProductFormatsMasterPanel } from "../components/ProductFormatsMasterPanel";
import { SupplierMasterPanel } from "../components/SupplierMasterPanel";
import { NoteMasterPanel } from "../components/NoteMasterPanel";
import { QuantityUnitsMasterPanel } from "../components/QuantityUnitsMasterPanel";
import { ConditionDefsMasterPanel } from "../components/ConditionDefsMasterPanel";
import { WeightClassesMasterPanel } from "../components/WeightClassesMasterPanel";
import { SETTINGS_MASTER_ITEMS } from "./settingsNav";

const MASTER_PANELS: Record<string, ComponentType> = {
  "product-master": ProductMasterPanel,
  "product-categories-master": ProductCategoriesMasterPanel,
  "product-kinds-master": ProductKindsMasterPanel,
  "type-master": TypeMasterPanel,
  "product-lines-master": ProductLinesMasterPanel,
  "product-formats-master": ProductFormatsMasterPanel,
  "supplier-master": SupplierMasterPanel,
  "note-master": NoteMasterPanel,
  "quantity-units-master": QuantityUnitsMasterPanel,
  "condition-defs-master": ConditionDefsMasterPanel,
  "weight-classes-master": WeightClassesMasterPanel,
};

export default function SettingsMasterPage() {
  const { t } = useTranslation();
  const { key } = useParams<{ key: string }>();
  const item = SETTINGS_MASTER_ITEMS.find((i) => i.key === key);
  const Panel = key ? MASTER_PANELS[key] : undefined;
  if (!item || !Panel) return <Navigate to="/super-admin/settings" replace />;
  return (
    <PageLayout titleText={t(item.labelKey)}>
      <Panel />
    </PageLayout>
  );
}
