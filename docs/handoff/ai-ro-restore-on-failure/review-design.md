# 設計審査 — ai-ro-restore-on-failure

**審査者**: Architect（Opus）  
**日付**: 2026-10-21  
**基準**: origin/main d7c5dc2e4（worktree HEAD と同じ）  
**対象**: recon.md / design.md / ADR-1024「### 改訂（失敗時の作り直し、2026-10-21）」  
**判定**: **REVISE**（方向は正しい。必須3件を直して再提出）

---

## 1. file:line の突合（全件）

| 引用 | 実物 | 結果 |
|---|---|---|
| recon `scripts/run_all_migrations.sh:20` set -e | :20 `set -e` | ○ |
| recon :119 drop | :119 `run_sql migrations/20261017_125900_drop_ai_ro_views.sql` | ○ |
| recon :121 コメント | 文は :121-122 にまたがる | ○（軽微。任意 O5） |
| recon :123 / :124 / :129 / :130 / :131 / :139 / :145 | 一致 | ○ |
| recon :1037 ai_reader 作成 | :1037 `run_sql migrations/20261017_130000_create_ai_reader_role.sql` | ○ |
| recon create SQL :6 / :8 / :23 / :62 / :74 / :78 | 一致（:81 COMMIT も一致） | ○ |
| recon create SQL :29「public と tenant_*」 | :29 は relkind、スキーマ条件は :30 | △（任意 O5） |
| recon `backend/app/ops/readonly_query.py:6` | 一致。backend/app で ai_ro を使うのはこの1本 | ○ |
| recon ADR-1024:31 / ADR-1037:42 | 一致 | ○ |
| recon `tests/sandbox/migration-run-sql-retry.sh:1` / `.github/workflows/sandbox-test.yml:1` | 実在 | ○ |
| recon :11「git grep ai_ro の結果は ADR-1024:31,67,80,89,92 と ADR-1037:42」 | 実際の結果は ADR-1024:6,31,80,89,92、ADR-1026:8,36、ADR-1028:8、ADR-1030:8、ADR-1037:42。ADR-1024:67 は "ai_ro" を含まない（fail-closed の行） | ×（必須 M3） |
| design :126-144 / :121-124 / :129-132 / :145 / :25 | 一致 | ○ |
| design `.github/workflows/deploy.yml:577` | :577 `bash scripts/run_all_migrations.sh`（:571 に set -e） | ○ |
| design `docs/handoff/migration-deadlock-retry/design.md:8` / `docs/handoff/shime-review-exclude/design.md:506` | 一致。`git grep "skip ai_ro\|views stay dropped" origin/main` は台本 :130 とこの2件だけ | ○ |

## 2. K1〜K3 と set -e / EXIT trap

【事実】macOS の /bin/bash 3.2.57 で、関数と同じ形の写し（scratchpad の t1.sh）を試した。
- `sh -c 'exit 3'` で set -e が止める → trap の中は rc=3。`if ! <失敗するコマンド>` の中で失敗しても set -e で抜けず、警告の分岐に入る。最後の終了コードは 3。
- rc=0 で作成が失敗 → 終了コードは 0。
- 結論: EXIT trap の中の `exit "${rc}"` は終了コードとして効く。`if !` の中の docker exec の失敗は set -e の対象外。K3 は通常の失敗では満たす。
- 【未確認】本番の bash 5（ubuntu）では試していない。T1/T4 を sandbox-test（ubuntu-latest）で流せば確かめられる。

K1: 通常の失敗では満たす。ただし M1 の場合（作成が待ち続ける）は満たさない。  
K2: 作成が元の表に取るのは ACCESS SHARE だけ（recon F5、/tmp/CC報告ファイル/ai-ro-restore/recon-raw-2.md:50-51）。読み取りとはぶつからない。待たせるのは、この後に来る ACCESS EXCLUSIVE の要求だけ。

## 3. 失敗時に作ってよいか（秘密列）

- 拒否リスト（create SQL :23）は、流した時点のカタログの列名だけで決まる（:34-41）。途中まで進んだ DB にも同じ条件が当たる。持ち主の権限（jarvis）と RLS の扱いも成功回と同じ。失敗時だけの新しい漏れ道は見つからなかった。
- 【事実】run_sql 334本のうち 321本は明示の BEGIN が無い（1文ずつ確定する）。そのため、成功回には無い途中の状態（例: 改名の途中の列名）が残ることがある。秘密系の列の `RENAME COLUMN` は、登録済みの BEGIN 無し migration に 0件だった。今は害が無い（任意 O1）。

## 4. lock_timeout を足さない判断

- lock_timeout を足すと 55P03 が 1本ずつの `EXCEPTION WHEN others`（create SQL :68）に飲まれ、そのビューだけ欠けたまま成功扱いになる。この点は正しい。ただし表名は NOTICE（:74）に出るので「黙って」ではない（任意 O6）。
- 欠けているのは、待ちの上限についての検討（必須 M1）。

## 5. 受け入れ基準の判定しやすさ

