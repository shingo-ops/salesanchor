# design: LLM使用量ダッシュボードのコスト表示を円（JPY）換算にする

## PO指示
2026-10-01 PO承認「よい」。LLM使用量ダッシュボードのコストを、現在の為替レート（ADR-148 SSOT）で円換算して表示する。

## recon参照
`docs/handoff/llm-usage-cost-jpy/recon.md`（本設計の事実根拠。origin/main `5f311c726e9e4089427456dd35313cd363db1cec` 時点）

## 対象ADR
- ADR-148（`docs/adr/ADR-148-fx-rate-ssot.md`）: 為替レートは `public.app_fx_rates` が唯一の正。フロントは `GET /api/v1/fx-rate/{currency}` を読むのみで、レート値のハードコードやフロント独自計算は禁止。本変更はこの原則に従い、レート値リテラルをコードに一切書かない。
- ADR-1004（`docs/adr/ADR-1004-llm-usage-ledger.md`）: 本コンポーネントの対象データ（`public.llm_usage_events`）。本変更はこのADRのデータ・API契約には触れず、表示レイヤーのみ変更する。
- ADR-027（`docs/adr/ADR-027-ui-internationalization.md`）: 全UI文字列 `t()` 経由。新規の注記文言もすべて `analysisRules.dashboard.usage.fx.*` キーで ja/en 対称に追加。
- ADR-067（`docs/adr/ADR-067-design-token-enforcement.md`）: 色・サイズはトークンのみ。本変更はCSS新規追加なし（既存クラス `.analysis-dashboard-section-note` を再利用）。
- ADR-144（`docs/adr/ADR-144-ui-component-governance.md`）: Card/DataTable 金型のみ使用。新規UI部品の追加なし。

## 設計方針

### 1. フェッチ
`frontend/src/pages/super-admin/components/LlmUsageSection.tsx` の既存 `useEffect`（llm-usage 取得）内で `GET /fx-rate/USD` も並行取得する。共有クライアント/hookは存在しない（recon確認済み）ため、`frontend/src/pages/super-admin/FxRatePage.tsx` と同じパターン（コンポーネント内 `interface FxRate` + `api.get<FxRate>("/fx-rate/USD")` 直接呼び出し）を踏襲した。

```tsx
useEffect(() => {
  setLoading(true);
  setError(null);
  Promise.all([
    api.get<LlmUsageResponse>(`/tcg/analysis-dashboard/llm-usage?days=${days}`),
    api.get<FxRate>("/fx-rate/USD").catch(() => null),
  ])
    .then(([res, fx]) => {
      setData(res);
      setFxRate(fx != null && typeof fx.rate_jpy === "number" ? fx : null);
    })
    .catch(() => {
      setError(t("analysisRules.dashboard.fetchError"));
    })
    .finally(() => {
      setLoading(false);
    });
}, [days, t]);
```
fx-rate の失敗は `.catch(() => null)` で握り、llm-usage 本体の表示を止めない（為替取得失敗時はUSDフォールバック、下記5）。

### 2. 換算（1箇所に集約）
```tsx
function toJpy(usd: number, rateJpy: number): number {
  return usd * rateJpy;
}
```
呼び出し元はすべてこの1関数経由。コンポーネント内では以下の2段ヘルパーに集約:
- `formatCost(usd: number | null): string` — 生のUSD値を受け取り、`costRate` があれば `toJpy` で換算してJPY整形、なければUSDのまま整形。サマリーヒーロー・全テーブルのコスト列で使用。
- `formatConvertedCost(value: number): string` — **既に換算済みの値**（チャート用に事前変換したデータ）を整形するのみ（二重換算を避けるため）。チャートTooltipで使用。

適用箇所（recon.mdの一覧に対応）:
1. サマリーヒーロー → `formatCost(data.total.cost_usd)`
2. 使いみち別テーブル `cost_usd` 列 → `formatCost(row.cost_usd)`
3. 日別テーブル `cost_usd` 列 → `formatCost(row.cost_usd)`
4. モデル別テーブル `cost_usd` 列 → `formatCost(row.cost_usd)`
5. 日次/月次費用チャートのデータ値 → `pivotByPurpose` に渡す前に `convertCost`（`toJpy` のnullガード版）で `cost_usd` を変換してから pivot（`pivotByPurpose` 自体は通貨を意識しない汎用関数のまま変更しない）
6. 日次/月次費用チャートのTooltip → `formatChartCurrency = (value) => formatConvertedCost(value)`（既に変換済みのデータ値を整形するだけ）

