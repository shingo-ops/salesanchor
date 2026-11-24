# 設計審査（architect）1回目 — 段階4 便3 実装カード

判定: **REVISE**（直す必要あり。R は 1 件）

- 理由1: 変えるファイルの sha256 が `scripts/migration-guard/reference-allowlist.tsv:7` に固定されており、カード §1 の範囲に入っていない。このまま実装すると PR の migration-guard が落ちる（R1）。
- 理由2: §0 の行番号と中身、EXIT trap・記録の対象外の説明、試験の土台、伏せたまま残る列、戻し方は、origin/main の実物と合う。
- 理由3: R1 以外の指摘は軽いもの（L1〜L4）だけ。R1 を §1・§2・§5 に足せば APPROVE できる。

審査した物: origin/release/ai-ops-stage4-bin3（77c82caa9）の `docs/handoff/ai-ops-247/card-stage4-bin3.md`。実物は origin/main（f6d54446e0b4f2573b6331a515d23a087e65e2b5）。

## 直す点（R）

### R1: 変えるファイルの sha256 の例外が漏れている（実装すると migration-guard が落ちる）

事実:
- `scripts/migration-guard/reference-allowlist.tsv:7` に `migrations/20261024_100300_create_ai_cloud_views.sql` の行があり、sha256 は `de1a32db3db2a20e6f6b1cf8be55506e48b56f90bcc75d84e9260664452caecf`。origin/main の同ファイルの `sha256sum` と一致する（今は有効な例外）。
- `scripts/check-migration-value-writes.py:164-174`: 一覧にあるファイルの sha256 が変わると「中身が変わったので例外は効かない」で確認 8 が失敗する。
- 同 `scripts/check-migration-value-writes.py:242-256`（repo モード）: 一覧の sha256 が今の中身と違うと problems になる。`.github/workflows/migration-guard.yml:441` が `python3 scripts/check-migration-value-writes.py repo` を流す。
- カード §1「触らない／変える」の一覧に `scripts/migration-guard/reference-allowlist.tsv` が無い。§1 は「このほかは触らない」と書いており、§3 にも sha の分岐が無い。実装役はそのまま止まるか、範囲外を触るかの二択になる。
- 過去の同種の変更は、この行の理由欄に「分類1列追加」「分類1行追加」と書き足している（同ファイル :7）。

直し方:
1. カード §1「変える」に `scripts/migration-guard/reference-allowlist.tsv` の :7 を足す。
2. §2 に手順（７）を足す。`migrations/20261024_100300_create_ai_cloud_views.sql` を最終形にしたあと、`sha256sum migrations/20261024_100300_create_ai_cloud_views.sql` で出した値を :7 の 2 列目に入れる。理由欄（3 列目）に「／ ai-ops-stage4-bin3（ops_incidents の alertname・severity を allow に変更）」を足す。列は 4 つ・タブ区切りのまま。ファイルを直したあと、sha を取り直すのを最後の手順にする（順番を間違えると再び食い違う）。
3. §2（６）に `python3 scripts/check-migration-value-writes.py repo` を足し、終了コード 0 を確かめる。
4. §5 受け入れ基準に「migration-guard の repo 検査が緑（sha256 が今の中身と一致）」の行を足す。
5. §3 の分岐に「sha256 の行が見つからない・列が 4 つでない → 止まる」を足す。

## 観点ごとの確認結果

### (1) §0 の行番号と中身（1件ずつ。ほぼ一致）

一致:
- `migrations/20261024_100300_create_ai_cloud_views.sql` :3（「1165 行を入れ直す」）、:6（tsv の元の記述）、:166（alertname・mask）、:168（severity・mask）、:169（status・allow）。
- `docs/handoff/cloud-case-ai/stage1-column-class.tsv` :232（alertname・mask）、:240（severity・mask）。どちらも 6 列（`awk -F'\t'` の NF=6）。
- `backend/app/routers/ops.py` :230（`require_ops_ingest`）、:253-254（alertname・severity）、:559（`_INSERT_HUMAN_INCIDENT_SQL`）、:565（`'discord-bug-report'`。INSERT の列に severity は無い）。
- `scripts/lib/migration_record.sh` :61-86（`mr_targets`。対象は `^run_(sql|py)[[:space:]]` の行だけ）。
- `backend/tests/ops/test_ai_cloud_views.py` :486（`== n0 == 1165`）、:424-445（`test_m8_acceptance_masks_counted` の mask 数の突き合わせ）、:1017（`test_t10_calendar_color_key_...`）、:1060（次の `test_t10_detects_added_columns`）。ops_incidents・alertname・severity の語は同ファイルに 0 件。
- `docs/ai-agents/ops-incident-agent.md` :132（「通知の名前（alertname）と強さ（severity）は今は伏せてある」）。
- `migrations/20261024_100000_create_ai_cloud_meta.sql` :16-19（class の CHECK と allow は reason 必須）。

ずれは軽いもの（L1・L2）。

### (2) 本番の移行が記録の食い違いで止まらないか

- 記録の食い違い（`migration_record`）では止まらない。`scripts/run_all_migrations.sh:426` で変数に入り、:445-448 の EXIT trap 内の `docker exec ... < "${REPO_DIR}/${AI_CLOUD_CREATE_SQL}"` で流れる。`run_sql` 行ではないので `mr_targets`（`scripts/lib/migration_record.sh:61-86`）の対象外。カードの説明は事実と合う。
- ただし別の門が 2 つ残る。
  - migration-guard の確認 8 の sha256（R1。カードに無い）。
  - `.github/workflows/migration-test.yml:1346`: このファイルが変わると専用の工程が走る。内容は未読のため、この工程の合否は未確認（実装後の CI で見る）。
