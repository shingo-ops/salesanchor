# SA-04 実装 recon — 変更対象 file:line 調査

**日付**: 2026-06-12
**担当**: Terminal CC
**対象ブランチ**: feature/morimoto/sa04-impl

---

## 変更対象ファイル一覧

| # | ファイル | 理由 |
|---|---------|------|
| 1 | `scripts/setup_tenant.py:207-253` | lead_channels / UNIQUE / guild_id 各 migration を public/tenant 両リストに追記 |
| 2 | `scripts/db/sync_tenant_schema.py:323-344` | 同上（setup_tenant.py と同期必須） |
| 3 | `migrations/20260612_100000_add_contact_channel_unique.sql` | 新規: UNIQUE(contact_id, channel, COALESCE(purpose,'')) + guild_id catch-up |
| 4 | `migrations/20260612_110000_add_company_discord_guild_id.sql` | 新規: company_discord.guild_id VARCHAR(50) 追加 |
| 5 | `backend/app/routers/contacts.py:611` | `POST /contacts/{master_id}/merge` エンドポイント追加 |
| 6 | `backend/app/schemas/contact.py` | `ContactMergeRequest` スキーマ追加 |
| 7 | `frontend/src/components/MergeContactModal.tsx` | 新規: MergeLeadModal を担当者用に適応 |
| 8 | `frontend/src/components/ContactChannelForm.tsx` | 新規: チャネルID追加・編集フォーム（URL非表示） |
| 9 | `frontend/src/pages/company-detail/CompanyContactsTab.tsx` | チャネル管理 UI を組み込み |
| 10 | `frontend/src/pages/company-detail/company-detail.types.ts` | ContactChannel 型 + チャネルフォーム型追加 |
| 11 | `frontend/src/locales/ja.json` + `en.json` | mergeContact / contactChannel キー追加 |
| 12 | `docs/plans/sa-progress/SA-04-plan.md` | 判断 J1〜J4 記録 + ステータス→実装中 |

---

## ADR-119 PR-D 検証（既実装確認）

- `backend/app/discord_gateway/dm_writer.py:162` — `'Inbound'` を使用（`'prospect'` ではない）✓
- `backend/app/routers/webhook.py:325-329` — `messaging_policy_enforcement` フィルタ済み ✓
- `backend/app/routers/webhook.py:341,390,770` — `is_echo` ガード済み ✓

**判定**: PR-D は既に実装済み。追加作業不要。

---

## 既存コード流用箇所

- `backend/app/routers/leads.py:2005-2212` — merge API のロック→guard→FK付け替え→削除→監査ログ のパターンを contacts.py に移植
- `frontend/src/components/MergeLeadModal.tsx` — 2段階確認 UI を MergeContactModal.tsx に移植
- `migrations/20260607_120000_create_lead_channels.sql:1-80` — pg_namespace ループ形式（public_migrations リストに追加）
- `backend/app/auth/dependencies.py:387` — `tenant_table_ref()` を contacts merge API で使用
