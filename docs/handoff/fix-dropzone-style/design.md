# design: fix-dropzone-style

**recon**: docs/handoff/fix-dropzone-style/recon.md

## あるべき姿

ダッシュボードのアップロードドロップゾーンは、インポートページと同様の
視覚スタイルを持つ。具体的には：

1. 破線枠（`2px dashed`）が明示的に表示される（既存 CSS 確認済み）
2. ファイルアイコン（Lucide file-up スタイル）が中央に表示される
3. テキストがアイコンの下に縦並びで中央寄せされる
4. hover 時に border-color が変化する

## 変更設計

### AnalysisDashboardPanel.tsx

- `analysis-dashboard-dropzone` div 内部に `<svg>` アイコンを追加
- `aria-hidden="true"` で装飾要素として扱う
- `className="analysis-dashboard-dropzone-icon"` でトークン経由スタイリング
- `ui-allow` コメント付与（登録アイコン非対象）

### AnalysisDashboardPanel.css

- `.analysis-dashboard-dropzone`: `display: flex`, `flex-direction: column`, `align-items: center`, `gap: var(--space-2)` 追加
- padding を `var(--space-4)` → `var(--space-6)` に拡張
- `:hover` 状態追加（`border-color: var(--color-primary)`, `background-color: var(--color-surface-hover)`）
- `.analysis-dashboard-dropzone-icon`: `color: var(--text-muted)` 追加
- `.analysis-dashboard-dropzone p`: `color: var(--text-secondary)`, `margin: 0` 追加

## ADR参照

- ADR-067: `docs/adr/ADR-067-design-token-enforcement.md`
- ADR-144: `docs/CC_UI_GOVERNANCE.md`

## 外部・過去事例の参照と我々への応用

`TcgLineImportPage.tsx:308-344` — 既存ドロップゾーン実装（破線 border + inline styles）を参照。
本実装はクラスベースに統一し、アイコン追加で視認性向上。
インポートページと同一パターンを採用することで、今後のドロップゾーン追加時も同様の実装が適用できる。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| アイコンが表示される | ブラウザで Import タブを開き SVG が描画されること |
| 破線枠が表示される | DevTools で `border: 2px dashed` が適用されていること |
| hover で border 色変化 | マウスオーバーで枠が primary 色になること |
| トークン外直値なし | `npm run check:css-hardcoded-colors` がパスすること |

## 維持の仕組み

スタイル変更はすべて CSS カスタムプロパティ（デザイントークン）経由。直値の混入は `npm run check:css-hardcoded-colors` で自動検出される。

守り手: `scripts/check-css-hardcoded-colors.js`（Frontend lint & custom checks CI）
