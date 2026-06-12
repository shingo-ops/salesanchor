# SA-03 計画票 — 顧客登録トークン基盤（ADR-097 + ADR-126 + ADR-127）

| 項目 | 内容 |
|------|------|
| 対応ADR | ADR-097（トークン基盤）、ADR-126（入力契約v2）、ADR-127（change_billing追加・二重発行防止） |
| ステータス | ⑤ 本番反映済み（進捗 90%・テスト発行検収待ち）|
| 担当 | PO: Shingo ／ Dev: Terminal CC |
| 最終更新 | 2026-06-12（Shingo完了条件確定）|

---

## 1. 計画票（スケジュール）

| # | ステップ | 担当 | 状態 | 完了日 |
|---|---------|------|------|--------|
| 1 | KGI承認 | Shingo | ✅ 承認済み（G1〜G4、ソフトオープン含む） | 2026-06-11 |
| 2 | recon完了（file:line差分表の記入） | Terminal CC | ✅ 完了 | 2026-06-11 |
| 3 | 差分レビュー＋KPI数値確定 | Shingo＋Planner | ✅ ADR-127 PO承認済み → GO | 2026-06-11 |
| 4 | 残作業（change_billing フォーム・3種発行UI・受信箱ボタン）実装 | Terminal CC | ✅ 完了（PR #1979 マージ・本番反映） | 2026-06-12 |
| 5 | 検証ゲート（CI・E2E・process-artifacts） | 自動＋Reviewer | ✅ 完了（smoke PASS） | 2026-06-12 |
| 6 | テスト発行検収＋KGI G4確認 | Shingo | 🔄 次のアクション（完了条件確定済み — §6参照） | |

> **注記**: ADR-097（基本トークン基盤）/ ADR-126（入力契約v2）/ ADR-127（一部）は別セッションで実装済み。
> 本計画票は未実装残作業（§3 差分参照）の追跡と KGI 正式承認のために起票。

---

## 2. KGI定義（recon後確定版 — Shingo承認待ち）

> KGI＝「本番でこれが観測できたら成功」という最終ゴール。数えられる形で書く。

| # | KGI | 種別 |
|---|-----|------|
| G1 | 登録（`register`）・住所追加（`add_address`）・請求先変更（`change_billing`）の全経路でテナントはトークン（HMAC-SHA256）のみで確定する。リクエストボディ・URLパスにテナントIDを受け付ける公開経路が**0箇所** | セキュリティ（テナント分離） |
| G2 | 期限切れ・使用済み・改ざんトークンは全て拒否（403）され、エラーは**エラーコード→フロント翻訳**方式で表示言語（EN/JA）に追従する。バックエンドから日本語の完成文を返す経路が**0箇所** | セキュリティ＋i18n |
| G3 | 登録フォーム送信 → 会社マスタ（`companies`・`company_addresses`・`contacts`）への直行で、担当者の手転記が**0件**。住所は上書き（UPDATE）でなく住所帳追加（INSERT only）。請求先変更は旧行降格＋新行INSERT（履歴保持） | データフロー・SSOT |
| G4 | 旧Googleフォームの廃止・実テナント登録の新フォーム切替（ソフトオープン）の状況（事実の把握のみ） | 運用切替 |

**承認欄**: ✅ 承認済み（Shingo 2026-06-11）— G1〜G4 + ソフトオープン含む

> **G4 達成条件確定（Shingo 2026-06-12）**: 旧Googleフォームは社内用途のみだったため、テナント告知（顧客向け連絡）は対象外。**「社内運用が新フォームへ切替済み」をもって G4 達成扱いとする**。テスト発行検収（#1 ＝ CompanyDetailPage から3種トークンを実際に発行・フォーム送信・カルテ反映確認）が完了した時点で Shingo が確認し、G4 達成を宣言する。

---

## 3. 現状調査結果と差分（recon記入欄 — 2026-06-11 Terminal CC）

