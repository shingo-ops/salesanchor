# security-recon: 外部会社ユーザーを tenant_002 に入れて在庫表だけ見せる案の調査

> この文書は何か：お客さんをアプリの利用者として入れた場合に、在庫表以外も見えてしまうかを調べた記録。

- 親（設計仕様書）: [docs/specs/inventory-management/inventory-viewer/README.md](../../specs/inventory-management/inventory-viewer/README.md)
- 設計: [design.md](./design.md) ／ ADR: ADR-1019（docs/adr/ADR-1019-inventory-viewer-separate-accounts.md）

基準: origin/main = e69ed67（読み取りのみ。本番・DB・secrets 未接触。値は一切記載しない）。
証拠: /tmp/CC報告ファイル/viewer_security/ （routes_matrix.tsv, routes_raw.tsv, decorators_grep.txt, login_only_body_scan.txt, public_tables_rls.tsv, tenant_py_tables.txt）
以下パスは特記なければ backend/ 配下。

## 1. 入口の全件数（【事実】）
- app.routes=618（APIRoute 614 + 組込み4: /openapi.json, /docs, /docs/oauth2-redirect, /redoc）
- decorator grep 628 − docstring例 4 − 未登録router 10（routers/badges.py 5, routers/buddy.py 5。main.py未登録で到達不能）= 614 で一致
- 種別: permission 299 / super_admin 238 / login_only 39 / own_token 20 / tenant_admin 10 / none 8

## 2. 閲覧者（tenant_002・products.view のみ）が呼べる入口
- (a) 認証なし = 28（none 8 + own_token 20）＋組込み /openapi.json
- (b) ログインだけ = 36
- (c) products.view = 10（decorator 8 + inline判定 2）
- 合計 74（+ /openapi.json）。残り 540 は 403 等で呼べない。

### (a) 認証なし 28
| method | path | file:line | 種別 | own_token |
|---|---|---|---|---|
| GET | /metrics | backend/app/metrics.py:58 | none |  |
| GET | /api/health | backend/app/routers/health.py:16 | none |  |
| POST | /api/v1/auth/logout | backend/app/routers/auth.py:150 | own_token | Bearer(自前検証) |
| POST | /api/v1/auth/login | backend/app/routers/auth.py:231 | none |  |
| POST | /api/v1/auth/refresh | backend/app/routers/auth.py:308 | none |  |
| POST | /api/v1/auth/password-reset/request | backend/app/routers/auth.py:370 | none |  |
| POST | /api/v1/auth/password-reset/confirm | backend/app/routers/auth.py:412 | none |  |
| GET | /api/v1/webhook/messenger | backend/app/routers/webhook.py:241 | own_token | Meta署名/verify_token |
| POST | /api/v1/webhook/messenger | backend/app/routers/webhook.py:265 | own_token | Meta署名/verify_token |
| POST | /api/v1/meta/data-deletion | backend/app/routers/meta.py:146 | own_token | Meta signed_request |
| GET | /api/v1/meta/deletion-status | backend/app/routers/meta.py:225 | own_token | confirmation_code |
| POST | /api/v1/contact | backend/app/routers/contact.py:72 | none |  |
| GET | /api/v1/public/register | backend/app/routers/registration_tokens.py:164 | own_token | 登録署名トークン |
| POST | /api/v1/public/register | backend/app/routers/registration_tokens.py:210 | own_token | 登録署名トークン |
| POST | /api/v1/public/register/address | backend/app/routers/registration_tokens.py:363 | own_token | 登録署名トークン |
| POST | /api/v1/public/register/change-billing | backend/app/routers/registration_tokens.py:452 | own_token | 登録署名トークン |
| GET | /api/public/staff-avatars/{token}.webp | backend/app/routers/public_staff_avatars.py:21 | own_token | URL内トークン |
| GET | /api/v1/discord/oauth/callback | backend/app/routers/discord_oauth.py:138 | own_token | OAuth state |
| GET | /api/v1/integrations/google-drive/connect/callback | backend/app/routers/integrations.py:104 | own_token | OAuth state |
| GET | /api/v1/integrations/paypal/return | backend/app/routers/integrations.py:757 | own_token | PayPalトークン |
| GET | /api/v1/integrations/paypal/cancel | backend/app/routers/integrations.py:819 | own_token | (要確認) |
| POST | /api/v1/integrations/paypal/webhook | backend/app/routers/integrations.py:885 | own_token | PayPal署名 |
| GET | /api/v1/google-calendar/connect/callback | backend/app/routers/google_calendar.py:88 | own_token | OAuth state |
| POST | /api/v1/google-calendar/webhook | backend/app/routers/google_calendar.py:353 | own_token | Googleチャネルtoken |
| POST | /api/v1/tcg/line-devices/start | backend/app/routers/line_import_devices.py:32 | own_token | 端末ハッシュ(承認待ち発行) |
| GET | /api/v1/tcg/line-devices/status | backend/app/routers/line_import_devices.py:39 | own_token | 端末トークン |
| POST | /api/v1/tcg/line-devices/import | backend/app/routers/line_import_devices.py:68 | own_token | 端末トークン |
| GET | / | backend/app/main.py:792 | none |  |

