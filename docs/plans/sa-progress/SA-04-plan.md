# SA-04 計画票 — 多チャネル名寄せ＋リンクテンプレSSOT

| 項目 | 内容 |
|------|------|
| 対応ADR | ADR-098（正本）、関連: ADR-119（lead_channels）、ADR-091（Discord Bot）、前提: ADR-095/096 |
| ステータス | ② recon（KGI承認済み 2026-06-12） |
| 担当 | PO: Shingo ／ Planner: Web Claude ／ recon・実装: Terminal CC |
| 最終更新 | 2026-06-12（Terminal CC・recon完了） |

---

## 1. 計画票（スケジュール）

| # | ステップ | 担当 | 状態 | 完了日 |
|---|---------|------|------|--------|
| 1 | KGI承認 | Shingo | ✅ 完了 | 2026-06-12 |
| 2 | recon指示 | Planner | ✅ 完了 | 2026-06-12 |
| 3 | architect recon（file:line差分表） | Terminal CC | ✅ 完了 | 2026-06-12 |
| 4 | 差分レビュー＋残作業確定 | Shingo＋Planner | 未 | |
| 5 | 設計確定（残作業分） | Planner | 未 | |
| 6 | 実装 | Generator（Terminal CC） | 未 | |
| 7 | 検証ゲート | 自動＋Reviewer | 未 | |
| 8 | KGI実測＋SA-01横断チェック | Shingo | 未 | |

---

## 2. KGI定義（承認済み: Shingo 2026-06-12）

| # | KGI | 種別 |
|---|-----|------|
| G1 | 連絡先のチャネル情報は**ID**（WhatsApp=電話番号、Discord=サーバー/チャンネルID等）で保存。**手入力のURL欄が0個**＝腐ったリンクが構造的に発生しない | データ構造（SSOT） |
| G2 | リンクの「URLの組み立て方」は**テンプレ表1か所**だけが持つ。型の変更は1行の修正で全顧客に一斉反映 | SSOT |
| G3改 | 連絡先タブで**クリック1回**で顧客スレッドを開ける。**チャネルの追加・編集は同タブからID単位**（URL文字列は見せない・編集させない）。**重複IDは保存前に警告し、統合への導線**を出す | UI/UX＋ポカヨケ |
| G4 | 複数チャネルから来ても**1顧客1カルテ**。自動の同一人物判定は**しない**（誤マージ0）。統合は人がUIから明示的に実行 | 名寄せ |

**注記**: Messenger/InstagramはMeta非公式の内部URLのため壊れ得る。安定保証の対象はWhatsApp/Telegram/Discordの3チャネル。Meta系は「テンプレ表の1セルに隔離され、壊れてもそこだけ直せる構造」が合格条件（ADR-098準拠）。

---

## 3. 現状調査結果と差分（recon記入欄）

