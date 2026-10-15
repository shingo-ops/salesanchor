<!-- GAS のコードは repo 外（~/tcg-viewer-1hc-release 等）。そのパスにはバッククォートを付けない。守り手: 人手で守る -->
# recon — 在庫一覧 GAS をアプリと同じ鮮度・1秒表示にするための材料集め

> この文書は何か：今の GAS 在庫一覧がなぜ遅いか、どこから在庫を取っているかを調べた記録。

- 親（設計仕様書）: [docs/specs/inventory-management/inventory-viewer/README.md](../../specs/inventory-management/inventory-viewer/README.md)
- 設計: [design.md](./design.md) ／ ADR: ADR-1019（docs/adr/ADR-1019-inventory-viewer-separate-accounts.md）
- 基準 SHA: 計測時（2026-10-14）の SHA は記録していない。設計で引く行番号は、2026-10-15 に origin/main 65ed8cd8b で再照合した（design.md「現在地」）。

**仕事名**: gas-viewer-fresh-fast  
**日付**: 2026-10-14  
**対象ADR**: ADR-1014（配信行の定義）、ADR-154  
**担当**: 調査（読み取りと計測のみ。製品コード・GAS・本番は未変更）

生の出力: /tmp/CC報告ファイル/gas_fast_recon/（breakdown_out.json, clean2_out.txt, clean3_out.txt, render_prof_out.txt, curl_html.txt, urlfetch.txt ほか）

---

## 1. GAS のコードの在りか

【事実】
- 本番 GAS のソースは repo の外。作業フォルダ ~/tcg-viewer-1hc-release/（Code.js, index.html, appsscript.json, .clasp.json）。テスト版は ~/tcg-viewer-1tb-head/（コード.js）。正本は別 repo shingo-ops/tcg-client-viewer（memory reference_tcg_client_viewer.md）。repo 内に在庫一覧 GAS 本体は無い（.gs は `docs/feedback_form_to_github.gs` のみ）。
- デプロイは CI 経由ではない。PO が `!` で push → create-version → redeploy（memory 同ファイル「反映手順」。`.github/` に clasp の記述なし＝`git grep -i clasp -- .github` 0件）。手順書 `docs/handoff/dist-deploy-guard/gas-deploy-runbook.md:25-40`（版14/20 以降は未反映）。
- バインド先シートを SpreadsheetApp.getActiveSpreadsheet() で読む（~/tcg-viewer-1hc-release/Code.js:55）。
- appsscript.json: executeAs=USER_DEPLOYING、access=ANYONE_ANONYMOUS（~/tcg-viewer-1hc-release/appsscript.json）。

呼び出しの流れ【事実】
1. doGet が `createTemplateFromFile('index').evaluate()` を返す（Code.js:35-36）。
2. index.html の DOMContentLoaded で `loadData(false)`（index.html:996-997）。
3. loadData が `google.script.run...getInventoryData()` を **1回だけ**呼ぶ（index.html:1139-1148）。初期表示の google.script.run は1回。「更新」ボタンも同じ関数（index.html:857）。
4. getInventoryData は `getDataRange().getValues()`（Code.js:62）で全セルを読み、13列の許可リストで絞って返す。
5. onDataLoaded → Sold out 除外、検索文字列生成、buildSeriesTabs、buildFilterOptions、render（index.html:1151-1182）。render は並べ替え→renderTable（innerHTML 一括）→fitTableZoom（index.html:1343-1425, 1427-1502, 1516-1539）。

## 2. 時間の内訳（本番 1hc、headless chromium、未ログイン、毎回新規コンテキスト）

計測スクリプトと生出力は /tmp/CC報告ファイル/gas_fast_recon/ にある。

【事実】段ごとの測定値（ms）。測定は複数回の別スクリプトで、同じ段でも大きくぶれた。

