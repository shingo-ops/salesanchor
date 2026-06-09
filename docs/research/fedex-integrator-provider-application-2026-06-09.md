# 配送キャリア連携 申請ガイド（FedEx / DHL・salesanchor 外部販売向け）

- 作成日: 2026-06-09（DHL セクション追記: 2026-06-09）
- 目的: salesanchor を外部企業へ販売する前提で、各導入企業が「自社のキャリアアカウント」を連携して送料見積・送り状・インボイス・追跡を行えるようにする。そのための申請手順・問い合わせ文面・スケジュールをまとめる。
- 構成: §0–§5 = **FedEx**（Integrator Provider / Compatible 認定）。§6 = **DHL**（MyDHL API・FedEx より大幅に軽い）。
- 関連: ADR-123（配送キャリア Integrator 連携アーキ）、[配送キャリア接続テスト（実装済）](../../README.md)

---

## 0. 前提（調査で確定した事実）

- 日本企業でも実現可能。実例: **Ship&co**（京都・APAC 初の FedEx Compatible Provider）/ **AnyLogi（AnyMind Group・東京）**（FedEx API 連携済）。
- 両社とも「各導入企業が自社 FedEx アカウントを接続 → SaaS が送り状/インボイス自動発行」モデル＝salesanchor が既に実装した **テナント別・暗号化認証情報モデル**と同型。
- 「申請」は2段階: **(1) 入口**（Integrator 登録＋Agreement）と **(2) Integrator Provider Validation 本提出**（本番キーの関門。ラベル等の実装エビデンス提出が必要）。
- 本番キーは FedEx 検証チームの承認が条件（`validationmtp@fedex.com` 提出）。テストキーは口座不要で即取得可。
- 日本は非 US 経路（US/Canada 手順は対象外、API Validation サポート経由）。本番の配送アカウントは日本の FedEx アカウントで可の見込み（要・APAC FedEx API チーム確認）。

出典:
- FedEx Integrator Provider Validation: https://developer.fedex.com/api/en-us/certification/integrator-provider.html
- FedEx Developer Portal 日本: https://developer.fedex.com/api/ja-jp/home.html
- Ship&co × FedEx Japan: https://www.fedex.com/ja-jp/shipping/industry-solutions/ecommerce/compatible/ship-co.html
- AnyLogi（AnyMind）FedEx 連携: https://anymindgroup.com/ja/news/press-release/anylogi-api-fedex

---

## 1. FedEx API チーム（APAC）への問い合わせ文面

⚠️ **FedEx Japan は FedEx API の案内を行っていない**（2026-06-09 FedEx Japan 回答）。
**問い合わせ先＝APAC FedEx API チーム：`apacfedexapi@fedex.com`**。
参考: 越境EC向け Web Services https://www.fedex.com/ja-jp/shipping/industry-solutions/ecommerce/webservices.html ／ 開発者ポータル(日本語) https://developer.fedex.com/wirc/browser/#/ja-jp/home

APAC 窓口のため**英語**で送るのが確実です（下記 英語版）。【　】を埋めて使用。日本語版が必要なら別途用意可。

**To:** apacfedexapi@fedex.com
**Subject:** FedEx API Integrator Provider — eligibility & process for a Japan-based SaaS

```
Dear FedEx API Team,

We are [Company name], based in Japan. (FedEx account number: [9-digit, if any])

We develop a B2B SaaS product, "Sales Anchor," which we plan to sell to other
businesses. Each of our clients would connect their OWN FedEx account to our
product to perform rating, label (shipping) creation, commercial invoice
generation, and tracking — similar to providers such as Ship&co and AnyLogi.

We would appreciate your guidance on the following:

[A. Category & process]
1. For this model, is the correct organization type "Integrator Provider"
   (a company that sells/provides software using FedEx technology)?
2. As a Japan-based company, what are the steps, required documents, and typical
   timeline to register as an Integrator Provider and complete validation?
   (The developer portal notes the US/Canada steps do not apply outside those
   countries.)

[B. Account requirement]
3. For production, can we and our clients use Japan-based FedEx accounts
   (i.e., a US-based account is not required)?

[C. Validation]
4. Where do we obtain the PIW and the Integrator Validation Cover Sheet, and is
   validationmtp@fedex.com the correct submission address?
5. May we submit the Limited Validation APIs (e.g., Authorization, Address
   Validation) first, and complete the Ship/Rate validation afterwards?
6. Can the "Comprehensive Rates & Transit Times" (rating) API be validated and
   moved to production INDEPENDENTLY of the Ship API? (We understand the label
   format requirements apply only to label-generating APIs.)

We aim to apply and go live as early as possible. Thank you for your help.

[Company name]
[Name / title]
[Email] / [Phone]
```

