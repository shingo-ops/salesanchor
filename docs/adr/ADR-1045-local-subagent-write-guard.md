# ADR-1045: 手元の担当（サブエージェント）は、ファイルの書き換え・git の保存・GitHub への送り出しをフックで止める

| 項目 | 内容 |
|------|------|
| ステータス | Proposed（PO の決定 2026-10-26「１」。フックの登録は ADR-1011:39 により PO が `!` で実行する） |
| 備考 | PO 2026-10-26「1」重い実装と試験はクラウド、手元の担当は Mac の中を見る短い調べものだけ／「１」書き換え・保存・GitHub への上げを全部止める |
| 起案日 | 2026-10-26 |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-1029（マージ前の Opus 審査のフック。台本の置き方の前例）、ADR-1011（hooks は AI がパッチ、PO が反映）、ADR-1003（GO の Opus 委任） |
| 設計・根拠 | [design.md](../handoff/local-subagent-guard/design.md)、[recon.md](../handoff/local-subagent-guard/recon.md) |

---

## What（何を決めるか）

1. 手元の Mac の ~/.claude/settings.json の PreToolUse に、matcher `Write|Edit|MultiEdit|NotebookEdit|Bash` の見張りを 1 つ足す。
2. 入力に `agent_id` がある（担当の中の呼び出し）とき、Write・Edit・MultiEdit・NotebookEdit を止める。Bash では git の保存・送り出し（commit・push・merge・rebase・cherry-pick・revert・am・tag）と GitHub への書き込み（gh pr create/merge/comment など・gh api の書き込み）を止める。
3. `agent_id` が無い（Opus 本体）ときは何もしない。読むだけの命令は担当でも止めない。
4. 台本と試験はリポジトリ（scripts/agent-hooks/local-subagent-guard/）に置き、CI（agent-hooks-test）で試験を流す。命令文の読み方はクラウドの見張り（scripts/agent-hooks/cloud/guard_pre_tool.py の scan_text）を使い回す。

## Why（なぜ）

- PO の決定で、手元の担当の仕事は調べものだけになった。決まり（文書）だけでは破れるので、仕組みで止める。
- フックの入力には model が無く、`agent_id` は担当の呼び出しにだけ入る（公式文書と、この Mac の記録で担当 49/54 件・本体 131/51 件。recon.md §1・§2）。そのため model ではなく agent_id の有無で分ける。
- 審査役は SubagentHandback の文で結果を返すだけで、書き換えも commit も要らない（recon.md §3）。そのため例外の担当を作らずに一律に止められる。

## 受け入れるリスク

- Bash の命令文での書き換え（`>`・`sed -i` など）は止めない。保存と送り出しが止まるので外には出ない。
- 変数で組み立てた命令・隠した命令は見抜けない。
- 入力の JSON が読めないときは通す（本体を止めないため）。
- 文字の中の語（`echo "git push"`）でも担当は止まる。

## 戻し方

`bash scripts/agent-hooks/local-subagent-guard/rollback.sh` を PO が `!` で実行する（settings.json から 1 件を外し、写した台本を消す）。
