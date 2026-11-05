# design: 予定を Google に送る処理の会社付け直し漏れ（作成・削除）

- recon: `docs/handoff/calendar-sync-tenant-reset/recon.md`
- 関係 ADR: ADR-072（commit 直後に reset）／ADR-131（返却時に空へ戻す）／ADR-1018（設定表の RLS）／ADR-1057（つないだ本人の予定だけ送る）／ADR-1060（Meet）
- 新しい ADR は作らない（ADR-072 の決まりに実装を寄せる直しで、新しい判断を含まない）

## 1. 目的（PO の言葉）
つないだ本人がアプリで作った予定が Google に送られ、Meet も付くようにする。アプリで消した予定が Google からも消えるようにする。

## 2. KGI（○×で判定）
| 基準 | 検証方法 |
|------|----------|
| K1 commit のあと別の接続になると、直す前のコードでは Google に送られないことが実 DB で再現する | 段A の commit で CI の pytest（実 PostgreSQL・RLS）が新しい試験だけ赤（失敗名が新しい試験だけ） |
| K2 直したあとは同じ試験が緑 | 段B の commit で CI の pytest が緑 |
| K3 消す処理も同じ（直す前は Google の消す処理が呼ばれない／直した後は呼ばれる） | K1・K2 と同じ |
| K4 ほかの試験を壊さない | CI 全体 fail 0 |
| K5 本番で、つないだ本人が作った新しい予定が「Google に送った」状態になり、Google カレンダーに出る | 本番反映後、PO が予定を1件作り、Google カレンダーに出るか目視。Opus が読み取り鍵で sync_status='synced'・google_event_id 有りを確かめる |

## 3. 対象と対象外
- 対象: `backend/app/services/calendar_service.py` の2か所（:271 の後、:486 の後）に `await reset_tenant_context(db, tenant_id)` を1行ずつ足す。新しい試験ファイル `backend/tests/test_calendar_sync_tenant_reset_pg.py`
- 対象外: 画面・migration・deploy・設定表・ほかの service の commit・止まっている「テスト」予定（id=2）の送り直し（本番データは触らない。K5 は新しい予定で確かめる）
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
- 土台は `backend/tests/test_google_config_rls.py:14-64` と同じ（`tests.rls_bootstrap` の `bootstrap_tenant_schema`・`public_bootstrap_lock`・`_apply_migration`、admin engine と app engine、RLS_ADMIN/RLS_TEST_DATABASE_URL が無ければ skip）
- 適用する migration: `076_add_google_calendar_config.sql`・`077_calendar_sync_mode_and_webhook_subscriptions.sql`・`078_create_calendar_events_tenant.sql`・`20260621_020000_add_schedule_calendar_category_and_owner_settings.sql`・`20261103_200000_add_google_calendar_import_sync.sql`・`20261104_161223_add_calendar_events_meet_url.sql`・`20261016_010000_add_google_config_rls.sql`（テナント表の migration がテナントを引数に取る形なら、既存の試験の当て方に従う）。当て方が分からなければ止まる
- app engine は `poolclass=NullPool`。commit のたびに新しい接続になる＝本番で別の接続が払い出された場合と同じ状態を必ず作る
- テナントは既存試験と重ならない番号（例 982）。設定表に bidirectional・connected_by_user_id=試験の user を admin で入れる
- 試験1 作成: app session で `set_tenant_context` → `calendar_service.create_event(db, tenant_id=…, user_id=つないだ本人, payload=…)`。`app.services.google_calendar.create_event` を偽物に差し替え `{"id": "g-1"}` を返す。期待: 偽物が1回呼ばれる・行の sync_status='synced'・google_event_id='g-1'
- 試験2 削除: admin で google_event_id='g-2' の予定を入れる → app session で `set_tenant_context` → `calendar_service.delete_event`。`google_calendar.delete_event` を偽物に。期待: 偽物が `'g-2'` で1回呼ばれる
- 試験3 対照: つないでいない人（connected_by と別の user）で作成 → 偽物は0回（ADR-1057 が崩れていないこと）
- 後始末: 入れた行を admin で消す・engine を dispose

## 6. 進め方（PO 指示「2,1の順番」）
- 段A（原因の確定）: 試験ファイルだけを commit・push・PR（Draft）。CI の pytest で試験1・試験2 が赤、試験3 が緑になることを記録（K1・K3）
- 段B（直し）: 4 の2行を commit・push。CI 全体緑（K2・K3・K4）
- 段C（数えるだけ）: `backend/app/services/` で「commit の後に reset せず、同じ関数の中でまた db.execute する」箇所を数え、一覧を impl-report に書く。コードは変えない

## 7. 代替案
- A 採用: commit 直後に reset を足す（ADR-072 の既存の形・ほかの7か所と同じ）
- B 不採用: commit の前に設定を読む順に入れ替える → Google 送信後の UPDATE も同じ接続問題が残る（:293 の UPDATE は search_path に依存）
- C 不採用: engine に接続取得時の自動設定を入れる → 全体に影響が大きく、ADR-131 の決定と食い違う

## 8. リスクと対処
- reset が SQLite で動かない → `set_tenant_context` は SQLite で何もしない（`dependencies.py:24-25`）。既存の SQLite 試験に影響なし
- 戻し方: この PR の merge commit を revert

## 9. 外部事例
不要。理由: ライブラリ挙動の比較ではなく、リポジトリ内の既存規則（ADR-072）への揃え直しで、根拠は実 DB の再現試験で直接取るため。

## 10. 維持の仕組み
- 新しい実 DB 試験が CI の pytest（必須チェック）で毎回走る
- 見張りを services に広げるのは段C の数を見て別の作業にする（今回は数だけ）

## 11. 実装カード（クラウド Sonnet 用）
- 枝: `release/calendar-sync-tenant-reset`（この設計書と同じ枝）
- 触ってよいファイル: `backend/tests/test_calendar_sync_tenant_reset_pg.py`（新規）・`backend/app/services/calendar_service.py`（4 の2行だけ）・`docs/handoff/calendar-sync-tenant-reset/impl-report.md`（新規）
- 段A→CI 結果を待って記録→段B→CI 結果を記録→段C の順。段A の CI で試験1・2 が赤にならなければ段B に進まず BLOCKED で止まる
- 想定分岐: (a) migration の当て方が既存試験と違う → 既存の RLS 試験の形に合わせる。合わせ方が分からなければ BLOCKED (b) `create_event` が偽物以外の Google 呼び出しをする → 呼び出し先を読んで同じく偽物にする (c) 試験3 が赤 → 止まって報告
