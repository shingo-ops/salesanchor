# design: Discord ticket channel を gateway が取り込めるようにする

**対象ADR**: ADR-091  
**recon**: docs/handoff/discord-ticket-gateway-visibility/recon.md  
**日付**: 2026-06-19  
**担当**: Generator

---

## 1. 目的

private ticket channel で gateway bot が `Missing Access` にならず、`discord_guild_channel_id` を持つ lead として扱えるようにする。

---

## 2. 変更内容

1. ticket channel 作成時に bot の permission overwrite を追加する。
2. opener が lead でなければ lead を新規作成し、`discord_user_id` と `discord_guild_channel_id` を保存する。
3. 既存 lead がある場合は channel id を更新する。
4. 既存の lead/channel がある場合は冪等に既存 channel を返す。

---

## 3. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| gateway bot が ticket channel を閲覧できる | `backend/tests/test_discord_ticket_channel.py:105-157` の bot overwrite アサートが通る |
| opener が未 lead でも lead が作成される | `backend/tests/test_discord_ticket_channel.py:166-210` の lead 作成アサートが通る |
| 既存 lead は channel 再作成せずに返す | `backend/tests/test_discord_ticket_channel.py:214-254` の冪等性アサートが通る |
| migration を追加しない | 変更ファイルに `migrations/` が無いことを `git diff --name-only` で確認する |
| Meta 経路と guild 在庫解析を壊さない | ticket creator と test 追加のみで、`client.py` / `dm_writer.py` / `inbound_writer.py` を変更しない |

---

## 4. 外部・過去事例の参照と我々への応用

該当なし。今回は Discord の private channel 権限と lead 紐付けを既存列で補完する局所修正であり、外部事例よりも実コードの権限 overwrite と upsert 経路の整合が重要。
