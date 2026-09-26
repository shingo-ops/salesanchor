# 設計骨格：取引フローのSSOT割当（Phase 3・design.md の土台）

> **この文書は何か（素人向け1行説明）**：「同じ事実は1か所にだけ書く」という原則で、取引の各事実の"正しい置き場所"を1つずつ決めた割当表。詳細設計（design.md）はこの割当に従って書く。

- **親文書**: `docs/specs/transaction-flow/README.md`（KGI承認済 2026-07-02）
- **根拠**: recon 2026-07-02（recon_a.txt / recon_b.txt・本番 `\d` 実測）
- **ステータス**: 骨格 **PO承認待ち**

---

## 0. 図解（PO確認済み 2026-07-02・v2）

- **DB構造の全体像（家系図＋帳簿）**: `images/ssot-db-structure-family-tree.svg` — lead を頂点に deal→company→order が順に生まれ、明細・仕入・トラブル・**出どころ（在庫接点 S14：自社在庫／ドロップシッピング・点線＝別仕様書 pending）**・事実の帳簿・マスタが繋がる図。
- **分析効果を最大化する仕組み**: `images/ssot-analysis-maximization-flow.svg` — 「①事実だけ記録 → ②答えは自動計算（保存しない）→ ③分析出力」の一方通行と、土台2つ（lead 1本の糸／マスタID＋SSOT）の図。

> **図解の同時更新ルール（文章規約・§1.6と同格）**：本仕様書群の構造（S表・KGI・テーブル関係）に触れる変更を行うPRでは、`images/` の該当SVGを**同一PRで**更新する。図と本文の不一致は「二重持ちのズレ」と同じ欠陥として扱う。
> リポジトリ登録時は `docs/specs/transaction-flow/images/` に配置し、親仕様書 README からも同パスで参照する。

## 1. SSOT割当表（事実 → 唯一の置き場所 → 重複の処遇）

| # | 事実 | SSOT（唯一の置き場所） | 現状の重複・分散（recon根拠） | 処遇 |
|---|---|---|---|---|
| S1 | 出自（どの lead から始まったか） | `deal.lead_id`・`company.lead_id`・`conversation_logs.lead_id` を **NOT NULL 直持ち**。order は `order.deal_id` **NOT NULL** 経由で辿る（**order.lead_id は作らない**＝経路の二重化禁止） | deals.lead_id 全NULL（006: 0/18）、companies.lead_id 2/51（004） | 必須化＋既存の穴は backfill |
| S2 | order と会社の関係 | `deal.company_id`（フォーム入力時にセット）。order の会社は **deal 経由の派生** | orders.company_id NOT NULL が独立に存在（`\d orders`）＝deal経由と**二重経路** | orders.company_id は「システムが deal から自動セット・手入力不可」に格下げ（保持は性能・RLS都合。値の正は deal 側） |
| S3 | 売った物（商品明細） | **`order_item` 新設**（product_id・condition_id・数量・単価・都度SKU・elogi用為替） | 明細が quote_items / invoice_items にだけ存在し「受注の明細」が無い | quote_items / invoice_items は**書類スナップショット**と役割を明記（分析には使わない）。分析は order_item のみ |
| S4 | 請求書発行の事実 | `invoices.issued_at`＋payment_method・currency（書類の事実は書類に） | orders.currency も存在（二重） | orders.currency は派生（invoice から）へ |
| S5 | 入金の事実 | `invoices.paid_at` | **orders.paid_at と invoices.paid_at の二重持ち**（両方の `\d` に実在） | orders.paid_at **廃止**（進行判定は invoice から導出） |
| S6 | 仕入の事実（発注・確定・支払） | `purchase_orders`（伝票：ordered_at・received_at・**paid_at 新設**）＋`purchase_order_items`（明細に **order_item_id 参照を追加**＝どの受注のための仕入か） | purchase_order_items が order と**未接続**（tenant.py:960-968）。⑤仕入費支払いの列が**なし** | 接続＋列追加。order_purchase_details（migration 049）は役割重複を精査し統合 |
| S7 | 発送の事実 | `order_shipping_details`（1受注に複数発送も表せる） | **orders に shipped_at/delivered_at/tracking 等が直付き**＋order_shipping_details テーブルが併存（二重） | orders 直付きの発送列は派生へ（正は details 側） |
| S8 | 進行段階 | **保存しない**。S4〜S7 の事実タイムスタンプから**導出**（K8） | orders.status が手動 varchar（default 'pending'） | orders.status 廃止（表示は導出値） |
| S9 | 成約 | **保存しない**。「入金済 ∧ 取引完了 ∧ 未解決トラブルなし」を**導出**（K9）。トラブルは **`trouble` 新設**（対象 order_item＋数量） | 成約列・トラブルテーブルとも**なし** | trouble 新設＋導出ロジック |
| S10 | 集計・派生値（累計・回数・利益・予測） | **保存しない**（ビュー/クエリで導出） | `order_financials` に**書込ルーター実在**（order_financials.py:152・006に9行）。companies/leads に per_order_amount・monthly_forecast 等の**手入力集計列** | 書込経路を閉鎖→派生ビュー化。AI予測値は「予測」領域として事実と分離（別途） |
| S11 | 分析軸（K3の6軸） | **マスタID参照**：channel_masters（既存）・countries_master（既存 migration 20260621）を FK 化。estimated_scale・店舗形態・取扱商材は**新マスタ** | 全軸が自由文字列 varchar（`\d leads`）。店舗形態・取扱商材は列自体なし | FK化＋新設。initiative は既存CHECK（inbound/outbound）でSSOT成立済み ✓ |
| S12 | 見積（本受注前の書類） | **deal（deal 前なら lead）に紐づく**。order には含めない。発行シーン：新規商談のクロージング／既存顧客の見積依頼 | quotes.deal_id は既存（tenant.py:820）だが company_id/contact_id 直も持つ二重経路 | 正は deal 経由に1本化（PO定義 2026-07-02） |
| S13 | 請求書（本受注確定の書類） | **order に属する**（invoice.order_id）。未入金・合意後破棄は `voided_at`/`void_reason`（既存列・本番実在）で**取消扱い**＝K9で非成約 | 現状は逆向き（orders.invoice_id が請求書を指す） | 向きを正常化（PO定義 2026-07-02） |
| S14 | 在庫との接点（自社在庫／ドロップシッピング） | 在庫本体は**別仕様書**（`docs/specs/inventory/README.md`・pending登録）。取引側は **order_item に「出どころ参照」1本だけ予約** | own_inventory 等の在庫資産は実在するが、業務のあるべき姿（2種在庫）は未設計 | 接点予約のみ。在庫のあるべき姿は在庫仕様書で別途PO対話 |

