# ADR-126: 顧客登録フォーム 入力契約v2（旧Googleフォーム互換・英語デフォルトi18n・改善5点）

**Status**: Proposed
**日付**: 2026-06-10（起案: Web Claude Planner / PO承認: shingo-ops）
**関連**: ADR-097（フォーム構造の正本・本ADRでは不変）/ ADR-096（顧客マスタ）/ ADR-101（書類生成・スナップショット）
**前提recon**: 2026-06-10 architect recon報告（本文に file:line 引用。recon整合エビデンス済み）

> このADRは What／Why／Scope のみを記す。実装手順（How）は Generator に委ねる。

---

## Why

- 入力項目の正本を旧Googleフォーム「Order Information Form」（TREASURE ISLAND JAPAN）に置き、項目セットをゼロベースで再確定した（PO承認済み・2026-06-10）。
- ADR-097のv1は完全実装済み（トークン生成・検証 `backend/app/services/registration_token.py`、公開ルーター `backend/app/routers/registration_tokens.py:105,151,271`、`frontend/src/pages/register/RegisterPage.tsx`）。**本ADRは入力契約の差し替えのみ**であり、構造（署名トークン・テナント自動決定・住所帳1:N・顧客入力／担当者後付けの役割分担）はADR-097のまま不変。
- 受け皿カラムは全て実在確認済み（マイグレーション不要）：`billing_display_name` / `payment_recipient_name`（migrations/028_create_companies.sql:74-75）、`company_addresses.address_line_1〜3 / city / state / zip / country_code / telephone / email / tax_id`（migrations/030_create_company_contact_subtables.sql:46-55）。

---

## What（決定）

### 1. 入力契約テーブルv2

**Section 0 — Contact Person（担当者・やり取りの窓口）**

| # | 項目（EN） | 必須 | 形式・ルール | 保存先 |
|---|---|---|---|---|
| 1 | Contact Name | 任意 | テキスト。**空欄時は `companies.billing_display_name` をフォールバックとして担当者レコードを必ず1件作成**。出口補完ではなく登録時確定（担当者は窓口の実体なので空のままにしない）。注記文: 「お一人で運営の場合は空欄で結構です（ご自身が窓口として登録されます）」| contacts.display_name |
| 2 | Contact Email | 任意 | メール形式 | contacts.primary_email |
| 3 | Contact Telephone | 任意 | テキスト | contacts.primary_phone |

> Section 0 はフォームの最上部に配置。Contact Name・Contact Email・Contact Telephone は全項目任意。空欄で送信した場合は請求先名が担当者名として contacts に保存される。

**Section 1 — Billing Address Registration**

| # | 項目（EN） | 必須 | 形式・ルール | 保存先 |
|---|---|---|---|---|
| 1 | Billing Name | ＊ | テキスト。説明文「Please enter store name for billing purposes」 | companies.billing_display_name |
| 2 | Telephone Number | ＊ | **国番号コンボボックス＋番号欄**。保存は結合した国際形式1値 | company_addresses.telephone |
| 3 | Email Address | ＊ | メール形式 | company_addresses.email |
| 4 | Payment Account Name（新設） | 任意 | テキスト。説明文「送金名義が請求先名と異なる場合のみ」 | companies.payment_recipient_name |
| 5 | Business Identification Number (EORI, TAX ID, TIN, ABN, etc.) | 任意 | テキスト | company_addresses.tax_id |
| 6 | Address Line 1 | ＊ | テキスト | company_addresses.address_line_1 |
| 7 | Address Line 2 | 任意 | (Apartment/Unit Details) | company_addresses.address_line_2 |
| 8 | City | 任意 | テキスト | company_addresses.city |
| 9 | State | 任意 | テキスト | company_addresses.state |
| 10 | ZIP/Postal Code | 任意 | **空欄可。DBは空のまま**（埋め値は出口で：§5） | company_addresses.zip |
| 11 | Country | ＊ | **検索つきコンボボックス**（自由入力で候補絞り込み→リスト選択）。保存はISO 3166-1 alpha-2 | company_addresses.country_code |
| 12 | Do you need to register a shipping address? | ＊ | 2択：Proceed to register. / Ship to the same address. **後者選択時はSection 2を非表示** | （分岐制御のみ・保存しない） |

> Section 1 は address_type='billing' の company_addresses 行として保存する。

**Section 2 — Shipping Address Registration**（address_type='delivery' 行として保存。「Ship to the same address.」選択時は非表示かつ billing 住所を delivery にコピー）

