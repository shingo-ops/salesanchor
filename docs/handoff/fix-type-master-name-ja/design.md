# Design: type_master.name_ja 英語値の修正

recon: docs/handoff/fix-type-master-name-ja/recon.md
ADR: ADR-156

## KGI
買取相場ページのカテゴリタブが全て日本語で表示される

## 変更
- `migrations/20260925_010000_fix_type_master_name_ja.sql`: UPDATE 2行

## 触らない範囲
- アプリケーションコード（変更不要）
- 他のtype_masterエントリ（既に日本語）

## 検証方法
| 基準 | 検証方法 |
|---|---|
| id=2 name_ja='ワンピース' | 本番DB SELECT確認 |
| id=24 name_ja='クロススタァ' | 本番DB SELECT確認 |
| 買取相場タブに英語タブなし | 画面目視 |

## 外部・過去事例の参照と我々への応用
該当なし（内部マスタデータ修正）。seed ON CONFLICT DO NOTHING による既存行未更新はPostgreSQLの標準動作であり、UPDATEマイグレーションで補正するのが一般的手法。

## 維持の仕組み
守り手: WHERE条件で現在値を指定しているため冪等。type_master.name_ja は NOT NULL 制約あり。今後の seed では ON CONFLICT DO UPDATE SET name_ja = EXCLUDED.name_ja を検討。
