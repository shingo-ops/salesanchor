# design: PR 本文の見張りが、申請の作業の名前から作業場所を見つける

作成: 2026-10-27 Opus（Planner）。PO 承認: 2026-10-27「1」（古い見張りを直す。申請に書いてある作業の名前から作業用のフォルダを自分で探す。新しい見張りの守りは弱めない）。
参照: [recon.md](recon.md)・ADR-1033（見張りの正本と入れ替え）・ADR-1045（confidential-quote-guard）。

## 1. 目的（KGI）
本店で始めた会話から、`gh pr create --head <ブランチ> --body-file <絶対パス>`・`gh pr edit <番号> --body-file <絶対パス>` を単独で流したとき、pr-body-guard がそのブランチの worktree で本文を検証し、2 つの見張りの両方を通る。confidential-quote-guard は 1 文字も変えない。

## 2. 対象と対象外
- 対象: `docs/handoff/conversation-consent/hooks/pr-body-guard.sh`（正本）、`scripts/dev/test-agent-hooks.sh`（試験を足す）。
- 対象外: confidential-quote-guard（guard.py）・validate-pr-body.sh・extract-pr-body.py・settings.json・ほかの見張り。

## 3. 変更前後
- 変更前: 検証の場所 = フックの cwd、命令文に `cd <パス>` があればそのパス（`pr-body-guard.sh:85-99`）。
- 変更後: 上の決め方は**そのまま**。そのうえで、命令文に `cd` が無いときだけ、次の順で場所を足す。
  1. ブランチ名を決める。`gh pr create` は `--head <b>`・`--head=<b>`・`-H <b>`。`gh pr edit` は `edit` の次の位置引数（番号か PR の URL）を `gh pr view <それ> [-R <repo>] --json headRefName -q .headRefName` で引く（10 秒で打ち切り。`-R`/`--repo` が命令文にあれば渡す）。
  2. `git -C "$CWD" worktree list --porcelain` から `branch refs/heads/<b>` の行を持つ worktree を探す。**ちょうど 1 つ**見つかり、ディレクトリがあるときだけ、そこを検証の場所にする。標準エラーに `pr-body-guard: 作業場所を <ブランチ> の worktree <パス> にしました` を 1 行出す。
  3. 見つからない・2 つ以上・引けない・時間切れのときは、何もしない（変更前と同じ動き = 本店で検証して、足りなければ止まる）。
- 止める・通すの判定（validate-pr-body.sh の中身）は変えない。場所が正しくなるだけ。
- 本文の読み出し（extract-pr-body.py の `--body-file` 相対パス解決）は、worktree に切り替える**前**の場所（`BODY_CWD`）で行う。gh は命令を流した場所でファイルを読むため、検証も同じファイルを読む。（2026-10-27 審査 REVISE on 9c7b05adc の指摘: 相対パスだと worktree 側の別ファイルを検証して素通りする）

## 4. 代替案と選択理由
- A（採用）: pr-body-guard が `--head`／PR 番号から worktree を探す。理由: 検証は「そのブランチの中身」で行うのが本来の意味で、cd で示すのと同じ場所になる。守りは弱まらない（見つからなければ今までどおり止まる側）。
- B: confidential-quote-guard に `cd <絶対パス> &&` を許す。却下: ADR-1045 の設計が「命令文から作業場所を推し量る作りは直すたびに穴が開いた」（`docs/handoff/confidential-quote-guard/design.md:78`）として外した形を戻すことになる。PO も 2 を選んでいない。
- C: PO が手で申請を出す。却下: 毎回止まり、点検を飛ばす。

## 5. リスクと対処
- 違うブランチの worktree で検証してしまう → `branch refs/heads/<b>` の完全一致で 1 つに限る。
- `gh pr view` が遅い・失敗 → 10 秒で打ち切り、何もしない（止まる側）。
- worktree の中身が push 前と違う → cd で示すときと同じ条件。今回は変えない。
- 本物への入れ替えで壊れる → `po-apply-consent.sh --update` が試験不合格なら自動で戻す（`docs/handoff/conversation-consent/po-apply-consent.sh:1-6`）。

## 6. 受入条件
| 基準 | 検証方法 |
|---|---|
| K1 `gh pr create --head <b>` を cd なしで流すと、<b> の worktree で検証する | test-agent-hooks.sh の新しい試験: 一時 repo に worktree を作り（recon.md・design.md あり）、cwd を本体にして `--head <b>` で流すと標準エラーに「作業場所を」の行が出る |
| K2 見つからないブランチは今までどおり | 同じ試験で `--head no-such` のとき「作業場所を」の行が出ず、検証の場所は cwd のまま |
| K3 cd があればそちらが勝つ | `cd <パス> && gh pr create --head <b>` で「作業場所を」の行が出ない |
| K4 既存の試験が全部通る | `bash scripts/dev/test-agent-hooks.sh` が FAIL 0 |
| K5 本物で両方の見張りを通る | 入れ替え後、本店の会話から便9の `gh pr create --head release/loading-english-literal --body-file <絶対パス>` を単独で流し、PR ができる |
| K7 本文は元の場所で読む | 同じ試験で、worktree にだけ `rel.md` を置き cwd を本体にして `--body-file rel.md` を流すと「--body-file を読み込めない」で止まる |
| K6 confidential-quote-guard は不変 | 入れ替え前後で `shasum ~/.claude/scripts/confidential-quote-guard/guard.py` が同じ |

## 7. 進め方
1. 実装（クラウド Sonnet、card-1.md）→ push。
2. 審査役（reviewer・opus）が push した sha を審査。
3. PO が `!` で worktree の `po-apply-consent.sh --update` を実行（試験つき・不合格なら自動で戻る）。この PR 自身もこの直しが入らないと作れないため、入れ替えを PR より先にする。
4. PR を作る（K5 の確かめも兼ねる）→ CI → GO → 合流。

## 7a. 外部・過去事例
- 社内の前例: pr-body-guard の cd 補正（`pr-body-guard.sh:88-99`）は 10/15 に `~` を展開しない件で止まった（memory pr_body_guard_cd）。今回も「場所の決め方」の穴で、決め方を足す直し。
- 外部事例は使わない。理由: 社内の見張り 2 本の食い違いで、外の数値が判断に効かない。

## 8. 維持の仕組み
- 守り手: `scripts/dev/test-agent-hooks.sh`（K1〜K3 の試験を足す）。`po-apply-consent.sh --update` が入れ替えのたびにこの試験を流し、不合格なら戻す。
