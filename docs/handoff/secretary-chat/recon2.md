# 現状の調べ（第2版）— 秘書チャットを「AI は文を決まった形に直すだけ」に改める前提の確認

基準: origin/main = `508e86036b5b1ab519d49cd3edde888986ba6e22`（2026-10-31 取得）
作業場所: `release/secretary-chat-recon2`（`scripts/new-worktree.sh` で origin/main から作成）
生の出力・公式資料の引用: [recon2-raw.txt](recon2-raw.txt)（以下「raw §X」）
旧設計: `origin/release/secretary-chat-recon` の `docs/handoff/secretary-chat/design.md`（AI が会社データを読む前提。本調査で前提を改める）

注意（実行環境）:
- 起動前の点検 `./scripts/dev/executor-preflight.sh` は `FAIL`（クラウドに `gh` が無く、GitHub API 到達と `gh auth` が失敗）。`git fetch`・`git push` は使えるため、深追いせず続行した。
- 製品コード・DB・設定は変更していない。本番には接続していない。パスは全て作業場所（origin/main 基準）の相対パス。

---

## A. Claude Code CLI（公式 https://code.claude.com/docs/ ）

| 項目 | 結論 | 根拠（URL と引用） |
|---|---|---|
| 非対話 `-p` | ある | cli-reference「`--print`, `-p` Print response without interactive mode」。headless「`claude -p "What does the auth module do?"`」 |
| 出力の形 | `--output-format json` で結果・session ID・メタデータ。`total_cost_usd` と model 別内訳も入る | headless「`json`: structured JSON with result, session ID, and metadata」「the response payload includes `total_cost_usd` and a per-model cost breakdown」。テキスト本体は `result` 欄 |
| 決まった JSON で答えさせる | **ある**。`--json-schema`（print モード限定）。答えは `structured_output` 欄 | cli-reference「`--json-schema` Get validated JSON output matching a JSON Schema after the agent completes its workflow (print mode only)」。headless「with the structured output in the `structured_output` field」。注意: 「If a run ends without valid structured output ... the response has no `structured_output` field. Before your script uses `structured_output`, check that the field is present.」＝欄の有無を必ず検査。`format` は注釈扱いで強制されない |
| 全部の道具を無効に | **ある**。`--tools ""`。MCP の道具には効かないので `--disallowedTools "mcp__*"` も併用。`--disallowedTools "*"` で全道具を外す書き方も記載 | cli-reference「`--tools` ... Use `""` to disable all」「The flag doesn't affect MCP tools; to deny those too, use `--disallowedTools "mcp__*"`」「`--disallowedTools` ... `"*"` removes every tool」。※「`""` removes it [EndConversation] only when no MCP tools remain」とあり、EndConversation だけは条件付き |
| `--strict-mcp-config` | ある | 「Only use MCP servers from `--mcp-config`, ignoring all other MCP configurations」。`--mcp-config` を渡さなければ MCP ゼロにできる（推測にならない範囲: 記載文からの読み取り。実機で未検証） |
| `--setting-sources` | ある | 「Comma-separated list of setting sources to load (`user`, `project`, `local`)」 |
| `--no-session-persistence` | ある（print モード限定） | 「sessions are not saved to disk and cannot be resumed. Print mode only」 |
| `--max-turns` | ある（print モード限定） | 「Limit the number of agentic turns (print mode only). Exits with an error when the limit is reached. No limit by default.」 |
| `--model` | ある | 「Sets the model ... alias such as `sonnet`, `opus`, `haiku`, or `fable`, or a model's full name」 |
| `--bare` | ある。**ただし月額契約のログインを読まない** | headless「Set `ANTHROPIC_API_KEY` ... because bare mode doesn't use your subscription login」、authentication「Bare mode does not read `CLAUDE_CODE_OAUTH_TOKEN`」。→ 月額契約で動かすなら `--bare` は使えない。代わりに `--tools "" --disallowedTools "mcp__*" --strict-mcp-config --setting-sources ""`（空指定が許されるかは**未確認**）等で絞る |
| `--bare` 無しの `-p` の注意 | プロジェクトの hooks・`.mcp.json` を読む | headless「Without `--bare`, a `-p` session runs the hooks in a project's `.claude/settings.json` and connects the servers in its `.mcp.json`」→ 専用容器の作業ディレクトリは空にしておく |
| 権限 | v2.1.302 以降、`-p` は何も指定しないと Manual モード（承認が要る呼び出しは拒否） | headless「`claude -p` runs start in Manual mode when nothing sets a permission mode」。`--permission-mode dontAsk` で「denies every call that would otherwise prompt」 |
| 月額契約でログインを保つ | `claude setup-token`（1年有効の OAuth トークン）→ 環境変数 `CLAUDE_CODE_OAUTH_TOKEN` | authentication「generate a one-year OAuth token with `claude setup-token`」「It does not save the token anywhere; copy it and set it as the `CLAUDE_CODE_OAUTH_TOKEN` environment variable」「requires a Pro, Max, Ultra, Team, or Enterprise plan. It can only make model requests」 |
| 優先順位の罠 | `ANTHROPIC_API_KEY` が環境にあると `-p` では**必ずそちらが使われる** | authentication「In non-interactive mode (`-p`), the key is always used when present」→ 容器に API キーを入れない |
| 認証切れの現れ方 | 実行内の失敗は stdout に結果として出る | headless「When a failure happens inside the run, such as missing authentication, Claude Code prints the failure as the result on stdout」、authentication「`Login expired · Please run /login`」 |
| Linux のログイン保存先 | `~/.claude/.credentials.json`（0600）。`CLAUDE_CONFIG_DIR` で場所変更可 | authentication「On Linux, credentials are stored in `~/.claude/.credentials.json` with file mode `0600`」 |
| 必要な通信先 | `api.anthropic.com`（API）・`claude.ai`・`platform.claude.com`（OAuth の更新。claude.ai 契約でも必要）。任意: `downloads.claude.ai`（自動更新）・datadog 2 ホスト（`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` で止める） | network-config「Network access requirements」表。SOCKS プロキシ非対応 |
| Docker への入れ方 | 公式の導入は `curl -fsSL https://claude.ai/install.sh \| bash`（推奨）または `npm install -g @anthropic-ai/claude-code`（Node.js 22 以上。バイナリ自体は Node 不要）。apt/dnf/apk の署名付き配布もある | setup ページ。**Docker 専用の手順は setup ページには無い**（devcontainer ページへのリンクが authentication ページにあるが本調査では未読＝未確認） |
| Linux の必要メモリ | 記載は「4 GB+ RAM」のみ。1 回の `-p` 実行の使用量・容器の下限の記載は**見つからない（未確認）** | setup「Hardware: 4 GB+ RAM, x64 or ARM64 processor」。旧設計の「0.25〜0.29GB」はクラウドでの測定値で公式記載ではない |
| 月額契約の利用規約 | 本調査の範囲外（PO 指示で調べない） | — |

