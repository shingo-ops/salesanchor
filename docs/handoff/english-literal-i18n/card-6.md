# 実装カード 便6 — 通信とエラーの英語を辞書の言葉にする

- 状態: Opus 作成・自己審査済み（同一AIの審査）。PO 承認: 設計・訳・実装 2026-10-29「1」
- 起点: 作成時の origin/main（ブランチ release/english-literal-error-text。worktree `/Users/tanizawashingo/worktrees/salesanchor/release-english-literal-error-text`。作業はこの中だけで行う）
- 設計: [design.md](design.md) §2-6・K1、現在地 [recon.md](recon.md) §6
- 対象ADR: ADR-027、ADR-144
- 調査の生出力: `/tmp/CC報告ファイル/english-literal-i18n/bin6/recon/`（api.ts・string_e_ctx.txt・dict_keys.txt・i18n_usage.txt・message_display.txt・http_dep.txt）
- Opus の設計判断:
  - 判断1: 設計の例 `common.error.http` は使えない（`common.error` は既に「エラー」という文字の値で、下にキーを置けない）。代わりに `common.httpError` を足す。値は ja「リクエストに失敗しました（{{status}}）」、en「Request failed (HTTP {{status}})」。既存の `common.requestFailed`（リクエストに失敗しました / Request failed）と言葉をそろえた
  - 判断2: 状態番号は文の中に残す。`TypeMasterPanel.tsx:139` の `e.message.includes("409")` が番号で判定しているため
  - 判断3: `api.ts:132`・`:189` の `new Error(\`HTTP ...\`)` は、読み比べると利用者に届かない（最後の回は `attempt < maxRetries` が偽になり `!res.ok` の ApiError に進む。ループの後の `throw lastError` に来るのは TypeError の続きだけ）。それでも英語の直書きなので、同じキーにする。`useInboxState.ts:348` の `/^HTTP 50[23]/` の枝は、ApiError の 502/503 を1つ目の枝が先に拾うため、効き目は変わらない。`useInboxState.ts` は触らない
  - 判断4: 設計の5か所に加え、同じ形の `frontend/src/lib/auth/selfAuth.ts:23` も直す（設計の対象の数え漏れ。中身は同じ「詳しい理由が無いときの言葉」）
  - 判断5: `String(e)` 11か所（e が Error でないものを投げたときだけ出る）は、`common.unknownError` を足してそれにする。値は ja「不明なエラーが発生しました」、en「An unknown error occurred」。既存の共通キーには「理由の分からないエラー」を表す1語が無い（`common.error` は「エラー」の1語で、単独で出す画面（DiagnosticsDrawer など）では意味が伝わらない）
  - 判断6: 保存値・通信の中身・ApiError の status と responseDetail は変えない。エラーの class も変えない

## 1. 直す所（行は 30943c0d0 頃の origin/main のもの。ずれていたら同じ文字の行を直す）

| ファイル:行 | 変更前 | 変更後 |
|---|---|---|
| `frontend/src/lib/api.ts:132` | `new Error(\`HTTP ${res.status}\`)` | `new Error(i18n.t("common.httpError", { status: res.status }))` |
| `frontend/src/lib/api.ts:143` | `: detail?.detail \|\| \`HTTP ${res.status}\`;` | `: detail?.detail \|\| i18n.t("common.httpError", { status: res.status });` |
| `frontend/src/lib/api.ts:189` | `:132` と同じ | `:132` と同じ |
| `frontend/src/lib/api.ts:194` | `body \|\| \`HTTP ${res.status}\`` | `body \|\| i18n.t("common.httpError", { status: res.status })` |
| `frontend/src/lib/api.ts:230` | `\|\| \`HTTP ${res.status}\`;` | `\|\| i18n.t("common.httpError", { status: res.status });` |
| `frontend/src/lib/auth/selfAuth.ts:23` | `super(detail ?? \`HTTP ${status}\`);` | `super(detail ?? i18n.t("common.httpError", { status }));`（同じファイルの既存の `i18n` の import を使う。無ければ NEEDS_DECISION:） |
| `frontend/src/features/tcg-analysis-review/DiagnosticsDrawer.tsx:52` | `e instanceof Error ? e.message : String(e)` | `e instanceof Error ? e.message : t("common.unknownError")` |
| `frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx:70`・`:77` | 同上 | 同上 |
| `frontend/src/features/tcg-analysis-review/SupplierQualityList.tsx:47` | 同上 | 同上 |
| `frontend/src/features/tcg-distribution/DistributionPreview.tsx:34`・`:50` | 同上 | 同上 |
| `frontend/src/features/tcg-distribution/DistributionTargetForm.tsx:91`・`:119` | 同上 | 同上 |
| `frontend/src/features/tcg-distribution/DistributionTargetList.tsx:46`・`:59` | 同上 | 同上 |
| `frontend/src/features/tcg-distribution/DistributionWorkspace.tsx:37` | 同上 | 同上 |

