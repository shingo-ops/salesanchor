# Discord Auto Setup Acceptance

## 検収日時

2026-06-14

## 対象環境

ローカル（http://localhost:5173 / docker-compose）

## 対象テナント

未確定（手動確認時に記入）

## 対象Discordサーバー

検収用テストサーバー（Bot未招待 → Step 1 で招待）

---

## 結果サマリー

| 項目 | 結果 |
|------|------|
| Bot招待 | 要手動確認 |
| 自動セットアップ UI | コードレビュー PASS（要実機確認） |
| Discord作成物 | 要手動確認 |
| 冪等性 | コードレビュー PASS（要実機確認） |
| Botロール順 | 要手動確認 |
| ロール同期 | 要手動確認 |

**判定**: 未確認（実機テスト待ち）

---

## コードレビュー確認済み項目

実機テスト前にコードで確認できた事項を記録する。

### PR マージ確認

| PR | タイトル | マージ日時 | develop SHA |
|----|----------|------------|-------------|
| #2155 | Backend API | 2026-06-14T01:02:30Z | `5b1499f1` |
| #2163 | Frontend UI | 2026-06-14T01:57:10Z | `e6ed661b` |
| #2145 | Botロール順ガイド | develop 済み | — |
| #2150 | 設計 | develop 済み | — |

### 冪等性ロジック（コード確認済み）

`discord_auto_setup.py` の冪等処理:

- **ロール**: `_find_role_id()` で名前一致検索 → 存在すれば `skipped`（API: `GET /guilds/{guild_id}/roles`）
- **チャンネル**: `existing_channel_ids = {ch["id"] for ch in existing_channels}` で ID 集合チェック → DB の stored ID が集合内なら `skipped`（API: `GET /guilds/{guild_id}/channels`）
- **チケットボタン**: `ch_ticket.status == "created"` の場合のみ投稿 → `skipped` のときはボタン投稿スキップ
- **カテゴリ失敗ガード**: `category_id` が None ならチャンネル3本すべて `failed`（ルート直下作成防止）

### 権限定数（コード確認済み）

```python
_VIEW_CHANNEL      = 1024   # 1 << 10
_SEND_MESSAGES     = 2048   # 1 << 11
_READ_MESSAGE_HISTORY = 65536  # 1 << 16
```

| チャンネル | @everyone | Staff | Member | Partner |
|-----------|-----------|-------|--------|---------|
| ticket-start | VIEW+READ（SEND禁止） | VIEW+READ+SEND | — | — |
| member-announcements | 全禁止 | 全許可 | VIEW+READ（SEND禁止） | VIEW+READ（SEND禁止） |
| partner-announcements | 全禁止 | 全許可 | — | VIEW+READ（SEND禁止） |

### ADR-072 準拠（コード確認済み）

`discord_auto_setup.py:341`: `await reset_tenant_context(db, tenant_id)` が `db.commit()` 直後に実装済み。

### COALESCE upsert（コード確認済み）

`discord_auto_setup.py:298-315`: 失敗ステップの列は `COALESCE(EXCLUDED.col, existing_col)` で既存値を保持する実装済み。

### 既存 Bot 権限確認（コード確認済み）

`discord_oauth.py:47`: `_DISCORD_PERMISSIONS = "268504082"` に MANAGE_CHANNELS・MANAGE_ROLES・SEND_MESSAGES を含む（recon.md §2 で展開済み）。

---

## Step 1 Bot招待確認

### 手順

1. `https://app.salesanchor.jp/channels` または `/admin/discord-config` から Bot を対象 Discordサーバーへ招待
2. `/admin/discord-config` を開く
3. Guild ID フィールドに接続済みの値が表示されることを確認

### 記録

```
Guild ID: （実測値を記入）
Bot 参加確認: □ 済み / □ 未確認
```

### スクショ貼付位置

> `docs/handoff/discord-auto-setup/screenshots/step1-guild-id.png`

---

## Step 2 自動セットアップ実行

### 手順

