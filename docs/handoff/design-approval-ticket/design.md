---
mode: handoff
status: draft（PO 承認待ち・実装未着手）
---

# 設計承認チケット：決めた設計を、関係のない権限不足で止めずに完走させる

この文書は何か（専門用語なしの1行）: PO が設計を承認するときに1回だけ許可を出せば、その設計に書いた作業は AI が最後まで止まらずに進められるようにする計画書。
親へのリンク: [ADR-1003（GO委任）](../../adr/ADR-1003-go-delegation-to-opus.md) / [opus-delegation.md](../go-record-transcription/opus-delegation.md)
現状の調査: [recon.md](recon.md)

## 1. あるべき姿（PO の原文・2026-10-12）

> 私は意思決定のみopusとの壁打ちで行うが、壁打ちが終わり設計が完了したらopusがマネジメントしてsonnetに実装などを任せるのだがその際に権限不足が多く、報告が帰ってきて開発がとなるケースが多い、なのでopusに権限委譲をして設計を完走させられるようにしてほしい

> 設計を固めるまではopusと話し合い意思決定を指定区の決めた内容を関係のない権限不足で止まっていまう現状を解消したい

> 基本的に開発に必要な権限は承認したい

## 2. KGI

| # | 合格条件 | 測り方 | 合格ライン |
|---|---|---|---|
| K1 | 承認チケットを出したあと、デプロイの確認が終わるまでの間に、権限が理由で PO に戻した回数 | 段3以降の最初の3設計で、Opus の PO への報告のうち、理由が権限不足のものを数える（`permission-denied.jsonl` と突き合わせる） | 0件 / 3設計 |
| K2 | 作業場所の誤判定（「working directory could not be resolved safely」）で止まった件数 | `agent-events.jsonl` と `permission-denied.jsonl` の該当文言を7日分数える（基準値: 75件/7日） | 0件 / 7日 |
| K3 | 実行しない文字列（ヒアドキュメントの本文、`echo` / `-m` / `--body` の引数）だけで危険操作フックや PR 本文フックが止めた件数 | 受入試験 T2-2 から T2-5 の結果 | 全て通過 |
| K4 | PO 本人に残す操作（DROP / TRUNCATE / secrets / ブランチ保護 / force push / 外部 GUI）が、チケットがあっても止まる | 受入試験 T3-4 の結果 | 全て停止 |
| K5 | 自動判定とフックで止まった操作が、理由つきで全件記録される | 段1のあと、止まった操作の件数と記録の件数を突き合わせる | 記録漏れ 0件 |

## 3. KPI

達成した KGI の数 ◯/5（段ごとに更新する）。

## 4. recon（要点。詳細は [recon.md](recon.md)）

- 直近7日の停止は、合計で約620件ある。
- 原因の大きいもの:
  - PR 本文のフック（190件）
  - 危険操作のフック（119件。本番 DB への書き込みが67件）
  - 自動判定（111件）
  - 作業場所のフック（100件。うち75件は誤判定）
  - `sleep` の拒否（78件）
- PO は本番 DB に1回書き込むたびに `scripts/permit-danger.sh` を実行している（7日で44回）。
- 危険操作のフックは、コマンド全体の文字列に危険語が含まれるだけで止める（`/Users/tanizawashingo/.claude/scripts/agent-danger-hook.sh:301-411`）。
- 公式仕様では、`allow` に文章の規則を足すか、ユーザーが操作そのものを具体的に書いた発言があれば、自動判定は通す。

## 5. design

段に分け、1段ずつ変更・反映・測定してから次の段へ進む。

### 段1：止まった操作を全件記録する（基準値を取る）

- 新規ファイル ~/.claude/scripts/permission-denied-log.sh
  - 公式の `PermissionDenied` フックとして登録する。
  - 受け取った JSON をそのまま `~/.claude/logs/permission-denied.jsonl` に1行ずつ追記する。項目は絞らない。
  - `tool_input` の中の秘密値の形（`*_TOKEN=`、`Bearer `、`password=`）は伏せ字にしてから保存する。
- 既存の4つのフック（worktree-only-guard、agent-danger-hook、pr-body-guard、gh-scope-guard）
  - 止める箇所の直前に、`agent-events.jsonl` に `{type:"hook_blocked", hook, reason, cmd_head(120字)}` を1行書く処理を足す。
  - 止める条件そのものは変えない。
- 触らない範囲: フックの判定ロジック、settings.json の autoMode。

### 段2：関係のない停止をなくす

1. 作業場所の誤判定（`/Users/tanizawashingo/.claude/scripts/worktree-only-guard.sh:46-57`）
   - 変更前: 先頭が `cd` のコマンドで引数を解析できないと、その場で拒否する。
   - 変更後: 解析できないときは「場所不明」として扱う。止めるのは、コマンドに `git commit` / `git push` が含まれる場合だけにする（:65-76 の保護ブランチの検査が意味を持つのはこの2つだけのため）。それ以外は通して、段1の記録に `cwd_unresolved` として残す。
   - 触らない範囲: :9-30（permits への書き込みの禁止）、:65-76 の判定内容。