| 段 | 測定値 | 根拠 |
|---|---|---|
| ① 外側ページ（/exec）の応答 | 630〜3041（中央 約1000）。curl 単発は TTFB 1.15 s、76,901 byte | clean2_out.txt の exec / curl_html.txt |
| ② Google の枠の読み込み（userCodeAppPanel、wardeninit、charts/loader.js）。ここまでで google.script.run が呼べる | /exec 開始から呼び出し開始（cbReq）まで 3316〜6713 | clean2_out.txt の cbReq、breakdown_out.json の net |
| ③ getInventoryData（サーバー実行＋往復。callback POST） | 1337〜2333（clean2）、1507〜4514（breakdown）。直接呼び 2000/2111 | gsr、breakdown_out.json direct_* |
| ④ 応答到着から表が見えるまで | 2241〜8989（バラつき大）。別実行の breakdown では 800〜2400 | clean2/3_out.txt の renderAfterCb |
| ⑤ 画面側の関数単体（ページ内で直接実行） | render_total 230〜303、fitTableZoom 476〜505、renderTable 95〜103、sort 35〜45、buildSeriesTabs/Filter 各 約1 | render_prof_out.txt。ALL_ROWS=825、表示564行（24時間絞り込み） |

- 全体（開いてから表）: 今回の測定は 6396〜9189（breakdown、4回）、7862〜15162（clean2/3、9回）。前回 gas_load_timing.txt は 10616〜16806。測定の度にぶれる。
- 【事実】HtmlService のページ配信（①②）だけで、google.script.run を呼べるまで 3.3〜6.7 秒。GAS 側のコードを速くしても、ここは下がらない（Google の枠）。
- 【事実】サーバーの getInventoryData は 1.3〜2.3 秒が多い。シート読みの純粋な内訳（getValues と変換）は未計測。
- 【事実】表の描画（⑤）はページ内の関数単体で 0.2〜0.8 秒。④ が ⑤ より大きく出る理由（応答の受け渡し／ブラウザの負荷）は未確定。
- 「更新」ボタンが 1.9〜2.5 秒になる理由【事実】: 更新は枠の読み込み（①②）を含まない。かつ計測の終点が「更新中」表示の解除で、解除は onDataLoaded の先頭（index.html:1151-1154）にあり、render 前。つまり getInventoryData の往復（③）だけの時間（直接呼び 2.0/2.1 秒と一致）。
- 【推測】初回の 10〜17 秒 ≒ ①②（3〜7秒）＋③（1.5〜4.5秒）＋④（1〜9秒）。④ の大きなぶれは未解明。
- 未計測: Apps Script の実行ログ上のサーバー実行時間（clasp の認証ファイルが共有のため触っていない）、実機スマホ、ログイン済みブラウザ、テスト版 1Tb（完全 ID 不明）。

## 3. GAS からバックエンドを呼んでいる既存の例

【事実】
- repo 内で UrlFetchApp を使うのは `docs/feedback_form_to_github.gs:127,219,254` のみ。宛先は GitHub API と Discord webhook で、api.salesanchor.jp ではない（同ファイルに api.salesanchor の記述 0件）。トークンは ScriptProperties（`docs/feedback_form_to_github.gs:27,190`）。在庫一覧 GAS には UrlFetchApp も PropertiesService も無い（Code.js 全文）。
- バックエンド側に「匿名向け API をトークンで守る」GAS 専用の前例は無い。近い既存の仕組み:
  - 端末トークン: `backend/app/routers/line_import_devices.py:15,64-65` の HTTPBearer、`backend/app/services/line_import_devices.py:89-111`（token_hash 照合・scope・失効・有効期限 90日）。用途は LINE 取り込み専用で super admin 所有の端末のみ。
  - Bot API キー: `backend/app/routers/bots.py:55-59`（`botkey_` + bcrypt）。発行・ローテートはあるが、検証側の dependency は backend/app 内に見つからない（`git grep api_key_hash` は bots.py, schemas/bot.py, services/tenant.py:675 のみ）。
  - スモーク用: `backend/app/auth/dependencies.py:38-41,140-150`（SMOKE_SERVICE_TOKEN、compare_digest。CI 専用）。
- 既存の在庫読み出し口: `GET /inventory`（`backend/app/routers/inventory_offers.py:282-287`）は `require_permission("products.view")`＝ログインユーザー必須。匿名では呼べない。
- ADR: GAS／UrlFetch／service token／api key を扱う外部連携トークン方式の ADR は見つからなかった（`git grep -il` で docs/adr を検索。ヒットは ADR-154 等の「GAS 解析の移植」で別件。docs/adr/FEATURE-INDEX.md に該当行なし）。

