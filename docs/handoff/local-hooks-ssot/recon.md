# recon — 個人側検問の正本化（local-hooks-ssot）

この文書は何か（専門用語なしの1行）: 実装者のパソコンで動く検問5本が、いま何本動き、何を止め、リポジトリの正本とどれだけずれているかを、実測だけで書いた現状報告。

親（設計仕様書）へのリンク: ../../specs/local-hooks-ssot/README.md

- 仕事名: local-hooks-ssot
- 日付: 2026-09-07
- 実測時の origin/main SHA: a984735808aedafdcf6336a7414c669b09d4ca21（機体側ファイルは同日 23:40 JST 時点。§1 の repo 側 settings.json のみ f156bccf 時点）
- 対象ADR: ADR-042（Claude Code 運用ガードレール強化）／関連: ADR-074（Worktree 強制によるエージェントPR混入防止）
- 担当: 設計パートナー（実測は実装役カード H-01〜H-05 の生出力による）
- 区分（STANDARD-WORKFLOW 1.8）: 既存の延長・修正（索引登録済み・あるべき姿とKGI承認済み 2026-07-20・recon 未作成）

---

## 0. 既存ADR検索の結果

- `git grep -il -E "hook|guard|PreToolUse|worktree|検問" -- docs/adr/` → 30件（head 上限に達したため全件ではない。SHA 9a197df8 時点）: ADR-018・024・025・026・029・034・035・038・039・042・046・069・074・075・077・082・086・089・091・095・098・101・107・114・116・119・131・132・134・136。
- `docs/adr/FEATURE-INDEX.md:42`: 「Claude Code 運用ガードレール / SessionStart hook」→ ADR-042。
- ADR-042（2026-05-19 Accepted）: `.claude/settings.json` の deny/ask 不在・PR ベースブランチ検証不在・main 保護不在を、運用ルール明文化＋機械的ガードレールで解決すると決定。
- ADR-074（2026-05-26 Accepted）: 並行エージェントのPR混入を worktree 強制で防ぐと決定。worktree-only-guard.sh の根拠。
- ADR-114: worktree 自動掃除（dev-continuity recon 柱2 が参照）。

事実: 機体側 hook 5本の中身・変更手順・記録形式を定めたADRは、本検索の範囲では見つかっていない。ADR-042 は「hook を置く」ことを決めたが、「hook の正本をどこに置き、どう一致を保つか」は決めていない。

---

## 1. 全体像（5本の検問と配線）

機体側 `~/.claude/settings.json` の hooks（実測 H-02）:

- PreToolUse／Bash: worktree-only-guard.sh → agent-danger-hook.sh → worktree-access-guard.sh → gh-scope-guard.sh の順
- PreToolUse／Read・Glob・Grep: worktree-access-guard.sh
- PreToolUse／Edit・Write: worktree-only-guard.sh → worktree-access-guard.sh
- PreToolUse（matcher なし）: agent-start-hook.sh（async）
- Stop: agent-stop-hook.sh

repo 側 `.claude/settings.json`（59行・f156bccf）: hooks は SessionStart の2本（check-freshness.sh・stop-log-digest.sh）のみ。PreToolUse は0件。permissions.allow は読み取り系 git/gh と一部スクリプトに限定。

事実: 危険操作を機械的に止める検問は、機体側にのみ存在する。repo を別の機体で開いた場合、検問は1本も掛からない。

---

## 2. 各検問の現在値

| 検問 | README 07-20 実測 | 今回実測 | 状態 | repo 内の原本 |
|---|---|---|---|---|
| worktree-only-guard.sh | 144行 | 48行 | 稼働。08-26 に用途ごと書き換え（先頭コメント「develop/main 直コミット・保護ブランチ force push・古い clone の push/fetch を止める」） | ledger-guard/artifacts/worktree-only-guard.v2.sh（144行）。diff は先頭から相違 |
| agent-danger-hook.sh | 107行 | 242行 | 稼働。.bak が 08-31・09-04 の2世代 | なし |
| worktree-access-guard.sh | 128行 | 128行 | 稼働（本文は先頭15行のみ確認） | なし |
| gh-scope-guard.sh | 330行 | 331行 | **無効**（2行目に `exit 0`。08-31 PO許可・guard-disabled-record.md） | なし |
| agent-start-hook.sh | 133行 | 133行 | 稼働（本文未読） | なし |

agent-danger-hook.sh が止めるもの（実測 H-03・H-04）:

- `~/.claude/agent-tokens.json` の `danger_ops` 17件との部分一致: DROP TABLE／DROP DATABASE／rm -rf／git push --force／git push -f／git reset --hard／DELETE FROM／TRUNCATE／git push origin main／git push origin develop／rm -r／git push -u origin main／git push -u origin develop／git push origin HEAD:main／git push origin HEAD:develop／git rebase／clasp push
- salesanchor スコープ限定: psql へのファイル流し込み5パターン（ssh+psql <・-f・pipe・docker+psql <・-f）と、`-c` 内の書き込みSQL
- `~/.claude/permits/` への直接アクセス
- 使い捨て許可: `scripts/permit-danger.sh`（repo 内・実在）で1回・30分

事実: `danger_ops` の定義は repo のどこにも文書化されていない（`git grep danger_ops -- docs/ scripts/` は dev-continuity recon の言及1件と check-stale-worktrees.sh の話者ID読み出しのみ）。

事実: agent-danger-hook.sh・worktree-access-guard.sh・gh-scope-guard.sh の3本は、先頭コメントが「exit 1: ブロック」と書き、実装は `exit 2` で止めている（Claude Code の仕様上、阻止は exit 2）。実装が正しく、説明が古い。

