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

## 外部事例
該当なし（内部マスタデータ修正）

## 守り手
type_master.name_ja は NOT NULL 制約あり。WHERE条件で現在値を指定しているため冪等。
