# ADR-101: 見積・請求の生成（正規化2テーブル・テンプレSSOT・関税ポリシー・スナップショット・発行モード）（ADR-SA-07）

## Status
Accepted（送料/関税の数式・Wise APIは未決＝ADR-095付録1）

> **2026-06-12 改訂**: §6 PayPal を Invoicing 方式へ／さらに 写しPDF自動保存＋追跡＋ケース管理を追加（下記「改訂」「改訂(2)」節）。

## Date
2026-06-04（起案: Hikky-dev / PO: shingo-ops）／改訂 2026-06-12（Invoicing 方式＋写しPDF/追跡/ケース拡張・PO 承認）

---

## 改訂 2026-06-12: PayPal 決済を「Invoicing 方式」へ（§6 PayPal (1) を上書き）

### 背景・決定
当初 §6 の PayPal「(1) API自動（リンク自動発行＋入金自動確認）」は **PayPal Checkout/Orders API（決済リンク）** で実装した（Increment 1/2/2.5）。しかし PayPal が**請求書をメール送付し、PayPal 上のページで支払い・ステータス管理する「Invoicing 方式（`/v2/invoicing/invoices`）」**に切り替える（しんごさん事前了承・Hitoshi 判断 GO）。

### 案Y（併存）を採用 — SSOT は維持
- **自社請求書（正規化2テーブル＋自社ブランドPDF）は引き続き SSOT のまま維持**（Wise 等 他決済でも流用するため）。
- **PayPal 決済時のみ**、自社請求書のデータから **PayPal Invoice を生成・送付**し、PayPal を「メール送付＋ホスト決済ページ＋ステータス管理」のチャネルとして使う。
- つまり「請求書の正本＝自社／PayPal は支払いチャネル」は不変。PayPal の請求書は**支払い導線**として併存。

### 新フロー
1. 請求書(issued) → PayPal 決済を選択 → `POST /v2/invoicing/invoices`（`detail.invoice_number`=自社IN-NNNN、`detail.reference`="tenant_id:invoice_id"、`primary_recipients[].billing_info.email_address`=contact.primary_email、items=自社明細）→ `POST .../{id}/send`（PayPal が顧客にメール＋`detail.metadata.recipient_view_url` ホスト決済ページ）。
2. 入金確認: webhook **`INVOICING.INVOICE.PAID`**（`detail.reference` で自社請求書にルーティング）→ 自社請求書 paid＋受注 sourcing。手動は `GET /v2/invoicing/invoices/{id}` の status=PAID で確認。
3. **PDF**: PayPal は API で PDF を返さない（確認済）ため、記録用 PDF は**自社生成のまま**（ADR-101 本文の自社PDF）。

### 旧 Orders 方式の扱い
PayPal の支払い導線は Invoicing に一本化。旧 Checkout/Orders 経路（決済リンク発行・戻りURL capture・CHECKOUT.ORDER.APPROVED webhook）は本改訂で置換（コードは段階的に整理）。`payment_fee` 等の列は流用（`paypal_order_id`=PayPal Invoice ID, `paypal_approval_url`=recipient_view_url を格納・migration 不要）。

### 制約
PayPal Invoicing は**送付先 email 必須**（PayPal がメール送付するため）。email 未登録の contact では発行不可（400）。

---

## 改訂 2026-06-12 (2): 写しPDF自動保存＋追跡＋ケース管理（KGI 4点・PO 承認）

