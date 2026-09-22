# Design: TCG_SCHEMA 配線統一

## 目的
全TCGコードの TCG_SCHEMA を "public" に統一し、tenant_004 参照を解消する。

## 変更前後
| 対象 | 変更前 | 変更後 |
|------|--------|--------|
| 10ファイルの TCG_SCHEMA | env var "tenant_004" | ローカル "public" |
| tcg_manufacturers/series/evidence_rules | tenant_004 のみ | public にコピー |
| line_import_devices.tcg_schema | 'tenant_004' | 'public' |

## 対象と対象外
- 対象: TCG_SCHEMA import → ローカルオーバーライド、3テーブル promote、デバイスDB更新
- 対象外: tcg_config.py 自体の変更、環境変数変更、tenant_004 テーブルの DROP

## 受入条件
| 基準 | 検証方法 |
|------|----------|
| tcg_config import がアプリコードに0件 | grep -rn "from app.tcg_config" backend/app/ |
| 3テーブルが public に存在 | psql SELECT from public.tcg_manufacturers |
| device.tcg_schema = 'public' | psql SELECT from public.line_import_devices |
| LINE import が正常動作 | import_jobs status=ok |

## 外部・過去事例の参照と我々への応用
- ADR-156 パイプライン17テーブルの tenant_004→public 移行（2026-09-21完了）の直接の続き。本PRはその残余配線10ファイルを同方針で統一する。
- 先行15ファイル（tcg_line_import.py 等）で `TCG_SCHEMA = "public"` ローカルオーバーライドパターンが実績あり。同一手法を適用。

## 維持の仕組み
- `grep -rn "from app.tcg_config import TCG_SCHEMA" backend/app/` で0件を CI でチェック可能（現状は手動確認）
- migration で public にコピーした3テーブルは tenant_004 側を将来 DROP する際の前提条件として記録済み（対象外・別PR）

## 対象ADR
ADR-156（SSOT migration）

## recon相互参照
docs/handoff/fix-tcg-schema-wiring/recon.md
