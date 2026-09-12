---
mode: handoff
status: implementation-ready
---
# Phase 3 設計 — 配信プレビューの不存在列修正

配信プレビューが開けない原因を直し、最後に解析した日時で直近30日を数えるための設計です。
親: [PMG取込・配信](../pmg-import-delivery-ssot/design.md)。
**対象ADR**: ADR-113、ADR-154
**recon**: docs/handoff/dist01-ar-created-at/recon.md
**日付**: 2026-09-12
**担当**: 設計担当（Planner→Architectの同一AI自己審査）

## 合意と承認の境界

POへ「最後に解析した日時」を推奨し、更新日時を代替として提示。その後のPO原文「進める」を推奨案の採用として受領。基準列はcomputed_atに確定する。
先行するPO原文「修正してくれ、離席するのでgo承認モード」は修正依頼として記録する。GO委任の開始・失効・承認経路は未整備であり、代理GO・マージ・本番反映の承認には使わない。
この設計担当は製品実装へ切り替わらず、実装カードを既存の実装担当へ渡す。新規エージェントは起動しない。

## What / Why

main adc8bc4dの_fetch_flag_gate_statusは存在しないar.created_atを参照する。正規migrationはcomputed_atとupdated_atのみ定義する。PR #3258 HEAD 3df471abはupdated_atへ置換する案だが、今回のPO合意でcomputed_atへ変更する。
解析サービスは再解析時にcomputed_atを現在時刻へ更新する。人の修正/後処理には日時を更新しない経路があるため、updated_atをすべての更新日時と説明できない。最後の解析からの経過を測るという合意をcomputed_atで表す。
既存のAPIテストはサービスを模擬しており問題のSQLを実行しない。過去CIはSUCCESS32/SKIPPED7でもこの不具合を検出していない。実SQLの回帰と境界試験を追加する。

## 対象・対象外・変更前後

製品変更はbackend/app/services/tcg_distribution_svc.pyの_fetch_flag_gate_status内の30日条件1行のみ。
既存PRでは `AND ar.updated_at >= NOW() - INTERVAL '30 days'` を `AND ar.computed_at >= NOW() - INTERVAL '30 days'` に置換する。
最新mainの未修正版ではar.created_atとなっている。対象関数内の一致を確認して置換し、他関数の日時参照を一括置換しない。
追加試験はbackend/tests/test_tcg_distribution_pg.py。文書は本設計・recon・実装カード。
最新mainのTCG_SCHEMA設定化・12列出力・再解析未完了時の配信停止を保持する。
API契約、DB migration、CI設定、運用scripts、配信有効化設定、JOIN/COUNT方式の変更は対象外。504修正も別設計でREVISE継続。

## 外部・過去事例の参照と我々への応用

外部事例は不要。自社の不存在列参照であり、正規DDL・製品関数・修正前後の実SQLで直接判断する。
既存のbackend/tests/test_tcg_product_list_pg.py:23–53の正規migration・ローカルDB限定・ランダムschema・rollback方式を採用する。

## 実SQL試験契約

ローカルjarvis_test_dbだけを許可し、UUID付き専用schemaをトランザクション内で作る。終了時はrollbackし、共有schemaを削除しない。
TCG_SCHEMAを試験schemaへ差し替える。正規migration 20260831_110000_create_tcg_analysis_tables_t004.sql、20260903_170000_item_corrections_t004.sql、20260903_210000_tcg_distribution_settings_t004.sqlを試験schemaへ適用する。created_atを追加しない。
必須FKはsource_messages→extraction_jobs→extraction_items→analysis_resultsの順に合成データを投入する。source_messagesはsupplier_channel_id=NULLを使える。analysis_resultsにはpid_resolved、unit_resolved、needs_review、engine_versionを明示する。条件値以外のマスタFKはNULLとし、実商品データは使用しない。
実行対象は製品_fetch_flag_gate_status、fetch_preview_data、プレビューAPI。SQLやサービス戻り値を模擬しない。API試験では認証とDB依存のみ試験用に置換する。外部Sheets呼出しは試験内で呼出し禁止とし、実配信をしない。
Tは同一試験トランザクションのNOW()。全fixtureをTから作り、実時間待ちを使わない。以下は合成入力であり本番実測件数ではない。

