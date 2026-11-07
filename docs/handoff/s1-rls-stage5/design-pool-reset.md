# 設計 — 接続を貸し出しに戻すたびに会社の文脈を消す（Bx・ADR-1070）

- 状態: 設計案（Opus 作成）。審査1回目 REVISE → M1〜M4・R1〜R9 を反映。審査2回目 REVISE（review-design-pool-reset-r2.md・必須 N1）→ N1〜N5 を反映。審査3回目 APPROVE（review-design-pool-reset-r3.md）→ 推奨 N6・N7 も反映。
- 基準: origin/main 170ff9612（2026-11-07 fetch）。b2bf39632 との差は backend/app・backend/requirements.txt・scripts/lint_tenant_schema.py で 0 件（審査 §冒頭）なので行番号は同じ。
- 前段の調査: docs/handoff/s1-rls-stage5/recon-pool-reset.md（r1〜m8）・xtenant-evidence.md（T 箇所と本番の実測）・recon-pool-reset-m9.md（文脈なしで RLS 表に触る箇所の全数）
- 関係する決定: ADR-131（get_db の finally で文脈を戻す）・ADR-072（tenant schema 修飾と commit 後の reset_tenant_context）・ADR-1067（S1 段階④）・ADR-065（準備済み文のキャッシュ）

## 1. 目的と利用者に見える変化

- 目的: ある要求が DB の接続に残した「会社の番号（app.tenant_id）・運営者の印（app.is_operator）・探す場所（search_path）」が、次にその接続を借りた別の要求に見えないようにする。
- 今（事実）: commit の後に流した SET は、close の rollback で消える（recon m1 手順 1: 返却後も `is_operator='true'`）。get_db の finally の `clear_tenant_context`（backend/app/auth/dependencies.py:386-405）は commit の後に流れるので効かない。pool_size 2 以上では、commit の後に同じ session で読むと別の要求の会社の文脈が見えた（recon m7: 20/20）。
- 変えた後: 接続を返すたびに rollback → `RESET ALL` → commit を流す。借りた直後の文脈は必ず空（recon m1 Bx・m2 Bx・m7 Bx 20/20 が空）。
- 利用者に見える変化: 無し（画面・応答は同じ）。変わるのは、文脈を張らずに RLS の表に触る箇所が「前の値で偶然動く」から「0 行・失敗」に変わること。そうなる箇所はこの便で全部直す（§4）。

## 2. 何を入れるか（Bx）

場所: backend/app/database.py。import（:1-5）・postgresql の分岐（:24-32）・`engine = create_async_engine(...)`（:33）の 3 か所。

```python
# 変更前（backend/app/database.py:1-5）
import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# 変更後（:4 の前に 1 行足す）
import os
from typing import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
```

```python
# 変更前（backend/app/database.py:24-33）
if DATABASE_URL.startswith("postgresql"):
    _engine_kwargs.update(
        pool_size=20,
        ...
        connect_args=_connect_args,
    )
engine = create_async_engine(DATABASE_URL, **_engine_kwargs)

# 変更後（update の中に 1 行足し、engine の前に 2 つの関数、後ろに 2 行）
if DATABASE_URL.startswith("postgresql"):
    _engine_kwargs.update(
        pool_size=20,
        ...
        connect_args=_connect_args,
        pool_reset_on_return=None,  # ADR-1070: pool 自身の rollback を止め、_reset_session_state に任せる
    )


def _reset_session_state(dbapi_connection, connection_record, reset_state):
    """ADR-1070 Bx: 接続を返すたびに rollback → RESET ALL → commit。"""
    if reset_state.terminate_only:          # 捨てる接続（GC・切り離し）は触らない
        return
    dbapi_connection.rollback()             # 開いている取引を閉じる（失敗した取引も）
    cur = dbapi_connection.cursor()
    try:
        cur.execute("RESET ALL")            # app.tenant_id・app.is_operator・search_path を初期値へ
    finally:
        cur.close()
    dbapi_connection.commit()               # RESET を確定させて idle で返す


def install_pool_reset(async_engine) -> None:
    """ADR-1070: pool_reset_on_return=None で作った async engine に Bx を付ける。試験もこの関数を使う。"""
    event.listen(async_engine.sync_engine.pool, "reset", _reset_session_state)


engine = create_async_engine(DATABASE_URL, **_engine_kwargs)
if DATABASE_URL.startswith("postgresql"):
    install_pool_reset(engine)
```

