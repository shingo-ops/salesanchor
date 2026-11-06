# recon — S1 段階④（public の会社ごとの 8 表の RLS）

> この文書は何か：会社ごとの設定・記録なのに、データベース自身の「他社の行を見せない・書かせない」仕組み（RLS）が無い 8 表について、今どこから読み書きされ、そのとき会社の文脈が張られているかを、実物の行番号で並べたものです。

- 基準: origin/main `2bd6c7b92`（2026-11-06 20:3x JST に fetch）。コードの行番号はこの版の `backend/app/` 配下。
- 調べた人: Claude Opus（設計担当）。抜き出しの道具と生の結果は本 PR に載せず、要点だけを下に引用する。
- 発端: ADR-1063 便5（PR #5194）の CI 確かめが、public に tenant_id 列があり RLS の無い表を 18 件見つけた（job 127777711016、2026-11-06T07:49:50Z）。うち会社ごとの 8 件が本段階の対象。残り 10 件（全社共用の一覧 6・運営の記録 4）は便5 の許可一覧に理由付きで載せる（本段階の対象外）。

## 1. 既存 ADR・仕様の検索結果

| 文書 | 関係 |
|---|---|
| docs/adr/ADR-1018-public-sensitive-tables-rls-staged.md | 監査 11 表の段階導入（Accepted）。表ごとに型（4 ポリシー／案 C／付けない）を選ぶ考え方と手順を本段階でも使う。対象は 11 表に固定されており、8 表は含まれない |
| docs/specs/tenant-rls/kgi.md | KGI-1〜3 は 11 表が対象。8 表を足すには KGI の追加に PO 承認が要る（A 区分） |
| migrations/20260626_130000_force_rls_public_products.sql:5-37 | 4 ポリシーの型（ADR-145） |
| docs/handoff/s1-rls-stage2b/design.md | 書込経路に運営の文脈を張る前例（漏れると INSERT は 42501、UPDATE は静かに 0 行） |
| docs/handoff/s1-rls-stage3c/design.md | 案 C（書込・削除だけ DB で止め、読取は全行可）の前例 |
| docs/handoff/tenant-owner-login-approval/design.md:113-125 | 便5（CI 確かめ）の設計。許可一覧に理由を書いて載せる手順 |

## 2. 会社の文脈を張る仕組み（実物）

- 画面からの要求: `backend/app/auth/dependencies.py` の `get_current_tenant` が `SET search_path`・`SET app.tenant_id = '<会社>'`・`SET app.is_operator = ''` を張る（dependencies.py 内 `get_current_tenant` 本文、`SET app.tenant_id` の行）。
- 道具: `set_tenant_context`（非同期）・`set_tenant_context_sync`（Celery）・`set_tenant_context_cursor`（生カーソル）・`reset_tenant_context`（commit 後の張り直し）・`clear_tenant_context`（返却前に空へ）・`set_operator_context`（`app.is_operator='true'`）・`reset_operator_context`。
- `backend/app/database.py:46-61` の `get_db` は開始時に何も張らず、終わりに `clear_tenant_context` を呼ぶ。→ `get_db` だけを使う運営画面（`require_super_admin`）は、会社の文脈も運営の文脈も空のまま SQL を流す。
- ポリシーの比べ方の前例: `tenant_id = current_setting('app.tenant_id', true)::INTEGER`。文脈が空だと右辺は NULL になり、行は 0 件に見える。

## 3. 本番の行数（reader 鍵の道・ADR-1024、2026-11-06T11:20:42Z、AUDIT sha=62bad8783d59）

| 表 | 会社ごとの行数 | 合計 |
|---|---|---|
| inventory_movements | （行なし） | 0 |
| discord_server_apply_runs | （行なし） | 0 |
| discord_server_snapshots | 1:1 | 1 |
| google_webhook_subscriptions | 1:1, 4:1 | 2 |
| tenant_llm_budgets | 4:1, 6:1 | 2 |
| tenant_discord_config | 1:2, 4:1, 6:1 | 4 |
| tenant_discord_ticket_config | 1:1, 4:1, 6:1 | 3 |
| tenant_settings | 1,3,4,5,6 各 1 | 5 |

- 窓口のビュー一覧（2026-11-06T11:20:23Z、AUDIT sha=a73d39854436）に出る 8 表は `public__<表>` だけで、会社スキーマ側に同名の表のビューは無い。pg_tables を直接読んでも 8 表は public にだけあり、他のスキーマには 0 件（2026-11-06T11:33:46Z、AUDIT sha=e126252f03aa）。
- 全 8 表で `tenant_id` が空（NULL）の行は 0（上の集計に NULL の組が出ない）。

## 4. 読み書きしている箇所と、そのときの文脈（試験コードを除く）

凡例: 会社＝`get_current_tenant` か `set_tenant_context*` で自社の文脈あり／運営＝`require_super_admin` だけで文脈なし／前＝会社が決まる前に読む／横断＝全社をまたいで読む