| 観点 | 現状（file:line） | 理想 | 差分 |
|------|-------------------|------|------|
| lead_channels（ADR-119 PR-A〜D）の完了状況 | PR-A（テーブル）: `migrations/20260607_120000_create_lead_channels.sql:16-26`（SERIAL PK, platform/external_id VARCHAR, UNIQUE(platform,external_id)）✓。PR-B（lookup切替）: `backend/app/routers/webhook.py:489-498`・`backend/app/discord_gateway/dm_writer.py:105-120` ✓。PR-C（merge API）: `backend/app/routers/leads.py:2005-2212` ✓。**PR-D（型統一）: `docs/adr/ADR-119-lead-channels-and-lead-merge.md:14-19` → PENDING。** さらに `scripts/setup_tenant.py` に lead_channels catch-up が未追記（新テナント未適用リスク） | テーブル・lookup切替・merge API・型統一すべて完了 | **PR-D（型統一）未完成**。新テナント setup 未登録（`scripts/setup_tenant.py` / `scripts/db/sync_tenant_schema.py` に追記必要） |
| 連絡先タブの現状（手入力URL欄の有無） | `frontend/src/pages/company-detail/CompanyContactsTab.tsx:97-169`：フォームフィールドは display_name/name/email/phone のみ。URL 入力欄なし ✓。チャネル表示は `frontend/src/components/ContactChannelLinks.tsx:15-21`（ChannelLink: channel/url/is_verified/label/notes）— url はサーバー生成、入力フィールドなし ✓ | URL欄0 | **チャネル追加・編集フォームの存在確認が未完**（ContactChannelLinks.tsx はリスト表示のみ。チャネルをID単位で追加・編集するフォームが別途必要か調査要） |
| チャネルIDの保存実態（ID/URL混在箇所） | `migrations/030_create_company_contact_subtables.sql:119-134`：`contact_contact_channels(channel VARCHAR30, purpose VARCHAR50, guild_id VARCHAR50)`— URLカラムなし ✓。`migrations/20260607_120000_create_lead_channels.sql:19-20`：`lead_channels(platform VARCHAR30, external_id VARCHAR255)`— IDのみ ✓。URL生成は `backend/app/routers/contact_channel_links.py:44-115`（`_build_url` が `link_templates.url_pattern` を受け取り on-demand 生成） | ID保存に統一 | 保存層はID統一済み。**未調査: チャネル編集フォームで purpose に URL 文字列をそのまま入力できるか否か**（フロントのバリデーション確認要） |
| リンクテンプレ表（SSOT）の有無・channel_mastersとの統合可否 | `migrations/20260604_090000_create_link_templates.sql:13-29`：`public.link_templates(channel PK, url_pattern TEXT, required_ids JSONB, is_verified BOOL, notes TEXT)` — 5チャネル（whatsapp/telegram/discord/messenger/instagram）シード済み ✓。`_build_url` は `link_templates.url_pattern` を引数で受け取り `contact_channel_links.py:163-165` で `public.link_templates` から取得 ✓。`migrations/20260611_100000_create_channel_masters.sql:42-54`：`channel_masters(id, tenant_id, platform, display_name, connection_type, is_active)`— `url_pattern` 列なし | テンプレ1か所 | **link_templates が既に SSOT として機能している（G2 構造充足）**。channel_masters に url_pattern を追加すれば統合可能だが、目的が異なる（link_templates=公開チャンネルURLカタログ、channel_masters=テナント単位の手動/auto管理）→ **Shingo判断: 統合 vs 分離維持** |
| Discord guild_id/channel_id保存とリンク生成（ADR-091被覆率） | `migrations/097_create_company_discord.sql:36-46`：`company_discord(channel_id VARCHAR50, user_id VARCHAR50, invoice_webhook, shipment_webhook)`— guild_id 列なし（注: channel_id という列名で Discord チャンネルID を保存）。`migrations/20260604_100000_add_guild_id_to_contact_channels.sql:35`：`contact_contact_channels.guild_id VARCHAR50` 追加済み。URL生成: `backend/app/routers/contact_channel_links.py:82-87` → `https://discord.com/channels/{guild_id}/{channel_id}` ✓。テナント guild_id: `public.tenant_discord_config` に保管（ADR-091） | 安定リンク生成 | `company_discord` に guild_id 列がない（カラム名の混乱: `channel_id` が実際は Discord チャンネルID）。会社レベルのDiscordリンクを生成する際の guild_id 取得経路が不明確 |
| 重複ID防止と統合UI（API有無・画面有無） | `migrations/030:132-136`：`contact_contact_channels` に UNIQUE(contact_id) WHERE is_primary=TRUE のみ — **同一 channel+purpose の重複行を防ぐ UNIQUE 制約なし**。`lead_channels`：UNIQUE(platform, external_id) ✓。`frontend/src/components/MergeLeadModal.tsx:2-6`：リード用統合UI存在 ✓。`backend/app/routers/contacts.py`：merge エンドポイントなし。`backend/app/schemas/contact.py:36`：`pending_dedup_review` ステータス存在 | 警告＋統合導線 | **contact_contact_channels に (channel, purpose) UNIQUE 制約なし → 重複ID保存が可能**（K5未達）。担当者レベルの dedup UI・merge API なし（G3/G4 部分未達）|
| Meta系内部URLの隔離構造 | `migrations/20260604_090000_create_link_templates.sql:27-28`：messenger/instagram を `is_verified=FALSE, notes="Meta内部URL・Meta担当パートナー検証待ち"` で link_templates に1行ずつ管理 ✓。`backend/app/routers/contact_channel_links.py:89-100`：`_build_url` が link_templates から受け取った url_pattern を使用（ハードコードなし） ✓ | 1セル隔離 | **構造的には隔離済み（G2/ADR-098 充足）**。Messenger は psid+page_id+bm_id すべて揃わないと URL 未解決（None 返却）— page_id/bm_id 取得経路が contact レベルでは未整備 |
| WhatsApp/Telegramの接続・ID保存の現状 | WhatsApp: `contact_channel_links.py:69-73` — purpose に電話番号、`wa.me/{phone}` 生成 ✓。Telegram: `contact_channel_links.py:75-80` — purpose にユーザー名、`t.me/{username}` 生成 ✓。API/Bot接続: なし（`backend/app/routers/webhook.py` に whatsapp/telegram ハンドラなし）。`channel_masters`：whatsapp/telegram はシード未登録（phone/in_person のみ） | ID保存（未連携ならSA-02手動チャネルとの整理方針を要判断） | WhatsApp/Telegram は**API未連携・手動チャネル運用**。channel_masters に whatsapp/telegram エントリなし。**Shingo判断: SA-02 channel_masters の手動チャネルとして whatsapp/telegram を追加するか、現行の contact_contact_channels のままにするか** |