> **ルール**: 推測禁止。「現状」列は必ず実コードの file:line を引用。
> 調査ベース: `origin/main` ブランチ（2026-06-11 時点）

### G1: 登録・住所追加・請求先変更がトークン経由のみか

| 経路 | 現状（file:line） | ADR-097/127 の理想 | 差分 |
|------|------------------|--------------------|------|
| `POST /public/register`（新規登録） | `backend/app/routers/registration_tokens.py:164-172` — `verify_token()` で token から `tenant_id`・`lead_id` を取得。リクエストボディにテナントIDフィールドなし | トークンのみでテナント確定 | **差分なし** ✅ |
| `POST /public/register/address`（住所追加） | `backend/app/routers/registration_tokens.py:354-363` — 同様に `verify_token()` 経由 | トークンのみでテナント確定 | **差分なし** ✅ |
| `change_billing` 経路 | **存在しない**。`backend/app/schemas/registration_token.py:26-28` — `TokenType` Enum は `register` / `add_address` の2種のみ。`migrations/20260604_080000_create_registration_tokens.sql:11` — DB CHECK制約も2種のみ。`backend/app/routers/registration_tokens.py` に `POST /public/register/change-billing` エンドポイントなし | `change_billing` トークン発行→`/register/change-billing?token=` ページで請求先変更 | **差分あり** ❌ `change_billing` 経路が未実装（ADR-127 §1-2） |

### G2: 期限切れ・使用済み・改ざんトークンの拒否と多言語エラー

| 観点 | 現状（file:line） | ADR-097/126/127 の理想 | 差分 |
|------|------------------|-----------------------|------|
| トークン検証3点（改ざん・期限切れ・使用済み） | `backend/app/services/registration_token.py:120-148` — ①hash不一致→None、②`used_at IS NOT NULL`→None、③`expires_at < now()`→None → router で 403 | 3点いずれも拒否 | **差分なし** ✅ |
| バックエンドのエラーレスポンス形式 | `backend/app/routers/registration_tokens.py:154-156` — `detail="invalid_token"`（文字列コード）。同157、203、224、282-284 も同様のコード文字列 | コードのみ返却（日本語完成文を返さない）| **差分なし** ✅（旧実装では日本語ハードコードがあったが #1936 で修正済み） |
| フロント側のエラーコード→i18n翻訳 | `frontend/src/pages/register/RegisterPage.tsx:62-75` — `KNOWN_ERROR_CODES` Set ＋ `resolveErrorCode()` → `t("registration.error.${code}")` | エラーコードから表示言語に従って翻訳 | **差分なし** ✅ |
| en.json / ja.json のエラーキー | `frontend/src/locales/en.json:registration.error.*` — `already_registered` / `invalid_token` / `company_not_found` / `unexpected_error` の4キー | en/ja 同一キー管理 | **差分なし** ✅（ja.json の同キー存在は目視確認済み） |
| `change_billing` フォームのエラーハンドリング | 未実装（フォームが存在しないため） | — | **差分あり** ❌（未実装に付随） |

### G3: 送信→顧客マスタ直行・手転記0・住所は追加式

