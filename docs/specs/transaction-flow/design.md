# design（便1：lead起点の親子構造確立）— 取引フロー

親（あるべき姿＋KGI）へのリンク: [README.md](README.md)

> この文書は何か（専門用語なしの1行）:
> お客さん(lead)を親として、商談・会社・受注・会話ログが必ずleadにぶら下がる状態を、コード修正とDB制約で実現するための便1の設計。

配置: docs/specs/transaction-flow/design.md
日付: 2026-07-15
PO: しんご
便: 便1（背骨必須化＋ライフサイクル順序）

---

## 1. あるべき姿（PO自筆・親から引用）

親 [README.md](README.md) §1 を正本とする（本書は道具）:

> lead が親、商談化したら deal の子IDが作成される、顧客がフォーム入力したらカンパニーの子IDが発行される、受注したら order の子IDが発行される。全ての子供は lead にぶら下がり、全てのデータが紐付き、分析できる状態になること。会話ログも lead ごとに紐づける。

---

## 2. KGI（便1のスコープ・○×で測る）

| # | 合格条件 | 測り方 | 合格ライン |
|---|---|---|---|
| B1-1 | 全deal・company・会話ログが、ちょうど1つのleadに辿れる | 各テーブルで親lead一意解決の行割合をSQL測定（NULL・複数解決0件） | 100% |
| B1-2 | orderはdeal_id経由でleadに辿れる（order.lead_idは作らない） | orders.lead_id列が存在しない＝1／order→deal→lead解決率 | 列なし=1 かつ 解決率100% |
| B1-3 | lead無しでdeal/company/会話ログを作れない | 負のテスト：lead無し登録を各3ケース試行し全拒否 | 3/3拒否（拒否率100%） |
| B1-4 | 便1のFK追加対象に孤児が無く、FKが張られている | conversation_logsのFK実在＋孤児0件をSQL測定 | FK在り=1 かつ 孤児0件 |

KPI: 達成KGI数 ◯/4。

親KGIのK3以降（分析軸マスタ化・ファネル出力＝S11・便5）は分類マスタ依存のため便1スコープ外。

---

## 3. recon（file:line 実物・推測禁止）

便1実装に効く確定事実（2026-07-15 実測・MAIN d28c933）:

親子構造（確定）:
- companies.lead_id → leads.id（tenant.py:194, 462-472）。leads本体にcompany_id列なし＝lead親・company子の片方向確定
- deals.lead_id NOT NULL REFERENCES leads.id（tenant.py:432）
- contacts.lead_id → leads.id（tenant.py:479-481・nullable）

順序逆転（直す対象）:
- convert_lead（leads.py:719-833）: company/contact存在・所属一致を先に確認してからdeal作成＝「会社が先」
- create_quote（quotes.py:154）＋QuoteCreate（quote.py:39）: company_id/contact_id必須＝設計図（deal経由一本化）と未整合
- 会社作成の抜け道: integrations.py:657-668 にlead無し会社insert（PAYPAL-TEST）

migration対象:
- conversation_logs.lead_id: 現状NOT NULL化済（20260703_020000_conv_backbone_ben1b.sql:20-24）だがFK無し（20260604_090000_create_conversation_logs.sql:34-55）
- 他（companies/contacts/deals/lead_channels/meta_messages）は既にleadsへのFKあり
- orders/quotes/invoices はlead_id列なし（deal経由設計・正しい）

実データ（tenant_004本番・tenant_006テスト）:
- deals・orders・quotes・invoices: 全0件（本番未使用）＝順序修正で壊れる取引データ無し
- companies.lead_id: 004で51件リンク済・NULL0・孤児0
- conversation_logs: 004で孤児0・NULL0／006で総13件・NULL3・孤児10
- contacts.lead_id: 004で52/52がNULL（便1スコープ外・別テーマ）

---

## 4. design（技術How）

### 4-1. コード修正①：商談化の順序（convert_lead）
- 現状: leads.py:748-786 でcompany/contact存在・所属一致を先に確認 → deal作成
- 変更後: company/contactチェックを必須から外し、deal作成はlead_id必須・company_id/contact_idはNULL可とする
- 意味: 商談化時点で会社未作成でもdealを作れる。会社は後続のフォーム入力で付与

### 4-2. コード修正②：見積のdeal一本化（create_quote）
- 現状: quotes.py:161-205 でcompany/contact所属一致検査、QuoteCreate（quote.py:39）でcompany_id/contact_id必須
- 変更後: 見積はdeal_id経由でcompany/contactを派生（deal前ならleadに紐づく）。company_id/contact_idの直持ち必須をやめる
- フロント波及: QuoteCreatePage（CompanyContactSelector）を「deal選択」ベースに変更。便1で最も画面波及が大きい箇所

### 4-3. コード修正③：会社作成の抜け道を塞ぐ（integrations.py）
- 現状: integrations.py:657-668 でlead無しのPAYPAL-TEST会社insert
- 変更後: この経路にlead必須化、またはテスト専用の明示ガード（本番テナントでは動作しない条件）を入れる
- 意味: KGI B1-3（lead無しでは会社を作れない）を満たす

