# guards.md — 停止ポイントの目次

> この文書は何か（専門用語なしの1行）:
> カードを出す前に「この作業なら、どのファイルを読むか」を引く目次。本文は guards/ 配下にある。

- 日付: 2026-09-07
- 使い方: 常設指示に置くのは本ファイルだけ。作業に対応するファイルを、下の順で読む。読んだファイル名を、カード冒頭に書き出す（書き出しの無い照合は、行われなかったものとみなす）。
- 追記: 新しい停止が起きたら、該当ファイルの末尾に1行足す。本ファイル（目次）は増やさない。

---

## 0. 原則

recon before write は、リポジトリと DB だけでなく、実行環境のガードと道具そのものにも適用する。

ガードは意図ではなく形で判定する。読み取りだけの SQL でも、ヘルプ表示でも、パターンに一致すれば止まる。

ガードに止められたら、回避策を考える前に「その語を使わずに済む方法」を探す。語の分割・エスケープ・別表記による回避は追いかけっこになり、長期的に必ず破綻する。回避が必要に見えるときは、目的の達成手段が間違っている可能性を先に疑う。

カードにプレースホルダを残さない。未確定の値は、それを作る手順を先に置く。

---

## 1. 作業ごとに読むファイル

| これから出すカードの作業 | 読むファイル（この順） |
|---|---|
| git・ファイルの読み取りだけ | guards/00-common.md → guards/01-read.md |
| 本番 DB を読む | guards/00-common.md → guards/01-read.md → guards/02-db.md |
| ファイルを作る・書き換える | guards/00-common.md → guards/01-read.md → guards/03-file.md |
| worktree・ブランチを作る | guards/00-common.md → guards/01-read.md → guards/04-worktree.md |
| PR を作る | guards/00-common.md → guards/04-worktree.md → guards/05-pr.md → guards/03-file.md |
| マージする | guards/00-common.md → guards/05-pr.md → guards/06-merge.md |
| migration を作る | guards/00-common.md → guards/02-db.md → guards/05-pr.md → guards/07-migration.md |
| VPS・SSH を触る | guards/00-common.md → guards/02-db.md → guards/08-vps.md |
| gh コマンドを使う | guards/00-common.md → guards/09-gh.md |
| 実行役が交代した | guards/10-executor.md |
| カードを出す前（毎回） | guards/11-lint.md の検査式に自分で通す |

---

## 2. 出所と未読

- 実測: CARD-GUARD-RECON-02（フック・スクリプト・関所の現物を1,523行で開示）。origin/main 916a7416 時点。
- 併記: 並行する全設計パートナーセッションからの停止事例 約60件。本セッションで裏を取っていないものは各ファイルに「未検証」と明記。
- 姉妹文書: card-ops.md（カードの書き方）。本書は「止まる場所」。
- 未読: check-process-artifacts.js は897行中200行のみ読了（201行付近・296行付近が未読）。~/.claude/agent-tokens.json の danger_ops 配列が未読。

---

## 3. 3段の関所

| 段 | 場所 | 何を止めるか | 状態 |
|---|---|---|---|
| 第1 | 設計パートナー | カードの形式・読了の書き出し・本書との照合 | 自己申告（弱い） |
| 第2 | 実行役のターミナル | UserPromptSubmit で card-lint.sh がカード全体を検査。各コマンドは PreToolUse の既存ガード | lint は未着手・PreToolUse は稼働中 |
| 第3 | GitHub の CI | process-artifacts gate ほか64本 | 稼働中 |

---

## 維持の仕組み

- 守り手: scripts/card-lint.sh（guards/11-lint.md を写したもの・未作成）。UserPromptSubmit フックに設置する。
- セッションの締めに、その便で起きた①カード不備の停止を、該当ファイルの末尾へ1行足す。同じ根の停止は統合する。
- 未検証の記述には出所と「本セッション未検証」を明記する。
- 1ファイルが40行を超えたら、そのファイルを目次に変え、項目ごとに孫ファイル（例: guards/02-db/01-connect.md）へ分ける。実測で積み上げた知見は削らない。
- 検査式にできたものは 11-lint.md へ移すが、元の場所には「検査式 L番号 で機械が止める」と1行残す。
- guards と正本（CLAUDE.md・STANDARD-WORKFLOW.md・design-partner.md）が食い違ったら、正本が優先。guards は補遺であり正本を上書きしない。食い違いを見つけたら、実測してから guards を直す。
