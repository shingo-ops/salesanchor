---
mode: handoff
---
# 実装カード：控えのムラをなくす（段5 5-4）— 控えなしで新しい手順を流しそうになったら止める（Sonnet・クラウド）

状態: **第1版（2026-11-21、Opus）。設計 `docs/handoff/migration-runner-redesign/design.md` §5-8（第9版）の実装。向きは PO 2026-11-21「1」。実装の開始は、設計とこのカードが審査に通り、PO の実装承認を受けた後。このカードは Draft の PR までで止まる。合流は委任 GO（設計 §5-3 の表の 5-4 の行）で、合流の前に結果を PO に見せる。**

## 発行前の照合（design-partner.md 5.5）
| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号をバッククォートで囲む | ○ |
| 2 | PR は Draft で作らせる。実装役はマージしない。この PR は `.github/workflows/deploy.yml` と本番の台本 `scripts/run_all_migrations.sh` を変えるので ADR-135・ADR-136 の危険 PR に当たる | ○ |
| 3 | 報告の宛先と生出力の全文 | ○（下の「報告」） |
| 4 | 1便1目的（控えなしの (c)>0 を止める見張りと、その試験。本番には何も流さない） | ○ |
| 5 | ブランチの起点を明示（`origin/main` から新しく `release/migration-backup-guard-5-4`） | ○ |
| 6 | 書式は実例で示す（下の「変更前後」） | ○ |
| 7 | 合格基準を出力まで縛る | ○（手順ごとの「合否の線」） |
| 8 | 件数と名前を対で出す | ○ |
| 9 | 出力量に上限のある命令だけ | ○ |
| 10 | 停止時の3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実測から（呼び出し元155行・本体を丸ごと流す所3つ・CI の回1〜回6） | ○ |
| 12 | 停止は不可逆なもの・設計の前提が崩れたときだけ | ○ |
| 13 | sleep させない・Write で書く・止められたら言い換えない | ○ |

## 読んだ節と照合（Opus、2026-11-21）
- docs/handoff/design-partner-card-ops/guards/00-common.md: 1手順1命令（手順4・手順6・手順8は命令を別々に流す）・出力に上限（手順7は tail -40、手順8は head -60）・プレースホルダを残さない・報告に無い出力を成功と扱わない（手順9で git log、手順11で番号を2通りで取る）・sleep で待たない。○
- docs/handoff/design-partner-card-ops/guards/03-file.md: 触るファイルを手順5で全部挙げた。変える行は「変更前後」に全文で書いた。○
- docs/handoff/design-partner-card-ops/guards/04-worktree.md・docs/handoff/design-partner-card-ops/guards/05-pr.md: 作業フォルダは new-worktree.sh で origin/main から。push は `-u origin HEAD`。PR は gh-pr-create-safe.sh・Draft・`触るファイル:` は1行カンマ区切り。○
- docs/handoff/design-partner-card-ops/guards/07-migration.md: `migrations/` は触らない。本体の登録の行（run_sql・run_py）も触らない。○
- docs/handoff/design-partner-card-ops/guards/10-executor.md: 散文で組み立てを頼まない（変える行は全部「変更前後」に書いた）。○

## 目的
控えの段を飛ばした本番反映で、記録に無い手順（(c)）が1本以上あるときは、本体が何も流さずに止まるようにする。控えの段の条件は変えない。受け入れ基準は設計 §5-9 の K5-13・K5-14・K5-16（CI と差分で測る物）。K5-15 は合流の後に Opus が本番のログで数える。

## 今の実物（Opus が 2026-11-21 に origin/main `8ae82d896` で読んだ物）
- `scripts/run_all_migrations.sh:49-51`: `MIGRATION_MODE` の説明2行と既定（`record`）。
- `scripts/run_all_migrations.sh:118-170` `mr_plan`。:155-158 で `targets`・(a)・(b)・(c) の行を出し、:162-165 で `record` かつ (a)+(b) が0でなければ `>>> [record] (a) or (b) is not 0; nothing was run` を出して `exit 1`。
- `scripts/run_all_migrations.sh:399` で `mr_plan` を呼ぶ。trap は :457。止まっても作り直しは走らない（:395-396 のコメント）。
- `.github/workflows/deploy.yml:246-248` 控えの段（`id: backup`、`if: steps.gate.outputs.db_migrations == 'true'`）。
- `.github/workflows/deploy.yml:890` `bash scripts/run_all_migrations.sh`（移行の段 `id: migrate` の中）。
- `.github/workflows/deploy.yml:925` に `${{ steps.migrate.outcome }}` を台本の中に書く前例がある。
- `.github/workflows/migration-test.yml:2305-` job `migration-runner-record`。回1（:2415 `run_main round1 NOOP=1`）は (c)=全件。回2〜回3は (c)=0。回4・回5は (b)・(a) で止まる。回6（:2493）は `full`。
- `scripts/tests/test-deploy-orphan-cleanup.sh` の C8（:210-211）と C10（:266-267）が、偽の docker の上で本物の本体を流す。C10 の②（:269）は ai_cloud を外す行が出ることを見る。

