# 設計 — 接続を貸し出しに戻すたびに会社の文脈を消す（Bx・ADR-1070）

- 状態: 設計案（Opus 作成）。審査前。
- 基準: origin/main 170ff9612（2026-11-07 fetch）
- 前段の調査: docs/handoff/s1-rls-stage5/recon-pool-reset.md（r1〜m8）・xtenant-evidence.md（T 箇所と本番の実測）・recon-pool-reset-m9.md（文脈なしで RLS 表に触る箇所の全数）
- 関係する決定: ADR-131（get_db の finally で文脈を戻す）・ADR-072（tenant schema 修飾と commit 後の reset_tenant_context）・ADR-1067（S1 段階④）・ADR-065（準備済み文のキャッシュ）

## 1. 目的と利用者に見える変化

- 目的: ある要求が DB の接続に残した「会社の番号（app.tenant_id）・運営者の印（app.is_operator）・探す場所（search_path）」が、次にその接続を借りた別の要求に見えないようにする。
- 今（事実）: commit の後に流した SET は、close の rollback で消える（recon m1 手順 1: 返却後も `is_operator='true'`）。get_db の finally の `clear_tenant_context`（backend/app/auth/dependencies.py:386-405）は commit の後に流れるので効かない。pool_size 2 以上では、commit の後に同じ session で読むと別の要求の会社の文脈が見えた（recon m7: 20/20）。
- 変えた後: 接続を返すたびに rollback → `RESET ALL` → commit を流す。借りた直後の文脈は必ず空（recon m1 Bx・m2 Bx・m7 Bx 20/20 が空）。
- 利用者に見える変化: 無し（画面・応答は同じ）。変わるのは、文脈を張らずに RLS の表に触る箇所が「前の値で偶然動く」から「0 行・失敗」に変わること。そうなる箇所はこの便で全部直す（§4）。

## 2. 何を入れるか（Bx）

場所: backend/app/database.py の `engine = create_async_engine(...)` の直後。postgresql のときだけ。

```python
# 変更前（backend/app/database.py）
engine = create_async_engine(DATABASE_URL, **_engine_kwargs)

# 変更後
if DATABASE_URL.startswith("postgresql"):
    _engine_kwargs["pool_reset_on_return"] = None   # pool 自身の rollback を止め、下のハンドラに任せる
engine = create_async_engine(DATABASE_URL, **_engine_kwargs)

def _reset_session_state(dbapi_connection, connection_record, reset_state):
    if reset_state.terminate_only:          # invalidate・GC で捨てる接続は触らない
        return
    dbapi_connection.rollback()             # 開いている取引を閉じる（失敗した取引も）
    cur = dbapi_connection.cursor()
    try:
        cur.execute("RESET ALL")            # app.tenant_id・app.is_operator・search_path を初期値へ
    finally:
        cur.close()
    dbapi_connection.commit()               # RESET を確定させて idle で返す


if DATABASE_URL.startswith("postgresql"):
    event.listen(engine.sync_engine.pool, "reset", _reset_session_state)
```

- 形は測定台本 docs/handoff/s1-rls-stage5/pool_reset_measure.py:50-79 の Bx（`_handler("Bx")`・`event.listen(eng.sync_engine.pool, "reset", ...)`）と同じにする。測った形から変えない。

