# recon: 設計承認後に「関係のない権限不足」で止まる現状

この文書は何か（専門用語なしの1行）: PO と Opus が決めた設計を Sonnet が実装するときに、どこで・何件・なぜ止まっているかを実物で調べた記録。
親（あるべき姿＋KGI）へのリンク: [design.md](design.md)

- 調査日: 2026-10-12（JST）
- 調査者: Sonnet（読み取りのみ）→ 結果の確認と判定は Opus
- 調査対象期間: 2026-10-05 13:01Z 〜 2026-10-12（直近7日）
- 生データの置き場所: 社外に出さないため、セッションの作業領域に置いた（permission-recon.md、design-recon.md、permit-bridge.md）。本書には集計値だけを記す。

## 0. 既存 ADR の検索結果

- 検索方法: `git grep -il` で permit / hook / 委任 / delegation / auto mode / 権限 を `docs/adr/` から検索した（約60件ヒットし、多くは無関係）。あわせて `docs/adr/FEATURE-INDEX.md` も見た。
- 関係がある ADR:
  - `docs/adr/ADR-1003-go-delegation-to-opus.md:14` — GO 発行を Opus に常時委譲する。
    - 条件（:25-29）: 必須 CI がすべて緑、Reviewer が APPROVE、PO への3行報告。
    - 例外（:33-41）: DROP TABLE/COLUMN、大量 DELETE、secrets、Ruleset/Branch Protection、workflow-lint.yml、外部 GUI、force push。
  - `docs/adr/ADR-136-cc-bot-github-identity.md` — 危険な PR の GO 手順（GO 権限は PO 単独）。ADR-1003:53 がこの部分だけを上書きしている。
  - `docs/adr/ADR-135-release-stowaway-prevention.md` — main へのマージは本番投入可の宣言。
  - `docs/adr/ADR-113-two-mode-dev-flow.md` — handoff モードの順序（Architect の整合検査 → Generator）。
  - `docs/adr/ADR-042-guardrails-and-release-flow.md` — Claude Code 運用のガードレール。
- auto mode を主題とする ADR: 見つからなかった。

## 1. 停止の件数（フックの記録）

出典: ~/.claude/logs/agent-events.jsonl（86,578行）。SessionStart の集計は /Users/tanizawashingo/salesanchor/.claude/hooks/stop-log-digest.sh:26-32。

| type | 7日件数 | 中身 |
|---|---|---|
| danger_detected | 230 | psql 書き込み 126 / `rm -rf` 56 / DELETE FROM 27 / clasp push 12 / TRUNCATE 6 / ほか 3 |
| danger_permit_consumed | 44 | psql-write 35 / clasp push 9（PO が都度 permit を発行した回数） |
| permits_self_issue_blocked | 15 | AI が permits に触れようとして止められた |

- 日別の danger_detected: 10/05=6、10/06=10、10/07=37、10/08=15、10/09=51、10/10=36、10/11=39、10/12=36
- 【事実】`stop` はセッション終了の記録で、停止ではない。
- 【事実】理由の文言を記録に残しているのは gh_scope_blocked だけ。ほかのフックは理由を stderr に出すだけで、あとから数えられない。

## 2. 停止の件数（セッション記録の tool_result）

- 対象: 直近7日のセッション記録 883本（うちサブエージェント 855本）。
- 抽出: エラーまたは拒否の文言を含む 1,388件。

| 種類 | main | sub | 計 |
|---|---|---|---|
| フック pr-body-guard | 100 | 90 | 190 |
| フック agent-danger-hook | 53 | 66 | 119 |
| 自動判定（classifier）の拒否 | 90 | 21 | 111 |
| 自動判定の判定エラー（no verdict） | 7 | 0 | 7 |
| フック worktree-only-guard | 16 | 84 | 100 |
| ツール側の `sleep` 拒否 | 30 | 48 | 78 |
| ユーザーが拒否 | 22 | 1 | 23 |

自動判定の分類名（111件の内訳、上位12）:

