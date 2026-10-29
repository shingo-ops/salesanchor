# 実装カード 便1 — 新しい英語の直書きを UI ガバナンス検査で止める

- 状態: Opus 作成・自己審査済み（同一AIの審査）。PO 承認: 2026-10-29「1」（選択肢の言葉は日本語にそろえ、この案で進める）
- 起点: origin/main d9b0c1771348e9c740eeff1eb662221d029436a6。ブランチ release/english-literal-i18n（手元で recon.md・design.md・本カード・ADR-027 追記・台帳を commit して push 済み。その上に積む）
- 設計: [design.md](design.md) §2-1・§5・§7、現在地 [recon.md](recon.md) §2
- 対象ADR: ADR-027（文字は t() 経由・2026-10-29 追記）、ADR-144（ui-allow の書式）
- 実行場所: クラウド。push までを行う。PR は手元で作る（scripts/agent-hooks/cloud/rules.md）
- Opus の設計判断:
  - 判断1: ESLint の規則ではなく、差分方式の `scripts/check-ui-governance.js` に種別を足す。理由: 今ある英語の直書き（約85か所）を編集するたびに止めない。増えた分だけ止める（`:773`）
  - 判断2: 構文解析の道具は使わない。理由: CI（`.github/workflows/ui-governance-gate.yml:27-38`）は依存を入れず node だけで動く。今ある `maskSource`（`:510`）の写しの上で数える
  - 判断3: 対象は .tsx だけ（今の `getChangedFiles` `:96` と同じ）。.ts の英文は後の便で grep で確かめる
  - 判断4: 誤って数えにくい3つの形だけを数える（§1-2）。拾えない形があることは design.md §6 に限界として書いてある

## 1. 直す所（`scripts/check-ui-governance.js` だけ）

### 1-1. 種別の追加
- 定数: `ENGLISH_LITERAL_DIRS = [PAGES_DIR, FEATURES_DIR, COMPONENTS_DIR]`（`LOADING_TERNARY_DIRS` `:45` と同じ中身。別名にして意味を分ける）
- `splitTargets`（`:111-119`）の戻り値に `englishFiles` を足す。条件は loadingFiles と同じ（3つのディレクトリ・.test.tsx を除く）。既存の legacyFiles・loadingFiles は変えない
- `main`（`:734-740`）: `englishPaths` を作り、`changedFiles` の条件に足す。`:742` の件数表示に英語の件数を足す
- `countAll`（`:707-717`）に `englishUiLiteral: countEnglishUiLiteral(content)` を足す
- `typeLabels`（`:760-768`）に `englishUiLiteral: '英語の直書き → t("key") を使い、ja.json と en.json に同じキーを足すこと（固有名詞も t() を通す。ADR-027 追記）'`
- `:770` の配列に `'englishUiLiteral'` を足し、`:772` の範囲の判定を「loadingTernary は loadingPaths、englishUiLiteral は englishPaths、ほかは legacyPaths」にする
- `module.exports`（`:829-847`）に `countEnglishUiLiteral` を足す
- ファイル冒頭の説明（`:1-30`）に種別の1行を足す

### 1-2. `countEnglishUiLiteral(content)` の数え方
`const { masked, strings } = maskSource(content)` を使う。英語の語は `/[A-Za-z]{2,}/`。各当たりは、その行か直前の行に有効な ui-allow があれば数えない（`hasUiAllowBefore` `:144`、行は `getLineIndex` `:137`）。

