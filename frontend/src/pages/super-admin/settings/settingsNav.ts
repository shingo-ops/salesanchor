// 全体設定（/super-admin/settings）の項目の正本。
// App.tsx の Route・SettingsHubPage の小さなメニュー・LINE解析の転送・転送表・取込画面の戻り先が、ここを読む。
// 項目を足すときは、ここに1行と SettingsMasterPage の Panel の表に1行。

export interface SettingsNavItem {
  key: string;
  labelKey: string;
}

/** 金額の設定の組。 */
export const SETTINGS_MONEY_ITEMS: readonly SettingsNavItem[] = [
  { key: "fx-rate", labelKey: "nav.superAdminFxRate" },
  { key: "tax-rates", labelKey: "nav.superAdminTaxRates" },
  { key: "sa-products", labelKey: "nav.superAdminSaProducts" },
];

/** マスタ管理の組（LINE解析にあった11件。並びも同じ）。 */
export const SETTINGS_MASTER_ITEMS: readonly SettingsNavItem[] = [
  { key: "product-master", labelKey: "analysisRules.sidebar.productMaster" },
  { key: "product-categories-master", labelKey: "analysisRules.sidebar.productCategoriesMaster" },
  { key: "product-kinds-master", labelKey: "analysisRules.sidebar.productKindsMaster" },
  { key: "type-master", labelKey: "analysisRules.sidebar.typeMaster" },
  { key: "product-lines-master", labelKey: "analysisRules.sidebar.productLinesMaster" },
  { key: "product-formats-master", labelKey: "analysisRules.sidebar.productFormatsMaster" },
  { key: "supplier-master", labelKey: "analysisRules.sidebar.supplierMaster" },
  { key: "note-master", labelKey: "analysisRules.sidebar.noteMaster" },
  { key: "quantity-units-master", labelKey: "analysisRules.sidebar.quantityUnitsMaster" },
  { key: "condition-defs-master", labelKey: "analysisRules.sidebar.conditionDefsMaster" },
  { key: "weight-classes-master", labelKey: "analysisRules.sidebar.weightClassesMaster" },
];

export function settingsMasterPath(key: string): string {
  return `/super-admin/settings/masters/${key}`;
}

export function isSettingsMasterKey(key: string | null | undefined): key is string {
  return !!key && SETTINGS_MASTER_ITEMS.some((i) => i.key === key);
}
