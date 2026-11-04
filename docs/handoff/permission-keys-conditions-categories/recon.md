# recon: 状態マスタ・商品カテゴリの権限キーが権限の一覧に無い

調査日: 2026-11-04（JST）。根拠は origin/main `cb9525b9d`（2026-11-04 09:13 JST）と、本番 DB の読み取り専用の道（ai_ro）。

## 0. きっかけ
ADR-1054（全画面を押した瞬間に開く速さにする）の点検用の役割に、3 画面の閲覧権限を足そうとした（PO「1」）。そのうち 2 画面（状態マスタ `/management-center/conditions`・商品カテゴリ `/management-center/product-categories`）は、コードが求める権限キーが本番の権限の一覧（`public.permissions`）に無く、誰にも付けられなかった。PO「1」（2 つの鍵を権限の一覧に足す設計を作る）で本調査と設計に進む。

## 1. 既存 ADR・文書の検索
- `git grep -i` で `conditions.view|product_categories.view|work_items.view|companies.view` を docs・migrations から検索 → 権限キーとしての言及は `docs/handoff/conditions-tenant-page/design.md:39`（「conditions.view 権限がないテナントはルーティング時にリダイレクト」）と `docs/handoff/s6-get-access-audit/recon.md:42`（companies.view の endpoint は frontend から呼ばれていない）だけ。キーを権限の一覧へ足す計画はどこにも無い。
- ADR-1007（`docs/adr/ADR-1007-migration-structure-only-run-once.md`）
  - :36 値の変更は「1回だけのデータの変更：PO の合意、DRY-RUN → COMMIT、docs/handoff/<topic>/ に SQL と記録を残す」。
  - :48-51 所有者は public.permissions の全部、管理者は system.manage を除いた全部を、コードで計算して持つ。
  - :70 新しい権限が所有者・管理者に届くまで最大 300 秒（cache.py の TTL）。
  - :73 「権限の一覧の正本が DB だけで、コードの中に写しが複数ある… 別の ADR で扱う」。その別の ADR はまだ無い。
- `docs/handoff/migration-hygiene/recon.md` §5.4
  - public.permissions にアプリの書き手は無い。
  - migration-guard の保護表に permissions が入った 2026-09-18 以降、キーの追加は無い。「現行ルールでの追加経路の前例は無い」。
- 値を 1 回だけ本番に入れた前例: `docs/handoff/product-packaging/data-change-1/README.md`（ADR-1028 便2）。
  - 手順: 事前確認（読み取り鍵）→ DRY-RUN（BEGIN…ROLLBACK・件数ガード）→ 本実行 → 事後確認。
  - 書き込みは Opus が、PO 本人の使い捨て許可 `permit-danger.sh "psql write"` のもとで流す（:12-35）。
- 関連する active-work.d: release-owner-admin-computed-permissions（DONE）。重なる作業は無い。

## 2. 権限判定の経路（実物）
- `backend/app/auth/dependencies.py:646-672` require_permission
  - 渡したキーのどれか 1 つを持てば通す（`required & user_perms`、:666）。
  - 持っていなければ 403。
- `backend/app/auth/dependencies.py` load_user_permissions
  - user_roles → role_permissions → public.permissions を JOIN する。
  - 所有者・管理者は `SELECT key FROM public.permissions` から計算する（compute_permission_keys）。
  - 結論: **public.permissions に無いキーは、所有者を含めて誰も持てない**。
- `migrations/002_add_permissions_master.sql:9-16`
  - public.permissions の列: id SERIAL、key VARCHAR(100) UNIQUE、resource、action、description NOT NULL、category NOT NULL。
  - migrations/018 で permission_group・display_name_jp・display_name_en・display_order を追加。
- `migrations/20261015_130000_add_permissions_rls.sql`
  - 読むのは誰でもよい。
  - 書くのは `app.is_operator = 'true'` のときだけ（FORCE RLS）。
- 権限の画面 `frontend/src/pages/roles/RolesPage.tsx`
  - :145-146 category ごとにまとめる。
  - :384 見出しに category の文字列をそのまま出す。
  - :416 各権限は description を出す。
  - CATEGORY_META（:57-66）に無い category は既定アイコンで順番 100。

## 3. コードが求めるのに一覧に無いキー（全 11 件）
コードの require_permission のキーは 97 種類、本番の一覧は 123 件。差は次の 11 件（`grep -n require_permission` の結果。行は cb9525b9d）。