| 観点 | 現状（file:line） | ADR-097/126/127 の理想 | 差分 |
|------|------------------|-----------------------|------|
| `register` フォーム送信先（会社マスタ直行） | `backend/app/routers/registration_tokens.py:215-299` — INSERT: ①`companies` に `billing_display_name`・`payment_recipient_name`（229-245）、②`company_addresses`（246-279）、③`contacts`（280-299）→ `db.commit()` でアトミックに保存 | フォーム送信→DB直書き（手転記なし） | **差分なし** ✅ |
| 住所追加の方式（上書きか追加か） | `backend/app/routers/registration_tokens.py:380-408` — INSERT only（ON CONFLICT なし）。`is_default=false` 固定（`frontend/src/pages/register/RegisterAddressPage.tsx:41`） | 住所帳に追加（上書きしない） | **差分なし** ✅ |
| 請求先変更の方式（ADR-127 案B） | `change_billing` 経路未実装 | 旧billing行 `is_default=false` 降格＋新行 `is_default=true` INSERT（履歴保持） | **差分あり** ❌ 未実装 |
| ADR-126 入力契約v2（dial code・Ship to same address分岐・Section 1/2） | `frontend/src/pages/register/RegisterPage.tsx:5-7`（コメント確認）・`:30` `telephone_dial` フィールド・`:85` `i18n.changeLanguage()`・`:132` 国際電話結合関数・`:197` "Ship to same address" 分岐 | ADR-126 §1-2 の全入力契約を充足 | **差分なし** ✅（PR #1886/#1906 で実装済み） |
| `contact_name` 任意化・フォールバック | `backend/app/routers/registration_tokens.py:218-227` — `billing_display_name` をフォールバックに使用。`backend/app/schemas/registration_token.py:119-121` — `contact_name` は Optional | ADR-126 §追補 の担当者名任意化 | **差分なし** ✅（PR #1906 で実装済み） |
| カルテ（会社詳細）への即反映 | `company_addresses`・`contacts` 直INSERT → `GET /companies/:id` が `addresses`・`contacts` を返す（`backend/app/routers/companies.py`）。スタッフが画面リロードすれば即確認可 | 登録後即カルテ反映 | **差分なし** ✅ |

### G4: 旧Googleフォーム廃止・ソフトオープン状況（事実のみ）

| 観点 | 事実（code/ADR/git） |
|------|---------------------|
| 旧Googleフォームの廃止 | コードに廃止・リダイレクトの変更なし。ADR-126:111「旧Googleフォームの廃止タイミング・顧客告知 → 運用判断（カナリー完了後）」と Scope外 明記 |
| 新フォームのルーティング | `frontend/src/App.tsx:118-119` — `/register?token=` ・ `/register/address?token=` ともに本番 routing 済み |
| 実テナントへのトークン発行手段 | `frontend/src/pages/company-detail/CompanyDetailPage.tsx:74-88` — `register` タイプのみ発行可。`add_address` ボタンは未実装 |
| ソフトオープン実施状況 | git log・コードから確認不可（運用判断領域）。確認はしんごさんに委ねる |

### ADR-127 残作業の実装状況一覧

| # | ADR-127 §項目 | 状態 | 根拠（file:line） |
|---|--------------|------|------------------|
| A-1 | `change_billing` TokenType Enum 追加 | ❌ 未実装 | `backend/app/schemas/registration_token.py:26-28` — 2種のみ |
| A-2 | DB migration CHECK制約拡張（`'change_billing'` 追加） | ❌ 未実装 | `migrations/20260604_080000_create_registration_tokens.sql:11` — 2種のみ |
| A-3 | `create_token` URL分岐に `change_billing` → `/register/change-billing?token=` | ❌ 未実装 | `backend/app/routers/registration_tokens.py:89-93` — 2種分岐のみ |
| B-1 | 請求先変更フォームページ `/register/change-billing` | ❌ 未実装 | `frontend/src/App.tsx:118-119` — ルートなし |
| B-2 | バックエンド `POST /public/register/change-billing` エンドポイント（旧行降格＋新行INSERT） | ❌ 未実装 | `backend/app/routers/registration_tokens.py` — エンドポイントなし |
| C-1 | `RegisterAddressPage` address_type 選択削除・delivery 固定 | ✅ 実装済み（PR #1934） | `frontend/src/pages/register/RegisterAddressPage.tsx:41` — `address_type: "delivery"` 固定、`<select>` 撤去済み |
| C-2 | `RegisterAddressPage` 言語切替 | ✅ 実装済み（PR #1934） | `frontend/src/pages/register/RegisterAddressPage.tsx:176` — `i18n.changeLanguage(lang)` |
| C-3 | `RegisterAddressPage` 電話 dial code 分割 | ✅ 実装済み（PR #1934） | `frontend/src/pages/register/RegisterAddressPage.tsx:27-28` — `telephone_dial` / `telephone_number` |
| D-1 | フロント第1層ゲート（登録済みなら `register` ボタン disabled） | ✅ 実装済み（PR #1936/#1942/#1950） | `frontend/src/pages/company-detail/CompanyDetailPage.tsx:94,119,122` — `isAlreadyRegistered` で disabled＋ラベル変更 |
| D-2 | バックエンド第1層ゲート（type=register かつ登録済みなら 409 `already_registered`） | ✅ 実装済み（PR #1936） | `backend/app/routers/registration_tokens.py:80-97` |
| E-1 | 受信箱 overflow menu の発行ボタン設置 | ❌ 未実装（足場のみ） | `frontend/src/pages/inbox/InboxKartePanel.tsx:264` — コメント「No implemented overflow items currently」 |
| E-2 | CompanyDetailPage 3種発行UI（`register`/`change_billing`/`add_address`） | ❌ 部分実装 | `frontend/src/pages/company-detail/CompanyDetailPage.tsx:78-88` — `register` タイプのみ。他2種のボタンなし |

