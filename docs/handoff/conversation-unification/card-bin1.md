# 実装カード 便1: 会話を書く所と読む所を meta_messages だけにする

> この文書は何か（専門用語なしの1行）:
> 会話を2つの表に二重に書いている所をやめ、手で記録した会話も受信箱の表1つに入れ、会話を読む画面と集計をその表だけから読むように直す作業の指示書。

- 親: design.md §4 便1・§6・§7、recon.md §8（KGI K1〜K5 は PO 承認 2026-11-07「1」。設計審査3回目 APPROVE）
- 基準: origin/main 7947055fe（2026-11-07 23:5x JST 取得）。行番号はすべてこの版で Opus が読んで確かめた（a8d860b76 と対象ファイルの中身は同じ）
- ブランチ: `release/conversation-unify-bin1`（`bash scripts/new-worktree.sh release/conversation-unify-bin1 --claude`）
- 読んだ決まり: docs/handoff/design-partner-card-ops/guards/00-common.md・04-worktree.md・05-pr.md・10-executor.md
- 受領確認: 着手の前に、このカードの §0 の3つを満たしたかを1行で返してから始める
- 起票: Draft・`--base main`・`shingo-cc` 名義。**危険 PR**（`migrations/`・`scripts/run_all_migrations.sh`・本番 `scripts/smoke_test_post_deploy.sh` を含む。ADR-135・ADR-136）。マージ・本番反映は担当が行わない

## 0. 着手条件（満たさなければ止まって BLOCKED: で返す）

- origin/main の次の行が下の表の「基準の中身」と同じ（例 `git show origin/main:backend/app/routers/webhook.py | sed -n '833p'` の形で、表の5行をそれぞれ確かめる。1つでも違えば BLOCKED: で差を返す）

| 場所 | 基準の中身（先頭の語） |
|---|---|
| `backend/app/routers/webhook.py:833` | `await write_conversation_log(` |
| `backend/app/routers/webhook.py:878` | `await write_conversation_log(` |
| `backend/app/discord_gateway/dm_writer.py:233` | `await write_conversation_log(` |
| `backend/app/routers/leads.py:999` | `where = ["lead_id = :lead_id", "tenant_id = :tenant_id"]` に当たる行 |
| `backend/app/routers/conv_logs.py:262` | `f"INSERT INTO {schema}.conversation_logs "` |

- 本番の名簿（全社1つ）は6行で、id 10・11・12（phone・in_person・whatsapp）の会話の置き場が conversation_logs、id 7・8・9 が meta_messages。Opus が 2026-11-07 に読み取り専用の鍵で確かめた（`/tmp/CC報告ファイル/conv/card5/q10.txt`）。名簿の値は**この PR では変えない**（§11 の手順で反映後に PO が流す）
- 本番の v_company_stats は5社とも同じ定義で、列は company_id・total_deal_amount・paid_invoice_count・last_paid_at・deal_count・conversation_count・last_conversation_at の順（`/tmp/CC報告ファイル/conv/card6/q13.txt`）

## 1. やること（この順）

1. `./scripts/dev/executor-preflight.sh || exit 1`
2. §2 の書く所を直す（写しをやめる）
3. §3 の手の記録の API を meta_messages に向ける
4. §4 の「手の記録を自動連携の行として扱わない」条件と「消した印」の条件を足す
5. §5 の読む所を meta_messages に付け替える
6. §6 の migration を足し、`scripts/run_all_migrations.sh` の末尾に1行足す
7. §7 の片付け（毎朝の突合・逆向きの台本・smoke [7e]・新しい会社の表の列）
8. §8 の画面を直す
9. §9 の試験を直す・足す
10. API の形の写しを作り直す: `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json`（API の形は変えないので差は出ない見込み。差が出たら NEEDS_DECISION:）
11. §10 の検索を流し、期待どおりの件数か確かめる
12. 試験は手元の Mac で回さない（PO 11/2）。push して GitHub の CI で確かめる
13. PR 本文に「消すファイル」欄（§7 の5つ）・`### 標準ワークフロー確認` 欄・`git diff main...HEAD --name-only` の全一覧・migration の一覧（§6 の1本だけ）を書く

