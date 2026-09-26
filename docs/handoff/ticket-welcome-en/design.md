# design: チケット歓迎メッセージ初期値の英語CTA統一

設計日: 2026-06-28 / 担当: CC / recon 参照: docs/handoff/ticket-welcome-en/recon.md / 関連: ADR-091

## 目的

コードに書かれた歓迎メッセージの「初期値（デフォルト）」を旧日本語から新英語CTAへ差し替える。  
welcome_template を独自設定していないテナントで新規チケットを開いた際に、英語の新CTAが顧客へ送られる状態にする。  
既に管理画面で独自文言を入れているテナントは不変（DB値優先のため）。

## 確定文言（PO確定）

```
Thanks for reaching out! I've created a private channel just for you. I'll connect you with our sales team — please reply with your name to get started.
```

## KGI / 検証方法

| 基準 | 検証方法 |
|------|---------|
| welcome_template 未設定のテナントで新規チケットを開くと英語CTAが送られる | welcome_template 未設定のユーザーでチケットを開き、専用チャンネルへの送信文言を目視確認 |
| 管理画面を未設定テナントで開いたときの初期表示が英語CTA | /admin/discord-config の管理画面を未設定テナントで開き、ウェルカムメッセージ欄の初期文を確認 |
| 独自設定済みテナントの文言が変わっていない | 既に独自設定を持つテナントでチケットを開き、文言がそのままであることを確認 |

## 変更内容

### ★必須（実送信）: `backend/app/discord_gateway/ticket_channel_creator.py:32`

- 前: `_DEFAULT_WELCOME = "ご連絡ありがとうございます。こちらのチャンネルでサポートいたします。"`
- 後: `_DEFAULT_WELCOME = "Thanks for reaching out! I've created a private channel just for you. I'll connect you with our sales team — please reply with your name to get started."`

### 推奨（管理画面フォーム表示）: `backend/app/routers/discord_ticket_config.py:57`

- 前: `welcome_template: str = "ご連絡ありがとうございます。こちらのチャンネルでサポートいたします。"`
- 後: 同じ英語CTAに変更

変えないと: DB未設定テナントが管理画面を開くと旧日本語がフォームに入り、保存し忘れると日本語のままDBに書き込まれる。

### 推奨（PUT省略時フォールバック）: `backend/app/routers/discord_ticket_config.py:70`

- 前: `default="ご連絡ありがとうございます。こちらのチャンネルでサポートいたします。"`
- 後: 同じ英語CTAに変更

変えないと: 管理画面以外からのPUTで welcome_template が省略された場合に旧日本語がDBに入る（通常は発生しないが整合上）。

### 任意（整合・実害なし）: `frontend/src/locales/ja.json:2776` / `frontend/src/locales/en.json:2776`

- `welcomeTemplateDefault` を新CTA（英語）に統一
- 変えないと: 管理画面ローディング中（API応答前 ~100ms）に旧文言が一瞬だけ見える

## 触らない範囲

- 既存の welcome_template DB値（独自設定済みテナント）：変更しない（コードのみ・DB操作なし）
- 歓迎メッセージの送信ロジック・チャンネル作成・_hide_ticket_start・受信振り分け：変更しない
- original_language 推定（infer_original_language）：変更しない
- migration / deploy.yml / docker-compose：変更なし（DB変更なし）

## 外部・過去事例と我々への応用

- F1（recon）: 実送信経路は `ticket_channel_creator.py:226` の `config.get("welcome_template") or _DEFAULT_WELCOME`。DB値優先なので既存テナントへの影響はゼロ。これにより安全に初期値のみ変更できる。
- F5（recon）: auto-setup が `welcome_template` をUPDATEしない設計（`discord_auto_setup.py:327-344`）が前例として存在し、auto-setup再実行による上書きリスクがないことを確認済み。

## リスク・副作用

- **影響範囲が限定的**: DB値が入っているテナントは完全に不変。DB値なしのテナントのみに効く（安全側）。
- **ロールバック**: revert PR で即時戻し可能（DB変更なし）。
- **文字長**: 新CTA（英語）= 約150文字。DB列の制限は確認要。APIスキーマ上は `max_length=500` (`discord_ticket_config.py:71`)。問題なし。