### recon結論（2026-06-11 Terminal CC）

#### 差分なし（ADR-097 + ADR-126 + ADR-127の実装済み部分）

| 領域 | 実装完了の根拠 |
|------|---------------|
| トークン HMAC-SHA256 生成・検証（3点） | `backend/app/services/registration_token.py:39-148` |
| `register` / `add_address` のテナント分離（トークン経由のみ） | `backend/app/routers/registration_tokens.py:164-172, 354-363` |
| エラーコード返却（日本語ハードコードなし）＋フロント翻訳 | `registration_tokens.py:154-156`、`RegisterPage.tsx:62-75`、`en.json/ja.json` の `registration.error.*` |
| ADR-126 入力契約v2（dial code / Ship to same address / billing_display_name / payment_recipient_name） | `RegisterPage.tsx:30,85,132,197`、`registration_token.py:124-125`、`registration_tokens.py:229-245` |
| 住所帳追加（上書きなし） | `registration_tokens.py:380-408`（INSERT only）、`RegisterAddressPage.tsx:41`（delivery 固定） |
| 第1層ゲート（フロント disabled + バックエンド 409） | `CompanyDetailPage.tsx:94,119`、`registration_tokens.py:80-97` |
| 言語切替・i18n（公開ページ英語デフォルト） | `RegisterPage.tsx:85-88`、`RegisterAddressPage.tsx:176-178` |

#### 差分あり（残作業）

| # | 残作業 | 優先度 | 関連ADR |
|---|--------|--------|---------|
| 1 | `change_billing` TokenType + DB migration + URL分岐（A-1/A-2/A-3） | 高 | ADR-127 §1 |
| 2 | 請求先変更フォーム（ページ + バックエンドエンドポイント）（B-1/B-2） | 高 | ADR-127 §2 |
| 3 | CompanyDetailPage 3種発行UI（E-2） | 中 | ADR-127 §5 |
| 4 | 受信箱 overflow menu の発行ボタン（E-1） | 低（ADR-127 §Scope外に近い） | ADR-127 §5 |
| 5 | G4 ソフトオープン実施確認（運用判断） | **バックログ切り出し（2026-06-12 Shingo決定）**: テナント告知は対象外（社内用フォームのため）。マニュアル作成はUIボタン配置最終確定後に実施（デザイン改善イニシアチブと連動）。残る確認はテスト発行検収のみ | ADR-126 §Scope外 |

---

## 4. KPI設定（recon後 — Shingo承認後に確定）