| # | 項目（EN） | 必須 | 形式・ルール | 保存先 |
|---|---|---|---|---|
| 1 | Recipient Name | ＊ | テキスト | company_addresses.name |
| 2 | Telephone Number | 任意 | Section 1と同仕様（国番号コンボボックス＋番号欄） | company_addresses.telephone |
| 3 | Email Address | **任意** | 空なら出口で請求先メールにフォールバック（§5） | company_addresses.email |
| 4 | Business Identification Number | 任意 | テキスト | company_addresses.tax_id |
| 5 | Address Line 1 | ＊ | テキスト | company_addresses.address_line_1 |
| 6 | Address Line 2 | 任意 | テキスト | company_addresses.address_line_2 |
| 7 | Address Line 3（新設） | 任意 | テキスト。受け皿実在（migrations/030_create_company_contact_subtables.sql:51） | company_addresses.address_line_3 |
| 8 | City | 任意 | テキスト | company_addresses.city |
| 9 | State | 任意 | テキスト | company_addresses.state |
| 10 | ZIP/Postal Code | 任意 | Section 1と同様 | company_addresses.zip |
| 11 | Country | ＊ | Section 1と同仕様 | company_addresses.country_code |

### 2. 旧フォームからの改善5点（PO個別承認済み）

| # | 決定 |
|---|---|
| 1 | Section 2の説明文を全て shipping 表記に修正（旧フォームは billing のままのコピペ跡）。タイポ修正（Sipping→Shipping / shippng→shipping） |
| 2 | 支払い名義（Section 1・任意）と Address Line 3（Section 2のみ・任意）をフォームに追加 |
| 3 | City・ZIPは旧フォーム通り任意を維持（実運用で空白提出でも配送に支障なしというPOエビデンスに基づく）。ZIP空欄の補完はDBでなく出口（§5） |
| 4 | 電話番号は国番号コンボボックス＋番号欄に分離。「数字のみ・+禁止」ルールは廃止 |
| 5 | 配送先Emailは任意化。空欄時は使用場面で請求先メールに自動フォールバック |

### 3. 国リストSSOT（新設）

国名・ISOコード（alpha-2）・国際電話番号（dial code）を持つ**静的データファイルを1つ新設**。Countryコンボボックスと電話国番号コンボボックスの両方が同一ファイルを参照する。recon確認により既存資産なし（新規作成）。配置・形式はGenerator裁量（フロント静的データで可。DBテーブル化はしない）。

### 4. i18n：公開フォームのみ英語デフォルト

- 公開フォームページ（RegisterPage / RegisterAddressPage）は**明示的に英語表示をデフォルト**とし、言語切替UIを設置。
- **グローバルの fallbackLng:"ja"（frontend/src/i18n.ts:36）は変更しない**（スタッフUIの既定言語を巻き込まないため）。
- 全文言は en.json / ja.json のキー管理。直書き禁止（ESLint local/no-japanese-literal 準拠）。

### 5. 出口補完2件（「DBは事実だけ、辻褄合わせは出口で」原則）

| 補完 | 仕様 | 差し込み口（recon確定） |
|---|---|---|
| ZIP埋め値 | 配送ラベル生成時、ZIP空欄なら埋め値（既定 `0000000`）を自動挿入。**DBには保存しない** | eLogi CSV生成：`backend/app/routers/order_shipping_details.py:292` `_build_csv_entry()` 周辺（zip_code は `:60` で取得、出力は `services/shipping_carriers/elogi.py:113`） |
| 配送先メール | order_shipping_details.email が空なら請求先（company_addresses billing行）のemailを参照 | 同上 `_build_csv_entry()` または email取得箇所（`elogi.py:109`）の手前 |

### 6. 電話番号バリデーション緩和

現行 `validate_phone`（`backend/app/schemas/base.py:16-23`、`^(\+?\d{10,15}|0\d{9,10})$`）は10桁未満の国際番号（例：アンドラ +376 は9桁）を弾く。国番号＋番号の結合国際形式を受けるため、**結合後の検証を「+ で始まり数字6〜15桁」（E.164の範囲）に緩和**する。既存の区切り記号自動除去（スペース・ハイフン・括弧）は維持。

変更後の正規表現（案）:
```
^(\+\d{6,15}|0\d{9,10})$
```

---

## 実装上の注意（誤実装防止）

- **偽データをDBに入れない。** ZIPの `0000000` はラベル生成時のみ。配送先メールのフォールバック値も保存しない（参照のみ）。
- **Contact Name のフォールバックはDBに保存してよい。** ZIPやメールの「出口補完（DBは空）」と異なり、担当者名は「この取引の窓口は誰か」という関係の記録。空のまま残すと後工程（連絡時の宛先）が機能しないため、登録の瞬間に `billing_display_name` で確定させる。実装: `/public/register` エンドポイントで `data.contact_name.strip() or billing_display_name` を `contacts.display_name` に保存。
- **fallbackLng のグローバル変更禁止。** 英語デフォルトは公開フォームページのスコープに限定する。
- **payment_recipient_name は業務語彙「支払い名義（送金者の名義）」として使う。** カラム名（recipient）と語彙にズレがあるが、改名（migration追加）はしない。本ADRを語彙の正とする。
- **v1からの差分のみ変更する。** `RegisterRequest`（`backend/app/schemas/registration_token.py:116`）に `billing_display_name` / `payment_recipient_name` 等の不足フィールドを追加する形。トークン検証・テナント決定・住所帳の既存ロジックには触れない。
- 旧フォームの説明文（helper text）は本ADR §2-1 の修正版を i18n キーで実装する。

