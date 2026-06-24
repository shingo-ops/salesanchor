# recon — inventory-ui-tweaks

**対象ADR**: ADR-093
**仕事名**: inventory-ui-tweaks（/inventory の微調整3点：警告の右上固定・検索行の高さ1.5倍・その他プルダウンの枠線統一）
**日付**: 2026-06-25

---

## 目的
本番稼働中の /inventory に対する見た目の微調整。本番DB無関係・migrationなし。

## 対象（frontend/src/pages/inventory/InventoryPage.tsx）
- `frontend/src/pages/inventory/InventoryPage.tsx:414` — 警告 <p> data-testid="inventory-expiry-warning"。現状 `<section>`(ツールバー)直後・FilterPanel直前に左寄せ配置。
- `frontend/src/pages/inventory/InventoryPage.tsx:415` — 警告 style `margin: var(--space-2) 0; fontSize: var(--font-sm); color: var(--text-secondary)`。
- `frontend/src/pages/inventory/InventoryPage.tsx:466` — タブ行コンテナ `<div className="tabs" style={display:flex; gap:var(--space-xs); flexWrap:wrap; margin:var(--space-sm) 0; alignItems:center}>`。justify-content 指定なし（左寄せ）。
- `frontend/src/pages/inventory/InventoryPage.tsx:492` — 「その他」<select>。style `fontSize:var(--font-xs); padding:var(--space-1) var(--space-10px)`。border/border-radius/background の指定なし＝OS標準外観。
- `frontend/src/pages/inventory/InventoryPage.tsx:383` — 検索 <input>。style `width:22rem; padding:var(--space-1) var(--space-10px); fontSize:var(--font-xs)`。明示 height なし。
- `frontend/src/pages/inventory/InventoryPage.tsx:395` — 検索ボタン `btn-primary btn-sm`。
- `frontend/src/pages/inventory/InventoryPage.tsx:398` — リセットボタン `btn-secondary btn-sm`。
- `frontend/src/pages/inventory/InventoryPage.tsx:403` — 詳細フィルタボタン `btn-primary/secondary btn-sm`。

## アプリ標準フォームスタイル（components.css）
- `frontend/src/components.css:19` — `.form-group input, select`: `border:1px solid var(--border); border-radius:var(--radius-sm); padding:var(--space-2) var(--space-3); font-size:var(--font-base)`。
- `frontend/src/components.css:25` — `border-radius: var(--radius-sm)`。
- `frontend/src/index.css:21` — `--border: #e2e8f0(light) / #334155(dark)`。
- `frontend/src/tokens.css:68` — `--space-1: 4px`。
- `frontend/src/tokens.css:14` — `--font-xs: 0.75rem (12px)`。
- `frontend/src/index.css:402` — `line-height: 1.6`（body）。
- `frontend/src/components.css:95` — `.btn-sm`: `padding: var(--space-1) var(--space-10px); font-size: var(--font-xs); border: none`。

## ギャップ結論
- #1 警告: タブ行の外にあり左寄せ → タブ行(:466)の右端へ移動・font を var(--font-xs) に・「※」付与。
- #2 高さ: input/btn とも明示 height なし(padding依存) → H=29px → 44px（×1.5）を4要素に付与。btn-sm は共有クラスのため直接編集せず、この画面のみスコープ適用。
- #3 その他select(:492): border/radius/background なし(OS標準) → .form-group select 相当(--border/--radius-sm/--bg-surface)に統一。
