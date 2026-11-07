# 審査 2 回目 — design-pool-reset.md と ADR-1070（差分 45719882f → a0368b43c）

- 役割: 設計の再審査役（Architect）。読むだけ。製品コード・本番・secret には触っていない。設計書と ADR は直していない。
- 対象: `git diff 45719882f a0368b43c`（6 ファイル: ADR-1070・design-pool-reset.md・k-baseline.sh・k-baseline-20261107T0917Z.txt・r5-notification-channels.md・review-design-pool-reset.md）の差分だけ。
- コードの基準: origin/main ce2815fd62fe6c54a79af7fdbf6469e623e14c17（2026-11-07 fetch）。`git diff --stat 170ff9612 origin/main -- backend/app` は 0 件（自分で流して確かめた）。行番号は 170ff9612 と同じ。
- SQLAlchemy: 上流タグ rel_2_0_38 の lib/sqlalchemy/pool/base.py（1515 行）と lib/sqlalchemy/dialects/postgresql/base.py（5038 行）を raw.githubusercontent.com から取って読んだ。以下「sqla pool/base.py」はこのファイル。
- 下の「設計」は docs/handoff/s1-rls-stage5/design-pool-reset.md（a0368b43c）の行番号、「ADR」は docs/adr/ADR-1070-pool-reset-on-return.md（a0368b43c）の行番号。

## 1. 前回の指摘ごとの照合表

| ID | 結果 | 根拠（設計・ADR の行／origin/main の実物） |
|---|---|---|
| M1 `event` の import | 直った | 設計:19-34 に変更前（backend/app/database.py:1-5 と一致）と変更後 `from sqlalchemy import event`（:4 の前）を明記 |
| M2 試験が成り立たない | 一部 | 方針（`install_pool_reset` に切り出し、T1 は別の Python で本体の engine を、T2〜T4 は `RLS_TEST_DATABASE_URL` の engine に同じ関数を当てる、CI では skip でなく fail）は前回の直し方どおり（設計:167-177、ADR:16）。backend/tests/conftest.py:18・.github/workflows/test.yml:114・:218-253・:234・:262-263・backend/tests/test_rls_auth_audit.py:24-35 は実物と一致。ただし T1 の判定 `pool._reset_on_return is None` は 2.0.38 では必ず False になり、K4 が満たせない（新指摘 N1） |
| M3 K1〜K3 の物差しと基準値 | 直った | docs/handoff/s1-rls-stage5/k-baseline.sh（読み取りだけ: curl の GET・ssh 先で docker inspect／docker logs）と生の出力 k-baseline-20261107T0917Z.txt が入った。設計:185-187 の値（60/60・中央値 1079.2ms・p95 1172.9ms・traceback 3／close_exc 3・12.7／時）は出力の :63-64・:67 と一致。K2 は 5 種 × 4 コンテナ＝20 マスの表（設計:194-200）で、文字は k-baseline.sh:39-44 と一致。台本の注記の数のずれは新指摘 N3 |
| M4 直す箇所の数 | 直った | ADR:18・:26、設計:92・:104 がすべて「6 起点・8 か所」。両ファイルに「7 か所」は残っていない（grep 0 件） |
| R1 §8・§9 の重複 | 直った | 設計:214-224 に §8・§9 が 1 回ずつ。§9 に §4-3・R4・Rule C の行がある（:223-224） |
| R2 行の範囲 | 直った | 設計:110「:11-24」＝backend/app/services/priority_scoring.py:11-24（:20-24 が括弧の import）。設計:119「:64 から :140 の commit・:142 の reset まで。:158 の関数より前」＝backend/app/routers/customer_priority.py:140・:142・:158 |
| R3 台本との違い | 直った | 設計:79 に違い 3 点（finally・名前・`install_pool_reset`）と「SQL の順番は変えない」を明記。設計:56-66 の順番は rollback → RESET ALL → commit のまま |
| R4 SQLAlchemy の根拠 | 直った | 設計:228-236 に rel_2_0_38 の URL と行。上流ファイルで確かめた: :955-956 `detach = ... or is_gc_cleanup`・`can_manipulate_connection = not is_gc_cleanup`、:989-990 `terminate_only=detach`・`asyncio_safe=can_manipulate_connection`、:1008-1012 "Exception during reset or similar" と `invalidate`、:1398 `_reset`・:1406 `pool.dispatch.reset(` は :1419 の `_reset_on_return` の判定より前、dialects/postgresql/base.py:265-284 の例。呼び方も設計:84 で `lib/sqlalchemy/dialects/postgresql/base.py` に揃った。/tmp の写しへの言及は 0 件 |
| R5 配信失敗通知の根拠 | 直った | docs/handoff/s1-rls-stage5/r5-notification-channels.md に SQL と結果（有効 0・tcg_distribution_error 0・全 0 行、2026-11-07T09:12Z）。設計:137 に反映。本番の値そのものは本審査では読んでいない（記録を採用） |
| R6 先頭 import の副作用 | 直った | 設計:109-111・:120 で起点2・3 は関数の中で import。根拠の backend/app/services/llm_budget.py:413-414・backend/app/routers/conv_logs.py:129・scripts/lead_regression/generate.py:27 は実物と一致。`# noqa: PLC0415` は backend/app/database.py:60 と同じ書き方 |
| R7 MagicMock の試験 | 直った | 設計:161。名前を挙げた backend/tests/test_message_translator.py・test_message_translator_usage_ledger.py・test_ticket_channel_translation.py・test_customer_reply_notifier.py・test_lead_regression_generate.py は origin/main にある。「priority_scoring…webhook を名前に含む試験」も test_priority_scoring.py・test_products.py ほかが該当 |
| R8 起点6 の理由 | 直った | 設計:128。backend/app/services/calendar_service.py:278-312、backend/app/services/google_calendar.py:293-294 と一致。細部: :271-272 は try（:278）の外の commit・reset なので「try の中の commit は…(:271-272…)」は言い方がずれるが、「except に来たときに文脈があるのは :272 か :294 の reset の後」という結論は正しい（直さなくてよい） |
| R9 窓の長さの違い | 一部 | 設計:181 で「各便の配備の直前にも同じ台本で取り直す」、設計:202 で K2 が × のときの切り分け（関係しない既存のものは記録して PO へ）が足された。ただし基準値の窓は約 15 分（出力 :66-69 の hours=0.236〜0.252）のままで、K2 は 24 時間で「20 マスすべて 0 件」の絶対値の判定。K3 ② の上限 20／時も 3 件／0.236 時間と 18 件／約 65 分から作っている（新指摘 N2） |