注: 公式 Alpine 手順は musl 用に `libgcc libstdc++ ripgrep` が要る。使う基底イメージ次第（未決）。

## B. `llm_budget.py` の purpose・sdk

- コード側の固定: `backend/app/services/llm_budget.py:159-166`（purpose 6 種）、`:171`（sdk は `google-genai`・`google-generativeai` の 2 種）。検査は `:242-245`（外れると `ValueError`）。
- **DB 側にも CHECK 制約がある**: `migrations/20260930_150000_create_llm_usage_events.sql:46-53`（`llm_usage_events_purpose_check`・`llm_usage_events_sdk_check`）。他の migration でこの制約を変えたものは**無い**（grep 結果は作成 migration とテストのみ。raw §B-4）。
- よって `secretary_chat` を purpose に、`claude-code-cli` 等を sdk に足すには、**コード（frozenset）と DB の CHECK の両方**の変更が要る（CHECK 変更は新しい migration。冪等に直す前例は本調査では未確認）。
- 列（同 migration `:25-44`）: `id UUID`・`occurred_at`・`purpose TEXT NOT NULL`・`tenant_id INTEGER`・`model TEXT NOT NULL`・`sdk TEXT NOT NULL`・`prompt_tokens`・`cached_content_tokens`・`candidates_tokens`・`thoughts_tokens`・`tool_use_prompt_tokens`・`total_tokens`・`cost_usd NUMERIC(12,6)`・`extraction_attempt_id`・`extraction_shadow_run_id`・`discord_inbound_message_id`・`source_ref TEXT`・`backfilled BOOLEAN`。列名は Gemini の用語（`cached_content_tokens`・`thoughts_tokens`）で、Claude CLI の `json` 出力の `usage` と 1 対 1 で合うかは**未確認**。
- 付随: `migrations/20261024_100300_create_ai_cloud_views.sql:141-142` が `purpose`・`sdk` を「値が限られる列」として許可扱いにしている。値が増える場合、この一覧の前提（制約で限られる）は保たれるが、一覧自体の更新要否は**未確認**。