## 2. 書く所（写しをやめる）

| 場所（origin/main 7947055fe） | 変更前 | 変更後 |
|---|---|---|
| `backend/app/routers/webhook.py:54` | `from app.services.conv_log_writer import write_conversation_log` | 消す（このファイルで使う所が無くなるため） |
| `backend/app/routers/webhook.py:818-853` の echo の枝 `if m.get("is_echo"):` | リードを探し、無ければ `_create_outbound_lead_for_echo` で作り、`write_conversation_log(... direction="outbound" ...)`・commit・reset・`continue` | 枝の中身を「ログに1行出して `continue`」だけにする（`logger.info("[webhook] echo skipped (conversation unification bin1): sender=%s", m.get("sender_id"))`）。リードを作らない・何も書かない。`_create_outbound_lead_for_echo` と `_find_lead_id_for_psid` の関数そのものは**消さない**（便1.5 で使う。他から呼ばれなくなっても残す） |
| `backend/app/routers/webhook.py:876-897` 受信の写し | `try: await write_conversation_log(...)`・commit・reset、`except` で warning | ブロックごと消す。直前の meta_messages への書き込みと、その後の処理はそのまま |
| `backend/app/discord_gateway/dm_writer.py:38` | `from app.services.conv_log_writer import write_conversation_log` | 消す |
| `backend/app/discord_gateway/dm_writer.py:230-250` | `# SA-02 Stage 1: conversation_logs にも書く` からの写し | 消す。`:252` の `await db.commit()` は残す |
| `backend/app/services/conv_log_writer.py` | 写しの関数と、会社・連絡先を補う関数 | **ファイルは残す**（`_get_company_id_for_lead`・`_get_contact_id_for_lead` を §3 で使う。`write_conversation_log` も便3 まで残す）。中身は変えない |

## 3. 手の記録の API（`backend/app/routers/conv_logs.py`）

URL・受け取る形・返す項目・状態番号（201・404・409・410）は**変えない**。表と列だけを替える。列の対応:

| 今の conversation_logs | meta_messages |
|---|---|
| channel_type | platform |
| content_text | message_text |
| occurred_at | occurred_at（そのまま。加えて created_at も同じ値） |
| deleted_at・recorded_by_user_id・lead_id・company_id・contact_id・direction | 同じ名前 |
| （無し） | is_manual = TRUE・sender_id = `'manual:user_' || recorded_by_user_id`・sender_name = NULL・message_id = `'manual_' || uuid4().hex` |

