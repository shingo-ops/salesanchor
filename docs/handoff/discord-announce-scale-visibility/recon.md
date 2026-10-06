# recon: Discord アナウンス表示出し分け＋403＋不明剥奪（1本目）

- 実施: 2026-06-29 / Planner（Web Claude）＋ Generator（Terminal CC）
- worktree: /tmp/sa-announce-split / base HEAD: ed01800e（origin/main, PR #2675 マージ後）
- 方針: recon先行・推測禁止。下記はすべて実コード file:line 引用。

## A. 顧客規模(大口/小口/不明)の保存場所
- leads.estimated_scale（VARCHAR(20)）= migrations/003_add_phase1_tenant_tables.sql:87
- 値は "Small" / "Large" の2系統。Medium/NULL は discord 文脈で非マッピング。
  - backend/app/services/discord_role_sync.py:35-37 `_SCALE_TO_COLUMN = {"Small":..,"Large":..}`
- 規模 ↔ Discord は同一行で完結（FK/JOIN 不要）:
  - leads.discord_user_id（migrations/091_add_leads_discord_messaging_columns.sql:30）
  - backend/app/routers/discord_role_resync.py:57 `SELECT discord_user_id, estimated_scale FROM {leads_t} WHERE id=:id`

## B. 表示制御の既存手段（ロール方式）
- ロール名は DB 設定（既定 Member/Partner）:
  - backend/app/routers/discord_auto_setup.py:129-130 small_role_name/large_role_name
- announcements 2チャンネルは同一カテゴリ配下（parent_id=category_id）:
  - discord_auto_setup.py:266（member-announcements）/ :284（partner-announcements）
- overwrite はロール単位（type=0）。ユーザー個別（type=1）は ticket/カテゴリのみ:
  - 前例 _ticket_ch_overwrites:658-665（bot_user_id type=1）

## C. 確認された3つの穴（本PRで修正）
1. 小口棚に大口許可が混在（KGI①違反）:
   - discord_auto_setup.py（修正前）_member_announcements_overwrites 内 partner_role_id ブロック
2. announcements 2チャンネルに bot 書込 overwrite 欠落（403/50013, KGI④⑤違反）:
   - _member_announcements_overwrites:671 / _partner_announcements_overwrites:718 に bot_user_id 引数なし
   - 継承元: カテゴリ @everyone deny SEND（discord_auto_setup.py:207-214）
3. 不明(NULL/Medium)へ戻した際、既存管理ロールが剥奪されない（KGI③違反）:
   - discord_role_sync.py:162-168（修正前）`if new_scale not in _SCALE_TO_COLUMN: ... return`（剥奪に到達しない）
   - 既存剥奪は Small↔Large 付け替え時のみ（discord_role_sync.py 付与パス内）

## D. トリガー経路（挙動は変更しない）
- 自動: leads.py:652-655（estimated_scale 更新時 fire-and-forget。discord_user_id 空ならスキップ）
- 手動: discord_role_resync.py:74（POST /discord/sync-role/{lead_id}）
- 本PRは sync 経由の挙動のみ修正。leads.py トリガー条件は不変。