## 2. 差分で新しく書いた フルパス:行番号・コードの形の照合

| # | 設計の記述 | origin/main・上流の実物 | 結果 |
|---|---|---|---|
| 1 | 設計:20-25 変更前の import（database.py:1-5） | backend/app/database.py:1-5 | 一致 |
| 2 | 設計:37-44 変更前の分岐と engine（:24-33） | backend/app/database.py:24-33 | 一致 |
| 3 | 設計:52 `pool_reset_on_return=None` を update に足す | create_async_engine に渡る。sqla pool/base.py:287-291 で `None` は `ResetStyle.reset_none` に変換される | 形は正しい（判定の書き方は N1） |
| 4 | 設計:56-66 `_reset_session_state` | docs/handoff/s1-rls-stage5/pool_reset_measure.py:50-65 の順番と同じ。違いは設計:79 の 3 点だけ | 一致 |
| 5 | 設計:69-76 `install_pool_reset` と postgresql のときだけ呼ぶ | `event.listen(async_engine.sync_engine.pool, "reset", ...)` は台本 :79 と同じ対象。admin_engine（backend/app/database.py:84）には呼ばない | 一致 |
| 6 | T1 の判定「postgresql: True・True」の 2 つ目 `d.engine.sync_engine.pool._reset_on_return is None` | sqla pool/base.py:95-107（`ResetStyle` と `reset_none = 2`）、:287-291（`None` → `ResetStyle.reset_none`）。`_reset_on_return` に None が入る道は無い | **不一致（N1）** |
| 7 | T1 の別プロセスで DB 無しに import できる | backend/requirements.txt:5 `asyncpg==0.31.0`。create_async_engine は接続しない。ADMIN_DATABASE_URL は未設定なら DATABASE_URL に倒れる（backend/app/database.py:66）ので admin_engine も接続なしで作られる | 一致（実行はしていない） |
| 8 | T2 `SHOW search_path` が `"$user", public` | CI の役 salesanchor_app に search_path を設定する `ALTER ROLE`／`ALTER DATABASE ... SET` は .github/workflows/test.yml・migrations・backend/tests に 0 件 | 一致（CI で既定値になる見込み。実行はしていない） |
| 9 | T3 Bx 無しで 991・true が残る | 既定の reset は rollback（sqla pool/base.py:1419-1432）で、commit 済みの session 単位の set_config は消えない。recon m7 の実測と同じ仕組み | 一致 |
| 10 | T4 失敗した取引の後も次が借りられる | AsyncSession の close は自分で rollback するので、reset ハンドラに届く時点で取引は閉じている。Bx を外しても T4 は緑になる。判定「自分の接続の state」は、その問い合わせ中の接続なので必ず `active` | 判定が何も見分けない（N4） |
| 11 | K1〜K3 の基準値 | k-baseline-20261107T0917Z.txt:63-64・:66-69 | 一致 |
| 12 | K2 の 5 種の文字 | docs/handoff/s1-rls-stage5/k-baseline.sh:39-44 | 一致 |
| 13 | 設計:181「7 種の文字」 | k-baseline.sh:38-45 は 7 種。同じ台本の注記 :5 は「6 種」 | 台本の注記がずれる（N3） |
| 14 | §5 の CI の場所（:114・:218-253・:234・:262-263） | .github/workflows/test.yml:114 `pytest-run`・:218 Run pytest・:234 `RLS_TEST_DATABASE_URL`・:263 `name: pytest (SQLite + PostgreSQL RLS)` | 一致 |
| 15 | §5 既存の skipif の書き方 | backend/tests/test_rls_auth_audit.py:24・:33-36 | 一致 |
| 16 | §10 の上流の行 | sqla pool/base.py:952-991・:1006-1012・:1398-1440、dialects/postgresql/base.py:265-284 | 一致 |
| 17 | k-baseline.sh の接続先の書き方 | 本番の IP（リポジトリに既に 210 か所）と鍵のファイルの場所だけで、鍵・パスワードの値は無い。DB には触らず docker logs と GET だけ（AGENTS.md の「DB 以外の読み取りだけの調査は恒常許可」の範囲） | 問題なし |

