# コード審査（便2 v6）— release/review-edit-v6 @ 381231bd1

審査者: Opus（コード審査役。コードは編集していない）
基準: `docs/handoff/review-edit-all-fields/design.md` §5（D1〜D6・5-2・5-3・5-4）、`review-opus-bin2.md` r2（APPROVE・任意 P1〜P3）
差分: `git diff origin/main...HEAD`（21 ファイル、+642/−60）

## 判定: REVISE

必須 1 件（新しい PG 試験が CI で止まる）。本体コード（backend・frontend）は設計どおりで、正しさの問題は見つからなかった。

---

## 1. 実行した確かめ（事実）

| 確かめたこと | 結果 | 根拠 |
|---|---|---|
| import の循環 | `import app.main` と変更した 6 モジュールの単独 import がすべて rc=0 | venv312 で `python -c "import ..."` |
| ruff | `All checks passed!`（変更した backend 9 ファイル） | `ruff check ...` |
| 非 PG の pytest | 252 passed。失敗 2・エラー 1 はすべて `GITHUB_ACTIONS` が無いことによる PG fixture の assert（`test_e5_does_not_overwrite_empty_or_manual_condition` の 2 件は既存の PG 試験、エラー 1 件は新規の `test_v6_value_overrides_pg.py`） | `pytest -o addopts="" tests/test_v102_value_overrides.py tests/test_unit_recovery.py tests/test_line_analysis_v102_svc.py tests/test_item_corrections.py tests/test_v102_transcription.py tests/test_v6_value_overrides_pg.py` |
| vitest `src/features/tcg-analysis-review` | Tests 209 passed。Unhandled Error 1 件は Storybook のブラウザ（Playwright の chromium が手元に無い）で、この変更とは関係ない | `npx vitest run src/features/tcg-analysis-review` |
| PG 試験を手元で流すこと | **流していない**。使い捨てのクラスタを作ろうとしたところ、`psql -c CREATE DATABASE` がフック（psql-write-guard）で止められたため。言い換えての実行はしていない | — |

## 2. 設計との照合

### 5-2 backend

| 項目 | 実装 | 判定 |
|---|---|---|
| H: `v102_analysis_lock_key` を H へ移す（D5） | `v102_human_decisions_svc.py:470-472`。中身は `f"v102_analysis:{job_id}"` で変わっていない。transcription は `v102_transcription_svc.py:24` で import し、定義は消えている。`line_analysis_v102_svc.py:1270` と H:593 の直書きもこの関数に揃えた | 合う |
| `item_basic_rejection`（404→422） | H:446-452 | 合う |
| `item_rejection` は 404→409→422 を保つ | H:455-464。`None`→404、v102 でない→409、そのあと `item_basic_rejection`。v6 で source が違っても 409（試験 `test_item_basic_rejection_does_not_check_version_but_item_rejection_does`） | 合う |
| `save_value_override` は basic を使う | H:589。docstring の 409 も消してある | 合う |
| R: value-override を basic にし、v102→再解析／v6→`await run_in_threadpool(schedule_distribution)` | `item_corrections.py:276,286-290`。`schedule_distribution` は例外を外へ出さない（`tcg_extraction.py:670-693`） | 合う |
| A: 鍵は全マスタを読んだ後、extraction_items の SELECT（FOR SHARE）の直前に1回 | `tcg_analyzer_svc.py:1441-1445`。鍵の文字列は `v102_analysis_lock_key(str(extraction_job_id))` | 合う |
| 鍵〜最初の commit（A:1837）の間に rollback・commit が無い | 1442〜1837 の `session` の呼び出しは execute・`load_v102_decisions`・`reanalysis_condition` だけ。`load_v102_decisions`（H:231-279）と `reanalysis_condition`（`tcg_condition_review_svc.py:286-297`）に rollback・commit は無い | 合う |
| ループの前に `load_v102_decisions` を1回 | A:1477（変数名 `human_decisions`。v5+ 分岐の `decisions` と名前がぶつからない） | 合う |
| empty_box の理由の後、`reanalysis_condition` の前に重ねる。dict のキー8つ。unit_id は str へ戻す | A:1699-1713。キーは `quantity_normalized, price_normalized, unit_id, unit_canonical, unit_resolved, note_ja, status, exclusion` で H の `_CURRENT_VALUES_SQL` と同じ。`unit_uuid = str(merged["unit_id"]) if ... else None`。単位の辞書 `unit_canonical_to_uuid` は H の `load_unit_canonical_ids`（A:78-80）と同じ SQL・同じ中身 | 合う |
| review_reasons・needs_review・stats は重ねる前の値 | `stats["unit_resolved"]` は A:1526 で重ねる前に数え、review_reasons は A:1690-1697 で重ねる前に作る。候補（candidate、A:1715-）は重ねた後なので人の値が束縛ハッシュに入る | 合う |
| 商品の直しがある件の分岐（A:1503-1513）に手を入れない | 触っていない | 合う |
| E3a/E4 の WHERE に `AND unit_resolved = FALSE`、rowcount=0 の扱い（P1） | `tcg_unit_recovery_svc.py:881,1186`。E3a は書けた行だけ `applied_updates` に入れて `e3a_updates` を置き換える（:870,891-893）ので、`e3a_recovered` にも E5 の対象（:930 以降の `ar_ids`/`e3a_map`）にも入らない。E4 は rowcount があるときだけ `resolved += 1`（:1195） | 合う（P1 解消） |
| E3a/E4 を v102 が呼ぶか | `git grep` で呼び出しは A:1850,1860 だけ（v6 のみ） | 事実の確認 |
| E4 の SELECT は既に `ar.unit_resolved = FALSE` | :1155 付近（関数内の SELECT の WHERE に `AND ar.unit_resolved = FALSE`） | 競合時以外は結果が変わらない |
| 対象外（v6 の再解析を積む仕組み・resolve_status_v2・配信 SQL・一覧 SQL・save_condition_review） | 差分に無い | 合う |