## C. `tenant_features` の入れ方

- 表: `migrations/20260627_120000_add_tenant_features_table.sql:6-13`（`tenant_id INTEGER`・`feature_key TEXT`・`enabled BOOLEAN DEFAULT TRUE`・`created_at`・主キー `(tenant_id, feature_key)`）。RLS あり（`:15-37`、自テナント行 + 運営者は全件）。
- **行を入れる前例は migrations・backend・scripts・docs のどこにも無い**（grep 結果が空。raw §C-2）。読む側は `backend/app/auth/dependencies.py:652-682`（`require_feature`。まだどこからも使われていない＝旧 recon と同じ）と `backend/app/routers/roles.py:147-154`（`/me/permissions` が `enabled_features` として返す）。
- `feature_key` の命名の決まり: **見つからない**（表の列は自由な TEXT で、`ai_cloud` の許可一覧でも「値の決まりが無く自由に入る列」扱い。`migrations/20261024_100300_create_ai_cloud_views.sql:262`）。docstring の例は `inventory_v2`（`dependencies.py:658`）＝小文字+アンダースコアの傾向（観測のみ）。
- テナントの id と schema 名: schema は `tenant_{id:03d}`（`backend/app/auth/dependencies.py:301`、`backend/app/services/tenant.py:1658-1660`）。したがって id=1 → `tenant_001`、id=4 → `tenant_004` という**規則上の対応**はコードで確認できる。`tenant_004` は HIGH LIFE JPN 専用（`migrations/20260831_110000_create_tcg_analysis_tables_t004.sql:7`、`backend/app/services/tcg_distribution_svc.py:1115` の `tenant_id=4,  # tenant_004`）。
- **未確認**: 「テナント 001 = どの会社か」「tenants の本番の行（tenant_code・tenant_name）」。migrations・seed に `INSERT INTO public.tenants` の本番行は見つからず（テストの bootstrap のみ: `backend/tests/rls_bootstrap.py:222`）。`Tenant` モデルは `backend/app/models.py:8-17`（`id`・`tenant_name`・`tenant_code`・`is_active`）。

## D. PO が 001 と 004 の両方をどう使うか／「PO 本人だけ」

- **users.tenant_id は 1 人 1 つ**: `backend/app/models.py:26`（`nullable=False`、単一列）、`email` は一意（`:29`）。リクエストごとの会社は `get_current_tenant` が `user.tenant_id` から決める（`backend/app/auth/dependencies.py:262-277`、「URLパラメータからtenant_idを受け取ることは絶対にしない」）。
- **テナントを切り替える仕組みは見つからない**: `switch tenant`・`impersonate`・`X-Tenant` 等の検索は backend・frontend とも該当なし（raw §D-5）。super admin（`public.users.is_super_admin`、`dependencies.py:516-545`）は別の入口（`/super-admin/*`）を持つが、`get_current_tenant` は super admin でも `user.tenant_id` を使う（`:276`）。
- → 「PO が 001 と 004 の画面を両方使う」は、(a) 001 と 004 に別々のログイン（別メール）があるか、(b) 1 人が super admin で運営用の口を使うか、**どちらか本調査では判別できない（未確認。本番の users が必要）**。設計は「各テナントごとに 1 人の PO のユーザーがいる」場合と「1 人しかいない」場合の両方を考える必要がある。
- 「PO 本人だけ通す」を今の仕組みで作る候補（行番号付き）:
  1. **`require_super_admin`**（`dependencies.py:516-545`）: `is_super_admin` が true の人だけ。PO が super admin かは**未確認**。運営者全員に及ぶ可能性。
  2. **owner ロール**（`backend/app/auth/system_roles.py:8,17-19,29-33`）: `owner` は全権限、`admin` は `system.manage` 以外。`system.manage` を要求すれば owner だけ通せる（`system_roles.py:10`、`migrations/002_add_permissions_master.sql:25`）。`require_permission("system.manage")` の形（`dependencies.py:623-648`）。owner が複数いる会社では PO 以外も通る。
  3. **新しい権限キー**（例 `secretary.use`）を `public.permissions` に足し、PO のロールにだけ付ける。権限キーの足し方の前例は `migrations/002_add_permissions_master.sql`。owner には自動で届く（`system_roles.py:3-4`）ので、owner 限定にはならない点に注意。
  4. **`tenant_features`**（`require_feature`、`dependencies.py:652`）: 会社単位の入口。001・004 だけ `enabled=true` にできる。**人単位ではない**ので、1 と 2 または 3 と併用が必要。
  5. **ユーザー id／メールの固定一覧**: 前例は閲覧者用の許可一覧（`backend/app/auth/viewer_allowlist.py`）があるが、スタッフ用で使われている例は未確認。
  - フロントの出し分けは `/me/permissions`（`roles.py:144-174`）の `permissions`・`is_super_admin`・`is_tenant_admin`・`enabled_features` を `usePermissions`・`useSuperAdmin`（`frontend/src/hooks/useSuperAdmin.ts`）が読む形。印の表示と backend の許可は**両方**に同じ条件が要る（画面だけでは守りにならない）。

