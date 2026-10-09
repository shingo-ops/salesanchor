// AY-2g: LINE解析と重複していたスーパー管理の旧ページ URL と、転送先の対応表。
// App.tsx の Route と legacyPageRedirects.test.tsx が、この配列だけを参照する。
export const LEGACY_SUPER_ADMIN_REDIRECTS = [
  { from: "/super-admin/tcg-product-master", to: "/super-admin/analysis-rules?section=product-master" },
  { from: "/super-admin/tcg-supplier-quality", to: "/super-admin/analysis-rules?section=accuracy-management" },
  { from: "/super-admin/supplier-master", to: "/super-admin/analysis-rules?section=supplier-master" },
] as const;