P2（鍵の正本の移し替え）: `git grep v102_analysis_lock_key backend/tests` は新しい試験 2 か所だけで、monkeypatch しているものは無い。解消。

### 5-3 frontend

| 項目 | 実装 | 判定 |
|---|---|---|
| `reviewFixRows.ts` の v102 条件を外す | `reviewFixRows.ts:37-43` | 合う |
| `availableFixChoices` の value の v102 条件を外す。ackableReasonCodes（`ReviewFixWizard.tsx:27`）と `ConditionReviewPanel.tsx:25` は残す | `ReviewFixWizard.tsx:39`。27 行目と ConditionReviewPanel は差分に無い | 合う |
| 保存後の文言の出し分け | `ReviewValueFixForm.tsx:87`。`is_v102 === true` なら `saved`、ほかは `savedNoReanalyze` | 合う |
| i18n（ADR-027） | ja「直しました」／en「Saved」を同じキー `reviewItem.valueFix.savedNoReanalyze` で両方に追加（各 1 件）。新しいハードコード文字列は無い。新しい UI 部品も無い（ADR-144） | 合う |
| 既存試験の期待値 | `ReviewFixWizard.test.tsx`・`ReviewItemDrawer.test.tsx`・`ItemComparison.test.tsx`・`reviewFixRows.test.ts` を直してある | 合う |

`is_v102` は一覧 API が返す（`tcg_analysis_review_svc.py:253`、`routers/tcg_analysis_review.py:92` で既定 False）。

### 5-4 受け入れ基準

| 基準 | 試験 | 判定 |
|---|---|---|
| V1 | `reviewFixRows.test.ts` の V1（8 キー・scope・manual_values）。state は空箱関連のときだけ、は既存の試験 | 満たす |
| V2 | `test_value_override_v6_saves_and_schedules_distribution_once_without_reanalysis`、`..._rejects_source_mismatch_and_missing_without_scheduling`、v6→409 の parametrize 行を削除、`item_rejection` の v6 は 409（source 不一致でも） | 満たす（即時 UPDATE そのものは PG 試験側） |
| V3 | 同上で `scheduled == [1]`・`enqueued == []`、v102 は `enqueued == ["job-1"]`・`scheduled == []` | 満たす |
| V4・V5 | `test_v6_value_overrides_pg.py:72-106` | 中身は満たす（ただし下の M1 で試験全体が CI で止まる） |
| V6 | 同 `:108-118` | **M1** |
| V6b | `test_lock_key_has_one_source_and_unchanged_string` ＋ import 確認 | 満たす |
| V6c | E4 は偽セッションで振る舞いを確かめる。E3a は `inspect.getsource` の文字列確認だけ | 満たす（O2 参照） |
| V6d | `ReviewValueFixForm.test.tsx` の V6d | 満たす |
| V7 | 非 PG と vitest は緑（上の表）。PG の既存試験は手元で未実行 | 非 PG は満たす。PG は【未確認】 |
| V8 | PG 試験の追加は 1 本 | 満たす |

---

## 3. 指摘

### 必須（M）

**M1 PG 試験の鍵の確かめが、lock_timeout が消えて止まったままになる（CI の pytest-run が 15 分で落ちる）**