| 場所 | 変更後 |
|---|---|
| `:68-70` `ChannelMasterCreate.platform` | `platform: str = Field(..., max_length=20)`（meta_messages.platform が VARCHAR(20) のため。`Field` は pydantic から import） |
| `:82-110` `_fetch_conv_log` | `SELECT id, lead_id, platform, direction, message_text, occurred_at, deleted_at, recorded_by_user_id, message_id, is_manual FROM {schema}.meta_messages WHERE id = :id`。返す辞書のキーは今の8つ（channel_type・content_text の名前のまま）に `message_id`・`is_manual` を足す |
| `:113-165` `_fire_translation` | 引数の `log_id` を `message_id: str` に替える（`:133` の `f"conv_log_{log_id}"` を消し、渡された message_id を使う）。書き戻しは `UPDATE {schema}.meta_messages SET original_language = :lang WHERE message_id = :mid` だけにする（translated_text の写しをやめる。訳は message_translations に残る）。`results.get("ja", next(iter(results.values())))` の選び方と、例外を握って warning にする形は今のまま |
| `:196-300` 作成 | `:212-222` の 400 は今のまま。`body.channel_type` が 20 文字を超えたら 400「連絡手段の名前が長すぎます」を足す。重複確認 `:227-256` は `FROM {schema}.meta_messages WHERE lead_id = :lead_id AND is_manual = TRUE AND deleted_at IS NULL AND platform = :channel_type AND message_text = :content_text AND occurred_at BETWEEN :from AND :to`（±1時間・409 の文言は今のまま）。INSERT `:260-279` は §3 の対応表の列で `INSERT INTO {schema}.meta_messages (tenant_id, lead_id, company_id, contact_id, platform, direction, message_text, occurred_at, created_at, recorded_by_user_id, is_manual, sender_id, sender_name, message_id) VALUES (...) RETURNING id`。company_id は今と同じ `_get_company_id_for_lead`、contact_id は `_get_contact_id_for_lead`（どちらも `app.services.conv_log_writer` から import）。監査 `:281-292` の表の名前は `"meta_messages"`、record_id は新しい meta の id（画面の名前の対応 `ja.json:2564`・`en.json:2564` に既にある）。翻訳の発火は INSERT した message_id で呼ぶ。返す `{"id": 新しい meta の id}` |
| `:308-344` 一覧 | `SELECT m.id, m.platform, m.direction, m.message_text, (SELECT mt.translated_text FROM {schema}.message_translations mt WHERE mt.message_id = m.message_id ORDER BY (mt.target_language = 'ja') DESC, mt.id ASC LIMIT 1), m.occurred_at, m.recorded_by_user_id, m.created_at FROM {schema}.meta_messages m WHERE m.lead_id = :lead_id AND m.is_manual = TRUE AND m.deleted_at IS NULL ORDER BY m.occurred_at ASC, m.id ASC`。返すキーは今の8つのまま |
| `:352-407` 変更 | `existing` が None、lead が違う、**または `existing["is_manual"] is not True`** なら 404（自動連携の行を手の記録の API で直させない）。410 は今のまま。UPDATE の列は `content_text`→`message_text`、`occurred_at` を直すときは `created_at` も同じ値にする（`SET message_text = :message_text` / `SET occurred_at = :occurred_at, created_at = :occurred_at`）。監査は表の名前 `"meta_messages"`、old_data・new_data のキーは今のまま（content_text・occurred_at）。再翻訳は `existing["message_id"]` で呼ぶ |
| `:415-455` 削除 | 404 に `is_manual is not True` を足す（変更と同じ）。`UPDATE {schema}.meta_messages SET deleted_at = :now WHERE id = :id`。監査は表の名前 `"meta_messages"`、old_data は今のまま |
| `:488` 付近 `create_channel_master` の INSERT | `'conversation_logs'` を `'meta_messages'` にする（新しく足す会社独自の手動窓口も meta に置く） |

## 4. 手の記録を「自動連携の行」として扱わない・消した行を出さない

`is_manual IS NOT TRUE` は「手の記録でない」の意味（今の自動連携の行は is_manual が NULL）。

| 場所 | 足す条件 |
|---|---|
| `backend/app/routers/leads.py:999` 会話の流れの where 一覧 | `"deleted_at IS NULL"` を足す（`:1008-1022` の添付列ありと `:1027-1041` の無し、両方がこの一覧を使う）。手の記録は**除かない**（K3） |
| `backend/app/routers/leads.py:1100-1115` 最新の窓口 | `messages[-1]["platform"]` を使う枝を消し、いつも別の問い合わせで読む。その問い合わせに `AND is_manual IS NOT TRUE` を足す |
| `backend/app/routers/leads.py:1119-1126` 24時間の窓（最後の受信） | `AND is_manual IS NOT TRUE` |
| `backend/app/routers/leads.py:1301-1310` 未読に戻す | `AND is_manual IS NOT TRUE` |
| `backend/app/routers/leads.py:1834-1844` 送信の宛先 | `AND is_manual IS NOT TRUE` |
| `backend/app/routers/leads.py:2453-2460` 画像の送信の宛先 | `AND is_manual IS NOT TRUE` |
| `backend/app/routers/meta_inbox.py:934-937` latest の CTE・`:946-948` agg の CTE | どちらにも `AND mm.is_manual IS NOT TRUE` |
| `backend/app/services/priority_scoring.py:266-277` | `AND is_manual IS NOT TRUE` |
| `backend/app/services/translation_monitor.py:72-73` の WHERE | `AND m.is_manual IS NOT TRUE` |

## 5. 読む所を meta_messages へ

