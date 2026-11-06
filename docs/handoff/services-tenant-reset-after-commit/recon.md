# recon: services の「commit の後に会社の付け直しが無い」6か所の実物点検

- 基準: origin/main d344d12ea（2026-11-05 #5158 マージ後）
- 出所: docs/handoff/calendar-sync-tenant-reset/impl-report.md「## 段C」（機械的に「commit の次に DB 操作がある」所を数えた6件）
- 生の出力: /tmp/CC報告ファイル/services-reset/02-sites.txt〜06-collision.txt
- 関係 ADR: ADR-072（commit 後は別接続になりうる→reset_tenant_context）／ADR-131（get_db は会社の設定を空にする）／ADR-1018（予定の設定表の RLS）／ADR-145（public.products の RLS）

## 判定の物差し

不具合になるのは、次の3つが全部そろうときだけ。

1. commit の前に、その DB セッションへ会社の設定（search_path・app.tenant_id）が入っている
2. commit の後に、同じセッションで DB を使う
3. その DB 操作の結果が、会社の設定の有無で変わる（会社ごとの表・RLS 付きの表）

## 6か所の判定

| # | 場所 | 判定 | 根拠 |
|---|---|---|---|
| 1 | backend/app/services/calendar_service.py:303→:306（create_event の失敗時） | 不具合なし | except に入るのは :303 の commit より前か :303 そのものの失敗だけ（:303 は try の最後の行）。その前の commit は :271 と google_calendar.py:293 の2つで、どちらも直後に reset_tenant_context がある（calendar_service.py:272、google_calendar.py:294）。google_calendar.create_event・get_event（google_calendar.py:380-416）に他の commit は無い |
| 2 | backend/app/services/tcg_condition_review_svc.py:415→:417（save_condition_review） | 不具合なし | :415 の commit の次の行は :416 の `return`。:417 は別の分岐（prior が無いとき）で、commit の後ではない |
| 3 | backend/app/services/tcg_product_master_svc.py:642→:645（create_product） | 不具合なし | 呼び元の画面2つ（backend/app/routers/tcg_product_master.py:245、backend/app/routers/tcg_product_import.py:426）は get_db と require_super_admin だけで、会社の設定を入れない（物差し1が無い）。:562 の `SET LOCAL app.is_operator` は書き込み用で、commit の後は読むだけ（:645 と find_code_collisions）。products の読み取り規則は「tenant_id が空、または会社が一致」（migrations/20260626_130000_force_rls_public_products.sql:9-13）。作った行は tenant_id を入れない共用商品なので、commit の前後どちらでも見える。CSV 取り込み（backend/app/services/tcg_product_import_svc.py:606）は commit=False で、:642 の commit を通らない |
| 4 | backend/app/services/tcg_product_master_svc.py:845→:849（_run_reanalyze_sync） | 不具合なし | 関数の中で自分の接続を作る（:828-831）。会社の設定は最初から一度も入れない（物差し1が無い）。表は TCG_SCHEMA で名前付き（"public"） |
| 5 | backend/app/services/tcg_product_master_svc.py:907→:910（_run_reanalyze_sync） | 不具合なし | 4と同じ関数・同じ理由 |
| 6 | backend/app/services/tenant.py:1756→:1764（create_tenant_schema） | 不具合なし | :1756 で commit するのは ddl_db（管理用の別セッション・:1682・:1755 の条件）。:1764 で使うのは db で、db は commit していない |

## 結論

- 6か所とも、ADR-072 の型の不具合ではない。コードを直す所は0件。
- 段C の一覧は「commit の次に DB 操作がある」という形だけで数えたため、6件すべてが見かけだけの当たりだった。
- 試験を動かす点検はしていない（コードを読む点検だけ）。

## 未確認

- 1 で :303 の commit そのものが DB 側で失敗したとき、except の UPDATE が動くかどうか（会社の設定とは別の話。失敗後のやり直し処理が無い）。今回の対象外として記録だけ残す。

