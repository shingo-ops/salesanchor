---
mode: handoff
---
# 実装カード：ひな形だけを変えて移行を足さない PR を CI で止める（段5 K5-2c）（Sonnet・クラウド）

状態: **第1版（2026-11-17）。PO の実装承認は 2026-11-17「1」（5-3 を作り始めてよい。その前にこの確かめを足すと Opus が PO に伝えた範囲）。**

## 発行前の照合（design-partner.md 5.5）
| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号をバッククォートで囲む | ○ |
| 2 | PR は Draft で作らせる。実装役はマージしない。マージは審査役の APPROVE・CI 緑・ADR-1003 の委任 GO がそろってから Opus が行う。migrations/・deploy.yml・本番の台本を変えないので ADR-136 の危険 PR に当たらない | ○ |
| 3 | 報告の宛先と生出力の全文 | ○（下の「報告」） |
| 4 | 1便1目的（CI の確かめを1つ足すだけ。本番は触らない） | ○ |
| 5 | ブランチの起点を明示（`origin/main` から新しく `release/migration-template-guard-5-2c`） | ○ |
| 6 | 書式は実例で示す（許可一覧の形は `scripts/migration-guard/dryrun-exclusions.tsv` の頭の説明と同じ形） | ○ |
| 7 | 合格基準を出力まで縛る | ○（手順ごとの「合否の線」） |
| 8 | 件数と名前を対で出す | ○ |
| 9 | 出力量に上限のある命令だけ | ○ |
| 10 | 停止時の3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実測から（下の「今の実物」） | ○ |
| 12 | 停止は設計の前提が崩れたときだけ | ○ |
| 13 | sleep させない・Write で書く・止められたら言い換えない | ○ |

## 目的
設計 `docs/handoff/migration-runner-redesign/design.md` §5-6「その後: ひな形を変える PR は、同じ PR に migrations/ の新しい手順が無ければ CI で止める」と受け入れ基準 K5-2c を実装する。
形の差0の検査（K5-2、PR #5551）は「移行が作る物がひな形にもある」向きだけを守る。逆向き（ひな形にだけ足して、今ある会社には足さない）をこの確かめで守る。

## 今の実物（Opus が 2026-11-17 に origin/main `7faae9090` で読んだ物）
- ひな形の本体は `backend/app/services/tenant.py` の、名前が `_` で始まり `_SQL` で終わるモジュールの定数（`_TENANT_TABLES_SQL` :194・`_RLS_ENABLE_SQL` :2298・`_RLS_POLICY_SQL` :2377・`_META_PAGE_ROUTING_TRIGGER_SQL` :2713 など）と、関数 `create_tenant_schema`（:2857）の中の文字列（既定の権限の文 :2923・:2925 を含む）。
- 見張りの CI は `.github/workflows/migration-guard.yml`（pull_request で main・develop。`paths:` は付けない規則。同 :437・:444 のコメント）。既存の step は PR の base と head を `github.event.pull_request.base.sha`・`head.sha` で比べる（同 :27-28）。
- 許可一覧の置き場所は `scripts/migration-guard/`（`dryrun-exclusions.tsv`・`value-write-allowlist.tsv` など。頭に `#` の説明、タブ区切り）。

## 前提
- 先に全部読む: `design.md` §5-6・§5-9 の K5-2c、`.github/workflows/migration-guard.yml` の全文、`scripts/migration-guard/value-write-allowlist.tsv` の頭の説明。
- 本番のサーバーと DB には一切つながない。DB は使わない（この確かめは git と Python の ast だけで動く）。

