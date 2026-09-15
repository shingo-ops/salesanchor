# 抽出試行記録・限定修正の設計根拠

固定ソース: e594d3ef、対象service/migrationはmain5afb5af1と一致。結果はrootが隔離PostgreSQL16.15で直接実行したもの。

- result-real-db.txt: 現行コードの不具合再現。正常/反復適用と不正CHECK/FKの通過、実recorder上限境界と超過サイズNULL。
- result-candidate.txt: 記録修正の検証用コピーで、超過サイズ保存を確認。構造比較は旧方式のため不正構造を受入れている。
- result-structure.txt: 構造比較候補の正常7/不正8/未知等価式1の16ケース。製品migration組込みの試験結果ではない。
- structure-expected.json: 正規DDLから独立した隔離基準schemaを生成して採取した9制約の期待値。顧客データを含まず、本番表から期待値を生成していない。

候補実行スクリプト/固定sourceは元の調査作業台に保存。正式な再現・回帰は本PRのbackend/testsによる実migration/実task試験で実施する。上記候補結果を正式試験の合格に転用しない。
