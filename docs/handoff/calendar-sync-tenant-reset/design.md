# design: 予定を Google に送る処理の会社付け直し漏れ（作成・削除）

- recon: `docs/handoff/calendar-sync-tenant-reset/recon.md`
- 設計審査: `docs/handoff/calendar-sync-tenant-reset/design-review.md`（1回目 REVISE・R1〜R6、2回目 REVISE・N1〜N3 を本版で反映）
- 関係 ADR: ADR-072（commit 直後に reset）／ADR-131（返却時に空へ戻す）／ADR-1018（設定表の RLS）／ADR-1057（つないだ本人の予定だけ送る）／ADR-1060（Meet）
- 新しい ADR は作らない（ADR-072 の決まりに実装を寄せる直しで、新しい判断を含まない）

## 1. 目的（PO の言葉）
つないだ本人がアプリで作った予定が Google に送られ、Meet も付くようにする。アプリで消した予定が Google からも消えるようにする。

## 2. KGI（○×で判定）
| 基準 | 検証方法 |
|------|----------|
| K1 commit のあと別の接続になると、直す前のコードでは Google に送られないことが実 DB で再現する | 段A の commit に対する CI の pytest（実 PostgreSQL・RLS・必須チェック）で、失敗した試験の名前が新しい試験ファイルの試験1・試験2・試験1b だけ。判定は Opus が `gh run view --log-failed` の生出力をファイルに保存して読む |
| K2 直したあとは同じ試験が緑 | 段B の commit に対する CI の pytest が成功 |
| K3 消す処理も同じ（直す前は Google の消す処理が呼ばれない／直した後は呼ばれる） | K1・K2 と同じ（試験2） |
| K4 ほかの試験を壊さない | 段B の CI で必須チェックがすべて成功 |
| K5 本番で、つないだ本人が作った新しい予定が「Google に送った」状態になり、Google カレンダーに出る | 本番反映後、PO が予定を1件作り、Google カレンダーに出るか目視。Opus が読み取り鍵で sync_status='synced'・google_event_id 有りを確かめる |

## 3. 対象と対象外
- 対象: `backend/app/services/calendar_service.py` の2か所（:271 の後、:486 の後）に `await reset_tenant_context(db, tenant_id)` を1行ずつ足す。新しい試験ファイル `backend/tests/test_calendar_sync_tenant_reset_pg.py`。試験の土台 `backend/tests/rls_bootstrap.py` の `_TENANT_LOOP_MIGRATIONS` に4行登録（R1）
- 対象外: 画面・migration・deploy・設定表・ほかの service の commit・`calendar_service.py:302,:311` の commit（関数の最後の DB 操作で、呼び出し元 `routers/calendar.py:365-377` も後で DB を読まないため今回の不具合に効かない。design-review (1) C3）・止まっている「テスト」予定（id=2）の送り直し（本番データは触らない。K5 は新しい予定で確かめる）・`routers/google_calendar.py:323,:383`
- 対象外（別の作業として記録）: 見張り `scripts/lint_tenant_schema.py` を services にも広げる。今回は services で同じ形がいくつあるかを数えるだけ（段C・読むだけ）

## 4. 変更前後
```python
# 変更前 calendar_service.py:270-276
    event_id = result.scalar_one()
    await db.commit()

    # Google Calendar に同期
    meet_url: Optional[str] = None
    # 接続は会社で1つ。…（PO 2026-11-02）
    if await can_add_meet(db, tenant_id, user_id):
# 変更後
    event_id = result.scalar_one()
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072: commit 後は別接続になりうる。設定表は RLS（ADR-1018）
    （以下同じ）

# 変更前 calendar_service.py:486-488
    await db.commit()

    sync_mode = await _get_sync_mode(db, tenant_id)
# 変更後
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072
    （以下同じ）
```
`reset_tenant_context` は既に `calendar_service.py:29` で import 済み。

