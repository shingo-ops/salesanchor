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
  - Bot API キー: `backend/app/routers/bots.py:55-59`（`botkey_` + bcrypt）。発行・ローテートはあるが、検証側の dependency は backend/app 内に見つからない（`git grep api_key_hash` は bots.py, schemas/bot.py, backend/app/services/tenant.py:675 のみ）。
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
- (a) app.salesanchor.jp の React: `/` は frontend コンテナに proxy（nginx/nginx.conf:237-238）、`/api/` は backend（:151-155）。本番 index は `https://app.salesanchor.jp/assets/index-wkjOFFUl.js` **2,577,818 byte**（圧縮なし。Content-Encoding 無し、`curl -I -H 'Accept-Encoding: gzip, br'` で content-length 2577818 のまま。/tmp/CC報告ファイル/viewer_recon/bundle_headers.txt）＋ CSS 301,247 byte（bundle_sizes.txt）。ブラウザ側キャッシュは max-age=31536000 immutable（2回目以降は読み込み不要。初回のみ重い）。コード分割: `React.lazy`/`import()` は frontend/src 全体で16行のみ、App.tsx:154-158 のルートは通常 import（lazy 0件）＝ほぼ分割されていない。公開ルートは /login, /register 等（App.tsx:154-158）。CSP は script-src 'self'（外部 JS 不可）。
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


## 段5（2026-10-19）

（調査の生記録: /tmp/CC報告ファイル/viewer_stage5/recon_raw.md。基準は origin/main。パスは frontend/src・backend/app の下をフルパスに展開して写した。）

基準: `git fetch origin main` 後の origin/main。行番号付き全文の写しは /tmp/CC報告ファイル/viewer_stage5/src/ 配下（ファイル名は パスの / を _ に置換）。

### R§1 ViewerAccountsPage.tsx（frontend/src/pages/super-admin/ViewerAccountsPage.tsx、360行）
【事実】import（:7-19）: react の useCallback/useEffect/useState、react-i18next useTranslation、`api, ApiError`(../../lib/api)、useSuperAdmin(../../hooks)、components の PageLayout / Button / ButtonLink / Badge(+BadgeVariant) / DataTable(+DataTableColumn) / EmptyState / Modal / Drawer / TextField。react-router の import は無い。
- 型: ViewerItem（:21-34、id,email,line_name,inventory_issue,status,trial_expires_at,created_at,discord_user_id,discord_channel_id,discord_channel_url,flag_many_ips,flag_shared_ip）、LoginItem（:36-41）、Action=activate|suspend|unsuspend|extend（:43）。
- 状態バッジ: STATUS_VARIANT（:45-51）active=success / trial=info / suspended=danger / pending=neutral / verified=neutral。STATUS_KEY（:53-59）→ ja の statusPending 等。
- データ取得: `api.get("/super-admin/viewers")` を load()（:90-100）。マウント時 isSuperAdmin なら実行（:102-106）。一覧は全件を1回で取り、ページ分け・絞り込みは画面側に無い。状態変更は `api.post(/super-admin/viewers/${id}/${action}, …)`（:131-136）後に load() 再取得。ログイン記録は `api.get(/super-admin/viewers/${id}/logins)`（:152）を Drawer(:334-357) に表示。
- 表の列（:174-257）: email / line_name / status(Badge) / trial_expires_at(期限) / discord_user_id(+discord_channel_url があれば ButtonLink「部屋を開く」) / flags(Badge warning ×2) / created_at / actions。
- 操作ボタン（:229-255）: trial の行に「本契約にする(primary)」「延長(secondary)」、suspended 以外に「停止(danger)」、suspended に「停止を解除(secondary)」、全行に「ログイン記録(ghost)」。pending/verified/active 行で出るのは「停止」と「ログイン記録」のみ。
- 確認 Modal（:289-332）、延長日数 TextField（:319-329）。PageLayout は navKey="nav.superAdminViewers" subtitleKey="superAdmin.viewers.subtitle"（:272）。noScroll なし。非 super admin は :164-172 でアクセス拒否表示。
- クリップボード・サイドメニュー・URL パラメータの利用は無い。
### テスト frontend/src/pages/super-admin/ViewerAccountsPage.test.tsx（153行、it 8本）
api と useSuperAdmin を vi.mock、i18n は en。確認内容: (1)非 super admin は拒否文のみで api.get 0回（:56）(2)状態バッジ・フラグバッジが該当行だけ（:63）(3)discord_channel_url がある行だけ「Open room」リンク（:73）(4)trial 行に Make active/Extend/Suspend、suspended 行に Unsuspend のみ（:93）(5)suspend のモーダル→POST `/super-admin/viewers/1/suspend` {}→一覧再取得2回（:107）(6)extend は0で送信不可・7で POST {days:7}（:117）(7)409 で競合メッセージ（:130）(8)ログイン記録 Drawer に時刻・IP・端末（:139）。MemoryRouter で包んで描画（:35-41）。