---

## 2. Integrator Provider 登録手順（developer.fedex.com）

アカウントオーナー（しんごさん）操作。所要 30 分〜。

| Step | 操作 | 補足 |
|---|---|---|
| 1 | developer.fedex.com でユーザー登録 or ログイン（言語 ja-jp 切替可） | 会社ドメインのメール推奨 |
| 2 | 「Create Organization（組織を作成）」 | |
| 3 | 組織タイプ＝**「FedExの技術を組み込んだソフトウェアを販売または提供（＝Integrator Provider）」を選択** | ★自社利用(1番目)ではなく**2番目** |
| 4 | 会社情報・会社ドメインのメール・対象地域（service territories）入力 | |
| 5 | 配送/請求アカウント番号を追加 | テスト段階は不要・本番化時に必要（日本アカウント可かは§1 で確認中） |
| 6 | **FedEx Integrator Agreement に同意** | 内容確認の上で同意 |
| 7 | プロジェクト作成 → **Test 用 API Key / Secret 取得** | 口座不要・即発行。これで実装に着手可能 |
| 8 | （後日）Request Production keys → Validation 提出 → 承認で本番キー | Phase D |

→ Step 7 完了で salesanchor 側の Ship/Rate/ラベル実装に実テストキーで着手できる（最短化の起点）。

---

## 3. 申請までのスケジュール（Claude Code フル稼働・本案件最優先 前提）

| マイルストーン | 最短 | 安全側 |
|---|---|---|
| 入口申請（登録＋Agreement＋テストキー＋APAC FedEx API 問い合わせ送付） | 今週中（〜6/13） | 6/16 |
| 限定 Validation 申請（Auth＋住所検証＝PIW+Cover Sheet のみ） | 6/16〜6/20 | 6/23 |
| Ship/ラベル本 Validation 提出（本番キーの本申請） | 6月末〜7月初 | 7月中旬 |
| FedEx 審査通過 → 本番キー | 7月中旬 | 7月下旬〜8月 |
| FedEx Compatible 認定（市場販売・ベータ脱却後） | 製品リリース後 | — |

### 律速（Claude では縮まない外部要因）
1. APAC FedEx API 問い合わせ応答（apacfedexapi@fedex.com・日数非公開）
2. FedEx 検証チームの審査時間（提出後・数日〜数週・差戻しリスク）
3. **600DPI ラベルの物理「印刷＋スキャン」**（実機が必要）
4. しんごさんの登録/Agreement/承認

### 必要工数（Claude フル稼働で大幅圧縮可。律速は上記外部要因）
Rate / Ship+ラベル(PDF/PNG/ZPL・600DPI・国際AWB・複数個口) / インボイス / Track / エンドカスタマー登録+MFA / EULA・disclaimer。詳細は ADR-123。

---

## 4. 申請に必要な実装（Validation 提出物に対応）

| 提出物 | 必要な実装 |
|---|---|
| Ship トランザクション 3形式（PDF/PNG/ZPL） | Ship API + ラベル生成（600DPI・国際AWB・複数個口） |
| エンドカスタマー登録（MFA 付き）JSON | エンドカスタマー登録フロー + MFA |
| スクショ（FedExサービス画面/disclaimer/EULA/登録フロー） | UI に FedExサービス表示・免責文・EULA・登録導線 |
| ラベルスキャン画像 | 物理プリンタ＋600DPIスキャナ |
| PIW / Integrator Validation Cover Sheet | 書類記入（会社情報＋利用APIの選択） |

---

## 5. 次アクション（FedEx）

1. **【最優先】APAC FedEx API チーム（apacfedexapi@fedex.com）へ §1 の問い合わせを送付**（外部依存を即始動・全体の律速）
2. **§2 の登録**（しんごさん操作・私が逐次案内）→ テストキー取得
3. ADR-123 の実装計画に沿って Phase B（Rate/Ship/ラベル/インボイス）着手（テストキー到着後）