## 5. 試験の設計（実 PostgreSQL・RLS）
- 土台: `backend/tests/test_google_config_rls.py:14-64`（環境変数が無ければ skip・admin engine と app engine・app は `poolclass=NullPool`）と、`backend/tests/test_lead_merge_pg.py:52-65,303-309`（全テナントを回す migration を試験のスキーマだけに限って流す形）
- テナント: **978**（スキーマ `tenant_978`）。`backend/tests` に 978 の使用が無いことを grep で確認済み（982 は `test_suppliers_rls.py:39` と重なるため使わない）
- 土台の登録（R1）: `backend/tests/rls_bootstrap.py` の `_TENANT_LOOP_MIGRATIONS` に次の4行を足す（値はテナントを選ぶ条件の出現回数。design-review の生出力どおり）
  - `"078_create_calendar_events_tenant.sql": 2`
  - `"20260621_020000_add_schedule_calendar_category_and_owner_settings.sql": 1`
  - `"20261103_200000_add_google_calendar_import_sync.sql": 1`
  - `"20261104_161223_add_calendar_events_meet_url.sql": 1`
- 準備の順番:
  1. `bootstrap_tenant_schema(admin_engine, 978)`
  2. `public_bootstrap_lock(admin_engine)` の中で `admin_engine.begin()` の接続を使い、`_apply_migration_on_conn` で次の順に流す: `076_add_google_calendar_config.sql`（schema_name なし）→ `077_calendar_sync_mode_and_webhook_subscriptions.sql`（なし）→ `20260606_010000_add_google_drive_config.sql`（なし。次の 20261016 が IF EXISTS なしで drive 設定表を ALTER するため。既存 `test_google_config_rls.py:45-49` と同じ並び。2回目審査 N1）→ `20261016_010000_add_google_config_rls.sql`（なし）→ `078_create_calendar_events_tenant.sql`（`schema_name="tenant_978"`）→ `20260621_020000_…`（同）→ `20261103_200000_…`（同。前半の public 部分も一緒に入る）→ `20261104_161223_…`（同）
  3. admin で `public.users` に試験の user 2人（つないだ本人 97801・ほかの人 97802、tenant_id=978）を入れる。列は `rls_bootstrap.py` の `_ensure_public_users` の INSERT と同じ列で、`ON CONFLICT (id) DO NOTHING`。値の firebase_uid・username・email は人ごとに別の値（例 `cal-reset-97801`・`cal-reset-97801@example.com`）にする（firebase_uid は UNIQUE `rls_bootstrap.py:238` のため、id=999 の値 `'test-user'` を写さない。2回目審査 N3）（R3。076 の `connected_by_user_id` と 078 の `user_id`・`created_by_user_id` の外部キーのため）
  4. admin で設定表 `public.tenant_google_calendar_config` に tenant_id=978・sync_mode='bidirectional'・connected_by_user_id=97801・`access_token_encrypted='x'`・`refresh_token_encrypted='y'`・calendar_id='primary' を入れる（先に tenant_id=978 の行を消す）
- app session: `async_sessionmaker(app_engine, class_=AsyncSession, expire_on_commit=False)`（`backend/app/database.py` と同じ設定）で作り、最初に `set_tenant_context(db, 978)`
- 偽物: `unittest.mock.patch("app.services.google_calendar.create_event", new=AsyncMock(...))`／`delete_event` も同じ。`calendar_service.py` は関数の中で `from app.services import google_calendar as cal_svc` してから属性を呼ぶので、この差し替えが効く（design-review (3)）
- 試験1 作成（Meet なし）: payload に `add_meet` を入れない（R6）。偽物 create_event は `{"id": "g-1"}` を返す。`create_event(db, 978, 97801, payload)` の後、期待: 偽物が1回呼ばれる・admin で読んだ行の sync_status='synced'・google_event_id='g-1'
- 試験1b 作成（Meet あり）: payload に `add_meet=True`。偽物 create_event は `{"id": "g-1b", "hangoutLink": "https://meet.google.com/test-abc"}` を返す（`_resolve_meet_url` は hangoutLink があれば `get_event` も `asyncio.sleep` も呼ばない。`calendar_service.py:92-112`）。期待: 偽物1回・返り値の meet_url と行の meet_url が `https://meet.google.com/test-abc`・sync_status='synced'
- 試験2 削除: admin で `tenant_978.calendar_events` に google_event_id='g-2'・user_id=97801・created_by_user_id=97801 の予定を1件入れる → `delete_event(db, 978, その id)`。期待: 偽物 delete_event が `(db, 978, 'g-2')` で1回呼ばれる（3番目の引数が 'g-2'）
- 試験3 対照: つないでいない人 97802 で作成（add_meet なし）→ 偽物 create_event は0回・行の sync_status='pending'（ADR-1057 が崩れていないこと）
- 後始末: admin で `tenant_978.calendar_events` の全行・設定表の tenant_id=978 の行・users 97801/97802 を消す。engine を dispose