### 3. フォーマット
- JPY金額: `new Intl.NumberFormat(language, { style: "currency", currency: "JPY", maximumFractionDigits: 2, minimumFractionDigits: 0 })`（`makeJpyFormatter`）
- コストチャートY軸ティック: `new Intl.NumberFormat(language, { style: "currency", currency: costRate == null ? "USD" : "JPY", notation: "compact", maximumFractionDigits: 1 })`（`makeCompactCurrencyFormatter`）。レート取得成功時は `¥500` `¥1.2K` のように単位付きで表示される（recon.mdで確認した「単位が付かない」既知課題の修正）。非コストチャート（リクエスト数・エラー数・トークン推移）のY軸は既存の `compactTick`（単位なし）のまま変更しない。

### 4. レート注記
サマリーカードの直下（`llm-usage-summary` Card の `</Card>` 直後、費用チャートCardより前）に表示:
```tsx
{costRate != null && fxRate != null ? (
  <p className="analysis-dashboard-section-note" data-testid="llm-usage-fx-note">
    {t("analysisRules.dashboard.usage.fx.note", {
      rate: fxRate.rate_jpy.toLocaleString(i18n.language, { minimumFractionDigits: 2, maximumFractionDigits: 4 }),
      fetchedAt: formatFetchedAtJst(fxRate.fetched_at, i18n.language),
    })}
  </p>
) : (
  <p className="analysis-dashboard-section-note" data-testid="llm-usage-fx-fallback-note">
    {t("analysisRules.dashboard.usage.fx.fallbackNote")}
  </p>
)}
```
`formatFetchedAtJst` は他ページ（`frontend/src/pages/super-admin/TcgSoldOutPage.tsx:61` 等）と同じ `Asia/Tokyo` 固定パターンを踏襲:
```tsx
function formatFetchedAtJst(isoString: string, language: string): string {
  return new Date(isoString).toLocaleString(language, {
    timeZone: "Asia/Tokyo",
    year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit",
  });
}
```

**既知の制約（PO申し送り）**: 過去の日次/月次データも、保存時点のレートではなく**現在取得したレート1本**で一律換算する。`public.app_fx_rates` は現在値のみを保持するSSOTで、履歴を持たないため（ADR-148）。これは注記文言内に明記（「過去の日も同じレートで計算しています」）。

### 5. フォールバック
`/fx-rate/USD` が失敗する、または `rate_jpy` がレスポンスに存在しない（`typeof fx.rate_jpy !== "number"`）場合、`costRate` は `null` のままとなり、`formatCost`/`formatConvertedCost`/`costTick` はすべて既存のUSDフォーマッタにフォールバックする。レートの推測値は一切使わない。フォールバック注記（`fx.fallbackNote`）のみ表示する。

### 6. i18nキー（`analysisRules.dashboard.usage.fx.*`、ja.json/en.json 対称）
```json
"fx": {
  "note": "1ドル＝{{rate}}円（{{fetchedAt}} 時点のレートで換算。過去の日も同じレートで計算しています）",
  "fallbackNote": "為替レートを取得できないため、ドルで表示しています"
}
```
（en.json側は英訳。新規ハードコード日本語文字列なし、すべて `t()` 経由）

## 変更ファイル
- `frontend/src/pages/super-admin/components/LlmUsageSection.tsx`（本体: fx-rate 並行取得・換算ヘルパー・フォーマッタ差し替え・レート注記追加）
- `frontend/src/pages/super-admin/components/LlmUsageSection.test.tsx`（fx-rate モックヘルパー追加 + JPY換算/注記/フォールバックの新規テスト6件）
- `frontend/src/locales/ja.json`（`analysisRules.dashboard.usage.fx` 追加、`:4519-4522` 付近）
- `frontend/src/locales/en.json`（同上、英訳）

バックエンド・CSSファイルは無変更（既存API・既存クラスを再利用）。

## 基準・検証方法

