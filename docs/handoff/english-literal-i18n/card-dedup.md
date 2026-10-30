# 実装カード 重複確認の言葉をそろえる

- 状態: Opus 作成・自己審査済み（同一AIの審査）。PO 承認: 2026-10-30「1」（「重複確認待ち」にそろえる。会社の画面も同じ言葉）
- 起点: origin/main 92c376d52（ブランチ release/english-literal-dedup-label。worktree `/Users/tanizawashingo/worktrees/salesanchor/release-english-literal-dedup-label`。作業はこの中だけで行う）
- 設計: [design.md](design.md) §2-5（選択肢の訳を1組に）、現在地 [recon.md](recon.md)
- 対象ADR: ADR-027
- 調査の生出力: `/tmp/CC報告ファイル/english-literal-i18n/dedup/recon/`（base.txt・keys.txt・usage.txt・tests.txt）
- 現在地（origin/main 92c376d52）:
  - `frontend/src/locales/ja.json:1057` `customers.status_pending_dedup` =「重複確認待ち」/ en `"Pending Dedup Review"`（会社の札と選択肢）
  - `frontend/src/locales/ja.json:1175` `contacts.statusPendingDedupOption` =「pending_dedup_review（重複確認待ち）」/ en `"pending_dedup_review (pending dedup)"`（連絡先の編集の選択肢。`ContactEditPage.tsx:192`・`ContactFormFields.tsx:43`）
  - `frontend/src/locales/ja.json:1196` `contacts.statusCode.pending_dedup_review` =「重複確認中」/ en `"Pending Review"`（連絡先の札。`statusPresentation.ts:169`・`MergeContactModal.tsx:233`）
  - 同じ状態なのに、画面により「重複確認待ち」「重複確認中」「pending_dedup_review（重複確認待ち）」の3つの書き方がある
  - 試験は言葉の値を見ていない（`statusPresentation.test.ts:144` はキーの名前だけ）。tests.txt で「重複確認中」「Pending Review」「pending dedup)」を期待する試験は0件
- Opus の設計判断:
  - 判断1: 連絡先の札の言葉を会社と同じ「重複確認待ち」/ "Pending Dedup Review" にする
  - 判断2: 連絡先の選択肢から保存値の英語 `pending_dedup_review` を外し、「重複確認待ち」/ "Pending Dedup Review" にする。理由: 画面に英語の保存値が出ており、このテーマ（画面の英語をなくす）の対象。会社の選択肢（`CompanyFormFields.tsx:32`）は既に言葉だけで、PO の「そろえる」に当たる
  - 判断3: キーの名前・保存値・コードは変えない。辞書の値だけを変える（別キーへの付け替えは、使う所が4ファイルに増え影響が広がるため採らない）

## 1. 直す所（辞書の値だけ）

| ファイル:行 | 変更前 | 変更後 |
|---|---|---|
| `frontend/src/locales/ja.json:1175` | `"statusPendingDedupOption": "pending_dedup_review（重複確認待ち）",` | `"statusPendingDedupOption": "重複確認待ち",` |
| `frontend/src/locales/en.json:1175` | `"statusPendingDedupOption": "pending_dedup_review (pending dedup)",` | `"statusPendingDedupOption": "Pending Dedup Review",` |
| `frontend/src/locales/ja.json:1196` | `"pending_dedup_review": "重複確認中"` | `"pending_dedup_review": "重複確認待ち"` |
| `frontend/src/locales/en.json:1196` | `"pending_dedup_review": "Pending Review"` | `"pending_dedup_review": "Pending Dedup Review"` |

- 行がずれていたら同じ文字の行を直す。他の行は変えない（行末のカンマ・字下げもそのまま）

## 2. 触らない範囲
- 辞書の他のキー（`leads.*`・`customers.*`・`reviewStatusPending`・`importPendingReview` など同じ英語の別の言葉）
- `.ts`/`.tsx` のコード・試験・バックエンド・`frontend/api-contract/openapi.json`
- 文書: design.md・recon.md

## 3. 実測（生出力は `/tmp/CC報告ファイル/english-literal-i18n/dedup/impl/`。クラウドでは作業場所の中の同名フォルダで可）
- 最初に `cd frontend && npm ci`
- 残りが0: `git grep -n '重複確認中' HEAD -- frontend/src` が0行。`git grep -n 'pending_dedup_review（\|pending dedup)' HEAD -- frontend/src/locales` が0行
- 辞書: `npm run check:i18n-missing-keys` exit 0
- JSON の形: `node -e "JSON.parse(require('fs').readFileSync('src/locales/ja.json','utf8'));JSON.parse(require('fs').readFileSync('src/locales/en.json','utf8'))"` exit 0
- 流す: `npx vitest run src/utils/statusPresentation src/components/MergeContactModal src/pages/contacts`

## 4. 検証
| 基準 | 検証方法 |
|---|---|
| 「重複確認中」が残っていない | §3 の grep が0行 |
| 保存値の英語が選択肢に出ない | §3 の grep が0行 |
| 辞書が壊れていない | check:i18n-missing-keys と JSON の形が exit 0 |
| 既存の試験が壊れない | §3 の vitest が通る |
| 範囲 | `git diff origin/main...HEAD --name-only` が辞書2つ・本カード・台帳だけ |
| CI | PR の必須の検査がすべて緑 |
| 本番 | 反映後の画面の JS に「重複確認中」が0件 |

## 5. 想定分岐
- 既存の試験が「重複確認中」や "Pending Review" を期待していて赤 → 試験の名前と失敗の文を保存し NEEDS_DECISION:
- check:i18n-missing-keys が今回と関係ない所で赤（origin/main でも赤） → origin/main の結果も保存して報告。直さない