- T1・T2・T4・T5: ○×で判定できる。
- T3: 「警告が出る」の文面が決まっていない（任意 O3）。
- T6: `^AI_RO_CREATE_SQL=` は :125 の1件、`^trap _ai_ro_create_on_exit EXIT` は :145 の1件。一意に取れる。切り出した範囲に trap の登録が入ること、POSTGRES / PSQL / REPO_DIR と set -e を試験側で用意することを前提として書くこと（任意 O3）。
- K-本番1: ○×で判定できる。ただし成功回では今も「skip ai_ro views」は 0行なので、変更の効果は測れない（後戻りしていないかの確認になる）。
- K-本番2 と K1 の「本数が直前の成功回と同じ」: 失敗した回で表が増えたり減ったりすると、正しく動いていても×になる（任意 O2）。

## 6. 影響範囲

- 台本を実際に動かすのは `.github/workflows/deploy.yml:577` だけ。`scripts/migration-dryrun-report.py:27` や migration-test.yml / migration-guard.yml は `^run_sql` の行を読むだけで、台本は動かさない。見落としは無い。
- 抜けていた点: 作成 SQL の既存試験 `backend/tests/ops/test_ai_ro_views.py:29`（変更の影響は無いが、T1 の秘密列の確認に使える）。`docs/handoff/ai-readonly-db-path/usage.md:38-40`（§4 デプロイ中の 42P01）は失敗回に触れていない（任意 O4）。

---

## 指摘

### 必須

- **M1 失敗時の作成に待ちの上限が無い。** 10/21 の失敗は、products の鍵を離さない相手が原因だった（ADR-1037:40-41）。相手がどの種類の鍵を持っていたかは未確認（ADR-1037:41、/tmp/CC報告ファイル/ai-ro-restore/recon-raw-2.md:69）。相手が ACCESS EXCLUSIVE を持っていると、作成（:139 は lock_timeout も statement_timeout も無し）は打ち切りの10分まで待つ。その場合、終了コードは元の rc=3 ではなく「打ち切り」になり、K1・K3 を満たさない。design R4 は在庫表の読み取りの待ちしか扱っていない。
  - 対処の候補（どちらかを design に書く）:
    - (a) 失敗8回のログから、鍵を持っていた相手の種類を確かめ、根拠を足す。
    - (b) 作成 SQL は変えずに、:139 の docker exec に `PGOPTIONS="-c statement_timeout=…"` を渡す。PostgreSQL 16 の公式文書（plpgsql-control-structures「OTHERS matches every error type except QUERY_CANCELED and ASSERT_FAILURE」）のとおり、statement_timeout（57014）は :68 に飲まれない。全体がロールバックし、警告の分岐に入る。§5 の「lock_timeout は不採用」とは矛盾しない。
  - どちらの場合も、受け入れ基準に「ACCESS EXCLUSIVE を持つ接続がある状態で失敗したとき、作成が N 秒以内に終わり、終了コードは元の rc」を足す。
- **M2 打ち切り・信号の扱いが事実と違う。** design §2 の対象外「10分で打ち切られた場合…今と同じく作らないまま終わる」と、recon 不明点5「今の作りでも作成しない」は、実測と合わない。bash 3.2 で SIGTERM / SIGHUP を送ると、EXIT trap が rc=0 として動き、今の関数でも作成に進んだ（scratchpad t1.sh: trap rc=0、TERM の終了コード 143 / HUP の終了コード 129）。本番の bash 5 と、appleboy/ssh-action が打ち切るときに遠隔へ信号を送るかは未確認。記述を事実に合わせるか、sandbox（ubuntu）で信号のときの試験を足すこと。
- **M3 recon :11 の ADR 検索結果が実物と違う**（上の表）。特に ADR-1026:36 は、この drop→create の仕組みを根拠にしている（ADR-1026:36 が指す行番号 :80,86-106 は今は古い）。結果を貼り直し、ADR-1026 / ADR-1030 に影響が無いことを1行書く。

### 任意

- O1 design R1 の「いつ流しても同じ」を「流した時点の列名で決まる。途中の状態の列名にも同じ判定が当たる」に直す。BEGIN 無し 321本の事実を添える。
- O2 K1・K-本番2 の本数の基準を「同じ回の `ai_ro views created: N` と reader の道で数えた本数が同じで、failed 0」にする。
- O3 T3 の警告文を固定する（例「ai_ro views の作成に失敗」）。T6 の前提（trap の登録が範囲に入る、変数と set -e は試験が用意する）を書く。
- O4 影響範囲に `backend/tests/ops/test_ai_ro_views.py:29` を足す。usage.md §4 に失敗回の扱いを書き足すか検討する。
- O5 recon の create SQL :29 を :29-30 に、台本 :121 を :121-122 に直す。
- O6 §5 B・ADR 改訂欄の「黙って欠ける」を「入れ替えは成功扱いのまま一部が欠ける（表名は NOTICE に出る）」に直す。

## 未解決

- 本番の bash 5 での EXIT trap の終了コードと、信号を受けたときの動き（未確認。M2）。
- 10/21 の失敗で products の鍵を持っていた相手の、鍵の種類（未確認。M1）。
- appleboy/ssh-action が10分で打ち切るとき、遠隔の台本に信号が届くか（未確認。M2）。