## E. 名前から id に直す検索／請求書・予定の形

- 会社: `GET /companies?search=`（`backend/app/routers/companies.py:291-319`。`company_code`・`name`・`normalized_name`・`billing_display_name` を `ILIKE`、権限 `customers.view`）。
- 担当者: `GET /contacts?search=&company_id=`（`backend/app/routers/contacts.py:258-283`。`contact_code`・`display_name`・メール・電話・`surname`・`given_name` を `ILIKE`、権限 `customers.view`）。
- 品物: `GET /products?search=`（`backend/app/routers/products.py:133-232`。空白区切りで分割した各語を複数列に `ILIKE`、一致度で並べ替え、権限 `products.view`）。専用の service 関数は無く、いずれも **router 内の SQL**（service に切り出されていない。再利用するなら関数化が要る。service 側の在庫検索は `backend/app/services/inventory_search.py` に別にあるが、請求書の品物と同じ表かは**未確認**）。
- 請求書 `POST /invoices`（`backend/app/routers/invoices.py:337` 周辺、権限 `invoices.create`）の本文 `InvoiceCreate`（`backend/app/schemas/invoice.py:39-51`（第3版で行番号を直した））:
  - 必須: `company_id`（int ≥1）・`contact_id`（int ≥1）・`items`（1 件以上）。
  - 任意: `currency`（既定 `JPY`）・`shipping_fee`・`tax_amount`・`exchange_rate_jpy`・`exchange_rate_usd`・`payment_method`・`due_date`（date）・`notes`（≤5000）。
  - `items[]` = `InvoiceItemInput`（`:27-36`）: **必須** `product_name`（1〜255 文字）・`quantity`（int ≥1）・`unit_price`（Decimal ≥0、小数 2 桁）。任意 `product_id`（int ≥1 または null）・`name_en`・`condition`（≤50）・`unit`（≤20）・`weight`。→ 品物は `product_id` が無くても、**名前・数量・単価があれば作れる**（id への解決は必須ではない）。ただし単価は AI が決めてはならない値（決め方は別途要確認）。
- 予定 `POST /calendar/events`（`backend/app/routers/calendar.py:336-361`）の `CreateEventBody`（`:102-109`）: `title: str`・`start_datetime: str`・`end_datetime: str`（以上必須）・`calendar_type: str = "shared"`（`shared` か `personal` 以外は 422、`:344`）・`description`・`location`（任意）・`is_all_day: bool = False`。
  - 日時の形式: ISO 8601 文字列。`datetime.fromisoformat(s.replace(" ", "+"))`（`backend/app/services/calendar_service.py:31-36`）。例 `2026-11-02T10:00:00+09:00`。時差なしの文字列を渡した場合の扱い（保存先の列が `timestamptz` か）は**未確認**。
  - **権限確認が無い**: `calendar.py` に `require_permission` は無く、認証のみ（旧 recon §2 と同じ観測。再確認）。

