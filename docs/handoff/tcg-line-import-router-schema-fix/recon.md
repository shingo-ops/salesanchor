# TCG LINE Import Router スキーマ修飾修正 — Recon

作成日: 2026-09-05  
ブランチ: `release/tcg-line-import-router-schema-fix`  
担当: Hikky-dev

---

## 問題の発見

IMP-08 で `import_jobs` テーブルの実在確認をした際、
`backend/app/routers/tcg_line_import.py:156` と `:200` の 2 箇所に
スキーマ修飾なしの `FROM import_jobs` が存在することが判明。

同ファイルは IMP-05/PR #3285 でマージ済みのため、IMP-10 で独立 PR として修正する。

## 修飾漏れの全件調査（手順1）

### tcg_line_import.py の FROM/INTO/JOIN 一覧

```
backend/app/routers/tcg_line_import.py:156:            FROM import_jobs
backend/app/routers/tcg_line_import.py:200:            FROM import_jobs
```

両行とも `tenant_004.` 修飾なし。

### text() を使うのに TCG_SCHEMA / tenant_004 を含まないファイル（全件）

コマンド:
```
grep -rln 'text(' backend/app/routers/ backend/app/services/ backend/app/tasks/ \
  | xargs grep -Ln "TCG_SCHEMA|tenant_004"
```

TCG 関連ファイルのみ判定:

| ファイル | TCG 関連か | スキーマ修飾状況 |
|---------|-----------|--------------|
| `backend/app/routers/tcg_line_import.py` | ✅ TCG | ❌ 修飾漏れ 2 件（本カード対象） |
| `backend/app/routers/super_admin_tcg.py` | ✅ TCG | ✅ `public.tcg_series_master` / `public.tcg_type_master` で `public.` 修飾済み |

他のファイル（auth, discord, leads, orders 等）は TCG 無関係。

## TCG_SCHEMA 定数の在処

```
backend/app/services/tcg_line_import_svc.py:24:TCG_SCHEMA = "tenant_004"
```

router から `from app.services.tcg_line_import_svc import TCG_SCHEMA` で import 可能。

## 修正対象 SQL の引用

`list_import_history`（line 150-160）:
```python
text("""
    SELECT id, filename, ...
    FROM import_jobs        ← スキーマなし
    ORDER BY created_at DESC
""")
```

`get_latest_unresolved`（line 196-204）:
```python
text("""
    SELECT id, unresolved_count
    FROM import_jobs        ← スキーマなし
    ORDER BY created_at DESC
""")
```

## 既存テスト確認

`backend/tests/test_tcg_line_import.py` — 29 件（DB 不要、全 PASS）
→ router エンドポイント自体のテストはなし（サービス層のみ）
→ 本カードで `test_tcg_schema_qualification.py` を追加して静的検証
