# design: LLM 使用量ダッシュボードUI（PR-B）

作成日: 2026-10-01　起案: Claude Opus（設計）／実装: Claude Sonnet
関連: [recon.md](./recon.md)

## 1. 目的（PO）

Gemini 呼び出しのどこで・どれだけコスト/トークンを使っているかを画面で見て、その使い方が適切か PO が判断できるようにする。データ SSOT は `public.llm_usage_events`（ADR-1004）。

## 2. ADR 相互参照

- ADR-1004（llm-usage-ledger）: データの出どころ・列定義・NULL 方針の正本。本PRはこの台帳を**読むだけ**（書き込みロジックには触れない）。
- ADR-027（i18n）: 全文字列 `t()` 経由、ja/en キー同一。
- ADR-067（デザイントークン）: 色・サイズのハードコード禁止。
- ADR-144（UIガバナンス）: 既存金型（Card/DataTable）のみ使用、生 select/input 禁止。

## 3. Backend 設計

### 3.1 エンドポイント

`GET /api/v1/tcg/analysis-dashboard/llm-usage?days=N`（`N` は 1〜360、既定 30）

- 認可: `Depends(require_super_admin)`（recon §3 の既存パターンと同一）
- 読み取り対象: `public.llm_usage_events` のみ。`WHERE occurred_at BETWEEN NOW() - INTERVAL '1 day' * :days AND NOW()`
- 4本の SELECT: `total`（全期間合算1行）・`by_purpose`（purpose別、cost_usd DESC NULLS LAST）・`by_model`（model別、cost_usd DESC NULLS LAST）・`daily`（日別、JST DATE_TRUNC、date DESC）
- トークン列・cost_usd は `SUM()` のみ（`COALESCE` を使わない）→ そのグループで SDK が一度も値を返さなかった場合、列は `NULL`（Optional）のまま返す。0 と推測しない（ADR-1004 の方針を踏襲）。
- `calls` は `COUNT(*)`（Optional にしない・常に int）。

### 3.2 日付バケットの選択（design 上の判断・recon §3 参照）

同ファイル内の `cost-summary`（`daily`）は `DATE(ea.started_at)`（TZ変換なし）を使うが、同ダッシュボードの「トレンド」系エンドポイント（`import-trend`/`trend`。実体は `tcg_analysis_dashboard_svc.py` の `get_import_trend`/`get_pipeline_trend`）は `DATE_TRUNC('day', ... AT TIME ZONE 'Asia/Tokyo')`（JST固定）を使う。

**本PRは JST DATE_TRUNC 側を採用した。** 理由: 本タブの `daily` は「日別トレンド」という性格が cost-summary の付随集計より trend 系エンドポイントに近く、TZ を明示しない `DATE()` はセッションTZ依存で本番/テスト間の挙動差リスクがあるため。cost-summary 自体は変更しない（設計スコープ外）。

### 3.3 レスポンスモデル

`LlmUsageResponse { total, by_purpose[], by_model[], daily[] }`。フィールドはカード本文の指定どおり（`docs/handoff/llm-usage-ui/recon.md` 不要、カード本文＝設計）。実装: `backend/app/routers/tcg_analysis_dashboard.py`。

## 4. Frontend 設計

### 4.1 タブ追加（最小差分）

`AnalysisDashboardPanel.tsx` への変更は3点のみ:
1. `DashboardTab` 型に `"usage"` を追加
2. `tabItems` に `{ key: "usage", label: t("analysisRules.dashboard.tabUsage") }` を追加
3. `{activeTab === "usage" && <LlmUsageSection days={trendDays} t={t} />}` を追加

期間セレクタ（`trendDays`）は既存実装で全タブ共通表示（recon §5）のため追加変更不要。

### 4.2 新規コンポーネント `LlmUsageSection.tsx`

- 単独で `api.get()` を呼び、loading/error/empty を既存タブ（`ImportTabContent` 等）と同じパターンで扱う。
- レイアウト: `Card variant="metric"` ×4（費用合計／呼び出し回数／入力トークン／出力トークン）→ `DataTable`（by_purpose）→ `DataTable`（daily）→ `DataTable`（by_model）。すべて既存金型（`Card`/`DataTable`）のみ。
- 出力トークン = `candidates_tokens + thoughts_tokens`。両方 NULL のときのみ「記録なし」、どちらか一方でもあれば合算値を表示（0 として加算）。
- NULL 表示: 各セル・カードで `null` の場合は `t("analysisRules.dashboard.usage.notReported")`（ja: 記録なし / en: Not reported）。
- 使いみちラベル: `analysisRules.dashboard.usage.purpose.<code>`。未知の purpose はコード文字列をそのまま表示（フォールバック、ハードコード日本語なし）。
- 費用フォーマット: `new Intl.NumberFormat(i18n.language, { style: "currency", currency: "USD", minimumFractionDigits: 4, maximumFractionDigits: 4 })`。
- 新規 CSS: `analysis-dashboard-section-note`（説明文用、既存トークン `--font-sm`/`--text-muted`/`--space-4` のみ使用）を `AnalysisDashboardPanel.css` に追加。新規 `.css` ファイルは作らなかった（既存ファイルへの4行追加で足りたため）。

## 5. 受入条件

| 基準 | 検証方法 |
|---|---|
| ① タブが表示され、4枚のメトリクスカード＋3つの表が出る | `LlmUsageSection.test.tsx` のレンダーテスト＋目視（Storybook対象外のため） |
| ② 値が同じ days で `public.llm_usage_events` を集計した SQL と一致する | `test_tcg_analysis_dashboard_llm_usage.py` で SQL に `llm_usage_events` のみ含まれ `extraction_attempts`/`extraction_shadow_runs` を含まないことを assert |
| ③ NULL は「記録なし」と表示される | `test_tcg_analysis_dashboard_llm_usage.py`（バックエンドの NULL 伝播）＋ `LlmUsageSection.test.tsx`（フロントの「Not reported」描画） |
| ④ ja/en のキーセットが同一 | `npm run check:i18n-missing-keys` PASS（実行済み・後述） |
| ⑤ 生 select/input・インラインカラーが無い | 目視 diff（`LlmUsageSection.tsx` は `Card`/`DataTable` のみ使用）＋ `npm run check:css-colors`/`check:css-values` PASS |
| ⑥ backend の days 範囲外（0, 361）が 422 | `test_llm_usage_days_out_of_bounds_returns_422`（parametrize 0/361）PASS |

## 6. 外部・過去事例

該当なし（社内専用の管理画面タブ追加であり、公開事例を要する新規パターンではない。既存の `cost-summary`／`import-trend` エンドポイントと同型のため、社内の既存実装を横展開した）。

## 7. 維持の仕組み

- 守り手: `backend/tests/test_tcg_analysis_dashboard_llm_usage.py`（SQL対象テーブル・NULL伝播・days境界）、`frontend/src/pages/super-admin/components/LlmUsageSection.test.tsx`（NULL表示・ラベル・通貨フォーマット）。
- CI: `npm run check:i18n-missing-keys`／`check:css-colors`／`check:css-values`／`check:css-class-naming`／`check:jsx-emoji`（既存 CI ワークフローに組み込み済みのため個別追加不要）。
- 台帳側（書き込み・列追加等）の変更は ADR-1004 の管轄。本タブは読み取り専用のため、台帳のスキーマ変更時は本エンドポイントのレスポンスモデルも合わせて見直す必要がある（既知のリスク・別PRで対応）。
