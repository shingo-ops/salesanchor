# Phase 3 設計 — Discord 自動セットアップのカテゴリ3分割

**対象ADR**: ADR-091・ADR-159  
**recon**: docs/handoff/discord-setup-categories/recon.md  
**日付**: 2026-10-02  
**担当**: Dev（Sonnet）／設計: Opus

## PO 決定（原文）

recon.md の「PO 依頼（原文）」参照（カテゴリ名3種・メンバー向け/大口向けの分離・既存サーバーは「作り替える (推奨)」）。

## 変更前後

| 項目 | 変更前 | 変更後 |
|---|---|---|
| カテゴリ | `Sales Anchor` 1つ（3チャンネル同居） | `📩｜DM`（ticket-start）/ `🍀｜Stock Information`（member-announcements・小口）/ `🍒｜Stock Information`（partner-announcements・大口） |
| カテゴリ名の置き場 | ルーター内リテラル | `backend/app/discord_gateway/bot_texts.py` の `CATEGORY_*`（SSOT） |
| 既存サーバーで再実行 | 何も変わらない | 旧 `Sales Anchor`（保存済み ticket_category_id）を `📩｜DM` へ名前変更（ID 不変）→ 🍀/🍒 を名前で検索し無ければ作成 → 保存済み small/large チャンネルを PATCH で移動（`lock_permissions=false`） |
| 再実行2回目 | - | 変更なし（名前一致・親一致でスキップ。重複作成なし） |
| 管理画面（結果表示） | category の1行 | category / category_stock_member / category_stock_large の3行・新ステータス「更新（名前変更・移動）」 |

触らない範囲: チャンネル名・ロール・permission_overwrites・DB スキーマ（migration なし）・Webhook/ボタン投稿・既存チケットチャンネル（DM カテゴリに残る）。チャンネル・メッセージの削除は一切しない。

## 外部・過去事例の参照と我々への応用

- 過去事例（自社）: `docs/handoff/discord-auto-setup/design.md` の冪等方針（保存ID → 名前検索 → 作成）。応用: 新カテゴリも名前検索で冪等にし、DB 列を増やさない。
- 外部事例: 該当なし（Discord REST の Modify Channel（`name` / `parent_id` / `lock_permissions`）による既存チャンネルの改名・移動のみで、外部事例に依存しない）。

## 受入条件

| 基準 | 検証方法 |
|---|---|
| 新規セットアップで3カテゴリが作られ、ticket-start=📩｜DM・member-announcements=🍀・partner-announcements=🍒 配下になる | `backend/tests/test_discord_auto_setup.py::test_fresh_setup_creates_three_categories_with_channels_under_each` |
| 旧構成の再実行で、カテゴリが ID 不変のまま 📩｜DM に改名され、アナウンス2チャンネルが移動し、DELETE が呼ばれず、権限を同期しない | `backend/tests/test_discord_auto_setup.py::test_rerun_migrates_legacy_setup_rename_and_move_without_delete` |
| 2回実行しても重複・追加 PATCH が発生しない | `backend/tests/test_discord_auto_setup.py::test_rerun_twice_is_idempotent_no_duplicates` |
| DB に small/large が未保存でも旧カテゴリ配下の同名チャンネルを重複作成せず移動する | `backend/tests/test_discord_auto_setup.py::test_rerun_without_stored_ids_finds_legacy_announcements_and_moves_them` |
| 移動失敗は partial で報告し、何も削除しない | `backend/tests/test_discord_auto_setup.py::test_move_failure_is_reported_and_nothing_deleted` |
| カテゴリ名が PO 指定どおり（全角縦線 U+FF5C） | `backend/tests/test_discord_auto_setup.py::test_category_names_are_po_specified` |
| 管理画面ラベルが ja/en 同一キー | CI（i18n キー一致チェック） |
| 本番: PO が tenant_001 で自動セットアップを再実行し、📩｜DM / 🍀｜Stock Information / 🍒｜Stock Information が正しいチャンネルを持つ。新規チケットは 📩｜DM 配下に作られる。チャンネルが1つも消えていない | PO が Discord で確認（本 PR の外） |

## 技術 How・KPI

- KPI: 再実行後のチャンネル消失 0 件・カテゴリ重複 0 件（tenant_001 を PO が目視）。
- 技術選択: DB 列を足さず実行時に名前検索（migration を避けるため）。改名は PATCH `/channels/{id}` の `name`、移動は `parent_id` + `lock_permissions=false`。

## 弊害・トレードオフ

- Bot に Manage Channels が無いと PATCH が 403 → 該当ステップのみ failed（partial）・何も壊れない。再実行で復帰可能。
- 旧カテゴリを PO が手で別名にしていた場合は改名しない（旧名 `Sales Anchor` のときだけ改名）。その場合 ticket-start 等は現在の親のまま、新2カテゴリのみ作成されアナウンスだけ移動する。
- 🍀/🍒 を PO が手で改名していると名前検索に外れて新規作成される（手動改名時のみ）。

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | bot_texts に CATEGORY_* 追加 | Sonnet |
| 2 | discord_auto_setup.py: `_ensure_dm_category_step` / `_ensure_channel_parent_step` 追加・チャンネル作成先を3カテゴリへ | Sonnet |
| 3 | フロント: ステップ名・ステータス `updated` の i18n 追加 | Sonnet |
| 4 | テスト追加・既存テスト更新 | Sonnet |

## 継続

- 完了後の監視: PO 受入（上表の本番行）。
- 次フェーズ: 在庫アナウンスの大口/メンバー分離配信は別便（本便はカテゴリ構成のみ）。
