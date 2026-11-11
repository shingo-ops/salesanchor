// AY-2g/AY-2h/AY-2i: LINE解析と重複・廃止したスーパー管理の旧ページ URL と、転送先の対応表。
// 運営メニュー組み替え（利用者管理・全体設定）で、為替・閲覧者・ログイン許可待ち・テンプレートの旧道も足した。
// App.tsx の Route と legacyPageRedirects.test.tsx が、この配列だけを参照する。
import { settingsMasterPath } from "./settings/settingsNav";

export const LEGACY_SUPER_ADMIN_REDIRECTS = [
  { from: "/super-admin/tcg-product-master", to: settingsMasterPath("product-master") },
  { from: "/super-admin/tcg-supplier-quality", to: "/super-admin/analysis-rules?section=accuracy-management" },
  { from: "/super-admin/supplier-master", to: settingsMasterPath("supplier-master") },
  { from: "/super-admin/tcg-parallel-report", to: "/super-admin/analysis-rules" },
  { from: "/super-admin/tcg-sold-out", to: "/super-admin/analysis-rules?section=sold-out-results" },
  { from: "/super-admin/fx-rate", to: "/super-admin/settings/fx-rate" },
  { from: "/super-admin/viewers", to: "/super-admin/users/viewers" },
  { from: "/super-admin/login-requests", to: "/super-admin/users/login-requests" },
  { from: "/super-admin/viewer-templates", to: "/super-admin/users/viewer-templates" },
] as const;