---

# 6. DHL（MyDHL API）— FedEx より大幅に軽い経路

## 6.1 結論
DHL は **SaaS 側の重い認定が不要**。各テナントが**自分で DHL の API キーを取得**して salesanchor に入力すれば動く（既存の接続テストページで土台は対応済み）。FedEx の Integrator Validation（PIW / Cover Sheet / ラベル3形式 / MFA登録フロー / スクショ提出）に相当するものは **DHL では不要**。

## 6.2 仕組み（per-customer モデル）
- 各顧客が**自社の DHL Express 口座（9桁）**を前提に、developer.dhl.com（**日本語対応**）で登録 →「Get Access」→ **「既存のプラグイン/EC/サードパーティ製ソリューション用に認証情報が必要」オプションを選択**（third-party ツール利用を DHL が公式に想定）→ **通常 翌営業日に承認**（「Test Access Approved」＋「Production Access Approved」の2通）→ **自分の API Key / Secret** を取得 → salesanchor に入力。
- **日本公式対応・日本の DHL 口座でOK**（米国アカウント不要）。
- 責任分界: third-party ツールに使わせても**口座保有者（顧客）が責任**を負う＝顧客が自分のキーで使う前提。
- 実例: Ship&co / AnyLogi / ShipStation 等が「複数の DHL アカウントを各キーで接続」運用。

## 6.3 FedEx との比較
| 項目 | FedEx Integrator Provider | DHL Express MyDHL API |
|---|---|---|
| SaaS側の認定 | 重い（Validation 提出→審査） | **ほぼ不要**（各顧客が自分でキー取得・third-party用オプションあり） |
| 各顧客の手続き | 自社FedEx＋テストキー | DHL口座＋申請→**翌営業日承認**（test＋prod両方） |
| 本番移行 | Validation 承認 | DHLコンサル/ポータル経由（軽い） |
| パートナー認定 | FedEx Compatible（任意・年次再認定） | DHL eCommerce Certified Partner（任意・メール申請） |
| 日本 | 非US経路で可（要確認） | **日本公式対応・JP口座OK** |

## 6.4 要件
- **SaaS（salesanchor）側**: 特別な認定は不要。テナント別に DHL の API Key/Secret を暗号化保存（**実装済み**）。Rate/Ship/ラベル/追跡は MyDHL API を実装（Phase B・FedEx と並行）。
- **各導入企業側**: 有効な DHL Express 口座 → developer.dhl.com で「third-party solution 用」を選んで申請 → 翌営業日承認 → 自分のキーを salesanchor に入力。
- **任意（推奨・パートナー化）**: DHL eCommerce **Certified Partner** にメール申請（ディレクトリ掲載・共同マーケ。FedEx Compatible 相当）。市場投入後。

## 6.5 すべきこと
1. **REST 版キーで接続テスト**: 以前見つかった顧客の古いキーは **MyDHL API XML 版**＝REST 版とは別物。developer.dhl.com で **REST 版**のアプリ/キー（「third-party solution 用」を選択）を取得 → salesanchor の DHL ページで接続テスト。
2. **Phase B 実装**: MyDHL API の Rate / Shipment（送り状・ラベル）/ Tracking を実装（FedEx と同時）。
3. **任意**: DHL Japan / DHL eCommerce のパートナー窓口へ certified partner 申請（市場投入後）。
4. **DHL への確認（軽め）**: ①各顧客が「third-party solution 用」キーで salesanchor を使う運用で問題ないか ②Express の partner certification の日本窓口・要件。

## 6.6 出典（DHL）
- DHL Developer Portal（日本語）: https://developer.dhl.com/?lang=ja
- MyDHL API (DHL Express) リファレンス: https://developer.dhl.com/api-reference/mydhl-api-dhl-express
- Test→Production 移行: https://support-developer.dhl.com/support/solutions/articles/47001224426-i-have-access-to-mydhl-express-test-api-how-can-i-move-to-production-
- DHL eCommerce Certified Partner Program: https://www.dhl.com/us-en/home/ecommerce/business-help-center/partner-program.html
- Ship&co：DHL REST API キー取得手順（per-customer 例）: https://support.shipandco.com/hc/en-us/articles/38801071543449-How-to-Obtain-DHL-Express-REST-API-Key-and-Secret-for-Ship-co-Integration
