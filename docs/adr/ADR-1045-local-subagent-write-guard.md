# ADR-1045: 手元の担当（サブエージェント）は、ファイルの書き換え・git の保存・GitHub への送り出しをフックで止める

| 項目 | 内容 |
|------|------|
| ステータス | Proposed（PO の決定 2026-10-26「１」。フックの登録は ADR-1011:39 により PO が `!` で実行する） |
| 備考 | PO 2026-10-26「1」重い実装と試験はクラウド、手元の担当は Mac の中を見る短い調べものだけ／「１」書き換え・保存・GitHub への上げを全部止める |
| 起案日 | 2026-10-26 |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-1029（マージ前の Opus 審査のフック。台本の置き方の前例）、ADR-1011（hooks は AI がパッチ、PO が反映）、ADR-1003（GO の Opus 委任） |
| 設計・根拠 | [design.md](../handoff/local-subagent-guard/design.md)、[recon.md](../handoff/local-subagent-guard/recon.md)、[cases.md](../handoff/local-subagent-guard/cases.md) |

---

## What（何を決めるか）

1. 手元の Mac の ~/.claude/settings.json の PreToolUse に、matcher `Write|Edit|MultiEdit|NotebookEdit|EnterWorktree|ExitWorktree|Bash|Monitor` の見張りを 1 つ足す。
2. 入力に `agent_id` がある（担当・fork・teammate の中の呼び出し）とき、Write・Edit・MultiEdit・NotebookEdit・EnterWorktree・ExitWorktree を止める。Bash・Monitor の命令では次を止める（design.md §5-3）。
   - git と gh の、「読むだけの一覧」（表A・表B）に無い使い方
   - 台本の実行（表C）。台本の名前の一覧は持たず、名前によらず止める
   - 別の AI（claude・codex とそのパッケージ）の起動（表D）
   - sudo・su・doas
3. `agent_id` が無い（Opus 本体）ときは何もしない。読むだけの命令は担当でも止めない（判定の例の正本は cases.md）。手元の generator も止まるので、generator はクラウド専用になる。担当の gh pr review も止まるが、マージの関所は VERDICT の行の記録で回る。
4. 台本と試験はリポジトリ（scripts/agent-hooks/local-subagent-guard/）に置き、CI（agent-hooks-test）で試験を流す。命令文の読み方はクラウドの見張り（scripts/agent-hooks/cloud/guard_pre_tool.py の scan_text・embedded_commands）を使い回す。

## Why（なぜ）

- PO の決定で、手元の担当の仕事は調べものだけになった。決まり（文書）だけでは破れるので、仕組みで止める。
- フックの入力には model が無く、`agent_id` は担当の呼び出しにだけ入る（公式文書と、この Mac の記録で担当 49/54 件・本体 131/51 件。recon.md §1・§2）。そのため model ではなく agent_id の有無で分ける。
- 審査役は SubagentHandback の文で結果を返すだけで、書き換えも commit も要らない。gh pr review の投稿も実際には使われていない（recon.md §3）。そのため例外の担当を作らずに一律に止められる。
- 「止める一覧」や「台本の名前の一覧」で守る形は、2 回の審査で漏れが見つかった。そのため「読むだけの一覧」と「台本は名前によらず動かさない」の形にした（design.md §6・§11）。

## 受け入れるリスク

- Bash の命令文での書き換え（`>`・`sed -i` など）は止めない。保存と送り出しが止まるので外には出ないが、本体と同じ作業場所の未保存の変更を上書きすることはありうる。
- 変数で組み立てた命令・隠した命令は見抜けない。
- 解釈系の中で書いた命令（`python3 -c` の中の subprocess など）と、GNU sed の `e` 命令は見抜けない（Mac 標準の sed には `e` が無い）。
- MCP の書き込み道具は対象外。
- 写した命令文の読み方（guard_pre_tool.py）は導入した時点の版で固まる。変わったら install し直す。
- 入力の JSON が読めないときは通す（本体を止めないため）。
- 文字の中の語（`echo "git push"`）でも担当は止まる。

## 戻し方

`bash scripts/agent-hooks/local-subagent-guard/rollback.sh` を PO が `!` で実行する（settings.json から 1 件を外し、写した台本を消す）。
