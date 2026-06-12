# SA-04 実装設計書

**ADR**: ADR-098（正本）、ADR-119（lead_channels）
**ステータス**: 実装中（2026-06-12 Shingo 判断 J1〜J4 確定）
**担当**: Terminal CC

---

## 確定判断（Shingo 2026-06-12）

| 判断 | 内容 |
|------|------|
| J1 | link_templates と channel_masters は分離維持（link_templates = 全テナント共通 URL パターン SSOT） |
| J2 | チャネルID（電話番号/username 等）は contact_contact_channels に保存。会話記録チャネルは channel_masters。同一事実の二重持ち禁止 |
| J3 | 担当者レベルの統合を SA-04 スコープに含める（重複 ID 警告 → 統合ボタン） |
| J4 | Messenger 等で page_id 欠如時はリンク生成・表示なし。本格対応は Meta パートナー検証待ち |

---

## 実装スコープ（recon 不足 6 点 → ADR-119 PR-D は既実装済みのため 5 点）

### [M-1] contact_contact_channels UNIQUE 制約（migration 必須・Shingo GO）

```
migrations/20260612_100000_add_contact_channel_unique.sql
```

- `UNIQUE(contact_id, channel, COALESCE(purpose, ''))` を全テナントに追加
- 事前確認: 本番 DB で重複行 = 0（recon 時に確認済み）
- 冪等: `CREATE UNIQUE INDEX IF NOT EXISTS`

| 基準 | 検証方法 |
|------|----------|
| 重複 ID 保存が DB レベルで阻止される | `INSERT ... ON CONFLICT` で 23505 エラーが発生すること |
| 既存データへの影響なし | migration 実行後 既存行数が変わらないこと |

### [M-2] company_discord.guild_id 追加（migration 必須・Shingo GO）

```
migrations/20260612_110000_add_company_discord_guild_id.sql
```

- `ALTER TABLE company_discord ADD COLUMN IF NOT EXISTS guild_id VARCHAR(50)`
- 会社レベルの Discord リンク生成に guild_id を使えるようにする（ADR-098 G2 補完）

| 基準 | 検証方法 |
|------|----------|
| guild_id 列が全テナントの company_discord に存在 | `\d tenant_001.company_discord` で確認 |

### [B-1] setup_tenant.py + sync_tenant_schema.py に catch-up 追加（コードのみ・CI 緑で可）

追加する migration（public_migrations リスト）:
- `20260607_120000_create_lead_channels.sql` — lead_channels テーブル（pg_namespace ループ形式）
- `20260612_100000_add_contact_channel_unique.sql` — UNIQUE 制約
- `20260612_110000_add_company_discord_guild_id.sql` — guild_id 追加

### [B-2] contact merge API（コードのみ・CI 緑で可）

```
POST /contacts/{master_id}/merge
Body: { "loser_id": int, "reason": str | null }
```

guard: `loser` が deals/orders/quotes/invoices を持つ場合は 400 ブロック（ADR-119 PR-C 相当の安全ガード）
処理順序:
1. FOR UPDATE ロック（昇順 ID）
2. guard: loser が deal/order/quote/invoice を持つ → 400
3. FK 付け替え: deals / orders / quotes / invoices の contact_id → master
4. contact_contact_channels を master へ再ポイント（UNIQUE 衝突は重複削除で吸収）
5. loser 削除
6. 監査ログ 2 件

| 基準 | 検証方法 |
|------|----------|
| 正常統合で loser が削除され master に FK 付け替えが完了 | POST 後に loser の GET が 404 |
| guard 違反で 400 が返る | deal 付き contact を loser 指定 → 400 |

### [F-1] ContactChannelForm（フロントエンド・CI 緑で可）

- チャネル種別セレクト（whatsapp/telegram/discord/instagram/messenger + その他）
- ID 入力欄（ラベルはチャネルで変わる: 電話番号 / ユーザー名 / サーバー ID 等）
- Discord: guild_id 入力欄を追加で表示
- URL 入力欄なし（G1 SSOT 維持）
- 保存前に重複チェック: 同一 channel + purpose が別 contact に存在 → 警告表示（J3）

### [F-2] MergeContactModal（フロントエンド・CI 緑で可）

- MergeLeadModal を担当者用に適応
- API: `POST /contacts/{master_id}/merge`
- 候補一覧は会社内担当者（`GET /companies/{company_id}/contacts`）から取得
- 2 段階確認 UI（select → confirm）

---

## 弊害・リスク

| リスク | 対策 |
|--------|------|
| UNIQUE 制約追加で既存重複行が migration 失敗 | 事前に重複 0 確認済み（recon 時）。それでも migration は重複チェック付き |
| contact merge で deal/order FK が宙に浮く | guard: loser に deal/order があれば 400 |
| guild_id 列追加でアプリが余計なフィールドを拾う | ADD COLUMN IF NOT EXISTS のみ、既存 SELECT に影響なし |

---

## 外部事例参照

ADR-119 PR-C（`backend/app/routers/leads.py:2005-2212`）— 同一プロジェクト内の merge パターンを移植。実績 = 本番稼働中。
