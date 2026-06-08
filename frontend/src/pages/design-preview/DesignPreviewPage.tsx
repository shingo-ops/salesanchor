/**
 * DesignPreviewPage -- コンポーネント標準 目視確認ページ（Task 1C / 2C）
 * dev-only preview: 日本語表記を許可（eslint.config.js の overrides 参照）
 *
 * アクセス: /design-preview（ログイン後 URL 直打ち・ナビ未掲載）
 *
 * 新セクション追加手順:
 *   1. `sections/XxxSection.tsx` を作成（セクション全責務はそのファイル内に完結）
 *   2. `sections/registry.ts` に 1 行追加
 *   既存ファイルの末尾編集不要 → マージ衝突しない
 */

import { useState } from "react";
import { PageLayout } from "../../components/PageLayout";
import { SECTION_REGISTRY } from "./sections/registry";
import "./DesignPreviewPage.css";

// -- 幅セレクタの選択肢 -------------------------------------------------------
const WIDTH_BANDS = [
  { label: "モバイル (375px)",   value: 375  },
  { label: "タブレット (768px)", value: 768  },
  { label: "PC (全幅)",          value: null },
] as const;

type BandValue = 375 | 768 | null;

export default function DesignPreviewPage() {
  const [bandWidth, setBandWidth] = useState<BandValue>(null);

  return (
    <PageLayout navKey="nav.designPreview" subtitleKey="designPreview.subtitle">
      {/* -- 幅セレクタ -- */}
      <div className="dp-band-selector">
        <span className="dp-band-label">プレビュー幅:</span>
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

      {/* -- プレビュー枠 -- */}
      <div
        className="dp-preview-frame"
        style={bandWidth != null ? { maxWidth: bandWidth, margin: "0 auto" } : undefined}
      >
        {SECTION_REGISTRY.map((Section, i) => (
          <Section key={i} />
        ))}
      </div>
    </PageLayout>
  );
}