1. `/admin/discord-config` の「Discordサーバー自動セットアップ」カードを確認
2. Guild ID 未設定時: ボタンが disabled になることを確認
3. Guild ID 設定済み: 「自動セットアップを実行」ボタンをクリック
4. 実行中は「セットアップ中...」表示になることを確認
5. 結果が表示されるまで待つ

### 期待レスポンス

```json
{
  "status": "completed",
  "steps": [
    {"step": "role_staff",  "status": "created", "discord_id": "..."},
    {"step": "role_partner","status": "created", "discord_id": "..."},
    {"step": "role_member", "status": "created", "discord_id": "..."},
    {"step": "category",    "status": "created", "discord_id": "..."},
    {"step": "ch_ticket",   "status": "created", "discord_id": "..."},
    {"step": "ch_member",   "status": "created", "discord_id": "..."},
    {"step": "ch_partner",  "status": "created", "discord_id": "..."},
    {"step": "button",      "status": "posted",  "discord_id": "..."}
  ],
  "role_order_guide_url": "..."
}
```

### 記録

```
UI 表示 status: □ completed / □ partial / □ failed
role_staff:   □ created / □ skipped / □ failed  error: 
role_partner: □ created / □ skipped / □ failed  error: 
role_member:  □ created / □ skipped / □ failed  error: 
category:     □ created / □ skipped / □ failed  error: 
ch_ticket:    □ created / □ skipped / □ failed  error: 
ch_member:    □ created / □ skipped / □ failed  error: 
ch_partner:   □ created / □ skipped / □ failed  error: 
button:       □ created / □ posted  / □ failed  error: 
ロール順ガイドリンク表示: □ 有り / □ なし
```

### スクショ貼付位置

> `docs/handoff/discord-auto-setup/screenshots/step2-result.png`

---

## Step 3 Discord作成物確認

### 手順

Discordサーバーを開き、以下を確認する。

ロール（サーバー設定 → ロール）:

- [ ] Sales Anchor Staff
- [ ] Member
- [ ] Partner

カテゴリ・チャンネル:

- [ ] 「Sales Anchor」カテゴリ
- [ ] ticket-start
- [ ] member-announcements
- [ ] partner-announcements

ticket-start チャンネル内:

- [ ] 「チケットを開く」ボタン付きメッセージが投稿されている

### 記録

```
Sales Anchor Staff ロール: □ 有り / □ なし
Member ロール:             □ 有り / □ なし
Partner ロール:            □ 有り / □ なし
Sales Anchor カテゴリ:     □ 有り / □ なし
ticket-start:              □ 有り / □ なし
member-announcements:      □ 有り / □ なし
partner-announcements:     □ 有り / □ なし
チケットボタン:             □ 有り / □ なし
```

### スクショ貼付位置

> `docs/handoff/discord-auto-setup/screenshots/step3-channels.png`
> `docs/handoff/discord-auto-setup/screenshots/step3-roles.png`
> `docs/handoff/discord-auto-setup/screenshots/step3-button.png`

---

## Step 4 権限確認

### 確認方法

Discord の「チャンネルを編集」→「権限」タブで各ロールの許可/拒否を確認。

### ticket-start

| 対象 | VIEW_CHANNEL | SEND_MESSAGES | READ_MESSAGE_HISTORY |
|------|-------------|---------------|----------------------|
| @everyone | allow | deny | allow |
| Sales Anchor Staff | allow | allow | allow |

### member-announcements

| 対象 | VIEW_CHANNEL | SEND_MESSAGES | READ_MESSAGE_HISTORY |
|------|-------------|---------------|----------------------|
| @everyone | deny | deny | deny |
| Member | allow | deny | allow |
| Partner | allow | deny | allow |
| Sales Anchor Staff | allow | allow | allow |

### partner-announcements

| 対象 | VIEW_CHANNEL | SEND_MESSAGES | READ_MESSAGE_HISTORY |
|------|-------------|---------------|----------------------|
| @everyone | deny | deny | deny |
| Partner | allow | deny | allow |
| Sales Anchor Staff | allow | allow | allow |

### 記録