## 4. バックエンドの在庫行の関数

【事実】
- `distribution_rows_parts(*, include_flag_single, age_condition, merge_same_post)` は SQL 文字列を返す関数（`backend/app/services/tcg_distribution_svc.py:274-370`）。引数は3つだけで、DB・リクエスト・認証に依存しない。配信以外からの呼び出し実績: `backend/app/routers/inventory_offers.py:342`（在庫表）。
- 実行用の入口: `fetch_output_rows(db, include_flag_single, max_age_hours)`（`backend/app/services/tcg_distribution_svc.py:390-411`）は14列（GAS と同じ列）のリストを返す。設定は `load_distribution_settings(db)` と `_max_age_hours`（`backend/app/routers/inventory_offers.py:322-337` と同じ手順）。
- 所要: 【事実】`/inventory` 全体で ON 0.53〜0.64 秒、OFF 0.51〜0.53 秒（本番再測定 #4249。docs/handoff/inventory-parity-bin1/recon.md:49 が引く /tmp/CC報告ファイル/same-post-rows/sp2/perf2/RESULT-20261014-4249.md）。この値は SQL＋ページング（50件）＋facet 込みで、全行（約825行）を返す `fetch_output_rows` 単体の時間は未計測。

## 5. キャッシュ・前計算の既存の仕組み

【事実】
- Redis 利用箇所: `backend/app/cache.py:1-80`（JWT 検証 5分・テナント 10分・権限 5分の TTL）、配信の予約キー `backend/app/tasks/tcg_extraction.py:647-648`（TTL600秒、60秒遅延）、`backend/app/services/sse_pubsub.py`、`backend/app/routers/dashboard.py`、`backend/app/tasks/dashboard.py` ほか（`git grep -il redis -- backend`）。在庫行そのもののキャッシュは無い。
- 配信は定期 cron ではなくイベント駆動: 解析後 `backend/app/tasks/tcg_extraction.py:455-457,605-608`、人の修正後 `backend/app/tasks/tcg_extraction.py:670-693`（60秒後・600秒に1回）、手動 `backend/app/routers/tcg_distribution.py:166-184`。TCG_AUTO_DISTRIBUTE は既定 0（`docker-compose.yml:104,224`）。beat に配信エントリ無し（`backend/app/celery_app.py:60-178`）。
- 配信先シートは書き込み前に `worksheet.clear()`（`backend/app/services/tcg_distribution_svc.py:632`）、行数上限 5000（同:44）。GAS の鮮度は「最後の配信時刻」で決まる。
- 【未確認】GAS 画面に最終配信時刻を出すコードがあるか（index.html を目視していない範囲あり）。

## 6. GAS の HTML の作り

