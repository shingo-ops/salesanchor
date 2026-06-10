# recon — 見た目改善（A）: 集計枠 Card 統一 ＋ 役割バッジ色修正

**仕事名**: 見た目改善（A）  
**日付**: 2026-06-11  
**対象ADR**: 未起案（本 recon を受けて Planner が起案）  
**担当**: architect

---

## 調査1: 生の `<fieldset>` が残っているページ

### 分類方針
- **Card 化対象**: 集計サマリー（read-only KPI 表示）
- **除外**: フォームセクション（`<input>` / `<select>` を含む入力グルーピング。`<fieldset>` の本来用途なので変更不要）

---

### ◎ Card 化対象（集計サマリー系）— 3箇所

| ページ | `path:line` | 表示内容 | Card variant 案 |
|--------|-------------|---------|----------------|
| 売上管理 | `frontend/src/pages/sales/SalesPage.tsx:90` | 件数・売上合計・原価合計・粗利合計・粗利率 (5 KPI) | `metric` |
| 報酬管理（月次集計） | `frontend/src/pages/commissions/CommissionsPage.tsx:134` | 年月フィルター ＋ 合計金額 ＋ スタッフ別・ロール別内訳テーブル | `container` |
| 報酬管理（管理操作） | `frontend/src/pages/commissions/CommissionsPage.tsx:218` | 受注一覧テーブル（担当者割当ボタン付き） | `container` |

**SalesPage.tsx:90–109 の現状:**
```tsx
<fieldset style={{ marginBottom: "var(--space-4)" }}>
  <legend>{t("sales.summaryLegend")}</legend>
  <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-6)" }}>
    <span>{t("sales.count")}: <strong>{data.count}</strong></span>
    <span>{t("sales.revenueTotal")}: <strong>{fmt(data.revenue_total)}</strong></span>
    <span>{t("sales.costTotal")}: <strong>{fmt(data.cost_total)}</strong></span>
    <span>{t("sales.grossProfitTotal")}: <strong>{fmt(data.gross_profit_total)}</strong></span>
    <span>{t("sales.grossProfitRate")}: <strong>{fmtRate(data.gross_profit_rate)}</strong></span>
  </div>
</fieldset>
```

**CommissionsPage.tsx:134–213 の現状:**
- `<fieldset>` に年月 `<input>` ＋ 合計 `<p>` ＋ DataTable x2（スタッフ別・ロール別）を包含
- 入力を含むが **集計表示が主目的** → `container` Card に変換可

**CommissionsPage.tsx:218–246 の現状:**
- `canEdit` 条件で表示される管理テーブル（受注一覧 ＋ 割当ボタン）
- 入力は行アクションボタンのみ → `container` Card に変換可

---

### △ 除外（フォームセクション用）— 変更不要

| ファイル | 行 | 理由 |
|---------|-----|------|
| `frontend/src/components/PurchaseDetailPanel.tsx` | 313, 346, 370, 397 | 仕入フォーム入力グルーピング（`<fieldset>` 正当用途） |
| `frontend/src/components/ShippingDetailPanel.tsx` | 386, 410, 434, 461, 499 | 配送フォーム入力グルーピング |
| `frontend/src/pages/products/ProductEditPage.tsx` | 266, 320, 349 | 商品編集フォーム |
| `frontend/src/pages/register/RegisterPage.tsx` | 189, 229, 239 | 登録フォーム（請求先・配送先） |
| `frontend/src/pages/register/RegisterAddressPage.tsx` | 158 | 住所入力フォーム |
| `frontend/src/pages/commission-settings/CommissionSettingsPage.tsx` | 187, 268 | 報酬レート入力フォーム |

---

### Card コンポーネントの現状

| `path:line` | 確認内容 |
|-------------|---------|
| `frontend/src/components/Card.tsx:1` | `Card` コンポーネント実装済み（variant: container / interactive / metric） |
| `frontend/src/components/Card.tsx:10` | コメント: "実画面への展開は Task 1E で行う。このコンポーネント自体は Preview 画面でのみ使用。" → **実ページへの展開がまだ** |
| `frontend/src/components/Card.css:68` | `.comp-card--metric { border-top: 3px solid var(--accent); }` → KPI 表示用のアクセントライン付き |

---

## 調査2: 役割バッジの「赤」ロジック

### 色の定義元（バックエンド）

| `path:line` | 内容 |
|-------------|-----|
| `backend/app/services/tenant.py:42` | `DEFAULT_ROLES` 配列の先頭が `"オーナー"` |
| `backend/app/services/tenant.py:44` | `"color": "#ef4444"` — **赤（理由コメントは「赤」のみ）** |
| `backend/app/services/tenant.py:52` | システム管理者: `"#a855f7"` (紫) |
| `backend/app/services/tenant.py:60` | リーダー: `"#3b82f6"` (青) |
| `backend/app/services/tenant.py:88` | 営業: `"#22c55e"` (緑) |
| `backend/app/services/tenant.py:112` | CS: `"#f97316"` (オレンジ) |
| `backend/app/services/tenant.py:1435` | `seed_system_roles()`: `INSERT INTO roles … color = EXCLUDED.color` で毎回 seed 値で上書き |

