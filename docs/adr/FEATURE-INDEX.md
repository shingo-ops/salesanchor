# 機能 → ADR 索引（着手前に必ず確認）

> **目的**: 機能に着手する前に「その領域の設計がすでに ADR で決まっていないか」を即座に引けるようにする索引。
> ADR は CLAUDE.md と違い自動ロードされない＝**指さないと参照されない**。見落とし防止のため、recon 段階で
> 必ずこの索引と `git grep -i "<機能キーワード>" docs/adr/` の両方で既存設計を拾うこと（[[docs/STANDARD-WORKFLOW.md]] Phase 2）。
>
> 網羅一覧は自動生成の [`README.md`](./README.md)。本ファイルは、すべての ADR を、正準 ADR 欄か末尾の「索引に載せない ADR・設計仕様書」のどちらかに載せる。CI（check_feature_index.py）が抜けを落とす。
> 新しい ADR を起案したら、ここにも 1 行足す（または除外の節へ理由つきで載せる）。
>
> 列の意味: 設計書＝`docs/specs/` の設計仕様書（`-` は無し）／コードの場所＝リポジトリ直下からの glob（`、` 区切り・`-` は手順や運用だけで持つコードが無い）。

## 受発注・請求まわり（Sales Anchor コア業務）

| 機能キーワード | 正準 ADR | 設計書 | コードの場所 | 補足 |
|---|---|---|---|---|
| 見積 / 請求 / invoice / quote / PDF / 発行モード / 振込先 / 請求書の宛名 | **ADR-101** ／ ADR-1079 ／ ADR-134 | [quote-invoice](../specs/quote-invoice/README.md) | backend/app/routers/invoices.py、backend/app/routers/quotes.py、backend/app/services/invoice_payment_methods.py | 正規化2テーブル・テンプレSSOT・発行モード。PayPal は Invoicing 方式（2026-06-12 改訂）。振込先は「版」で持つ（ADR-1079）・宛名は billing_display_name を優先（ADR-134） |
| 決済 / 入金確認 / payment / PayPal / Wise / 売上 / P&L | **ADR-104** ／ ADR-101 §6 | - | backend/app/services/paypal_payments.py | 入金確認→受注ステータス遷移・売上計算。ADR-021 も受注報酬計算 |
| 受注 / order / フルフィルメント / 引当 / 発注 | **ADR-102** ／ ADR-021 ／ ADR-071 | [order-management](../specs/order-management/README.md)、[transaction-flow](../specs/transaction-flow/README.md) | backend/app/routers/orders.py、backend/app/routers/purchase_orders.py | 受注管理・発注最適化・ナビ導線 |
| トラブル / 返金 / 受注のトラブル分岐 | **ADR-105** | - | backend/app/routers/orders.py | 受注ステータスの「トラブル」分岐の中身 |
| 発送 / 出荷 / shipping / 同梱 / 配送キャリア / FedEx / DHL / FedEx Rates / Label Validation | **ADR-103** ／ ADR-123 ／ ADR-128 ／ ADR-125 ／ ADR-129 | - | backend/app/routers/shipping.py、backend/app/services/fedex_rates.py | 出荷タイミング・キャリア連携・Integrator 認定。FedEx 見積取得は ADR-125・Label Validation 申請ウィザードは ADR-129（fedex-label-validation-wizard） |
| 為替 / fx / 為替レート SSOT | **ADR-148** | - | backend/app/services/fx_rate.py、backend/app/routers/fx_rate_admin.py | 為替レートは public.app_fx_rates の 1 か所 |
| 売上管理 / 売上ページ / CRM の定義 / 商談 / 案件 / SSOT 背骨 | **ADR-094** ／ ADR-095 ／ ADR-096 ／ ADR-136 | [sales-management](../specs/sales-management/README.md) | frontend/src/pages/sales/**、backend/app/routers/reports.py | 売上管理ページ・「案件」→「商談」のリネーム・SSOT 原則と 2 本背骨・顧客マスタ／CRM データモデル・会社の統計の SSOT（ADR-136 company-stats-ssot） |
| 在庫 / inventory / 商品マスタ / 仕入元 / オファー | **ADR-099** ／ ADR-093 ／ ADR-014 ／ ADR-1014 ／ ADR-143 ／ ADR-1066 ／ ADR-158 | [inventory-management](../specs/inventory-management/README.md) | backend/app/routers/inventory_aggregated.py、backend/app/services/inventory_aggregation.py | 在庫モデル・商品/在庫マスタ分離・Discord 収集。配信行を出す（ADR-1014）・public.inventory は v2 形が正典（ADR-143）・配信シート 15 列（ADR-1066）・商品単位の差分更新（ADR-158） |
| 在庫の閲覧専用ページ / 閲覧者 / viewer / 契約手続き / 商材・プラン・税率 | **ADR-1019** ／ ADR-1061 | [viewer-contract-invoicing](../specs/viewer-contract-invoicing/README.md) | backend/app/routers/viewer.py、backend/app/routers/super_admin_viewers.py | アプリと交わらない閲覧専用アカウント・契約手続き中の状態と請求書 |
| 共用商品の登録 / 必須項目 / 調べたが無い / product_blank_confirmations / 細分類 | **ADR-1020** ／ ADR-155 ／ ADR-156 | [product-master](../specs/product-master/README.md) | backend/app/services/tcg_product_guards.py、backend/app/routers/products.py | 9項目必須・4項目は印で空を認める・全入口で check_required_fields。値の決め方は docs/specs/product-master/registration-rules.md |
| 商品マスタの構造 / products / 商品ID / 商品コード PM- / type_master / work_id / 作品 / 荷姿 / 図鑑取込 | **ADR-083** ／ ADR-084 ／ ADR-090 ／ ADR-1001 ／ ADR-1002 ／ ADR-1006 ／ ADR-1026 ／ ADR-1028 ／ ADR-1030 ／ ADR-1038 | [db-ssot](../specs/db-ssot/README.md)、[master-ssot-migration](../specs/master-ssot-migration/design.md) | backend/app/routers/product_masters.py、backend/app/services/tcg_product_master_svc.py、backend/app/services/product_packagings.py | 種別マスタ・図鑑取込・products の中央化・商品IDの INTEGER 一本化・PM-00001 形式・荷姿の表・細分類は作品の子・tcg_type と type_master_id の廃止 |
| 状態 / コンディション / 区分 / 単位 / PSA / 箱の〆 / ブックレット / condition_vocab | **ADR-1023** ／ ADR-1031 ／ ADR-1035 ／ ADR-1036 ／ ADR-1041 ／ ADR-1073 | - | backend/app/services/condition_vocab.py、backend/app/routers/conditions.py | 状態語の価値順・シングル系の状態・区分ごとの単位・値段で単位を決める・箱の〆（v102） |
| 取り込み / 解析 / パイプライン / Discord 収集 | **ADR-100** ／ ADR-014 ／ ADR-1050 | - | backend/app/services/tcg_line_import_svc.py | 提供元メッセージ→生オファー。一時的に断られた解析の送り直しと、諦めた分の知らせ・月曜の数の知らせは ADR-1050 |
| LINE 解析 / Gemini / 仕入先別プロンプト / 復活止め / 自動切り替え / TCG PARITY | **ADR-085** ／ ADR-154 ／ ADR-1032 ／ ADR-1062 | [line-analysis-tuning](../specs/line-analysis-tuning/README.md) | backend/app/services/gemini_route.py、backend/app/services/line_analysis_v102_svc.py、backend/app/services/tcg_analyzer_svc.py | 仕入先別プロンプト（ADR-085）・GAS 解析の Python 移植（ADR-154）・隠れていた古い行を現行に戻さない（ADR-1032）・Gemini への道の自動切り替え（ADR-1062） |
| 解析の誤り報告 / 自律修正 / analysis_error_reports | **ADR-1025** | [analysis-error-report](../specs/analysis-error-report/README.md) | backend/app/routers/analysis_error_reports.py、backend/app/services/analysis_error_report_svc.py | 報告は本番の表 1 か所・起動は agent-console |
| 買取相場 / buyback / 外部買取店の価格 | **ADR-157** | - | backend/app/routers/buyback_prices.py、backend/app/services/buyback_scraper/** | 外部買取店の価格の定期取得 |
| まとめ売り / N枚セット / bundle_size / バルク / bulk_price_basis_unknown / bundle_unverified | **ADR-1027** ／ ADR-1021 | [bundle-sale](../specs/bundle-sale/README.md) | backend/app/services/v102_bundle_svc.py、backend/app/services/line_analysis_v102_svc.py | 値段を割らずまとめの数を保存・商品名の欄に「N単位セット」。バルク系だけ形 P1・P2 を足す（2026-10-21 追記）。新しい書き方の手順は [`docs/runbooks/bundle-sale-new-wording.md`](../runbooks/bundle-sale-new-wording.md) |
| 社外秘の原文 / 書き写し / confidential-quote-guard / 送る前の見張り | **ADR-1045** ／ ADR-1043 ／ ADR-1029 | - | scripts/agent-hooks/confidential-quote-guard/** | 仕入元の投稿の原文を「」『』で書き写したまま push・PR 本文・コメントで公開の置き場へ送るのを Mac の PreToolUse で止める。表は社外秘フォルダ |

## 顧客・リード・テナント

| 機能キーワード | 正準 ADR | 設計書 | コードの場所 | 補足 |
|---|---|---|---|---|
| 会社 / 顧客情報 / Client Profile / contact / 担当者 / 顧客登録フォーム / 登録フォーム | **ADR-060** ／ ADR-058 ／ ADR-097 ／ ADR-089 ／ ADR-126 ／ ADR-127 | [customer-management](../specs/customer-management/README.md)、[deal-removal](../specs/db-ssot/deal-removal/design.md)、[customer-address-form](../specs/customer-address-form/README.md) | backend/app/routers/companies.py、frontend/src/pages/companies/**、backend/app/routers/registration_tokens.py | 会社はリードの子。作る道は受信箱から送る登録フォームでお客様が登録する道だけ（ADR-097）。画面から手で作る道（顧客情報の「新規登録」ボタン）は直さず撤去する（ADR-097 §6）。リネーム・担当者統合。customers は廃止して companies に一元化（ADR-089）・入力契約 v2（ADR-126）・登録後の変更フォーム（ADR-127 registration-post-forms） |
| リード / lead / lead_channels / 名寄せ / リードの統合 / リードのタブ | **ADR-015** ／ ADR-119 ／ ADR-098 ／ ADR-1049 ／ ADR-059 ／ ADR-107 | - | backend/app/routers/leads.py、backend/app/routers/duplicates.py | リード管理・チャネル・名寄せ。統合は 13 表すべてを付け替え（ADR-1049）・ナビはクリック＋ページ内タブ（ADR-059）・顧客優先度付け（ADR-107） |
| ステータス / status / 不変コード / customer_statuses / ステータスの見た目 | **ADR-1076** ／ ADR-109 ／ ADR-120 | - | backend/app/services/customer_statuses.py、backend/app/routers/customer_statuses.py | 会社と連絡先の状態は public.customer_statuses が正本・不変コード＋i18n ラベル・ステータス→見た目の中央対応表 |
| 既存顧客 / 顧客への自動切り替え / 3 条件 / 登録済み | **ADR-1091** | - | backend/app/services/customer_conversion.py | 既存顧客は 登録済み（既定の請求先）・会社あり・支払い済み の 3 つがそろったときだけ自動で付く。手で付けない・自動で戻さない |
| 受信箱 / inbox / カルテ / Meta Business Suite 風 / 送信ガード | **ADR-108** ／ ADR-110 ／ ADR-022 ／ ADR-061 ／ ADR-063 ／ ADR-064 ／ ADR-143 ／ ADR-1086 ／ ADR-1089 | [inbox](../specs/inbox/README.md) | frontend/src/pages/inbox/**、backend/app/routers/meta_inbox.py | カルテの再編と是正（ADR-108・ADR-110 karte-reference）・Meta 風レイアウトの変遷・送信ガード Phase A（ADR-143 send-guard）・PC 3列の幅は比率＋最大の幅（ADR-1086）・段階ごとのカルテのタブと項目（ADR-1089） |
| 翻訳 / 受信翻訳 / 会話ログ翻訳 / 辞書 / 双方向自動判定 | **ADR-110** ／ ADR-141 ／ ADR-SA-17 | - | backend/app/services/inbound_translation.py、backend/app/services/translation_glossary.py | 会話ログ翻訳サブシステム（ADR-110 sa-translation）・標準入口 enqueue_inbound_translation()・双方向の辞書 2 層 |
| テナント / RLS / schema prefix / tenant_context | **ADR-072** ／ ADR-034 ／ ADR-036 ／ ADR-106 ／ ADR-131 ／ ADR-132 ／ ADR-142 ／ ADR-145 ／ ADR-1067 ／ ADR-1070 ／ ADR-065 ／ ADR-SA-18 ／ ADR-SA-19 | [tenant-rls](../specs/tenant-rls/README.md) | backend/app/services/tenant.py、backend/app/database.py | 書込後 reset_tenant_context・新規テナント migration 自動化・整合性・マルチテナント方針・自動クリア・BackgroundTasks 保護・provisioning の漏れ無し・products の FORCE RLS・public 8 表の RLS・接続の返却時に文脈を消す・asyncpg のキャッシュ無効化・アプリ DB 最小権限・DB セキュリティ検証ゲート |
| 権限 / role / 認証 / Firebase / 共通ロール / 認証ロック | ADR-023 ／ ADR-032 ／ ADR-127 ／ ADR-147 | [auth-roles](../specs/auth-roles/README.md) | backend/app/auth/**、backend/app/routers/roles.py | 認証3層同期・カスタム認証ドメイン・認証ロック巻き添えの解消（ADR-127 auth-lockout）・共通6ロール |
| スタッフ / 人の正本 / users.id / 自己登録 / 招待リンク | **ADR-1008** ／ ADR-1068 | - | backend/app/routers/staff.py、backend/app/routers/staff_join.py、backend/app/services/staff_join.py | 「人」の正本は public.users.id 一本・スタッフの自己登録 |
| password_hash / bcrypt / 認証情報 DB 保存 | **ADR-1013** | - | backend/app/auth/** | password_hash 列廃止（Firebase 専一）は ADR-138（置き換え済み）。列削除 recon では ORM モデル定義確認必須。現行は ADR-1013 |
| ログイン / パスキー / WebAuthn / 生体認証 / パスワード再設定 / 自社認証 | **ADR-1013** | [auth-login](../specs/auth-login/README.md) | backend/app/routers/auth.py、backend/app/services/auth_mail.py | Firebase から自社サーバーへ移行・Argon2id・パスキー・再設定メール。ADR-138 を覆す |
| 更新トークン / 自動ログアウト / 使わない日数 / ログインし直し | **ADR-1084** | - | backend/app/auth/self_tokens.py | 最後の取り替えから 7 日使わなければ更新を断る。30 日の絶対期限・入館証 15 分・機械の覚え 180 日は変えない |
| Claude in Chrome / ブラウザ操作 / 画面の確かめ / 外部 GUI / 区分 | **ADR-1085** | [browser-operation-delegation](../specs/browser-operation-delegation/README.md) | - | 区分1は Opus だけ・区分2は同意票・区分3（支払い等）は PO 本人。PreToolUse の見張りで機械で守る（Draft） |
| 新しい機械のログイン承認 / 回数止め / 接続元 IP / 期限切れの札 | **ADR-1055** ／ ADR-1063 ／ ADR-1083 | [client-ip](../specs/client-ip/README.md) | backend/app/routers/login_approvals.py、backend/app/routers/tenant_login_requests.py、backend/app/client_ip.py、backend/app/auth/dependencies.py | いつもの機械で番号を選んで許可・会社のオーナーが自社社員の機械を許可・期限が切れただけの札は回数止めに数えない（ADR-1083） |
| カレンダー / 予定 / Google カレンダー / sync-mode / 取り込み / Google Meet / meet_url / 時間割 / 予定の色 | **ADR-1057** ／ ADR-1059 ／ **ADR-1060** ／ ADR-1018 ／ ADR-1075 ／ ADR-1065 ／ ADR-1074 ／ ADR-1081 | [schedule](../specs/schedule/README.md) | backend/app/routers/calendar.py、backend/app/services/calendar_service.py、backend/app/services/event_colors.py | 接続は会社で1つ・送るのはつないだ本人の予定だけ・Google の予定を直接扱う口は本人だけ・取り込みは双方向のとき15分おき（ADR-1059）・Meet は本人の予定だけ、URL は calendar_events.meet_url の1か所（ADR-1060）・繰り返しは元の行の recurrence_rule 1 か所で表示のときに広げる（ADR-1075・Proposed）・FullCalendar v6 の金型 CalendarView（ADR-1065）・窓いっぱいの編集画面 EditorPage（ADR-1074）・予定の色は Google の 24 色（ADR-1081） |
| 管理者の2段階の確認 / 二段階認証 / MFA / TOTP / 認証アプリ / 新しい機器の承認 | **ADR-1048** | - | backend/app/routers/login_approvals.py | 管理者はパスキーかパスワード＋6桁が必須・初めての機器はいつもの機器で番号を選んで承認 |
| 管理センター / プロフィール / アカウント設定 | - | [management-center](../specs/management-center/README.md)、[profile-account-settings](../specs/profile-account-settings/README.md) | frontend/src/pages/account-settings/** | 設計仕様書だけで決める画面（対応する ADR は無い） |
| チームボード | - | [team-board](../specs/team-board/README.md) | - | 設計仕様書だけで決める画面（対応する ADR は無い） |
| 添付ファイル / attachment | - | [attachment-storage](../specs/attachment-storage/README.md) | - | 添付ファイルの保管の設計仕様書（対応する ADR は無い） |
| ファネル / ダッシュボード / 目標対比 / KGI ダッシュボード | **ADR-138**（funnel-dashboard-stage1） ／ ADR-139 | [dashboard](../specs/dashboard/README.md) | backend/app/routers/dashboard.py、frontend/src/pages/dashboard/**、frontend/src/api/funnel.ts | ファネル型目標対比ダッシュボードの第1弾（バック・フロント）。ADR-138 の password_hash 版は除外の節 |

## 横断・運用・プロセス

| 機能キーワード | 正準 ADR | 設計書 | コードの場所 | 補足 |
|---|---|---|---|---|
| i18n / 国際化 / ja.json / en.json | **ADR-027** | - | frontend/src/locales/** | 全 UI 文字列 `t()` 経由・キー同期必須 |
| LINE 書き出しアプリ / 端末自動化 / 省電力 / AlarmManager / 電池最適化 / ユーザー補助 / 記録の保持 | **ADR-1090** | - | tools/line-auto-export-app/** | 端末アプリは省電力の間引きを前提に作る。除外の外れと空振りを記録し、設定画面から利用者が戻せる。実測値と Android の一般仕様を区別し回数の具体値に依存しない。記録は文字だけ（画面画像・音声・動画は保存しない）・保持は 90 日 |
| リリース / release PR / develop→main / branch protection | **ADR-050** | [branch-operations](../specs/branch-operations/README.md) | - | merge commit のみ（squash 禁止＝back-merge 構造バグ防止）・Ruleset 15777895 |
| リリース相乗り防止 / 危険変更の develop 入口関所 / develop=出荷可能 | **ADR-135** | - | - | 危険変更(migrations/deploy.yml/scripts)は PO GO まで feature で待機・develop マージ＝本番投入可宣言。CODEOWNERS/PRテンプレ済、B（B-2 方式）・C（main 必須チェック追加）・D・E も実施済み（ADR-135:32-60） |
| 自動マージ / human-in-the-loop / develop 自動 merge | **ADR-056** | - | - | develop は AI 自動 merge・main は人間。通知集約 |
| 並行開発 / worktree / AEON / Evidence | **ADR-086** ／ ADR-074 ／ ADR-114 | [dev-continuity](../specs/dev-continuity/README.md)、[reaper-auto-cleanup](../specs/reaper-auto-cleanup/README.md) | scripts/new-worktree.sh、scripts/cleanup-worktree.sh | 複数エージェント並行開発の標準化・Worktree 強制でエージェント PR 混入防止（ADR-074）・worktree ライフサイクルの自動化（ADR-114） |
| 標準ワークフロー / SOP / process-artifacts gate | **ADR-121** ／ ADR-112 | [recon-standard](../specs/recon-standard/README.md)、[STANDARD-WORKFLOW.md](../STANDARD-WORKFLOW.md) | scripts/check-process-artifacts.js | KGI→recon→設計の関所 |
| 設計仕様書 / あるべき姿 / 仕様書索引 | **ADR-121** | [specs/README.md](../specs/README.md)、[sales-anchor-app](../specs/sales-anchor-app/README.md)、[doc-parent-child](../specs/doc-parent-child/README.md) | - | 領域→設計仕様書の地図。索引に載る領域に触れる開発は仕様書を先に読む |
| Claude Code 運用ガードレール / SessionStart hook | **ADR-042** | - | .claude/hooks/** | 運用ガードレール・hook 整備 |
| CLAUDE.md / AGENTS.md / 入口の行数 / 目次 / 指示文書の構成 | **ADR-1040**（Accepted） ／ ADR-076 | [doc-agenda-nav](../specs/doc-agenda-nav/README.md)、[doc-estate](../specs/doc-estate/README.md) | scripts/ci/check_doc_index.py | 入口→目次→章→末端。本文の正本は AGENTS.md・入口の上限90行（ADR-076 のルート上限と命名を一部改訂） |
| 機能→ADR 索引 / 要件の書類を作業の場面で見せる / 読まずに不具合と判定しない | **ADR-1040**（Accepted） ／ ADR-121 | [requirement-library](../specs/requirement-library/README.md) | scripts/ci/check_feature_index.py、scripts/ci/feature_index_lib.py | この索引を全件網羅にし漏れを CI で止める。決まりのある場所を開いたら行を示し、要件を読まずに「不具合」と書いたら止める |
| 担当者アイコン / 英語名必須 / Discord webhook 送信 / avatar | **ADR-159** ／ ADR-091 | - | backend/app/services/staff_avatar.py、backend/app/services/discord_webhook_sender.py | Discord 返信を担当者の名（given_name_en）とアイコンで送る・Bot 名義では送らない（便A=アイコン+英語名必須 / 便B=webhook 送信） |
| Discord ゲートウェイ / Discord Bot / リアクション / サーバー管理 | **ADR-009** | [discord-reaction](../specs/discord-reaction/README.md)、[discord-server-management](../specs/discord-server-management/README.md) | backend/app/discord_gateway/** | Discord Gateway Worker |
| 24時間保守運用 / 障害記録 / 応急処置 / routines / アラート札 page・auto・ticket | **ADR-1012**（Proposed） ／ ADR-115 | [ai-ops-247](../specs/ai-ops-247/README.md)、[discord-ops-intake](../specs/discord-ops-intake/README.md)、[mac-jobs-watch](../specs/mac-jobs-watch/README.md) | - | 経路の正本は Alertmanager・障害記録の正本はアプリ DB・AI は PR で修理（ADR-136 の GO）・C は予備 |
| Meta / Facebook / Instagram / Webhook / ドメイン認証 / 撮影用データ / 英語UI | ADR-024 ／ ADR-025 ／ ADR-041 ／ ADR-026 ／ ADR-016 ／ ADR-017 ／ ADR-018 ／ ADR-019 ／ ADR-037 | - | backend/app/routers/meta.py、backend/app/services/meta_graph.py | 連携整備・フォールバック・mid TEXT 化・ドメイン認証タグ（ADR-016/017/018）・Instagram 送信（ADR-018）・撮影用データと英語 UI の一時デプロイ（ADR-019）・ページ接続経路の調査（ADR-037） |
| クラウドの相談係 AI / Discord 発の保守 / 個人の値を伏せたビュー ai_cloud / 解除申請 | **ADR-1052**（Accepted） ／ ADR-1024 ／ ADR-1042 ／ ADR-1039 | - | backend/app/routers/ops_case.py | Discord は合図だけ・外へ出さない・中身は申請して Opus が許可・case-api だけに届く |
| Discord の知らせを AI が読む / 読むだけの鍵 / SA Bug Intake の権限 | **ADR-1088**（Accepted） ／ ADR-1039 ／ ADR-079 | [discord-ops-intake](../specs/discord-ops-intake/README.md) | - | 受付の Bot に知らせの3部屋の「見る」「履歴を読む」だけを足す・鍵の写しは ADR-079 の置き場（ADR-1039 Decision 7 の例外）・読めないときは強い鍵に切り替えず止める |
| アプリ内チャット秘書 / 決まり帳 / 予定のカルテ / 声 / 音声入力 / TTS / LIVE の声の会話 | **ADR-1056** ／ ADR-1077 ／ ADR-1078 ／ ADR-1080 ／ ADR-1082 ／ ADR-1087 | [secretary-chat](../specs/secretary-chat/README.md) | backend/app/services/secretary_*.py、backend/app/routers/assistant.py | AI に会社のデータも道具も渡さず頼みの文を決まった形にする・決まり帳は人が承認してから効かせる・予定の頼みは予定と決める・声の読み上げと聞き取り |
| AI の担当 / モデル割り当て / LLM 使用量 / llm_usage_events | **ADR-1058** ／ ADR-1004 | - | backend/app/services/ai_assignment.py、backend/app/services/llm_budget.py | 担当は DB の 1 か所・LLM 使用量台帳 |
| 画面のデザイン / テーマ / ダークモード / ロゴ / デザイントークン / ブランドアセット | **ADR-033** ／ ADR-066 ／ ADR-067 ／ ADR-068 ／ ADR-073 ／ ADR-013 | [design-system](../specs/design-system/README.md)、[design-tokens-ssot](../specs/design-tokens-ssot/README.md) | frontend/src/tokens.css | ライト/ダーク切替・サイドバーロゴの白反転・トークン強制・ブランドアセット方針・KGI ルーブリック・ロゴと favicon の統一 |
| 画面の共通部品 / hub-shell / Modal / SubMenu / モバイルナビ / UI ガバナンス | **ADR-144** ／ ADR-087 ／ ADR-122 ／ ADR-149 ／ ADR-140 | - | frontend/src/hub-shell.css、frontend/src/components/** | 共通部品の遵守・共通シェルレイアウト・Modal への移行・SubMenu の SSOT 集約・下部タブバー。手順は docs/CC_UI_GOVERNANCE.md |
| 画面のデータ取得 / キャッシュ / 変わった合図 / 失敗時の文 / API パス / 例外の中身 | **ADR-1054** ／ ADR-1016 ／ ADR-1071 ／ ADR-152 | [db-error-detail](../specs/db-error-detail/README.md) | frontend/src/lib/api.ts、frontend/src/pages/inbox/discordSendError.ts、frontend/src/features/discord-connect/discordConnectError.ts、backend/app/realtime/** | TanStack Query の 1 か所・書込成功で合図を送る・失敗の文は「何が起きたか＋次にすること」（ADR-1071）・フロントの API パスに /api/v1 を含めない |
| LP / ランディングページ / Astro / 検索に載せない | **ADR-1044** ／ ADR-046 ／ ADR-047 ／ ADR-049 ／ ADR-054 ／ ADR-057 | - | lp/src/** | LP は Meta 申請用（ADR-1044）・LP の再設計とコピーと構成の変遷 |
| JST / 今日の基準 / 日付 | **ADR-151** | - | backend/app/services/time.py | バックエンド全域で「今日」の基準を JST に統一 |
| 監査ログ / audit | **ADR-129** | [get-access-audit](../specs/get-access-audit/README.md) | backend/app/services/audit.py | 監査ログのカバレッジ補完（ADR-129 audit-log-coverage） |
| データ保全 / バックアップ / 時点復旧 | **ADR-153** | [data-durability](../specs/data-durability/README.md) | scripts/backup.sh | 時点復旧10分・復旧半日・3拠点 |
| Python のバージョン / 3.12 / 3.14 | **ADR-1022** | - | backend/pyproject.toml、backend/Dockerfile | 3.12 のまま作り続け、2027 年 10 月までに本番ごと 3.14 へ |
| 設計図書サイト / design site | **ADR-134** | - | scripts/design-site/** | アプリ VPS の静的配信＋Basic 認証（ADR-134 design-site-delivery） |
| 外部状態の検証 / 外部 API スモーク / 本番の画面点検 / 開く速さ / QA Smoke | **ADR-035** ／ ADR-038 ／ ADR-1000 ／ ADR-1017 ／ ADR-1051 ／ ADR-1053 | - | .github/workflows/qa-smoke.yml、.github/workflows/prod-ui-check.yml、.github/workflows/external-api-smoke.yml | 外部状態 6 システム×5 層・QA Smoke・実 Sandbox スモーク必須・smoke 認証は最小権限・本番の画面点検 |
| AI 開発フロー / claude-pipeline / Codex / Generator / Evaluator / 外部プランナー | **ADR-011** ／ ADR-012 ／ ADR-039 ／ ADR-040 ／ ADR-048 ／ ADR-051 ／ ADR-053 ／ ADR-055 ／ ADR-081 ／ ADR-082 ／ ADR-113 ／ ADR-150 ／ ADR-999 | [agent-complete-design](../specs/agent-complete-design/README.md)、[design-partner-loop](../specs/design-partner-loop/README.md)、[lessons-guard](../specs/lessons-guard/README.md) | scripts/codex-exec.sh、.claude/agents/** | 役割分担・3者協調・What/How 分離・コードの現状把握・自動化・Codex フォールバック（ADR-082 generator-executor）・2モード開発フロー・エージェント担当領域の窓・design-review-gate 廃止（ADR-081 remove-design-review-gate）・ADR-999 はパイプライン動作テスト用 |
| GO 委任 / 権限の自律保守 / 危険操作の同意 / 台帳 / 決まりの台帳 / ガード | **ADR-1003** ／ ADR-136 ／ ADR-1011 ／ ADR-1015 ／ ADR-1033 ／ ADR-1034 ／ ADR-1047 ／ ADR-1072 | [rule-enforcement](../specs/rule-enforcement/README.md)、[process-hardening](../specs/process-hardening/README.md)、[ledger-guard](../specs/ledger-guard/README.md)、[local-hooks-ssot](../specs/local-hooks-ssot/README.md) | scripts/permit-danger.sh、scripts/ci/check_rule_registry.py | GO は Opus へ常時委譲（例外あり）・許可の自律保守・B 区分は PO 承認なし・会話の同意票・Opus の権限台帳・決まりは台帳が正本・AI が足した見張りの記録・cc ボットの GitHub 名義（ADR-136 cc-bot-github-identity） |
| secrets / GitHub Secrets / 権限と秘密の SSOT | **ADR-075** | [secrets-permission-ssot](../specs/secrets-permission-ssot/README.md) | .github/workflows/secret-scan.yml | GitHub Secrets 一元管理 |
| API 型契約 / OpenAPI / 配線台帳 | **ADR-1010** | - | frontend/package.json | OpenAPI→TypeScript の型契約と配線台帳の自動生成 |

## インフラ / デプロイ / nginx

| 機能キーワード | 正準 ADR | 設計書 | コードの場所 | 補足 |
|---|---|---|---|---|
| nginx / inode / bind mount / force-recreate / deploy / git reset | **ADR-137** ／ ADR-130 | - | nginx/** | git reset 後の inode ズレ対策。nginx/** 変更時のみ conditional force-recreate（git reset 後・bootstrap 前）。reload ポリシー（ADR-130） |
| 502 / resolver / backend IP / proxy_pass | **ADR-137** ／ ADR-133 | - | nginx/** | PR-B 相当は ADR-133 で実装済み。ADR-137 では解消済みとして統合記録 |
| デプロイ / blue-green / migration の流し方 / ロック待ち / 多重実行 / デプロイスタンプ | **ADR-045** ／ ADR-082 ／ ADR-092 ／ ADR-116 ／ ADR-129 ／ ADR-1005 ／ ADR-1007 ／ ADR-1037 ／ ADR-044 | [build-on-github](../specs/build-on-github/README.md) | scripts/blue-green-cutover.sh、scripts/run_all_migrations.sh、scripts/deploy-db-precheck.sh、.github/workflows/deploy.yml | 本番の入れ替え・migration は構造の変更だけ 1 回だけ流す・ロック待ちを 1 秒で諦める（ADR-1037）・フロントのみのデプロイでは migration を飛ばす（ADR-082 deploy-skip）・GitHub Actions のランタイム追従（ADR-129 github-actions-node） |
| runner / self-hosted / ラベル / VPS runner / 仮想マシン試験 / Colima | **ADR-029** ／ ADR-078 ／ ADR-111 | [vm-test-on-gha](../specs/vm-test-on-gha/README.md)、[colima-idle-stop](../specs/colima-idle-stop/README.md) | .github/workflows/runner-label-lint.yml | Mac 2 台体制・VPS runner 登録・専用ラベルで環境分離 |
| 監視 / Uptime Kuma / Grafana / Prometheus / 監視 VPS / GitHub Actions メトリクス / SOP ヘルス | **ADR-069** ／ ADR-070 ／ ADR-077 ／ ADR-079 ／ ADR-080 ／ ADR-081 ／ ADR-124 | [server-resource-optimization](../specs/server-resource-optimization/README.md) | monitoring/prometheus/**、docker-compose.monitoring.yml | 監視スタックの分離・最終運用設計（ADR-081 monitoring-vps）・Claude Code 専用の読み取りアクセス・定量監視ダッシュボード |

> **使い方（recon）**: ①この表で領域の正準 ADR を引く → ②`git grep -i "<keyword>" docs/adr/` で取りこぼしを確認 → ③該当 ADR を read してから設計に入る。該当が無ければ「既存設計なし（grep 済み）」と recon.md に明記する。

## 索引に載せない ADR・設計仕様書

| 番号・ファイル名・フォルダ | 理由（どれに置き換わったか） |
|---|---|
| ADR-020 | Superseded。recording/english-ui の本番デプロイ実行は完了済みで、現行は ADR-019（Meta審査期間中の英語UI一時デプロイ）の行に集約 |
| ADR-028 | Superseded。置き換え先は scripts/setup_review_tenant.py と docs/META_APP_REVIEW_PRE_RECORDING_CHECKLIST.md（ADR ではない） |
| ADR-1009 | Superseded。置き換え先は ADR-1012（24時間保守運用の行） |
| ADR-138-remove-password-hash.md | Superseded。password_hash 列廃止は ADR-1013（自社認証）に置き換え。同じ番号の ADR-138-funnel-dashboard-stage1.md は生きていてファネルの行にある |

## ADR 候補バックログ（未起案）

| 課題 | 概要 | 起案優先度 |
|---|---|---|
| ADD 系 migration の expand-contract 運用 | `ADD COLUMN NOT NULL` など新列追加 migration は blue-green cutover **前**に実行される（deploy.yml 構造）。旧コンテナが新列を知らない状態で列が追加されると、RLS/VIEW/trigger 依存によっては旧コンテナが壊れる可能性がある。対策候補: ①cutover 前後で migration を pre/post に分割、②ADD 系は nullable で追加して NOT NULL は後 PR で付与、③新列は ORM 側でオプショナル定義してから追加。構造保証として ADR 化する | 中 |