- 作成 SQL は失敗しても `build_log` に失敗を書いて終了コードを変えない作りで、移行全体は止まらない（`scripts/run_all_migrations.sh:449-455` 付近）。

### (3) §2（３）の試験が今の土台でそのまま書けるか（書ける）

- 土台: `_new_db(control, prefix)`（`backend/tests/ops/test_ai_cloud_views.py:99`）、`_read(fname)`（:71）、`_rows(conn, sql, role=None, params=None)`（:204）、定数 `_AI_READER_SQL`（:33）・`_META_SQL`（:34）・`_ROLE_SQL`（:35）・`_CREATE_SQL`（:36）、`cluster` フィクスチャ（:111）。カードの流す順（ai_reader → role → meta → ops の表 → create）は、既存の :1017 の試験と同じ順序の前半に、ops の表を足しただけで、順序の問題は見当たらない。
- `ai_cloud_meta.build_columns` の列名は `view_name`・`column_name`・`source`・`source_type`・`class`・`mode`（`migrations/20261024_100000_create_ai_cloud_meta.sql:30-37`）。mode の値は `pass`・`mask`・`mask_bare`・`excluded`（:36）。ビュー名は `schema || '__' || table`（:157）なので `public__ops_incidents` は合う。allow の列は `v_mode := 'pass'`（:119-120）。カードの書き方で通る。
- ops の表の移行 `migrations/20261016_100000_create_ops_incident_tables.sql` は `salesanchor_app` が無くても通る。ロールの GRANT は `IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app')` の中だけ（:120-125）。他の表への外部キーも無い（自己参照のみ。`recurrence_of`）。`gen_random_uuid()` は PG13 以降の標準。よってカードの「ロールが無ければ作る」は不要（L3）。
- build_views は 1 表の失敗を `EXCEPTION WHEN others` で数えるだけ（meta :171 以降）で、ops の表だけの DB でも作成 SQL は通る。1165 行の分類のうち実在しない表の行は単に使われない（:1017 の既存の試験も同じ状況）。
- 試験は admin 接続（superuser）で `build_columns` を読む。`ai_reader` の SET ROLE は不要で、`_rows(conn, sql)` でよい。

### (4) 伏せたままにする列が伏せたまま残るか（残る）

- `labels`・`annotations`・`fingerprint`・`root_cause`・`review_note`・`detection_path`・`first_aid_result` は `migrations/20261024_100300_create_ai_cloud_views.sql:167` の 1 行で mask。カードは :166・:168 だけを変えるので、:167 は影響を受けない。
- 分類に無い列は、型で判定される（meta :119-129 付近）。text・jsonb は mask になる。数・日付・uuid・真偽・enum だけが pass。alertname・severity が 'allow' に変わるのは分類表の行の変更だけで、他の列には波及しない。
- 名前の拒否リスト（meta :76）に alertname・severity・labels などは当たらない（`password`・`_token`・`hash` など）。allow が `excluded` に負けて見えなくなることはない。
- 行数: :166・:168 は class と reason の置換だけで、行数は 1165 のまま（`backend/tests/ops/test_ai_cloud_views.py:486`）。

### (5) 戻し方 §6（成り立つ）

- 分類表は毎回の作成 SQL の先頭で空にして入れ直す（`migrations/20261024_100300_create_ai_cloud_views.sql:3`）。revert して次の移行の EXIT trap が走れば、2 列は mask に戻る。表の形は変えないので戻しのファイルは不要、というカードの説明は成り立つ。
- ただし revert でも `reference-allowlist.tsv` の sha256 が食い違う。revert は R1 の変更も一緒に戻すので問題は出ない（R1 を同じ PR に含めることが条件）。§6 に「sha の行も同じ PR で戻る」と一言足すとよい（L4）。

## 軽い指摘（L）

- L1: §0 の `scripts/run_all_migrations.sh:425-449` は、425 がコメント、426 が変数、:428 が関数の開始、:445-448 が作成 SQL の実行、:465 が `trap`。要点（:448）は合っている。範囲は `:426・:445-448・:465` とするとよい。
- L2: §0「前例: 2026-11-16・11-18・11-20 に同じファイルを変えた」は未確認。この作業場所の履歴は浅く（`git rev-parse --is-shallow-repository` は true）、`git log origin/main -- migrations/20261024_100300_create_ai_cloud_views.sql` で見えるのは f09362af3（2026-11-21、#5650）の 1 件だけ。日付と件数は、フル履歴のある手元で確かめた値であることを書くか、`reference-allowlist.tsv:7` の理由欄の前例（card-s2-2c・card-E）を根拠にするとよい。
- L3: §2（３）の「`salesanchor_app` のロールが無ければ作る」は不要。作ると、クラスタ共通のロールが残る（`backend/tests/ops/test_ai_cloud_views.py:80-91` の `_Cluster.cleanup` は ai_reader・ai_reader_cloud・aic_owner しか消さない）。省くか、省かない理由を書く。
- L4: §6 に「revert は `reference-allowlist.tsv` の sha も戻す（同じ PR に含める）」を足す。§4 に変更は無い。
