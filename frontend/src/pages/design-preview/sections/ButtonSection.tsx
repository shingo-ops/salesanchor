/**
 * §2 ボタン — 種類 × サイズ
 * §3 ボタン — 状態
 * §4 アイコンボタン — 実例
 */
import { Button } from "../../../components/Button";
import { X, PAGE_ICONS, INBOX_ACTION_ICONS, NAV_ICONS } from "../../../constants/icons";
import { ICON } from "../../../constants/iconSizes";
import { SectionHeader } from "./_shared";

const VARIANT_LABEL: Record<string, string> = {
  primary:   "主要 (primary)",
  secondary: "補助 (secondary)",
  ghost:     "控えめ (ghost)",
  danger:    "破壊的 (danger)",
  outline:   "枠線 (outline)",
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
        {(["primary", "secondary", "ghost", "danger", "outline"] as const).map((variant) => (
          <div key={variant} className="dp-row">
            <span className="dp-row-label">{VARIANT_LABEL[variant]}</span>
            <div className="dp-row-items">
              <Button variant={variant} size="sm">小 (sm)</Button>
              <Button variant={variant} size="md">中 (md)</Button>
              <Button variant={variant} size="lg">大 (lg)</Button>
            </div>
          </div>
        ))}
        {/* outline 透過デモ: 色背景の上でのみ意図が伝わる */}
        <div className="dp-row">
          <span className="dp-row-label">透過デモ</span>
          <div className="dp-row-items dp-colored-bg-demo">
            <Button variant="outline" size="sm">小 (sm)</Button>
            <Button variant="outline" size="md">中 (md)</Button>
            <Button variant="outline" size="lg">大 (lg)</Button>
          </div>
        </div>
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
          <span className="dp-row-label">アイコン sm</span>
          <div className="dp-row-items">
            <Button variant="ghost" size="sm" iconOnly aria-label="閉じる (sm)">
              <X size={ICON.md} aria-hidden="true" />
            </Button>
            <Button variant="primary" size="sm" iconOnly aria-label="追加 (sm)">
              <X size={ICON.md} aria-hidden="true" />
            </Button>
            <Button variant="ghost" size="sm" iconOnly aria-label="添付 (sm)" disabled>
              <INBOX_ACTION_ICONS.attach size={ICON.md} aria-hidden="true" />
            </Button>
          </div>
        </div>
        <div className="dp-row">
          <span className="dp-row-label">アイコン md</span>
          <div className="dp-row-items">
            <Button variant="ghost" size="md" iconOnly aria-label="閉じる (md)">
              <X size={ICON.base} aria-hidden="true" />
            </Button>
            <Button variant="ghost" size="md" iconOnly aria-label="設定 (md)">
              <PAGE_ICONS.settingsSolid size={ICON.base} aria-hidden="true" />
            </Button>
            <Button variant="danger" size="md" iconOnly aria-label="削除 (md)">
              <INBOX_ACTION_ICONS.delete size={ICON.base} aria-hidden="true" />
            </Button>
          </div>
        </div>
        <div className="dp-row">
          <span className="dp-row-label">アイコン lg</span>
          <div className="dp-row-items">
            <Button variant="ghost" size="lg" iconOnly aria-label="閉じる (lg)">
              <X size={ICON.lg} aria-hidden="true" />
            </Button>
            <Button variant="ghost" size="lg" iconOnly aria-label="設定 (lg)" disabled>
              <PAGE_ICONS.settingsSolid size={ICON.lg} aria-hidden="true" />
            </Button>
          </div>
        </div>
      </section>

      {/* §4: アイコンボタン実例 */}
      <section className="dp-section">
        <SectionHeader
          title="4. アイコンボタン — 実例 (usage patterns)"
          desc="実物基準: .icon-btn（36×36px）/ .send-attach-btn（28×28px）。ヘッダー・スレッド・インラインの3パターン。"
        />

        {/* 受信箱ヘッダー風 */}
        <div className="dp-row dp-row--top">
          <span className="dp-row-label">ヘッダー風</span>
          <div className="dp-icon-btn-bar">
            <Button variant="ghost" size="md" iconOnly aria-label="設定">
              <PAGE_ICONS.settingsSolid size={ICON.md} aria-hidden="true" />
            </Button>
            <Button variant="ghost" size="md" iconOnly aria-label="その他のアクション">
              <NAV_ICONS.more size={ICON.md} aria-hidden="true" />
            </Button>
            <Button variant="ghost" size="md" iconOnly aria-label="閉じる">
              <NAV_ICONS.close size={ICON.md} aria-hidden="true" />
            </Button>
          </div>
        </div>

        {/* スレッドヘッダー風 */}
        <div className="dp-row dp-row--top">
          <span className="dp-row-label">スレッド風</span>
          <div className="dp-icon-btn-bar">
            <Button variant="ghost" size="md" iconOnly aria-label="未読にする">
              <INBOX_ACTION_ICONS.markUnread size={ICON.base} aria-hidden="true" />
            </Button>
            <Button variant="ghost" size="md" iconOnly aria-label="アーカイブ">
              <INBOX_ACTION_ICONS.exclude size={ICON.base} aria-hidden="true" />
            </Button>
            <Button variant="danger" size="md" iconOnly aria-label="削除">
              <INBOX_ACTION_ICONS.delete size={ICON.base} aria-hidden="true" />
            </Button>
          </div>
        </div>

        {/* 送信エリア内インライン（28px小） */}
        <div className="dp-row dp-row--top">
          <span className="dp-row-label">インライン</span>
          <div className="dp-icon-btn-bar dp-icon-btn-bar--pill">
            <Button variant="ghost" size="sm" iconOnly aria-label="画像を添付">
              <INBOX_ACTION_ICONS.attach size={ICON.md} aria-hidden="true" />
            </Button>
            <Button variant="ghost" size="sm" iconOnly aria-label="翻訳">
              <INBOX_ACTION_ICONS.translate size={ICON.md} aria-hidden="true" />
            </Button>
            <Button variant="ghost" size="sm" iconOnly aria-label="送信">
              <INBOX_ACTION_ICONS.send size={ICON.md} aria-hidden="true" />
            </Button>
          </div>
        </div>
      </section>
    </>
  );
}
