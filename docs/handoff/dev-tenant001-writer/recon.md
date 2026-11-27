# recon: 試験用テナント（tenant_001）だけに書き込める AI の道

> 状態: 草案（2026-11-27、Claude Opus）。PO の方向の決定「1」（2026-11-27「テナント001専用の鍵を作る形で進める」）を受けた現在地の調べ。

## 0. 既存 ADR の検索
- `git grep -i "tenant_001" origin/main -- docs/adr`:
  - ADR-1001:136「tenant_004（本番）+ tenant_001（QA）」→ tenant_001 は試験用（QA）として扱われている。
  - ADR-1051:19 画面点検の専用の人は tenant_001 に作った。
  - ADR-1085:16 部屋 A に「自社アプリの tenant_001 だけの利用者」。
- 本番 DB の AI の道: ADR-1024（読むだけの道。`ai_reader`・`ai_ro`・reader 鍵・専用コンテナ・台本・GO 記録の境界）。今回はこの型を書き込みに広げる。
- ADR-SA-18（アプリの最小権限ロール）、ADR-025（手動 DB 書き込みの原則。本番運用フェーズ移行後に効く）、ADR-135/136（危険パスの GO）。

## 1. テナントの一覧（本番、reader 鍵で読んだ。2026-11-27 11:0x JST）
`SELECT * FROM ai_ro.public__tenants`:

| id | 名前 | code |
|---|---|---|
| 1 | テスト株式会社 | test-corp |
| 3 | 権限確認用 | perm-check-zzz |
| 4 | HIGH LIFE JPN | highlife-jpn（本物のお客さま） |
| 5 | テストテナント2 | test-tenant-2 |
| 6 | Sales Anchor App Review | tenant-review（Meta 審査用） |

## 2. tenant_001 スキーマの守り（pg_class・pg_policies）
- 表 112 枚。行の制限（RLS）あり 64 枚（うち FORCE 1 枚）、なし 48 枚。生出力 /tmp/CC報告ファイル/dev001/q1.tsv。
- 方針は全部 `ALL TO public`。条件は `tenant_id = current_setting('app.tenant_id')` か `current_tenant_id()`、子の表は親の表の tenant_id を見る形（18 種類）。生出力 q3.tsv・q4.tsv。
- → 書き込み用のロールが BYPASSRLS を持たない場合、`SET LOCAL app.tenant_id = '1'` が無いと 64 枚は書けない（読み書きとも 0 行）。

## 3. 他のスキーマへ書き込む道
- 外部キー: tenant_001 → public が 31 本、tenant_001 → tenant_001 が 72 本。他スキーマ → tenant_001 は 0 本（q6.tsv・q7.tsv）。
- 利用者が作った引き金（trigger）30 本（q5.tsv）。29 本は同じ表の中だけ（updated_at の付け直し・支払い記録の消し止め）。
- **1 本だけ public に書く**: `tenant_001.tenant_meta_config` の `trg_sync_meta_page_routing` → 関数 `tenant_001.sync_meta_page_routing()` は SECURITY DEFINER（持ち主の権限で動く）で、`public.meta_page_routing` に INSERT／UPDATE／DELETE する（q8.tsv）。これは Facebook・Instagram のページの知らせを、どのテナントに届けるかの表。書き込み用のロールに GRANT が無くても、この関数は持ち主の権限で public を書き換える。
- PostgreSQL 公式（ddl-rowsecurity、Context7 /websites/postgresql）: 外部キーの確かめは行の制限を受けない。参照先の public の表に SELECT 権限が要るかは公式の文で確かめられていない（未確認 → 試験 K で測る）。

## 4. tenant 1 が外のサービスにつながっているもの（reader 鍵、件数）
| つながり | 件数 | 中身 |
|---|---|---|
| Discord | 2 | 「customer」1 件（guild …397393）、「own」（自社のスタッフ用）1 件（guild …185749） |
| Discord の受付 | 1 | |
| Google カレンダー | 1 | |
| Google Drive | 1 | |
| PayPal | 1 | 本番か試験用（sandbox）かは未確認 |
| 配送会社の鍵 | 0 | |

## 5. 定期の作業（celery beat）で外に影響が出うるもの
`backend/app/celery_app.py`（origin/main）の 34 本のうち:
- `discord_own_staff_sync.sync_all_own_servers`（5 分ごと）: 「own」の Discord を登録した全テナントのスタッフのロールを点検する（`backend/app/tasks/discord_own_staff_sync.py:1-4`）。tenant 1 は「own」を持つ → tenant_001 のスタッフの行を書き換えると、本物の Discord サーバーのロールが変わる可能性がある。サーバーの中の人が試験用かは未確認。
- `google_calendar_sync.sync_google_calendar_all`（15 分ごと）: Google → アプリの取り込み（`backend/app/tasks/google_calendar_sync.py:1-5`）。アプリ → Google の書き出しは画面・API の操作からで、DB を直接書いても動かない（未確認: 書き出しの道の全走査はまだ）。
- `tcg_mirror.run_tcg_mirror_write`: 決まったスプレッドシートへの書き出し。テナント単位かは未確認。
- `dashboard.refresh_all_tenant_kpis`・`tenant_isolation_daily_check`: 読むだけと見られるが、中身は未確認。

