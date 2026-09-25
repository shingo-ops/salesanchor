# Recon: conditions テーブル match_type/effect 追加

## 調査日: 2026-09-25

## 既存実装の確認

### tcg_analyzer_svc.py
- `backend/app/services/tcg_analyzer_svc.py:load_condition_entries`: conditions テーブルから match_keyword 等を取得
- `backend/app/services/tcg_analyzer_svc.py:resolve_condition_v2`: KEYWORD パターンで状態解決
- `backend/app/services/tcg_analyzer_svc.py:_match_status_pattern`: REGEX/LITERAL/DEFAULT マッチングの実装（tcg_status_master で使用中）

### routers
- `backend/app/routers/conditions.py`: テナント向け conditions CRUD
- `backend/app/routers/super_admin_conditions.py`: SaaS 管理向け conditions CRUD + CSV

### schemas
- `backend/app/schemas/condition.py`: ConditionBase / ConditionUpdate
- `backend/app/schemas/central_masters.py`: CentralConditionBase / CentralConditionUpdate

## ADR 検索結果
- ADR-104, ADR-109, ADR-120 を確認
- conditions テーブル固有の ADR なし
- tcg_status_master の match_type パターンは ADR に記録なし（実装から確認）

## 変更前後の比較

### conditions テーブル（変更前）
match_keyword のみ → KEYWORD 動作のみ

### conditions テーブル（変更後）
match_type (KEYWORD/REGEX/LITERAL/DEFAULT) + effect (OUTPUT/EXCLUDE) を追加
KEYWORD デフォルトで既存動作を完全維持