- 形は測定台本 docs/handoff/s1-rls-stage5/pool_reset_measure.py の Bx（:50-65 `_handler`・:75-76 `pool_reset_on_return=None`・:79 `event.listen(eng.sync_engine.pool, "reset", ...)`）と同じ。違うのは 3 点だけで、どれも流れる SQL の順番は変えない: ① cursor の close を finally に入れた（台本 :58-64 は try/finally なし）、② ハンドラに名前を付けた、③ 登録を `install_pool_reset` に切り出した（試験から同じ関数を呼ぶため・§5）。
- `terminate_only` だけを見ればよい理由: async の方言では、`asyncio_safe=False`（GC の後始末）のときは必ず `terminate_only=True` になる（SQLAlchemy 2.0.38 lib/sqlalchemy/pool/base.py:952-956 `detach = connection_record is None or is_gc_cleanup`・`can_manipulate_connection = not is_gc_cleanup`、:986-991 で `terminate_only=detach`・`asyncio_safe=can_manipulate_connection` を渡す）。
- `pool_reset_on_return=None` でも reset のイベントは呼ばれる: 同 base.py:1405-1417 は `pool.dispatch.reset(...)` を `_reset_on_return` の判定（:1419-1440）より前に呼ぶ。

- 対象外: `admin_engine`（database.py の SA-18 Phase2・jarvis 役・RLS を通らない）と Celery・作業台本の同期 engine（recon r1 #8〜#13）。この便では触らない。
- 順番が公式の例と違う理由: SQLAlchemy 2.0.38 の PostgreSQL の例（lib/sqlalchemy/dialects/postgresql/base.py:265-284。出典は §10）は `pool_reset_on_return=None` と reset ハンドラで「CLOSE ALL / RESET ALL / DISCARD TEMP の後に rollback」。この順だと RESET ALL は開いた取引の中で流れ、最後の rollback で取り消される（recon m1 の A と同じ仕組み: 返却直後の last_query が ROLLBACK で値が残る）。rollback を先にし、最後に commit で確定させる（recon m1: B は `idle in transaction` のまま残り、psycopg2 では次の checkout が落ちた＝m6。Bx は idle・エラー無し）。
- CLOSE ALL・DISCARD TEMP を入れない理由: backend/app は一時表とサーバー側カーソルを使っていない（`git grep -n -i -E "CREATE (TEMP|TEMPORARY) TABLE|stream_results|DECLARE [a-z_]+ CURSOR|\.stream\(|yield_per|LISTEN " origin/main -- backend/app` が 0 件・2026-11-07 170ff9612）。DISCARD ALL は準備済み文も消すので使わない（ADR-065 と m3: RESET ALL は 6 回とも通る）。
- 速さ: 1 回の貸し借りで中央値 +0.44ms（0.997→1.441ms）・p95 +0.28ms（recon m5・手元の DB）。本番の基準値は §6。

## 3. 便の分け方（変更は一度に 1 つ）

| 便 | 中身 | 今の本番での効き目 | 測るもの |
|---|---|---|---|
| 便1 | §4-1 の 6 起点・8 か所に「commit・rollback の直後に `reset_tenant_context(db, tenant_id)`」を足すだけ | 無し（同じ要求の同じ会社の文脈を張り直すだけ。今は前の値が残って偶然同じ値） | CI・単体試験・配備後 24 時間のエラー件数が基準値から増えない（§6） |
| 便2 | Bx（§2）だけ | 接続を返すたびに文脈を消す | §6 の全項目 |

