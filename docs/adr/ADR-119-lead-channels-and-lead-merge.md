# ADR-119: lead_channels テーブル + リード統合エンドポイント

**Status**: Accepted（実装中）
**Date**: 2026-06-07
**Author**: Hikky-dev
**PO**: shingo-ops

---

## What（何を）

4つの PR で段階的に実装する。

| PR | 内容 |
|----|------|
| **PR-A** | `lead_channels` テーブル追加 + バックフィル（本 ADR 文書） |
| **PR-B** | `dm_writer.py` + `webhook.py` の lookup を `lead_channels` に切り替え |
| **PR-C** | `POST /leads/{master_id}/merge` エンドポイント（リード統合） |
| **PR-D** | `type='Inbound'` 統一 + Meta システム通知フィルタリング |

---

## Why（なぜ）

**現状の問題**:

1. **1 lead : 1 channel** — `leads.source` の文字列比較でプラットフォームを識別している。1人の顧客が Facebook Messenger と Instagram 両方でコンタクトしてきた場合、2つの別 lead として登録される。
2. **既存客への再接続が名寄せされない** — `existing_customer` リードにチャンネルが紐付けられないため、新規窓口からのメッセージが既存顧客カルテに届かない。
3. **型不統一** — `dm_writer.py` は `type='prospect'`、`webhook.py` は `type='Inbound'` と食い違っている。

---

## Scope

### PR-A: lead_channels テーブル（本 PR）

**新テーブル** `{schema}.lead_channels`:

| 列 | 型 | 説明 |
|----|-----|------|
| `id` | SERIAL PK | |
| `lead_id` | INTEGER NOT NULL → leads.id CASCADE DELETE | |
| `platform` | VARCHAR(30) NOT NULL | `'messenger'` / `'instagram'` / `'discord'` |
| `external_id` | VARCHAR(255) NOT NULL | PSID / IGSID / Discord UID |
| `display_name` | VARCHAR(255) | プラットフォーム側の表示名（任意） |
| `created_at` / `updated_at` | TIMESTAMPTZ | |

制約: `UNIQUE (platform, external_id)` — 1 チャンネル → 1 リード（テナントスコープ内）

バックフィル: 既存 `leads.source`（`messenger:*` / `instagram:*` / `discord:*`）と `leads.discord_user_id` から移植。

### PR-B: lookup 切り替え

`dm_writer.py` と `webhook.py` の `WHERE source = :source` を
`WHERE lc.platform = :platform AND lc.external_id = :external_id` に変更。

lead 新規作成時は同一トランザクション内で `lead_channels` にも INSERT する。

### PR-C: リード統合エンドポイント

```
POST /leads/{master_id}/merge
Body: { "loser_id": <int> }
```

**guard 条件**: `loser.converted_deal_id IS NOT NULL` → 400 ブロック

（master が `existing_customer` / `converted_deal_id` 非NULL は許可。コア用途 = 既存客への再接続。）

**guard ガイドライン**:

| master | loser | 判定 |
|--------|-------|------|
| 既存客（converted） | 新規リード（未converted） | ✅ 許可（コア用途） |
| 新規リード | 新規リード | ✅ 許可 |
| 何でも | 既存客（converted） | ⛔ v1 ブロック |

**処理順序**（同一トランザクション・FOR UPDATE ロック）:

1. master / loser を `FOR UPDATE` でロック（昇順 ID・デッドロック防止）
2. guard チェック: `loser.converted_deal_id IS NOT NULL` → 400
3. FK 付け替え: `companies` / `contacts` / `deals` の `lead_id = loser.id` → `master.id`
4. `meta_messages` の `lead_id = loser.id` → `master.id`（ON DELETE SET NULL に委ねない）
5. `lead_channels` の `lead_id = loser.id` → `master.id`（重複は DO NOTHING）
6. loser 削除（`converted_deal_id = NULL` が前提）
7. 監査ログ 2 件

### PR-D: type 統一 + Meta システム通知フィルタリング

- `dm_writer.py`: `type='prospect'` → `type='Inbound'`（ADR-109 準拠）
- `webhook.py` Format A: `is_echo` guard 既存済み
- `webhook.py` Format B: システム通知フィルタリング追加（`messaging_policy_enforcement` 等）

---

## 非機能要件

- 全 migration は冪等（`IF NOT EXISTS` / `ON CONFLICT DO NOTHING`）
- `lead_channels` の GRANT は `ALTER DEFAULT PRIVILEGES`（SA-18）で自動付与済み
- `source` 列は UI 自由記述として維持（対応B）、`lead_channels` が lookup 権威
- PO チェックポイント: 本番 migration GO（`lead_channels` 作成 = 本番DB変更）

---

## 関連 ADR

- ADR-015: leads テーブル基盤
- ADR-109: status SSOT（`existing_customer` コード確定）
- ADR-SA-18: salesanchor_app ロール（GRANT 自動付与の根拠）