- 場所: `backend/tests/test_v6_value_overrides_pg.py:108-118`
- 事実:
  1. 試験は `with Session(engine) as session: session.execute(text("SET lock_timeout='200ms'"))` のあと `analyze_extraction_job(session, jobid)` を呼ぶ（:111-114）。`SET` は Session が始めた取引の中で走る。
  2. `analyze_extraction_job` は鍵より前に `load_normalization_rules(session)`（`tcg_analyzer_svc.py:1388`）を呼ぶ。これは `{TCG_SCHEMA}.tcg_normalization_rules` を読み、失敗すると `session.rollback()` する（`tcg_analyzer_svc.py:953-972`）。
  3. pg fixture は `analyzer.TCG_SCHEMA` を `tenant_901` に差し替える（`test_tcg_work_matching_integration.py:369-370`）。`tenant_901` を作る `provision`（:49-54）が流す `20260906_120000_create_tcg_tables_t001.sql` の CREATE TABLE 一覧に `tcg_normalization_rules` は無い。`migrate()` が作るのは `public.tcg_normalization_rules`（`migrations/20260921_110000_pipeline_tables_public.sql:337`）だけ。よってこの読みは失敗し、rollback が走る。
  4. PostgreSQL では、取引の中の `SET`（LOCAL なし）は取引が rollback されると取り消される（PostgreSQL 公式文書の SET の項）。rollback の後の Session は新しい取引（接続も pool から取り直し）で続く。
  5. 結果、`pg_advisory_xact_lock` は lock_timeout なしで待つ。鍵を持つ `holder` は同じスレッドの `finally`（:116-118）でしか放されないので、待ちは終わらない。
  6. CI の `pytest-run` は `timeout-minutes: 15`（`.github/workflows/test.yml:119`）。pytest-timeout の設定は backend に無い（`grep timeout backend/pyproject.toml backend/requirements*.txt` で 0 件）。
- 【推測】CI ではこの試験で pytest が止まり、15 分で `pytest-run-internal` が失敗し、必須チェック `pytest (SQLite + PostgreSQL RLS)` が赤になる。手元の PG で流していないので、実際に止まることは**未確認**。ただし 1〜6 はコードと公式の挙動だけで決まる。
- 直し方（例）: 解析側の接続に、接続を開く時点で lock_timeout を持たせる。rollback で消えない。止まり続けないよう statement_timeout も付ける（打ち切りは 57014 になるので、55P03 の assert と区別できる）。

  ```python
  waiter_engine = create_engine(
      engine.url,  # URL オブジェクトのまま渡す（str にするとパスワードが伏せられる）
      connect_args={"options": "-c lock_timeout=200ms -c statement_timeout=10s"},
  )
  holder = Session(engine)
  try:
      holder.execute(text(decisions_svc._LOCK_SQL), {"key": decisions_svc.v102_analysis_lock_key(jobid)})
      with Session(waiter_engine) as session:
          with pytest.raises(OperationalError) as caught:
              analyzer.analyze_extraction_job(session, jobid)
      assert getattr(caught.value.orig, "pgcode", None) == "55P03"
  finally:
      holder.rollback()
      holder.close()
      waiter_engine.dispose()
  ```

  鍵を持つ取引（holder）を最後に閉じる今の順は正しいので、そのまま残す。fixture 側に `tenant_901.tcg_normalization_rules` を作る直し方は、ほかの PG 試験に影響するので取らない。

### 任意（O）

- **O1 PG 試験の残りの部分**: fixture の使い方（`pg` の import と `# noqa: F401`、`decisions_svc.TCG_SCHEMA` の monkeypatch、試験後に DB を DROP する fixture の後始末）、`_save` が毎回 async engine を dispose すること、状態マスタの `status_id` が ST0001/ST0002/ST0004 で一意（`uq_tcg_status_master_status_id`）、`item_corrections` の `field_name` に CHECK が無い（t001:216-225）ことは確かめた。V4/V5 の流れで問題は見つからなかった。PG を流していないので結果は【未確認】。
- **O2 E3a の振る舞いの試験**: `test_e3a_update_sql_is_guarded_by_unit_resolved_false`（`backend/tests/test_unit_recovery.py:405-411`）はソースの文字列を見るだけで、「rowcount 0 の行が `e3a_recovered` と E5 の対象から外れる」ことは確かめていない。E4 と同じ偽セッションで `e3a_recovered == 1` を見る試験があると強い。V6c の文言（SQL 文字列か PG）は満たしているので任意。
- **O3 P3（参考）**: 商品の判断（resolved_product_code/work_id）は鍵より前に読む（A:1398-1437）。r2 の記録どおり今回の守りの範囲外で、悪化はしない。対応は不要。

---

## 4. 戻し方・測り方

設計 §5-5 のままでよい（PR の revert。override_* の行が残っても、古いコードの v6 解析は読まない）。M1 は試験だけの直しなので、本体の戻し方・測り方は変わらない。

## 5. 再審査で見ること

- M1 の直しで、試験の鍵を確かめる部分が lock_timeout の付いた別接続で走り、CI の `pytest-run-internal` が緑で、`test_v6_value_overrides_pg.py` が passed（skip でない）と出ていること。