| 分類名 | 件数 |
|---|---|
| 理由なし（dangerous, no explanation） | 22 |
| Auto-Mode Bypass | 14 |
| Merge Without Review | 13 |
| Self-Modification | 11 |
| Modify Shared Resources | 9 |
| Remote Shell Writes | 7 |
| Interfere With Workloads | 5 |
| Self-Approval / Secret-Store Writes / Production Deploy / Irreversible Local Destruction / Instruction Poisoning | 各3 |

フックが止めた理由の1行目（上位）:

| 文言 | 件数 |
|---|---|
| worktree-only-guard「working directory could not be resolved safely」 | 75 |
| agent-danger-hook「[psql-write-guard] 本番DBへの直接書き込みは禁止」 | 67 |
| pr-body-guard「宣言外のファイルから行を削除」 | 24 |
| agent-danger-hook「'rm -rf' は不可逆操作のためブロック」 | 21 |
| worktree-only-guard「protected target branch (main)」 | 15 |
| pr-body-guard「守り手: が空欄」 | 15 |
| agent-danger-hook「'DELETE FROM' …」 | 11 |
| agent-danger-hook「[permits-guard]」 | 10 |

## 3. 止める仕組みの実物

### 3-1. worktree-only-guard（/Users/tanizawashingo/.claude/scripts/worktree-only-guard.sh）

- :40 — 作業ディレクトリが絶対パスでない、または存在しないときは拒否する。
- :46-49 — 先頭が `cd` のコマンドは、引数が次の正規表現に合わないと拒否する。
  - 正規表現: `^\s*cd[ \t]+(?:--[ \t]+)?("[^"$`\n]*"|'[^'\n]*'|[^\s;&|<>()$`\\]+)[ \t]*(?:&&|;|\n|$)`
  - 拒否される例: 引数に `$VAR`・`$(..)`・バッククォート・括弧を含む、`cd` 単独、`cd X || …`、`cd X | …`
- :55-57 — `cd` の先が存在しないときは拒否する（`cd -` も拒否される）。
- :65-76 — 次のものを拒否する。
  - develop/main 上での `git commit`
  - 旧クローンでの push / fetch
  - develop/main への force push
- 【事実】`git -C X` やサブシェルの `( cd X && … )` は解析の対象外。拒否されないが、cd の先は検査されない。

### 3-2. agent-danger-hook（/Users/tanizawashingo/.claude/scripts/agent-danger-hook.sh、413行）

- :41-106 psql-write-guard
  - 本番 DB への書き込みを検出する。検出する形は `ssh+psql < file`、`-f file`、`| psql`、`docker exec psql`、`psql -c` の書き込み SQL。
  - :89 で `python3 ~/.codex/salesanchor/permit_bridge.py consume-ticket` を呼ぶ。"consumed" が返らなければ exit 2 で止める。
- :108-141 permits-guard — コマンドの文字列に permits のパスが出たら、例外なく exit 2 で止める。
- :143-296 — 本店（作業場所でない元の場所）での `git clean` / 破壊系の `git stash` / `git checkout --` / `git restore` を止める。作業場所の中では記録だけする。
- :301-411 danger_ops の照合
  - 照合の対象はコマンド全体の文字列。`&&` `||` `;` `|` で単純に分割し、引用符は解釈しない。
  - 例外は、分割した各部分の先頭が grep / rg / cat / head / tail / less / `sed -n` の場合だけ（:312-337）。
  - 【事実】ヒアドキュメントの本文、`echo` の引数、`git commit -m` の文字列に危険語が入っていても止まる。今回の調査中にも、集計スクリプトの本文に `rm -rf` の文字列があっただけで止められた（実行はしていない）。
- :362-391 permit の消費 — ~/.claude/permits/danger-permit-*.json を読み、op が部分一致すれば `os.remove` で削除する（1回限り）。

### 3-3. permit の発行と消費

- 発行: `scripts/permit-danger.sh:15-36`
  - ~/.claude/permits/danger-permit-<op>-<UTC時刻>.json を作る。
  - 中身は `{op, created_at, expires_at: 30分後, created_by: "manual"}`。
  - 本人を確認する仕組みはない。permits-guard は permits のパスの文字列だけを照合するので、`bash scripts/permit-danger.sh "psql write"` という形の実行は止めない。
  - ~/.claude/settings.json の autoMode.allow には、PO の決定に基づいて AI がこれを1回実行してよいとする規則がある（Reviewer 再審査 LOW-F で確認）。
