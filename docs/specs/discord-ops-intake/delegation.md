# 委任表 — AI が承認なしで実行してよい操作（discord-ops-intake）

> この文書は何か：監視通知を受けた AI が「しんごさんの承認なしで自分の判断で実行してよい操作」の一覧です。ここに無い操作は、Discord の承認チャンネルのボタンが押されるまで実行されません。

親: [README.md](README.md)　／　KGI-3: [kgi.md](kgi.md)

---

## 運用ルール

- 委任を広げる・狭めるのは PO の言葉が起点。変更したら下の「変更履歴」に日時・PO の言葉・追加/削除した操作を 1 行で残す。
- この表は、受付用 worktree の Claude Code 許可設定（`.claude/settings.local.json` の `permissions.allow`）と**ツール単位で 1 対 1** にする。表と設定が食い違ったら、設定を表に合わせる。
- 書き込み系（Write・Edit・NotebookEdit）は `permissions.ask` に入れ、Claude Code が既定で通す書き込みも必ず許可確認にする（2026-10-13 実測: /tmp への Write が無確認で通った）。
- 受付の作業場所はリポジトリのクローンのため、リポジトリ共有設定（.claude/settings.json）の allow も効く。そのうち読み取り（git status/diff/log/branch/fetch/show、gh pr view/list/diff、gh run list/view、gh workflow view/list、gh issue view/list）は「読む」区分として認める。読み取り以外（scripts/ の実行・docker）は受付の settings.local.json の deny で塞ぐ（2026-10-13 配置時に発見）。
- [kgi.md](kgi.md) の「変えない約束」に挙がる操作は、この表に入れない。

## 現在の委任（第1段・初期値）

| 区分 | 承認なしで実行してよい操作 | 許可設定の行 |
|---|---|---|
| 読む | リポジトリのファイルを読む・検索する | Read / Grep / Glob（Claude Code の既定で許可されるため allow 行なし。1 対 1 の唯一の例外） |
| 読む | Git の履歴を読む | `Bash(git log:*)`・`Bash(git show:*)`（共有設定の allow により git status/diff/branch/fetch も読み取りとして可） |
| 読む | GitHub の状態を読む | `Bash(gh pr list:*)`・`Bash(gh run list:*)`・`Bash(gh run view:*)`（共有設定の allow により gh pr view/diff、gh workflow view/list、gh issue view/list も読み取りとして可） |
| Discord | 承認チャンネルに不具合スレッドを作る・書く・解決策を出す・読む・反応を付ける | `mcp__plugin_discord-ops_discord-ops__create_thread`・`__reply`・`__propose`・`__fetch_messages`・`__react`・`__list_monitor_alerts` |

初期値に**入れないもの**: 本番サーバーへの SSH（制限付き鍵でも）。必要になったら、許可コマンドの一覧を確認したうえで PO の言葉で追加する（独立レビュー MEDIUM-9）。

## 変更履歴

| 日時 | PO の言葉 | 追加 / 削除した操作 |
|---|---|---|
| 2026-10-13 | 「運用しながら担当範囲や権限委譲を行うのでその場合は自律的に判断して実行して良い」 | 初期値として上表を設定。SSH は初期値から外した（レビュー指摘） |
| 2026-10-13 | （配置時の不整合の是正。委任の拡大なし） | 共有設定 allow の読み取りを「読む」区分で認定。scripts/ 実行・docker を settings.local.json の deny で塞いだ |
