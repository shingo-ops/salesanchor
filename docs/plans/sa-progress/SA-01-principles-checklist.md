# SA-01 横断合格基準チェックシート

> **これは何？** ADR-095が定める「SSOT・2本背骨・派生値・ポカヨケ」原則が、各SAで守られているかを確認するための横断チェックリスト。
> **使い方**: 各SA実装PR完了時（フェーズ④通過後）に、該当SAのチェック欄を埋める。全チェック✅が本番反映（フェーズ⑤）への条件。
> **正本ADR**: `docs/adr/ADR-095-sa-ssot-two-backbone-architecture.md`

---

## チェック項目

### 原則1: SSOT（保管庫は1か所）

| チェック | SA-02 | SA-03 | SA-04 | SA-05 | SA-06 | SA-07 | SA-12 |
|---------|-------|-------|-------|-------|-------|-------|-------|
| 同じ事実を手入力で複数箇所に持っていない | ⬜ | ✅ | ✅ | ⬜ | ⬜ | ⬜ | ⬜ |
| マスタの変更が全下流に自動反映される | ⬜ | ✅ | ✅ | ⬜ | ⬜ | ⬜ | ⬜ |

> SA-03 根拠: フォーム送信→`companies`/`company_addresses`/`contacts` への直接INSERT（手転記なし）。`GET /companies/:id` が即反映（`registration_tokens.py:215-299`）。

> SA-04 根拠: チャネルIDは `contact_contact_channels.purpose` 1か所のみ保存（URLカラムなし `migrations/030:119-134`）。`public.link_templates.url_pattern` を変更すると全テナント・全連絡先に即反映（`contact_channel_links.py:163-165`）。本番検収でwa.meリンクが番号IDから自動生成されることを確認（Shingo 2026-06-13）。

### 原則2: 派生値は自動計算のみ（手入力禁止）

| チェック | SA-02 | SA-03 | SA-04 | SA-05 | SA-06 | SA-07 | SA-12 |
|---------|-------|-------|-------|-------|-------|-------|-------|
| 書き込み可能な派生値カラムが存在しない | ⬜ | ✅ | ✅ | ⬜ | ⬜ | ⬜ | ⬜ |
| UI・APIに派生値の上書きエンドポイントがない | ⬜ | ✅ | ✅ | ⬜ | ⬜ | ⬜ | ⬜ |

> SA-03 根拠: `registration_tokens` テーブルに派生値カラムなし。公開エンドポイントは新規INSERT専用で上書きパスなし（`registration_tokens.py:380-408` — INSERT only, ON CONFLICT なし）。

> SA-04 根拠: `contact_contact_channels` にURL派生値カラムなし（`migrations/030:119-134`）。チャネル編集フォームはID（purpose）入力のみ（URL文字列フィールドなし）。`GET /.../contact-channel-links` がオンデマンドURL生成 — 書き込みパスなし（`contact_channel_links.py:44-115`）。本番検収でURL入力欄がないことを確認（Shingo 2026-06-13）。

### 原則3: ポカヨケ（設計で防ぐ）

| チェック | SA-02 | SA-03 | SA-04 | SA-05 | SA-06 | SA-07 | SA-12 |
|---------|-------|-------|-------|-------|-------|-------|-------|
| 対応するKPI事故系（ADR-095 KPI#1〜5・8）が実装されている | ⬜ | ✅ | ✅ | ⬜ | ⬜ | ⬜ | ⬜ |
| 計測素データ（ログ）が最初から残っている | ⬜ | ✅ | ✅ | ⬜ | ⬜ | ⬜ | ⬜ |

> SA-03 根拠: 誤テナント登録 → HMAC-SHA256 検証でテナント分離（`registration_token.py:120-148`）。`registration_tokens.used_at` により使用ログ保持。二重使用防止（`used_at IS NOT NULL` → 403）。

> SA-04 根拠: 重複ID登録時に警告＋「統合する／別人として保存」2択UIで誤マージ0を保証（K3・K5達成）。UNIQUE制約（PR #2008）で物理防止。contact merge操作は `audit_logs` に記録（`contacts.py` `/merge` endpoint）。本番検収で重複警告・統合モーダルの動作を確認（Shingo 2026-06-13）。

### 原則4: マルチテナント（ADR-106）

| チェック | SA-02 | SA-03 | SA-04 | SA-05 | SA-06 | SA-07 | SA-12 |
|---------|-------|-------|-------|-------|-------|-------|-------|
| 新規テーブルにRLSが適用されている | ⬜ | ✅ | ✅ | ⬜ | ⬜ | ⬜ | ⬜ |
| テナント分岐がif文散在でなくポリシー注入 | ⬜ | ✅ | ✅ | ⬜ | ⬜ | ⬜ | ⬜ |

> SA-03 根拠: `registration_tokens` はテナントスキーマ分離（`tenant_NNN`）で実質RLS同等。公開エンドポイントはトークンで tenant_id を確定し `set_tenant_context()` を呼び出す（`registration_tokens.py:164-172`）。テナント分岐は `verify_token()` + `set_tenant_context()` に集約（if 文散在なし）。

> SA-04 根拠: `contact_contact_channels` はテナントスキーマ内（`tenant_NNN`）でRLS適用済み（`migrations/030:119-134`）。PR #2008 追加 migration（UNIQUE制約・guild_id）も同スキーマ内。`get_current_tenant` dependency + `set_tenant_context()` でテナント分岐を一括制御（`contacts.py` / `contact_channel_links.py` 全endpoint共通）。

---

## ADR-095 KPI 対応表（全件完了時の最終確認）

| KPI | 目標 | 確認方法 |
|-----|------|---------|
| 誤テナント登録件数 | 0 | 登録時テナント監査ログ（SA-03） |
| オーバーセル件数 | 0 | A在庫 利用可能<0 の発生（SA-05） |
| 請求書と実配送先の不一致件数 | 0 | スナップショット突合（SA-07） |
| 二重持ちしている事実の数 | 0 | 全SA完了後DBスキーマ監査 |
| 自動計算項目への手入力上書き件数 | 0 | 書込み可否フラグ＋ログ（SA-02/04/07） |
| 解析：提供元別除外率／平均確信度 | 監視内 | 解析ログから算出（SA-06） |
| 集計同期のビュー化 | 成立 | 集計を実テーブル保存せず動的導出（SA-05） |
| 関税・送料のハードコード箇所 | 0 | grepスキャン（SA-07/SA-12） |

---

_更新: 2026-06-13（SA-04 ✅ 記入 — Terminal CC・Shingo本番検収完了）/ 作成: Hikky-dev_
