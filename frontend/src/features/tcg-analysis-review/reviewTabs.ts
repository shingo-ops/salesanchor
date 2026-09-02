export type ReviewTabId = 'ALL' | 'NEEDS_REVIEW' | 'PRODUCT_MASTER_UNREGISTERED' | 'SUPPLIER_UNREGISTERED' | 'PRODUCT_ID_UNRESOLVED' | 'NORMAL_COMPLETED';
export type ReviewTab = { id: ReviewTabId; label: string; tone: 'neutral' | 'warning' | 'danger'; enabled: boolean; matches: (issues: string[]) => boolean };
const has = (issues: string[], issue: string) => issues.includes(issue);
export const REVIEW_TABS: ReviewTab[] = [
  { id: 'ALL', label: 'すべて', tone: 'neutral', enabled: true, matches: () => true },
  { id: 'NORMAL_COMPLETED', label: '正常完了', tone: 'neutral', enabled: false, matches: () => false },
  { id: 'NEEDS_REVIEW', label: '要確認', tone: 'warning', enabled: true, matches: (issues) => has(issues, 'PRODUCT_ID_UNRESOLVED') || has(issues, 'UNIT_UNRESOLVED') || has(issues, 'EXCLUDED') },
  { id: 'PRODUCT_MASTER_UNREGISTERED', label: '商品マスタ未登録', tone: 'danger', enabled: true, matches: (issues) => has(issues, 'PRODUCT_MASTER_UNREGISTERED') },
  { id: 'SUPPLIER_UNREGISTERED', label: '仕入元未登録', tone: 'warning', enabled: true, matches: (issues) => has(issues, 'SUPPLIER_UNREGISTERED') },
  { id: 'PRODUCT_ID_UNRESOLVED', label: '商品ID未解決', tone: 'danger', enabled: true, matches: (issues) => has(issues, 'PRODUCT_ID_UNRESOLVED') },
];