| 場所 | 変更後 |
|---|---|
| `backend/app/routers/analytics.py:2253-2261` 週次の助言 | `SELECT company_id, MAX(COALESCE(occurred_at, created_at)) AS last_conversation_at FROM meta_messages WHERE company_id IS NOT NULL AND deleted_at IS NULL GROUP BY company_id`。前後の try・辞書の作り方は今のまま |
| `backend/app/routers/analytics.py:2484-2525` 成約分析の会話 | `meta_platforms` と `log_platforms` を順番を保って合わせた1つの一覧（重複なし）にし、`meta_messages` の問い合わせ（今の `:2487-2502` の形・`m.created_at AS ts`）を1回だけ流す。`wa_rows` と conversation_logs の問い合わせを消す。`platforms_by_store` の2回の呼び出しは残す（名簿の値を変える前も後も同じ結果になるため）。本番で前後の入力が同じことは Opus が確かめた（下の §12） |
| `backend/app/routers/companies.py:1082-1131` 会社の会話タブ | `SELECT m.id, m.contact_id, m.lead_id, m.platform, m.direction, m.message_text, (SELECT mt.translated_text FROM {schema}.message_translations mt WHERE mt.message_id = m.message_id ORDER BY (mt.target_language = 'ja') DESC, mt.id ASC LIMIT 1), COALESCE(m.occurred_at, m.created_at), m.recorded_by_user_id, co.display_name FROM {schema}.meta_messages m LEFT JOIN {schema}.contacts co ON co.id = m.contact_id WHERE m.company_id = :company_id AND m.deleted_at IS NULL {contact_filter} ORDER BY COALESCE(m.occurred_at, m.created_at) DESC, m.id DESC LIMIT :limit`。contact_filter は `m.contact_id`。返すキー10個（channel_type・content_text の名前のまま）は今のまま。関数の説明文の「conversation_logs」を「meta_messages」に |
| `backend/app/services/lang_judge.py:33-37` `_NOT_VERBATIM_CLAUSE` | `cm.platform = cl.channel_type` を `cm.platform = m.platform` に |
| `backend/app/services/lang_judge.py:45-76`・`:85-111` | どちらも UNION ALL をやめ、meta_messages だけの1つの問い合わせにする: `FROM {schema}.meta_messages m WHERE m.lead_id = :lead_id AND m.direction = 'inbound' AND m.original_language IS NOT NULL AND m.deleted_at IS NULL {_NOT_VERBATIM_CLAUSE}`。params の `tenant_id` は残す。説明文の「conversation_logs」を消す |
| `scripts/lead_regression/generate.py:430-524` | WhatsApp の会話を conversation_logs から読む所を、analytics と同じく meta_messages から読む形にする。`copy_rows`（conversation_logs への写し）を消す。期待の数（試験）は変えない |

## 6. 集計ビューの作り直し（migration）

新しいファイル `migrations/20261108_100000_rebuild_company_stats_on_meta_messages.sql`。`scripts/run_all_migrations.sh` の末尾（`:66` の `20261107_160000` の行の後）に、説明の1行と `run_sql migrations/20261108_100000_rebuild_company_stats_on_meta_messages.sql` を足す。

中身の決まり:
- `DO $$ ... $$` で `pg_namespace` の `^tenant_\d+$` を回す（`migrations/20260612_120000_fix_company_stats_ssot.sql:107-164` と同じ形）
- 次の3つが全部あるスキーマだけ対象。無ければ `RAISE NOTICE` して CONTINUE: `companies` 表、`meta_messages` 表、`meta_messages.company_id`・`occurred_at`・`deleted_at` の3列（`information_schema.columns` で数える）
- **`DROP` を書かない**。`CREATE OR REPLACE VIEW %I.v_company_stats AS` で、列の名前・順番・型を今と同じにする:

```sql
SELECT
    c.id AS company_id,
    COALESCE(SUM(i.total_amount), 0)                                                     AS total_deal_amount,
    COUNT(DISTINCT i.id)                                                                  AS paid_invoice_count,
    MAX(i.paid_at)                                                                        AS last_paid_at,
    COUNT(CASE WHEN l.status IN ('negotiating', 'existing_customer', 'lost') THEN 1 END) AS deal_count,
    COUNT(DISTINCT m.id)                                                                  AS conversation_count,
    MAX(COALESCE(m.occurred_at, m.created_at))                                            AS last_conversation_at
FROM %I.companies c
LEFT JOIN %I.invoices i
    ON i.company_id = c.id
    AND i.paid_at IS NOT NULL
    AND i.voided_at IS NULL
LEFT JOIN %I.leads l
    ON l.id = c.lead_id
LEFT JOIN %I.meta_messages m
    ON m.company_id = c.id
    AND m.deleted_at IS NULL
GROUP BY c.id
```

- 型の根拠: 今の `last_conversation_at` は `conversation_logs.occurred_at TIMESTAMPTZ`（`migrations/20260604_090000_create_conversation_logs.sql:53`）の MAX。新しい方は `meta_messages.occurred_at TIMESTAMPTZ`（`migrations/20260622_010000_add_meta_messages_master_history_columns.sql:40`）と `created_at TIMESTAMPTZ`（`backend/app/services/tenant.py:1038`）の COALESCE なので同じ型
- 1社ごとに `RAISE NOTICE 'migration 20261108_100000: %.v_company_stats を meta_messages で作り直し'`。最後に件数
- ファイル末尾のコメントに戻し方: 「`migrations/20260612_120000_fix_company_stats_ssot.sql` の CREATE 部分を CREATE OR REPLACE にして流す（列が同じなので DROP は要らない）」
- 値を変える文（INSERT・UPDATE・DELETE）は書かない（ADR-1007・`backend/tests/test_value_migrations_neutralized.py`）

## 7. 片付け

| 場所 | 変更 |
|---|---|
| `backend/app/celery_app.py:32` | `"app.tasks.sa02_recon_monitor",` の行を消す |
| `backend/app/celery_app.py:151-157` | `sa02-daily-recon` の項目と、その上の3行の説明を消す |
| `backend/app/tasks/sa02_recon_monitor.py` | ファイルごと消す |
| `backend/tests/test_sa02_recon_monitor.py` | ファイルごと消す |
| `scripts/migrate_sa02_stage2_meta_to_conv_logs.py`・`scripts/verify_sa02_stage2_count_check.py` | ファイルごと消す（逆向きの台本。`scripts/run_all_migrations.sh` からは呼ばれていない） |
| `backend/tests/test_sa02_stage2_preflight.py` | ファイルごと消す（上の台本2本の試験） |
| `scripts/tests/test-detect-external-api-change.js:117`・`:186` | `sa02_recon_monitor.py` の行を消し、`:119` の `cases.length, 8` を 7 に、`:203` の `29` を 28 にする |
| `scripts/smoke_test_post_deploy.sh:158-165` [7e] | 読む表を `tenant_004.meta_messages` に替え、見出しと PASS・FAIL の文の `conversation_logs` を `meta_messages` に替える。ほかは今のまま |
| `backend/app/services/tenant.py:1045` の後（新しい会社の meta_messages） | 新しい会社でも §4 の条件が動くよう、`ALTER TABLE {schema}.meta_messages ADD COLUMN IF NOT EXISTS ...` を1文で足す。足す列は `migrations/20260622_010000_add_meta_messages_master_history_columns.sql:33-43` の11列と**同じ名前・同じ型・同じ既定値**（contact_id・company_id・deal_id・channel_identity・original_language・status・analysis・occurred_at・deleted_at・recorded_by_user_id・is_manual）。今は新しい会社の表にこの列が無く、次の移行の実行まで受信箱が読めない（設計審査3回目の低3） |

## 8. 画面（手で記録した直後に会話の流れに出す・K3）

