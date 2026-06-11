# ADR-127: 登録後の変更・追加を専用フォーム化（請求先変更／配送先追加）＋新規登録の二重発行防止

**Status**: Proposed
**日付**: 2026-06-11（起案: Web Claude Planner / PO承認: shingo-ops）
**関連**: ADR-097（登録フォーム・署名トークン・住所帳の正本／本ADRはこれを拡張）/ ADR-101（請求書スナップショット）/ ADR-126＋追補（入力契約v2・エラーハンドリング）
**前提recon**: 2026-06-11 architect recon（本文に file:line 引用。recon整合エビデンス済み）

> What／Why／Scopeのみ記す。実装手順（How）はGeneratorに委ねる。

---

## Why

新規登録フォーム（ADR-126）は「全項目を1枚で登録」する作り。登録後に請求先を変えたい／配送先を足したい場合の専用経路が無く、新規登録フォームを再送する運用になっていた。これが is_default 一意制約（idx_company_addresses_one_default）に衝突し、カナリーで二重登録エラーとして顕在化した。

PO方針：**登録後の変更・追加は目的別の専用フォームを発行制にし、変更・追加はそこからのみ承認する。** 入口を絞ることで、野放図な上書き・二重登録を構造的に防ぎ、いつ・どの経路で何が変わったかを発行単位で追えるようにする。

recon確定事実（要点）：
- トークン種別は `register` / `add_address` の2種のみ（`backend/app/schemas/registration_token.py:26-28`、migration CHECK制約 `migrations/20260604_080000_create_registration_tokens.sql:11`）。新種別追加には Enum値＋DB CHECK拡張が必要。
- 配送先追加フォーム（`RegisterAddressPage` / `POST /public/register/address`）は実在・append-only。ただし address_type選択が露出・言語切替なし・電話 dial code 分割なし（RegisterPageと非対称）。
- 請求先を更新する公開経路は存在しない（新規実装）。
- 過去の請求書は `invoices.bill_to_snapshot`（JSONB）で作成時点に凍結（ADR-101 / `backend/app/routers/invoices.py:53-82`）。billing行を後から変更しても既存請求書は不変＝請求先変更は安全。
- 登録済み判定は `EXISTS(billing行 WHERE is_default=true)`。フロントは `GET /companies/:id` の addresses 配列で `billingAddresses.length > 0` で即判定可（`frontend/src/pages/company-detail/CompanyDetailPage.tsx:90`）。
- 受信箱の発行ボタン足場：`karte-action-bar` の overflow menu（`frontend/src/pages/inbox/InboxKartePanel.tsx:262-266`、「サブADRごとに追加」とコメント済み）。

---

## What（決定）

### 1. トークン種別に change_billing を追加

- `TokenType` Enum に `change_billing` 追加（`backend/app/schemas/registration_token.py:26-28`）。
- DB migration：CHECK制約を `('register','add_address','change_billing')` に拡張（**migration変更を含む＝本番投入前にPO明示GO必須**）。
- 発行URL分岐（`backend/app/routers/registration_tokens.py:90-93`）：`change_billing` → `/register/change-billing?token=`、`add_address` → `/register/address?token=`、`register` → `/register?token=`。
- トークン発行API（`POST /registration-tokens`）は `type` を受けて発行する既存構造のまま（API署名変更不要）。

### 2. 請求先変更フォーム（新規ページ）— 案B（履歴を残す）

- 新規公開ページ＋公開エンドポイント（`POST /public/register/change-billing` 相当）。
- 更新方式＝**案B**：既存 billing 行（`is_default=true`）を **is_default=false に降格**し、新しい billing 行を **is_default=true で INSERT**。上書き（UPDATE）はしない。
  - 理由：配送先（住所帳）と同じ「追加式・履歴を残す」思想で一貫。変更の前後が追える。
  - 既存クエリ（請求書作成 `invoices.py` 等が `WHERE is_default=true` で最新を読む）は、新行を true・旧行を false にすることでそのまま最新を拾える。整合確認済み。
- 入力契約はADR-126の請求先セクションに準拠（電話 dial code 分割・国コンボ・i18n・エラーコード方式を踏襲）。

### 3. 配送先追加フォーム（既存RegisterAddressPageを整備）

実装状況（#1934 完了時点）:
- **address_type選択を削除**し `delivery` 固定・`is_default=false` 固定（`frontend/src/pages/register/RegisterAddressPage.tsx` の select 撤去）。✅ #1934 で対応済み。
- **言語切替**（RegisterPageと同等）— ✅ #1881（ADR-126実装）で対応済み。
- **電話 dial code 分割**（国番号コンボ＋番号欄）— ✅ #1881（ADR-126実装）で対応済み。
- append-only（INSERT のみ）は現状維持。#1918のエラーコード方式は適用済み（本番反映済み）。