---

## Scope外（別Issue・別ADR）

- **請求書PDFのZIP未印字**（recon発見：`invoice_renderer.py:115-122` の `AddressSnapshot` に zip フィールドがなく、snapshot dict の `postal_code` が出力されない）→ **別Issue起票**（v2はフォーム改修に集中）。
- 国連動のZIP要否自動判定（郵便番号なし国リスト）→ 将来改善。v2は任意＋出口補完で十分。
- 旧Googleフォームの廃止タイミング・顧客告知 → 運用判断（カナリー完了後）。

---

## 外部・過去事例の検討

- **E.164（ITU-T国際電話番号規格）**：国番号込み最大15桁。本ADRの検証緩和（6〜15桁）の根拠。
- **ISO 3166-1 alpha-2**：国コード標準。既存バリデーション（`registration_token.py:104-113`）と整合。
- **郵便番号制度のない国・地域の実在**（UAE・香港等）：ZIP一律必須化を採らない根拠。主要EC・キャリアの住所フォームも同理由でZIPを国により任意化している。
- **過去事例（社内）**：SA-18 Phase2の教訓どおり、確実性はゲートで担保（受け入れ条件＋Evaluator）。配送先スナップショット（ADR-101）と同じ「事実保存・出口補完」思想を踏襲。

---

## 受け入れ条件（観測可能な挙動）

- [ ] 公開フォームが英語デフォルトで表示され、言語切替で日本語表示できる。スタッフUIの既定言語は変わらない。
- [ ] Section 1 の項目・必須/任意・説明文が §1 の表と一致する。Payment Account Name が任意項目として表示される。
- [ ] 「Ship to the same address.」選択時、Section 2 が表示されずに送信でき、配送先には請求先と同住所が登録される。
- [ ] 「Proceed to register.」選択時のみ Section 2 が表示され、Address Line 3 を含む項目が §1 の表と一致する。
- [ ] Country・電話国番号とも、文字入力で候補が絞り込まれ、リストから選択した値（ISOコード／dial code）が保存される。自由文字列はそのまま保存されない。
- [ ] +つき9桁の国際電話番号（例: +376367830）がバリデーションを通過する。
- [ ] ZIP空欄で登録した顧客の eLogi CSV に埋め値が出力され、DB（company_addresses.zip / order_shipping_details.zip_code）は空のままである。
- [ ] 配送先Email空欄の注文の eLogi CSV に請求先メールが出力される。
- [ ] 送信されたデータが正しいテナントの companies / company_addresses（address_type別）に保存される（トークン検証経由・他テナント混入なし）。
- [ ] 全文言が en.json / ja.json のキーで管理され、ESLint local/no-japanese-literal を通る。
- [ ] 担当者名を空欄で送信すると、請求先名（billing_display_name）を担当者名とする contacts レコードが1件作成される。
- [ ] 既登録住所（`idx_company_addresses_one_default` 制約違反）で登録試行 → 409 + `{"detail": "already_registered"}` が返り、フォームに「この住所はすでに登録されています」と表示される。
- [ ] 409 時にトークンは消費されず、再送が可能である。
- [ ] 公開フォームの全エラーメッセージが i18n キー（`registration.error.*`）経由で表示され、内部コード・日本語ハードコードが顧客に露出しない。

---

## 追補: 公開フォームエラーハンドリング（2026-06-11）

### 背景

カナリーテストで `POST /public/register` が `UniqueViolationError`（既登録住所）時に「データベースエラーが発生しました」を顧客に露出することを検出。

### 決定

**Case イ: 公開エンドポイント内捕捉**（グローバルハンドラー不変）

- `register_customer` エンドポイント内の address INSERT ループを `try/except SQLAlchemyError` で囲み、`idx_company_addresses_one_default` 制約違反を検知したら 409 + `"already_registered"` を返す。
- 全 `detail` 文字列を機械読み取り可能コード（`invalid_token` / `company_not_found` / `already_registered`）に統一。
- フロントエンド（`RegisterPage.tsx` / `RegisterAddressPage.tsx`）は `resolveErrorCode()` で既知コードを `registration.error.*` i18n キーに変換。未知コードは `registration.submitError` にフォールバック。
- `main.py` グローバルハンドラーは変更しない（スタッフUI ~16画面保護のため）。

### 追加 i18n キー

| キー | en | ja |
|------|----|----|
| `registration.error.already_registered` | This address has already been registered... | この住所はすでに登録されています... |
| `registration.error.invalid_token` | Invalid or expired registration link... | 登録リンクが無効または期限切れです... |
| `registration.error.company_not_found` | Company information not found... | 会社情報が見つかりません... |
| `registration.error.unexpected_error` | An unexpected error occurred... | 予期しないエラーが発生しました... |
