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