| ケース | 入力 | 期待値 |
|---|---|---|
| 不存在列の回帰 | 正規DB定義、補正テーブルあり | 修正前は不存在列エラー、修正後は成功。同じ試験を前後で実行 |
| 空 | FLAG_SINGLE 0件 | recent_samples=0、rate=null、insufficient_samples |
| 下限未満 | FLAG_SINGLE49件、補正0件 | 49、0.0%、insufficient_samples |
| 下限ちょうど | FLAG_SINGLE50件、補正0件 | 50、0.0%、threshold_met |
| 許容上限 | FLAG_SINGLE100件、別々の5明細に補正1件ずつ | 100、5.0%、threshold_met |
| 許容超過 | FLAG_SINGLE100件、別々の6明細に補正1件ずつ | 100、6.0%、threshold_not_met |
| 30日境界 | computed_at=T-30日-1秒、T-30日、T-30日+1秒の3行 | recent_samples=2 |
| 日時列の区別 | A: computed_at=T-1日/updated_at=T-31日、B: computed_at=T-31日/updated_at=T-1日 | Aだけを集計、recent_samples=1。Aに最近の補正1件、Bに補正なしを置き、rate=100.0%も確認 |
| 補正日時の境界 | 対象行3件、補正日時は30日境界の前/ちょうど/後 | corrected_count=2相当、rate=66.7% |
| FLAG以外 | 最近の非FLAG_SINGLE行だけ | recent_samples=0 |
| 補正表なし | 補正migrationを適用しない別の隔離fixture | no_correction_table |
| API実接続 | 上記DBと実サービスでGET preview | HTTP200、件数/ゲート値一致、include_flag_singleはfalseのまま |

「不存在列の回帰」は現在mainの関数を使う修正前と、修正後で同じ正常系試験を走らせて失敗→成功を記録する。最終的な試験コードに不存在列エラーを正常扱いする分岐を残さない。
日時列の区別試験ではA/Bの件数だけでなく補正率も確認し、別の1行を誤って選んでも成功しないようにする。
1明細に複数修正がある場合のJOIN増幅は既存の別論点として維持し、本便の成功を精度ゲート全体の意味の正しさと説明しない。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 実DB定義でプレビューが200 | 新規test_tcg_distribution_pg.pyのAPI試験（サービス非模擬） |
| 最後の解析日時の30日境界を使う | 上表の境界とA/B試験で件数2、件数1/率100.0%を検証 |
| 既存の閾値分岐を維持 | 上表の0/49/50/100件ケースを実PGで検証 |
| 本番・外部配信への書込みなし | ローカルDB限定fixture、外部呼出し禁止、preview前後の設定比較 |
| 回帰が検出できる | 同一試験で修正前失敗と修正後成功の出力・HEADを保存 |
| 最新mainの変更を保持 | main統合後の実差分と既存配信試験を確認 |

## 計画票

1. 実装担当は既存release/fix-dist01-ar-created-atを継続し、設計文書を保持してmainを統合する。
2. 製品の1行と専用試験を実装し、実PGで修正前後を検証する。修正前の再現のため対象1行だけを一時的にmainのcreated_atへ戻し、終了後computed_atを復元する。無関係な差分は戻さない。
3. lint・実PG専用試験・既存配信試験の結果と差分を報告する。失敗は修正担当が本設計の範囲内で直し、設計変更が必要なら戻す。
4. 最終HEADのReviewer/CI確認と本番承認は別工程。現在のカードはローカル実装・検証・コミットまでで、push/PR本文更新/マージ/本番操作を含めない。

## 復旧・リスク

