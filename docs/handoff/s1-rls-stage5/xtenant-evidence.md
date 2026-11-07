# 接続を貸し出しに戻すときの後始末（Bx）— 別の会社の文脈が残る箇所の全数点検と本番の実測

> この文書は何か（1行）: Bx（返却時に rollback → RESET ALL → commit）を入れる前に、「commit の後に文脈を張り直さずにテナント表を触る箇所（T 箇所）」を全部数え、本番で実際に起きたかを読み取り専用の道で数えた記録。前段の調査は recon-pool-reset.md。

- 基準: origin/main 170ff9612（2026-11-07 fetch）
- 本番の読み取り: ADR-1024 reader 道（1 回 1 文・ai_ro ビューと統計表のみ）。生出力は手元 /tmp/CC報告ファイル/xtenant/q1〜q18
- 本番 DB の起動時刻（統計の起点）: 2026-10-17 03:38:23Z、stats_reset は null

## 1. 本番で漏れが起きたか（実測）

| # | 何を数えたか | 結果 | 判定 |
|---|---|---|---|
| E1 | message_labels・customer_scores の行数と挿入数（5 スキーマ, pg_stat_user_tables） | 全スキーマ n_live_tup=0・n_tup_ins=0 | 分類・点数の経路は本番で一度も動いていない |
| E2 | tenant_calibrations の行数 | 全スキーマ 0 | 同上 |
| E3 | 送信の写し（echo）から自動作成された客（notes='[便1b] echo受信時に自動作成'）の数（q16） | 全スキーマ 0 件 | echo の新規作成経路は本番で一度も動いていない |
| E4 | conversation_logs の tenant_id がスキーマの会社と違う行（q17） | 001: 3579 行中 0、004: 6 行中 0、他は 0 行 | 混入 0 |
| E5 | conversation_logs の lead_id・company_id・contact_id が同じスキーマに無い行（q17） | 全スキーマ 0 | 別会社の客・会社・担当者を指す行 0 |
| E6 | echo で作った客のうち会話記録が無いもの（q18） | 全スキーマ 0 | — |
| E7 | calendar_events | 001: 3 行（挿入 3・更新 1）、004: 12 行（挿入 14・更新 6・削除 2）、他 0 | 件数のみ。中身は読んでいない |

結論（事実）: 現時点の本番データに、別の会社の文脈で書かれた・読まれた跡は見つからない。T 箇所はどれも本番で通っていない、または通っても漏れの形の行を残していない。

## 2. T 箇所（commit の後に張り直さずテナント表を触る）全数

| # | 場所（origin/main） | 何が起きるか | 本番で通ったか |
|---|---|---|---|
| T1 | backend/app/services/priority_scoring.py `label_lead_messages` の `if saved > 0: await db.commit()`（そのあと呼び出し元が続けて読む） | `_compute_and_persist` が commit 後に message_labels・tenant_calibrations を読み、customer_scores へ書く。commit 後は別の接続になりうる | E1・E2 で 0（通っていない） |
| T2 | backend/app/routers/customer_priority.py `get_message_labels` → `label_lead_messages` の commit 後に message_labels を読む | 同上 | E1 で 0 |
| T3 | backend/app/routers/webhook.py `_create_outbound_lead_for_echo` の末尾 `await db.commit()`（張り直し無し）→ 呼び出し元が `write_conversation_log` | companies・contacts を読み、conversation_logs へ書く。conv_log_writer.py の説明（5 行目）「commit 後は reset_tenant_context を呼んでから本関数を呼ぶこと」に反する | E3 で 0（通っていない） |
| T4 | backend/app/services/calendar_service.py 同期の `except` 内 `UPDATE calendar_events SET sync_status='failed'` | try の中の commit（:303 付近）が成功した後に例外が出た場合、張り直し無しで更新 | 件数からは切り分け不能（E7）。経路は commit 自体の失敗後のみ。**改訂（2026-11-07）: 漏れではない。** :303 の commit が失敗した後の except は取引が中断状態で、Bx の有無にかかわらず UPDATE は通らない。commit が成功する側は :271-272・google_calendar の :293-294 で reset 済み（design-pool-reset.md §4-2） |

