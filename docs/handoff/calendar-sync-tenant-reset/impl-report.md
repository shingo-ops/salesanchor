# impl-report: calendar-sync-tenant-reset

## 段A

開始時点の HEAD: `3ebeefa41 docs: calendar-sync-tenant-reset の設計再審査（3回目・APPROVE）`

### 変えたファイル
- `backend/tests/rls_bootstrap.py`: `_TENANT_LOOP_MIGRATIONS` に設計 §5 の4行だけ足した（078 は 2、ほか3本は 1）
- `backend/tests/test_calendar_sync_tenant_reset_pg.py`（新規）: テナント978・user 97801（つないだ本人）/97802（ほかの人）
- `backend/app/services/calendar_service.py` は触っていない（段B）

### 各試験が確かめること
- 試験1 `test_create_event_sends_to_google_after_commit`: Meet なしの作成で、偽物 create_event が1回呼ばれ、行が synced・google_event_id='g-1'
- 試験1b `test_create_event_with_meet_saves_meet_url`: add_meet=True で、返り値と行の meet_url が hangoutLink、synced・'g-1b'
- 試験2 `test_delete_event_calls_google_delete_after_commit`: 削除で偽物 delete_event が `(db, 978, 'g-2')` で1回呼ばれる
- 試験3 `test_create_event_by_non_connected_user_is_not_sent`: 97802 の作成では create_event 0回・sync_status='pending'（ADR-1057 の対照）
- 準備の順番・偽物・後始末は設計 §5 のとおり（後始末は calendar_events 全行・設定表978・users 2人を消し engine を dispose）

### py_compile 生出力
```
$ python -m py_compile tests/rls_bootstrap.py tests/test_calendar_sync_tenant_reset_pg.py
py_compile exit=0
```
（出力なし・終了コード0）

### 補足（未確認事項）
- 手元には sqlalchemy が無く、pytest は実行していない（実 DB の赤/緑は段Aの CI で確認する）
- 登録した4本の migration について、選択条件の出現回数を正規表現で数え 2/1/1/1 で一致を確認した

### 想定分岐 (a)〜(d)
- (a) 数の不一致: 当たらなかった
- (b) create_event の偽物以外の Google 呼び出し: 当たらなかった（`_resolve_meet_url` は hangoutLink があれば追加呼び出しなし）
- (c) 試験3が赤になる作り: 当たらなかった
- (d) users の列不一致: 当たらなかった（`_ensure_public_users` の列に合わせた）

### push 後の git log --oneline -2
```
443535720 test: 予定の作成・削除の会社付け直し漏れを再現する実DB試験（段A）
3ebeefa41 docs: calendar-sync-tenant-reset の設計再審査（3回目・APPROVE）
```
push 先: `origin/release/calendar-sync-tenant-reset`（3ebeefa41..443535720）。pre-push の入口は全部通過（落ちた検査 0 件）。

## 段B

変えたのは `backend/app/services/calendar_service.py` の2行（足しただけ）。

### git diff 生出力

```
diff --git a/backend/app/services/calendar_service.py b/backend/app/services/calendar_service.py
index d769d991c..7e6d128e3 100644
--- a/backend/app/services/calendar_service.py
+++ b/backend/app/services/calendar_service.py
@@ -269,6 +269,7 @@ async def create_event(
     )
     event_id = result.scalar_one()
     await db.commit()
+    await reset_tenant_context(db, tenant_id)  # ADR-072: commit 後は別接続になりうる。設定表は RLS（ADR-1018）
 
     # Google Calendar に同期
     meet_url: Optional[str] = None
@@ -484,6 +485,7 @@ async def delete_event(
         {"id": event_id},
     )
     await db.commit()
+    await reset_tenant_context(db, tenant_id)  # ADR-072
 
     sync_mode = await _get_sync_mode(db, tenant_id)
     if google_event_id and sync_mode in ("bidirectional", "write_only"):
```

### py_compile 生出力

```
$ python -m py_compile backend/app/services/calendar_service.py
(出力なし)
exit=0
```

## 段C

読むだけ（コードは変えていない）。`backend/app/services/` 配下で、`commit` の後に `reset_tenant_context` を呼ばず、同じ関数の中でまた `execute` する箇所。段B 適用後の行番号。

**数: 6 件**

| # | commit | その後の execute | 関数 |
|---|---|---|---|
| 1 | backend/app/services/calendar_service.py:303 | :306 | create_event |
| 2 | backend/app/services/tcg_condition_review_svc.py:415 | :417 | save_condition_review |
| 3 | backend/app/services/tcg_product_master_svc.py:642 | :645 | create_product |
| 4 | backend/app/services/tcg_product_master_svc.py:845 | :849 | _run_reanalyze_sync |
| 5 | backend/app/services/tcg_product_master_svc.py:907 | :910 | _run_reanalyze_sync |
| 6 | backend/app/services/tenant.py:1756 | :1764 | create_tenant_schema |

注意（未確認の点）:
- 数え方は文面の並び順（ソース上の行順）。分岐・繰り返しの実行順は見ていない。
- 1 は commit が try の中、execute が except の中（commit 自体が失敗した後の経路）。実際に会社付けが落ちる経路かは未確認。
- 各件で、その execute が会社ごとの表（RLS）を触るかは見ていない。要否の判断は PO / 設計役。
- `db` 以外の名前のセッションでも `.commit()` / `.execute()` なら数える作りで、`reset_tenant_context` は名前一致で判定。

### 数え方のコマンド

```
python -I <scratchpad>/stagec.py backend/app/services
```

stagec.py の中身: `ast` で各関数（入れ子の関数は除く）の `.commit()` / `.execute()` / `reset_tenant_context()` の呼び出しを行順に並べ、commit のあとに reset が無いまま execute が来たら1件と数える（1つの commit につき最初の execute だけ）。

生出力:

```
backend/app/services/calendar_service.py:303 (commit) -> :306 (execute) in create_event
backend/app/services/tcg_condition_review_svc.py:415 (commit) -> :417 (execute) in save_condition_review
backend/app/services/tcg_product_master_svc.py:642 (commit) -> :645 (execute) in create_product
backend/app/services/tcg_product_master_svc.py:845 (commit) -> :849 (execute) in _run_reanalyze_sync
backend/app/services/tcg_product_master_svc.py:907 (commit) -> :910 (execute) in _run_reanalyze_sync
backend/app/services/tenant.py:1756 (commit) -> :1764 (execute) in create_tenant_schema
COUNT 6
```
