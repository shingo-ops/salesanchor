/**
 * DesignPreviewPage — コンポーネント標準 目視確認ページ（Task 1C / 開発環境専用）
 *
 * アクセス: /design-preview（import.meta.env.DEV のみ App.tsx でルート登録）
 *
 * 確認内容:
 *   - Button 全バリアント × 全サイズ × 各状態
 *   - Card 全バリアント × 全密度
 *   - 幅セレクタ（モバイル 375px / タブレット 768px / PC 全幅）で 3 バンド確認
 */

import { useState } from "react";
import { PageLayout } from "../../components/PageLayout";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import "./DesignPreviewPage.css";

// ── 幅セレクタの選択肢 ──────────────────────────────────────────
const WIDTH_BANDS = [
  { label: "Mobile (375px)",   value: 375  },
  { label: "Tablet (768px)",   value: 768  },
  { label: "PC (full width)",  value: null },
] as const;

type BandValue = 375 | 768 | null;

// ── セクションヘッダー ──────────────────────────────────────────
function SectionHeader({ title }: { title: string }) {
  return <h3 className="dp-section-title">{title}</h3>;
}

// ── トークン値サマリ ──────────────────────────────────────────────
const TOKEN_SUMMARY = [
  { token: "--comp-btn-radius",           desc: "ボタン角丸",               expected: "6px (radius-md)" },
  { token: "--comp-card-radius",          desc: "カード角丸",               expected: "8px (radius-lg)" },
  { token: "--comp-card-padding",         desc: "カード余白 (PC/tab)",      expected: "24px (space-6)"  },
  { token: "--comp-card-padding-compact", desc: "カード余白 (mobile/compact)", expected: "16px (space-4)" },
  { token: "--comp-card-gap",             desc: "カード間ギャップ",          expected: "24px (space-6)"  },
];

