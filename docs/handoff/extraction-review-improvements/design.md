# Design: extraction-review-improvements

## 参照ADR
- ADR-158: 商品マッチング精度改善

## KGI
- _resolve_pid が非整数入力を受け付けなくなり、誤マッチが構造的に排除される
- `/super-admin/needs-review` ページが表示され、NEEDS_REVIEW アイテムの一覧が確認できる

## 変更1: _resolve_pid 整数制限

### 変更前
```python
def _resolve_pid(pid: str | None) -> str | None:
    if pid is None or pid == "" or pid == "-":
        return None
    validated = validate_product_id(pid, reference)
    if validated is not None:
        return validated
    mapped_id = product_code_to_id.get(pid)
    if mapped_id is not None:
        return validate_product_id(mapped_id, reference)
    return None
```

### 変更後
```python
def _resolve_pid(pid: str | None) -> str | None:
    if pid is None or pid == "":
        return None
    if not pid.isdigit():
        return None
    return validate_product_id(pid, reference)
```

- product_code_to_id 変数は rawcode_to_id.update() で使用中のため残置
- "-" は isdigit() で False になるので自動的に拒否される

## 変更2: NeedsReviewListPage

### API
- `GET /api/v1/tcg/analysis-results?status_tab=NEEDS_REVIEW&offset=N&limit=20`
- 既存 AnalysisResultItem 型をそのまま利用

### UIコンポーネント
- DataTable + onRowClick（行クリックで `/super-admin/inbound/:id/review` へ遷移）
- DataTable 組み込みページネーション（page/hasNextPage/onPageChange）
- useSuperAdmin フック（認証ガード）

### 追加ファイル
- `frontend/src/pages/super-admin/NeedsReviewListPage.tsx`
- `frontend/src/App.tsx` (ルート追加)
- `frontend/src/components/DesktopShell.tsx` (nav追加)
- `frontend/src/components/MobileShell.tsx` (nav追加)
- `frontend/src/locales/ja.json` (needsReview + nav.superAdminNeedsReview)
- `frontend/src/locales/en.json` (同上)

## KPI検証方法
- `npm run build` が通ること
- `ruff check` が通ること
- `-` や `M1L` が _resolve_pid に渡ったとき None が返ること（isdigit() = False）
- `/super-admin/needs-review` にアクセスしてテーブルが表示されること

## 弊害
- _resolve_pid の変更: 2026-09-23以前の旧形式（product_code文字列）は None になるが、これは仕様通り（誤マッチ排除）

## 外部事例
- N/A（内部リファクタリング）