| 場所 | 変更 |
|---|---|
| `frontend/src/pages/inbox/ManualRecordSection.tsx:80-83` Props | `onSaved?: () => void` を足す |
| 同 `handleSave` の成功の所（`setSavedCount((c) => c + 1);` の後） | `onSaved?.();` を足す。依存配列に `onSaved` を足す |
| `frontend/src/pages/inbox/useInboxState.ts` | `const reloadMessages = useCallback(async () => { if (selectedLeadId !== null) await loadMessages(selectedLeadId); }, [selectedLeadId, loadMessages]);` を足し、`:1120` からの返す物に `reloadMessages` を足す（反応を付けた後の読み直し `:524`・`:530` と同じやり方） |
| `frontend/src/pages/inbox/InboxMessageThread.tsx:53` からの Props | `onManualRecordSaved?: () => void` を足す。`:862-867` の `ManualRecordSection` に `onSaved={onManualRecordSaved}` を渡す |
| `frontend/src/pages/inbox/InboxPage.tsx:129` からの `InboxMessageThread` | `onManualRecordSaved={state.reloadMessages}` を渡す |
| 文字・色 | 新しい文字・色・部品は足さない（i18n・デザイントークンの変更なし） |
| `frontend/src/pages/company-detail/CompanyConvLogsTab.tsx:4` | 説明コメントの「conversation_logs」を「meta_messages」に。ほかは変えない（返すキーが同じため） |

## 9. 試験

### 9-1. 試験の表の形（列を足すだけ。期待の数は変えない）

`deleted_at`・`is_manual` を読む条件を足すので、試験で自前に作る meta_messages の表に列が無いと落ちる。次の定義に、無い列だけ足す（`deleted_at TIMESTAMP`・`is_manual BOOLEAN`。SQLite は型名だけで良い。PG は `TIMESTAMPTZ`・`BOOLEAN`）:

- `backend/tests/conftest.py:155-178`（INBOX_BADGE の SQLite。両方無い）
- `backend/tests/conftest.py:2158-2165`（PG の tenant_001.meta_messages。is_manual が無い）
- `backend/tests/conftest.py:2226-2231`（deleted_at はある。is_manual を足す）
- `backend/tests/test_conversations.py:114`・`test_discord_inbox.py:99`・`test_message_image_send.py:98`・`test_message_send.py:116`・`test_messages.py:115`・`test_outbound_draft_send.py:94`・`test_webhook_instagram.py:94`
- 手の記録の作成で入れる列（company_id・contact_id・occurred_at・recorded_by_user_id・original_language）が無い定義を手の記録の試験で使うなら、その定義にも足す

名簿の種（会話の置き場の値）: `backend/tests/conftest.py:906-908`・`:2211` の `'conversation_logs'` を `'meta_messages'` に、`:645` の既定 `'conversation_logs'` を `'meta_messages'` に（本番の §11 の後の姿にそろえる）。

### 9-2. 直す試験（データの入れ先を meta_messages にするだけ。期待は変えない）

- `backend/tests/test_conv_logs_router.py`・`test_company_conv_logs.py`・`test_conv_logs_fire_translation.py`: 手の記録の入れ先・読み先を meta_messages に。翻訳は `message_id` が `manual_` で始まることを見る
- `backend/tests/test_analytics.py`（conversation_logs が6か所）・`test_lead_conversion_factors.py`（1か所）・`test_lead_regression_generate.py`（3か所）: 会話の種を meta_messages に入れる。**数値の期待は1つも変えない**
- `backend/tests/test_discord_inbox.py`（3か所）: 写しを確かめている所は「conversation_logs に1行も書かれない」に反転
- `backend/tests/test_conv_backbone_ben1b.py`（7か所）: `write_conversation_log` の関数そのものの試験は残す。webhook・dm_writer が写しを呼ぶことを確かめている所があれば「呼ばない」に反転
- `backend/tests/test_lead_merge_pg.py`・`rls_bootstrap.py`・`test_channel_masters_shared_pg.py`・`test_tenant_loop_migration_guard.py`: 変えない（便3 まで conversation_logs の表は残る）

### 9-3. 足す試験（新 `backend/tests/test_conversation_unify_bin1.py`、SQLite）

