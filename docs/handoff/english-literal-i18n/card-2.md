# 実装カード 便2 — 一覧表の部品（DataTable）の英語を辞書の言葉にする

- 状態: Opus 作成・自己審査済み（同一AIの審査）。PO 承認: 設計・訳・実装 2026-10-29「1」、便2 の着手 2026-10-29「1」（一覧表の部品の英語を直す）
- 起点: origin/main a2bf75a7c。ブランチ release/english-literal-datatable（手元で本カードと台帳を commit して push 済み。その上に積む）
- 設計: [design.md](design.md) §2-2・§5、現在地 [recon.md](recon.md) §3-1
- 対象ADR: ADR-027（文字は t() 経由・ja.json と en.json は同じキー）、ADR-144
- 実行場所: クラウド。push までを行う。PR は手元で作る（scripts/agent-hooks/cloud/rules.md）
- 調査の生出力: `/tmp/CC報告ファイル/english-literal-i18n/bin2/`（手元。行番号は a2bf75a7c と同じ）
- Opus の設計判断:
  - 判断1: 空の表示は既存の `common.noData`（ja「データなし」/ en「No data」）を使う。design.md §2-2 は `common.dataTable.*` と書いたが、同じ意味のキーを2つ作らない（辞書の SSOT）。en は今の表示と同じ
  - 判断2: 読み上げ名（aria）は新しいキー `common.dataTable.*` を作る。en の値は今の英語と1文字も変えない（小文字のまま）。理由: 英語で探している試験4本（§3）を書き換えずに通すため。ja だけが新しい日本語になる
  - 判断3: `t()` に `defaultValue` を付けない。英語の直書きが別の形で残るため。試験は i18n を初期化して en にする
  - 判断4: 閲覧ページ（`frontend/src/pages/viewer/InventoryView.tsx:758`）も DataTable を使う。閲覧ページは自分の辞書（`frontend/src/pages/viewer/i18n.ts:8-9`）だけを読むので、同じキーを閲覧ページの辞書にも入れる（4ファイル）。`frontend/scripts/check-i18n-missing-keys.js` の決まりと同じ
  - 判断5: `prevPageLabel = '‹'`・`nextPageLabel = '›'`（`:163-164`）は記号なので変えない。`String(row[col.key] ?? '')`（`:327`・`:441`）は空文字なので変えない

## 1. 直す所

### 1-1. `frontend/src/components/DataTable.tsx`
- `import { useTranslation } from 'react-i18next';` を足し、関数の先頭で `const { t } = useTranslation();`
- 11か所を次のとおり置き換える（行は a2bf75a7c のもの）

| 行 | 変更前 | 変更後 |
|---|---|---|
| 257 | `aria-label="previous page"` | `aria-label={t('common.dataTable.previousPage')}` |
| 269 | `aria-label="next page"` | `aria-label={t('common.dataTable.nextPage')}` |
| 290 | `aria-label="data table"` | `aria-label={t('common.dataTable.table')}` |
| 292 | `{emptyState ?? 'No data'}` | `{emptyState ?? t('common.noData')}` |
| 321 | `` aria-label={`select row ${key}`} `` | `aria-label={t('common.dataTable.selectRow', { key })}` |
| 350 | `aria-label="select all"` | `aria-label={t('common.dataTable.selectAll')}` |
| 355 | `aria-label="select all rows"` | `aria-label={t('common.dataTable.selectAllRows')}` |
| 404 | `{emptyState ?? 'No data'}` | `{emptyState ?? t('common.noData')}` |
| 434 | `` aria-label={`select row ${key}`} `` | `aria-label={t('common.dataTable.selectRow', { key })}` |
| 468 | `aria-label="data table"` | `aria-label={t('common.dataTable.table')}` |
| 482 | `aria-label="data table"` | `aria-label={t('common.dataTable.table')}` |

### 1-2. 辞書（4ファイル。`common` の中に足す。既存のキーは変えない）
`frontend/src/locales/ja.json`・`frontend/src/locales/en.json` には `common.dataTable` だけを足す（`common.noData` は既にある）。`frontend/src/locales/viewer/ja.json`・`frontend/src/locales/viewer/en.json` には `common.noData` と `common.dataTable` の両方を足す。

