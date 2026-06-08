/**
 * デザインプレビュー セクションレジストリ
 *
 * 新しいコンポーネントを追加する手順:
 *   1. `sections/XxxSection.tsx` を新規作成
 *   2. ここに 1 エントリ追加（key / label / group / component）
 *   → サイドメニュー項目とルームが自動で増える（DesignPreviewPage が読み込む）
 */
import type { ComponentType } from "react";
import { TokenSection }     from "./TokenSection";
import { ButtonSection }    from "./ButtonSection";
import { CardSection }      from "./CardSection";
import { FormSection }      from "./FormSection";
import { BadgeSection }     from "./BadgeSection";
import { DataTableSection } from "./DataTableSection";
import { TabsSection }      from "./TabsSection";
import { SubMenuSection }   from "./SubMenuSection";

export interface SectionEntry {
  /** URL クエリパラメータ ?room=<key> に使用 */
  key: string;
  /** サイドメニューに表示する日本語ラベル */
  label: string;
  /** サイドメニューのグループ見出し */
  group: string;
  component: ComponentType;
}

export const SECTION_REGISTRY: SectionEntry[] = [
  { key: "tokens",   label: "トークン",     group: "基本",  component: TokenSection    },
  { key: "button",   label: "ボタン",       group: "基本",  component: ButtonSection   },
  { key: "card",     label: "カード",       group: "基本",  component: CardSection     },
  { key: "form",     label: "フォーム入力", group: "入力",  component: FormSection     },
  { key: "badge",    label: "バッジ",       group: "表示",  component: BadgeSection    },
  { key: "table",    label: "テーブル",     group: "表示",  component: DataTableSection },
  { key: "tabs",     label: "タブ",         group: "表示",  component: TabsSection     },
  { key: "submenu",  label: "サブメニュー", group: "ナビ",  component: SubMenuSection  },
];
