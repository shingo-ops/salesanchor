# design: PR本文の半角かっこ注記をファイル名から外す

参照: recon.md（同ディレクトリ）、ADR-121

## 変更の前後

scripts/check-process-artifacts.js:266 と :274 の2行。

前: .replace(/（[^）]*）/g, '')
後: .replace(/[（(][^）)]*[）)]/g, '')

## 触らない範囲

- 解析のそれ以外の部分、ゲートの判定ロジック、ワークフロー定義。
- migrations/・deploy.yml・本番サーバー。

## 受入条件

|基準|検証方法|
|---|---|
|a: 削除欄の「- migrations/a.sql (22行削除)」が migrations/a.sql になる|node scripts/tests/test-process-artifacts.js の 注記かっこ除去テスト (a)|
|b: 全角の注記も従来どおり外れる|同 (b)|
|c: 注記なしのパスはそのまま|同 (c)|
|d: 触る欄の半角注記も外れる|同 (d)|
|変更前は a と d が失敗する|変更前に実行し 2 FAIL を確認済み（121+4=125 件中 123 PASS / 2 FAIL）|
|既存テストと CI が通る|同スクリプト全 PASS（125 PASS / 0 FAIL）と PR の checks|

## 外部事例

該当なし：社内の正規表現修正のため。

## 維持の仕組み

scripts/tests/test-process-artifacts.js に追加したテスト a〜d。

## 戻し方

このPRを revert する（2行とテストのみ。DB・本番に影響なし）。