T ではないと確かめた箇所（本文を読んだ）:
- auth.py register_user: commit 後の `db.refresh(user)` は public.users（SELECT 方針 true）→ 影響なし
- discord_gateway/outside_ticket_notice.py:175: `send_discord_notification`（notifications.py:197-198）が commit→reset、`_create_bell`（:103-104）も commit→reset、失敗時は `_recover_session`（rollback→reset）
- line_device_admin.py:34: 触る表は public.line_import_devices だけ（line_import_devices.py）
- line_import_admin.py:158: 表は `{TCG_SCHEMA}.` と `public.` で修飾済み、文脈を使わない
- routers/analysis_error_reports.py:36・services/analysis_error_report_verify.py:167/:182: operator は `set_config(...,true)`（トランザクション内だけ）、表は public 修飾
- routers/calendar.py:559: 直前 :552-553 で commit→reset、`register_webhook`（google_webhook.py:138-139）も commit→reset
- routers/integrations.py:901: `_handle_invoice_paid` は :926 で set_tenant_context してから処理
- routers/item_corrections.py:157: `save_condition_review`・`v102_job_id_of_item` は `{TCG_SCHEMA}.`・`public.` 修飾
- services/google_webhook.py:405 と tasks/google_calendar_sync.py:26/:62/:63: `sync_tenant_from_google` は自分で set_tenant_context（:255・:278）し、commit→reset（:361-362）
- tasks/tcg_extraction_recovery.py:512-515: 同期エンジンを毎回 dispose、表は修飾済み
- customer_reply_notifier.py `send_customer_reply_notice`: 自分で set_tenant_context（:45）
- webhook.py `_persist_meta_message`: commit のたびに reset（:638-639・:676-677・:690-691・:701-702）
- super_admin_llm_budget.py:173・super_admin_phase_switch.py:156: `reset_operator_context` が commit の**前**（同じトランザクション内）→ 戻る

## 3. operator 'true' が接続に残る箇所（commit の後に戻すだけ）

recon-pool-reset.md r2 の 9 箇所（admin.py:90→95 ほか）に加え、super_admin_suppliers.py:58-75 `_operator_writes`（ハンドラが commit した後の finally で `SET app.is_operator=''`。その SET は新しいトランザクションに入り、close の rollback で消える）。

今の動き（事実の組み立て）: get_db の finally の `clear_tenant_context`（dependencies.py:403-405）も同じく commit の後の新しいトランザクションに入るため、close の rollback で消え、`app.is_operator='true'` が接続に残る。次にその接続を借りた要求が set_tenant_context を通らずに public 表を読むと、operator として読む。

Bx を入れると、返却のたびに RESET ALL が commit されるので、この残りは構造的に 0 になる（recon m4 の実測）。

## 4. 設計への入力（結論）

1. Bx を入れると T1〜T4 は「漏れ」から「失敗（空の文脈＝search_path public）」に変わる（fail closed）。T1〜T3 は commit の直後に `reset_tenant_context` を足して、Bx の前の便（便1）で直す。T4 は直さない（漏れではない。§2 の T4 の改訂と design-pool-reset.md §4-2）。m9 で見つかった残りの箇所も便1 で直す（design-pool-reset.md §4-1）。
2. §3 の operator の残りは Bx だけで消える。個別の直しは要らない（直しても害はないが、変更は一度に 1 つ）。
3. 本番の既存データの修復は不要（E4〜E6 が 0）。

## 5. 気付いた別の不具合（今回の範囲外・記録のみ）

- webhook.py echo / inbound の `except Exception:` は rollback をしないので、commit 自体が失敗すると同じループの後続メッセージも失敗し続ける（今の本番の失敗回数は未確認）。