export default function DesignPreviewPage() {
  const [bandWidth, setBandWidth] = useState<BandValue>(null);

  return (
    <PageLayout navKey="nav.designPreview" subtitleKey="designPreview.subtitle">
      {/* ── 幅セレクタ ── */}
      <div className="dp-band-selector">
        <span className="dp-band-label">Preview width:</span>
        {WIDTH_BANDS.map((b) => (
          <button
            key={String(b.value)}
            className={`dp-band-btn${bandWidth === b.value ? " dp-band-btn--active" : ""}`}
            onClick={() => setBandWidth(b.value as BandValue)}
          >
            {b.label}
          </button>
        ))}
      </div>

      {/* ── プレビュー枠 ── */}
      <div
        className="dp-preview-frame"
        style={bandWidth != null ? { maxWidth: bandWidth, margin: "0 auto" } : undefined}
      >

        {/* ════════════════════════════════════════
            トークン確認
            ════════════════════════════════════════ */}
        <section className="dp-section">
          <SectionHeader title="1. 標準トークン確認" />
          <table className="dp-token-table">
            <thead>
              <tr>
                <th>Token</th>
                <th>説明</th>
                <th>期待値</th>
                <th>実測値</th>
              </tr>
            </thead>
            <tbody>
              {TOKEN_SUMMARY.map(({ token, desc, expected }) => (
                <TokenRow key={token} token={token} desc={desc} expected={expected} />
              ))}
            </tbody>
          </table>
        </section>

        {/* ════════════════════════════════════════
            Button — バリアント × サイズ
            ════════════════════════════════════════ */}
        <section className="dp-section">
          <SectionHeader title="2. Button — バリアント × サイズ" />

          {(["primary", "secondary", "ghost", "danger"] as const).map((variant) => (
            <div key={variant} className="dp-row">
              <span className="dp-row-label">{variant}</span>
              <div className="dp-row-items">
                <Button variant={variant} size="sm">Small</Button>
                <Button variant={variant} size="md">Medium</Button>
                <Button variant={variant} size="lg">Large</Button>
              </div>
            </div>
          ))}
        </section>

        {/* ════════════════════════════════════════
            Button — 状態
            ════════════════════════════════════════ */}
        <section className="dp-section">
          <SectionHeader title="3. Button — 状態" />

          <div className="dp-row">
            <span className="dp-row-label">normal</span>
            <div className="dp-row-items">
              <Button variant="primary">Normal</Button>
            </div>
          </div>
          <div className="dp-row">
            <span className="dp-row-label">disabled</span>
            <div className="dp-row-items">
              <Button variant="primary" disabled>Disabled</Button>
              <Button variant="secondary" disabled>Disabled</Button>
              <Button variant="ghost" disabled>Disabled</Button>
              <Button variant="danger" disabled>Disabled</Button>
            </div>
          </div>
          <div className="dp-row">
            <span className="dp-row-label">loading</span>
            <div className="dp-row-items">
              <Button variant="primary" loading>Saving...</Button>
              <Button variant="secondary" loading>Loading</Button>
            </div>
          </div>
          <div className="dp-row">
            <span className="dp-row-label">fullWidth</span>
            <div className="dp-row-items dp-row-items--full">
              <Button variant="primary" fullWidth>Full Width Button</Button>
            </div>
          </div>
          <div className="dp-row">
            <span className="dp-row-label">icon only</span>
            <div className="dp-row-items">
              <Button variant="primary" iconOnly aria-label="Add item">＋</Button>
              <Button variant="ghost" iconOnly aria-label="Close">✕</Button>
              <Button variant="secondary" iconOnly aria-label="Settings">⚙</Button>
            </div>
          </div>
        </section>

        {/* ════════════════════════════════════════
            Card — バリアント × 密度
            ════════════════════════════════════════ */}
        <section className="dp-section">
          <SectionHeader title="4. Card — バリアント × 密度" />

          {(["container", "interactive", "metric"] as const).map((variant) => (
            <div key={variant} className="dp-card-row">
              <div className="dp-card-col">
                <span className="dp-card-col-label">{variant} / default</span>
                <Card variant={variant} density="default">
                  <p className="dp-card-title">{variant}</p>
                  <p className="dp-card-body">
                    padding: 24px (--comp-card-padding)
                    <br />
                    radius: 8px (--comp-card-radius)
                  </p>
                </Card>
              </div>
              <div className="dp-card-col">
                <span className="dp-card-col-label">{variant} / compact</span>
                <Card variant={variant} density="compact">
                  <p className="dp-card-title">{variant}</p>
                  <p className="dp-card-body">
                    padding: 16px (--comp-card-padding-compact)
                    <br />
                    radius: 8px (--comp-card-radius)
                  </p>
                </Card>
              </div>
            </div>
          ))}
        </section>

        {/* ════════════════════════════════════════
            カード列グリッド確認（gap 検証）
            ════════════════════════════════════════ */}
        <section className="dp-section">
          <SectionHeader title="5. カードグリッド（gap = 24px）" />
          <div className="dp-card-grid">
            {["Card A", "Card B", "Card C"].map((label) => (
              <Card key={label} variant="container">
                <p className="dp-card-title">{label}</p>
                <p className="dp-card-body">gap: var(--comp-card-gap) = 24px</p>
              </Card>
            ))}
          </div>
        </section>

      </div>
    </PageLayout>
  );
}

// ── トークン実測値を CSS から読み出す行コンポーネント ────────────
function TokenRow({ token, desc, expected }: { token: string; desc: string; expected: string }) {
  const actual =
    typeof getComputedStyle === "function"
      ? getComputedStyle(document.documentElement).getPropertyValue(token).trim()
      : "—";

  return (
    <tr>
      <td className="dp-token-name"><code>{token}</code></td>
      <td>{desc}</td>
      <td className="dp-token-expected">{expected}</td>
      <td className="dp-token-actual">{actual || "—"}</td>
    </tr>
  );
}