- (A) 属性の文字列: `strings` の各要素について、`masked.slice(0, s.start)` の末尾が `/\b(aria-label|placeholder|title|alt|label)=\{?\s*$/` に合い、`s.value` に英語の語がある（quote が `` ` `` のものは数えない）
- (B) JSX の文字: `masked` で `/>([^<>{}]*)</g` の当たりのうち、次のすべてを満たすもの
  - `>` の直前の文字が `=` でも `-` でもない（`=>`・`->` を除く）
  - 中身に `( ) ; = & | ?` を含まない
  - `<` の直後が `/` か英字
  - 中身に英語の語がある
- (C) 英文の既定値: `strings` の各要素について、`masked.slice(0, s.start)` の末尾が `/(\?\?|\|\|)\s*$/` に合い、`s.value` に空白と英語の語の両方がある（例 `?? 'No data'`。`?? 'primary'` は数えない）
- 1つの文字列が (A) と (C) の両方に当たっても1件と数える

## 2. 試験（`scripts/tests/test-ui-governance.js`。既存の `assert(説明, 実際, 期待)` `:35` の書き方に合わせて末尾に足す）
数える（期待 1）:
- `<span>No data</span>`
- `<input aria-label="Close" />`
- `<input placeholder={"Search..."} />`
- `{emptyState ?? 'No data'}`
- `<p>Send failed</p>`（直前の行に `{/* ui-allow: x */}`＝番号なしで書式不正 → 除外されず 1）
数えない（期待 0）:
- `<span>{t("common.noData")}</span>`
- `<input aria-label={t("common.close")} />`
- `const f = (a) => a > 0 && b < c;`
- `useState<string>("")`
- `{variant ?? 'primary'}`
- `<div className="foo bar">中身</div>`
- `<p>送信に失敗しました</p>`
- `{/* ui-allow: 固有名詞の見本 (#1) */}` の次の行の `<span>No data</span>`
- `// <span>No data</span>`（コメント）
- `splitTargets` に .test.tsx を渡すと englishFiles に入らない

## 3. 実測（生出力は `/tmp/CC報告ファイル/english-literal-i18n/bin1/`。無ければ作る。主な結果は報告に書く）
- 基準値: origin/main の `frontend/src/{pages,features,components}` の .tsx（.test.tsx・.stories.tsx・design-system・design-preview を除く）すべてに `countEnglishUiLiteral` をかけ、合計件数と、件数の多い順に上位20ファイルを保存する（一度だけの node の式でよい。スクリプトは commit しない）
- 当たり確認: recon.md §3-1 の `frontend/src/components/DataTable.tsx` が 1 件以上数えられている
- 止まる確認（実装を commit したあとに行う）: ブランチを動かさずに試す。`frontend/src/pages/` の任意の .tsx に `<span>Temporary text</span>` を1行足して `git add` し、`git commit-tree $(git write-tree) -p HEAD -m tmp` で枝に付かない commit を作る。`BASE_SHA=HEAD HEAD_SHA=<その sha> node scripts/check-ui-governance.js` が exit 1 になり englishUiLiteral の行が出ることを確かめる。そのあと `git restore --staged --worktree <そのファイル>` で戻し、`git status` が空であることを確かめる（reset・stash は使わない）

## 4. 触らない範囲
- `.github/workflows/`（必須チェックの名前も変えない）
- 既存の7種別の数え方と対象ディレクトリ
- `frontend/`（画面・辞書・ESLint 設定）。英語の直書きそのものは直さない（便2〜6）
- 文書: recon.md・design.md・本カード・ADR-027 は手元で commit 済み。中身を変えない

## 5. 検証
| 基準 | 検証方法 |
|---|---|
| 試験 | `node scripts/tests/test-ui-governance.js` exit 0（§2 の追加込み） |
| 今ある分で止まらない | `BASE_SHA=origin/main HEAD_SHA=HEAD node scripts/check-ui-governance.js` exit 0 |
| 増えたら止まる | §3 の止まる確認で exit 1、戻したあと `git status` が空 |
| 範囲 | `git diff origin/main...HEAD --name-only` が `scripts/check-ui-governance.js`・`scripts/tests/test-ui-governance.js`・docs/handoff/english-literal-i18n/ の3ファイル・ADR-027・docs/adr/README.md・台帳だけ |
| CI | PR の UI governance gate が緑 |

## 6. 想定分岐
- 基準値の合計が 300 を超える → 誤って数えている形がある。上位20ファイルの当たり行を10件保存し NEEDS_DECISION:（数え方を広げたり狭めたりを自分で決めない）
- 基準値で DataTable.tsx が 0 件 → 数え方の誤り。BLOCKED:（当たらなかった行の中身を添える）
- 既存の試験が赤 → 既存の種別を壊している。BLOCKED:
- `maskSource` が JSX の文字まで文字列として隠してしまい (B) が当たらない → BLOCKED:（どの行で起きたか）
- 止まる確認の一時の変更が commit に混ざった → 戻さずに報告して BLOCKED:
