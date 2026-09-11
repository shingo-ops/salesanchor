# design: Discord アナウンス表示出し分け＋403＋不明剥奪（1本目）

- Planner（Web Claude）/ 2026-06-29 / base: origin/main ed01800e
- 関連 recon: docs/handoff/discord-announce-scale-visibility/recon.md
- 関連 ADR: ADR-146（Discord 共通bot単一・guild_id 振り分け／本PRは踏襲・変更なし）

## §1 KGI（PO承認済み・実機 006_test/004-test 目視）
3アカウント（大口/小口/不明）で:
1. 大口: partner-announcements 見える / member-announcements 見えない
2. 小口: member-announcements 見える / partner-announcements 見えない
3. 不明: 両方見えない
4. 大口→不明に変更後、partner-announcements が消える（自動剥奪の実証）
5. bot テスト投稿が member-announcements に出る（403なし）
6. bot テスト投稿が partner-announcements に出る（403なし）

## §2 変更内容（変更前後・file:line）
### 穴①: 小口棚から大口許可削除（discord_auto_setup.py）
- _member_announcements_overwrites の partner_role_id ブロックを削除。
- シグネチャから partner_role_id を削除。呼び出し（:271）から partner_role_id を除去。

### 穴②: 両棚に bot 書込 overwrite 追加（discord_auto_setup.py）
- 前例 _ticket_ch_overwrites:658-665 と同パターンで type=1 overwrite を return 直前に追加。
- _member / _partner 両関数に bot_user_id: str = "" を追加。呼び出し（:271/:289）に bot_user_id=bot_user_id。

### 穴③: 不明で全管理ロール剥奪（discord_role_sync.py）
- bot_token/guild_id 取得を不明判定の前へ一本化（付与パスは取得位置が前進しただけで挙動不変）。
- new_scale not in _SCALE_TO_COLUMN の分岐を「スキップ return」から
  「管理ロール（small/large）を本人の現在ロールと突合し、保有分のみ DELETE → return」へ変更。
- 剥奪成功時のみ success、DiscordAPIError 時は failed を記録（success 誤記録を防止）。
- role_name = scale_to_role[new_scale] を不明分岐の後ろへ移動（KeyError 回避）。

## §3 触らない範囲
- ticket-start / _ticket_ch_overwrites:637（PR #2655 確定分）
- カテゴリ生成・統合構成（:207-235、カテゴリ分離はしない）
- ADR-146 guild_id 振り分け・受信B方式
- leads.py:652-655 の自動トリガー条件
- 在庫データ／価格出し分け（=2本目の別PR）

## §4 既知の残課題（本PR対象外・次PR候補）
- 剥奪は estimated_scale 更新トリガー時のみ発火（leads.py:652-655 仕様の素直な帰結）。
  「過去に大口・今後 estimated_scale を触らない不明客」の一括棚卸しは別タスク。

## §5 外部事例・過去事例
- 過去事例: PR #2644（ticket-start の bot overwrite 欠落による 403/50013 を type=1 付与で解消）。
  本PRの穴②は同根の欠落を announcements 2チャンネルへ水平展開したもの。
- Discord Permissions: カテゴリの @everyone deny がチャンネルへ継承される仕様（Discord API 公式の
  permission overwrite 継承モデル）に基づき、bot 個別 overwrite で明示許可する。
- ロール方式採用理由: 既存 auto-setup が type=0（ロール単位）で統一。ユーザー個別 overwrite 方式は
  保守コスト増のため不採用（recon B 準拠）。