## 3. 新しい食い違い（ADR と設計、§同士）

- ADR:16 の `install_pool_reset(engine)`・ADR:18 と :26 の「6 起点・8 か所」・ADR:34 の物差し（k-baseline.sh と 09:17Z の出力、配備直前に取り直す）は、設計 §2・§3・§4-1・§6 と一致。
- 設計の §5 T1 の判定と「維持の仕組み」（設計:244「install_pool_reset の呼び出しを外すと T1 が赤」）は、N1 を直せば一致する。今のままだと T1 は Bx が入っていても赤。
- 設計:181（7 種）と k-baseline.sh:5（6 種）が食い違う（N3）。
- それ以外の §同士の食い違いは見つからなかった。

## 4. 新しい指摘

| ID | 重さ | 指摘 | 根拠 | 直し方 |
|---|---|---|---|---|
| N1 | 必須 | T1 の 2 つ目の判定 `d.engine.sync_engine.pool._reset_on_return is None` は、Bx を正しく入れても False になる。SQLAlchemy 2.0.38 は `pool_reset_on_return=None` を `ResetStyle.reset_none` に変えて持つ。このままでは T1 が赤で K4 を満たせず、実装役が判定を勝手に書き換える余地が残る | sqla pool/base.py:95-107（`class ResetStyle`・`reset_none = 2`・`reset_rollback, reset_commit, reset_none = list(ResetStyle)`）、:287-291（`ResetStyle.reset_none: ["none", None, False]`）、:1419・:1433 も `is reset_rollback`／`is reset_commit` で比べる | 設計:171 の判定を `from sqlalchemy.pool.base import reset_none` の上で `pool._reset_on_return is reset_none`（または `.name == "reset_none"`）に直す。sqlite の側は `event.contains` が False であることだけを判定にする（sqlite 側の `_reset_on_return` は既定の `reset_rollback`） |
| N2 | 推奨 | 基準値の窓が約 15 分（コンテナ起動 09:04〜09:05Z から 09:17Z）しかない。K2 は 24 時間で 20 マスすべて 0 件の絶対判定、K3 ② の上限 20／時は 3 件の数え（12.7／時）と別の数え方の 65 分（約 16.6／時）から作っている。設計:202 の切り分けの手順で誤判定は回収できるが、既存の失敗が 24 時間のうちに出ると毎回この切り分けが要る | k-baseline-20261107T0917Z.txt:66-69（hours=0.252・0.236）、設計:186-187 | 便1 の配備の直前に、コンテナが 24 時間近く動いた状態で k-baseline.sh を流して基準値にする（そこで 0 でないマスがあれば、K2 の判定を「その件数から増えない」にする） |
| N3 | 推奨 | k-baseline.sh の注記が「6 種の文字列」だが、数えている文字は 7 種（設計:181 も 7 種）。物差しの台本の説明が中身と合わない | docs/handoff/s1-rls-stage5/k-baseline.sh:5 と :38-45 | :5 を「7 種」に直す |
| N4 | 推奨 | T4 は Bx の有無を見分けない。AsyncSession の close が先に rollback するので、Bx を外しても B は借りられる。判定の「自分の接続の state が idle in transaction (aborted) でない」は、自分の問い合わせ中なので常に `active` | 設計:174。既定の reset は rollback（sqla pool/base.py:1419-1432） | T4 は「回帰の確認（Bx が失敗した取引の後でも例外を出さない）」と目的を書き直し、state の判定は外すか、別の接続（RLS_ADMIN_DATABASE_URL）から session A の `pg_backend_pid()` の state を読む形にする。K4 の「Bx を外すと見分けられる」は T1・T3 だけが担うと §5・維持の仕組みに書く |
| N5 | 推奨 | K1 の中央値（約 1.08 秒）はほぼ手元から本番までの回線の時間で、流す機械が変わると +10% の判定が意味を失う。台本も設計もどの機械で流すかを書いていない | k-baseline-20261107T0917Z.txt:3-62、設計:185 | 「基準値と事後値は同じ機械・同じ回線で取る」と §6 に書く |

## 5. 判定

**REVISE**

必須は N1 の 1 件だけ（T1 の判定の書き方 1 か所）。前回の M1・M3・M4 は直った。M2 は方針として直ったが、N1 が残るため「一部」。N1 を直せば実装へ進めてよい。次の審査は設計:171 の T1 の判定の行だけを見れば足りる。推奨 N2〜N5 と R9 の残りは、実装と並べて直してよい。