### recon結論（2026-06-12 Terminal CC）

**流用できるもの（7点）:**
1. `public.link_templates` — url_pattern SSOT として稼働中（G2 構造充足）`migrations/20260604_090000_create_link_templates.sql:13-29`
2. `contact_contact_channels(purpose, guild_id)` — ID保存済み（URLカラムなし・G1 構造充足）`migrations/030:119-134`
3. `backend/app/routers/contact_channel_links.py:_build_url` — link_templates を読んで on-demand URL 生成（G2 実装充足）
4. lead_channels PR-A/B/C — テーブル・lookup切替・merge API 完成（G4 lead 層充足）`migrations/20260607_120000, backend/app/routers/leads.py:2005-2212`
5. Discord guild_id + channel_id 保存 + 安定 URL 生成 `contact_channel_links.py:82-87`
6. `MergeLeadModal.tsx` — 2段階統合UI（リード用）をコンタクト用に流用可能
7. Meta URL は `link_templates` 1セルに隔離済み（is_verified=FALSE 管理）

**不足しているもの（6点）:**
1. **ADR-119 PR-D（型統一）未完**：`docs/adr/ADR-119:14-19`
2. **lead_channels が新テナント setup 未登録**：`scripts/setup_tenant.py` / `scripts/db/sync_tenant_schema.py` に catch-up 追記必要
3. **contact_contact_channels に重複ID防止 UNIQUE 制約なし**：UNIQUE(contact_id, channel, purpose) 追加必要（K5 達成）
4. **担当者レベル merge API・dedup UI がない**：`backend/app/routers/contacts.py` に `/merge` エンドポイント追加 + MergeLeadModal 相当の UI 新設
5. **チャネル追加・編集フォーム（ID入力、URL非表示）**：CompanyContactsTab に ID 単位でチャネルを追加・編集できる UI が未確認（要追加調査または新設）
6. **company_discord に guild_id 列なし**：会社レベルの Discord リンク生成経路が不完全

**Shingo判断が必要な事項（4点）:**
1. **link_templates と channel_masters の統合方針**：channel_masters に url_pattern 列を追加して link_templates を廃止するか（統合・テナント分離）、link_templates を公共カタログとして維持するか（分離・現状維持）。設計影響大のため SA-04 着手前に確定要
2. **WhatsApp/Telegram の扱い**：API未連携なので SA-02 channel_masters の手動チャネルとして追加するか、contact_contact_channels のまま维持するか
3. **担当者 merge UI のスコープ**：SA-04 内に contact merge endpoint + UI を含めるか、別SA（SA-05以降）とするか
4. **Messenger psid+page_id 取得経路**：contact レベルで page_id/bm_id が取れないため Messenger URL が None になるケースあり。Meta 担当パートナーとの検証状況と合わせて方針確定要

---

## 4. KPI設定（recon後に確定）

| # | KPI候補 | 目標 | 測り方 |
|---|---------|------|--------|
| K1 | 手入力URL欄の残存 | 0個 | コード確認 |
| K2 | スレッド到達クリック数 | 1 | UIレビュー |
| K3 | 誤マージ（他人の合体） | 0件 | ガード＋監査 |
| K4 | リンク型変更の修正箇所 | 1か所 | テンプレ表検証 |
| K5 | 重複ID登録の阻止 | 100% | UNIQUE制約＋警告テスト |

---

## 5. 実装記録

| 日付 | PR | 内容 | 状態 |
|------|----|------|------|
| | | | |

---

## 6. チェックシート（完了条件）

- [x] ① KGI承認（Shingo 2026-06-12）
- [x] ② recon完了（file:line差分表 2026-06-12）
- [ ] ③ 設計確定（残作業分）
- [ ] ④ 実装PRマージ
- [ ] ⑤ 本番反映
- [ ] ⑥ KGI G1〜G4実測＋SA-01横断チェック
- [ ] 総合進捗表の更新