- 便1 を先に本番へ入れて §6 の K1〜K3 を測ってから便2 に進む。便2 を先に入れると §4-1 の箇所が本番で失敗する。
- どちらも migrations・deploy.yml・本番 scripts に触らない（ADR-135/136 の危険パスではない）。

## 4. 文脈を張らずに RLS の表に触る箇所（m9）の扱い

根拠: recon-pool-reset-m9.md（origin/release/s1-rls-pool-reset-m9 c8dfa799a。表A 116 行＋表B）。BREAK-新 9 起点・BREAK-既 6 起点・未確認 U1〜U7 の全部を、下の 4-1〜4-4 のどれかに振り分けた（漏れ無し）。

### 4-1 便1 で直す（BREAK-新 のうち、Bx がかかる async engine の経路）

直し方はどれも ADR-072 の型。行番号は origin/main 170ff9612。6 起点（1・2・3・4・5・7）・8 か所（起点3 が 3a・3b・3c の 3 か所）。

| 起点 | 場所 | 直し | import |
|---|---|---|---|
| 1 | backend/app/discord_gateway/ticket_channel_writer.py `process_ticket_channel_message` の `await db.commit()`（:249）の直後・`if inserted_row is None:` の前 | `await reset_tenant_context(db, tenant_id)` | :20 の `from app.auth.dependencies import set_tenant_context` に `reset_tenant_context` を足す（このファイルは既に app.auth.dependencies を先頭で読んでいる） |
| 2 | backend/app/services/message_translator.py `translate_inbound` の `await db.commit()`（:507）の直後・`logger.info(` の前 | 同上（引数 `tenant_id` は :425） | 関数の中で import する: commit の直前か直後に `from app.auth.dependencies import reset_tenant_context  # noqa: PLC0415` を置く。ファイルの先頭には足さない（理由は下の R6） |
| 3a | backend/app/services/priority_scoring.py `calibrate_tenant_weights` の `await db.commit()`（:250）の直後・`return weights` の前 | 同上（引数 :160） | 起点2 と同じく関数の中で import（今のファイル先頭の import 並び :11-24 には足さない） |
| 3b | 同 `label_lead_messages` の `if saved > 0:` の中の `await db.commit()`（:313）の直後 | 同上（引数 :257） | 同上 |
| 3c | 同 `_compute_and_persist` の `await db.commit()`（:439）の直後・`return CustomerScoreResponse(` の前 | 同上（引数 :386） | 同上 |
| 4 | backend/app/routers/tenant_commission_settings.py `_create_default` の except 側 `await db.rollback()`（:109）の直後 | 同上 | 済み（:33） |
| 5 | backend/app/routers/products.py `delete_product` の `await db.rollback()`（:706）の直後・`record_audit_log` の前 | 同上 | 済み（:32） |
| 7 | backend/app/routers/webhook.py `_create_outbound_lead_for_echo` の `await db.commit()`（:580）の直後・`return lead_id` の前 | 同上（引数 `tenant_id` :540） | 済み（:50） |

- 3a は呼び出し元が 0 件（m9 表D）。同じファイルで型を揃えるために直す（害が無く、将来呼ばれたときの落とし穴を消す）。
- 2 は conv_logs.py:136 → :145 の UPDATE、tasks/translation.py:79 の 2 回目以降の translate_inbound、llm_budget.py:472・:524（m9 表A 行 3・13・14・表B B1）をまとめて直す。
- 3c は customer_priority.py `override_priority_score`（:64 から :140 の commit・:142 の reset まで。:158 の関数より前）の続きの読み書き（m9 表A 行 4・5）も直す。
- 関数の中で import する理由（審査 R6）: message_translator.py の先頭で app.auth.dependencies を読むと、message_translator を読むだけで app.database（engine の作成）も読まれる。message_translator は scripts/lead_regression/generate.py:27 からも読まれる。同じ理由で backend/app/services/llm_budget.py:413・backend/app/routers/conv_logs.py:129 は関数の中で import している。この型に揃える。
- 循環 import にならないことを実装役が `python -c "import app.services.message_translator, app.services.priority_scoring, app.discord_gateway.ticket_channel_writer"` で確かめる。
- 本番で今どれだけ通る経路か（q28・2026-11-07 08:44 UTC 読み取り）: 翻訳の保存は会社1 0 件・会社4 35 件（最後 2026-06-28）、Discord 添付の記録は会社1・4 とも 0 件。通る回数は少ないが、直しは無害なので全部入れる。