### R§2 状態の値と list_viewers
【事実】DB: migrations/20261016_150000_add_viewer_accounts.sql:21 `CONSTRAINT ck_viewer_accounts_status CHECK (status IN ('pending','verified','trial','active','suspended'))`。:29 コメント「pending／verified／trial／active／suspended。verified は将来用」。
- 意味（ja.json:2667-2671）: pending=申込中 / verified=確認済み / trial=お試し / active=本契約 / suspended=停止中。
- 遷移の実装: 申込 POST /signup で pending を INSERT（backend/app/routers/viewer.py:458-459）。trial への移行は Discord 受付の申込コード照合（design.md:594 Q5「照合が済んだ時点で自動的にトライアル。verified は今回使わない（5値は残す）」）。activate は trial→active のみ（backend/app/services/viewer_admin.py:147-150）、extend は trial のみ（:171-175）、suspend は suspended 以外（:151-154）、unsuspend は直前 suspend の from_status に戻す（:155-170）。
- status変更履歴 viewer_status_changes（migration:79-93）action CHECK は activate/suspend/unsuspend/extend/start_trial、actor は po/claude/system。
- list_viewers（backend/app/services/viewer_admin.py:88-90）: `_LIST_SQL`（:39-65）。返す項目: v.id,email,line_name,inventory_issue,status,trial_expires_at,created_at,discord_user_id,discord_channel_id,discord_guild_id(→discord_channel_url に変換 :68-77),flag_many_ips,flag_shared_ip。並び順 `ORDER BY v.created_at DESC, v.id DESC`（:64）。WHERE なし・LIMIT なし・ページ分けなし（全件）。status での絞り込みはサーバー側に無い（クエリパラメータも無し。backend/app/routers/super_admin_viewers.py:85-86 は引数 db のみ）。
- ログイン記録だけ LIMIT 500（backend/app/services/viewer_admin.py:22,105）。
- 応答モデル ViewerAdminItem（backend/app/routers/super_admin_viewers.py:37-51）。申込コード/招待に関する項目は一覧に無い。
- ja.json superAdmin.viewers（frontend/src/locales/ja.json:2657-2705）キー: subtitle, colEmail, colLineName, colStatus, colExpires, colDiscord, openRoom, colFlags, colCreated, colActions, statusPending/Verified/Trial/Active/Suspended, flagManyIps, flagSharedIp, empty, activate, extend, suspend, unsuspend, logins, confirmActivate/Suspend/Unsuspend, extendTitle, extendTarget, extendDays, run, loadError, notFoundError, conflictError, genericError, loginsTitle, loginsEmpty, colLoginAt/Type/Ip/Agent, eventLoginSucceeded…eventCodeMatched。招待・コピー・申込フォーム・絞り込み用のキーは無い。nav.superAdminViewers=閲覧者管理（ja.json:264）。