### 4-1. inventory_movements（0 行）
| 箇所 | 種類 | 文脈 |
|---|---|---|
| backend/app/services/inventory_movements.py:38 | SELECT（不変条件の確かめ、試験用の道具） | 呼び出し元は試験だけ（本番コードに呼び出しなし） |
| scripts/export_inventory_for_sheet.py:98-118 | SELECT（手で流す CSV 書き出し） | `engine.connect()` で直接つなぎ、文脈を張らない。`WHERE tenant_id = :tid` だけ |
- 本番コードに INSERT・UPDATE・DELETE は無い（2026-10-02 に取込機能を削除。inventory_movements.py:4-11 の説明）。

### 4-2. discord_server_snapshots（1 行）・discord_server_apply_runs（0 行）
| 箇所 | 種類 | 文脈 |
|---|---|---|
| backend/app/routers/discord_own_server.py:107（`take_own_server_snapshot` :117 から） | INSERT | 会社（:119 get_current_tenant） |
| backend/app/routers/discord_own_server.py:375（`apply_own_server_plan` :386 から） | INSERT | 会社（:389） |
- 読む箇所は本番コードに無い。

### 4-3. tenant_discord_config（4 行）
| 箇所 | 種類 | 文脈 |
|---|---|---|
| backend/app/discord_gateway/client.py:108-126 `_resolve_tenant_id` | SELECT（guild_id → 会社） | 前（文脈なし） |
| backend/app/tasks/discord_own_staff_sync.py:24 `_run_all` | SELECT（全社の一覧） | 横断 |
| backend/app/services/discord_role_sync.py:66 | SELECT | 前（文脈なし）。`_get_guild_and_role_names`（:53-80）が自分で AsyncSessionLocal を開き、文脈を張らずに読む（U2 で確認） |
| backend/app/routers/discord_guild_config.py:71・199 | SELECT | 会社（:65・:193） |
| backend/app/routers/discord_guild_config.py:122 | INSERT | 会社（:116） |
| backend/app/routers/discord_guild_config.py:160・223 | DELETE | 会社（:155・:218） |
| backend/app/routers/discord_oauth.py:221 | INSERT | 会社（:215 で set_tenant_context） |
| backend/app/routers/discord_own_server.py:124・247 | SELECT | 会社（:119・呼び出し元 :233/:393） |
| backend/app/routers/discord_remove.py:63 | SELECT | 会社（`_get_guild_id` の呼び出し元 :82・:145・:195 はどれも `Depends(get_current_tenant)`＝:85・:148・:198） |
| backend/app/routers/discord_auto_setup.py:101 | SELECT | 会社（:91） |
| backend/app/routers/discord_ticket_config.py:241 | SELECT（JOIN） | 会社（:228） |
| backend/app/services/discord_own_staff_sync.py:110 | SELECT | 会社（:108） |

### 4-4. tenant_discord_ticket_config（3 行）
| 箇所 | 種類 | 文脈 |
|---|---|---|
| backend/app/discord_gateway/outside_ticket_notice.py:51 `_is_staff` | SELECT | 会社（呼び出し元 ticket_channel_writer.py:193 は :180 の set_tenant_context の後。U1 で確認） |
| backend/app/discord_gateway/ticket_channel_creator.py:54 `get_ticket_config` | SELECT | 呼び出しが 2 つ: ticket_channel_creator.py:305 は会社（:292 で set_tenant_context の後）／discord_gateway/client.py:308 は前（:303 `_resolve_tenant_id` の直後に新しいセッションを開き、文脈を張らずに読む）。U1 で確認 |
| backend/app/routers/discord_auto_setup.py:127・391 | SELECT・INSERT | 会社（:91） |
| backend/app/routers/discord_channel_invite.py:105 | SELECT | 会社（:68） |
| backend/app/routers/discord_guild_config.py:88 | SELECT | 会社（:65） |
| backend/app/routers/discord_ticket_config.py:113・147・240 | SELECT・INSERT・SELECT | 会社（:104・:141・:228） |
| backend/app/services/discord_role_sync.py:67 | SELECT（JOIN） | 4-3 と同じ |

### 4-5. google_webhook_subscriptions（2 行）
| 箇所 | 種類 | 文脈 |
|---|---|---|
| backend/app/services/google_webhook.py:212 `verify_channel` | SELECT（channel → 会社） | 前（Google からの通知の受け口） |
| backend/app/services/google_webhook.py:395 `renew_expiring_webhooks` | SELECT（期限切れ間近の全社） | 横断。その後 :404 で会社ごとに set_tenant_context |
| backend/app/services/google_webhook.py:85・119 `register_webhook` | SELECT・INSERT | 呼び出し元が文脈を張る（:387 の説明・:404） |
| backend/app/services/google_webhook.py:170・191 `stop_webhook` | SELECT・DELETE | 呼び出し元 routers/calendar.py:566（register は :559）は会社の画面。register の他の呼び出し元 tasks/google_calendar_sync.py:62（:44 で会社の文脈）・google_webhook.py:405（:404 で会社の文脈）。U2 で確認 |
| backend/app/services/google_webhook.py:283・355 `sync_tenant_from_google` | SELECT・UPDATE | 会社（:255・:278） |
| backend/app/tasks/google_calendar_sync.py:55 | SELECT | 会社（:44） |