参照: recon = `docs/handoff/paypal-invoice-epic/recon.md`。前項「Invoicing 方式」(PR #1980) の上に積む拡張。

### 背景・決定（What / Why）
PayPal 正規請求書（Invoicing）の運用を、取引の証明・手間削減・トラブル対応まで広げる。**KGI（PO 承認 2026-06-12）**:
1. アプリの請求書から PayPal 正規請求書を作成・送信でき、顧客が支払える（**PR #1980 実装済み**）。
2. **送信成功時に写しPDFを自動生成・保存**。原本画面（invoicer_view_url）をワンクリックで開けるリンクも取得。
3. 発送時に**追跡番号を PayPal へ登録**（Add Tracking API）。
4. **ケース（dispute）の発生/更新/解決を webhook で受信**し、請求書/受注に紐づけ表示。

### PDF の整理（前項 §3「自社生成のまま」を具体化）
- PayPal 描画 PDF の自動取得は**公式 API が存在しない**（OpenAPI 仕様で全 endpoint 確認）ため**追わない**。非公式手段（内部URL叩き・ヘッドレス）は規約/破損リスクで**不採用**。
- 代わりに、原本レコード（PayPal Invoice 番号 INV2-…・金額・明細が自社レコードと一致）から **写しPDF を自社生成（reportlab・ADR-101 テンプレ SSOT）して自動保存**。写しPDF には「PayPal 請求書の写し」表記＋**原本リンク＋QR**を含める。
- **証明力の源泉は PayPal 側レコード**であり、写しPDF はその印刷物。原本が要る稀なケースは保存済み `invoicer_view_url` から手動 DL で運用（PO 合意）。

### スコープ（インクリメント）
- Inc1: 写しPDF 自動保存＋ `invoicer_view_url` 取得・ワンクリック導線（保存方式は DB 保存を既定・recon §5）。
- Inc2: 入金自動確認（`INVOICING.INVOICE.PAID` webhook）＝**PR #1980 実装済み**。
- Inc3: 追跡番号登録（`POST /v1/shipping/trackers-batch`・**transaction_id 必須**＝Inc3 で capture id 取得・保存）。
- Inc4: ケース管理（`CUSTOMER.DISPUTE.CREATED/UPDATED/RESOLVED` webhook → 既存署名検証基盤を流用 → dispute↔invoice/order 紐づけ表示）。

### 危ない変更・PO 依頼事項
- 新列・写しPDF 保存テーブルの **migration は本番投入前に Shingo の明示 GO 必須**。
- webhook 公開エンドポイント拡張は**署名検証を必須要件**（既存基盤あり）。
- **PayPal アカウント作業（Shingo 領域）**: REST アプリで Invoicing/Disputes 機能の有効化、webhook の dispute イベント本番登録、Add Tracking 利用可否確認。

---

## Context（背景）

見積・請求は「データ」ではなく注文＋マスタ＋発行者情報から生成する「書類」。現行GASは2版（正規化型／単一シート型）あり食い違う。送料・為替換算・支払い手数料・PDFは未実装。US向けのみDDPで関税を請求する等、テナント・国・顧客で条件が違う。

---

## Decision（What / Why / Scope）

### 確定した設計

#### 1. データ構造＝正規化2テーブル

**見積ヘッダ**（採番 `QT-00001`）＋**見積明細**（`QTI-00001`）。請求も同型。

- GASの「1行目に合計」方式は不採用
- ヘッダー名で読む（列順非依存）
- PDF URL保持

#### 2. 計算式

```
小計（Σ 単価 × 数量）
  ＋ 送料（テナント別キャリア）
  ＋ 支払い手数料（方法別 Wise/PayPal）
  → 必要なら通貨換算
  ＝ 合計
```

**通貨:**
- 既定JPY
- 外貨指定時のみライブレートで換算（USD/AUD/EUR/GBP）
- **使用レートはスナップショット保存**
- 有効期限：テナント設定（既定＝その日限り＝本日レート）。「翌日以降は変動」を明示

#### 3. 見積の発行タイミング

**登録フォーム前でも発行可能**（必要なのは 国＋キャリア＋商品＋数量）。承認された見積→請求へ変換（文書種別 QUOTATION→INVOICE 差し替え）。

#### 4. テンプレ設計＝標準1枚＋テナント変数

フリーフォーム自作不可。複数テンプレは将来（後から足せる構造）。

**標準項目（全テナント固定）:**

| 項目 |
|---|
| 文書種別 / 番号 / 日付 / 有効期限 / 宛先 / 明細 / 集計 / 注記 / フッター |
| 輸出必須項目（HSコード・Tax ID等）＝税関トラブル防止のため固定 |

**テナント変数:**

| 変数 | 仕様 |
|---|---|
| ロゴ | PNG/SVG・透過・ロゴ枠に自動フィット |
| ブランド色 | カラーピッカー・決まった場所のみ適用・文字色は可読性自動確保 |
| 発行者情報 | 管理センターのSSOTを自動流し込み |
| 有効期限既定日数 | テナント設定 |
| 注記/規約 | テナント設定 |
| 言語 | テナント設定 |
| 既定通貨 | テナント設定 |

#### 5. 請求書（INVOICE）仕様

| 項目 | 仕様 |
|---|---|
| 言語 | 顧客向けPDFは英語（スタッフUIは日本語、言語はテナント設定可） |
| 宛先 | **Bill To ＋ Ship To 両方**（見積はBill To＝名前＋国でよい） |
| 配送先 | **注文確定時のスナップショット**（顧客マスタ参照「生き値」にしない） |
| 必須項目 | Registration number / Due date / Invoice # / Payment Terms（方法・通貨・期限・手数料は買い手負担・Wise口座名義の注記） |
| 注記 | "Production"表記は"Description"に修正 |

#### 6. 発行モード

**大原則＝請求書は必ず自社システムに記録＋自社ブランドPDFを生成（SSOT）。**

| 決済方法 | モード |
|---|---|
| PayPal | (1) API自動（リンク自動発行＋入金自動確認） |
| PayPal | (2) 手動発行＋リンク貼付 |
| PayPal | (3) 自社PDF |
| Wise | 自社PDF＋メール送金（入金確認は手動）。請求書発行APIは想定しない |

テナント×決済方法で選択。

#### 7. 関税（Duty）ポリシー（テナント設定）

| 設定 |
|---|
| 既定インコタームズ（DAP/DDU/DDP） |
| 国別・顧客別の課税ON/OFF |
| 計算式（キャリア×国×テナント設定） |

**Duty行は課税判定時のみ表示**（例：US/DDP）。日本の輸出は消費税免税（0%）。

FedEx現行例（US）＝関税15%＋DDP手数料(請求額2% or $20の高い方)＋MPF 0.3464%($32.71〜$634.62) ※**一例**。正確な数式はキャリア連携の段で確定（後日）。

### 仕組み（意図）

「標準エンジン＋テナント別ポリシー」。構造は固定（崩れない）、変数だけ各社が変える。単価/発行者情報を1か所直せば全書類に反映。各社ブランドで出るが必須項目は崩れない。

---

## 実装上の注意（誤実装防止）

- **配送先はスナップショット（注文確定時の値を注文に保全）。** 顧客マスタ住所帳を後から変えても過去の請求書がズレない。請求書の配送先＝顧客マスタ参照「生き値」にしない（トラブル時に揉める）。
- **関税の数式をハードコードしない。** 「キャリア×国×テナント」設定。
- **送料はテナント別キャリアAPI**（後日）。設計上は「差し込める口」を用意し、未連携時は0でなく「未計算」を明示。
- 為替は**保存だけでなく取得・換算**を実装し、**使用レートをスナップショット**。
- 支払い手数料（Wise/PayPalで異なる）を合計計算に必ず含める。
- GASの2版を混在実装しない（正規化型に一本化）。
- 複数テンプレ・テンプレビルダーを今作らない（過剰実装）。色/ロゴ/発行者情報の変数化に留める。

---

## 依存・関連

- 注文: ADR-102
- 入金/完了: ADR-104
- テナント設定: ADR-106
- デザイントークン: ADR-095付録3
- 未決（送料数式・Wise API）: ADR-095付録1