---

## 追記：見張りの規則案（Rule C）の試し測定（2026-11-05・基準 d344d12ea）

クラウドの調査役が python3 標準の ast だけで試しの規則を作り、今のコードと直す前のコードに当てた（生の記録: クラウド実行 cse_01W47tdhWiUAkufRmiJB2su8）。

- 試しの規則: 引数に db と tenant_id を持つ async def の中で、`await db.commit()` の後に実行されうる文を順にたどり、db を含む最初の文が `await reset_tenant_context(db, ...)` でなければ違反。
- 結果:
  - backend/app/services/ … 0件
  - 直す前の calendar_service.py（d344d12ea^1）… 2件（create_event :271→:276、delete_event :486→:488）＝前回の不具合を2か所とも当てた
  - backend/app/routers/ … 10件（backend/app/ 全体も同じ10件）
  - 今の見張り scripts/lint_tenant_schema.py は services に当てても routers に当てても「OK」

### routers の10件の仕分け（すべて origin/main の実物で確認）

| # | 場所 | 仕分け | 根拠 |
|---|---|---|---|
| 1 | backend/app/routers/leads.py:1649→:1651 | 見かけだけ | :1650 で `reset_tenant_context as _reset_ctx` と別名で読み込み、:1651 で呼んでいる。試しの規則が別名を知らなかった |
| 2 | backend/app/routers/leads.py:2672→:2674 | 見かけだけ | 1 と同じ形（:2673-2674） |
| 3 | backend/app/routers/super_admin_llm_budget.py:171→:174 | 見かけだけ | upsert_budget の tenant_id は URL の値（:143）で、get_current_tenant を通らない＝会社の設定が入らない（物差し1が無い）。表は public.tenant_llm_budgets |
| 4 | backend/app/routers/super_admin_tenants.py:161 | 見かけだけ | delete_tenant_physical の tenant_id は URL の値（:106）。:162 に「reset 不要（get_current_tenant なし）」と書かれている |
| 5 | backend/app/routers/leads.py:712→:759 | 本物 | update_lead（tenant_id は get_current_tenant・:503）。commit の後に _fetch_lead_selections（:335-356）と _fetch_sales_form_options（:359-374）で会社の表を読む |
| 6 | backend/app/routers/order_commissions.py:322→:324 | 本物 | assign_commission（:262）。commit の後に _get_one_commission_row（:202-219）で order_commissions を読む。空なら 500「割当の保存に失敗しました」（:325-330） |
| 7 | backend/app/routers/order_commissions.py:385→:387 | 本物 | unassign_commission（:343）。6 と同じ読み取り |
| 8 | backend/app/routers/order_commissions.py:472→:474 | 本物 | recalculate_order_commissions（:419）。commit の後に _list_commissions（:222-237） |
| 9 | backend/app/routers/orders.py:440→:441 | 本物 | create_order_items（:390）。commit の後に _get_order_items（:162-178）で order_items を読む |

試し1回目の出力は super_admin_tenants.py:161 の後ろが切れて読めず、10件目はこの時点で特定できていない（下の2回目で特定）。

### 試し2回目（規則を直した版・2026-11-05 11:01-11:03Z・origin/main 32b39bd59・クラウド実行 cse_01W47tdgGyhSWrpzrLeWbMh8）

直した点: (a) `@router.*` の付いた関数は tenant_id の既定値が `Depends(get_current_tenant)` のときだけ数える（URL の値の tenant_id は外す）。(b) 付いていない関数は引数に db と tenant_id の両方があるとき。(c) `from app.auth.dependencies import reset_tenant_context as X`（set_tenant_context も）の別名 X も合格とする。生の結果: /tmp/CC報告ファイル/services-reset/25-probe-v2.txt