2. 危険語の照合（`/Users/tanizawashingo/.claude/scripts/agent-danger-hook.sh:301-411`）
   - 照合の前に、次の部分を照合の対象から外す。
     - ヒアドキュメントの本文（`<<'X'` から `X` まで）。ただし、その行の先頭のコマンドが `cat` / `tee` で、行き先が `>` のファイルの場合に限る。
     - `git commit -m` / `gh pr … --body` / `--title` の引数。
   - `rm -rf` は、すべての対象パスが次の場所の下にあれば通す。
     - `~/worktrees/` の下で、自分のセッションの作業場所であるもの（worktree-access-guard の所有判定を使う）
     - セッションの作業領域（`/private/tmp/claude-*`）
   - 触らない範囲: `bash -c` / `sh -c` / `eval` の引数（実行される文字列なので外さない）、:41-106 psql-write-guard、:108-141 permits-guard。
3. PR 本文フック（`/Users/tanizawashingo/.claude/scripts/pr-body-guard.sh:23-30`）
   - 変更前: 文字列のどこかに `gh pr create` と `--body` があれば動く。
   - 変更後: `&&` `;` `|` で分けた各部分の先頭が `gh pr create|edit` のときだけ動く。ヒアドキュメントの本文は判定に使わない。
   - 触らない範囲: 検証の本体 `scripts/dev/validate-pr-body.sh`。
4. 委任文の定型（`docs/ai-agents/design-partner.md` §5.5 に13番として追記する）
   - 担当に `sleep` で待たせない。待つのは Opus が行う。
   - ファイルの作成は Write ツールで行う。
   - PR を作る前に `bash scripts/dev/validate-pr-body.sh < body.md` を通させる。
   - フックや自動判定に止められたら、言い換えて再試行しない。止まって報告する（既存の規則を再掲する）。

### 段3：設計承認チケット

1. 操作一覧ファイル docs/handoff/<topic>/ops.yaml
   - 設計者（Opus）が設計書と一緒に作り、PR に載せる。
   - 書くこと: 設計 ID、作業場所のパス、期限（既定は72時間、上限は7日）、操作の一覧。
   - 操作は次の種類だけを書ける。

| kind | 必須項目 | 束縛 |
|---|---|---|
| psql-write | `sql_file`、`host`（prod1 等） | SQL ファイルの sha256、ホスト名 |
| clasp-push | `project_dir` | ディレクトリの realpath |
| rm-rf | `paths` | realpath が作業場所の下 |
| merge | `pr` | PR 番号 |
| deploy-check | `pr` | PR 番号 |
| command | `cmd`（完全一致） | 文字列 |

   - 各操作に `max_uses`（既定は1）を書く。
2. 発行スクリプト（新規）`scripts/approve-design.sh <ops.yaml>`
   - PO が `!` を付けて1回実行する。
   - 操作の一覧を画面に表示し、~/.claude/permits/design-approval-<id>.json を作る。
   - ファイルの中身: ops.yaml の内容、SQL ファイルの sha256、`approved_at`、`expires_at`、`created_by: "po-bang"`。
   - 次のどれかが一覧にあれば、拒否して終了する。
     - SQL の中の `DROP` / `TRUNCATE` / `ALTER TABLE … DROP`、行の条件がない `DELETE`
     - secrets
     - `gh api` によるブランチ保護の変更
     - force push
3. AI による発行を防ぐ（agent-danger-hook.sh の permits-guard の並びに追加する）
   - AI のコマンド文字列に `approve-design` が出たら、例外なく exit 2 で止める。
   - 既存の permits-guard が、`~/.claude/permits` への AI の読み書きを止める仕組みはそのまま使う。
4. チケットの消費（agent-danger-hook.sh に新しい関数 `consume_design_ticket` を追加する）
   - psql-write-guard（:41-106）と danger_ops の照合（:301-411）で止める直前に、有効なチケットを探す。
   - 次の条件をすべて満たせば通し、使用回数を1つ減らす。
     - kind と束縛が一致する（psql-write なら、コマンドが参照する SQL ファイルの sha256 とホストが一致する）
     - 期限内である
     - 作業場所が一致する
   - 通したときは、段1の記録に `ticket_used` を書く。
   - 既存の `scripts/permit-danger.sh`（1回限り・30分）は残す（設計外の単発作業に使う）。
5. ADR
   - ADR-1003 に追補として「設計承認チケット」の節を足す。PO の承認文と残す例外を書く。
   - `node scripts/generate-adr-index.js` で索引を作り直す。