【事実】
- `createTemplateFromFile('index').evaluate()` を使うが、index.html に scriptlet（`<?`）は0件（`grep -c "<?"` = 0）。テンプレート機能は使っておらず、データは埋め込まれていない。
- データは読み込み後に google.script.run で取得する作り（index.html:996-997, 1145-1148）。DOMContentLoaded までは骨組みだけ。
- 外部 JS/CSS（warden, charts/loader.js, Material Icons）は Google の枠が自動で読み込む。index.html 側は単一ファイル（1620行、64,898 byte）。
- データ埋め込みにするなら `evaluate()` 前に `tmpl.data = ...` を渡す形に変える必要がある（現状はそうなっていない）。その場合も ①② は残る。

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/services/tcg_distribution_svc.py:274` | distribution_rows_parts は SQL 文字列を返す関数 |
| `backend/app/services/tcg_distribution_svc.py:390` | fetch_output_rows（14列。配信が使う実行入口） |
| `backend/app/services/tcg_distribution_svc.py:632` | 配信先シートを clear してから書く |
| `backend/app/routers/inventory_offers.py:282` | GET /inventory は products.view 必須 |
| `backend/app/routers/inventory_offers.py:342` | distribution_rows_parts の配信以外からの呼び出し |
| `backend/app/tasks/tcg_extraction.py:670` | 人の修正後の配信予約（Redis NX、60秒後） |
| `backend/app/celery_app.py:60` | beat_schedule に配信エントリ無し |
| `backend/app/cache.py:1` | Redis の既存用途（JWT・テナント・権限） |
| `backend/app/services/line_import_devices.py:89` | 端末トークン方式（hash 照合・scope・失効）の前例 |
| `backend/app/routers/bots.py:55` | Bot API キー（bcrypt）の発行 |
| `backend/app/auth/dependencies.py:140` | SMOKE_SERVICE_TOKEN の Bearer 判定 |
| `docs/feedback_form_to_github.gs:127` | repo 内の UrlFetchApp（GitHub 宛て） |
| `docs/handoff/dist-deploy-guard/gas-deploy-runbook.md:25` | GAS の反映手順書 |
| `docs/handoff/inventory-parity-bin1/recon.md:49` | /inventory の所要 0.5 秒台の出典 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | getInventoryData のサーバー実行時間の内訳（getValues／変換／転送） | Apps Script の実行記録を PO 側で確認、または計測コード付きのテスト版（1Tb）で測る | 未解決 |
| 2 | 応答到着から表が見えるまで（④）が 2〜9 秒とぶれる原因 | ログイン済みブラウザの Performance 録画で、受け渡しと render を分ける | 未解決 |
| 3 | fetch_output_rows 単体（全約825行）の所要 | 本番の別コンテナで read-only 計測（PO 許可が要る） | 未解決 |
| 4 | GAS 向け匿名・トークン API の既存 ADR | docs/adr に見つからない＝新規 ADR が要る見込み | 未解決 |
| 5 | Bot API キーを検証する dependency の所在 | bots.py 以外にコードが無い。別 repo／別サービスかは未確認 | 未解決 |
| 6 | テスト版 1Tb の完全 ID・実機スマホでの時間 | PO から入手 | 未解決 |
| 7 | GAS 画面に「最終配信時刻」を出せるか（鮮度の見える化） | 配信結果テーブルの有無を設計時に確認 | 未解決 |

**未解決ゼロ確認**: 上記7件が未解決（設計便の着手前に 1〜3 を解消するのが望ましい）

---

## 補足

- 【推測】初期表示の下限は ①②（Google の枠）で 3〜7 秒。GAS の枠を使い続ける限り、データ取得方式を変えても1秒以内には届かない。1秒を狙うなら、枠の外（アプリ側 or 静的ページ）で表示する案が候補。設計は別便。
- 仕入れ先の原文は含めていない。

---

## 閲覧ページ（2026-10-14 追加調査）

生の出力: /tmp/CC報告ファイル/viewer_recon/（adr_hits.txt, t002_code.txt, bundle_sizes.txt, bundle_headers.txt, app_index.html ほか）。読み取りのみ。本番 DB・GAS は未接触（本番へは公開の静的ファイルの GET/HEAD のみ）。

### 1. 既存 ADR
【事実】
- 閲覧者向け・トライアル・契約管理・匿名の閲覧ページを扱う ADR は無い。`git grep -il`（キーワード各種）のヒットは docs/adr/ADR-1013、ADR-126、ADR-127 ほか別件で、docs/adr/FEATURE-INDEX.md にも該当行なし（ログイン／パスキーの行のみ。FEATURE-INDEX.md:28 付近）。→ 新規 ADR が要る。
- ADR-1013（docs/adr/ADR-1013-self-hosted-auth-and-passkey.md Decision 1〜5b）: パスワード・パスキー・再設定メールを自社で持つ。ログインは public.users.id に紐づく。メールは salesanchor.jp から自社サーバーが送る（Decision 5）。ログイン API は app.salesanchor.jp 以外から呼ぶと拒否（5b）。PO 承認済み。
- ADR-1014（docs/adr/ADR-1014-inventory-view-shows-distribution-rows.md）: 配信行の定義は distribution_rows_sql の1か所。
- ADR-097/126/127: 署名トークン付きの公開登録フォーム（顧客登録）の前例。ADR-127(auth-lockout) は IP ブルートフォース保護。ADR-072: テナントの schema 修飾と `reset_tenant_context`。

### 2. ユーザー・テナント・権限
【事実】
- public.users は tenant_id 必須（NOT NULL、FK tenants）、email 一意、is_active、is_super_admin（backend/app/models.py:22-37）。public.tenants は tenant_name/tenant_code/is_active/settings(JSON)（models.py:8-17）。
- 外部の人を「ユーザー」にする経路: `POST /api/v1/auth/register` は super admin 専用（backend/app/routers/auth.py:38-75）。ユーザー作成後の初回設定メールは ADR-1013 の仕組み（backend/app/services/auth_mail.py:51-64、SMTP）。
- 権限: `require_permission`（backend/app/auth/dependencies.py:598-622）はテナントのロールの権限の和集合で判定。在庫表 `GET /inventory` は products.view（backend/app/routers/inventory_offers.py:285）。ロールはテナントごとの表（tenant_xxx.roles/role_permissions/user_roles）で、新テナント作成時に既定ロールを種付けする（backend/app/services/tenant.py:46-130 付近、:1576 seed_system_roles）。
- テナント分離: schema 方式。`SET search_path = tenant_NNN, public` と `SET app.tenant_id`（backend/app/auth/dependencies.py:280-283, 325-326）。テナント作成は `create_tenant_schema`（backend/app/services/tenant.py:1634、`POST /tenants` は super admin 専用 backend/app/routers/admin.py:17）。RLS は各テナント表のポリシー。
- メール送信: あり。SMTP 直送（`smtplib`、STARTTLS）。設定は backend/app/services/mail_config.py:27-35（SMTP_HOST/USER/PASSWORD/MAIL_FROM がそろわないと「送らずログだけ」）。使用箇所 backend/app/services/auth_mail.py:51-64、backend/app/routers/contact.py:40-69、backend/app/routers/purchase_orders.py:414-465。【未確認】本番で SMTP が実際に設定済みか（ADR-1013 Context は「自社のメール送信設定は無い」2026-10-13、その後 便3 で追加の記録あり。値は見ていない）。

### 3. 期限付きアクセスの前例
【事実】
- users / tenants に有効期限・契約状態・トライアルの列は無い（models.py:8-37。tenants は is_active のみ）。`git grep -iE "trial|valid_until|contract_status|plan_tier"` で該当する契約系の表・列は無し。ヒットは別件（トークン失効、Meta の subscription 等）。
- 近い前例: `public.tenant_features`（tenant_id, feature_key, enabled。migrations/20260627_120000_add_tenant_features_table.sql:6、`require_feature` backend/app/auth/dependencies.py:625-）＝テナント単位の機能スイッチ。期限は持たない。
- 期限付きトークンの前例: 端末トークン（有効期限 90日、backend/app/services/line_import_devices.py:89-111）、登録フォームの署名トークン（backend/app/services/registration_token.py）、パスワード再設定の使い捨て鍵（migrations/20261013_160000_add_self_hosted_auth_tables.sql）、`inventory_offers` の期限切れ削除（backend/app/celery_app.py の purge-expired-inventory-offers 1800秒）。

### 4. フォーム・問い合わせの前例
【事実】
- LP（Astro）: lp/src/pages/index.astro:334-335 の `contact-form` が `https://api.salesanchor.jp/api/v1/contact` へ POST（:871）。LP のページは index, pricing, privacy, terms, data-deletion, deletion-status, 404（lp/src/pages/）。
- 受け口: backend/app/routers/contact.py:36-100。入力は name/email/company のみ。**DB には保存しない**。support@salesanchor.jp にメール転送（SMTP 未設定時はログのみ）。送信失敗でも「受付」を返す。
- スパム対策: CAPTCHA/honeypot/Turnstile は repo に無し（`git grep -iE "turnstile|recaptcha|hcaptcha"` 0件）。共通の rate limit のみ: 未認証 IP 60回/分（backend/app/middleware/rate_limit.py:25-27、Redis 不通は fail-open）、nginx `limit_req zone=api rate=30r/s burst=50`（nginx/nginx.conf:8,152-153）、auth は 10r/m（:6,97,293）。
- 公開フォーム（匿名）の前例: `/register`（顧客登録、署名トークン必須）frontend/src/App.tsx:156-158、API は backend/app/routers/registration_tokens.py:105,151,271。

