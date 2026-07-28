# recon: 便E DROP TABLE deals

## 調査日時
2026-07-29

## 対象テナント
- tenant_001, tenant_003, tenant_004, tenant_005, tenant_006（deals テーブル存在）
- tenant_002（deals テーブルなし・スキップ）

## deals 依存オブジェクト実測（DROP 直前）

| 種別 | 件数 | 備考 |
|---|---|---|
| FK（deals を指す） | 0 | 実測確認 |
| ビュー（deals 参照） | 0 | 前置き: tenant_005.v_company_stats を付け替え後 |
| 関数 | 0 | 実測確認 |
| トリガー | 0 | 実測確認 |
| RLS ポリシー | 4 | deals 自身のポリシー（DROP で自動消去） |
| pg_depend 外部依存 | 0 | AUTO(シーケンス・インデックス)は除く |

## deals 行数（DROP 直前）
- tenant_001: 0
- tenant_003: 0
- tenant_004: 0
- tenant_005: 0
- tenant_006: 18（QAデモデータ）

## 前置き補完
- tenant_005.v_company_stats が deals を参照したまま（D-2 漏れ）
- DROP 直前に deals 参照除去 → 依存ゼロを確認してから DROP 実行

## バックアップ
- pre_drop_deals_20260729_042503.dump（2.4M / 04:25 JST）
- パス: /home/ubuntu/backups/postgres/pre_drop_deals_20260729_042503.dump