### 段4：自動判定（classifier）にチケットを伝える

- ~/.claude/settings.json の `autoMode.allow` に、次の文章の規則を1件足す。
  > Operations listed in a PO-issued design approval: when the user ran scripts/approve-design.sh via a `!` command in this session and its output lists the operations, executing exactly those listed operations (same SQL file, host, PR number, path or command) before the printed expiry is explicitly authorized by the user, including when performed by a subagent whose prompt quotes the design ID and the listed operation verbatim.
- 書き込みは Self-Modification に当たるので、PO が `!` を付けて追記スクリプトを1回実行する。スクリプトは Opus が作る。
- Sonnet への委任文には、設計 ID と ops.yaml の該当操作を原文のまま書き写す。

### 触らない範囲（全段共通）

- ADR-1003:33-41 の例外の操作。
- `hard_deny`。
- `.github/workflows/workflow-lint.yml`、Branch Protection、Ruleset。
- 本番の secrets。
- permit_bridge.py（Codex 側の仕組みで、本便では変えない）。

## 6. 弊害・トレードオフ

| 弊害 | 対処 |
|---|---|
| チケットの有効期間中は、一覧にある操作を PO が見ないまま実行できる | 期限を短くする（既定72時間・上限7日）。束縛を厳しくする（sha256・PR 番号・パス）。回数に上限を付ける。段1の記録で事後に全件確認できるようにする |
| 照合から外す範囲を広げると、本当に危ない操作を見逃すおそれがある | `bash -c` / `eval` / `sh -c` は外さない。受入試験 T2-6 で、実行される危険操作が今までどおり止まることを確認する |
| 自動判定は文章の規則で判断するので、段4の規則が効くかは保証されない | 受入試験 T4-1 で実測する。効かなかった場合は、その時点で PO に報告し、別案（その都度 PO が `!` で承認する範囲を広げる）に戻す |
| フックがリポジトリの外（`~/.claude/scripts`）にあり、変更の履歴が残らない | 変更前に `~/.claude/scripts/.backup/<日時>/` に写しを置く。変更後の差分を PR 本文に貼る |
| AI が ops.yaml を書くので、承認前に一覧へ余計な操作を入れられる | PO は `!` を実行した時点で表示される一覧を見る。発行スクリプトは例外の操作を機械的に拒否する |

## 7. 外部・過去事例

- 公式（code.claude.com/docs/en/auto-mode-config、2026-10-12 に Context7 で確認）
  - 定型の操作は `allow` に規則を足す。作業中ずっと使う接続先は `environment` に書く。止められた操作は `PermissionDenied` で記録する。
  - 本設計の段1と段4は、この推奨にそのまま従っている。
  - 適用の限界: `hard_deny` は解除できない。文章の規則が効くかは実測が必要。
- 過去事例（社内）
  - 2026-09-30 の PO 決定（本番データ変更の委譲）と PR #3874 で、PO が合意した SQL が自動判定に止められ、PO が `!` で自分で実行した。本設計の段3と段4は、この再発を防ぐもの。
- 数値つきの外部事例: 該当なし。理由: 「承認時に期限つきの範囲許可を出す」形（just-in-time の権限付与）について、AI エージェントへの適用で数値を伴う公開事例を本便では確認していない。成功の根拠にはせず、K1 から K5 の実測で判定する。

## 8. 受入基準

| # | 基準 | 検証方法 |
|---|---|---|
| T1-1 | 自動判定に止められた操作が `permission-denied.jsonl` に1行増える | 自動判定が止める既知の操作を1回試し、行数の増え方を見る |
| T1-2 | フックで止めたときに `hook_blocked` と理由が記録される | 試験用の入力 JSON を各フックに渡し、記録を見る |
| T2-1 | `cd "$X" && ls` が通る | フックに試験用 JSON を渡して exit 0 になる |
| T2-2 | `cat > f <<'E'` の本文に `rm -rf` と書いても通る | 同上 |
| T2-3 | `git commit -m "… DELETE FROM …"` が通る | 同上 |
| T2-4 | 本文に `gh pr create --body` を含むファイル書き込みで PR 本文フックが動かない | 同上 |
| T2-5 | 自分の作業場所の下への `rm -rf` が通る | 同上 |
| T2-6 | `bash -c "rm -rf …"`、作業場所の外への `rm -rf`、main 上の `git commit` は今までどおり止まる | 同上で exit 2 になる |
| T3-1 | PO の `!` 実行で発行スクリプトがチケットを作れる | PO が実行し、表示を見る。`!` にも PreToolUse フックがかかって止まった場合は、PO が別のターミナルで実行する手順に切り替え、その手順を段3のカードに書く |
| T3-2 | AI が発行スクリプトを実行すると止まる | AI 側から実行して exit 2 になる |
| T3-3 | チケットにある SQL ファイルの psql 書き込みが通る。ファイルを1文字変えると止まる | 試験用 JSON（本番に送らない形）で確認する |
| T3-4 | DROP / TRUNCATE / 条件のない DELETE を含む ops.yaml は発行を拒否する | 発行スクリプトに試験用の ops.yaml を渡す |
| T3-5 | 期限切れ、または `max_uses` を超えたら止まる | 試験用チケットで確認する |
| T4-1 | 段4の規則のあと、チケットにある操作を Sonnet が実行して自動判定を通る | 試験用の設計で1件実行して確認する |

