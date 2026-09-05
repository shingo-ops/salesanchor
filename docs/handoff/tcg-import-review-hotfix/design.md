---
branch: release/tcg-import-hotfix-imp39
date: 2026-09-05
card: IMP-39
---

# design: TCG LINE import ホットフィックス（IMP-39）

## KGI

`GET /tcg/line-import/history` および `POST /tcg/line-import` が 200 を返すこと。

| 基準 | 検証方法 |
|------|----------|
| /history が 200 | デプロイ後 `curl -s -o /dev/null -w "%{http_code}" GET /api/v1/tcg/line-import/history` → 200 |
| POST upload が 200 | TestClient でファイルアップロード → レスポンス 200 |
| 既存テスト全件 PASS | `pytest backend/tests/test_tcg_line_import.py` → 51 件 GREEN |

## 修正方針

### バグ 1: 固定パスは可変パスより前に定義する

FastAPI は登録順にルートマッチを試みる。
`/{import_job_id}` のような可変パスは任意の文字列にマッチするため、
**固定パス（`/history`, `/pending`, `/unresolved`）は必ず可変パス（`/{import_job_id}`）より前に定義する。**

```python
# CORRECT ORDER（変更後）
router.add_api_route("/tcg/line-import/pending",   ...)  # 固定 ← 先
router.add_api_route("/tcg/line-import/history",   ...)  # 固定 ← 先
router.add_api_route("/tcg/line-import/unresolved",...)  # 固定 ← 先
router.add_api_route("/tcg/line-import/{import_job_id}", ...)  # 可変 ← 後
```

**リグレッション防止**: `test_history_route_before_job_id_route` / `test_pending_route_before_job_id_route` がルーター順序を毎回検証する。

### バグ 2: asyncpg TIMESTAMPTZ には datetime オブジェクトを渡す

asyncpg は `TIMESTAMPTZ` カラムへの `str` 渡しを型エラーとして拒否する。
`_compute_window` の戻り値（`str | None`）は文字列比較用途のまま温存し、
INSERT 直前に `datetime.strptime` で変換する。

```python
ws_dt = datetime.strptime(effective_window_start, "%Y-%m-%d %H:%M:%S") if effective_window_start else None
we_dt = datetime.strptime(effective_window_end,   "%Y-%m-%d %H:%M:%S") if effective_window_end else None
# INSERT params に ws_dt / we_dt を渡す
```

**リグレッション防止**: `test_import_window_start_passed_as_datetime` が INSERT 時の型を毎回検証する。

## 影響範囲

| ファイル | 変更種別 | 影響 |
|----------|----------|------|
| `backend/app/routers/tcg_line_import.py` | ルート定義順序変更 + コメント追加 | /history /unresolved のみ。既存エンドポイント動作変更なし |
| `backend/app/services/tcg_line_import_svc.py` | INSERT 直前に datetime 変換追加 | `_compute_window` 戻り値型変更なし。文字列比較ロジック変更なし |
| `backend/tests/test_tcg_line_import.py` | テスト 3 件追加 | 51 件すべて GREEN |

## 戻し方

```bash
git revert HEAD  # 本 PR のコミットを revert
```

migration は含まない。戻しリスクなし。

## 外部事例

FastAPI 公式ドキュメント "Path Parameters" — 「パスが重なる場合、最初に宣言されたルートが優先される」と明記。
asyncpg 公式 — PostgreSQL 型マッピング: `TIMESTAMPTZ` → Python `datetime.datetime`（aware）。

## 守り手

- `test_history_route_before_job_id_route` — 順序リグレッション防止（毎 CI）
- `test_pending_route_before_job_id_route` — 同上
- `test_import_window_start_passed_as_datetime` — 型リグレッション防止（毎 CI）