- 上の 11 か所で `t` がその場で使えない（部品の外の関数・`useCallback` の依存に `t` が無く lint が止める等）ときは、依存に `t` を足すのは可。それ以外の形の変更が要るときは NEEDS_DECISION:
- `{{status}}` は i18next の差し込み（既存の `i18n.t` の使い方と同じ）

## 2. 辞書
- `frontend/src/locales/ja.json` と `en.json` の `common` に2つ足す（既存の `common.requestFailed` の近く）
  - `common.httpError`: ja「リクエストに失敗しました（{{status}}）」 / en「Request failed (HTTP {{status}})」
  - `common.unknownError`: ja「不明なエラーが発生しました」 / en「An unknown error occurred」
- 既存のキーの値は変えない。消すキーは無い

## 3. 触らない範囲
- `useInboxState.ts`・`TypeMasterPanel.tsx`・`authErrorMessage.ts`・試験の入力に `"HTTP 500"` などを使っている既存の試験（`ReviewCsvPanel.test.tsx:86`・`authErrorMessage.test.ts:39`・e2e `error-scenarios-502-429.spec.ts:105`）
- バックエンド・`scripts/`・`.github/workflows/`・stories
- 文書: design.md・recon.md

## 4. 実測（生出力は `/tmp/CC報告ファイル/english-literal-i18n/bin6/impl/`）
- 最初に `cd frontend && npm ci`
- 残りが0: `git grep -n 'HTTP \${' HEAD -- frontend/src/lib` が0行。`git grep -n 'String(e)' HEAD -- 'frontend/src/*.tsx' ':!*.test.tsx'` が0行
- 検査: `BASE_SHA=<merge-base> HEAD_SHA=HEAD node scripts/check-ui-governance.js` exit 0
- 辞書: `npm run check:i18n-missing-keys` exit 0
- 試験を足す: `frontend/src/lib/api.httpError.test.ts`（既存の `lib/api.no-double-prefix.test.ts` の fetch の差し替え方に合わせる）。detail が空の 409 の応答で、投げられる ApiError の status が 409、message が `i18n.t("common.httpError", { status: 409 })` と同じで `"409"` を含むこと。日本語の文字は試験に書かない
- 流す: `npx vitest run src/lib src/features/tcg-analysis-review src/features/tcg-distribution src/pages/inbox src/pages/super-admin/components/TypeMasterPanel* src/features/tcg-review-csv`
- 全体: `npm run lint`・`npx tsc --noEmit`（既存4件だけ）・unit 全体（揺れたら揺れたファイルだけ流し直した結果も保存）

## 5. 検証
| 基準 | 検証方法 |
|---|---|
| 英語が残っていない | §4 の grep が0行 |
| 状態番号の判定が壊れない | 新しい試験で message に "409" が入る |
| 既存の試験が壊れない | 対象の試験と unit 全体が通る |
| 範囲 | `git diff origin/main...HEAD --name-only` が §1 のファイル・辞書2つ・試験1つ・本カード・台帳だけ |
| CI | PR の必須の検査がすべて緑 |
| 本番 | 反映後の画面の JS に「不明なエラーが発生しました」が入っている |

## 6. 想定分岐
- 既存の試験が `HTTP 4xx` などの message の文面を期待していて赤 → 試験の名前と失敗の文を保存し NEEDS_DECISION:
- `i18n.t` の型が `{ status: number }` を受けず tsc が赤 → 保存し NEEDS_DECISION:
- 11か所のどれかが部品の外で `t` を持たない → 保存し NEEDS_DECISION:
- check:i18n-missing-keys が今回と関係ない所で赤（origin/main でも赤） → origin/main の結果も保存して報告。直さない