## PO 承認要否 / Generator 着手可否

- Ready For Generator: false（REVISE）
- PO Approval Required: 必須の修正で成功条件（K1〜K3）が変わらなければ不要。M1 で (b) を選んで「作成を N 秒で打ち切る」を足す場合も、K の範囲の中に収まる。

---

## 再審査（2026-10-21、2回目）

**判定**: **REVISE**（design.md・recon.md・ADR-1024 改訂欄・usage.md は合格。直すのは card.md の1件だけ）

### 前回の必須の確認

| 指摘 | 確認 | 結果 |
|---|---|---|
| M1 待ちの上限 | design §3（:50, :63-64）。`AI_RO_CREATE_TIMEOUT` は既定 30s、`docker exec -e PGOPTIONS="-c statement_timeout=…"` を渡す。`run_sql`（`scripts/run_all_migrations.sh:84`）と同じ渡し方。PostgreSQL 16 公式文書で、OTHERS は QUERY_CANCELED を捕まえないこと（plpgsql-control-structures）と、57014=query_canceled・55P03=lock_not_available（errcodes-appendix）を確かめた。打ち切りは DO ブロック（create SQL :11-76）の中から外へ伝わり、ON_ERROR_STOP（:25）で psql が 0 以外を返す。BEGIN（:6）の中なので全体が戻る。R4（:119-122）と T7（:144）を足し、§5 B'（:106）で選んだ理由も書いてある | ○ |
| M2 信号 | design §2（:29-32）と recon 不明点5 が、実測と未確認の点に合った。T8 は記録だけ（:145） | ○ |
| M3 ADR 検索 | recon :11 が `git grep` の実際の結果（ADR-1024:6,31,80,89,92 / ADR-1026:8,36 / ADR-1028:8 / ADR-1030:8 / ADR-1037:42）と合った。ADR-1026:36 に影響が無いことも書いてある | ○ |

O1〜O6: design R1（:112-116）、T1・K-本番2（:139, :148）、T3・T6（:141, :146）、影響範囲（:97-98）、§5 B（:105）に入った。

成功した回への影響: 成功した回でも、作成は30秒で打ち切られるようになる（design :83）。今の作成は約0.7秒なので約40倍の余裕がある。打ち切られても終了コードは 0 のままで、K3 に反しない。ADR 改訂欄にも書いてある。

### 指摘

#### 必須

- **N1 card.md の T3・T7 が、正しく動いても FAIL になる**（`docs/handoff/ai-ro-restore-on-failure/card.md:42-45`, `:51-55`）
  - 本番では、作成の前に必ず :119 でビューを外す。試験は切り出した範囲（:125〜:145）だけを動かすので、この「外す」が入らない。
  - そのため T2・T5 で作った `ai_ro.sb_items` が残る。T3（ロールが無い）と T7（打ち切り）では作成全体が戻り、作成 SQL の `DROP SCHEMA`（create SQL :8）も戻る。前のビューが残るので、「ビューが0本」の条件で FAIL になる。
  - T7 の想定分岐「一部のビューだけが残る → NEEDS_DECISION」（card :83）にも当たってしまい、無駄な止まりになる。
  - 直し方: 失敗の道の試験（少なくとも T1・T3・T7。できれば各試験）の前に `migrations/20261017_125900_drop_ai_ro_views.sql` を流して、:119 を再現する、とカードに書く。

#### 任意

- P1 design §3 のコメント案（:77）が「いつ流しても同じ」のまま。R1 に合わせて「流した時点の列名で決まる」にする。
- P2 design :125「戻し方: ファイル2つ」が古い。今は台本・試験・ADR・usage.md などが入る。「PR を revert（DB の形は変えない）」でよい。
- P3 usage.md :40 は、足した1文が「その間は 42P01」の前に入ったので、「その間」が何を指すかずれた。足した文を行末に移す。

### 未解決

- 本番の bash 5 での信号のときの動きは、T8 の記録待ち（合否には入れない）。
- 10/21 に products の鍵を持っていた相手の、鍵の種類は未確認のまま。上限30秒を付けたので、結果は左右されない。

### PO 承認要否 / Generator 着手可否

- Ready For Generator: false（N1 を card.md に直せば、もう一度の審査なしで APPROVE としてよい。design 側に必須は残っていない）
- PO Approval Required: 不要（K1〜K3 は変わらない）

## 再審査の条件の消化（Planner 記録、2026-10-21）

- N1: card.md に「T1〜T5・T7・T8 の直前に `migrations/20261017_125900_drop_ai_ro_views.sql` を流す」を足した。
- P1: design §3 のコメント案を、R1 の書き方（流した時点の列名で決まる）に合わせた。
- P2: design の「戻し方」を、動きが変わるファイルは1つ、という書き方に直した。
- P3: usage.md の足した1文を、行の終わりに移した。
- 再審査の結論は「N1 を直せば再審査なしで APPROVE」だった。N1 を直したので、判定は **APPROVE**。
- 未解決: 本番の bash 5 で信号を受けたときの動き（T8 で記録する）。10/21 の鍵の持ち主の種類（30秒の上限で結果は左右されない）。
