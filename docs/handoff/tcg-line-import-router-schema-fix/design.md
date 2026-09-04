# TCG LINE Import Router スキーマ修飾修正 — 設計書

作成日: 2026-09-05  
ADR 参照: ADR-072, ADR-154  
recon 参照: `docs/handoff/tcg-line-import-router-schema-fix/recon.md`

---

## KGI

**`backend/app/routers/tcg_line_import.py` の全 SQL が `tenant_004.` スキーマ修飾済みになり、`backend/tests/test_tcg_schema_qualification.py` が GREEN になること**

受け入れ基準（PO が画面・ログで一義に判定できる粒度）:
| 基準 | 検証方法 |
|------|---------|
| `FROM tenant_004.import_jobs` が router に 2 箇所存在する | `grep -n "FROM.*import_jobs" backend/app/routers/tcg_line_import.py` |
| `FROM import_jobs`（修飾なし）が router に 0 件 | 同 grep で `tenant_004.` を含まない行ゼロ |
| pytest test_tcg_schema_qualification.py が 2 件 PASS | `python3 -m pytest tests/test_tcg_schema_qualification.py -v` |
| ruff check が clean | `ruff check backend/app/routers/tcg_line_import.py` → All checks passed |

---

## 変更ファイル一覧

| ファイル | 変更内容 | 触らない範囲 |
|---------|---------|-----------|
| `backend/app/routers/tcg_line_import.py` | import に `TCG_SCHEMA` 追加、2 箇所の SQL を f-string + `{TCG_SCHEMA}.` 修飾 | ビジネスロジック・Pydantic schema・エンドポイント定義 |
| `backend/tests/test_tcg_schema_qualification.py` | 新規（静的 SQL スキーマ修飾テスト） | — |
| `docs/handoff/tcg-line-import-router-schema-fix/recon.md` | 新規 | — |
| `docs/handoff/tcg-line-import-router-schema-fix/design.md` | 本ファイル | — |

---

## 設計詳細

### 修正箇所（差分）

```python
# Before（list_import_history）:
text("""
    SELECT ... FROM import_jobs ...
""")

# After:
text(f"""
    SELECT ... FROM {TCG_SCHEMA}.import_jobs ...
""")
```

同様に `get_latest_unresolved` も 1 箇所。

### TCG_SCHEMA import 追加

```python
# Before:
from app.services.tcg_line_import_svc import import_line_export

# After:
from app.services.tcg_line_import_svc import TCG_SCHEMA, import_line_export
```

### 再発防止テストの方式

**ソースを正規表現で読む方式**を採用。

理由:
- SQL は DB 接続なしに静的検証できる
- 既存の 29 件テストが DB レスなので同じ実行環境で動く
- async 関数を呼び出して SQL を捕まえる方式は DB セッションモックが複雑で壊れやすい

テスト `test_all_tcg_sql_are_schema_qualified`:
- `text(...)` 引数を正規表現で抽出
- 対象テーブル名 (`import_jobs` 等) が登場する箇所に `tenant_004.` or `{TCG_SCHEMA}.` が前置されているか確認
- 未修飾の場合 FAIL

テスト `test_no_literal_tcg_schema_placeholder`:
- f-string でない `text()` に `{TCG_SCHEMA}` が残っていないか確認（IMP-05 の反省）

RED → GREEN 確認済み:
- 修正前: `test_all_tcg_sql_are_schema_qualified` FAILED（import_jobs 未修飾）
- 修正後: 2 件 PASSED

---

## 弊害・リスク

| リスク | 評価 | 対策 |
|-------|------|------|
| super_admin エンドポイントのため本番影響は小（super_admin のみアクセス可） | 低 | require_super_admin で保護済み |
| f-string 化による既存挙動変化 | なし（文字列に `{` が含まれないため補間以外の副作用なし） | ruff check PASS + 29 件テスト PASS で確認 |

---

## 戻し方

```bash
git revert <merge-commit>
```

migration なし・DB 変更なし。

---

## 外部・過去事例の参照と我々への応用

- IMP-05（PR #3285）で同種バグを 6 箇所修正済み（サービス層）。ルーター層が取り残された教訓。
- 再発防止テスト (`backend/tests/test_tcg_schema_qualification.py`) を追加し、IMP-09 マージ後に tcg_extraction.py 等を追記する拡張ポイントを用意。

## 維持の仕組み

守り手: backend/tests/test_tcg_schema_qualification.py  
（CI pytest で毎 PR 実行。スキーマ未修飾 SQL が混入したら自動 FAIL）