## 前提
- 先に全部読む: 設計 §5-7・§5-8（第9版）・§5-9 の K5-13〜K5-16、`scripts/run_all_migrations.sh` の全文、`.github/workflows/migration-test.yml` の job `migration-runner-record` の全文、`scripts/tests/test-deploy-orphan-cleanup.sh` の C8・C10。設計とこのカードが食い違ったら設計を正とし、記録して止まる（`NEEDS_DECISION:`）。
- 本番のサーバーと DB には一切つながない。`migrations/` を変えない。
- 変えない物: `.github/workflows/deploy.yml` の控えの段（:236-271）の全部、本体の `run_sql`・`run_py`・trap の中の行、`MIGRATION_OUTSIDE_RECORD` の配列、回2〜回6の線。

## 変更前後

### 1. `scripts/run_all_migrations.sh`（説明: :51 の次に足す）
```bash
# 控えの段の結果（段5 5-4・設計 §5-8）。本番反映は steps.backup.outcome（success・skipped・failure・cancelled）を渡す。
# record で (c) が1本以上なのに success でなければ、何も流さずに止まる。人が record を手で流すときは、
# 先に bash scripts/backup.sh deploy で控えを取り、MIGRATION_PREDEPLOY_BACKUP=success を付ける。
```

### 2. `scripts/run_all_migrations.sh` `mr_plan`（:158 の `(c) to-run` の行の次に1行、:165 の `fi` の次に4行）
変更前（:158・:162-165）:
```bash
  echo ">>> [record] (c) to-run=${MR_TO_RUN}"
...
  if [ "${MIGRATION_MODE}" = "record" ] && [ $((a + b)) -ne 0 ]; then
    echo ">>> [record] (a) or (b) is not 0; nothing was run"
    exit 1
  fi
```
変更後:
```bash
  echo ">>> [record] (c) to-run=${MR_TO_RUN}"
  echo ">>> [record] predeploy-backup=${MIGRATION_PREDEPLOY_BACKUP:-unset}"
...
  if [ "${MIGRATION_MODE}" = "record" ] && [ $((a + b)) -ne 0 ]; then
    echo ">>> [record] (a) or (b) is not 0; nothing was run"
    exit 1
  fi
  if [ "${MIGRATION_MODE}" = "record" ] && [ "${MR_TO_RUN}" -ne 0 ] && [ "${MIGRATION_PREDEPLOY_BACKUP:-}" != "success" ]; then
    echo ">>> [record] (c) is not 0 but pre-deploy backup is not success (MIGRATION_PREDEPLOY_BACKUP=${MIGRATION_PREDEPLOY_BACKUP:-unset}); nothing was run"
    exit 1
  fi
```

### 3. `.github/workflows/deploy.yml:890`
変更前: `            bash scripts/run_all_migrations.sh`
変更後: `            MIGRATION_PREDEPLOY_BACKUP='${{ steps.backup.outcome }}' bash scripts/run_all_migrations.sh`
その上に説明1行: `            # 段5 5-4（設計 §5-8）: 控えの段の結果を本体に渡す。控えなしで (c)>0 なら本体が止まる。`

### 4. `.github/workflows/migration-test.yml`
- 回1: `run_main round1 NOOP=1` → `run_main round1 NOOP=1 MIGRATION_PREDEPLOY_BACKUP=success`。
- 回5の `echo "回5: 止まることを確かめた（合格）"` の次、回6の前に「回5b（K5-13・K5-14）」を足す。
  - 記録から `$VICTIM` の行を1行消す（`DELETE FROM ops.migration_runs WHERE file = '$VICTIM'`）。`ROWS_BEFORE=$(rows)` を取る。
  - `run_main round5b_unset NOOP=1`: 終わりの番号が0でない／`(c) to-run=1`／`predeploy-backup=unset`／`(c) is not 0 but pre-deploy backup is not success (MIGRATION_PREDEPLOY_BACKUP=unset); nothing was run` の行／`\] psql < ` の行が0／記録の行数が `ROWS_BEFORE` のまま。
  - `run_main round5b_skipped NOOP=1 MIGRATION_PREDEPLOY_BACKUP=skipped`: 同じ線で、値は `skipped`。
  - `run_main round5b_success NOOP=1 MIGRATION_PREDEPLOY_BACKUP=success`: 終わりの番号が0／`ran-and-recorded=1`／記録の行数が `EXPECTED`／`final_ok round5b_success`。
  - 最後に `echo "回5b: 控えなしで止まり、控えありで流れることを確かめた（合格）"`。
- 回6 以降は変えない。最後の `echo "回1〜回6 すべて合格"` も変えない。

