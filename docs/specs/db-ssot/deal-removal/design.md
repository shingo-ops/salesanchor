# dealsテーブル廃止・リード統合（deal-removal）— 設計図

> この文書は何か（専門用語なしの1行）:
> 商談（deals）を別テーブルで持つのをやめ、リードの状態の1つとして扱う設計。商談は「新規顧客と関係を築く1回きりの局面」なので、紙を分ける必要がないと判断した。親テーマ「DB設計のSSOT化」の子。

親: ../README.md ／ あるべき姿・KGI: ../ideal-state.md, ../kgi.md

## 1. あるべき姿（PO自筆・2026-07-18・原文のまま）

私の考えている商談とは新規顧客との商談で、最終的な結果は成約するか失注するか、対象外の結果しか想定していない
成約の方向であれば顧客登録フォームに記入をしてもらい顧客テーブルが作成され、そこから発注をいただければ請求書を発行することでorderテーブルが作成される

つまりdealとはリードで登録された新規の顧客と信頼関係を構築して新しいパートナーシップを築くための商談のことを指している

## 2. KGI（○×で測る）

| # | 合格条件 | 測り方 | 合格ライン |
|---|---|---|---|
| D1 | 新規の商談化でdealsテーブルに行が作られない | 商談化ボタン押下後のdeals行数増分 | 0 |
| D2 | 商談の金額・通貨・完了予定日がleadsで管理される | leadsに対応列が実在 | 1 |
| D3 | orders.deal_id 必須が解消され company_id 参照に置換 | スキーマ実測 | 1 |
| D4 | 失注理由（deal_close_reasons）がlead_id参照で維持され、既存データが失われない | 移設後の行数=移設前の行数 | 1 |
| D5 | dealsテーブルが全テナントから削除されている | \dt 実測でdeals不在 | 1 |
| D6 | 分析・ダッシュボードのdeals参照コードが0件 | git grep "FROM deals" = 0 | 0件 |

KPI: 達成KGI数 ◯/6

## 3. recon（実測・2026-07-18・origin/main ff093ab）

- 影響規模: py 272箇所・tsx/ts 302箇所・deal_id 391箇所・md 185ファイル
- DB依存: orders.deal_id NOT NULL（tenant.py:492）／leads.converted_deal_id FK（tenant.py:448-460）／deal_close_reasons（migrations/20260613_020000）
- conversation_logs.deal_id: 列あり・FKなし
- 過去便: docs/handoff/deal-removal-track-a/（ADR-121）は dashboard 可視参照外しのみ。テーブル温存。本設計と矛盾なし・前哨戦として接続

## 4. design（3段階）

- 段階①（書き込み停止）: 商談化はleads.statusの遷移のみに変更。leadsへ amount/currency/expected_close_date 相当を追加。deals新規作成コードを停止
- 段階②（読み替え）: 分析・ダッシュボード・受注のdeals参照をleads/companies参照へ書き換え。orders.deal_id→company_id移行。deal_close_reasons→lead_id参照へ移設
- 段階③（削除）: 全参照0を実測確認後、migrationでdeals削除（バックアップ→dry-run→PO自筆GO→実行→検算）
- 各段階は独立の便で recon→design→実装→GO を踏む。段階③は危険操作（migrations）

## 4.5 段階①の差分設計（PO確定・2026-07-18）

### 移す列・捨てる列（PO確定）
- leadsへ追加する3列: amount NUMERIC(15,2)・currency VARCHAR(10) DEFAULT 'JPY'・expected_close_date DATE
- 移さない（段階③で消滅）: title・probability・deal_code。理由: 1リード=商談1回のため案件名はリード名で代替、probabilityは温度感で代替済み、deal_codeはlead_codeが既存

### 書き込み経路の停止（recon 2026-07-18・origin/main 81165c7）
- 経路1: leads.py:719-833 convert_lead — deals INSERT（765行）を廃し、leads.status='negotiating'遷移＋amount/currency/expected_close_date の直接保存に書き換え。アトミッククレームは converted_deal_id から status 遷移条件へ変更
- 経路2: deals.py:168 INSERT・351 UPDATE — 新規作成APIを405封鎖（段階②で読み替え完了までUPDATE系は温存）
- 経路3: companies.py:454/760 会社マージ時のdeals更新 — 段階②で除去（段階①では温存）
- フロント: LeadsPage.tsx の商談化モーダルから会社・担当者・案件名入力を除去し、金額・通貨・完了予定日入力へ簡素化

### 段階①の受入基準
- 商談化操作後、dealsの行数増分=0（KGI D1）
- leadsに3列が実在（KGI D2）
- 既存テスト緑＋商談化の新テスト（3列保存の実測）追加

## 5. 弊害・トレードオフ（空欄不可）

- 工期が長い（複数便）。ただし段階①完了時点で新規データの二重化は止まる
- 「1リード=商談1回」が前提。同一リードと2回目の商談が将来必要になった場合、本設計は再検討が必要（現業務では再アプローチ状態で表現する）
- 既存deals実データ（金額・履歴）の移行手順は段階②のreconで確定する（本書では未確定と明記）

## 6. 外部・過去事例

- ADR-121 / deal-removal-track-a: dashboard可視参照の先行撤去（2026-06-23）。本設計はその延長
- ADR-089: customers→companies統一。テーブル統廃合の先例として手順を参照

## 7. 受入基準

各KGI（D1〜D6）の測り方をそのまま受入検証とする。段階ごとのPRで該当KGIのみ検証

## 8. 維持の仕組み

- 守り手: .github/workflows/（process-artifacts gate）。migrations変更はGO記録必須
- 対象: dealsが「復活」する実装（新規deals参照コード）の混入防止。段階③完了後、CI grepガード（FROM deals検出）の追加を検討

## 9. 接触面分析（6面走査）

- ①人: PO（GO発行）・実装役。②エージェント: 本design.mdが正本、着手時に必読。③機械: process-artifacts gate・migration-test.yml（deal_id記載2箇所は段階②で更新）。④データ: 全テナントdeals行（tenant_004本番は特別注意・移行はバックアップ必須）。⑤本番: 段階③はmigration=デプロイ順序リスク対象。⑥外部: 利用者画面から/dealsページが消える（段階②で導線変更）