1. 手の記録を作ると meta_messages に1行（is_manual TRUE・sender_id `manual:user_<id>`・message_id `manual_` で始まる・created_at = occurred_at）、conversation_logs に0行
2. 手の記録が会話の流れの API（`GET /api/v1/leads/{id}/messages`）に出る（K3）
3. 過去の時刻で記録した手の記録が、流れのその時刻の位置に並ぶ。あとで時刻を直すと、直した時刻の位置に並ぶ
4. 消した手の記録が流れに出ない
5. 手の記録が最新の行でも、送信の宛先・画像の送信の宛先・未読に戻す行・24時間の窓・最新の窓口・受信箱の一覧の宛先と未読数が、手の記録の無いときと同じ
6. 自動連携の行の id を手の記録の変更・削除の API に渡すと 404
7. 電話の手の記録（inbound・original_language 'en'）が言語判定に数えられない
8. 本文のラベル付け（priority_scoring）に手の記録が入らない
9. webhook の受信1件・echo 1件・Discord の DM 1件で、conversation_logs に0行（写しが書かれない）。echo でリードが作られない
10. migration の文字の確かめ（ファイルを文字として読む）: `CREATE OR REPLACE VIEW` を含み、`DROP` を含まず、`meta_messages` と `deleted_at IS NULL` を含み、`conversation_logs` を含まない（戻し方のコメント行を除く）。この試験は全社を回す移行を文字として読むので、`backend/tests/test_tenant_loop_migration_guard.py` の `_REVIEWED` に `"test_conversation_unify_bin1.py": ("text_only", "文字として読むだけ", frozenset({"20261108_100000_rebuild_company_stats_on_meta_messages.sql"}))` を足す

## 10. 終わったときの検索（PR の枝で流し、結果を PR 本文に貼る）

```bash
# 写しの呼び出し（0件）
git grep -n 'write_conversation_log' HEAD -- backend/app/routers backend/app/discord_gateway
# アプリの読み書きに残る conversation_logs（leads.py の統合一覧 1件と、conv_log_writer.py の中だけ）
git grep -n 'conversation_logs' HEAD -- backend/app ':!backend/app/services/conv_log_writer.py'
# 消したファイルの名前（0件）
git grep -n 'sa02_recon_monitor\|migrate_sa02_stage2_meta_to_conv_logs\|verify_sa02_stage2_count_check' HEAD -- backend scripts .github
# 手の記録の除外（§4 の9か所が出る）
git grep -n 'is_manual IS NOT TRUE' HEAD -- backend/app
```

2つ目の期待: `backend/app/routers/leads.py` の `_MergeTable("conversation_logs", "tenant")` の1件だけ。ほかに出たら §3〜§5 の漏れ。

## 11. 名簿の値（この PR の外・反映の後に PO が流す）

`docs/handoff/conversation-unification/data-store/` に一式がある（Opus が用意。担当は触らない）。名簿 id 10・11・12 の会話の置き場を meta_messages にする。§5 の成約分析は値の前後で同じ結果になる形にしてあるので、反映と値の変更の順番は結果に効かない。

## 12. 想定される分かれ道（こうなったらこうする）

| 起きたこと | どうする |
|---|---|
| §0 の行が基準と違う | BLOCKED: で差を返す |
| SQLite の試験で `IS NOT TRUE` が通らない | `COALESCE(is_manual, FALSE) = FALSE` に替えてよい（PG と同じ意味）。替えたら §10 の4つ目の検索の語も同じに替え、PR 本文に書く |
| 9-1 の表以外にも meta_messages を自前で作る試験があり、列が無くて落ちる | その定義に列を足すだけにする。期待は変えない |
| 数値の期待（test_analytics・test_lead_conversion_factors・test_lead_regression_generate）が1つでも変わる | 期待を書き換えない。BLOCKED: で差を返す |
| `_create_outbound_lead_for_echo` が使われなくなったと lint が止める | 関数に `# noqa` を付けず、NEEDS_DECISION: で返す |
| migration の `CREATE OR REPLACE VIEW` が試験や CI で「列を変えられない」と落ちる | DROP に替えない。BLOCKED: で生の出力を返す |
| `test_tenant_loop_migration_guard` が落ちる | 9-3 の10の登録を確かめる。直らなければ BLOCKED: |
| `test_celery_beat_registered` が落ちる | `:32` と `:151-157` の両方を消したか確かめる。直らなければ BLOCKED: |
| api-contract-check が赤 | §1 の 10 の命令で作り直したか確かめる。手で openapi.json を直さない。形が変わったなら NEEDS_DECISION: |
| 会話の流れの順番の試験（9-3 の3）で、同じ時刻の行の順が揺れる | 時刻を1秒ずらした種にする（ORDER BY は今の `created_at ASC, id ASC` のまま） |
| §3〜§5 の外で conversation_logs を読む所が見つかった | 足さずに NEEDS_DECISION: で場所を返す |
| 手元で試験を回したくなる | 回さない。CI の結果を読む |