この修正はSELECTのみでデータを変更しない。異常時は配信・再解析を新規開始せず、HEAD、GET結果、ログを保存し設計担当へ戻す。
未設計のcreated_at追加migrationを復旧手段にしない。既知の500を再導入するrevertを成功扱いしない。デプロイ取消・旧版復元が必要なら、対象版と影響を確認した別承認で扱う。
再解析するとcomputed_atが更新され、古い投稿も直近の解析として集計に入る。これは「投稿から30日」ではなく、今回合意した「最後の解析から30日」の仕様である。

## PR記載の訂正

前回の「削除するファイルをなしへ変更」という指摘を撤回する。scripts/check-process-artifacts.js:797–817は1行以上の削除・置換も宣言対象とする。サービスの記載は正しい。公開本文を変更する工程では実numstatに従う。
過去のGO本文は新しい変更やHEADの承認根拠に読み替えない。

## Architect整合検査

APPROVE（この限定修正設計のみ）。同一AI自己審査であり独立した第二者レビューではない。
根拠: 正規DDLと不存在列、解析時刻の更新経路、POの日時選択、対象関数の1行置換以外の一致、既存PG隔離方式、既存CIのPostgreSQL接続とpytest収集を照合した。
受入条件は実SQL・日時境界・API結果で判定可能。実装範囲と対象外、復旧境界を固定した。実装試験の成功は未確認であり、設計合格を製品合格やGOにしない。

## 維持の仕組み

守り手: .github/workflows/test.yml
実装担当が新規test_tcg_distribution_pg.pyを維持し、Reviewerが修正前失敗/修正後成功とCIの非skipを確認する。CIにはRLS_ADMIN_DATABASE_URLがありpytestで新規ファイルが収集される。環境不足によるskipを合格にしない。設計担当が日時の意味、POが変更の採否を維持する。


## 2026-09-12 実装委任とローカル試験環境の補正

POからCodex Terra起動・ローカル実装/試験/コミットまでの限定委任について「進める」を受領し実装担当を起動した。追加エージェントは禁止、rootは設計/読取レビューを継続。新規エージェント未起動という冒頭記録は本節で更新する。
初回実装は設計文書54c3c241、main統合8f64ebfaまで完了、コード/試験は未コミット。Docker socketなしとPython3.14/Bandit内部エラーで実PG未検証。製品不合格ではなく環境前提不足として分類し、カード02に補正した。
実機にはPython3.12.8とColima0.10.3、停止中sa-private-ci profileがある。既存profileは触らず、今回だけのdist01-3258をCPU1/メモリ1GiB/ディスク4GiB、既定context/SSH config変更なし・mountなしで起動し、終了後停止する。Python3.12専用venvへ指定依存を導入する。
Context7 MCPは利用可能一覧に存在しなかった。許可済み代替としてColima公式 https://github.com/abiosoft/colima と実機start/status --helpを確認した。CLIのprofile、cpus/memory/disk、activate/ssh-config/mount引数を照合。製品・CI・本番設定の変更はない。
限定補正の自己審査APPROVE: ローカル実テストの既存目的内、他環境分離、資源上限と終了条件を固定。実PG実測結果はまだ未確認。


## 2026-09-12 実装検証とPR更新依頼

実装510548c3でcomputed_atの1行修正と専用実PG試験を保存。修正前実DBの不存在列エラー8失敗/2成功、修正後専用+既存試験35成功/skip0をTerraが実行しrootがログ照合した。Ruff成功、Bandit高重大0/skip0。mypyは最終ログ531診断で非blocking、途中71という報告は訂正。同環境mainの全診断比較は未実施。試験専用Colima停止済み、製品依存・CI変更なし。
PO原文「進めるPRマージして本番反映させてくれ」を受領。既存PR更新とCI確認をカード04で進める。番号付きGO原文を創作せず、現行検査の形式が揃うまでマージしない。旧updated_at案のGO記載は新HEADへ再利用しない。
