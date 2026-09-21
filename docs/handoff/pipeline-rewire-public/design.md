# Design: pipeline-rewire-public (Step 4/5)

## KGI
backend Python コードが public スキーマの17テーブルを参照する。
`grep -rn "{TCG_SCHEMA}\." backend/app/ --include="*.py"` が17テーブル名にヒット = 0件。

| 基準 | 検証方法 |
|-----|---------|
| 17テーブルへのTCG_SCHEMA参照がゼロ | grep実行・CI確認 |
| 残存TCG_SCHEMA参照が全て正当 | コードレビュー |
| ruff lint通過 | CI確認 |

## 設計方針

### 変更アプローチ
- `{TCG_SCHEMA}.tablename` → `public.tablename` (全17テーブル)
- schema関数のデフォルト値を "public" に更新
- 不要インポートを削除

### 変更しない参照
- LOOKUP_TABLES動的参照（非移行テーブル）
- line_import_devicesのtcg_schemaカラム値（デバイス認証メタデータ）
- Redisキープレフィックス（後方互換）
- リビジョンハッシュ計算（後方互換）

## 外部事例

PostgreSQL best practice: 明示的なスキーマ修飾 `public.tablename` を使用することで
search_path設定に依存せず、移行後も安全に動作する。

## 影響範囲

- 全TCGパイプライン処理（抽出・解析・配信）
- マージ前提条件: PR #3625 + Step 2 + Step 3 完了

## ADR参照

対象ADR: 対象外（スキーマ移行はPRシリーズで管理、ADR未起案）

## 守り手

- ruff lint (CI)
- backend pytestスイート (CI)
