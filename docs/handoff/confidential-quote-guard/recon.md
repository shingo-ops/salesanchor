# recon — 社外秘の原文の書き写しを送る前に止める（confidential-quote-guard）

- 基準: origin/main ebab342eb（2026-10-25）
- 設計: [design.md](design.md)
- 審査: 同一 AI（Opus）の自己審査。独立した第二者レビューではない。
- この文書には、仕入元名・投稿の原文・投稿 id を書かない。件数とパスだけを書く。

## 0. 既存 ADR・仕組みの検索

| 探したもの | 結果 | 根拠 |
|---|---|---|
| 「社外秘」を含む ADR | 1 件。ADR-1043 が「正解表は Mac にしかなく、社外秘なので公開リポジトリに置けない」と書く | `docs/adr/ADR-1043-accuracy-gold-in-db.md:21` |
| 「confidential」を含む ADR | 0 件 | git grep -il confidential origin/main -- docs/adr |
| FEATURE-INDEX の社外秘・confidential | 0 件 | `docs/adr/FEATURE-INDEX.md` を grep |
| 秘密情報の検査 | あるが、鍵やトークンの「形」を見るもので、原文との照合はしない | `.github/workflows/secret-scan.yml`、`.gitleaks.toml`、`docs/adr/ADR-075-github-secrets-only-policy.md` |
| 個人側の見張りの正本の決まり | ある。PO のあるべき姿は「見張りの中身の変更は PR と GO で管理され、勝手に変わらない」。原本を repo に置く前例は review-gate | `docs/specs/local-hooks-ssot/ideal-state.md`、`scripts/agent-hooks/review-gate/install.sh` |
| PR 本文の見張り | PR 本文と recon・design の書式とバッククォート内のパスの実在を見る。「」の中は見ない | `scripts/dev/validate-pr-body.sh:50-87`、`scripts/dev/validate-pr-body.sh:243-273` |

## 1. 何が起きたか（2026-10-25）

- 設計書の PR を 3 回出した（#4727・#4729・#4730）。前の 2 回は、仕入元の投稿の文面の切れ端を「」で引用していたため、審査で REVISE になり閉じた。
- 切れ端は、PR を出す前の `git push` の時点で公開された。このリポジトリは公開設定（gh repo view の visibility が PUBLIC）。
- 閉じた PR の中身は GitHub の refs/pull/4727/head と refs/pull/4729/head に残る（git ls-remote で確認）。PO の判断（2026-10-25「2」）で、残った分はそのままにし、再発防止だけ作る。
- 決まり自体は覚え書きにあった（「repo の設計書には集計値と file:line だけを書く」）。書いたあとに照らす仕組みが無かった。

## 2. 送る前の見張りの今の形

- 見張りは Mac のホームの設定（~/.claude/settings.json）の PreToolUse:Bash に並ぶ。順は worktree-only-guard.sh → agent-danger-hook.sh → worktree-access-guard.sh → gh-scope-guard.sh → pr-body-guard.sh → ほか（担当の調べ。生出力 /tmp/CC報告ファイル/confid-guard-recon/hooks.txt）。
- pr-body-guard.sh は `gh pr create`／`gh pr edit` に `--body`／`--body-file` が付くときだけ動き、止めるときは exit 2。git push では動かない。
- 見張りのスクリプト置き場（~/.claude/scripts）は git 管理ではない。変更の跡は .bak とバックアップのフォルダで残す運用。テストは ~/.claude/scripts/tests/ に 4 本あり、標準入力に JSON を渡して動かす形。
- 状態の言葉の一覧は repo に無い（状態マスタは本番 DB）。過去に取った写しが社外秘フォルダにある。

## 3. 社外秘の原文の置き場

- ~/CC報告ファイル-keep/ 直下に 139 項目。accuracy-20261024 は 55,472 行・約 11.6MB。
- 投稿の原文そのものが入るのは、accuracy-20261024 では design-prep/R2-raw/msgs_*.tsv（3 列目）と new-posts/check3/msgs/*.txt（111 件）。合わせて 120 ファイル・約 2.9MB。
- ほかにも原文がありそうなフォルダが 17 ある（accuracy-20261014 など。中身は未確認）。
- 分析の出力（判定の表・集計）も同じフォルダにあり、そこには自分たちの言葉も混じる。照合の相手を「投稿の原文だけ」に絞らないと、自分の言葉で止まる。

## 4. 試し（Mac 内で実施。語句は表示せず件数だけ）

照合の決まり: 追加した行の「」の中の語句で、4 文字以上、状態の言葉の一覧に無く、原文 120 ファイルにそのまま現れるものを数える。

| 記録 | 止まる語句の数 | 期待 |
|---|---|---|
| #4727 のコミット 79ec6fa76 | 10 | 止まる |
| #4729 のコミット f13e335fb | 1 | 止まる |
| #4730 のコミット 18060e58f（審査合格） | 1 | 通る |

- #4730 で止まった 1 語は、状態の一般語（ダメージの有無の言い方）で、状態の言葉の写しに同じ書き方が無かった。一般語の除外表を足せば 0 になる。
- 照合の時間は 1 回 0.4 秒（担当の time の値）。
- 既存の docs と backend/tests 全体に当てた結果は §4-1。

### 4-1. 既存の書類に当てた結果

- 対象: origin/main の docs/ と backend/tests/ の .md・.py・.sql・.txt・.json、4,322 ファイル。
- 止まる語句があったファイル: 182。止まる語句（ファイルごとに数えた延べ）: 479。語句の種類: 324。
- 324 種類を形で仮分けした結果（語句は書かない）:

| 仮の分け方 | 種類 | 延べ |
|---|---|---|
| 数字と区切りだけ（年・個数など） | 14 | 17 |
| 商品名・シリーズ名・一般の言葉 | 170 | 266 |
| 投稿の書き写しに見えるもの（値段・発送や入荷の案内・〆の行・在庫数・見出しの飾り・店の名前など） | 140 | 196 |

- 仮分けは機械の目印（記号や「発送」「在庫」などの言葉）による。1 種類ずつの判定はまだしていない（便1 で行う。design §4 K3）。
- 分かったこと:
  1. 4 文字以上・原文に現れる、だけでは商品名や一般の言葉でも止まる（170 種類）。除外表に商品名を入れないと誤って止まる。
  2. main の書類には、すでに書き写しに見える語句が約 140 種類ある。今回の試しで初めて分かった。
  3. 見張りは「送る差分で足した行」だけを見るので、既にある行は、その行を書き換えない限り止まらない。
- 生出力は社外秘フォルダ（Mac 内）にだけ置く。

## 5. 不明点

| # | 内容 | 扱い |
|---|---|---|
| 1 | 17 フォルダのどれに投稿の原文があるか | 実装の便で、原文の置き場を 1 か所に決める（design §3） |
| 2 | 閉じた PR の中身を GitHub から消せるか | PO の判断で対象外（そのまま残す） |
| 3 | main の書類にある書き写しに見える約 140 種類をどうするか | PO に判断を求める（§4-1 の 2） |
