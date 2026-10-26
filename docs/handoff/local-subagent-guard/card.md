# 作業指示書 — 手元の担当の書き換え・保存・送り出しを止める見張り（ADR-1045 便1）

- 状態: 発行済み（設計 第7.2版。第8回の審査 APPROVE on acff149f9。発行は POの委任に基づく Claude Opus）
- 枝: `release/local-subagent-guard-design`（PR #4795 に足す。新しい枝・PR は作らない）
- 実行する場所: クラウド（Sonnet）。push まで。PR の本文の更新・マージ・導入は手元の本体が行う
- 正本: [design.md](design.md) §5・§8、[cases.md](cases.md)、試作 [proto_judge.py](proto_judge.py)
- 読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・03-file.md・04-worktree.md・12-guard-authoring.md
- 受領確認: 着手したら最初に「受領確認: card.md 第7.2版・HEAD の 1 行」を出力する
- 停止: 迷ったとき・§5 の分かれ道で止まるときは、作業をやめて `BLOCKED: 理由` か `NEEDS_DECISION: 問い` を最後の行に書いて報告を返す（推測で続けない。報告先は起動した本体）

## 1. 作るもの（これ以外のファイルは触らない）

| ファイル | 中身 |
|---|---|
| scripts/agent-hooks/local-subagent-guard/guard.py | design.md §5-2 の入口（JSON の読み・agent_id・道具の名前・import の失敗・止める文・log）と、§5-3 の判定。§5-3 の判定は proto_judge.py の関数を写す（判定の中身を変えない） |
| scripts/agent-hooks/local-subagent-guard/test_guard.sh | design.md §8 の K1〜K8 を確かめる。cases.md の全例（止める 263・通す 218）を Bash と Monitor の両方で当てる。本物の ~/.claude には触れない（HOME は mktemp -d） |
| scripts/agent-hooks/local-subagent-guard/install.sh | design.md §5-5。scripts/agent-hooks/review-gate/install.sh と同じ型（冪等・バックアップ・JSON の確認後に置き換え） |
| scripts/agent-hooks/local-subagent-guard/rollback.sh | design.md §5-5。review-gate/rollback.sh と同じ型。log は消さない |
| .github/workflows/agent-hooks-test.yml | job `local-subagent-guard` を 1 つ足す（下の §3）。既存の job `review-gate` と on: は変えない |

触らないもの: scripts/agent-hooks/cloud/ 全部（guard_pre_tool.py は import して使うだけ）、scripts/agent-hooks/review-gate/ 全部、docs/ の全部（このカード・design.md・cases.md・proto_judge.py・ADR を含む）、~/.claude、.claude/agents/。

## 2. guard.py の作り方（変更前→変更後）

- 変更前: ファイルは無い。
- 変更後:
  1. 先頭で design.md §5-2「guard_pre_tool の読み込み」のとおり、`os.path.dirname(os.path.abspath(__file__))`（guard.py のある場所）を sys.path に入れ、そこに guard_pre_tool.py が無ければ、その場所の `../cloud` も入れて import する。失敗は例外を覚えておくだけ（その場で止めない）。
  2. proto_judge.py の定数と関数（GIT_READ 〜 judge まで）を、そのまま写す。proto_judge.py 冒頭の sys.path の行と `import guard_pre_tool as g` は 1. に置き換える。判定の式・集合・順番は変えない。
  3. main(): design.md §5-2 の手順 1〜5 をこの順で書く。止めるときは exit 2 と stderr の 1 行（§5-2 の文をそのまま。山括弧の 2 か所に agent_type の値と規則名を差し込む）。log は `~/.claude/logs/local-subagent-guard.log` に「UTC 時刻・agent_type・tool_name・規則名」をタブ区切りで 1 行。命令文は書かない。log に書けない例外は握りつぶして止めることは続ける。
  4. Python 3 の標準ライブラリだけ。`python3 -I guard.py` で動くこと。

## 3. CI の job（足す分）

```yaml
  local-subagent-guard:
    name: local-subagent-guard hook test
    runs-on: ubuntu-latest
    timeout-minutes: 10
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v5
      - name: Run local-subagent-guard tests
        run: bash scripts/agent-hooks/local-subagent-guard/test_guard.sh
```

ファイル冒頭の注釈に「scripts/agent-hooks/local-subagent-guard/ (ADR-1045) の受入試験。docs/handoff/local-subagent-guard/design.md §8。」を 1 行足す。

## 4. test_guard.sh の作り方

- cases.md の取り出し方: `## 止める例` と `## 通す例` の見出しの後のコード枠の中を 1 行 1 例。`\n`（バックスラッシュと n の 2 文字）は改行 1 文字に置き換え、ほかの `\` はそのまま。取り出しは python3 の小さな式で行ってよい。
- 入力 JSON は python3 の json.dumps で作る（命令文の引用符を壊さないため）。担当の入力は `{"agent_id":"t1","agent_type":"general-purpose","tool_name":"Bash","tool_input":{"command":…}}`、本体の入力は agent_id を除いたもの（K2 は空文字の agent_id も試す）。
- K6 ②: 一時ディレクトリに guard.py だけを写して起動する。
- K8: HOME=mktemp -d に空の `{}` の settings.json と、別のフックの項目 1 つを置いて、install を 2 回・rollback を 1 回流す。install.sh が `git rev-parse HEAD` を使うので、リポジトリの中から流す。
- 最後に「合格 N / 不合格 M」を出し、不合格が 1 つでもあれば exit 1。

## 5. 実物の点検と想定の分かれ道

- 最初に `git log --oneline -1` が PR #4795 の最新（docs: local-subagent-guard design v7.2 …）であることを確かめる。違えば止まって報告（BLOCKED:）。
- 写した guard.py に cases.md の全例を当てて、proto_judge.py と結果が 1 件でも違えば、guard.py を直す（試作が正）。試作の側が cases.md と合わない例が見つかったら、直さずに止まって報告（NEEDS_DECISION:）。
- ubuntu の CI で `/private/tmp` が無いことによる失敗は、試験の作りの側で直す（判定は変えない）。
- review-gate/install.sh の型が design.md §5-5 と食い違う点があれば、design.md を正にする。

## 6. 終わり方

- `bash scripts/agent-hooks/local-subagent-guard/test_guard.sh` の出力の最後の 5 行と、`git diff --stat origin/release/local-subagent-guard-design` を報告に貼る。
- commit は 1 つ: `feat: local-subagent-guard hook (ADR-1045 便1)`。push は `git push origin HEAD:release/local-subagent-guard-design`。
- force push・rebase・PR の作成と編集・マージはしない。

END OF CARD