### 4-2 Bx の影響を受けない（直さない・理由つき）

| 起点 | 理由（根拠） |
|---|---|
| 6（calendar_service.py:303 の commit の後の :306） | try（:278-312）の中の commit は、:303 以外すべて reset が続く（:271-272、google_calendar.py `_refresh_if_needed` の :293-294）。そのため except（:306）に来たとき文脈が無いのは :303 の commit 自体が失敗した場合だけで、そのときは取引が中断状態なので Bx の有無にかかわらず UPDATE は通らない。Google API の失敗（cal_svc.create_event の例外）で except に来たときは :272 か :294 の reset の後なので文脈はある。xtenant-evidence.md §2 の T4 を「漏れではない」に改訂 |
| 8（tasks/refresh_meta_tokens.py） | 自前の同期 engine `create_engine(DATABASE_URL)`（:97-99）。Bx は app.database の async `engine` にだけかける（U3 の答え） |
| 9（tasks/verify_meta_subscriptions.py） | 同上（:82-84） |
| BREAK-既 data_deletion（m9 表A 行 32-34） | 自前の ADMIN engine（tasks/data_deletion.py:59）。同上（U4 は Bx の範囲外になるので判断に要らない） |

### 4-3 Bx の前から動いていない既存の不具合（この便に混ぜない・PO へ別件で報告）

| 起点 | 事実 | 扱い |
|---|---|---|
| BREAK-既 1（配信失敗の Discord 通知 routers/notifications.py:166・:187 を tcg_distribution_svc.py:1160-1184 が tenant_id=4 で文脈なしに呼ぶ） | 本番 tenant_004.notification_logs は全期間 0 行（q26）。加えて、送信先の tenant_004.notification_channels は 0 行（有効 0・tcg_distribution_error を含む有効 0。2026-11-07T09:12Z reader 道、SQL と結果は r5-notification-channels.md）。送る先が無いので、Bx の前も後も Discord への送信（:185）は起きない＝退行ではない | 直すと外へ出る通知が新たに始まり得る。範囲外。PO へ別件 |
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
| 便1 | 該当関数の単体試験を先に流す（審査 R7） | 実装役が手元ではなく CI と同じ形で、`backend/tests/` の test_message_translator*.py・test_ticket_channel_translation.py・test_customer_reply_notifier.py・test_lead_regression_generate.py と、priority_scoring・customer_priority・tenant_commission_settings・products・webhook を名前に含む試験を流し、全部緑。db を MagicMock にした試験で execute の回数・順番が変わって赤になったら、試験の期待値を「commit の直後に reset が 1 回増える」に直す（製品コードの直しを減らさない）。直した試験はカードの報告に全部書く |
| 便1 | 既存の全試験 | CI（必須チェック「pytest (SQLite + PostgreSQL RLS)」・lint_tenant_schema.py の Rule C）が全部緑 |
| 便1 | import 確認 | §4-1 の python -c が通る |
| 便2 | 新しい試験 backend/tests/test_pool_reset_on_return.py | 下の表 |
| 便2 | 既存の全試験 | 全部緑（文脈の消え方が変わっても試験が通ること） |

便2 の新しい試験（審査 M2 の直し）。pytest は backend/tests/conftest.py:17-18 で DATABASE_URL を SQLite に差し替えるので、`app.database.engine` そのものには listener が付かない。そのため「本体の engine に付くこと」と「付いたときに効くこと」を分けて試す。

