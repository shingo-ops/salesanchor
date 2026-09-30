# Discord Bot 顧客向け文言の英語化 — recon（現在地）

> 実測時の origin/main: 4de895d48583e170bf6ef4ecb38166da7ee3f309
> 前提となる過去決定: docs/handoff/ticket-welcome-en/design.md（2026-06-28・PO 確定のウェルカム英語文。コード既定値のみ変更した）

## 事実

- チケット押下後のウェルカム既定文（コード）: backend/app/discord_gateway/ticket_channel_creator.py:32 が英語の `_DEFAULT_WELCOME`。使用は backend/app/discord_gateway/ticket_channel_creator.py:226 の `config.get("welcome_template") or _DEFAULT_WELCOME`（DB の値が空でない限り DB が優先）。
- DB 側の既定は日本語のまま: migrations/20260602_120000_add_discord_ticket_config.sql:10 が `welcome_template TEXT NOT NULL DEFAULT 'ご連絡ありがとうございます。こちらのチャンネルでサポートいたします。'`。`git grep -n welcome_template origin/main -- migrations` のヒットはこの1行のみ（後続 migration で既定は変更されていない）。
- 自動セットアップの INSERT は welcome_template を列に含めない: backend/app/routers/discord_auto_setup.py:329（列）と backend/app/routers/discord_auto_setup.py:332（値）。そのため自動セットアップで作られた行は DB の日本語既定を持ち、ウェルカムは日本語で送られる（コードの英語既定に届かない）。
- 手動設定 API の既定は英語（リテラル重複）: backend/app/routers/discord_ticket_config.py:57 と backend/app/routers/discord_ticket_config.py:70。
- ボタン押下への ephemeral 応答は日本語（backend/app/discord_gateway/client.py:173 / :185 / :201 / :216 / :222）。
- チケット開始ボタンの投稿文・ラベルが日本語で2箇所に重複: backend/app/routers/discord_auto_setup.py:591・:599 と backend/app/routers/discord_ticket_config.py:257・:265。custom_id は backend/app/routers/discord_auto_setup.py:566 と backend/app/discord_gateway/client.py:160 でも文字列リテラル `ticket_open`。
- 既に投稿済みのボタンメッセージ（各 Discord サーバー上）は日本語のまま残る。コードからは編集していない。

## PO 決定（2026-09-30・原文）

- 「チケットを開いた後のチャンネルメッセージが日本語担っているので英語にしたい…英語でメッセージを送ることをデフォルトにしてくれ」
- 範囲の回答: 「お客様向けは全部英語 (推奨)」（管理画面の API エラー・内部通知は日本語のまま）

## ADR 検索（着手前）

- 対象 ADR: ADR-091（docs/adr/ADR-091-discord-bot-scope-definition.md・Bot の業務範囲）。B方式（ADR-146 と表記されるコード内参照）は docs/adr/ に ADR-146 のファイルが無い（`ls docs/adr | grep ADR-146` が空）ため対象 ADR に含めない。
- 過去の同テーマ: docs/handoff/ticket-welcome-en/design.md（コード既定のみ）。本便は DB 既定の乖離と他の顧客向け文言を含めて SSOT 化する。