## F. 画面

- アプリ全体の枠: `frontend/src/App.tsx:135-146`（`ShellSwitch`＝767px 以下は `MobileShell`、以上は `DesktopShell`）。右下の固定ボタンの前例は `frontend/src/components/DesktopShell.tsx:401-410` の `avatar-btn`（`<Outlet />` の直後に置かれた固定ボタン）。**印を置くなら両方の Shell（`DesktopShell.tsx` と `MobileShell.tsx`）に必要**（または `ShellSwitch` の外側に 1 回）。どちらにするかは設計判断。
- API を呼ぶ共通の関数: `frontend/src/lib/api.ts:240-252` の `api.get/post/put/patch/delete`（`request` 経由。`/api/v1` の二重付与を防ぐ試験あり: `api.no-double-prefix.test.ts`）。
- i18n: `frontend/src/locales/ja.json`・`en.json`（`frontend/src/i18n.ts:14-15` で読み込み）。画面側は `useTranslation()` の `t("key")`。`secretary` に当たるキーは未存在。
- Drawer の props: `frontend/src/components/Drawer.tsx:28-55` — `open`・`onClose`・`title`・`children`（必須）、`onOpenFullPage`・`onEscape`・`footer`・`size`（`default` 480px / `wide` 1100px）・`mobileInset`・`headerContent`、戻る用 `onBack`+`backLabel`（組で指定）。
- 金型の決まり: `docs/CC_UI_GOVERNANCE.md:5-19`「`components/` に金型があるか先に確認」「無ければ実装しない・止めて報告する」「PO 許可を得てから登録」「作法: `Xxx.tsx` + `Xxx.css`（`var()` のみ）+ `Xxx.stories.tsx`」。禁止（CI が赤）: 生 `<select>`・生 `<input type=text/search/省略>`・生 checkbox/radio・読み込み中の文字だけ・ボタン文言の入れ替え・自作タブ・色直値。
- 検査: `.github/workflows/ui-governance-gate.yml:31-38` が `node scripts/tests/test-ui-governance.js` と `node scripts/check-ui-governance.js` を実行。対象は `frontend/src/pages|features|components/`（`scripts/check-ui-governance.js:43-49`）。`components/` の英語固定文言（`englishUiLiteral`）・`loadingTernary`・生 `<select>`/`<input>` を見る（`:16-18,188-`）。`component-standard.md` は Button/Card 等の確定値（`docs/specs/component-standard.md`。吹き出し・チャット窓の金型は**無い**＝旧 recon §5 のとおり）。
- Storybook の前例: `frontend/src/components/Drawer.stories.tsx:1-40`（`Meta<typeof Drawer>`・`title: 'Components/Drawer'`・`parameters: { layout: 'fullscreen', docs: { disable: true } }`・`tags: []`）。
- アイコン: `frontend/package.json` に `lucide-react ^1.14.0` と `@heroicons/react ^2.2.0` の両方（raw §F-9）。どちらを標準とするかの決まりは**未確認**。
- `--z-*`（`frontend/src/tokens.css:126-135`）: `--z-base:10`・`--z-dropdown:50`・`--z-topbar:100`・`--z-sidebar:200`・`--z-sidebar-overlay:210`・`--z-backdrop:298`・`--z-avatar:300`・`--z-drawer:301`・`--z-modal:400`・`--z-toast:500`。右下の印の `z-index` は avatar(300)・drawer(301) との重なりを決める必要がある（新トークン追加は金型/トークンの変更扱いになりうる）。

## G. デプロイ