### 5. キャッシュの土台
【事実】
- Redis 接続: backend/app/cache.py:12-40（`init_redis`/`get_redis`、REDIS_URL 既定 redis://redis:6379/0）。JWT 5分・テナント 10分・権限 5分の TTL（:15-20）。
- celery beat: `beat_schedule`（backend/app/celery_app.py:60-）。最短は 600秒（dashboard KPI）、300秒（review mail）。**1分（60.0）の定期は現状無い**が、`"schedule": 60.0` の秒指定は同じ書式（既存 600.0/900.0/1800.0）で書ける【推測：動く見込み。未実行】。
- 「定期で作って Redis に置く」前例: backend/app/tasks/dashboard.py（同期 engine＋Redis、`refresh-dashboard-kpis` 600秒、_compute_kpis 49行〜）。
- 配信は Redis NX 予約キーで 60秒遅延・600秒に1回（backend/app/tasks/tcg_extraction.py:647-693）。
- ワーカーが重い SQL で他タスクを詰まらせる懸念は【未確認】（worker 並列数は未調査）。

### 6. 軽いページの置き場所
【事実】
- (a) app.salesanchor.jp の React: `/` は frontend コンテナに proxy（nginx/nginx.conf:237-238）、`/api/` は backend（:151-155）。本番 index は `/assets/index-wkjOFFUl.js` **2,577,818 byte**（圧縮なし。Content-Encoding 無し、`curl -I -H 'Accept-Encoding: gzip, br'` で content-length 2577818 のまま。/tmp/CC報告ファイル/viewer_recon/bundle_headers.txt）＋ CSS 301,247 byte（bundle_sizes.txt）。ブラウザ側キャッシュは max-age=31536000 immutable（2回目以降は読み込み不要。初回のみ重い）。コード分割: `React.lazy`/`import()` は frontend/src 全体で16行のみ、App.tsx:154-158 のルートは通常 import（lazy 0件）＝ほぼ分割されていない。公開ルートは /login, /register 等（App.tsx:154-158）。CSP は script-src 'self'（外部 JS 不可）。
- (b) backend が HTML を直接返す: `/api/` は backend へ proxy（nginx.conf:151-155）。api.salesanchor.jp も同様（:347-351）。FastAPI で HTMLResponse を返せば bundle 無しで可。Redis にそのまま HTML 文字列を置ける。nginx の `limit_req zone=api` 30r/s が掛かる。
- (c) Astro LP: salesanchor.jp は nginx が静的ファイルを配信（root /var/www/salesanchor、nginx.conf:457,461-476）。静的なので閲覧の表（動的データ）は JS で API から取るしかない。LP の CORS・CSP は未確認。
- nginx の `location = /design` のように専用パスを切る前例あり（nginx.conf:211-223）。