| # | 試験 | 作り方 | 判定 |
|---|---|---|---|
| T1 | 本体の engine に付くこと | `subprocess.run([sys.executable, "-c", ...], env={..., "DATABASE_URL": "postgresql+asyncpg://u:p@127.0.0.1:1/x"})` で別の Python を起こし、`import app.database as d` の後に `event.contains(d.engine.sync_engine.pool, "reset", d._reset_session_state)` と、`from sqlalchemy.pool.base import reset_none` の上で `d.engine.sync_engine.pool._reset_on_return is reset_none` を表示させる（SQLAlchemy 2.0.38 は `pool_reset_on_return=None` を `ResetStyle.reset_none` に置き換えて持つ: 上流 lib/sqlalchemy/pool/base.py:95-107・:287-291。`is None` は常に False なので使わない。審査 2 回目 N1）。create_async_engine は作るだけでは接続しないので DB は要らない。同じ形で DATABASE_URL を `sqlite+aiosqlite:///:memory:` にした場合は `event.contains` が False になることだけを判定にする（sqlite 側の `_reset_on_return` は既定の `reset_rollback` で、判定に使わない）。別の Python で動かすのは、同じ pytest の中で app.database を読み直すと他の試験の engine が入れ替わるため | postgresql: True・True。sqlite: `event.contains` が False |
| T2 | 借りた直後の文脈が空（漏れの形） | `RLS_TEST_DATABASE_URL` から `create_async_engine(url, pool_size=1, max_overflow=0, pool_reset_on_return=None)` を作り `install_pool_reset(eng)`。session A で `set_config('app.tenant_id','991',false)`・`set_config('app.is_operator','true',false)`・`SET search_path TO tenant_991, public` → commit → close。session B で `pg_backend_pid()` が A と同じ（同じ接続）、`current_setting('app.tenant_id', true)` と `current_setting('app.is_operator', true)` が空か NULL、`SHOW search_path` が `"$user", public` | 3 つとも空・既定 |
| T3 | 対照（Bx を外すと T2 が赤になること） | T2 と同じ engine を `install_pool_reset` を呼ばず、`pool_reset_on_return` も既定のままで作り、同じ手順 | session B で `app.tenant_id` が `991`・`app.is_operator` が `true` のまま（＝今の本番の漏れ。T2 の判定がこれを見分けられる証拠） |
| T4 | 回帰の確認: Bx が入っていても、失敗した取引の後に例外を出さず次が借りられる（Bx の有無を見分ける試験ではない。AsyncSession の close が先に rollback するため。審査 2 回目 N4） | T2 の engine で session A が `SELECT 1/0` を流して例外を受け、rollback せずに close。session B で `SELECT 1` | 1 が返る（state の判定は置かない。自分の問い合わせ中の接続は常に `active` で何も見分けないため） |

- T2〜T4 は PostgreSQL が要る。`RLS_TEST_DATABASE_URL` が無いとき、環境変数 `CI` が `true` なら skip ではなく `pytest.fail` にする（CI で黙って飛ばされないように）。手元（CI が無い）では skip。既存の書き方（backend/tests/test_rls_auth_audit.py:24-35 の skipif）に CI の判定を足す形。
- CI では .github/workflows/test.yml の pytest-run ジョブ（:114・:218-253、`RLS_TEST_DATABASE_URL` は :234）で流れ、必須チェック「pytest (SQLite + PostgreSQL RLS)」（:262-263）がその結果を集約する。backend に変更がある PR なので detect-changes で飛ばされない。

## 6. 受入条件（KGI）