## 6. Mac 側の見張り
- 本番 DB への書き込みの命令は、命令の文字で止まる（`~/.claude/scripts/agent-danger-hook.sh` の psql-write-guard と、DROP TABLE・DELETE FROM 等の語）。11/13〜11/27 に 36 回（その多くは検索の文字）。
- 読むだけの道（ADR-1024）は K17 でフックの免除なしで動いた。書き込みの道は SQL の本文に INSERT・DELETE 等が入るため、免除が要る見込み（未確認）。免除の追加は PO 本人が行う（AI は自分の見張りをゆるめない）。

## 7. 未確認（まとめ）
- U1 → 解決（PO 2026-11-27 選択肢「1」: 4 つとも試験用。中の人も試験用か PO だけ）。外へ送られても困らない。
- U2 参照先の public の表に SELECT 権限が要るか（試験で測る）。
- U3 DB を直接書いたときに外へ送る作業の全一覧（担当に全走査を頼む）。
- U4 書き込みの道にフックの免除が要るか（試験で測る）。

## 8. 第1回審査のあとの追加の読み取り（reader 鍵、2026-11-27 12:21 JST）
使った SQL（L7。件数を後から確かめられるように書く）:
- 表の数: `SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='tenant_001' AND c.relkind IN ('r','p')` → 112
- スキーマの権限: `SELECT nspname, nspacl::text FROM pg_namespace WHERE nspname IN ('public','tenant_001')` → public は `=U/pg_database_owner`（PUBLIC は USAGE だけ）、tenant_001 は `jarvis=UC`・`salesanchor_app=U`・`ai_unmask_owner=U`
- DB の権限: `SELECT datname, datacl::text FROM pg_database WHERE datname = current_database()` → `=Tc/jarvis`（PUBLIC は TEMP・CONNECT だけ）
- SECURITY DEFINER の関数: `pg_proc` を `prosecdef` で絞る → 6 個（`ops_case.unmask_fetch` と 5 テナントの `sync_meta_page_routing`）
- 秘密の列（ADR-1024 の型）: `pg_attribute` を `attname ~* '^password|_encrypted$|_secret|_token|hash|^secret|^api_key|private_key|credential|account_number|^iban$'` で絞る → 7 表 9 列（design §3-2）。`information_schema.columns` では 0 行（他人の表の列が見えないため）
- 既存の試験用ロール: `qa_tenant006_rw`（LOGIN・NOBYPASSRLS・接続上限なし。migration に無い）
- 表 112・RLS 64・外部キー 31/72・引き金 30 の元: `pg_class.relrowsecurity`、`pg_constraint`（contype='f'）、`pg_trigger`（NOT tgisinternal）を tenant_001 で数えた

## 9. 第2回審査のあとの追加の読み取り（reader 鍵、2026-11-27 12:30 JST）
- 規則 B の 6 表の秘密でない列の数（`pg_attribute` を表ごとに数え、`lower(attname)` が拒否の型に当たらない列）: bots 13・discord_channel_webhooks 5・staff 18・tcg_distribution_targets 10・tenant_invoice_payment_bank 11・tenant_invoice_payment_wise 12（合計 69）
- 秘密の列が「空を許さず既定値なし」（`attnotnull` true かつ `atthasdef` false）: bots・discord_channel_webhooks・tenant_invoice_payment_bank の 3 表。tcg_distribution_targets は既定値あり。staff・tenant_invoice_payment_wise は空を許す
- tenant_001 の連番（relkind 'S'）: 74
- `tenant_meta_config` の外部キー（`pg_constraint` を oid で結んで読んだ）: 1 本だけ。`fk_tenant_meta_config_connected_by_staff_id_user`（tenant_meta_config → public.users、消したとき空にする）。tenant_meta_config を参照先にする外部キーは 0 本。→ tenant_001 の別の表を消した連鎖で、tenant_meta_config の引き金が動く道は無い
- `'tenant_001.tenant_meta_config'::regclass` を reader 鍵で使うと権限エラー（InsufficientPrivilege）。ai_reader は tenant_001 の USAGE を持たないため。→ 権限の数えは oid で渡す