## 6. 進め方（PO 指示「2,1の順番」）
- 段A（原因の確定）: クラウドの実装役が `rls_bootstrap.py` の登録4行と試験ファイルだけを commit・push。Opus が手元で shingo-cc 名義の Draft PR を作り（R4。クラウドの実装役は PR を作らない）、CI の pytest で試験1・1b・2 が赤、試験3 が緑であることを記録（K1・K3）。赤にならなければ段B に進まない
- 段B（直し）: クラウドの実装役が §4 の2行を commit・push。Opus が CI 全体緑を記録（K2・K3・K4）
- 段C（数えるだけ）: 段B と同じ依頼で、`backend/app/services/` で「commit の後に reset せず、同じ関数の中でまた db.execute する」箇所を数え、一覧を impl-report に書く。コードは変えない

## 7. 代替案
- A 採用: commit 直後に reset を足す（ADR-072 の既存の形。同じ4ファイルで commit 直後に reset している9か所、うち calendar_service.py 内4か所と同じ）
- B 不採用: commit の前に設定を読む順に入れ替える → Google 送信後の UPDATE も同じ接続問題が残る（UPDATE は search_path に依存）
- C 不採用: engine に接続取得時の自動設定を入れる → 全体に影響が大きく、ADR-131 の決定と食い違う

## 8. リスクと対処
- reset が SQLite・偽物の db で動かない → `_dialect_supports_search_path`（`backend/app/auth/dependencies.py:264-274`）が対象外の dialect では何もしない（:293-294）。偽物の db（`AsyncMock`）でも db.execute を消費しない。実例: `update_event` は :364-365 で既に reset しており、`backend/tests/test_calendar_service.py:385` は side_effect 3件のまま通っている
- 試験の migration が共有 DB のほかのテナントを回る → R1 の登録で `tenant_978` だけに限る
- 戻し方: この PR の merge commit を revert

## 9. 外部事例
不要。理由: ライブラリ挙動の比較ではなく、リポジトリ内の既存規則（ADR-072）への揃え直しで、根拠は実 DB の再現試験で直接取るため。

## 10. 維持の仕組み
- 新しい実 DB 試験が CI の pytest（必須チェック）で毎回走る
- 見張りを services に広げるのは段C の数を見て別の作業にする（今回は数だけ）

## 11. 実装カード（クラウド Sonnet 用）
- 枝: `release/calendar-sync-tenant-reset`（この設計書と同じ枝）
- 触ってよいファイル: `backend/tests/test_calendar_sync_tenant_reset_pg.py`（新規）・`backend/tests/rls_bootstrap.py`（`_TENANT_LOOP_MIGRATIONS` に §5 の4行を足すだけ）・`backend/app/services/calendar_service.py`（§4 の2行だけ・段B のみ）・`docs/handoff/calendar-sync-tenant-reset/impl-report.md`（新規）
- 依頼は2回に分ける。1回目=段A（試験と登録だけ push して DONE）。2回目=段B と段C（Opus が段A の CI 赤を確かめた後）
- PR は作らない（Opus が手元で作る）
- 想定分岐: (a) `_scope_tenant_migration` の数が合わず ValueError → 生出力を impl-report に書いて BLOCKED (b) `create_event` が偽物以外の Google 呼び出しをする → 呼び出し先を読んで同じく偽物にする (c) 試験3 が赤になる作りに見える → 止まって報告 (d) users の列が `_ensure_public_users` と合わない → その INSERT 文に合わせる。分からなければ BLOCKED