| キー | ja | en |
|---|---|---|
| common.noData（閲覧ページの辞書だけに足す） | データなし | No data |
| common.dataTable.previousPage | 前のページ | previous page |
| common.dataTable.nextPage | 次のページ | next page |
| common.dataTable.table | データ表 | data table |
| common.dataTable.selectAll | すべて選択 | select all |
| common.dataTable.selectAllRows | すべての行を選択 | select all rows |
| common.dataTable.selectRow | {{key}} の行を選択 | select row {{key}} |

### 1-3. 試験 `frontend/src/components/DataTable.test.tsx`
- 先頭で `import i18n from '../i18n';` し、`beforeAll(async () => { await i18n.changeLanguage('en'); })`。既存の期待値（`:83`・`:89`・`:97`・`:104`・`:113`）は変えない
- 末尾に足す（describe を1つ。終わりに en へ戻す）:
  - ja にして、`data=[]`・emptyState なしで描くと「データなし」が出る
  - ja にして、ページ送りありで描くと、名前「次のページ」のボタンがある
  - ja にして、selectable で描くと、名前「すべての行を選択」のチェックボックスと「2 の行を選択」がある
  - en にして、`data=[]`・emptyState なしで「No data」が出る
  - `emptyState={<span>空です</span>}` を渡すと「空です」が出て「データなし」は出ない

## 2. 触らない範囲
- DataTable の props・DOM・クラス名・`data-testid`
- DataTable を使う画面（77か所・60ファイル）。emptyState を渡す35か所はそのまま
- 他の試験（§3 の3本は書き換えない。通ることだけ確かめる）
- `scripts/`・`.github/workflows/`・`DataTable.stories.tsx`
- 文書: design.md・recon.md・本カード

## 3. 実測（生出力は `/tmp/CC報告ファイル/english-literal-i18n/bin2/impl/`。無ければ作る。主な結果は報告に書く）
- 最初に `cd frontend && npm ci`
- 残りが0: `grep -nE "previous page|next page|data table|select all|select row|'No data'" frontend/src/components/DataTable.tsx` が0行
- 検査の件数: origin/main に対し `BASE_SHA=origin/main HEAD_SHA=HEAD node scripts/check-ui-governance.js` exit 0。`countEnglishUiLiteral` を DataTable.tsx にかけて 0 件
- 辞書: `cd frontend && npm run check:i18n-missing-keys` exit 0。4つの JSON が `node -e 'JSON.parse(...)'` で読める
- 試験: `cd frontend && npx vitest run src/components/DataTable.test.tsx src/components/DataTable.bin1.test.tsx` と、英語の名前で探している3本（`NeedsReviewTabsPanel.timing.test.tsx`・`ProductMasterPanel.test.tsx`・`InventoryPage.rowdrawer.test.tsx`。場所は `git ls-files` で探す）と `InventoryView.test.tsx`
- 全体: `cd frontend && npm run lint`・`npx tsc --noEmit`（package.json の型検査の命令があればそれ）・unit の試験全体

## 4. 検証
| 基準 | 検証方法 |
|---|---|
| 英語が残っていない | §3 の grep が0行・countEnglishUiLiteral 0 件 |
| 辞書のキーがそろう | check:i18n-missing-keys exit 0 |
| ja で日本語・en で今と同じ | §1-3 の追加試験が通る |
| 既存の試験が壊れない | §3 の試験・unit 全体が通る |
| 範囲 | `git diff origin/main...HEAD --name-only` が DataTable.tsx・DataTable.test.tsx・辞書4つ・本カード・台帳だけ |
| CI | PR の必須の検査がすべて緑 |
| 画面（反映後・PO） | 0件の一覧表で「No data」が「データなし」になっている |

## 5. 想定分岐
- 英語で探している試験が §3 の3本以外にも赤 → その試験の名前と失敗の文を保存し NEEDS_DECISION:（期待値を自分で書き換えない）
- i18n を初期化していない試験で、キー名（`common.dataTable.*`）が見えて赤 → 同じく NEEDS_DECISION:
- `../i18n` の import が試験で動かない（読み込みの失敗） → 動いている例（`ProductMasterPanel.test.tsx:6-10`）の書き方に合わせる。それでも駄目なら BLOCKED:
- 閲覧ページの辞書に `common` が無い・形が違う → BLOCKED:（今は `common` に close など5件ある）
- check:i18n-missing-keys が今回と関係ない所で赤（origin/main でも赤） → origin/main での結果も保存して報告。直さない
