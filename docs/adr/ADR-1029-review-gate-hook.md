# ADR-1029: AI のマージは、その PR の今の HEAD に Opus 審査役の APPROVE 記録が無ければフックで止める

| 項目 | 内容 |
|------|------|
| ステータス | Proposed（KGI R1〜R7 は PO 合意 2026-10-18。フックの登録は ADR-1011:39 により PO が `!` で実行する） |
| 備考 | PO 2026-10-18「これをhookで矯正してくれ、工程を飛ばすことなくopusに審査を依頼すること」 |
| 起案日 | 2026-10-18 |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-1011（許可の自律保守。hooks は AI がパッチ、PO が反映）、ADR-1003（GO の Opus 委任）、ADR-136（危険 PR の GO 手順）、ADR-1015（開発フロー） |
| 設計・根拠 | [design.md](../handoff/review-gate-hook/design.md)、[recon.md](../handoff/review-gate-hook/recon.md) |

---

## What（何を決めるか）

1. 審査役（subagent_type `reviewer`、model opus）は、報告の最後の行を `VERDICT: <APPROVE|REQUEST_CHANGES|REJECT> on <40桁のHEAD sha> PR #<番号>` にする。
2. PostToolUse のフック（SubagentHandback に当てる）が、審査役の報告（`tool_input.message`）からこの行を読み、meta.json の model が opus で、sha がその PR の今の HEAD と同じで、判定が APPROVE のときだけ `~/.claude/review-gate/records/` に記録する。
3. PreToolUse のフックが、AI の Bash のマージ操作（先頭の語には頼らず、区切りの中に `gh pr merge`・`gh-pr-merge-safe.sh`（番号は `.pr-number` から読む）・`check-pr-merge-ready.py`・`gh api` の merge・`curl` の `api.github.com` の merge）を見つけたら、その PR の今の HEAD の記録が無ければ止める。番号が取れない・gh が失敗した・command が読めないときも止める。`--auto` は `--match-head-commit` が記録の HEAD と同じときだけ通す。
4. 同じフックが、記録の置き場と記録台本への Bash・Write/Edit を止め、審査役を opus 以外の model で起動するのを止める。
5. 関所はユーザー設定なので全リポジトリにかかる。そのため ~/.claude/agents/reviewer.md にも同じ決まりを足す。
6. フックの台本と試験はリポジトリ（scripts/agent-hooks/review-gate/）に置き、`scripts/agent-hooks/**` が変わる PR では CI で試験を流す。
7. （追補 2026-11-01・PO「１」）shingo-ops/salesanchor の PR は、3 の照合が通った後に `gh pr checks <番号> --json name,bucket` を読み、必須でない確かめも含めて全部が pass か skipping でなければ止める（fail・pending・cancel・知らない値）。一覧が読めない・空・JSON でないときも止める。終了コードは見ない。ほかのリポジトリには、かけない。設計: [design.md](../handoff/merge-red-check-guard/design.md)、[recon.md](../handoff/merge-red-check-guard/recon.md)。

## Why（なぜ）

- 「マージ前に reviewer の APPROVE」は決まり（文書）だけで、仕組みでは強制されていなかった。マージの入口（scripts/dev/check-pr-merge-ready.py:195-198 ほか）は CI 緑と HEAD 固定だけを確かめる（recon.md §3）。
- 審査役は SubagentHandback で報告を返し、last_assistant_message は 161 件中 154 件で空だった（recon.md §2）。公式も報告は SubagentHandback の `tool_input.message` で読むとする（recon.md §1）。そのため、報告本文の決まった形の 1 行で判定と sha を受け渡す。
- sha を記録に入れることで、審査後に HEAD が変わったら同じ記録では通らない。
- （What 7）2026-10-31 に、必須でない確かめ（test-schema-dup gate）が赤いまま 22 件が本線に入った。正規の合流の道（scripts/dev/check-pr-merge-ready.py:100-101）は赤のある PR を止めるが、直接の合流の命令はこのフックが審査の記録だけを見て通していた（merge-red-check-guard/recon.md §1・§2）。道によって基準が違う状態をなくすため、フックでも同じ基準で止める。

## 受け入れるリスク

- GitHub の画面からのマージ、Actions の自動マージ（.github/workflows/ledger-auto-done-main.yml）はフックの外。
- Bash の難読化（変数で組み立てる・eval 等）は見つけられない。試験台本 test_review_gate.sh をリポジトリ側で書き換えて、例外の実行から本物の置き場へ書かせる道も同じ扱いで止めない。
- `gh` の別名（gh alias）経由のマージは見つけられない（今の別名は `co: pr checkout` の 1 件だけ・recon.md §3）。台本ファイルを作ってから実行する形（中に merge を書いた .sh を後で `bash x.sh`）も見つけられない。
- glob（`cd …/review-gat*` 等）で置き場へ移る形は、難読化と同じ扱いで見つけられない。
- 止める側に倒したもの: `bash -c $'…'`、`python`・`perl` 等の `-c`/`-e` の本文やヒアドキュメントに単語としての merge を含むもの、`GH_REPO`・`GH_HOST` の代入がある command のマージ、`popd` 後のマージ、here-string（`<<<`）で shell 等へ merge を渡す形、`xargs` の後ろのマージ、`--repo`・`--match-head-commit` の重ね書き、URL と `--repo` の食い違いは、中身や照合先を確かめられないので止める（design.md §5-3(d)）。
- Branch Protection・Ruleset は変えない（PO 指定の対象外）。
- ~/.claude/settings.json・~/.claude/scripts/ の書き換え、~/.claude/projects 下への偽の会話記録・meta.json の作成は、このフックでは止めない（ADR-1011 の自己変更の決まりに依る）。
- 審査役（opus）に中身を見ずに APPROVE を書かせる指示は止められない（審査役の起動指示の質に依る）。
- （What 7）画面からの合流と台帳の自動合流は、確かめの色でも止まらない（上の 1 行目と同じ）。作業画面アプリ（GEN-RYU-System/agent-console）は今の運用で赤のまま合流しているため対象外（merge-red-check-guard/recon.md §5）。本線が赤い間は関係のない PR も AI は合流できない（本線の赤を先に直す）。

## 戻し方

`bash scripts/agent-hooks/review-gate/rollback.sh` を PO が `!` で実行する（settings.json から 2 件を外し、~/.claude/agents/reviewer.md に足した節を外す）。
What 7 だけを戻すときは、その実装 PR を revert し、PO が install.sh を `!` でもう一度実行する。
