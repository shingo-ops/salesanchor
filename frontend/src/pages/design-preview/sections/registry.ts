/**
 * デザインプレビュー セクションレジストリ
 *
 * 新しいコンポーネントを追加する手順:
 *   1. `sections/XxxSection.tsx` を新規作成
 *   2. ここに 1 行 import + 1 行 export を追加
 *   既存のセクションファイルは変更不要 → マージ衝突しない
 */
import { TokenSection }     from "./TokenSection";
import { ButtonSection }    from "./ButtonSection";
import { CardSection }      from "./CardSection";
import { FormSection }      from "./FormSection";
import { BadgeSection }     from "./BadgeSection";
import { DataTableSection } from "./DataTableSection";
import { TabsSection }     from "./TabsSection";

export const SECTION_REGISTRY = [
  TokenSection,
  ButtonSection,
  CardSection,
  FormSection,
  BadgeSection,
  DataTableSection,
  TabsSection,
] as const;
