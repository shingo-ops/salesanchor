# 実装カード 段階3 便7a — ボタンの言葉を読み込み中に入れ替える三項を UI ガバナンス検査で赤にする

- 状態: Opus 作成・自己審査済み（同一AIの審査）。PO 承認: 方針 2026-10-23「1」、設計 2026-10-24「1」（design.md 3-3 便7・3-7）、便7 着手 2026-10-26「1」
- 起点: 最新 origin/main（便6b #4761 合流 90428a9b4 を含む）。ブランチ `release/loading-button-bin7a`
- 根拠: /tmp/CC報告ファイル/loading-button-bin7/recon/（check-ui-governance.js.txt・test-ui-governance.js.txt・fp-candidates.tsv・removed-keys-uniq.txt）、/tmp/CC報告ファイル/loading-button-recon/targets.tsv（段階3着手前 69721d365^1 時点の対象 134 件）
- 対象ADR: ADR-144（UI ガバナンス）・ADR-027
- 便7 の分け方（Opus 判断）: 便7a＝検査（本カード）。便7b＝使われなくなった辞書キーと CSS の片付け（別カード）。理由: 検査の追加と削除の片付けは、壊れ方も戻し方も違うため、1つずつ変える

## 1. 何を足すか
scripts/check-ui-governance.js に7つ目の種別 `loadingTernary` を足す。数える対象は、読み込み中の言葉と元の言葉を三項演算子で入れ替える式。ただし prop の値（`=` の直後の `{`）にあるものは数えない。

数える形（どれも 1 件と数える）:
- (A) `cond ? t("<読込キー>") : <何でも>`、または `cond ? <何でも> : t("<読込キー>")`
- (B) `t(cond ? "<読込キー>" : <何でも>)`、および逆順の形。テンプレート文字列 `` `${s}.saving` `` も、末尾がキーの判定に合えば数える
- (C) `cond ? "..." : <何でも>`、または `cond ? "…" : <何でも>`（文字列リテラルが `...` または `…` だけのもの）

読込キーの判定: キーを `.` で区切った最後の部分が、下の動詞の現在進行形の語を含むこと。比べるときは大文字小文字を区別しない。含むとは、最後の部分の先頭にあるか、直前が小文字で語頭が大文字になっていて、その語のあとが終わりか大文字であること。例: `saving`・`sendingEmail`・`lvStep7Loading`・`payTestRunning`。
- 語の一覧（定数 `LOADING_VERBS` としてファイルに置く）: saving, submitting, sending, loading, processing, testing, merging, confirming, running, connecting, disconnecting, reconnecting, changing, uploading, downloading, signingIn, searching, calculating, recalculating, exporting, importing, issuing, syncing, deploying, committing, checking, adding, deleting, updating, creating, registering, fetching, generating, applying, resetting, retrying, verifying, analyzing
- 理由: 段階3で消えた読込キーの最後の部分（removed-keys-uniq.txt）を全部含み、shipping・billing・pending・setting のような読み込みでない語を拾わないため

ui-allow: 既存の型どおり `hasUiAllowBefore` で除外する。

## 2. どのファイルを見るか（この種別だけ広げる）
- 今の検査は `PAGES_DIR` だけを見ている（:63-98）。`loadingTernary` だけは pages/・features/・components/ の .tsx を見る。除外は今と同じ（stories・design-system・design-preview）。試験ファイル（`.test.tsx`）も除外する
- 実装: `getChangedFiles(baseSha, headSha, dirs = [PAGES_DIR])` に引数を足す。既存6種別は今と同じ PAGES_DIR の一覧で数える。`loadingTernary` は3ディレクトリの一覧で数える。features/・components/ だけが変わった PR では、既存6種別は数えない（今と同じ動き）
- `pages/ への変更なし。スキップ` の早期終了（:396 付近）は、「3ディレクトリのどれにも変更がない」ときだけにする。メッセージも合わせて直す
- 理由: 既存6種別を components/ に広げると、金型の中身（生 select など）で赤になる。広げるのは新しい種別だけにする

## 3. 表示
- typeLabels に `loadingTernary: 'ボタン等の言葉を読み込み中に入れ替える三項 → 金型 Button の loading={条件} を使い、言葉は元のままにすること'` を足す。英語はいらない（既存に合わせる）
- 違反の見出し「新規の生UI部品を検出しました」は今のまま