### R§3 申込の流れ
【事実】backend/app/routers/viewer.py（487行）
- :399 SIGNUP_CODE_TTL=7日。:416 `POST /signup`。
- 流れ: Origin 検査 :426 → email 正規化・line_name 1〜100 字 :427-430 → IP 1時間10回・email 1時間3回の回数制限 :433-440（Redis で数えられないときは招待を作らない `limits_ok` :440,:486）→ generate_signup_code（16文字 Crockford base32）:442 → honeypot `website` が入っていれば行も招待も作らず捨てコード+invite_url null :445-446 → 既存 users に email があれば何もしない :448-451 → viewer_accounts が無ければ status 'pending' で INSERT :455-463 → 既存が pending なら旧 signup_code トークンを DELETE して作り直し :468-473 → viewer_login_tokens に INSERT（purpose 'signup_code'、sha256 のみ、expires_at=7日後）:474-481 → login_events に 'signup' :482 → commit :483 → commit の後に create_viewer_invite :486 → 応答 `{signup_code(XXXX-XXXX-XXXX-XXXX), expires_at, invite_url}` :403-404。
- 申込コードの保存: public.viewer_login_tokens（migration:39-56）列 id, viewer_account_id(→viewer_accounts.id), token_sha256 BYTEA(32バイト・UNIQUE), purpose('signup_code'|'password_reset'), expires_at, created_at。平文は保存しない（ハッシュ化 backend/app/auth/viewer_signup_code.py:24-25）。申込コードは viewer_account_id で viewer の行に結びつく（1 viewer・pending 再申込のたび差し替え）。
- 招待 backend/app/services/viewer_invite.py（57行）create_viewer_invite: viewer_discord_config(id=1) の reception_channel_id を読み（:31）、`POST /channels/{reception_channel_id}/invites` に `{"max_age":604800,"max_uses":1,"unique":true}`（:39-46。定数 :19-20 = 7日・1回）。bot token は環境変数 DISCORD_BOT_TOKEN（:36）。戻りは `https://discord.gg/<code>`（:50）、失敗時は None（:34,:38,:49,:54,:58）。docstring :5「招待は DB に保存しない（正本は Discord）」。招待 URL の列・表は無い（`viewer_discord_config` は migrations/20261017_100000:2-12 の guild_id, reception_channel_id, ticket_category_id, staff_role_id のみ）。招待と申込コード/viewer の紐づきはコード上に無い（invite_url は応答にだけ載り、DB に保存されない）。
- 【事実】招待は「申込1回につき1本」を作る仕様。つまり現行の招待は /signup の応答でしか得られない。管理画面から発行する API（super-admin 側）は現状無い（backend/app/routers/super_admin_viewers.py の docstring :5-12 の6本のみ）。
- Q16 の記載: docs/handoff/gas-viewer-fresh-fast/design.md:607（Q16 決定 2026-10-17 PO「y」、期限1週間・使用1回）、:260（D5「招待リンク」PO 決定。原文引用）、:261（API 呼び出し）、:263（作れなかったとき）、:264（登録済み email でも作る／honeypot では作らない）、:265（DB に保存しない・期限は申込コードと同じ7日）、:267（権限 805432406→805432407）、:364-368（受け入れ基準）、:494,:504-509（段4実施）。ADR-1019 本文（docs/adr/ADR-1019-inventory-viewer-separate-accounts.md、40行）には「招待」「管理画面」の語は無い（grep 0件。:23 に「申込と本人の結び付けは…受付で申込コードを照合」）。

### R§4 閲覧ページから申込画面への入口
【事実】frontend/src/pages/viewer/ViewerApp.tsx: 画面状態 Screen に `{name:"signup"}`（:23）。URL で入口を決めるのは `#reset=` のみ（:25-33,:50-51,:57-59）。signup を直接開くハッシュ・クエリは無い（`git grep "location.(hash|search)|URLSearchParams" frontend/src/pages/viewer` の結果は ViewerApp.tsx:29,:57 と Password.test.tsx:117 のみ）。初期画面は トークン有→loading、無→login（:52）。
- 現在の行き方: LoginView.tsx:99-101 の「申込」ボタン（data-testid="viewer-login-signup"、文言 frontend/src/locales/viewer/ja.json:74）→ onSignup（LoginView.tsx:40,:113 in ViewerApp）→ setScreen({name:"signup"})（ViewerApp.tsx:113）。申込画面は SignupView（:116）。
- 閲覧ページの URL: app.salesanchor.jp/viewer/（ADR-1019:15、frontend/viewer/index.html）。つまり申込フォームの URL としてコピーできるのは現状 `https://app.salesanchor.jp/viewer/` までで、申込画面を直接開く URL は存在しない（ログイン画面が出る）。
- SignupView（153行）: 完了画面で signup_code と invite_url と案内を表示（:60-91）、入力は email, lineName, inventoryIssue, 隠し欄 website（:101-141）。
- 重要: 閲覧ページは別バンドルで 300KB 上限（design.md:509）。ButtonLink を使わない理由が書かれている。

