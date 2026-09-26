# recon: tcg-import-review-fix

調査日: 2026-09-05  
調査者: Hikky-dev (REVIEW-R2)

---

## 0. 調査起点の事象

2026-09-05 17:25〜17:50 の本番操作で resolve が機能しない報告。

---

## 1. 本番エラーログ（生出力・事実）

```
# タイムスタンプは jq で確認不可（INFO ログのみ）
GET  /api/v1/tcg/diagnostics/suppliers                        200 OK
POST /api/v1/tcg/line-import/65cf6b75-078e-471e-9e54-6fbf1f9725cb/resolve  200 OK  ← 1回目
GET  /api/v1/tcg/diagnostics/suppliers                        200 OK  ← 別 ReviewSection がマウント
GET  /api/v1/tcg/line-import/pending                          200 OK
POST /api/v1/tcg/line-import/65cf6b75-078e-471e-9e54-6fbf1f9725cb/resolve  404 Not Found  ← 2回目
```

- 422 は出ていない（create 操作は試行されていなかった）
- 404 の詳細 body はサーバーログに出ない（INFO レベルのみ）
- diagnostics/suppliers の二重 GET は ReviewSection が2インスタンス同時にマウントされた証拠

---

## 2. resolve ルーターの実装（事実）

`backend/app/routers/tcg_line_import.py:432-436`

```python
if body.display_name not in current_names:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"'{body.display_name}' は unresolved_names に含まれていません",
    )
```

→ 1回目の 200 OK で DB の unresolved_names から名前が除去済み。  
2回目は同じ名前が current_names にないため 404 が返った。

`import_jobs.unresolved_names` の UPDATE は存在する（:432-539 に実装済み）。  
1回目の resolve でコミット完了していた。**DB 更新自体は正常だった。**

---

## 3. commit の再解決設計（事実）

`backend/app/routers/tcg_line_import.py:598-612`

commit は `pending_messages` の各メッセージを「その時点の仕入元マスタ名」で  
`resolve_suppliers()` を用いて再解決する。`unresolved_names` は参照しない。

→ **（b）パターン（保存済み unresolved_names をそのまま信じる）ではない。**  
assign 操作で仕入元の name を display_name に書き換え済みであれば、  
commit 時の完全一致照合で正常に解決される。**commit ロジックは正しかった。**

---

## 4. SP0007 が "overlap" に書き換わった経緯（事実・本番操作記録）

- resolve action='assign' は対象仕入元の `name` を `display_name` に上書きする
- SP0007（本来の仕入元名）に対して `display_name="overlap"` を割り当て操作した結果、  
  tcg_suppliers.name が "overlap" に書き換わった
- その後手作業で元の name に復旧した
- これは仕様どおりの動作。assign 操作の副作用（name 書き換え）の説明が不十分だった

---

## 5. フロントエンドの問題（事実）

### 5-1. 二重 ReviewSection マウント

`frontend/src/pages/super-admin/TcgLineImportPage.tsx`

- アップロード後 `result.review_status === "pending_review"` で ReviewSection #1 が表示（:375付近）
- 同時に pending_jobs 一覧にも同じ job_id が表示され「確認する」ボタンで ReviewSection #2 が開ける
- 同一 job_id の ReviewSection が2インスタンス同時マウント可能 → 同じ名前を2回 resolve → 2回目 404

### 5-2. resolve 成功後に状態がローカル Set 止まり

`frontend/src/features/tcg-import-review/ReviewSection.tsx:92`

```tsx
setResolved((prev) => new Set([...prev, displayName]));
```

ページリロードで `resolved` Set がリセット → DB では解決済みでも UI では未解決表示に戻る。  
また `unresolvedNames` prop はマウント時のスナップショットで更新されない。

### 5-3. create アクションに supplier_code がない（仕様の食い違い）

`frontend/src/features/tcg-import-review/ReviewSection.tsx:111-114`

```tsx
await api.post(`/tcg/line-import/${importJobId}/resolve`, {
  display_name: displayName,
  action: "create",
  // supplier_code なし
});
```

バックエンドの `ResolveRequest.supplier_code: str`（必須）→ Pydantic が 422 を返す。  
今回の操作ログに 422 がなかった理由: create ボタンは押されていなかった。

---

## 6. 変更ファイル一覧

| ファイル | 変更種別 |
|---|---|
| `backend/app/routers/tcg_line_import.py` | supplier_code Optional化 / assign必須チェック / 冪等化 |
| `backend/tests/test_tcg_line_import.py` | 新規テスト3件追加 |
| `frontend/src/features/tcg-import-review/ReviewSection.tsx` | DB再取得 / currentUnresolvedNames state |
| `frontend/src/pages/super-admin/TcgLineImportPage.tsx` | 二重マウント防止フィルタ |
| `docs/handoff/tcg-import-review-fix/recon.md` | 本ファイル |
| `docs/handoff/tcg-import-review-fix/design.md` | 設計ファイル |
