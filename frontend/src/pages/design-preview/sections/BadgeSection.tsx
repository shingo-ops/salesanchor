/**
 * §8 バッジ・ステータス (Badge)
 * variant 5 × appearance 2 × size 2。ドット付き・アイコン付きの例も確認できる。
 */
import { Badge } from "../../../components/Badge";
import { X, PAGE_ICONS } from "../../../constants/icons";
import { SectionHeader } from "./_shared";

export function BadgeSection() {
  return (
    <section className="dp-section">
      <SectionHeader
        title="8. バッジ・ステータス (Badge)"
        desc="variant 5 × appearance 2 × size 2。ドット付きの例も確認できる。"
      />

      {/* variant × appearance */}
      {(["neutral", "info", "success", "warning", "danger"] as const).map((variant) => (
        <div key={variant} className="dp-row">
          <span className="dp-row-label">{variant}</span>
          <div className="dp-row-items">
            <Badge variant={variant} appearance="soft"  size="sm">{variant} / soft / sm</Badge>
            <Badge variant={variant} appearance="soft"  size="md">{variant} / soft / md</Badge>
            <Badge variant={variant} appearance="solid" size="sm">{variant} / solid / sm</Badge>
            <Badge variant={variant} appearance="solid" size="md">{variant} / solid / md</Badge>
          </div>
        </div>
      ))}

      {/* ドット付き */}
      <div className="dp-row">
        <span className="dp-row-label">dot</span>
        <div className="dp-row-items">
          <Badge variant="success" dot>対応済み</Badge>
          <Badge variant="warning" dot>保留中</Badge>
          <Badge variant="danger"  dot>要対応</Badge>
          <Badge variant="info"    dot>処理中</Badge>
          <Badge variant="neutral" dot>未分類</Badge>
        </div>
      </div>

      {/* アイコン付き */}
      <div className="dp-row">
        <span className="dp-row-label">icon</span>
        <div className="dp-row-items">
          <Badge variant="success" icon={<PAGE_ICONS.settingsSolid size={10} />}>設定済み</Badge>
          <Badge variant="danger"  icon={<X size={10} />}>エラー</Badge>
        </div>
      </div>
    </section>
  );
}