### R§5 既存の部品（金型）
【事実】frontend/src/components/ の .tsx 一覧（stories/test を除く）に次がある: Badge, Button, ButtonLink, Callout, Card, Checkbox*, ConfirmModal, DataTable, Drawer, EmptyState, ListRow, Modal, MultiSelect, NavDropdown, NavItemList, Popover, Select, Sheet, Stack, SubMenu, Tabs, TextField, Textarea, Toggle, Tooltip, TwoColumn（OverflowTabs は components 直下に .tsx としては見つからず）。
- サイドメニュー: **SubMenu.tsx**（縦型サイドナビ。variant grouped/flat。props groups[{title?, items[{key,label,icon?,badge?(数字),disabled?,to?}]}], activeKey, onChange?, className。`to` 有り=NavLink の「ドア型」、無し=button の「リモコン型」 :13-38,:64-117）。使用例: frontend/src/pages/crm/CustomerHubPage.tsx:72-77、frontend/src/pages/management-center/ManagementCenterPage.tsx:117-122（`<div className="hub-shell">` + `<SubMenu variant="grouped" className="hub-subnav" …/>` + `<div className="hub-content">`、PageLayout は noScroll）。hub-shell.css:1-40 が .hub-shell/.hub-subnav の寸法を定義。
- タブ: **Tabs.tsx**（variant underline|pill, size sm|md, items[{key,label,count?,icon?,disabled?}], activeKey, onChange :25-44）。super-admin 内の使用: AnalysisDashboardPanel.tsx:38, ExtractionErrorLogPanel.tsx:25, NeedsReviewTabsPanel.tsx:13, ProductMasterPanel.tsx:17, RuleManagementPanel.tsx:19。
- 状態バッジ: **Badge.tsx** variant neutral/info/success/warning/danger/purple（:16）。ViewerAccountsPage が既に使用（:14,:45-51,:181）。
- AnalysisRulesPage（frontend/src/pages/super-admin/AnalysisRulesPage.tsx, 200行）+ components/AnalysisRulesSidebar.tsx（134行）: PageLayout noScroll（:141-146）→ `div.hub-shell`（:151）→ **自前の** AnalysisRulesSidebar（`<nav className="hub-subnav">` の中に生の `<button className="hub-subnav-item active">` :50-56,:75-80。SubMenu は使っていない。共通 SubMenu への移行前の旧作り）→ `div.hub-content`（:159）。選択状態は useState + `useSearchParams` の `?section=`（:99-113、`setSearchParams({section:key},{replace:true})`）。
- URL で絞る既存例: (a) クエリ `?section=`（AnalysisRulesPage）(b) 子ルート+Outlet（CustomerHubPage の /crm/leads,/crm/companies,/crm/archive、ManagementCenterPage）。`:tab` のような動的セグメントで状態を分ける例は App.tsx の `path=".../:xxx"` 検索（App.tsx:162,180,183,185,198,212,217,220,248,250,252,262）に無い（すべて :id か :carrier）。useSearchParams を使うページ: contacts/ContactsPage, design-preview, inbox/useInboxState, register/*, schedule/SchedulePageImpl, super-admin/AnalysisRulesPage。
- docs/CC_UI_GOVERNANCE.md: :9-15 必須チェック（components/ に金型があるか先に確認→あれば使う→無ければ実装せず止めて報告）、:23-29 禁止表（:27 自作タブ＝className に `tab` を含む div/nav は禁止、:28 色直値、:29 生px）、:33-46 例外コメント書式 `ui-allow: <理由> (#<番号>)`、:59 ADR-144。ADR-149 は SubMenu への集約（CustomerHubPage.tsx:71 のコメント）。
- クリップボード: `navigator.clipboard` の既存利用 = frontend/src/features/tcg-distribution/DistributionTargetForm.tsx:125（writeText 後 setCopied(true) → 2秒で戻す）、frontend/src/features/tcg-import-workflow/ExtractionAttemptHistory.tsx:34、frontend/src/pages/inbox/InboxKartePanel.tsx:429（Button secondary sm +「registration.copyLink」）、frontend/src/pages/integrations/FedexLabelValidationTab.tsx:157。共通の hook / CopyButton 部品は無い（`git grep -i "useCopy|CopyButton|copyToClipboard" frontend/src` はコピー文言キーのみ）。各所が個別に writeText を直書き。

### R§6 グローバルメニュー・ルート
【事実】
- frontend/src/App.tsx:89 import、:342 `<Route path="/super-admin/viewers" element={<ViewerAccountsPage />} />`（フラットなルート。子ルート・Outlet なし）。
- frontend/src/components/DesktopShell.tsx:193-198 saasAdminItems の最後 `{ to:"/super-admin/viewers", labelKey:"nav.superAdminViewers" }`、:364-379 で isSuperAdmin のとき NavLink 描画。
- frontend/src/components/MobileShell.tsx:185-190 resolveItem("viewerAccounts","nav.superAdminViewers",…,"/super-admin/viewers")。
- nav.superAdminViewers = ja「閲覧者管理」(ja.json:264)。
- 状態ごとの URL 分けの既存例: クエリ（?section=）か子ルート+Outlet（上記）。ViewerAccountsPage は今どちらも使わない。

### R§7 ADR-1019 と design.md の管理画面・招待・申込フォーム
【事実】ADR-1019（40行）: 「管理画面」「招待」「申込フォーム」を含む行 0件。関連する行は :23（申込→Discord 受付で申込コード照合）、:27（discord-gateway が viewer_* に書く）。
design.md（docs/handoff/gas-viewer-fresh-fast/design.md、620行）:
- 申込フォーム: :158（⑤申込の画面）、:246（D5 見出し）、:259-267（応答・招待リンク・保存しない・権限）、:551 Q2b/:554 Q2f（フォームはメールと LINE 名の2つ）/:555 Q2g（在庫関連の課題・任意）。
- 招待: :260-265, :267, :364-368, :427-429（案B＝その人専用の招待で見分ける案は MANAGE_GUILD が要り ADR-091 で除外）, :494, :504-509, :607, :620（社内ユーザーの招待トークン発行は別件）。
- 管理画面: :448（PO 質問「ツールの顧客管理も出来るように」への答え）、:449（PO 決定「saas管理者y」・置き場所 DesktopShell/MobileShell）、:486-491（段4を4PRに。4a-2＝管理 API・viewer_admin.py・専用スクリプト・/super-admin/viewers の画面）、:510-511（4a-2 の細部。一覧の Discord 部屋 URL は 4c で足す）、:568, :580（画面は ViewerAccountsPage 1ページ、部品 DataTable/Badge/Button/TextField）。
- 対象外・未実装として明記されている関連: :551 本契約用の詳しい情報フォームは対象外（別の便）、:554 Discord ID の自動取得は別設計。**管理画面に「申込フォーム URL のコピー」「招待発行ボタン」「状態別の左メニュー」は design.md に記載なし**（上の grep 全件にその語はない）。:580 周辺の画面部品指定は DataTable/Badge/Button/TextField のみ（左メニューの記載なし）。
補足: 別の読み取り用ファイルに全文あり → /tmp/CC報告ファイル/viewer_stage5/src/docs_handoff_gas-viewer-fresh-fast_design.md（行番号付き）。

### R§8 FEATURE-INDEX
`git grep -n -i -E "viewer" origin/main -- docs/adr/FEATURE-INDEX.md` の結果: **0件**（出力なし）。

### 未確認
- design.md:580 付近と :568-575 の本文全体（管理 API の設計詳細）は行番号のみ拾い、全文の精読はしていない。
- OverflowTabs の実体（components 直下に .tsx が見つからない。別ディレクトリにあるかは未確認）。
- 本番で bot に「招待を作成」権限が付いているか、reception_channel_id の実値は未確認（DB・Discord は見ていない）。
- 招待発行 API を管理画面から呼ぶ際の権限・回数制限（/signup は IP/email の回数制限 viewer.py:433-440。super-admin 経由の扱い）は設計されていない（コード上に無いことのみ確認）。

## 段6（2026-10-19、origin/main d92162bd8 基準。詳細は /tmp/CC報告ファイル/viewer_stage6/recon_raw.md, recon_raw2.md）
- 延長：backend/app/services/viewer_admin.py:175-179 は trial のみ受け付け、期限は「今+日数」。上限365は backend/app/routers/super_admin_viewers.py:74-75 の ExtendRequest だけ。日付指定の入力は無かった。
- 画面の延長 Modal：frontend/src/pages/super-admin/ViewerAccountsPage.tsx:459-502。日付入力の金型は専用品が無く、TextField type="date"（frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx:276）。
- 作り直し：backend/app/services/viewer_admin.py:283-297 は pending のみ。画面は frontend/src/pages/super-admin/ViewerAccountsPage.tsx:294-298 で pending のみ表示。
- 受付：backend/app/discord_gateway/viewer_trial.py:269 は pending 以外を CODE_INVALID、:290-307 は status='trial'・期限14日へ更新（trial/active を通すと本契約がお試しに下がるため、段6で分岐）。
- 目印の SQL：backend/app/services/viewer_admin.py:43-65（一覧 SQL の中）。通知の対象も同じ条件を使うため、定数に切り出した。
- 通知の型：backend/app/tasks/master_required_fields_monitor.py と backend/app/celery_app.py の beat_schedule／include。重複防止の型は backend/app/services/review_mail_notifier.py:89-115（Redis キー＋TTL）。送信は backend/app/services/discord_notifier.py:45-64。
- 期限切れ trial の拒否（変えない）：backend/app/routers/viewer.py:193-200、backend/app/auth/viewer_dependencies.py:88-91。

## 段7（2026-10-20、origin/main 95e623fd3 基準。実物の点検）
- 画面：frontend/src/pages/super-admin/ViewerAccountsPage.tsx。列定義は `const columns`（約209行目）。段7前の並び：email, line_name, status, trial_expires_at, discord_user_id（openRoom の ButtonLink を含む）, flags, created_at, actions
- 表：frontend/src/components/DataTable.tsx。`onRowClick?: (row: T) => void`（100行目）。セル内のボタンは isInteractiveTarget（302行目・414行目）で行クリック扱いにならない。stopPropagation は不要
- スライド：frontend/src/components/Drawer.tsx。props は open / onClose / title / children / footer / size。使用例 frontend/src/pages/contacts/ContactsPage.tsx:365
- 横並び：frontend/src/components/Stack.tsx は縦積みのみ（Stack.css は flex-direction: column）。横並びの金型は無かった
- ラベルと値の並べ方：frontend/src/company-forms.css:78-98 の `.form-grid` / `.form-row` / `.form-grid > .form-row > label`（共通 class。使用例 frontend/src/pages/contacts/ContactsPage.tsx:305 の作成モーダル。同ページの Drawer（365行目）は ContactFormFields を使い form-grid は使わない）
- 既存 ADR 検索：ADR-1019（閲覧者管理）、ADR-144（金型）

## 段8（2026-10-20、origin/main d6f543e64 基準。実物の点検）
- LINE名の置き場所は public.viewer_accounts.line_name の1か所だけ。写しは無い
  - 書き込み：申込 backend/app/routers/viewer.py:458、初回登録 backend/app/services/viewer_admin.py:323
  - 読み出し：一覧 backend/app/services/viewer_admin.py:71
  - Discord の部屋の名前などには使っていない（backend/app/discord_gateway/viewer_trial.py に line_name は出てこない）
  - backend/app/routers/super_admin_suppliers.py の line_name は仕入元の別の項目で、関係ない
- 申込のときの決まり：前後の空白を除いて 1〜100 文字（backend/app/routers/viewer.py:87、428-429）
- 管理側 API：backend/app/routers/super_admin_viewers.py（保護は require_super_admin、誤りの変換は _ERROR_STATUS と _http_error、応答の型は ViewerAdminItem、1件の読み出しは viewer_admin._get_item）
- 画面：frontend/src/pages/super-admin/ViewerAccountsPage.tsx の Drawer。LINE名は読むだけの表示だった
- 編集スライドの前例：frontend/src/features/supplier-master/SupplierDetailDrawer.tsx（TextField 金型・api.patch・422 は入力の誤り・footer に Button）。仕入元の PATCH にも変更の履歴は無い
