# design: fix-supplier-migration-wiring

## recon 参照

`docs/handoff/fix-supplier-migration-wiring/recon.md`

## 関連 ADR

- `docs/adr/ADR-1001-deprecate-tcg-products-unify-to-public.md`

## 変更内容

### 修正1: line_import_admin.py

`from app.tcg_config import TCG_SCHEMA` を削除し、ローカル定義に変更。

変更前:
```python
from app.tcg_config import TCG_SCHEMA  # noqa: E402
```

変更後:
```python
# Step 4/5: TCG テーブルは public スキーマに移行済み。
# テスト互換性のため TCG_SCHEMA 属性を維持する（monkeypatch.setattr 対象）。
TCG_SCHEMA = "public"
```

### 修正2: tcg_config.py

デフォルト値とバリデーション正規表現を更新。

変更前:
```python
_RAW: str = os.getenv("TCG_SCHEMA", "tenant_004")
_VALID = re.compile(r"^tenant_\d{3}$")
```

変更後:
```python
_RAW: str = os.getenv("TCG_SCHEMA", "public")
_VALID = re.compile(r"^(tenant_\d{3}|public)$")
```

## KGI/KPI

| 基準 | 検証方法 |
|------|---------|
| `line_import_admin.py` に `from app.tcg_config import TCG_SCHEMA` が存在しない | `grep -n "from app.tcg_config import TCG_SCHEMA" backend/app/line_import_admin.py` が 0 件 |
| 環境変数未設定時のデフォルト値が `public` | `python -c "from app.tcg_config import TCG_SCHEMA; print(TCG_SCHEMA)"` が `public` を出力 |
| `TCG_SCHEMA=public` 設定時にエラーが出ない | `TCG_SCHEMA=public python -c "from app.tcg_config import TCG_SCHEMA"` が exit 0 |

## 弊害・リスク

- `tcg_config.py` を import している他ファイル（9ファイル）は、デフォルト値が安全側（`public`）に変わるのみ。既存動作を壊さない。
- 旧 `tenant_004` スキーマへの接続が必要な場合は環境変数 `TCG_SCHEMA=tenant_004` で上書き可能（正規表現も許容）。

## 外部事例

前回の移行済みファイルのパターン（PR #3663 で確立済み）を踏襲。