- 対象外: `admin_engine`（database.py の SA-18 Phase2・jarvis 役・RLS を通らない）と Celery・作業台本の同期 engine（recon r1 #8〜#13）。この便では触らない。
- 順番が公式の例と違う理由: SQLAlchemy 2.0.38 の PostgreSQL の例（dialects/postgresql/base.py の写し /tmp/CC報告ファイル/xtenant/sqla/pg_base.py:265-284）は `pool_reset_on_return=None` と reset ハンドラで「CLOSE ALL / RESET ALL / DISCARD TEMP の後に rollback」。この順だと RESET ALL は開いた取引の中で流れ、最後の rollback で取り消される（recon m1 の A と同じ仕組み: 返却直後の last_query が ROLLBACK で値が残る）。rollback を先にし、最後に commit で確定させる（recon m1: B は `idle in transaction` のまま残り、psycopg2 では次の checkout が落ちた＝m6。Bx は idle・エラー無し）。
- CLOSE ALL・DISCARD TEMP を入れない理由: backend/app は一時表とサーバー側カーソルを使っていない（`git grep -n -i -E "CREATE (TEMP|TEMPORARY) TABLE|stream_results|DECLARE [a-z_]+ CURSOR|\.stream\(|yield_per|LISTEN " origin/main -- backend/app` が 0 件・2026-11-07 170ff9612）。DISCARD ALL は準備済み文も消すので使わない（ADR-065 と m3: RESET ALL は 6 回とも通る）。
- 速さ: 1 回の貸し借りで中央値 +0.44ms（0.997→1.441ms）・p95 +0.28ms（recon m5・手元の DB）。本番の基準値は §6。

## 3. 便の分け方（変更は一度に 1 つ）

| 便 | 中身 | 今の本番での効き目 | 測るもの |
|---|---|---|---|
| 便1 | §4-1 の 7 か所に「commit・rollback の直後に `reset_tenant_context(db, tenant_id)`」を足すだけ | 無し（同じ要求の同じ会社の文脈を張り直すだけ。今は前の値が残って偶然同じ値） | CI・単体試験・配備後 24 時間のエラー件数が基準値から増えない（§6） |
| 便2 | Bx（§2）だけ | 接続を返すたびに文脈を消す | §6 の全項目 |

- 便1 を先に本番へ入れて §6 の K1〜K3 を測ってから便2 に進む。便2 を先に入れると §4-1 の箇所が本番で失敗する。
- どちらも migrations・deploy.yml・本番 scripts に触らない（ADR-135/136 の危険パスではない）。

## 4. 文脈を張らずに RLS の表に触る箇所（m9）の扱い

根拠: recon-pool-reset-m9.md（origin/release/s1-rls-pool-reset-m9 c8dfa799a。表A 116 行＋表B）。BREAK-新 9 起点・BREAK-既 6 起点・未確認 U1〜U7 の全部を、下の 4-1〜4-4 のどれかに振り分けた（漏れ無し）。

### 4-1 便1 で直す（BREAK-新 のうち、Bx がかかる async engine の経路）

直し方はどれも ADR-072 の型。行番号は origin/main 170ff9612。

| 起点 | 場所 | 直し | import |
|---|---|---|---|
| 1 | backend/app/discord_gateway/ticket_channel_writer.py `process_ticket_channel_message` の `await db.commit()`（:249）の直後・`if inserted_row is None:` の前 | `await reset_tenant_context(db, tenant_id)` | :20 の `from app.auth.dependencies import set_tenant_context` に `reset_tenant_context` を足す |
| 2 | backend/app/services/message_translator.py `translate_inbound` の `await db.commit()`（:507）の直後・`logger.info(` の前 | 同上（引数 `tenant_id` は :425） | `from app.auth.dependencies import reset_tenant_context` を足す（今は import 無し） |
| 3a | backend/app/services/priority_scoring.py `calibrate_tenant_weights` の `await db.commit()`（:250）の直後・`return weights` の前 | 同上（引数 :160） | `from app.auth.dependencies import reset_tenant_context` を足す（今は import 無し・:11-20） |
| 3b | 同 `label_lead_messages` の `if saved > 0:` の中の `await db.commit()`（:313）の直後 | 同上 | 同上 |
| 3c | 同 `_compute_and_persist` の `await db.commit()`（:439）の直後・`return CustomerScoreResponse(` の前 | 同上（引数 :386） | 同上 |
| 4 | backend/app/routers/tenant_commission_settings.py `_create_default` の except 側 `await db.rollback()`（:109）の直後 | 同上 | 済み（:33） |
| 5 | backend/app/routers/products.py `delete_product` の `await db.rollback()`（:706）の直後・`record_audit_log` の前 | 同上 | 済み（:32） |
| 7 | backend/app/routers/webhook.py `_create_outbound_lead_for_echo` の `await db.commit()`（:580）の直後・`return lead_id` の前 | 同上（引数 `tenant_id` :540） | 済み（:50） |

