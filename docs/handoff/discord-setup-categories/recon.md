# recon — Discord 自動セットアップのカテゴリ3分割

**仕事名**: discord-setup-categories  
**日付**: 2026-10-02  
**対象ADR**: ADR-091（`docs/adr/ADR-091-discord-bot-scope-definition.md`）・ADR-159（`docs/adr/ADR-159-staff-identity-on-discord.md`・ロール/Webhook名義の関連）。自動セットアップ専用の ADR は `git grep -il "auto-setup\|auto_setup\|自動セットアップ" -- docs/adr` の結果 ADR-091 のみで、新規 ADR は不要（既存構成の名前・配置の変更）。  
**担当**: Dev（Sonnet）

## PO 依頼（原文）

「自動セットアップで作成されるカテゴリ名がSales Anchor担っている、チケットを開いてPrivateメッセージを行うカテゴリなので"📩｜DM"というカテゴリ名にしたい。　在庫情報を配信するアナウンスチャンネルも同じカテゴリに作られている。大口と小口でアナウンスは分離するのでそれぞれ別のカテゴリとして作成してセットアップしてほしい。"🍀｜Stock Information"→メンバー向けのアナウンスチャンネル　"🍒｜Stock Information"→大口向けのアナウンスチャンネル　"📩｜DM"→チケットチャンネル」

既存サーバー: 「作り替える (推奨)」（自動セットアップをもう一度押すと、既存の「Sales Anchor」カテゴリを「📩｜DM」に名前変更し、アナウンスの2チャンネルをそれぞれ新しいカテゴリへ移動。チャンネルや会話は消さない（移動と名前変更のみ）。押さなければ変わらない）

## file:line 引用表（origin/main 4c17eeebe 時点・変更前）

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/routers/discord_auto_setup.py:227` | カテゴリ名が `"Sales Anchor"` で1つだけ作られる |
| `backend/app/routers/discord_auto_setup.py:250` | ticket-start は同カテゴリ配下（`existing_id=existing_ticket_ch_id` は :254） |
| `backend/app/routers/discord_auto_setup.py:266` | member-announcements も同カテゴリ配下（保存ID `existing_small_ch_id` は :270） |
| `backend/app/routers/discord_auto_setup.py:284` | partner-announcements も同カテゴリ配下（保存ID `existing_large_ch_id` は :288） |
| `backend/app/routers/discord_auto_setup.py:118` | `small_role_name` 既定 `Member`（:119 `large_role_name` 既定 `Partner`） |
| `backend/app/routers/discord_channel_invite.py:114` | `estimated_scale == "Small"` → `small_channel_id` |
| `backend/app/routers/discord_channel_invite.py:116` | `estimated_scale == "Large"` → `large_channel_id` |
| `backend/app/routers/discord_channel_invite.py:41` | `_SCALE_LABEL`: Small=小口 / Large=大口 |
| `backend/app/discord_gateway/ticket_channel_creator.py:257` | 新規チケットチャンネルは `ticket_category_id` 配下に作られる |
| `backend/app/services/discord_rest.py:34` | `discord_api_request` は任意 method（PATCH 可）を受ける |

## チャンネル ↔ 規模のマッピング（根拠）

【事実】small_channel_id = member-announcements = 小口（Small・Member ロール）、large_channel_id = partner-announcements = 大口（Large・Partner ロール）。根拠: `discord_channel_invite.py:114-117`（Small→small_channel_id / Large→large_channel_id）と `discord_auto_setup.py:266-288`（ch_member が small、ch_partner が large として保存）。よって 🍀（メンバー向け・小口）= member-announcements、🍒（大口向け）= partner-announcements。曖昧さなし。

## 設計制約の確認

- 新カテゴリの ID を保存する DB 列は追加しない（migration なし）。カテゴリは実行時に名前で検索する。🍀/🍒 は絵文字が異なり完全一致検索で一意に特定できる。
- `tenant_discord_ticket_config.ticket_category_id` は DM カテゴリを指す（新規チケットは📩｜DM 配下）。旧「Sales Anchor」を同一 ID のまま改名するため値は不変。

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | メンバー向け/大口向けとチャンネルの対応 | 上記 file:line | 解消済み |
| 2 | 新カテゴリ ID の保存要否 | 名前検索で足りる（DB 列追加なし） | 解消済み |
| 3 | 移動で個別権限が消えないか | Discord API は `lock_permissions` 未指定/false で overwrite を同期しない。コードは false を明示 | 解消済み（実機は PO 受入で確認） |

**未解決ゼロ確認**: 全て解消済み