## 13. 触らない

- `conversation_logs` の表・行・既存の migration（便2・便3 の担当）
- `backend/app/routers/leads.py:3014` の `_MergeTable("conversation_logs", "tenant")`（便3 まで残す）
- `backend/app/services/conv_log_writer.py` の中身
- `backend/tests/rls_bootstrap.py`・`backend/tests/test_lead_merge_pg.py`・`backend/tests/test_channel_masters_shared_pg.py`・`backend/tests/test_value_migrations_neutralized.py`
- `public.channel_masters` の行（§11 で PO が流す）
- `.github/workflows/`
- 既読 `leads.py:1207`・訳 `:1412`・添付の取り直し `:1567`・Discord の反応 `reaction_writer.py:115`・`discord_reactions.py:107`（影響なしと確かめ済み）

## 14. 終わりの報告

- `DONE`／`BLOCKED: 理由`／`NEEDS_DECISION: 問い` のどれかで始める
- 停止したとき: その場で手を止め、`BLOCKED:` で始めて、止まった手順・命令・生の出力を返す。自分で回り道を作らない
- PR 番号・HEAD・CI の結果（名前と結論の生の一覧）・§10 の4つの検索の生の出力・消したファイル・変えた試験の一覧・`git diff main...HEAD --name-only` の生の出力
- 推測で埋めない。読めなかった出力は「読めなかった」と書く

## 15. 反映の後（Opus が行う。担当はしない）

- 反映の**前**に、K5 の基準値を読み取り専用の鍵で取って保存する（下の問いの「今の形」）。反映の後に「新しい形」で取り、差 0 を確かめる
  - 成約分析の入力: 会社ごとに、成約・失注のリードの会話の (lead_id, direction, 時刻) の集まり。今の形 = meta（instagram・messenger のリード、created_at）＋ conversation_logs（whatsapp のリード、occurred_at）。新しい形 = meta だけ（3つの窓口のリード、created_at）。2026-11-07 23:50 JST に Opus が下見: 5社とも差 0（001 社 1739 行。`/tmp/CC報告ファイル/conv/card6/q15.txt`）、同じ時刻で向きの違う行の組 0（`q16.txt`。並べ替えで結果が変わらない）
  - 週次の助言: 会社ごとの最終会話日。今の形 = conversation_logs の MAX(occurred_at)（company_id あり）。新しい形 = meta の MAX(COALESCE(occurred_at, created_at))（company_id あり・消した印なし）
  - 会社詳細の会話タブ: 会社ごとの件数と最新時刻（今の形 = conversation_logs、新しい形 = meta）
  - v_company_stats: 5社の全行の conversation_count・last_conversation_at
  - 言語判定: 受信のあるリードごとの（確定か・確定のときの言語）。今の形 = meta ＋ conversation_logs（原文でない窓口を除く）、新しい形 = meta だけ（原文でない窓口を除く）。下見: 会社4 のリード38 だけ生の数が変わり（en 1 → 0）、どちらも未確定で画面は同じ（recon §8-6）
- K2: 反映後 24 時間、conversation_logs に created_at が反映時刻より後の行が 0
- K3: PO が本番の受信箱で電話の会話を1件記録し、その相手の会話の流れに出ることを目視
- smoke の [7e] が PASS（反映の記録で読む）
- §11 の名簿の値を、PO の同意の後に流す

END OF CARD
