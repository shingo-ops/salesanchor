/**
 * usePageTitle — 現在のルートに対応するページ見出しを返す hook。
 *
 * ROUTE_TITLE_KEYS (src/config/routeTitles.ts) を Single Source of Truth として参照し、
 * サイドバーラベルと完全に同一の nav.* i18n キーで見出しを生成する。
 *
 * 注意:
 *   - 詳細ページ (/companies/:id など) では空文字を返す。
 *     詳細ページは PageLayout の titleText にデータ名を渡すこと（生の h1/h2 直書きは禁止。
 *     design: docs/specs/design-system/component-ssot/page-title/design.md D1）。
 */
import { useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ROUTE_TITLE_KEYS } from "../config/routeTitles";

export function usePageTitle(): string {
  const { pathname } = useLocation();
  const { t } = useTranslation();
  const key = ROUTE_TITLE_KEYS[pathname] ?? "";
  return key ? t(key) : "";
}