### 4-6. tenant_llm_budgets（2 行）
| 箇所 | 種類 | 文脈 |
|---|---|---|
| backend/app/routers/super_admin_llm_budget.py:102・121 | SELECT（全社の一覧・1 社） | 運営（:101 require_super_admin、get_db だけ） |
| backend/app/routers/super_admin_llm_budget.py:154 | INSERT（upsert） | 運営（文脈なし） |
| backend/app/routers/tcg_analysis_dashboard.py:526 | SELECT | 運営（:466） |
| backend/app/services/llm_budget.py:434・475・527・567 | SELECT・UPDATE・UPDATE・INSERT | 呼び出し元 services/message_translator.py:462-490・614-623（翻訳。画面 routers/translation.py・leads.py・conv_logs.py と Celery tasks/translation.py から）Celery 側は tasks/translation.py:79 で set_tenant_context の後に呼ぶ（U3 で確認） |
| backend/app/services/discord_notifier.py:222・254 | UPDATE（通知の間引き） | 予算切れの通知（:182・:208）から。呼び出し元の文脈は翻訳と同じ |
| backend/app/services/translation_monitor.py:114・129 | SELECT・INSERT | 会社（:59 set_tenant_context） |

### 4-7. tenant_settings（5 行）
| 箇所 | 種類 | 文脈 |
|---|---|---|
| backend/app/routers/tenant_policy.py:65・101・129・153 | SELECT・SELECT・UPDATE・SELECT | 会社（:52・:88） |
| backend/app/routers/super_admin_phase_switch.py:72・126・129 → services/phase_gate.py:75・147 | SELECT・INSERT（upsert） | 運営（:89 require_super_admin、文脈なし） |
| backend/app/services/tenant.py:1803 `create_tenant_schema` | INSERT（会社を作るときの初期行） | :1780 で `set_config('app.tenant_id', <新しい会社>, true)` |

## 5. 分かったこと（事実）

1. 8 表とも、会社の画面からの読み書きは自社の文脈の中で行われ、SQL にも `WHERE tenant_id` がある（4 章の「会社」の行）。
2. 会社が決まる前・全社をまたいで読む箇所が 3 表にある: tenant_discord_config（Discord の受け口・全社の点検）、google_webhook_subscriptions（Google の通知の受け口・期限の点検）、tenant_discord_ticket_config（Discord の受け口 client.py:308。文脈を張る前に読む）。加えて tenant_discord_config は discord_role_sync.py:66 も文脈なしで読む。
3. 運営画面が文脈なしで読み書きする表が 2 つある: tenant_llm_budgets・tenant_settings。この 2 表で書込を DB で止めると、運営画面の予算の保存と段階の切替が止まる（運営の文脈を張る変更が要る）。
4. inventory_movements は本番 0 行で、本番コードからの書込は無い。読むのは試験用の道具と手で流す書き出しだけ。
5. 8 表に秘密の値（鍵・パスワード）の列は無い（列の一覧は便5 の調べ。google_webhook_subscriptions は channel_token_hash＝札そのものではなくハッシュと、sync_token を持つ）。

## 6. 未確認だった点と確かめた結果（2026-11-06）

| 番号 | 問い | 結果 | 根拠 |
|---|---|---|---|
| U1 | outside_ticket_notice.py:51・ticket_channel_creator.py:54 は文脈の前か | :51 は会社の文脈の中。:54 の get_ticket_config は client.py:308 から文脈なしで呼ばれる | ticket_channel_writer.py:180→:193、client.py:303→:308、ticket_channel_creator.py:292→:305 |
| U2 | discord_role_sync.py:66-67・discord_remove.py:63・google_webhook.py:170/191 の呼び出し元の文脈 | role_sync は文脈なし（自分でセッションを開く）。discord_remove は会社。stop_webhook は会社の画面から | discord_role_sync.py:53-80、discord_remove.py:85/148/198、routers/calendar.py:559/566 |
| U3 | Celery の翻訳から llm_budget の書込までに文脈があるか | ある | tasks/translation.py:79 set_tenant_context → :81 ensure_inbound_translations |
| U4 | export_inventory_for_sheet.py の接続役 | `DATABASE_URL`（アプリの接続役）。文脈は張らない。型A にすると 0 行になる | scripts/export_inventory_for_sheet.py:182 |
| U5 | 会社スキーマに同名の表があるか | 窓口のビュー 417 本（tenant_*）に 8 表の名前は 0 件 | AUDIT sha=8a083664564d・42166385014e、pg_tables 直接 AUDIT sha=e126252f03aa（2026-11-06）。8 表とも public にだけある |
| U6 | 本番の守りの状態をカタログで読めるか（K4-1 の測り方） | 読める。users は ENABLE・FORCE とも有効、ポリシー 4 本。inventory_movements は両方とも無効 | AUDIT sha=ffc923a4ba16・356907e75a95（2026-11-06T11:32Z） |