- 3a は呼び出し元が 0 件（m9 表D）。同じファイルで型を揃えるために直す（害が無く、将来呼ばれたときの落とし穴を消す）。
- 2 は conv_logs.py:136 → :145 の UPDATE、tasks/translation.py:79 の 2 回目以降の translate_inbound、llm_budget.py:472・:524（m9 表A 行 3・13・14・表B B1）をまとめて直す。
- 3c は customer_priority.py `override_priority_score`（:64-115）の続きの読み書き（m9 表A 行 4・5）も直す。
- 循環 import にならないことを実装役が `python -c "import app.services.message_translator, app.services.priority_scoring, app.discord_gateway.ticket_channel_writer"` で確かめる。
- 本番で今どれだけ通る経路か（q28・2026-11-07 08:44 UTC 読み取り）: 翻訳の保存は会社1 0 件・会社4 35 件（最後 2026-06-28）、Discord 添付の記録は会社1・4 とも 0 件。通る回数は少ないが、直しは無害なので全部入れる。

### 4-2 Bx の影響を受けない（直さない・理由つき）

| 起点 | 理由（根拠） |
|---|---|
| 6（calendar_service.py:303 の commit の後の :306） | :303 の commit が失敗した後の except 側。取引が中断状態なので Bx の有無にかかわらず UPDATE は通らない。commit が成功する側は :271-272 で reset 済み・google_calendar の `_refresh_if_needed` も commit の後に reset（:293-294）。xtenant-evidence.md §2 の T4 を「漏れではない」に改訂 |
| 8（tasks/refresh_meta_tokens.py） | 自前の同期 engine `create_engine(DATABASE_URL)`（:97-99）。Bx は app.database の async `engine` にだけかける（U3 の答え） |
| 9（tasks/verify_meta_subscriptions.py） | 同上（:82-84） |
| BREAK-既 data_deletion（m9 表A 行 32-34） | 自前の ADMIN engine（tasks/data_deletion.py:59）。同上（U4 は Bx の範囲外になるので判断に要らない） |

### 4-3 Bx の前から動いていない既存の不具合（この便に混ぜない・PO へ別件で報告）

| 起点 | 事実 | 扱い |
|---|---|---|
| BREAK-既 1（配信失敗の Discord 通知 routers/notifications.py:166・:187 を tcg_distribution_svc.py:1160-1184 が tenant_id=4 で文脈なしに呼ぶ） | 本番 tenant_004.notification_logs は全期間 0 行（q26）。Bx の前から一度も記録されていない＝退行ではない | 直すと外へ出る通知が新たに始まる。範囲外。PO へ別件 |
| BREAK-既 4（discord_role_sync.py:112-130 `_update_sync_status`） | 本番の全 schema で discord_role_sync_at が NULL（q27・0 行）。一度も成功していない | 範囲外。PO へ別件 |
| BREAK-既 2（tcg_product_import.py:484 の共通商品 DELETE を operator なしで） | app.is_operator は get_current_tenant が毎回空にする（dependencies.py:281）。Bx の前後で同じ | 範囲外。PO へ別件 |
| BREAK-既 5（product_packagings.py:164・:174・:203） | 同上 | 範囲外。PO へ別件 |
| BREAK-既 3（webhook.py:125・:219 の代替経路） | 本番に meta_page_routing がある（ai_ro.public__meta_page_routing あり）ので通常は :106 で return する | 範囲外。記録のみ |
| m9 表B B4（tcg_product_import.py:497 が無い `app.services.tenant_context` を import） | 別の不具合（Bx と無関係） | PO へ別件 |

### 4-4 未確認の扱い

