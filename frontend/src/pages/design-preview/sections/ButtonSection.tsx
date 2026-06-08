/**
 * §2 ボタン — 種類 × サイズ
 * §3 ボタン — 状態
 */
import { Button } from "../../../components/Button";
import { X, PAGE_ICONS } from "../../../constants/icons";
import { SectionHeader } from "./_shared";

const VARIANT_LABEL: Record<string, string> = {
  primary:   "主要 (primary)",
  secondary: "補助 (secondary)",
  ghost:     "控えめ (ghost)",
  danger:    "破壊的 (danger)",
};

export function ButtonSection() {
  return (
    <>
      {/* §2: 種類 × サイズ */}
      <section className="dp-section">
        <SectionHeader
          title="2. ボタン — 種類 × サイズ (variant x size)"
          desc="主要＝その画面で一番押してほしい操作 / 補助＝その次 / 控えめ＝軽い操作 / 破壊的＝削除など取り消せない操作"
        />
        {(["primary", "secondary", "ghost", "danger"] as const).map((variant) => (
          <div key={variant} className="dp-row">
            <span className="dp-row-label">{VARIANT_LABEL[variant]}</span>
            <div className="dp-row-items">
              <Button variant={variant} size="sm">小 (sm)</Button>
              <Button variant={variant} size="md">中 (md)</Button>
              <Button variant={variant} size="lg">大 (lg)</Button>
            </div>
          </div>
        ))}
      </section>

      {/* §3: 状態 */}
      <section className="dp-section">
        <SectionHeader
          title="3. ボタン — 状態 (states)"
          desc="無効＝押せない状態（薄く表示）。読み込み中＝処理中のスピナー表示。横幅いっぱい＝コンテナ全幅に伸縮。"
        />
        <div className="dp-row">
          <span className="dp-row-label">通常</span>
          <div className="dp-row-items">
            <Button variant="primary">通常</Button>
          </div>
        </div>
        <div className="dp-row">
          <span className="dp-row-label">無効 (disabled)</span>
          <div className="dp-row-items">
            <Button variant="primary" disabled>無効</Button>
            <Button variant="secondary" disabled>無効</Button>
            <Button variant="ghost" disabled>無効</Button>
            <Button variant="danger" disabled>無効</Button>
          </div>
        </div>
        <div className="dp-row">
          <span className="dp-row-label">読み込み中 (loading)</span>
          <div className="dp-row-items">
            <Button variant="primary" loading>保存中...</Button>
            <Button variant="secondary" loading>読み込み中</Button>
          </div>
        </div>
        <div className="dp-row">
          <span className="dp-row-label">横幅いっぱい (fullWidth)</span>
          <div className="dp-row-items dp-row-items--full">
            <Button variant="primary" fullWidth>横幅いっぱいのボタン</Button>
          </div>
        </div>
        <div className="dp-row">
          <span className="dp-row-label">アイコンのみ (icon only)</span>
          <div className="dp-row-items">
            <Button variant="primary" iconOnly aria-label="追加">+</Button>
            <Button variant="ghost" iconOnly aria-label="閉じる">
              <X size={16} aria-hidden="true" />
            </Button>
            <Button variant="secondary" iconOnly aria-label="設定">
              <PAGE_ICONS.settingsSolid size={16} aria-hidden="true" />
            </Button>
          </div>
        </div>
      </section>
    </>
  );
}
