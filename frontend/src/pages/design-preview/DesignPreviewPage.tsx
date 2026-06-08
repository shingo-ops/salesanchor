/**
 * DesignPreviewPage -- コンポーネント標準 目視確認ページ（Task 1C-6D）
 * dev-only preview: 日本語表記を許可（eslint.config.js の overrides 参照）
 *
 * アクセス: /design-preview?room=<key>（ログイン後 URL 直打ち・ナビ未掲載）
 *
 * 新セクション追加手順:
 *   1. `sections/XxxSection.tsx` を新規作成
 *   2. `sections/registry.ts` に 1 エントリ追加（key / label / group / component）
 *   → サイドメニュー項目とルームが自動で増える
 */

import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { PageLayout } from "../../components/PageLayout";
import { SubMenu } from "../../components/SubMenu";
import type { SubMenuGroup } from "../../components/SubMenu";
import { SECTION_REGISTRY } from "./sections/registry";
import "./DesignPreviewPage.css";

// -- 幅セレクタの選択肢 -------------------------------------------------------
const WIDTH_BANDS = [
  { label: "モバイル (375px)",   value: 375  },
  { label: "タブレット (768px)", value: 768  },
  { label: "PC (全幅)",          value: null },
] as const;

type BandValue = 375 | 768 | null;

/** registry からサイドメニュー用グループを生成（グループ順は registry 登録順） */
function buildGroups(): SubMenuGroup<string>[] {
  const map = new Map<string, SubMenuGroup<string>>();
  for (const entry of SECTION_REGISTRY) {
    if (!map.has(entry.group)) {
      map.set(entry.group, { title: entry.group, items: [] });
    }
    map.get(entry.group)!.items.push({ key: entry.key, label: entry.label });
  }
  return Array.from(map.values());
}

const GROUPS = buildGroups();

export default function DesignPreviewPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [bandWidth, setBandWidth] = useState<BandValue>(null);

  const activeKey =
    searchParams.get("room") ?? SECTION_REGISTRY[0].key;
  const activeEntry =
    SECTION_REGISTRY.find((e) => e.key === activeKey) ?? SECTION_REGISTRY[0];
  const ActiveSection = activeEntry.component;

  return (
    <PageLayout navKey="nav.designPreview" subtitleKey="designPreview.subtitle" noScroll>
      <div className="dp-shell">
        {/* 左: サイドメニュー（SubMenu 金型のドッグフーディング） */}
        <aside className="dp-sidebar">
          <SubMenu
            variant="grouped"
            groups={GROUPS}
            activeKey={activeKey}
            onChange={(key) => setSearchParams({ room: key }, { replace: true })}
          />
        </aside>

        {/* 右: 選択中ルーム */}
        <div className="dp-room">
          {/* 幅セレクタ */}
          <div className="dp-band-selector">
            <span className="dp-band-label">プレビュー幅:</span>
            {WIDTH_BANDS.map((b) => (
              <button
                key={String(b.value)}
                type="button"
                className={`dp-band-btn${bandWidth === b.value ? " dp-band-btn--active" : ""}`}
                onClick={() => setBandWidth(b.value as BandValue)}
              >
                {b.label}
              </button>
            ))}
          </div>

          {/* プレビューフレーム */}
          <div
            className="dp-preview-frame"
            style={bandWidth != null ? { maxWidth: bandWidth, margin: "0 auto" } : undefined}
          >
            <ActiveSection />
          </div>
        </div>
      </div>
    </PageLayout>
  );
}