| 基準 | 検証方法 |
|---|---|
| サマリーヒーロー・全コスト列・費用チャートが JPY（¥、maximumFractionDigits:2）で表示される | `vitest`: `"shows the hero cost converted to JPY using the fetched rate"` / `"shows JPY in the by-purpose, daily, and by-model cost table columns"`（rate=150固定、0.0021 USD → ¥0.32 を検証） |
| コストチャートY軸ティックに通貨単位が付く（JPY成功時は¥、フォールバック時は$） | `makeCompactCurrencyFormatter` の分岐（`costRate == null ? "USD" : "JPY"`）。手動確認: `node -e` で `¥500`/`¥1.2K` を実測済み（recon.md不要・本design内で実測）。vitest は `"renders the cost charts ... without throwing"` で描画成功のみ確認（recharts の tickFormatter 個別呼び出しはjsdomでは描画サイズ依存のため値アサーションはTooltip側に寄せる） |
| 非コストチャート（リクエスト数・エラー数・トークン推移）のY軸は従来通り単位なし | コード上 `compactTick` を変更していない（`costTick` は費用チャート2箇所のみに適用）。既存テスト（リクエスト/エラー/モデル別トークンのレンダリングテスト）が継続PASSすることで確認 |
| レート取得成功時に注記「1ドル＝150円（...時点のレートで換算...）」が表示される | `vitest`: `"shows the rate note with the converted rate and JST fetched_at"` |
| レート取得失敗時・`rate_jpy` 欠落時はUSD表示＋フォールバック注記、レートの推測値を使わない | `vitest`: `"falls back to USD and shows the fallback note when the fx-rate request fails"` / `"falls back to USD when the fx-rate response has no rate_jpy"` |
| 既存テスト（USD表示前提の19件）が壊れない | `vitest run` 全27件PASS（既存19件 + 新規6件 + 既存 `formatCompactNumber` 2件） |
| 過去日も現在レート一律換算である旨が注記に含まれる | i18nキー `fx.note` の文言に明記（ja/en とも）。レビューで文言確認 |
| i18n: ja/en キー対称、新規ハードコード日本語なし | `npm run check:i18n-missing-keys` PASS ＋ `grep -n '[ぁ-んァ-ヶ一-龠]' frontend/src/pages/super-admin/components/LlmUsageSection.tsx` の非コメント行が0件（実行済み・0件確認） |
| ADR-067（トークンのみ） | CSS無変更。新規色・サイズ値の追加なし |
| ADR-144（金型のみ） | 既存 `Card` / `.analysis-dashboard-section-note` を再利用、新規UI部品なし |
| 型エラーなし | `npx tsc --noEmit` exit 0（実行済み・無出力） |
| Lintエラーなし | `npx eslint --max-warnings=0` 対象.tsxファイルで 0件（実行済み） |
| CSSガード系 | `check:css-colors` / `check:css-values` / `check:css-class-naming` / `check:dark-parity` 全てPASS（CSS無変更のため影響なしの確認目的、実行済み） |

## 外部・過去事例
該当なし（理由: 社内管理画面のコスト表示を自社SSOTの為替レートで円換算するだけの表示整形であり、外部の実装パターン比較を要する新規UI/UXデザイン判断ではない。レートSSOTの設計自体はADR-148で既に確立済み）。

## 影響範囲
- `frontend/src/pages/super-admin/components/LlmUsageSection.tsx` の呼び出し元は `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx` の1箇所のみ（props `days`, `t` は変更なし）。
- `GET /fx-rate/USD` は読み取り専用・冪等であり、既存の `frontend/src/pages/super-admin/FxRatePage.tsx` / `frontend/src/pages/quote-detail/QuoteDetailPage.tsx` の呼び出しと衝突しない（バックエンド側変更なし）。
- `pivotByPurpose` 自体は変更していないため、他の呼び出し元（本ファイル内のみ、`git grep -n "pivotByPurpose" frontend/src` で1ファイル内完結を確認）への影響なし。

## 戻し方
本コミットを `git revert` すれば、fx-rate 取得・換算ロジック・注記UI・i18nキー・テストがすべて復元され、コスト表示はUSD固定に戻る。バックエンド・DBスキーマ・マイグレーションは一切変更していないため、revertのみで完結する（不可逆操作なし）。

## 維持の仕組み
- 為替レートのSSOT性は ADR-148 とバックエンド `backend/app/routers/fx_rate_admin.py` が保証する。フロント側はレート値を一切ハードコードせず、常に `GET /fx-rate/USD` の現在値を使うため、レート更新（Celery Beatの1日2回UPSERT）が自動的に反映される。
- 換算ロジックを `toJpy` 1関数に集約し、表示箇所（ヒーロー・3テーブル・2チャート）はすべて `formatCost`/`formatConvertedCost` 経由で呼ぶ設計のため、将来コスト表示箇所が増えても二重実装・レート不整合が起きにくい。
- i18nキー対称性は `npm run check:i18n-missing-keys`（CI必須チェック）が継続的に保証する。

守り手: `frontend/src/pages/super-admin/components/LlmUsageSection.tsx`, `frontend/src/pages/super-admin/components/LlmUsageSection.test.tsx`, `backend/app/routers/fx_rate_admin.py`, `frontend/scripts/check-i18n-missing-keys.js`