- 試験用の入力は scripts/dev/test-agent-hooks.sh（新規）にまとめる。フックに JSON を渡して exit 値を比べる。

## 9. 維持の仕組み

- 守り手: Opus（設計担当）。
  - 毎週月曜に `permission-denied.jsonl` と `hook_blocked` を数える。新しく増えた定型の停止は、規則を足す案として PO に1件ずつ出す。
- 関所: scripts/dev/test-agent-hooks.sh。
  - フックを変えるたびに実行する。全件 exit が期待どおりでなければ、フックの変更を戻す。
- 期限: チケットそのものに `expires_at` がある。期限切れのチケットは、フックが見つけ次第削除する（既存の permit と同じ）。
- 解除: PO が「委譲停止」と言えば、~/.claude/permits/design-approval-*.json をすべて削除する（PO が `!` で実行する）。ADR-1003:49 と同じ。

## 10. 接触面分析

| 面 | 影響 |
|---|---|
| ①人（PO） | 設計を承認するときに `!` で1回実行する。単発の `scripts/permit-danger.sh` は設計外の作業でだけ使う |
| ②エージェント | Opus は ops.yaml を作り、委任文に原文を書き写す。Sonnet は委任文の定型（§5 段2-4）に従う。並行セッションのフックも同じものなので、段2の誤検知の修正は全セッションに効く |
| ③機械 | `~/.claude/scripts` の4つのフック、settings.json の hooks と autoMode、新しく `PermissionDenied` を登録する。CI は変えない |
| ④データ | 本番 DB の中身は変えない。psql 書き込みの許可の経路だけが変わる（tenant_004 を含め、承認した SQL ファイルに限る） |
| ⑤本番 | deploy.yml と VPS の設定は変えない |
| ⑥外部 | 外部 API と利用者への影響はない。理由: 変わるのはローカルの Claude Code の設定とフックだけだから |

逆参照: `scripts/permit-danger.sh` / `permit_bridge` / `pr-body-guard` / `worktree-only-guard` を repo 内で grep した。`docs/handoff/design-partner-card-ops/guards/02-db.md:23-24`、`docs/handoff/fx-rate-history/design.md:80`、`docs/handoff/dist-deploy-guard/gas-deploy-runbook.md:30` が `scripts/permit-danger.sh` を案内している。単発の許可として残すので、書き換えは不要。

## 実装の順番と承認

| 段 | 内容 | 実装の承認 | PO の操作 |
|---|---|---|---|
| 段1 | 記録 | 要（本設計の承認とは別） | settings.json への hooks 登録を `!` で1回 |
| 段2 | 誤検知の修正・委任文の定型 | 要 | 実行前に danger_ops 一覧の読み取りを `!` で1回 |
| 段3 | 設計承認チケット・ADR-1003 追補 | 要（ADR の承認を含む） | 試験 T3-1 を `!` で実行 |
| 段4 | autoMode.allow の規則 | 要 | 追記スクリプトを `!` で1回 |

## 設計審査（Architect 役・同一 AI による自己審査。独立した第二者のレビューではない）

- 判定: APPROVE（設計書として合格）。実装の可否は、段ごとのカードを PO が承認してから判断する。
- 根拠:
  - 停止の上位5原因（recon §2）が、どれかの段に対応している。
    - PR 本文フック → 段2-3、段2-4
    - 危険操作フック → 段2-2、段3
    - 自動判定 → 段4
    - 作業場所フック → 段2-1
    - `sleep` → 段2-4
  - KGI の5件すべてに、測り方と受入試験がある。
  - 残す例外は ADR-1003:33-41 と一致している。
- 未解決（実測で決めるもの。設計の範囲は確定している）: T3-1（`!` にフックがかかるか）と T4-1（自動判定に効くか）。どちらも、うまくいかなかったときの手順を §6 と §8 に書いた。
- 本便での実例:
  - 2026-10-12 に、この設計書の追記と `git add` を1つのコマンドで実行しようとしたところ、自動判定が [Self-Modification] で拒否した。
  - PO の y を受けて再実行した。
  - 文書だけの作業でも、「権限に関する設計」は自動判定に止められうる。段4の規則の対象に含めるかどうかは、段1の記録を見て決める。