### 5. `scripts/tests/test-deploy-orphan-cleanup.sh`
- C8（:210-211 の `env ... bash scripts/run_all_migrations.sh`）と C10（:266-267）の env に `MIGRATION_PREDEPLOY_BACKUP=success` を足す。ほかの線は変えない。

## 手順
1. 受領確認: 報告の先頭に「本報告はカード 5-4 の実行結果である」と書く。
2. 作業フォルダ: `git fetch origin` → `bash scripts/new-worktree.sh release/migration-backup-guard-5-4`（`--claude` は付けない。付けると別の Claude が起動する）→ 作ったフォルダへ移り、`git rev-parse HEAD`・`git rev-parse origin/main` を記録する。reset・rebase・force・pull は使わない。以後の命令は、すべてそのフォルダへの `cd` で始める。
3. `./scripts/dev/executor-preflight.sh` を流し、出力を記録する。合否の線: 0 で終わる。HEAD が `origin/main` と同じ。
4. 変える前の数を取る（基準値）: `grep -c '' scripts/run_all_migrations.sh`・`grep -nE 'run_main round' .github/workflows/migration-test.yml`・`grep -n "db_migrations == 'true'" .github/workflows/deploy.yml` の3つ（1手順1命令で別々に流す）。合否の線: `run_main round` の行が round1〜round6 の6行。`db_migrations == 'true'` の行の中に控えの段の `if:` がある。違えば `NEEDS_DECISION:`（実物が設計の時と変わった）。
5. 上の「変更前後」1〜5 を Write/Edit で入れる。触るのはこの4つのファイルだけ: `scripts/run_all_migrations.sh`・`.github/workflows/deploy.yml`・`.github/workflows/migration-test.yml`・`scripts/tests/test-deploy-orphan-cleanup.sh`。
6. 書いた物の形を確かめる: `bash -n scripts/run_all_migrations.sh`・`git diff --stat`・`git diff .github/workflows/deploy.yml`・`git diff scripts/run_all_migrations.sh`。合否の線: `bash -n` が 0。差分のファイルは手順5の4つだけ。`deploy.yml` の差分は `+` 2行・`-` 1行（:890 の行の置き換えと説明1行）。控えの段の行（`db_migrations == 'true'`）は差分に無い（K5-16）。本体の差分の `-` の行は 0。
7. 手元で回せる試験だけ回す（重い試験は CI に任せる）: `bash scripts/tests/test-deploy-orphan-cleanup.sh > /tmp/CC報告ファイル/k54-orphan.txt 2>&1` の後、終わりの番号と `tail -40 /tmp/CC報告ファイル/k54-orphan.txt` を記録する。合否の線: 終わりの番号 0。C8・C10 が合格（bash 5 が無くて飛ばされた場合は、飛ばされたと書いて報告する。線を緩めない）。
8. `[record]` の行の数や並びを決め打ちしている試験を探す: `git grep -n 'record\]' -- backend/tests scripts/tests tests .github/workflows | head -60`。合否の線: 見つかった試験それぞれについて、`predeploy-backup` の1行が増えても通るかを読んで確かめ、ファイル名・行・結論を報告に書く。通らない物があれば `NEEDS_DECISION:`（直し方を勝手に決めない）。
9. commit を1つ作る。文は `feat(migration): stop record run with new steps when pre-deploy backup was not taken (stage5 5-4)`。作った後に `git log -1 --stat` で実在を確かめる。
10. `git push -u origin HEAD` を単独で流す。
11. Draft の PR を `bash scripts/gh-pr-create-safe.sh --draft --base main` で作る（`--title` と、本文を書いたファイルを `--body-file` で渡す）。本文は PR のひな形から作り、`### 標準ワークフロー確認` の中に、設計 §5-8・このカードの場所・K5-13〜K5-16 を書き、`触るファイル:` に手順5の4つを1行・カンマ区切りで書く。作った後に `.pr-number` と `gh pr list --head release/migration-backup-guard-5-4 --json number` の両方で番号を取り、一致を確かめる。合否の線: PR が Draft で作られた。CI の結果は待たない（PR の URL を報告する）。

## 止まる条件
- 設計とカード、または実物とカードが食い違う → `NEEDS_DECISION:`。
- 本番のサーバー・DB・secrets に触る必要が出た → `BLOCKED:`（触らない）。
- 見張り（フック）に止められた → 言い換えずに `BLOCKED:` で止めた命令と文面を報告。

## 報告
最後の行に `DONE` / `BLOCKED: 理由` / `NEEDS_DECISION: 問い` のどれか1つ。その前に次を全文で書く（要約しない）。
1. 手順2・手順3・手順4・手順6・手順7・手順8 の出力の全文（長い物はファイルの場所と、そのファイルの全行の数）。
2. commit の 40 字、PR の番号と URL。
3. 停止したときは、止まった命令・出力・自分の判断の3点。

END OF CARD