| キー | 使う場所 | 画面側 |
|---|---|---|
| conditions.view | backend/app/routers/conditions.py:130（一覧）、:186（1件）、:371（CSV 出力）、:414（取り込みの下見）、:452（取り込みの確定）、:522（別名の一覧） | ManagementCenterPage.tsx:53（メニューの表示）、ConditionsPage.tsx:369、ConditionImportPage.tsx:130（取り込みボタン） |
| conditions.create | conditions.py:210 | ConditionsPage.tsx:377 |
| conditions.update | conditions.py:273、:551 | ConditionsPage.tsx:281、:469、:568 |
| conditions.delete | conditions.py:327、:595 | ConditionsPage.tsx:255、:428、:536 |
| product_categories.view | backend/app/routers/product_categories.py:95、:155 | ManagementCenterPage.tsx:54 |
| product_categories.edit | product_categories.py:130、:191、:231、:295 | ProductCategoriesPage.tsx:182、:246、:255、:354、ProductCategoriesImportPage.tsx:136 |
| product_categories.delete | product_categories.py:329 | ProductCategoriesPage.tsx:187 |
| work_items.view | conditions.py:163（`/conditions/catalog`。呼ぶのは ConditionsPage.tsx:150 だけ） | — |
| companies.view | backend/app/routers/duplicates.py:69 | frontend からの呼び出しなし |
| customers.edit | backend/app/routers/contacts.py:659 | — |
| leads.edit | backend/app/routers/discord_channel_invite.py:63、backend/app/routers/discord_role_resync.py:43 | — |

- 入った時期（`git log -S`）
  - conditions.* は 2026-09-20、ec86fcf02・327cfe9de・ad6881f58・fa25fbec9。
  - product_categories.* は 2026-09-20〜21、ad6881f58・47e2a0d93。
  - leads.edit は 2026-06-02、ed7b6af8b・abecd7962。
  - customers.edit は 2026-06-12、786b9f25f。
  - どの変更も、キーを一覧へ足す手順を持たない。
  - 9/18 以降は migration で足せなくなっていた（§1）。
- 一覧に同じ役目の別キーがある: customers.update（id 10）、leads.update（id 14）、customers.view（id 8）。companies.* と work_items.* は一覧に 1 件も無い。
- 一覧の action の数（本番）: view 25・access 19・create 14・update 13・delete 11・edit 9 ほか。edit は既に使われている形。

## 4. 見つけた別の穴（書き込みが閲覧キーで通る）
- `backend/app/routers/conditions.py:450-515` 取り込みの確定 `/conditions/import/commit`
  - public.conditions に INSERT と UPDATE をする（:476-503。UPDATE は :481-490 付近、INSERT は :492-502 付近）。
  - それなのに求めるキーは conditions.view（:452）。下見（:414）も同じ。
  - 画面側も取り込みボタンを conditions.view で出す（ConditionImportPage.tsx:130）。
- 今は conditions.view が誰にも付かないため、実害は出ていない。
- conditions.view を一覧に足すと、閲覧だけの役割（点検用など）が CSV で状態マスタを書き換えられるようになる。足す前に塞ぐ必要がある。
- 商品カテゴリの取り込みは product_categories.edit で守られている（:191、:231）。同じ穴は無い。

## 5. データの持ち主（どの表を書くか）
- 状態マスタ: public.conditions。`tenant_id = :tenant_id` の行だけを読み書きする（conditions.py:1-10、:476-503）。
- 商品カテゴリ: public.tcg_product_categories。テナントの行だけを扱い、共用の行（tenant_id IS NULL）は読まない（product_categories.py:1-5、:107、:166）。
- `/conditions/catalog` は共用の行（tenant_id IS NULL）を読むだけ（conditions.py:160-180）。

## 6. 本番の状態（読み取りの道・2026-11-04 09:10〜09:13 JST）
- public.permissions は 123 件。conditions.*・product_categories.*・work_items.*・companies.* の行は 0 件。
- テナントは 5 社。1 テスト株式会社（開発用・PO 指定の試し先）、3 権限確認用、4 HIGH LIFE JPN、5 テストテナント2、6 Sales Anchor App Review。
  - キーを足すと、5 社すべての所有者・管理者に、状態マスタと商品カテゴリのメニューが出る（計算で届くため。§2）。
- テナント 1 の役割「点検用（見るだけ）」（id 2611）は 45 権限。うち書き込みのキーが 20 ある。これは別件として PO に聞く予定。
- 既存の descriptionの書き方の例: products.view「商品一覧の閲覧」、goals.edit「目標を作成・編集する」。

## 7. 見張りの置き場所の候補（実物）
- `backend/app/metrics.py:1-140`
  - /metrics を読むたびに値を計算して Gauge に入れる形が既にある（_update_viewer_inventory_gauges 等）。
  - backend の worker は 1 つ（backend/Dockerfile:37-39）。
- `monitoring/prometheus/alert_rules.yml:219-241` は ViewerInventoryStale の例。
  - 試験は monitoring/prometheus/tests/alert_rules_test.yml にある。
  - 通知は alertmanager の既定の宛先 discord-server-alerts に届く。
- DB の接続: `backend/app/database.py:36` AsyncSessionLocal。

## 8. 未確認
- 本番で誰かが状態マスタ・商品カテゴリの API を叩いて 403 になったか。
  - メニューが出ないため、直接 URL を開いた場合だけ起きる。
  - Prometheus の http_requests_total{status="403"} を見れば分かるが、まだ見ていない。
  - 設計の判断はこれに依存しない。
- companies.view・customers.edit・leads.edit を既存キーへ付け替えるべきかどうか。誰が使えるようになるかが変わるため、PO の判断が要る。本設計の範囲外とする。