### (b) ログインだけ 36
| method | path | file:line | tenant_ctx |
|---|---|---|---|
| GET | /api/v1/{company_id}/conv-logs | backend/app/routers/companies.py:1068 | Y |
| POST | /api/v1/registration-tokens | backend/app/routers/registration_tokens.py:67 | Y |
| GET | /api/v1/countries | backend/app/routers/countries.py:14 | Y |
| GET | /api/v1/permissions | backend/app/routers/roles.py:114 | Y |
| GET | /api/v1/me/permissions | backend/app/routers/roles.py:132 | Y |
| GET | /api/v1/integrations/google-drive/status | backend/app/routers/integrations.py:223 | Y |
| POST | /api/v1/integrations/google-drive/test-upload | backend/app/routers/integrations.py:242 | Y |
| GET | /api/v1/staff/me | backend/app/routers/staff.py:246 | Y |
| PATCH | /api/v1/staff/me/locale | backend/app/routers/staff.py:294 | Y |
| PATCH | /api/v1/staff/me/theme | backend/app/routers/staff.py:315 | Y |
| PATCH | /api/v1/staff/me/profile | backend/app/routers/staff.py:343 | Y |
| POST | /api/v1/staff/me/avatar | backend/app/routers/staff.py:446 | Y |
| DELETE | /api/v1/staff/me/avatar | backend/app/routers/staff.py:499 | Y |
| GET | /api/v1/me/inventory-filters | backend/app/routers/me_inventory_filters.py:85 | N |
| PATCH | /api/v1/me/inventory-filters | backend/app/routers/me_inventory_filters.py:123 | N |
| GET | /api/v1/fx-rates/{currency} | backend/app/routers/fx_rate_admin.py:61 | N |
| GET | /api/v1/google-calendar/status | backend/app/routers/google_calendar.py:209 | Y |
| GET | /api/v1/google-calendar/events | backend/app/routers/google_calendar.py:243 | Y |
| POST | /api/v1/google-calendar/events | backend/app/routers/google_calendar.py:269 | Y |
| PATCH | /api/v1/google-calendar/events/{event_id} | backend/app/routers/google_calendar.py:296 | Y |
| DELETE | /api/v1/google-calendar/events/{event_id} | backend/app/routers/google_calendar.py:328 | Y |
| GET | /api/v1/calendar/events | backend/app/routers/calendar.py:130 | Y |
| GET | /api/v1/calendar/owners | backend/app/routers/calendar.py:156 | Y |
| POST | /api/v1/calendar/events | backend/app/routers/calendar.py:336 | Y |
| PATCH | /api/v1/calendar/events/{event_id} | backend/app/routers/calendar.py:370 | Y |
| DELETE | /api/v1/calendar/events/{event_id} | backend/app/routers/calendar.py:421 | Y |
| GET | /api/v1/calendar/sync-mode | backend/app/routers/calendar.py:448 | Y |
| GET | /api/v1/channel-masters | backend/app/routers/conv_logs.py:189 | Y |
| POST | /api/v1/leads/{lead_id}/conv-logs | backend/app/routers/conv_logs.py:225 | Y |
| GET | /api/v1/leads/{lead_id}/conv-logs | backend/app/routers/conv_logs.py:337 | Y |
| PATCH | /api/v1/leads/{lead_id}/conv-logs/{log_id} | backend/app/routers/conv_logs.py:381 | Y |
| DELETE | /api/v1/leads/{lead_id}/conv-logs/{log_id} | backend/app/routers/conv_logs.py:444 | Y |
| POST | /api/v1/admin/channel-masters | backend/app/routers/conv_logs.py:492 | Y |
| DELETE | /api/v1/admin/channel-masters/{master_id} | backend/app/routers/conv_logs.py:526 | Y |
| GET | /api/v1/buyback-prices | backend/app/routers/buyback_prices.py:154 | Y |
| GET | /api/v1/buyback-prices/{shop_product_id}/history | backend/app/routers/buyback_prices.py:744 | Y |

