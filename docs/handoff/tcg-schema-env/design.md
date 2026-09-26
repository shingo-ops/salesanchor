# design: TCG_SCHEMA 環境変数化（TENANT-01）

## 概要

TCG システム全体で 12 箇所にハードコードされていた `TCG_SCHEMA = "tenant_004"` を、
`backend/app/tcg_config.py` という Single Source of Truth に集約し、
環境変数 `TCG_SCHEMA` で上書き可能にする。

## ADR 参照

| ADR | 関連 |
|-----|------|
| ADR-072 | テナントコンテキスト Hybrid 戦略（スキーマ修飾 OR reset_tenant_context） |
| ADR-131 | `clear_tenant_context()` による get_db finally クリア |

TCG_SCHEMA 環境変数化に特化した ADR は未存在。本 PR 規模（リファクタ・動作変更なし）で新規 ADR 不要と判断。

## 設計方針

### Why 環境変数化するか

- 将来的に TCG テナントが `tenant_004` 以外に移行した場合、コード変更なしに切り替えられる
- コンテナ起動時の検証（regex: `^tenant_\d{3}$`）でインジェクションを水際防止
- 12 ファイルへの分散定義を 1 ファイルに集約し、保守コストを削減

### tcg_config.py の設計

```python
_RAW = os.getenv("TCG_SCHEMA", "tenant_004")
_VALID = re.compile(r"^tenant_\d{3}$")

if not _VALID.match(_RAW):
    raise RuntimeError(...)   # コンテナ起動時に即クラッシュ

TCG_SCHEMA: str = _RAW
```

- `tenant_\d{3}$` のみ許可：任意文字列を SQL に埋め込むインジェクションリスクを排除
- モジュールロード時に検証するため、不正値でコンテナが起動しない（早期検出）
- デフォルト `tenant_004`：環境変数未設定でも現行動作を維持

### コンテナへの伝達経路

| 起動方式 | 設定箇所 |
|---------|---------|
| `docker compose up` (開発・CI) | `docker-compose.yml` の `environment` セクション |
| `blue-green-cutover.sh` (本番) | `docker run --env TCG_SCHEMA=...` |
| `celery-worker` / `celery-beat` | `docker-compose.yml` の各サービス `environment` |

全経路で `${TCG_SCHEMA:-tenant_004}` 形式を採用し、未設定時のデフォルトを保証。

## 変更ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `backend/app/tcg_config.py` | **新規** — TCG_SCHEMA の SSOT |
| `backend/app/routers/tcg_line_import.py` | 定義削除 → `from app.tcg_config import TCG_SCHEMA` |
| `backend/app/services/tcg_analysis_review_svc.py` | 同上 |
| `backend/app/services/tcg_analyzer_svc.py` | 同上 |
| `backend/app/services/tcg_diagnostics_svc.py` | 同上 |
| `backend/app/services/tcg_distribution_svc.py` | 同上 |
| `backend/app/services/tcg_line_import_svc.py` | 同上 |
| `backend/app/services/tcg_parallel_report_svc.py` | 同上 |
| `backend/app/services/tcg_product_master_svc.py` | 同上 |
| `backend/app/services/tcg_supplier_quality_svc.py` | 同上 |
| `backend/app/tasks/tcg_extraction.py` | 同上 |
| `backend/app/tasks/tcg_mirror.py` | 同上 |
| `backend/app/tasks/tcg_import_discard.py` | 同上 |
| `docker-compose.yml` | backend/celery-worker/celery-beat に `TCG_SCHEMA` 追加 |
| `scripts/blue-green-cutover.sh` | `docker run --env TCG_SCHEMA=...` 追加 |
| `backend/tests/test_tcg_config.py` | **新規** — tcg_config ユニットテスト |
| `backend/tests/test_tcg_gemini_extraction.py` | `_TCG_SCHEMA` 動的利用に更新 |
| `backend/tests/test_tcg_line_import.py` | SQL アサーションを動的スキーマ参照に更新 |

## KGI / KPI

| 基準 | 検証方法 |
|------|---------|
| `TCG_SCHEMA = "tenant_004"` のハードコードが backend/ から消える | `git grep 'TCG_SCHEMA = "tenant_004"' backend/` → 0 件 |
| TCG_SCHEMA 未設定で tenant_004 として動作する | `test_tcg_config_default_is_tenant_004` PASS |
| TCG_SCHEMA=tenant_006 で SQL に tenant_006. が入る | `test_tcg_config_custom_schema` + monkeypatch テスト PASS |
| 不正値でコンテナが起動失敗する | `test_tcg_config_invalid_value_raises` 9 パターン PASS |
| 既存テスト全件 PASS | `pytest backend/tests/ -v` 全件グリーン |

## 外部・過去事例の参照と我々への応用

**IMP-29（blue-green-cutover.sh 導入）の教訓**:  
`docker-compose.yml` だけを更新しても本番コンテナに環境変数は渡らない。
blue-green-cutover.sh の `docker run` にも必ず追加する必要がある（本 PR で対応済み）。

**ADR-072 の SQL インジェクション対策**:  
TCG の SQL はスキーマ名を f-string で直接埋め込む設計（`f"SELECT ... FROM {TCG_SCHEMA}.tcg_suppliers"`）。
任意文字列を受け入れると SQL インジェクションになるため、
`^tenant_\d{3}$` の regex 制約を tcg_config.py のモジュールロード時に強制する。

## 維持の仕組み

- **CI による静的テスト**: `test_tcg_schema_qualification.py` がスキーマ未修飾 SQL を検出
- **コンテナ起動時バリデーション**: 不正な `TCG_SCHEMA` 値ではコンテナが起動しない（RuntimeError）
- **`git grep` チェック**: PR 作成前に `git grep 'TCG_SCHEMA = "tenant_004"' backend/` で残留がないことを確認する運用

## 弊害・リスク

| リスク | 対策 |
|-------|------|
| 環境変数未設定でデフォルト動作が変わる | デフォルト `tenant_004` で現行維持 |
| 不正値でコンテナが落ちる | regex バリデーション + 起動時クラッシュで早期検出 |
| celery-worker/beat に渡し忘れ | docker-compose.yml の全サービスに追加済み |
| blue-green 経路に渡し忘れ | cutover.sh の `docker run` に追加済み |

## 戻し方

1. `backend/app/tcg_config.py` を削除
2. 各ファイルの `from app.tcg_config import TCG_SCHEMA` を `TCG_SCHEMA = "tenant_004"` に戻す
3. `docker-compose.yml` と `scripts/blue-green-cutover.sh` から `TCG_SCHEMA` 行を削除