---

## 3. 記録の現在値

`~/.claude/logs/agent-events.jsonl`: 11,213,758 バイト（09-06 23:40）。danger_detected の行は type／session／branch／op／ts を持つ。「なぜ止めたか」は op 名（例: `psql-write:pipe to psql`）のみ。

実測例: 2026-09-06T14:38:01Z と 14:38:57Z の2件は、本 recon 用カード H-03 で実装役が hook 本文を heredoc でファイルに書こうとし、hook が自身のパターンを検知して止めた記録。検問は設計どおりに働いた。

---

## 4. 維持の仕組みの現在値

在るもの:

- `scripts/check-hooks.sh`（62行）: 機体側6本の存在と実行権限のみ検査。中身は見ない。
- `.github/workflows/hook-permission-check.yml`: check-hooks.sh 変更時のみ発火（guard-disabled-record.md §3）。
- ledger-guard の「配布原本 → 手作業カードで cp → diff 逐語検収」方式（1本分）。

無いもの:

- 4本の原本（repo 内）
- 原本と実機の一致検査（1本分も、実機が先に変わり原本が置き去り）
- PR を経ない変更の検出（今回、5本中3本が PR なしで変わっていたことを行数比較で初めて把握）
- 新環境への導入手順書（該当語の検索0件）
- 実装役向け「検問 failed 時は停止して全文報告」の明記（`docs/ai-agents/executor-preamble.md` で failed／BLOCKED／停止して／全文報告／素通り の一致0件）

---

## 5. 同じ原因で起きた過去の事象

- `docs/ai-agents/evidence-registry.md:1356-1369`: gh-scope-guard が block を記録した約6秒後にマージが成立（#2924・#2927）。「不合格でもマージ成立」が常態と判定済み。
- `docs/specs/local-hooks-ssot/guard-disabled-record.md`（08-31）: 無効化理由5件。うち #4「自分のPRでも gh pr edit が止まる」・#5「CI の赤ログを読む経路が塞がり、実装役が自力で修復できない」。守り手が厳しすぎて自律修復を殺し、結果として守り手ごと止めた。
- `docs/specs/ledger-guard/README.md`: 第1弾 G1 達成（07-04）と記されるが、実機は 08-26 に別物へ変わっている。

---

## 6. 設計図との対照（KGI H1〜H10）

| # | 合格ライン | 現在値（実測） | 判定 |
|---|---|---|---|
| H1 原本 | 5/5 | 1/5 | 不足 |
| H2 説明書 | 5/5 | 0/5（先頭コメントのみ・3本は exit 記述が実装と不一致） | 不足 |
| H3 一致 | 5/5 | 0/5（原本が在る1本も不一致） | 不足 |
| H4 ずれ検出 | 1 | 0 | 不足 |
| H5 PR外変更の発見 | 1 | 0（3本が PR なしで変更） | 不足 |
| H6 素通り穴 | 1 | 0（守り手自体が無効） | 不足 |
| H7 記録3点 | 5/5 | 判定保留（いつ・何を＝あり、なぜ＝op名のみ。「なぜ」の定義は design で決める） | 保留 |
| H8 導入手順書 | 1 | 0 | 不足 |
| H9 failed 時ルール | 1 | 0（executor-preamble に0件） | 不足 |
| H10 先行参照 | 3以上 | 3（README に3リンク） | 達成 |

KPI: 1/10。

設計図に記載なし（余剰・要判定）: `scripts/permit-danger.sh` による使い捨て許可経路。`agent-start-hook.sh`／`agent-stop-hook.sh` の記録機能。

---

## 7. ノイズと境界

- gh-scope-guard の再設計は本 recon の範囲外（guard-disabled-record.md §5）。現状の「無効」を事実として記すのみ。
- CI 関所側（process-hardening）は範囲外。
- agent-start-hook.sh・worktree-access-guard.sh の全文は未読。
- 他の機体・他の実装役の状態は未測。
- `agent-tokens.json` は `danger_ops` と鍵名のみ取得。他の値は読んでいない。

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|---|---|---|
| 1 | 対象ADR | H-06 の検索で確定 | 未解消 |
| 2 | H7「なぜ」の定義 | design で決める | 未解消 |
| 3 | danger_ops 17件を誰がいつ決めたか | 記録の検索（agent-events／DEPLOY_LOG） | 未解消 |
| 4 | worktree-only-guard 08-26 変更の理由と記録の所在 | .bak 比較・記録検索 | 未解消 |
| 5 | H9 相当の記述が executor-preamble 以外に在るか（design-partner.md §6 等） | 横断検索 | 未解消 |
| 6 | 余剰2項目（permit-danger／start・stop hook）を残すか | POの判定 | 未解消 |

未解決ゼロ確認: 未解決6件あり。design 局面またはPO判断で解消する。

---

## 実測の出所

- 機体側ファイル: `~/.claude/settings.json`（`jq '.hooks'` のみ）、`~/.claude/scripts/*.sh`（head／grep／sed／wc）、`~/.claude/agent-tokens.json`（`jq '.danger_ops'` と `jq 'keys'` のみ）、`~/.claude/logs/agent-events.jsonl`（tail 5）。
- repo 側: `git show origin/main:<path>`／`git grep … origin/main`／`git ls-tree`。ローカル作業ツリーは読んでいない。
- 書き込みは一切行っていない。agent-danger-hook.sh は 242 行中、実装役が hook の自己検知回避のため要約置換した約30行を「見えていない」として扱い、本 recon の根拠に使っていない。
- H-05 手順4の `diff` 終了コードは、パイプ後の `$?` を拾った誤測定のため使用しない（差分本文で相違を確認）。