### (c) products.view 10
| method | path | file:line | permissions |
|---|---|---|---|
| GET | /api/v1/own-inventory | backend/app/routers/own_inventory.py:59 | products.view |
| GET | /api/v1/own-inventory/{own_inventory_id} | backend/app/routers/own_inventory.py:145 | products.view |
| GET | /api/v1/products | backend/app/routers/products.py:148 | products.view |
| GET | /api/v1/products/tcg-types | backend/app/routers/products.py:257 | products.view |
| GET | /api/v1/products/attribute-options | backend/app/routers/products.py:288 | products.view |
| GET | /api/v1/products/{product_id} | backend/app/routers/products.py:334 | products.view |
| GET | /api/v1/products/{product_id}/check-inventory | backend/app/routers/products.py:687 | products.view |
| GET | /api/v1/inventory/search | backend/app/routers/inventory_search.py:68 | products.view|inventory.visibility.* (inline) |
| GET | /api/v1/inventory/aggregated | backend/app/routers/inventory_aggregated.py:43 | products.view|inventory.visibility.* (inline) |
| GET | /api/v1/inventory | backend/app/routers/inventory_offers.py:282 | products.view |

### 秘密・他社情報が見える入口（【事実】）
- 仕入元名・仕入元別単価・数量: GET /api/v1/inventory (routers/inventory_offers.py:282; InventoryRow に supplier_id/supplier_name/unit_price/quantity :137-168、suppliers facet :371-385)。GET /inventory/search (routers/inventory_search.py:68; services/inventory_search.py:471-472, 369-370, mask_stock=False「全テナント共通・マスク撤廃」)。GET /inventory/aggregated (routers/inventory_aggregated.py:43; supplier_name は含まず price/quantity)。いずれも public 表（RLS無し・全テナント共通）。
- 商品マスタの unit_price/notes/supplier_default_id/moq/hs_code: schemas/product.py:138- （GET products 系 routers/products.py:148,257,288,334,687）
- 買取価格: GET /api/v1/buyback-prices (routers/buyback_prices.py:154)、/buyback-prices/{id}/history (:744)。権限チェック無し・ログインのみ。public.buyback_* は RLS無し・テナント絞り無し。
- 同テナント他社の名前等: GET /api/v1/calendar/events (routers/calendar.py:130 → services/calendar_service.py:84-151)。type未指定だと同テナント全員の personal イベントが owner_name/created_by_name 付きで返る。POST/PATCH/DELETE (calendar.py:336,370,421) も login のみ。
- 会話本文: GET /leads/{lead_id}/conv-logs (routers/conv_logs.py:337)、GET /api/v1/{company_id}/conv-logs (routers/companies.py:1068) は権限チェック無し。
- 権限名と実態の乖離: POST/DELETE /admin/channel-masters (conv_logs.py:492,526)、POST /registration-tokens (registration_tokens.py:67) がログインだけで実行可。google-calendar events CRUD (google_calendar.py:243-328)、integrations google-drive test-upload (integrations.py:242) もログインのみ。
- 他テナントデータ: テナント絞りの無い public 共通データ（/inventory系、buyback、countries、permissions一覧 roles.py:114）。ユーザー一覧系は staff.view 等が必要で閲覧者は 403。
- 非表示設定 (me_inventory_filters.py:85 hide_supplier_ids 等) は利用者指定のフィルタで、サーバー強制のマスクではない。

## 3. テナントの壁
【事実】
- auth/dependencies.py:242 get_current_tenant: DB の user.tenant_id から `tenant_{id:03d}` を作り :280 SET search_path={schema}, public、:283 SET app.tenant_id、:287 app.is_operator=''。get_db が finally で解除 (database.py:46-61)。アプリDB接続は NOBYPASSRLS ロール（dependencies.py コメント）。スキーマ存在の確認は無い。get_current_tenant を使わない login_only 系は search_path 未設定。
- RLS 付き public 表は5つ: products (migrations/20260626_130000_force_rls_public_products.sql:5-14; SELECT は tenant_id IS NULL OR 自テナント)、app_fx_rates、app_fx_rate_history、tenant_features、translation_glossary。
- `public.` 明示 CREATE TABLE 88 表中 RLS 無しは 83（public_tables_rls.tsv）: analysis_results, extraction_items/jobs, source_messages(LINE原文), suppliers, supplier_channels, supplier_aliases, inventory, inventory_movements, buyback_*, audit_log, auth_events, auth_refresh_tokens, password_reset_tokens, webauthn_credentials, registration_tokens, tenant_discord_config, meta_page_routing, llm_usage_events, line_import_devices, user_inventory_filters, permissions, countries ほか。
- tenantスキーマ側 (backend/app/services/tenant.py) 41表中36表が RLS（policy: tenant_id = current_setting('app.tenant_id') tenant.py:1240-1248）。無し: close_reasons, deal_close_reasons, goals, lead_channels, tenant_profile。
- 共通 products 行 (tenant_id IS NULL) は全テナントに見える。配信行(/inventoryの元)は pipeline 表で全テナント同一内容。
【推測】tenant_002 のスキーマが無い場合 search_path が public に落ち、public にも products/suppliers 同名表があるため意図しない表を読む恐れ（未検証）。

