# recon — migrate-lead-edit-select

**仕事名**: migrate-lead-edit-select
**日付**: 2026-06-26
**対象ADR**: ADR-073
**担当**: Hikky-dev

---

## 背景

移行フェーズ正典・試運転①。
frontend/src/pages/leads/LeadEditPage.tsx に存在した生 select 7個を共通 Select コンポーネントへ置き換える。
ADR-073（デザインシステム KGI ルーブリック）の軸1（共通コンポーネント適用率）向上が目的。

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/pages/leads/LeadEditPage.tsx:154` | initiative フィールド：`<Select>` コンポーネント適用済み |
| `frontend/src/pages/leads/LeadEditPage.tsx:164` | type フィールド：`<Select>` コンポーネント適用済み |
| `frontend/src/pages/leads/LeadEditPage.tsx:174` | status フィールド：`<Select>` コンポーネント適用済み |
| `frontend/src/pages/leads/LeadEditPage.tsx:183` | temperature フィールド：`<Select>` コンポーネント適用済み |
| `frontend/src/pages/leads/LeadEditPage.tsx:194` | estimatedScale フィールド：`<Select>` コンポーネント適用済み |
| `frontend/src/pages/leads/LeadEditPage.tsx:205` | customerType フィールド：`<Select>` コンポーネント適用済み |
| `frontend/src/pages/leads/LeadEditPage.tsx:217` | responseSpeed フィールド：`<Select>` コンポーネント適用済み |
| `frontend/src/components/Select.tsx:36` | `Select` コンポーネント本体（export function Select）|
| `frontend/src/components/Select.tsx:73` | `<select className="comp-field__select">` — 棚の DOM 構造 |
| `frontend/src/components/FormField.css:48` | `.comp-field__select` ベーススタイル定義 |
| `frontend/src/components/FormField.css:53` | `border-radius: var(--comp-input-radius)` — 6px（棚の標準値） |
| `frontend/src/components.css:7` | `.form-group` — 旧スタイル定義（置き換え元） |
| `frontend/src/components.css:20` | `.form-group select` — 旧 border-radius: var(--radius-sm) = 4px |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | border-radius 差異（4px→6px）はPO承認済みか | PO 目視確認＋GO #2599 受領（2026-06-26） | ✅ 解消済み |
| 2 | DB 値の日本語文字列に eslint 対応が必要か | `// eslint-disable-next-line local/no-japanese-literal -- DB value` で除外 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