### 7. 閲覧のテナント
【事実】
- 配信行の元データは public スキーマ: TCG_SCHEMA = "public"（backend/app/services/tcg_distribution_svc.py:41）。analysis_results / extraction_items / extraction_jobs / source_messages / supplier_channels（同:317-324）、tcg_distribution_settings（:181）はすべて public。public.products / public.type_master / public.suppliers は LEFT JOIN（同:72-76）。配信設定にテナントの概念は無い（`tenant` 検索で関連は :1074 `tenant_id=4` の1箇所のみ）。
- 【事実】public.products のみ FORCE RLS: `tenant_id IS NULL OR tenant_id = app.tenant_id`（migrations/20260626_130000_force_rls_public_products.sql:5-14）。パイプライン表（analysis_results 等）に RLS を付ける migration は見つからない（migrations/20260921_110000_pipeline_tables_public.sql に ROW LEVEL SECURITY / POLICY の記述 0件）。
- 【事実】`/inventory` は既存ログインユーザーのテナントの search_path で動くが、使う表は public 側なので、どのテナントのユーザーでも同じ行が見える設計（inventory_offers.py:313-345）。
- GAS を見ている人の把握: GAS 側コード（Code.js）に記録処理は無い（recon 本文 §3: UrlFetchApp/PropertiesService なし）。【未確認】Apps Script の実行ログ・Google 側のアクセス数（clasp 未使用のため見ていない）。