物差しは 1 つ: docs/handoff/s1-rls-stage5/k-baseline.sh（読み取りだけ。health の GET を 60 回、4 コンテナの `docker logs` を 7 種の文字で数え、コンテナ起動からの時間で 1 時間あたりに直す）。基準値はこの台本の生の出力 k-baseline-20261107T0917Z.txt。各便の配備の直前にも同じ台本で取り直して PR に貼る（その時点の基準値）。配備でコンテナが入れ替わると `docker logs` は起動からしか数えられないので、「配備後 24 時間」は次の配備でコンテナが入れ替わる前に数える。24 時間に満たずに入れ替わる場合は、入れ替わる直前に数えて、その時間を書く。
- 基準値と事後値は同じ機械（PO の Mac）・同じ回線で取る。K1 の中央値の大半は手元から本番までの回線の時間なので、機械が変わると +10% の判定が意味を失う（審査 2 回目 N5）。
- 09:17Z の基準値はコンテナ起動から約 15 分の窓しかない（審査 2 回目 N2）。そのため便1 の配備の直前に、コンテナがなるべく長く動いた状態で k-baseline.sh を取り直し、それを便1 の基準値にする。そこで 0 でないマスがあれば、そのマスの K2 の判定は「0 件」でなく「1 時間あたりの件数が基準値から増えない」に置き換え、置き換えたマスを PR に書く。K3 ② の上限も、取り直した基準値の `close_exc_per_h` が 16.6 を超えたら、その値の 1.2 倍に置き換えて PR に書く（審査 3 回目 N6）。便2 も同じ扱い。

| # | 基準 | 検証方法 | 基準値（k-baseline-20261107T0917Z.txt・2026-11-07T09:17Z） |
|---|---|---|---|
| K1 | 本番の /api/health が 60 回中 60 回 200、中央値が配備直前の基準値の +10% 以内 | 配備後に k-baseline.sh（`k1_ok200`・`k1_median_ms`） | 60/60 が 200・中央値 1079.2ms・p95 1172.9ms |
| K2 | 配備後の本番ログで、下の 5 種 × 4 コンテナの 20 マスがすべて 0 件 | k-baseline.sh の K2/K3 行 | 20 マスすべて 0 件（下の表） |
| K3 | 配備後、celery-worker の ① `traceback` の件数と `close_exc` の件数が同じ（既存の `Exception closing connection` 以外の traceback が 0 件）、② `close_exc_per_h` が 20 以下 | 同上 | ① 3 件と 3 件で同じ ② 12.7／時（参考: 07:43〜08:48Z の別の数え方では 18 件／約 65 分＝約 16.6／時）。20 は 2 回の実測の大きい方に 2 割足した上限 |
| K4（便2 だけ） | 借りた直後の接続の文脈が空で、Bx を外すとそれを見分けられる（見分けるのは T1〜T3。T4 は回帰の確認） | §5 便2 の T1〜T4 が必須チェック「pytest (SQLite + PostgreSQL RLS)」の中で緑（skip でない）。CI の pytest の出力に test_pool_reset_on_return.py の 4 件が passed で出ることを PR で確かめる | — |
| K5（便2 だけ） | 返した接続が `idle in transaction` で残らない | 配備後に reader 鍵で pg_stat_activity を読み、アプリの役の接続で state が `idle in transaction` かつ state_change が 1 分より前のものが 0 件 | 配備前に同じ読み方で取る |
| K6（便2 だけ） | 会社1 で画面の主な操作が通る | 本番で会社1 の在庫表・リードの詳細・カレンダーを開き、エラー表示が無い（評価役が画面で確かめる） | — |

K2 の 20 マス（基準値。数える文字は k-baseline.sh の `pat` の並びのとおり。`grep -c -F` で行を数える）:

| 名前 | 数える文字 | backend | celery-worker | discord-gateway | celery-beat |
|---|---|---|---|---|---|
| relnotexist | `does not exist` | 0 | 0 | 0 | 0 |
| rls | `row-level security` | 0 | 0 | 0 | 0 |
| invalid_int | `invalid input syntax for type integer` | 0 | 0 | 0 | 0 |
| s500 | `" 500 ` | 0 | 0 | 0 | 0 |
| reset_exc | `Exception during reset` | 0 | 0 | 0 | 0 |

- K2 が × のとき（1 マスでも 1 件以上）: その行の前後をそのまま読み、どの関数から出たかを file:line で特定する。便の変更（便1 の reset・便2 の Bx）に関係する経路なら、その便の PR を revert して配備する。関係しない既存のものなら、根拠つきで本書の末尾に記録し、PO へ別件として上げる。どちらか分からないときは revert する（安全側）。