- psql 用の消費: /Users/tanizawashingo/.codex/salesanchor/permit_bridge.py（105行）
  - :1-4 で "No ticket issuance" と宣言している（発行はしない）。
  - :55-56 の受理条件: op == "psql write"、created_by == "manual"、有効期間が1800秒以下、uid が一致する、symlink でない。
  - :59 で受理と同時にチケットを削除する。
  - :15-21、:60-62 で、そのコマンドの sha256 に束縛された30秒の領収書を作る。
  - 【事実】repo 内の参照（`git grep permit_bridge`）は0件。repo の外だけにある仕組み。
- 【事実】PO は、本番 DB に1回書き込むたびに `scripts/permit-danger.sh` を1回実行している（7日で44回）。

### 3-4. pr-body-guard（/Users/tanizawashingo/.claude/scripts/pr-body-guard.sh、115行）

- :23-30 — Bash のコマンド文字列に `gh pr create|edit` と `--body` / `--body-file` の両方が含まれると動く。
  - 【事実】今回の調査中、調査結果をヒアドキュメントでファイルに書こうとしたところ、本文にこの文字列が含まれていたため止められた。
- 検証の本体は `scripts/dev/validate-pr-body.sh`（322行）。
  - 作業場所で `bash scripts/dev/validate-pr-body.sh < body.md` と実行すれば、PR を作る前に単独で検査できる（合格 exit 0 / 不合格 exit 1）。

### 3-5. 現在の許可設定

- ~/.claude/settings.json
  - `defaultMode: auto`
  - `permissions.allow`: Read / Write / Edit / Glob / Grep / WebFetch / WebSearch
  - `autoMode.allow`: `$defaults` に加えて、PO の決定に基づく文章の規則が約20件ある（GO 委任、本番の読み取り、PO が合意した本番データ変更、個別の作業の許可など）。
  - `autoMode.soft_deny`: `$defaults`、`Bash(gh pr merge *)`、`Bash(docker compose restart *)`
- PreToolUse Bash のフックの順番: worktree-only-guard → agent-danger-hook → worktree-access-guard → gh-scope-guard → pr-body-guard

### 3-6. 公式仕様（Context7 `/websites/code_claude`、2026-10-12 照会）

- auto-mode-config
  - 判定の優先順は hard_deny → soft_deny → allow（soft_deny の例外）→「ユーザーの発言が、これから行う操作そのものを具体的に書いている」。
  - 一般的な依頼は、明示的な意図として数えない。
- auto-mode-config — 止められた操作の入力全文は `PermissionDenied` フックが `tool_input` として受け取れる。
- sub-agents — 親が auto mode のとき、サブエージェントも同じモードで動き、親の block / allow 規則で判定される。終了時の報告も審査される。
- 入力スキーマの全体は未確認（下記）。
- `claude --version` = `2.1.296 (Claude Code)`

## 4. 未確認（設計で扱いを決めたもの）

| 項目 | 設計での扱い |
|---|---|
| ~/.claude/agent-tokens.json の danger_ops 一覧（自動判定が読み取りを拒否） | 段2の実装の前に、PO の端末で `!` を付けて読み取ってもらう（段2カードの最初の手順） |
| PermissionDenied フックの入力 JSON の全項目 | 段1で実際の入力をそのまま保存し、項目を確定する（保存する項目を絞らない作りにする） |
| PO の `!` 実行に PreToolUse フックがかかるか | 段3の受入試験 T3-1 で実測する |
| 承認チケットがサブエージェントの自動判定にも効くか | 段4の受入試験 T4-1 で実測する。効かなければ段4の時点で報告する |
| 整合検査（ADR-113）の実行コマンド名 | 本便は docs のみのため対象外。実装カードの発行前に `.claude/agents/architect.md:24-33` の手順で行う |
