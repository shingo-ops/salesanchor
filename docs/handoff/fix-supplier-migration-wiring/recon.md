# recon: fix-supplier-migration-wiring

## 目的

public スキーマ移行後（PR #3663）の残存バグを修正する。
backend/app/line_import_admin.py が依然 `from app.tcg_config import TCG_SCHEMA` を import しており、
backend/app/tcg_config.py のデフォルト値が旧 tenant_004 のままになっている。

## 現在地

### 修正対象ファイル

- backend/app/line_import_admin.py:23 — `from app.tcg_config import TCG_SCHEMA  # noqa: E402`
  → 他の移行済みファイルと異なりローカル定義になっていない
- backend/app/tcg_config.py:20 — `_RAW: str = os.getenv("TCG_SCHEMA", "tenant_004")`
  → デフォルト値が旧スキーマのまま
- backend/app/tcg_config.py:21 — `_VALID = re.compile(r"^tenant_\d{3}$")`
  → "public" を許容しないため環境変数に "public" を設定するとエラーになる

### import している他ファイル（今回は変更しない）

```
backend/app/routers/tcg_product_import.py:42
backend/app/tasks/tcg_mirror.py:33
backend/app/services/tcg_product_import_svc.py:34
backend/app/services/tcg_product_master_svc.py:25
backend/app/services/tcg_product_detail_svc.py:13
backend/app/services/line_import_devices.py:12
backend/app/services/tcg_product_roundtrip_svc.py:16
backend/app/services/tcg_work_comparison_svc.py:20
backend/scripts/check_keyword_quality.py:29
```

これらは引き続き backend/app/tcg_config.py を import するが、デフォルト値が public になることで安全になる。

### SQL 中の tenant_004 ハードコード調査結果

- backend/app/routers/tcg_product_master.py:306-313 — ドキュメントコメント内のサンプルSQL（実行されない）
- backend/app/services/tcg_distribution_svc.py:859 — tenant_id=4（Discord通知のテナントID整数値・スキーマ文字列ではない）
- その他は全てコメント・docstring 内（実行コードに tenant_004 の SQL ハードコードなし）

## 関連 ADR

- docs/adr/ADR-1001-deprecate-tcg-products-unify-to-public.md — TCG テーブル public 移行決定
- docs/adr/ADR-072-tenant-schema-prefix-enforcement.md — スキーマ修飾強制

## 前提 PR

- PR #3663 (release/line-import-schema-rewire) — line_import_admin.py 以外のファイルを移行済み
