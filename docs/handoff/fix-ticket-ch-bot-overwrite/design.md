# 設計: ticket-start チャンネル bot 書込許可追加（403修正）

関連ADR: ADR-146（B方式）  
recon: docs/handoff/fix-ticket-ch-bot-overwrite/recon.md  
設計日: 2026-06-28

## 変更内容

`backend/app/routers/discord_auto_setup.py` の `_ticket_ch_overwrites` 関数（:637）に `bot_user_id` 引数を追加し、ticket-start チャンネルに bot の `type=1 member overwrite (allow SEND_MESSAGES)` を付与する。

- 変更箇所1: `:255` 呼び出し — `bot_user_id` 引数を追加
- 変更箇所2: `:637` 関数定義 — `bot_user_id: str = ""` パラメータ追加、overwrite append 追加

カテゴリ作成（:207-219）と同パターン。DB・migration・deploy.yml・docker-compose は無変更。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| ticket-start に「チケットを開く」ボタンが表示される | テストサーバーで auto-setup 再実行後、Discord で目視確認 |
| bot が 403 を返さずボタンを投稿できる | バックエンドログに `button post failed` が出ないこと |
| 既存の @everyone / Staff overwrite が壊れていない | Discord API で permission_overwrites を確認 |
| on_interaction によるチケット作成が動作する | ボタン押下でチケットチャンネルが作成されること |

## 外部・過去事例の参照と我々への応用

Discord の permission 解決順序（公式ドキュメント）: カテゴリレベルの overwrite よりチャンネルレベルの overwrite が優先される。bot user に対するカテゴリの `type=1 member overwrite` は、チャンネル個別の `@everyone deny SEND_MESSAGES` によって無効化される。解決策はチャンネルレベルでも bot user の `type=1 overwrite` を明示的に追加すること（カテゴリ:207-219 で既に採用済みのパターン）。