| # | 結果 |
|---|---|
| U1 | 式が NULLIF ありでもなしでも「失敗に変わる」は同じ（m9 3-4）。§4-1 で全部直すので判断に影響しない |
| U2 | 本番 public.products 1465 行は全部共通（tenant_id NULL）、suppliers 315 行のうち会社1 のものが 1 行（id 26070・2026-10-31 作成）、translation_glossary 0 行（q24）。要確認 84 行で Bx 後に見え方が変わり得るのは会社1 の仕入先 1 行だけで、文脈なしの経路から見えなくなるのは RLS の本来の形 |
| U3 | Bx は app.database の async `engine` だけ（§2）。同期 engine は範囲外（4-2） |
| U4 | data_deletion は自前 ADMIN engine で範囲外（4-2） |
| U5・U6 | 呼び出し元 0 件の関数。動的呼び出しは未確認のまま。§6 K3 の本番ログ監視で検出する（失敗は relation does not exist／row-level security の文字で出る） |
| U7 | backend/app/tools/ は手動実行の道具。本番の要求経路ではない。範囲外 |

- Celery の作業（tasks/*.py の `AsyncSessionLocal`）も app.database の `engine` を使うので Bx がかかる。tasks/translation.py は §4-1 の 2 で直る。

## 5. 試験

| 便 | 試験 | 中身 |
|---|---|---|
| 便1 | 既存の単体試験 | CI（pytest・lint_tenant_schema.py の Rule C）が全部緑 |
| 便1 | import 確認 | §4-1 の python -c が通る |
| 便2 | 新しい試験 backend/tests/test_pool_reset_on_return.py | (1) postgresql のとき `engine.sync_engine.pool` に reset の listener が 1 つ登録されている（`event.contains(engine.sync_engine.pool, "reset", _reset_session_state)` が True）。(2) CI の postgres で: session で `set_tenant_context(db, 1)` → commit → close → 新しい session で `current_setting('app.tenant_id', true)` と `current_setting('app.is_operator', true)` が空、`SHOW search_path` が既定。(3) 同じく失敗した取引（わざと SQL エラー）の後に close しても次の checkout が通る（m6 の形） |
| 便2 | 既存の単体試験 | 全部緑（文脈の消え方が変わっても試験が通ること） |

## 6. 受入条件（KGI）

| # | 基準 | 検証方法 | 基準値（2026-11-07 実測） |
|---|---|---|---|
| K1 | 本番の /api/health の応答が 60 回中 60 回 200、中央値の増え方が基準値の +10% 以内 | 配備後に同じ台本で 60 回（health_base.txt と同じ取り方） | 60/60 が 200・中央値 1081.5ms・p95 1207.3ms |
| K2 | 配備後 24 時間の本番ログで、`does not exist`・`row-level security`・`invalid input syntax for type integer`・`" 500`・`Exception during reset` の件数が 0 件のまま | backend・celery-worker・discord-gateway・celery-beat の `docker logs` を grep で数える（読み取りのみ） | 4 つとも 0 件（07:42〜08:48 UTC） |
| K3 | 配備後 24 時間、celery-worker の `Exception closing connection` の 1 時間あたりの件数が基準値を超えない | 同上 | 18 件／約 65 分（07:43〜08:48 UTC。Bx の前からある既存のもの・§7 R4） |
| K4（便2 だけ） | 借りた直後の接続の文脈が空 | §5 便2 の試験 (2) が CI で緑 | — |
| K5（便2 だけ） | 返した接続が `idle in transaction` で残らない | 配備後に reader 鍵で pg_stat_activity を読み、アプリの役の接続で state が `idle in transaction` かつ state_change が 1 分より前のものが 0 件 | 配備前に同じ読み方で取る |
| K6（便2 だけ） | 会社1 で画面の主な操作が通る | 本番で会社1 の在庫表・リードの詳細・カレンダーを開き、エラー表示が無い（評価役が画面で確かめる） | — |

## 7. リスクと対処

| # | リスク | 対処 |
|---|---|---|
| R1 | m9 が拾えなかった「文脈なしで触る箇所」が Bx の後に失敗する | 失敗は 0 行か例外（漏れの反対側＝安全側）。K2 の監視で見つけ、ADR-072 の型で直す。戻すときは便2 の PR を revert（DB 変更なし） |
| R2 | reset ハンドラの中の失敗（接続切れなど） | SQLAlchemy 2.0.38（backend/requirements.txt:4）の pool/base.py `_finalize_fairy` は reset 中の例外を "Exception during reset or similar" と log して、その接続を invalidate する（写し /tmp/CC報告ファイル/xtenant/sqla/base.py:1006-1012）＝汚れた接続は貸し出しに戻らない。K2 の grep にこの文字も足して数える（基準値 0）。Bx 形が idle で返ることは m1・m7 で確かめた |
| R3 | 1 回の貸し借りが遅くなる | m5 で中央値 +0.44ms。K1 で本番を確かめる |
| R4 | Celery の `Exception closing connection`（RuntimeError: Event loop is closed・AsyncEngine.dispose の中）が増える | Bx の前からある既存のもの（K3 の基準値）。reset は checkin のとき＝その作業の event loop の中で走り、dispose の close とは別の場面。K3 で増えないことを確かめる。既存のもの自体は範囲外で PO へ別件 |
| R5 | 便1 の直しで import が循環する | §4-1 の python -c で確かめる |

## 8. 戻し方

- 便ごとに、その便の PR を revert して配備する。DB の変更は無い（migrations に触らない）。

## 9. 触らない範囲・後続

- admin_engine・同期 engine（Celery の同期・作業台本）の返却処理。
- xtenant-evidence.md §3 の「commit の後に operator を戻すだけ」の 9 か所＋1 か所（Bx で構造的に消えるので個別に直さない）。
- webhook.py の except で rollback しない件（xtenant-evidence.md §5・別件）。
- §4-3 の既存不具合 6 件と R4 の Celery の既存エラー（PO へ別件）。
- CI の台本 scripts/lint_tenant_schema.py の Rule C は rollback の後・自分で session を開く関数・同期経路を見ない（m9 3-5 の 5）。Bx が入ると漏れは「失敗」になって K2 の監視で見えるので、この便では Rule C を広げない。後続の候補として記録する。

## 8. 戻し方

- この便の PR を revert して配備する。DB の変更は無い（migrations に触らない）。

## 9. 触らない範囲・後続

- admin_engine・同期 engine（Celery・作業台本）の返却処理。
- xtenant-evidence.md §3 の「commit の後に operator を戻すだけ」の 9 か所＋1 か所（Bx で構造的に消えるので個別に直さない）。
- webhook.py の except で rollback しない件（xtenant-evidence.md §5・別件）。

## 10. 外部・過去事例の参照と我々への応用

- SQLAlchemy 2.0 公式「Reset On Return」・PostgreSQL の例（2.0.38 の写し: /tmp/CC報告ファイル/xtenant/sqla/pooling.rst・base.py:1405-1432）。公式は `pool_reset_on_return=None` ＋ reset ハンドラで RESET ALL を流す形を示す。我々は順番だけ変える（§2）。
- 数値の外部事例は使わない（速さと効き目は recon m1〜m7 の実測で判断する）。

## 維持の仕組み

- 仕組みで守る: Bx が入ると、文脈を張り忘れた新しいコードは「前の値で偶然動く」ことがなくなり、0 行か例外になる（漏れが起きない側に倒れる）。
- 試験で守る: backend/tests/test_pool_reset_on_return.py（§5 便2）が CI で毎回、listener の登録と「借りた直後は空」を確かめる。誰かが Bx を外すと CI が赤になる。
- 既存の見張り: scripts/lint_tenant_schema.py の Rule C（commit の後の最初の文が reset か）は今のまま動く。
- 担当: 配備後 24 時間の K2・K3 の数え直しは Opus（設計担当）が行い、結果を本書の末尾に追記する。