## 7. リスクと対処

| # | リスク | 対処 |
|---|---|---|
| R1 | m9 が拾えなかった「文脈なしで触る箇所」が Bx の後に失敗する | 失敗は 0 行か例外（漏れの反対側＝安全側）。K2 の監視で見つけ、ADR-072 の型で直す。戻すときは便2 の PR を revert（DB 変更なし） |
| R2 | reset ハンドラの中の失敗（接続切れなど） | SQLAlchemy 2.0.38（backend/requirements.txt:4）の pool/base.py `_finalize_fairy` は reset 中の例外を "Exception during reset or similar" と log して、その接続を invalidate する（lib/sqlalchemy/pool/base.py:1006-1012。出典は §10）＝汚れた接続は貸し出しに戻らない。K2 の reset_exc で数える（基準値 0）。Bx 形が idle で返ることは m1・m7 で確かめた |
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

## 10. 外部・過去事例の参照と我々への応用

SQLAlchemy の根拠は、上流のタグ rel_2_0_38 のファイルを行つきで引く（backend/requirements.txt:4 が `sqlalchemy==2.0.38`）。2026-11-07 に raw.githubusercontent.com から取ったファイルと、調査で使った手元の写しを `cmp` で比べ、3 本とも 1 バイトも違わないことを確かめた（pool/base.py 1515 行・dialects/postgresql/base.py 5038 行・pooling.rst）。

| 何の根拠か | 上流の場所 |
|---|---|
| reset のイベントは `pool_reset_on_return=None` でも呼ばれる | https://github.com/sqlalchemy/sqlalchemy/blob/rel_2_0_38/lib/sqlalchemy/pool/base.py#L1398-L1440 |
| async 方言で `asyncio_safe=False` なら `terminate_only=True` | 同 base.py#L952-L991 |
| reset 中の例外は log して invalidate | 同 base.py#L1006-L1012 |
| 公式の PostgreSQL の例（CLOSE ALL / RESET ALL / DISCARD TEMP の後に rollback） | https://github.com/sqlalchemy/sqlalchemy/blob/rel_2_0_38/lib/sqlalchemy/dialects/postgresql/base.py#L265-L284 |
| 文書「Reset On Return」「Custom Reset-on-Return Schemes」 | https://github.com/sqlalchemy/sqlalchemy/blob/rel_2_0_38/doc/build/core/pooling.rst#L130 ・ #L168 |

- 公式は `pool_reset_on_return=None` ＋ reset ハンドラで RESET ALL を流す形を示す。我々は順番だけ変える（§2）。
- 数値の外部事例は使わない（速さと効き目は recon m1〜m7 の実測で判断する）。

## 維持の仕組み

- 仕組みで守る: Bx が入ると、文脈を張り忘れた新しいコードは「前の値で偶然動く」ことがなくなり、0 行か例外になる（漏れが起きない側に倒れる）。
- 試験で守る: backend/tests/test_pool_reset_on_return.py（§5 便2 の T1〜T4）が必須チェックの中で毎回流れる。database.py から `install_pool_reset(engine)` の呼び出しを外すと T1 が赤、`_reset_session_state` の中身を外すと T2 が赤（T3 が「外した状態」を見分けられることの証拠）。Bx の有無を見分けるのは T1〜T3 で、T4 は回帰の確認だけを担う。CI で PostgreSQL が無いときは skip でなく失敗にする。
- 物差しで守る: k-baseline.sh を、この先の RLS の便（S1 段階⑤）でも配備の前後に同じ形で流す。
- 既存の見張り: scripts/lint_tenant_schema.py の Rule C（commit の後の最初の文が reset か）は今のまま動く。
- 守り手: Opus（設計担当）。配備後 24 時間の K2・K3 の数え直しは Opus（設計担当）が行い、結果を本書の末尾に追記する。