## 1b. 文書構造の決定（PO承認 2026-07-02）

各ドメイン（取引フロー・商材マスタ・在庫・予約販売・送料・住所・勤怠・CS・古物台帳）は**独立した仕様書**として索引 `docs/specs/README.md` に登録し、それぞれが自分のあるべき姿＋KGIを持つ（§1.7 新規テーマ＝フルセット）。仕様書同士は親子でなく**兄弟**、接点は**双方に相互参照1行**で同期する（文書のSSOT）。未着手ドメインは索引に「pending＋1行説明＋取引フローとの接点」で登録のみ行う。

## 2. ライフサイクル順序の正常化（K2・最大の構造差）

現状は **deal 作成に company_id＋contact_id が必須**（deal.py:57-58）＝「会社が先」で、あるべき姿と逆。設計：

```
商談化      → deal 作成（lead_id 必須・company_id は NULL 可）
フォーム入力 → company 作成（lead_id 必須）＋ deal.company_id をセット
請求書発行  → order 作成（deal_id 必須。company は deal から自動）
```

## 3. 外部・過去事例（設計docの必須欄・要旨）

- **単一グレイン＋単一経路**（Kimball 次元モデリングの定石）：同じ事実へ2経路あると集計が割れる → S1/S2 の経路1本化。
- **状態は保存せず事実から導出**（Stripe の payment status 設計等）：手動 status は必ず実態とズレる → S8/S9。
- **過去ADR**：ADR-096（conversation_logs＝会話SSOT）・countries_master／channel_masters の既存資産を流用（新発明しない）。

## 4. 段階計画（便割り・各便で recon→design→dry-run→GO）

| 便 | 内容 | 対応KGI |
|---|---|---|
| 便1 | 背骨必須化＋ライフサイクル順序（S1・S2・§2）＋既存51社/会話ログの backfill | K1・K2 |
| 便2 | order_item 新設＋仕入接続（S3・S6） | K5(素材)・K7 |
| 便3 | 段階・成約の導出化＋status/paid_at二重の解消＋trouble（S4・S5・S7・S8・S9） | K7・K8・K9 |
| 便4 | 派生値の書込閉鎖・手入力集計列の廃止（S10） | K10・K6 |
| 便5 | 分析軸のマスタID化（S11）＋ファネル/カルテ/優先リストの出力 | K3・K4・K5・K6 |

## 5. 維持の仕組み（design.md 各便で具体化する守り手の方針）

- DB制約（NOT NULL・FK・CHECK）＝「壊れたデータが作れない」の第一の守り手（K1負のテスト）。
- 書込経路の閉鎖は API 層＋テストで担保。CI 上の守り手は各便の design.md「## 維持の仕組み」欄で関所ファイルを名指しする。