### 8. 1回の重さを測る方法（候補のみ・未実行）
【事実】
- 配信の run_distribution は fetch_output_rows の所要を測っていない（backend/app/services/tcg_distribution_svc.py:933-935 に時間計測なし。ログは件数・警告のみ）。`last_distributed_at/count` は終了時刻と件数のみ（:795-796）。
- 全リクエストの所要は Prometheus `http_request_duration_seconds`（backend/app/metrics.py:12-16）。/inventory は 50件ページング込みの値（0.5秒台、前述）。
候補（実行は PO 許可後）:
1. 本番の別コンテナで read-only トランザクションに SELECT だけ（`EXPLAIN (ANALYZE, BUFFERS)` を distribution_rows_parts の SQL に対して）。memory prod_measure_isolated_container の方式。
2. 同じ SQL を psql の `\timing` で 5 回（人間実行、memory cc_db_path_backlog）。
3. ローカルでは本番データが無いので不可。Prometheus の /inventory の per_page=200 を使う案は、ページング込みで fetch_output_rows とは別物。
4. 実装時に `time.perf_counter()` を fetch_output_rows の前後に入れてログに出す（製品コード変更のため設計便）。

### 9. tenant_002 の現状と、閲覧専用テナントにできるか
【事実】
- (a) tenant_002 は repo では CI のダミー表と一覧にしか出ない: .github/workflows/migration-test.yml:421-465, 1352-1490（deals なしテナントの CREATE SCHEMA）、backend/app/routers/super_admin_db_schema.py:30（対象スキーマ一覧）、テスト backend/tests/test_data_deletion_helpers.py:92 ほか。seed・設定ファイルには無し。テナントは schema 方式（tenant_NNN）＋ public.tenants の行。tenant_001 は本番の確認用で実在（memory project_paid_at_payment_date、project_discord_reaction_heart）。
- 「使っていない」の根拠: memory project_attachment_storage_progress.md に「tenant_002 はスキーマ自体が存在しないため対象外（実測済み）」（2026-09-02 の本番 migration 結果。その時点で tenant_001/003/004/005/006 のみ NOTICE）。docs/handoff/roles-system-key-column/recon.md:35 は「本番に tenant_002 などの欠番スキーマがあるかは確認していない」。**現在も無いかは未確認**。tenant_002 は「欠番」の可能性があり、「使っていないテナント」ではなく「作られていない番号」かもしれない。
- (b) 配信の元データは public（上記7）。tenant_002 のユーザーも、パイプライン表は読める（RLS 無し）。public.products は tenant_id IS NULL の共通行のみ読める（他テナント固有行は RLS で見えない）。配信行が products の共通行に紐づいているか固有行かは【未確認】（行ごとの tenant_id の分布を見ていない）。
- (c) 閲覧専用に制限: 権限はテナントのロール単位（require_permission、dependencies.py:598-622）なので、tenant_002 に products.view だけのロールを作れば他 API は 403 になる。ただし画面（CRM・受信箱）のメニュー閉鎖が権限で制御されているかはフロントを未確認。また新テナント作成は既定ロール6種（管理者・マネージャー等）を種付けし（tenant.py:46-130）、オーナーは全権限（"ALL"）。super admin は PO と担当エンジニア限定（memory project_super_admin_policy、2026-10-07）のため、外部利用者に付与しない。
- (d) 本番 tenant_002 の実データ: **【未確認】**（コードからは判断不能。本番では実行しない）。人間が実行する確認 SQL 候補: public.tenants の id=2 の行、information_schema.schemata の tenant_002、public.users の tenant_id=2。

### 未確認の一覧（追加分）
1. 本番 SMTP の設定有無（値は見ない）。
2. celery beat を 60秒周期にしたときのワーカー負荷・並列数。
3. fetch_output_rows（約800行）単体の所要。
4. 配信行が参照する public.products の tenant_id 分布（共通 NULL か固有か）。
5. 本番に public.tenants id=2 / tenant_002 スキーマ / users が今あるか。
6. フロントのメニューが権限で閉じるか（外部ユーザー向け）。
7. LP→API の CORS・CSP（Astro 置き場の場合）、GAS の現閲覧者数。