- 本体の容器: `.github/workflows/deploy.yml:475` `docker compose up -d --no-deps --remove-orphans frontend celery-worker celery-beat discord-gateway gemini-egress` — **サービス名はこの行に列挙**（backend の起動行は本調査では特定していない＝未確認。確認範囲は 463-484 と 885-899）。
- 別ファイル・別プロジェクトで足す前例: `docker-compose.ai-reader-cloud-http.yml`（全文は raw §G-1）を `deploy.yml:619-635` の別ステップで `docker compose -p astro-webapp-casewindow -f ... up -d --build=false --force-recreate` する。失敗しても本体は止めない（`|| echo "::warning::..."`）。`.env` の `COMPOSE_PROJECT_NAME` が優先されるので `-p` が必須（compose の先頭コメント）。
- GitHub secrets を `.env` に書く仕組み: `deploy.yml:325-326`（古い行を削除する `sed`）と `:379-380`（`CASE_AGENT_TOKEN='${{ secrets.CASE_AGENT_TOKEN }}'` のように書く）。新しい秘密（例 `CLAUDE_CODE_OAUTH_TOKEN`）を足すなら同じ 2 か所の形に従う。ただし「**secrets の変更**」は PO 本人の GO が要る（H 参照）。
- 前例（新容器）の PR の変更ファイル: 
  - `833860119`: `backend/app/ops/read_window_http.py`・`backend/tests/ops/test_read_window_http.py`・`docker-compose.ai-reader-cloud-http.yml`（3 ファイル）
  - `64b31eec6`: `.github/workflows/deploy.yml`・`migrations/20261024_100000/100100/100200/100300_*.sql`・`scripts/run_all_migrations.sh`（6 ファイル）
  - `ab7197912`（続きの容器 ai-unmask-http）: `.github/workflows/deploy.yml`・`migrations/20261031_200000_create_ops_case.sql`・`scripts/tests/test-deploy-nginx-recreate-guard.sh`・`tests/sandbox/compose-run-nginx-mount.sh`（4 ファイル）
  - ※これらは**コミット**単位で、PR 番号単位の一覧は未取得（`gh` 不可）。
- メモリ上限の書き方: compose の `mem_limit: 128m`（`docker-compose.ai-reader-cloud-http.yml:42`、`ai-reader-http.yml:38`、`ai-unmask-http.yml:39`）、`mem_limit: 256m`（`ai-reader.yml:23`）。同ファイルは `read_only: true`・`tmpfs: /tmp`・`cap_drop: ALL`・`no-new-privileges`・`logging: none` も併用。`docker-compose.yml:29,52` と monitoring/exporters は `deploy.resources.limits.memory` 形式（`memory: 256M` 等）で**書き方が 2 通りある**。
- 注意（観測）: 新容器の compose の**読み取り専用 root**（`read_only: true`）は Claude Code が `~/.claude` に書く要件と衝突しうる（`CLAUDE_CONFIG_DIR` を tmpfs にする必要。実機での動作は**未確認**）。

## H. 危険な変更の決まり — どれが GO 必須か

根拠: `AGENTS.md`「不可逆操作」「ブランチと作業場所」、ADR-135（`docs/adr/ADR-135-release-stowaway-prevention.md:60`）、ADR-136（`:46`）、ADR-1003（`docs/adr/ADR-1003-go-delegation-to-opus.md:31-45`）、`scripts/check-process-artifacts.js:1023-1041,51-53`。

