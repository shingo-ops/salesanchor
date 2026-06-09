# FedEx Integrator Provider 申請ガイド（salesanchor 外部販売向け）

- 作成日: 2026-06-09
- 目的: salesanchor を外部企業へ販売する前提で、各導入企業が「自社の FedEx アカウント」を連携して送料見積・送り状・インボイス・追跡を行えるようにする。そのための **FedEx Integrator Provider / FedEx Compatible 認定**の申請手順・問い合わせ文面・スケジュールをまとめる。
- 関連: ADR-122（配送キャリア Integrator 連携アーキ）、[配送キャリア接続テスト（実装済）](../../README.md)

---

## 0. 前提（調査で確定した事実）

- 日本企業でも実現可能。実例: **Ship&co**（京都・APAC 初の FedEx Compatible Provider）/ **AnyLogi（AnyMind Group・東京）**（FedEx API 連携済）。
- 両社とも「各導入企業が自社 FedEx アカウントを接続 → SaaS が送り状/インボイス自動発行」モデル＝salesanchor が既に実装した **テナント別・暗号化認証情報モデル**と同型。
- 「申請」は2段階: **(1) 入口**（Integrator 登録＋Agreement）と **(2) Integrator Provider Validation 本提出**（本番キーの関門。ラベル等の実装エビデンス提出が必要）。
- 本番キーは FedEx 検証チームの承認が条件（`validationmtp@fedex.com` 提出）。テストキーは口座不要で即取得可。
- 日本は非 US 経路（US/Canada 手順は対象外、API Validation サポート経由）。本番の配送アカウントは日本の FedEx アカウントで可の見込み（要・FedEx Japan 確認）。

出典:
- FedEx Integrator Provider Validation: https://developer.fedex.com/api/en-us/certification/integrator-provider.html
- FedEx Developer Portal 日本: https://developer.fedex.com/api/ja-jp/home.html
- Ship&co × FedEx Japan: https://www.fedex.com/ja-jp/shipping/industry-solutions/ecommerce/compatible/ship-co.html
- AnyLogi（AnyMind）FedEx 連携: https://anymindgroup.com/ja/news/press-release/anylogi-api-fedex

---

## 1. FedEx Japan への問い合わせ文面（テンプレート）

送り先（おすすめ順）: ① 既存の FedEx 営業/アカウント担当者 ② developer.fedex.com（ja-jp）のサポート ③ FedEx Compatible 窓口（営業経由）。【　】を埋めて使用。

**件名:** FedEx Integrator Provider / Compatible 認定について（日本法人・自社SaaSへのAPI組込のご相談）

```
FedEx ご担当者さま

お世話になっております。【会社名】の【担当者名・役職】と申します。
（弊社 FedEx アカウント番号：【あれば記載／9桁】）

弊社では自社開発の B2B SaaS「Sales Anchor」を提供しており、今後この製品を
外部企業へ販売・提供する予定です。各導入企業が「自社の FedEx アカウント」を
本製品に連携し、送料見積・送り状(ラベル)・インボイス発行・追跡を行えるように
したいと考えています（Ship&co 様や AnyLogi 様と同様のモデルです）。

つきましては、以下についてご教示いただけますでしょうか。

【A. 区分・手続き】
1. 上記モデルの場合、developer.fedex.com の組織タイプは
   「Integrator Provider（ソフトウェアを顧客に提供）」で正しいでしょうか。
2. 日本法人として Integrator Provider 登録・FedEx Compatible 認定を取得する
   際の、日本での申請手順・必要書類・標準的な所要期間をご教示ください。
3. FedEx Compatible 認定の日本窓口（Channel Manager 等）と、費用の有無を
   ご教示ください。

【B. アカウント要件】
4. 本番（production）移行に必要な配送/請求アカウントは、
   「日本の FedEx アカウント」で問題ありませんか。
   （米国アカウントが必須でないことの確認です）

【C. 検証(Validation)】
5. Integrator Provider Validation の提出物（PIW / Integrator Validation
   Cover Sheet 等）の入手先と提出先（validationmtp@fedex.com で良いか）を
   ご教示ください。
6. まず「限定 Validation（Authorization / 住所検証 等＝PIW・Cover Sheet のみ）」を
   先行して申請し、その後に出荷(Ship)・ラベルの Validation を行う進め方は
   可能でしょうか。

弊社としては可能な限り早期の申請・本番化を目指しております。
お忙しいところ恐縮ですが、ご回答のほどよろしくお願いいたします。

【会社名】
【担当者名・役職】
【メール】／【電話】
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
| 入口申請（登録＋Agreement＋テストキー＋FedEx Japan 問い合わせ送付） | 今週中（〜6/13） | 6/16 |
| 限定 Validation 申請（Auth＋住所検証＝PIW+Cover Sheet のみ） | 6/16〜6/20 | 6/23 |
| Ship/ラベル本 Validation 提出（本番キーの本申請） | 6月末〜7月初 | 7月中旬 |
| FedEx 審査通過 → 本番キー | 7月中旬 | 7月下旬〜8月 |
| FedEx Compatible 認定（市場販売・ベータ脱却後） | 製品リリース後 | — |

### 律速（Claude では縮まない外部要因）
1. FedEx Japan 問い合わせ応答（日数非公開）
2. FedEx 検証チームの審査時間（提出後・数日〜数週・差戻しリスク）
3. **600DPI ラベルの物理「印刷＋スキャン」**（実機が必要）
4. しんごさんの登録/Agreement/承認

### 必要工数（Claude フル稼働で大幅圧縮可。律速は上記外部要因）
Rate / Ship+ラベル(PDF/PNG/ZPL・600DPI・国際AWB・複数個口) / インボイス / Track / エンドカスタマー登録+MFA / EULA・disclaimer。詳細は ADR-122。

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

## 5. 次アクション

1. **【最優先】FedEx Japan へ §1 の問い合わせを送付**（外部依存を即始動・全体の律速）
2. **§2 の登録**（しんごさん操作・私が逐次案内）→ テストキー取得
3. ADR-122 の実装計画に沿って Phase B（Rate/Ship/ラベル/インボイス）着手（テストキー到着後）
