# Discord Bot 顧客向け文言の英語化 — design

> recon: docs/handoff/discord-bot-english-texts/recon.md
> 前提の過去決定: docs/handoff/ticket-welcome-en/design.md（コード既定のみ英語化。DB 既定が残った点が本便の対象）
> 対象 ADR: ADR-091

## 目的

Discord サーバーの顧客（メンバー）に見える Bot の文言をすべて英語にし、英語を既定に一本化する。チケットを開いた後のウェルカム文が日本語になる原因（DB の既定値）を取り除く。

## PO 決定（原文）

- 「チケットを開いた後のチャンネルメッセージが日本語担っているので英語にしたい…英語でメッセージを送ることをデフォルトにしてくれ」
- 「お客様向けは全部英語 (推奨)」（管理画面の API エラー・内部通知は日本語のまま）

## 変更前後

| 項目 | 変更前 | 変更後 |
|---|---|---|
| 文言の置き場 | client.py・2つのルーターに日本語/英語リテラルが分散 | backend/app/discord_gateway/bot_texts.py に一本化（SSOT） |
| ウェルカム既定（DB） | migration が日本語を既定にしていた | 新 migration で既定を英語に変更し、旧日本語既定のままの行だけ英語へ更新 |
| 自動セットアップの INSERT | welcome_template を指定せず DB 既定に依存 | bot_texts の英語既定を明示（ON CONFLICT 側は更新しない＝独自文言は保持） |
| ボタン投稿文 / ラベル | サポートが必要な場合は下のボタンを押してください。 / チケットを開く | Need help? Click the button below to open a private support ticket. / Open a ticket（custom_id と絵文字は不変） |
| ボタン押下の応答（ephemeral） | 日本語 5 種 | 英語 5 種（PO 指定文言そのまま） |

## 設計判断と代替案

- 文言は Python モジュール bot_texts.py に定数で持つ（Bot はフロントの i18n を使わず、顧客の言語は英語固定のため）。ボタンのペイロードも関数化し、2つのルーターの重複を除去する。
- DB 既定の是正は migration で行う（新規行の既定と、旧日本語既定のままの既存行の両方が必要なため）。代替案「コードで DB 値を無視して常に英語」は、テナントが管理画面で設定した独自文言を上書きするため不採用。
- 旧日本語の既定文と完全一致する行だけを UPDATE する。独自文言に編集済みの行は変更しない。DROP・DELETE は使わない。
- 既に各 Discord サーバーへ投稿済みの日本語ボタンメッセージは、管理画面の「ボタンを投稿する」または自動セットアップの再実行で再投稿されるまで日本語のまま残る（コードから過去メッセージを編集する処理は追加しない）。

## 触らない範囲

管理画面の API エラー文・内部通知・ログ（日本語のまま）、フロントエンド、Discord 権限設定、チャンネル名・ロール名。

## 受入条件

| 基準 | 検証方法 |
|---|---|
| ボタン押下への応答 5 種が英語で bot_texts から供給される | backend/tests/test_discord_bot_texts.py |
| ボタン投稿ペイロード（本文・ラベル英語、custom_id・絵文字不変） | backend/tests/test_discord_bot_texts.py と backend/tests/test_discord_auto_setup.py |
| ウェルカム既定・設定 API の既定が bot_texts と一致し、自動セットアップの初回 INSERT が英語既定を渡す | backend/tests/test_discord_bot_texts.py と backend/tests/test_discord_auto_setup.py |
| migration の英語文が bot_texts と同一で、旧日本語既定の行のみ更新・DROP/DELETE なし | backend/tests/test_discord_bot_texts.py |
| migration が実DBで実行できる | CI「マイグレーションSQL 実行テスト（実DB）」 |
| CI 必須チェック全緑 | `gh pr checks` |
| 本番: 新規チケットのウェルカム・ボタン押下応答が英語 | PO が Discord で確認（本 PR の外） |

## 外部・過去事例の参照と我々への応用

- 過去事例（自社）: docs/handoff/ticket-welcome-en/design.md。コード既定だけを英語化して DB 既定が残り、実際の送信は日本語のままだった。応用: 既定値は「コード」と「DB」の両方を同時に揃え、文言の正本を1箇所にする。
- 外部事例: 該当なし（既存機能の文言と既定値の是正であり、外部事例に依存しない）。

## 影響範囲

- 文言の利用箇所: backend/app/discord_gateway/client.py・backend/app/discord_gateway/ticket_channel_creator.py・backend/app/routers/discord_auto_setup.py・backend/app/routers/discord_ticket_config.py（`git grep -n bot_texts` で全件確認）。
- 既存テナントの welcome_template: 旧日本語既定のままの行のみ英語へ。独自文言は不変。
- migration は scripts/run_all_migrations.sh に登録（deploy.yml は同スクリプトを呼ぶため変更不要）。

## 戻し方

マージコミットを revert する。DB は既定値と旧既定のままだった行が英語になっているため、日本語へ戻す場合は同条件の逆 UPDATE を別 migration で行う（独自文言の行は元々触っていない）。

## 維持の仕組み

- 守り手: backend/tests/test_discord_bot_texts.py が CI の pytest で常時実行される。文言・既定値・migration の文言が bot_texts とずれるとテストが落ちる。
- 対象: 顧客向け文言の SSOT と DB 既定値の一致。
- 関所なしの場合: 該当なし。