| 想定する変更 | GO が要るか | 理由／誰の GO |
|---|---|---|
| `migrations/*.sql`（CHECK に `secretary_chat` を足す・`tenant_features` に行を入れる・権限キーを足す） | **要る** | `^migrations/` は DANGEROUS_PATTERNS（`check-process-artifacts.js:1024`）。GO は ADR-1003 により Claude Opus 設計担当へ委譲可。ただし追加行に `DROP TABLE`/`DROP COLUMN` 等があれば PO 本人の GO（ADR-1003 例外）。CHECK の差し替えを `DROP CONSTRAINT` で書く場合の判定は**未確認**（`requiresPoOnlyGo` の正規表現を未読） |
| `.github/workflows/deploy.yml`（新容器の起動ステップ・`.env` への秘密の書き込み） | **要る** | `:1027` DANGEROUS。委譲可 |
| GitHub secret の追加（月額契約のトークン） | **PO 本人の GO** | ADR-1003 例外「secrets の変更」（`:37`）。機械では検査されず手順で担保（`:79`）。AGENTS.md「secrets変更」も不可逆操作一覧 |
| 月額契約のトークン取得（`claude setup-token`）・VPS への配置 | PO 本人の作業 | 秘密の値は AI が見ない・書かない。VPS 上の変更は「作業ごとに PO の GO」（AGENTS.md「VPS 直作業禁止」） |
| 新しい `docker-compose.secretary-*.yml` | **機械では止まらない（観測）**。ただし deploy.yml の変更とセット | DANGEROUS_PATTERNS に載っているのは `docker-compose.ai-reader.yml`・`ai-reader-http.yml` だけで、`ai-reader-cloud-http.yml`・`ai-unmask-http.yml` は載っていない（`:1034-1035`）。載せるかは設計判断 |
| `scripts/`（新しい起動・検査スクリプト） | **要る** | `^scripts/`（`:1025`、ADR-135 B-2） |
| `backend/app/ops/` 配下に置く場合 | **要る** | `^backend\/app\/ops\/`（`:1033`） |
| `backend/app/services/llm_budget.py`・routers・schemas の追加 | 危険パスではない | 通常の PR（`shingo-cc` 名義が必須。AGENTS.md） |
| `frontend/src/**`（印・Drawer・i18n） | 危険パスではない | ただし金型（吹き出し・チャット窓）の新設は **PO の許可**が先（`docs/CC_UI_GOVERNANCE.md:17-19`）。`frontend/src/pages-layout.css` を触る場合は GO 必須（`:1028`） |
| `.github/workflows/workflow-lint.yml` | PO 本人の GO | ADR-1003 例外・AGENTS.md |
| 本番 DB の `tenant_features` 直接 INSERT | 現状（開発フェーズ）は継続可だが本番運用フェーズ移行後は制限 | AGENTS.md「本番運用フェーズ移行後に effective」。migration で入れるのが前例なし（C）のため設計判断 |
| 本番への接続・VPS の変更 | PO の GO | AGENTS.md「VPS 直作業禁止」。本調査では未実施 |

---

## 観測事実／未確認（まとめ）

観測事実（コードは本ファイルの根拠行、公式は raw §A）:
- `--json-schema`（`structured_output` 欄）・`--tools ""`・`--disallowedTools`・`--strict-mcp-config`・`--setting-sources`・`--no-session-persistence`・`--max-turns`・`--model` は公式に存在する。
- 月額契約のログインは `claude setup-token` → `CLAUDE_CODE_OAUTH_TOKEN`。`--bare` はこのトークンを読まない。`-p` で `ANTHROPIC_API_KEY` があるとそちらが優先される。
- 必要な通信先は `api.anthropic.com`・`claude.ai`・`platform.claude.com`。
- `llm_usage_events` の purpose・sdk はコードと DB の CHECK の両方で固定。
- `tenant_features` に行を入れる前例は無い。`require_feature` は未使用。
- users は 1 人 1 テナント。テナント切替の仕組みは見つからない。
- 請求書は `company_id`・`contact_id`・`items`（`product_name`・`quantity`・`unit_price` 必須）で作れる。予定は `title`・`start_datetime`・`end_datetime` 必須、ISO 8601。予定の口には権限確認が無い。
- 会社・担当者・品物の名前検索は router 内の SQL（service に無い）。
- 右下の固定ボタンの前例は `DesktopShell.tsx:401-410` の `avatar-btn`。チャット用の金型は無い。
- 新容器は別 compose＋deploy.yml の別ステップ＋`mem_limit` が前例。秘密は deploy.yml の 2 か所で `.env` に書く。
- ADR-1003 により secrets の変更は PO 本人の GO。migrations・deploy.yml・scripts は GO 必須（委譲可）。

未確認:
- Claude Code の `-p` 1 回の実メモリ・容器の下限（公式は「4 GB+ RAM」のみ）。
- `--setting-sources ""` 等の空指定の可否。`--strict-mcp-config` だけで MCP が確実にゼロになるか（実機未検証）。
- 読み取り専用 root の容器で Claude Code が動くか。Docker 専用の公式手順（devcontainer ページ未読）。
- Claude の `usage` と `llm_usage_events` の列の対応。CHECK の差し替え migration の書き方と GO 区分（`DROP CONSTRAINT` の扱い）。
- 本番の tenants の行（001 = どの会社か）、PO が 001・004 を別ログインで使うのか、PO が super admin か、owner が何人か。
- 請求書の品物の単価をどこから決めるか。時差なしの日時の扱い。
- `feature_key` の命名規則（決まりは見つからず）。PR 番号単位の変更ファイル一覧（`gh` 不可）。