## 手順
1. 受領確認: 報告の先頭に「本報告はカード 5-2c の実行結果である」と書く。
2. 作業フォルダ: `git fetch origin` → `bash scripts/new-worktree.sh release/migration-template-guard-5-2c` → `git rev-parse HEAD`・`git rev-parse origin/main` を記録。reset・rebase・force・merge・pull は使わない。
3. `./scripts/dev/executor-preflight.sh` を流し、出力を記録する。
4. **台本 `scripts/check_template_needs_migration.py` を新しく作る**。引数は `--base <sha> --head <sha>`。動き:
   - (1) base と head の `backend/app/services/tenant.py` を `git show <sha>:backend/app/services/tenant.py` で読み、Python の `ast` で解く（import して動かさない）。
   - (2) 「ひな形の文字列」を取り出す: モジュールの直下で、名前が `^_[A-Z0-9_]*_SQL$` に合う代入の右辺の文字列（`ast.Constant` の str と、f 文字列 `ast.JoinedStr` の中の str の部分）と、関数 `create_tenant_schema` の中の全部の文字列。定数の名前（関数の中は `create_tenant_schema` と出てくる順の番号）と文字列の組の一覧にする。説明文（コメント）は ast に残らないので比べに入らない。
   - (3) base と head の一覧が同じなら「ひな形の変更なし」で成功。
   - (4) 違うときは、変わった定数の名前を全部出す。そのうえで、PR が `migrations/` に新しいファイルを足していて（`git diff --name-only --diff-filter=A <base> <head> -- migrations/`）、そのファイルのどれか1本以上が head の `scripts/run_all_migrations.sh` の `^run_(sql|py)[[:space:]]` の行に登録されていれば成功。
   - (5) そうでなければ、`scripts/migration-guard/template-only-allowlist.tsv`（新しく作る。列はタブ区切りで `pr`・`reason`。頭に `#` で説明と規則を書く）にこの PR の番号の行があれば成功。PR の番号は引数 `--pr <番号>` で受ける。
   - (6) どれにも当たらなければ失敗。失敗の文は「ひな形（tenant.py）の <定数の名前の一覧> が変わったのに、migrations/ に登録済みの新しい手順がありません。今ある会社にも同じ物を足す手順を同じ PR に足してください。足す必要が無い（説明の直しだけ・登録済みの移行が作る形に合わせるだけ）ときは、scripts/migration-guard/template-only-allowlist.tsv に PR 番号と理由を足してください」とする。
   - 許可一覧の規則（頭の説明に書く）: 行は PR 1本ごと。理由は「どの移行が既に同じ物を作っているか」をファイル名で書く。合流した後も行は残す（記録として）。
   - 合否の線: 下の手順6の6つの試験が全部通る。
5. **CI に足す**: `.github/workflows/migration-guard.yml` の既存の job `check` に、新しい step を1つ足す（新しい job にしない。必須チェックの名前を変えないため。`paths:` は付けない）。`python3 scripts/check_template_needs_migration.py --base "${{ github.event.pull_request.base.sha }}" --head "${{ github.event.pull_request.head.sha }}" --pr "${{ github.event.pull_request.number }}"`。step の上に1行で理由（設計 §5-6・K5-2c）を書く。既存の step は変えない。
6. **試験 `backend/tests/test_check_template_needs_migration.py`** を足す。使い捨ての git の作業場所（`tmp_path` に `git init`）で base と head の commit を作って台本を呼ぶ。6つ:
   - (a) ひな形の文字列が同じ（説明文だけ変えた）→ 成功
   - (b) `_TENANT_TABLES_SQL` に列を1つ足し、migrations/ を足さない → 失敗、文に `_TENANT_TABLES_SQL` が出る
   - (c) (b) に、登録の行に足した新しい migrations/ のファイル1本を加える → 成功
   - (d) (b) に、登録していない新しい migrations/ のファイルを加える → 失敗
   - (e) (b) で、許可一覧にこの PR 番号の行がある → 成功
   - (f) `create_tenant_schema` の中の既定の権限の文を変え、migrations/ を足さない → 失敗
   - Mac では流さない。CI で確かめる。
7. **赤の実演**（K5-2c の測り方）: PR を出した後、同じブランチに `_TENANT_TABLES_SQL` の説明でない所（例: どれかの表の列の後ろ）に列を1つ足す commit を push し、新しい step が赤になることを確かめ、URL と失敗の文を記録する。続けてその commit を打ち消す commit（`git revert` は使ってよい。force は禁止）を push し、緑に戻ることを確かめる。
8. 自分の PR がこの確かめで赤にならないこと（この PR は tenant.py を変えない）を確かめる。
9. commit・push（force 禁止）。Draft の PR を `--base main` で作る。本文は `.github/pull_request_template.md` から書き、「触るファイル:」に全ファイルを列挙する。マージしない。

## 停止
- 止めるのは、設計と食い違うとき、ひな形の文字列の取り出しが今の tenant.py で定数を1つも拾えないとき（拾った定数の名前の一覧を書いて `NEEDS_DECISION:`）、push・PR の拒否、フックや自動判定に止められたとき。言い換えて再試行しない。
- `migrations/`・`deploy.yml`・`backend/app/` を変えない。本番に接続しない。
- sleep しない。rm しない。Bash に psql の語を書かない。
- 停止したら報告に「止まった手順の番号／最後に流した命令／止まった理由の原文」を書く。

## 報告
- 最後の行は `DONE`・`BLOCKED: <理由>`・`NEEDS_DECISION: <問い>` のどれか。
- commit の番号、PR の番号、手順4の (2) で今の tenant.py から拾った定数の名前と件数、手順6の試験の結果、手順7の赤と緑の URL を書く。