### 4. 新規登録の二重発行防止（第1層ゲート）

登録済み（billing行 `is_default=true` が存在）の会社に対し、新規登録（`register`）リンクの発行を止める。**フロント＋バックエンドの二段**：
- **フロント**：発行ボタンを `billingAddresses.length > 0` で無効化／非表示（`CompanyDetailPage.tsx:90`。受信箱側に置く場合も同条件）。誤操作を未然に防ぐ。
- **バックエンド**：`POST /registration-tokens` で `type=register` かつ登録済みなら発行拒否（409相当＋エラーコード `"already_registered"`）。最後の砦。
- `change_billing` / `add_address` の発行は登録済みでも当然可（変更・追加は登録後の操作なので）。

### 5. 発行ボタンの設置（ページ先行・ボタン後付け）

- 本ADRのスコープは**フォームのページ＋発行経路を作り、いつでも繋げる状態にする**こと。
- 受信箱への発行ボタン設置（`karte-action-bar` overflow menu）は足場が既にある（`InboxKartePanel.tsx:262-266`）。具体配置は別途。`CompanyDetailPage` の既存ボタンは `type` 指定を増やせば流用可。
- 3種（`register` / `change_billing` / `add_address`）を発行し分けるUIにする。`register` は第1層ゲートで登録済みなら不可。

---

## 実装上の注意（誤実装防止）

- **請求先変更は案B（降格＋INSERT）。** `is_default=true` は `(company_id, address_type)` で常に1行（一意制約）。新行を true にする前に旧行を false にする順序を守る（同一トランザクション内）。逆順だと一意制約に衝突する。
- **過去の請求書には触らない。** `bill_to_snapshot` で保護済み（ADR-101）。billing行の変更が既存 invoice に波及しないこと。
- **第1層ゲートは `register` のみ対象。** `change_billing` / `add_address` を巻き込まない。
- **配送先追加の address_type 固定。** billing を選べる余地を残さない（重複行の温床）。
- **i18n：** 全フォームの文言は en/ja キー管理。エラーはコード返却＋フロント翻訳（#1918方式）を踏襲。公開ルーターは日本語の完成文を返さない。
- **既存の `register` / `add_address` の挙動を壊さない。** 追加は新種別と新ページに閉じる。
- 署名トークンの検証・テナント決定・単回使用/期限のロジックはADR-097のまま流用（変更フォームでも同じ仕組み）。

---

## Scope外

- 受信箱の発行ボタンの最終的な配置・文言（足場確認済み、配置は別途）。
- スタッフUI全体のエラー表示整理（#1918でグローバルハンドラーは不変とした方針を維持）。
- 旧Googleフォーム廃止・顧客告知（運用判断）。

---

## 外部・過去事例の検討

- ADR-097「上書きせず追加（住所帳）」の思想を請求先にも拡張（案B）。系統間で一貫。
- ADR-101 スナップショットにより「現データの変更が過去帳票を壊さない」ことが担保済み＝変更フォームを安全に提供できる根拠。
- #1918（エラーコード＋フロント翻訳）方式を新フォームにも踏襲し、公開ページの文言ガバナンスを統一。
- 二段ゲート（フロント無効化＋バックエンド拒否）は #1918 の入口/出口二重防御と同じ設計原則。

---

## 受け入れ条件（観測可能な挙動）

- [ ] 登録済みの会社では新規登録（`register`）リンクの発行ボタンが無効/非表示になり、APIを直接叩いても `register` 発行が拒否される。未登録の会社では従来どおり発行できる。
- [ ] `change_billing` トークンで請求先変更フォームが開き、送信すると旧billing行が `is_default=false` に降格、新billing行が `is_default=true` で追加される（住所帳に履歴が残る）。
- [ ] 請求先変更後に作成する請求書は新しい請求先を使い、変更前に作成済みの請求書は旧スナップショットのまま不変である。
- [ ] `add_address` トークンで配送先追加フォームが開き、address_type選択は表示されず `delivery` 固定で追加される。billing 行は作られない。
- [ ] 配送先追加フォームが英語デフォルト表示＋言語切替でき、電話は国番号コンボ＋番号欄で国際形式保存される（RegisterPageと同仕様）。
- [ ] 3種のフォームすべてで、エラーはコード→i18n翻訳で表示され、顧客画面に日本語の内部用語・生コードが出ない。表示言語に追従する。
- [ ] 署名トークン経由で正しいテナント・会社に紐づき、他テナント混入がない。単回使用/期限の挙動はADR-097どおり。
- [ ] 全文言が en/ja キー管理で、ESLint `local/no-japanese-literal` を通る。
