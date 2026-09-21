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

対象ADR: ADR-036 (tenant-schema-integrity) — スキーマ境界の保全原則に基づく移行

## 維持の仕組み

- ruff lint (CI): `{TCG_SCHEMA}.tablename` 形式の新規混入を検知
- backend pytestスイート (CI): 既存テストが public スキーマ参照で通過することを確認

## 外部・過去事例の参照と我々への応用

PostgreSQL の `search_path` 設定に依存しない明示的なスキーマ修飾 (`public.tablename`) は
PostgreSQLコミュニティの標準プラクティス。`SET search_path TO public` が設定されている場合でも、
明示修飾することで将来のsearch_path変更に対して堅牢になる。

本プロジェクトの前例: ADR-036（tenant-schema-integrity）でテナントスキーマの境界を
明示的に管理する方針が定められており、その延長として public スキーマへの移行も
明示的な修飾を維持する。