## 4. 権限を偽れないか
【事実】
- 権限はサーバーが user_roles→role_permissions→public.permissions を引いて判定 (auth/dependencies.py:540-578, Redis 5分キャッシュ)。require_permission は「いずれか1つ」(:598-622)。
- JWT claims は iss/sub/email/jti/iat/exp のみで role/tenant を載せない (services/self_tokens.py:86-98)。検証は DB の is_active/email一致/password_changed_at (dependencies.py:86-113)。Firebase 経路は tenant_id クレームを DB と照合し不一致は 403 (:229-231)。→ トークンの書換えによる権限偽装の経路は見つからない。
- テナント切替ヘッダー無し（X-Tenant 系 grep 0件）。tenant_id をパス/ボディで受けるのは super-admin 系のみ。
- super admin は public.users.is_super_admin のみで判定 (require_super_admin :491-519)。
- 注意点: POST /auth/register (routers/auth.py:38, super admin専用) は作成時に既定ロール "CS" を自動付与 (auth.py:115-135, backend/app/services/tenant.py:125-146, :189)。CS は customers/leads/deals/orders/quotes/invoices/shipping/reports/dashboard の view 等を含む。閲覧専用にするには作成後に CS を外し products.view のみのロールへ付け替えが必須（初期値が開く側）。権限キャッシュ5分のため変更反映に遅延。
- 気になる点: スモーク用サービストークンのバイパス (dependencies.py:136-155、環境変数設定時のみ有効)。X-Forwarded-For をそのまま信用して IP 決定 (dependencies.py:67-75, rate_limit.py:54, session_guard.py:59, audit.py:66)。rate_limit は JWT を署名検証せずバケットキーに使用 (rate_limit.py:39-)。
- 「全エンドポイントに権限必須」を強制する CI テストは見つからない。

## 5. 画面
【事実】frontend/src/App.tsx: ProtectedRoute は認証のみ (components/ProtectedRoute.tsx)、ルートに権限ガード無し。/crm, /orders, /quotes, /suppliers, /staff, /roles 等は URL直打ちで画面は開く（一部ページ内で403表示）。メニューは DesktopShell.tsx / MobileShell.tsx で hasPermission により出し分けるが、/schedule は常時表示 (DesktopShell.tsx:235-242)。トップ "/" は DashboardPage。画面の閉鎖は見た目のみで、防御はサーバー側 (上記74入口)。

## 6. 別案比較
| 観点 | (A) tenant_002 のアプリユーザー | (B) 閲覧専用アカウント＋閲覧ページ1つ＋専用API1本 |
|---|---|---|
| 呼べる入口 | 74 (+/openapi.json)【事実】 | 【推測】閲覧ページ用API1本＋認証系(login/logout等)。件数は設計依存 |
| 将来API追加時 | get_current_user だけ付けた API が全ログイン者に開く「デフォルト開放」構造。実例 login_only 39件【事実】 | 既存routerを通さず allowlist 方式の別dependencyにすれば既定で到達不能【推測】 |
| 社間分離 | 同テナントに複数社を入れると分離なし (calendar, conv-logs)【事実】 | 専用APIで絞れば分離可能【推測】 |
| 運用 | CS既定ロールの付け替え必要、キャッシュ5分【事実】 | 新認証機構の実装リスク・ADR要【推測】 |
注意: (A)(B) いずれも在庫データ自体 (仕入元名・単価) は public 共通で、見せる範囲は API 側で決める必要がある【事実】。

## 未確認
1. 本番に tenant_002 のスキーマ/tenants行/users が現存するか（本番未接触）
2. tenant_002 に CRM データ (leads/conv-logs/calendar) があるか
3. /openapi.json が本番で外部から取得できるか（nginxに遮断記述なし。docs_url は本番 None main.py:195）
4. public.users/tenants など無修飾 CREATE の public 表の RLS 状態、DB GRANT 範囲
5. GAS 在庫一覧が仕入元名・単価を出しているか（アプリ /inventory は出す）
6. 本番 SMTP 設定
7. SMOKE_SERVICE_TOKEN の本番設定有無
8. nginx の X-Forwarded-For 上書き挙動
9. 配信行が参照する public.products の tenant_id 分布
10. tenant_002 の既定ロール seed 状況