- backend/app/ 全体 … 6件: 上の表 5〜9 の5件 ＋ backend/app/routers/tenant_profile.py:141→:143 update_tenant_profile
- 直す前の calendar_service.py … 2件（create_event :271→:276、delete_event :486→:488）＝前回の不具合を2か所とも当てた
- 上の表 1〜4（見かけだけ）は0件になった

### 10件目 tenant_profile.py:141 の仕分け

- update_tenant_profile（backend/app/routers/tenant_profile.py:90-150、`@router.put`、tenant_id は `Depends(get_current_tenant)`）。:141 で commit、:143 で tenant_table_ref 付きの表名で tenant_profile を読み直す。reset は呼んでいない。
- 本番の表の設定（reader 鍵の道・2026-11-05T11:05:22Z・生: /tmp/CC報告ファイル/services-reset/29-prod-rls.txt）: tenant_001/003/004/005/006 の tenant_profile は relrowsecurity=False。同じ照会で leads・order_commissions・order_items は5社とも True。
- migrations にも tenant_profile の RLS を入れる文は無い（/tmp/CC報告ファイル/services-reset/27-tp-rls.txt、28-generic-rls.txt）。
- よって今は RLS で行が見えなくなることは起きない（会社名付きの表名で search_path の問題も避けている）。ただし ADR-072 §4 の2の文言（write 系 endpoint で commit の後に reset を呼ばない）には当たる。→ 直し方は他の5か所と同じ1行を足す（例外を作らない）。

### 本番の表の設定で 5〜9 を裏付け

- 上の同じ照会で、leads（5）・order_commissions（6〜8）・order_items（9）は本番の5社すべてで RLS が有効（relrowsecurity=True）。

### 5〜9 を「本物」とした根拠（事実だけ）

- アプリの DB の役は RLS を飛ばせない（migrations/20260605_030000_create_salesanchor_app_role.sql:7 `NOBYPASSRLS`）。set_tenant_context の説明（backend/app/auth/dependencies.py:280-282）も「RLS が見る app.tenant_id を必ず入れる」と書く。
- 読む表には会社ごとの RLS がある: order_commissions（migrations/050_add_commissions.sql:168-183、`tenant_id = public.current_tenant_id()`）、order_items（migrations/20260703_030000_order_items_ben2.sql:43-45、`current_setting('app.tenant_id', true)`）。
- SQLAlchemy の公式資料（Session Basics, 2.0）: commit の後「その接続はプールに返され」「次のトランザクションは新しい接続の払い出しで始まる」。プールの既定は use_lifo=False（Connection Pooling, 2.0）で「順番に使い回す」。本番の接続数は pool_size=20（backend/app/database.py:26）。
- 接続を返す前に get_db が会社の設定を空にする（backend/app/database.py:57-61、backend/app/auth/dependencies.py:361-380）。
- よって commit の後に別の接続へ移ると、app.tenant_id が空か別の会社の値になり、RLS で行が見えなくなる。会社名付きの表名（tenant_table_ref）は search_path の問題しか解かず、RLS には効かない。
- 今の見張りの Rule B はこの5か所を数えない。Rule B は tenant_table_ref を使う関数を対象外にしている（scripts/lint_tenant_schema.py の lint_file 内「`tenant_table_ref` を使っている = 案 A 採用済なので除外」）。ADR-072 §4 の2（docs/adr/ADR-072-tenant-schema-prefix-enforcement.md:106）は「write 系 endpoint で commit の後に reset を呼ばない」を違反と定めており、5か所はこの文言に当たる。

### 未確認

- 5〜9 が本番で実際に空の応答や 500 を出したことがあるか（本番の記録は見ていない）。直し方（commit の直後に reset を1行足す）は SET を3つ打つだけで、出ても出なくても害が無い。
- 公式資料は「新しい払い出し」とだけ書き、同じ接続が戻るか別の接続かは保証していない。別の接続になる場合の振る舞いは上の RLS の定義から導いた。