```
ticket-start @everyone SEND 禁止: □ 確認 / □ 不一致
ticket-start Staff SEND 許可:    □ 確認 / □ 不一致
member-annc @everyone 閲覧禁止:  □ 確認 / □ 不一致
member-annc Member 閲覧許可:     □ 確認 / □ 不一致
partner-annc @everyone 閲覧禁止: □ 確認 / □ 不一致
partner-annc Partner 閲覧許可:   □ 確認 / □ 不一致
```

---

## Step 5 冪等性確認

### 手順

1. Step 2 で completed になった状態で、もう一度「自動セットアップを実行」をクリック
2. Discordサーバーのチャンネル数・ロール数を実行前後で比較する

### 期待結果

```json
{
  "status": "completed",
  "steps": [
    {"step": "role_staff",  "status": "skipped"},
    {"step": "role_partner","status": "skipped"},
    {"step": "role_member", "status": "skipped"},
    {"step": "category",    "status": "skipped"},
    {"step": "ch_ticket",   "status": "skipped"},
    {"step": "ch_member",   "status": "skipped"},
    {"step": "ch_partner",  "status": "skipped"},
    {"step": "button",      "status": "skipped"}
  ]
}
```

### 記録

```
2回目 status: □ completed / □ partial / □ failed
全ステップ skipped: □ 全 skipped / □ 一部 created が再発生
チャンネル重複: □ なし / □ 有り（内容: ）
ロール重複: □ なし / □ 有り（内容: ）
ボタン重複: □ なし（追加投稿なし） / □ 有り
```

### スクショ貼付位置

> `docs/handoff/discord-auto-setup/screenshots/step5-idempotent.png`

---

## Step 6 Botロール順確認

### 手順

`docs/runbooks/discord-role-order-guide.md` に従い Discordサーバーのロール順を設定する。

目標順序:

```
Owner / Admin（最上位）
Sales Anchor Bot
Sales Anchor Staff
Partner
Member
@everyone（最下位）
```

注意: Sales Anchor Bot ロールを Sales Anchor Staff より上に置く必要があるか否かを実機で確認する。
（MANAGE_ROLES は Bot が自分より下のロールしか操作できないため、Bot ロールが Staff ロールより下だとロール付与に失敗する可能性がある）

### 記録

```
Bot ロール順設定: □ 完了 / □ 未実施
Bot が Staff より上: □ 確認 / □ 要調査
```

---

## Step 7 ロール同期確認

### 手順

1. テストリードを作成し、Discordユーザーと紐づける
   - `discord_user_id` が設定済みであること
2. `estimated_scale = Small` に変更 → Member が付与されること
3. `estimated_scale = Large` に変更 → Partner が付与され、Member が外れること

### 確認できない場合の切り分け

- `discord_user_id` 未設定 → Lead の Discord 連携が未完了
- テストユーザー未紐づけ → 検収用 Discord アカウントとリードを紐づける
- Bot権限不足 → Bot ロールが Staff ロールより下の可能性（Step 6 参照）

### 記録

```
discord_user_id 設定: □ 済み / □ 未設定（原因: ）
Small → Member付与: □ 成功 / □ 失敗（原因: ）
Large → Partner付与: □ 成功 / □ 失敗（原因: ）
Large → Member除去: □ 成功 / □ 失敗（原因: ）
```

---

## 検出した問題

（実機テスト後に記入）

---

## 未確認事項

| 項目 | 理由 | 対処 |
|------|------|------|
| 全 Step 1〜7 の実機確認 | Playwright ブラウザが別セッションで占有中・Docker 未起動のため実機接続できず | しんごさんが手動確認 |
| Bot 招待フロー | 検収用 Discord サーバーに Bot 未招待 | Step 1 から順に実施 |
| ロール同期 Step 7 | discord_user_id 設定・テストリード紐づけが必要 | 紐づけ後に確認 |

---

## 判定

- **PASS 条件**: Step 2〜5 completed + Step 6 ロール順設定 + Step 7 ロール同期成功
- **PARTIAL 条件**: Step 2〜5 は成功、Step 7 のみ確認できない
- **FAIL 条件**: Step 2 が failed / 重複作成発生 / 必須チャンネル・ロールが作られない

現時点判定: **PENDING**（実機テスト完了後に PASS / PARTIAL / FAIL を記入）