### 4-4. migration④：conversation_logs.lead_id にFK追加
- 対象: conversation_logs.lead_id → leads.id のFK制約を新規追加
- 前提: FK追加前に対象テナントの孤児（lead_idがleadsに存在しない行）を0にする
  - tenant_004: 孤児0（掃除不要）
  - tenant_006: 孤児10・NULL3 → FK追加前に掃除（削除 or 正しいleadへ再接続）
- ON DELETE挙動: design時に確定（別途PO確認）。lead_channels=CASCADE・meta_messages=SET NULL を参考に決める

---

## 5. 弊害・トレードオフ（空欄不可）

- 見積のdeal一本化（4-2）はフロント画面の使い勝手を変える。既存の「会社を選んで見積」に慣れた運用からの移行コストがある。緩和: 便1完了後にUIの案内を追加
- migration（4-4）は危険操作。dry-run→GO→検算の手順が必須で、実行に時間を要する
- FK追加後は、アプリを通さない直接データ投入（CSV等）でもlead無しが物理的に不可になる。将来のCSVインポート機能は、この前提で自動採番（次テーマ予約）を実装する必要がある
- 便1はK1・K2に絞り、分析軸（K3以降）は未着手。分析画面の完成は便5を待つ

---

## 6. 外部・過去事例

- 該当あり: 便1bで conversation_logs.lead_id を NOT NULL化した先行手順（20260703_020000_conv_backbone_ben1b.sql）を踏襲。NOT NULL化の次段としてFK追加を行う自然な延長
- ssot-allocation.md のSSOT割当表（S1出自・S2 order会社関係・S12見積）をそのまま実装に落とす

---

## 7. 受入基準（各基準に検証方法を紐づけ）

- B1-1: 004で deal・company・会話ログの親lead一意解決率をSQL測定 → 100%（NULL・複数解決0件）
- B1-2: orders.lead_id列の非存在を\d ordersで確認＋order→deal→lead解決率SQL → 列なし かつ 100%
- B1-3: lead無しでdeal/company/会話ログ登録を各3ケース試行 → 3/3拒否。会社の抜け道（integrations.py）も塞がれていることを含む
- B1-4: conversation_logsのFK実在を pg_constraint で確認＋孤児0件をSQL → FK在り かつ 孤児0
- 全基準: まず006で予行（dry-run・BEGIN→変更→確認→ROLLBACK）し全基準を満たすことを確認してから004本番

---

## 8. 維持の仕組み（守り手）

- 守り手: conversation_logs.lead_id のFK制約（DB制約そのものが番人）＋既存の各lead子テーブルFK
- 対象: lead無しのデータがどの入口（アプリ・CSV・直接SQL）からも入らないこと
- コード側（4-1〜4-3）の守り手: 現状、順序を強制する関所は無い＝人手レビューで守る。将来、便のCIチェック化は別途recon→設計
- 関所なしの箇所（コードの順序）: 人手で守る＋理由（順序違反を機械検出する仕組みは未設計。FK＝DB制約が最終防波堤として実質的に順序を担保する）

---

## 9. 危険操作の手順（migration・本番）

順序（省略不可）:
1. 006の孤児掃除（会話ログ孤児10・NULL3を削除 or 再接続）
2. 006で予行（dry-run）: BEGIN → 4-1〜4-4適用 → 全受入基準確認 → ROLLBACK
3. バックアップ（004本番の対象テーブル）
4. PO自筆GO（GO #PR番号・Shingo または shingo-ops）
5. 本実行（004）
6. 検算（KGI B1-1〜B1-4のSQLを004で実測し合格ライン到達を確認）

SQL転送はファイル経由で psql -f。DB確認はSSH prod1経由のVPS内実行が唯一の経路。

---

## 10. 接触面分析（6面走査・空欄不可）

- ①人: PO（GO発行）・実装役（カード実行）・Morimoto-san（handover読者）
- ②エージェント: 本design.md・実装カード・executor-preamble。並行セッションへ active-work.md で節/ファイル先約
- ③機械: process-artifacts gate（migration・routers変更でGO必須判定）・husky hooks
- ④データ: tenant_004（本番・特別注意）・tenant_006（テスト・自由使用可）。孤児掃除は006のみ
- ⑤本番: deploy.yml・本番scriptsは触らない。migrationは本番DB（004）に適用＝要バックアップ
- ⑥外部: PayPal（integrations.py変更が決済テスト経路に触れる）・受信箱（会話ログFKが着信書き込みに影響しないか予行で確認）

---

## 11. 次テーマ予約（PO約束・2026-07-15）

CSVインポートの連番自動採番を、便1完了後の次テーマとして予約する（PO しんご 2026-07-15）:
- 仕様（PO自筆）: 末尾+1の連番を自動採番。末尾が0001なら1件取り込みで0002、10件なら0002〜0011を連番付与。lead_id・deal・company等の固有IDも同方式
- 目的: CSVインポート時にlead_id等が空でも自動で埋め、FK（便1で追加）に違反しない状態で取り込む
- 着手前に本テーマ専用のあるべき姿→KGI→reconを経る（既存designの流用不可）