| # | KPI候補 | 目標 | 測り方 |
|---|---------|------|--------|
| K1 | トークン以外の経路でテナントが確定した件数 | 0件/月 | `registration_tokens` テーブルに `tenant_id` 不一致行 0を確認（DB constraint が保証）|
| K2 | 403拒否後に顧客画面に日本語内部用語が表示された件数 | 0件 | Playwright E2E: 期限切れトークンで `/register` を開き、表示文字列が `t("registration.error.invalid_token")` の英訳であることを確認 |
| K3 | 登録フォーム送信後に `company_addresses` / `contacts` に手動入力が必要だった件数 | 0件/月 | `company_addresses.created_at` と `registration_tokens.used_at` の時刻差が 1 秒以内（自動直行の証拠）|
| K4 | change_billing フォーム経由の請求先変更でスナップショット不変（ADR-101） | 100% | 変更前作成済み `invoices.bill_to_snapshot` が変更後も同一であること（E2E検証） |

---

## 5. 実装記録

| 日付 | PR | 内容 | 状態 |
|------|----|------|------|
| 2026-06-01 | #1610 | ADR-SA-03 基盤実装（トークン生成・検証・公開 register / add_address エンドポイント） | マージ・本番反映済み |
| 2026-06-10 | #1773/#1762/#1884 | fix: company lookup SSOT・contacts INSERT修正・contacts address_type Literal | マージ・本番反映済み |
| 2026-06-10 | #1886 | ADR-126 実装（dial code / Ship to same / billing_display_name / input contract v2） | マージ・本番反映済み |
| 2026-06-10 | #1906 | fix(ADR-126): 担当者名を任意化・billing_display_name フォールバック | マージ・本番反映済み |
| 2026-06-10 | #1927 | docs: ADR-127 起案（Proposed） | マージ済み |
| 2026-06-11 | #1934 | ADR-127 Phase1: RegisterAddressPage — delivery 固定・言語切替・dial code | マージ・本番反映済み |
| 2026-06-11 | #1936 | ADR-127 Phase2: 第1層ゲート（フロント disabled + バックエンド 409） | マージ・本番反映済み |
| 2026-06-11 | #1942/#1950/#1966 | ADR-127 Phase2b/2c: 登録済みラベル UX + ボタン色修正 | マージ・本番反映済み |
| 2026-06-11 | #1975 | SA-03 recon（差分確認・SA-03-plan.md §3 記入） | マージ済み |
| 2026-06-12 | #1979 | ADR-127 A-1〜A-3, B-1/B-2, E-1/E-2 実装（change_billing 一式 + 発行UI + 受信箱 overflow menu） | マージ・本番反映済み（smoke PASS） |

---

## 6. チェックシート（完了条件）

> **完了条件確定（Shingo 2026-06-12）**: 以下の3点がSA-03の唯一の残タスク。Shingo「検収OK」を受けてCCが⑥〜⑧をチェックし100%に更新する。

- [x] ① KGI承認（Shingo 2026-06-11 承認済み・G1〜G4）
- [x] ② recon完了（差分表が file:line で埋まっている）— 2026-06-11 Terminal CC
- [x] ③ 設計確定（ADR-127 PO承認済み → 実装 GO）
- [x] ④ 残作業 PR マージ（change_billing フォーム・3種発行UI）— PR #1979 マージ済み（2026-06-12）
- [x] ⑤ 本番反映（CI緑＋smoke通過）— 2026-06-12 smoke PASS
- [ ] ⑥ **テスト発行検収（Shingo）**: CompanyDetailPage から `register` / `add_address` / `change_billing` を各1回発行 → フォーム送信 → カルテ反映確認 → 「検収OK」をCCに送信
- [ ] ⑦ KGI G1〜G4 実測確認（⑥完了後にCCが記録）
- [ ] ⑧ SA-01横断チェックシート記入＋総合進捗表（00-SA-OVERVIEW.md）100%更新

> **バックログ（SA-03 100%達成後に別途対応）**:
> - マニュアル作成: UIボタン配置最終確定後（デザイン改善イニシアチブと連動）
> - テナント告知: 対象外（旧Googleフォームは社内用途のみ）