## 4. 試験（scripts/tests/test-ui-governance.js）
既存の型で T45 以降を足す（`assert(説明, 実際, 期待)`）。最低限、次の形を入れる:
- 赤（1件）: (A) `{saving ? t("common.saving") : t("common.save")}`、逆順、(B) `{t(saving ? "productDetail.saving" : "productDetail.save")}`、テンプレート `` {t(saving ? `${s}.saving` : "common.save")} ``、(C) `{fetching ? "..." : t("x.fetchNow")}`、camel `t("discord.discordRoleSyncing")`
- 数えない（0件）: 規則3 の結果 `{existing ? t("common.update") : t("common.register")}`、prop `confirmLabel={x ? t("a.disconnecting") : t("a.disconnect")}`、prop `label={loading ? t("common.loading") : undefined}`、`{shipping ? t("a.shipping") : t("a.billing")}`、`{pending ? t("a.pending") : null}`、ui-allow 付きの (A)
- 広げた範囲: features/ だけが変わった場合に `loadingTernary` を数え、既存6種別は数えないことを、`getChangedFiles` の振り分けの関数単位の試験で確かめる（git を呼ばない形に関数を分けてよい）
- module.exports に `countLoadingTernary` と `LOADING_VERBS`、範囲を振り分ける関数を足す

## 5. 当たり外れの実測（生出力を /tmp/CC報告ファイル/loading-button-bin7a/impl/ へ）
- 取りこぼしなし: 段階3着手前の 69721d365^1 の時点で targets.tsv の 134 行が載っているファイルを `git show` で読み、`countLoadingTernary` で数える。ファイルごとに「数えた件数 ≧ targets.tsv のそのファイルの行数」になること。下回るファイルがあれば、その行と理由を miss.tsv に書いて BLOCKED:
- 拾いすぎの確認: 今の origin/main の pages/・features/・components/ の .tsx を全部数え、1件以上のファイルと行を now.tsv に書く。recon の fp-candidates.tsv（InboxMessageThread:850 の sr-only の span ほか）と照らし、ボタンでないものが何件あるか報告する。今ある分は差分方式なので赤にならないが、件数を残す
- 本体の動作: BASE_SHA=起点・HEAD_SHA=HEAD で本体を走らせて exit 0。わざと features/ の1ファイルに (A) を1つ足した一時 commit で exit 1 になることを確かめ、その commit は push しない。`git reset` は使わず、`git revert` か新しい commit で戻すか、別の使い捨て worktree で試す

## 6. 文書
- docs/CC_UI_GOVERNANCE.md:19-30 の禁止の表に1行足す。「ボタンの言葉を `{保存中 ? '保存中…' : '保存'}` のように入れ替える｜押している間は金型 Button の loading で丸を出し、言葉は元のまま（ADR-144・段階3）。pages/・features/・components/ を見る」
- design.md 3-7 の「検査:」の行を「検査: UI ガバナンス検査の loadingTernary（便7a）が、pages/・features/・components/ で増えたら赤にする」に書き換える。3-3 の便7 の行の下に「- 便7a（card-15）= 検査。便7b = 使われなくなった辞書キーと CSS の片付け。」を足す
- 本カードを docs/handoff/loading-indicator/card-15.md として同じ PR に入れる
- 台帳 .claude-pipeline/active-work.d/release-loading-button-bin7a.md

## 7. 触らない範囲
- .github/workflows/（ui-governance-gate.yml を含む。変えなくても新しい種別は今の job で走る）、既存6種別の数え方、frontend/src、辞書、CSS、金型

## 8. 検証
| 基準 | 検証方法 |
|---|---|
| 試験 | `node scripts/tests/test-ui-governance.js` が全件 pass（T1〜T44 は今のまま pass） |
| 取りこぼしなし | §5 の miss.tsv が 0 行 |
| 今の main で赤にならない | §5 の本体の動作で exit 0 |
| 増えたら赤 | §5 の一時 commit で exit 1、表示に loadingTernary の見出しが出る |
| 範囲 | `git diff origin/main...HEAD --name-only` が scripts/check-ui-governance.js・scripts/tests/test-ui-governance.js・docs/CC_UI_GOVERNANCE.md・design.md・card-15.md・台帳 だけ |

## 9. 想定分岐
- 既存の試験の書き方が関数の require で足りず、git を呼ぶ形しかない → 振り分けの部分だけ純粋な関数に分ける。それでも既存の試験を変える必要が出たら NEEDS_DECISION:
- 正規表現で (B) の逆順や、複数行に分かれた三項が取りにくい → 改行を含めて数える（`[\s\S]` を使う）。§5 の取りこぼしで確かめる
- 今の main の数え上げが 0 にならないファイルが pages/ にある（例 InboxMessageThread）→ 差分方式なので赤にはならない。そのまま件数を報告し、直さない
