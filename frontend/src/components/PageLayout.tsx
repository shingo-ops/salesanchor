import { useTranslation } from "react-i18next";

interface PageLayoutBaseProps {
  subtitleKey?: string;
  /** タイトルのすぐ右に並べるコンテンツ（ナビゲーション等）*/
  headerLeft?: React.ReactNode;
  headerAction?: React.ReactNode;
  noScroll?: boolean;
  children: React.ReactNode;
}

/**
 * タイトルの渡し方は2択（排他・design: component-ssot/page-title/design.md D1）:
 * - 一覧系: navKey（サイドバーと同一の nav.* キー）
 * - 詳細系: titleText（データ名等の生文字列）
 * 見た目（字体・大きさ・色・配置）のpropsは提供しない＝金型（.text-page-title）が独占する。
 */
type PageLayoutProps =
  | (PageLayoutBaseProps & { navKey: `nav.${string}`; titleText?: never })
  | (PageLayoutBaseProps & { titleText: string; navKey?: never });

export function PageLayout({
  navKey,
  titleText,
  subtitleKey,
  headerLeft,
  headerAction,
  noScroll,
  children,
}: PageLayoutProps) {
  const { t } = useTranslation();
  return (
    <div className="page-layout">
      <header className="page-layout-header">
        <div className={`page-layout-title-row${subtitleKey ? " page-layout-title-row--has-subtitle" : ""}`}>
          <h2 className="text-page-title">{navKey ? t(navKey) : titleText}</h2>
          {headerLeft}
          {headerAction && (
            <div className="page-layout-header-right">{headerAction}</div>
          )}
        </div>
        {subtitleKey && (
          <p className="page-subtitle">{t(subtitleKey)}</p>
        )}
      </header>
      <div className={noScroll ? "page-layout-content page-layout-content--no-scroll" : "page-layout-content"}>{children}</div>
    </div>
  );
}
