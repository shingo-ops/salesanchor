# recon: チケット案内文2種の英語化

- 日付: 2026-06-29
- 担当: Hikky-dev
- 関連: ADR-091

## 調査対象

①ボタン案内文（ticket-startチャンネル）と②専用チャンネル案内（ボタン押下後エフェメラル）の定義箇所特定。

## F1: ①ボタン案内文の定義箇所（2コードパス）

```
backend/app/routers/discord_auto_setup.py:591
    "content": "サポートが必要な場合は下のボタンを押してください。"
    → _post_ticket_button_step() 内 payload["content"]
    → 自動セットアップ時に呼ばれる

backend/app/routers/discord_ticket_config.py:257
    "content": "サポートが必要な場合は下のボタンを押してください。"
    → deploy_ticket_button() 内 payload["content"]
    → POST /admin/discord-ticket-config/deploy-button（管理画面から手動）
```

性質: コード固定定数。i18nキーなし。DB保存なし。

## F2: ②専用チャンネル案内文の定義箇所（1か所）

```
backend/app/discord_gateway/client.py:192-195
    await interaction.followup.send(
        f"専用チャンネルを用意しました → {channel.mention}",
        ephemeral=True,
    )
```

性質: コード固定。i18nなし。ボタン押下のたびに生成（毎回新規）。ephemeral=True（本人のみ）。

## F3: i18n・DB保存の有無

①②ともコード直書き日本語。`en.json`/`ja.json`に該当キーなし。
（`welcomeTemplateDefault`はticket作成時の歓迎メッセージ用・別概念）

## F4: ①の再投稿ロジック

`_ensure_ticket_button_step`（`discord_auto_setup.py:526-573`）は
直近50件から`custom_id=ticket_open`を検索し、見つかればskipする。

```python
# discord_auto_setup.py:563-569
for msg in messages:
    for row in msg.get("components", []):
        for component in row.get("components", []):
            if component.get("custom_id") == "ticket_open":
                return AutoSetupStep(step=step_name, status="skipped", ...)
```

→ コード英語化後に自動セットアップを再実行しても既存の日本語ボタンは差し替わらない。
→ 差し替え手順: Discord側で既存ボタンメッセージを手動削除 → deploy-button または auto-setup再実行。

## F5: ②の反映タイミング

コード変更後の次回チケット発行（ボタン押下）から自動的に新文言。再投稿不要。

## F6: テストのアサーション

```
backend/tests/test_discord_auto_setup.py:227  — _existing_button_msg の content
backend/tests/test_discord_auto_setup.py:874  — existing_button_messages の content
```

## 変更対象ファイル

| ファイル | 行 | 内容 |
|---|---|---|
| `backend/app/routers/discord_auto_setup.py` | 591 | ①ボタン案内文（auto-setupパス） |
| `backend/app/routers/discord_ticket_config.py` | 257 | ①ボタン案内文（deploy-buttonパス） |
| `backend/app/discord_gateway/client.py` | 193 | ②専用チャンネル案内 |
| `backend/tests/test_discord_auto_setup.py` | 227, 874 | テストアサーション追従 |