**結論**: オーナーが赤になる理由は `DEFAULT_ROLES` の `color` フィールドが `#ef4444` だから。

### 色の表示箇所（フロントエンド）

| `path:line` | 表示方法 |
|-------------|---------|
| `frontend/src/pages/roles/RolesPage.tsx:344` | サイドバー: `style={{ borderLeft: "4px solid ${r.color}" }}` |
| `frontend/src/pages/roles/RolesPage.tsx:370` | メインヘッダーバッジ: `style={{ background: selectedRole.color, color: "var(--on-accent)" }}` |
| `frontend/src/pages/roles/RolesPage.tsx:563` | ユーザー割当モーダルのチェックボックス行: `style={{ background: r.color }}` |

**共通パターン**: 全て DB の `roles.color` を **インライン style** で直接適用。CSS クラスは使っていない。

### フロントのカラーパレット

| `path:line` | 内容 |
|-------------|-----|
| `frontend/src/pages/roles/RolesPage.tsx:74` | `COLOR_PALETTE[0] = "#ef4444"` (赤) — 新規ロール作成時のデフォルト |
| `frontend/src/pages/roles/RolesPage.tsx:92` | `emptyRoleForm.color = COLOR_PALETTE[0]` → **赤がデフォルト** |

---

## 調査3: `statusPresentation.ts` の流用可否

| `path:line` | 確認内容 |
|-------------|---------|
| `frontend/src/utils/statusPresentation.ts:13` | `BadgeBucket` = `"success" \| "danger" \| "warning" \| "info" \| "neutral"` — 5バケット |
| `frontend/src/utils/statusPresentation.ts:38` | `StatusDomain` = 11ドメイン（lead/quote/invoice/deal/order/purchaseOrder/parseStatus/staff/bot/prospectRank/erpJobStatus） |
| `frontend/src/utils/statusPresentation.ts:45` | 設計コメント: `danger = 失敗/エラー/期限超過/失注/拒否` と明記 → **赤=危険予約済み** |

### ロール名への流用可否

**制約**: ロール名は自由入力（テナント管理者がカスタマイズ可能）→ 可変な文字列を `StatusDomain` の固定マッピングに乗せるのは不適合。

**ただしシステムロールは適合範囲**:
- `is_system = True` のロール（オーナーのみ）は名前が固定 → マッピング可能だが過剰設計
- より**シンプルかつ根本的な解決策**: `backend/app/services/tenant.py:44` の `#ef4444` を意味に合った色（例: `#6366f1` インディゴ=最高権限）に変更するだけ
- `seed_system_roles()` が `color = EXCLUDED.color` で毎回 seed 値を反映するため、**バックエンド1行変更が全テナントに自動適用**される

### 「赤=危険」の予約の現状

| バケット | 意味 | 現在の用途 |
|---------|------|-----------|
| `danger` | 失敗/エラー/期限超過 | `badge-lost`, `badge-cancelled`, `badge-trouble`, `comp-badge--danger` |
| （なし） | 権限レベル | オーナーロール色 `#ef4444` — **danger と同値だが意味が違う** |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | Card の `metric` variant は SalesPage の 5 KPI を横並びで入れ替えられるか（レスポンシブ） | Card.css:68 確認済み。内部レイアウト（flex wrap）はそのまま維持可能 | ✅ 解消済み |
| 2 | CommissionsPage の fieldset は `<input>` を含むため Card 化してよいか | コンテンツ主体が集計表示であり、年月入力は「フィルター」扱い → container Card で可 | ✅ 解消済み |
| 3 | `seed_system_roles()` の color 変更が既存テナントに即時反映されるか | `ON CONFLICT … SET color = EXCLUDED.color` の確認済み → 次回 seed 実行（テナント初期化 or 手動再実行）で反映。**既存テナントへの即時適用にはマイグレーション SQL が別途必要** | ⚠️ 要 Planner 判断 |
| 4 | オーナー以外のロールでも「危険色」が使われているケースがあるか | `COLOR_PALETTE[0]` が赤でデフォルト → 既存テナントで赤を使うカスタムロールが存在しうる。ただし**カスタムロールは seed 対象外**なので今回の変更影響外 | ✅ 解消済み（スコープ外確認） |

**未解決**: 不明点3（既存テナント適用方法）は Planner 判断事項。

---

## 補足

- `Card` コンポーネントコメント「Task 1E で実画面展開」とあるが、Task 1E が完了したかどうかは git log で確認要。現状 `Card` を実ページで使用しているコードはなし（Preview/Stories のみ）。
- `CommissionSettingsPage.tsx:187,268` の fieldset はフォーム入力主体のため今回スコープ外。
- `ProductEditPage.tsx`, `PurchaseDetailPanel.tsx`, `ShippingDetailPanel.tsx`, `RegisterPage.tsx` の fieldset は全てフォームセクションのため変更不要。
