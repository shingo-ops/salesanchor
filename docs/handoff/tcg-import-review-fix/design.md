# design: tcg-import-review-fix

設計日: 2026-09-05  
担当: Hikky-dev (REVIEW-R2)  
対象ADR: ADR-154  
recon: docs/handoff/tcg-import-review-fix/recon.md

---

## KGI

resolve 操作が確実に成功し、未解決リストがリロード後も正しく表示される。

| 基準 | 検証方法 |
|---|---|
| action="create" で supplier_code なし → 422 でなく 200 | テスト: `test_resolve_request_create_no_supplier_code_is_valid` |
| action="assign" で supplier_code なし → 400 | テスト: `test_resolve_assign_without_supplier_code_raises_400` |
| resolve 2回目（既解決）→ 404 でなく 200 + 現状維持 | テスト: `test_resolve_already_resolved_is_idempotent` |
| 同一 job_id の ReviewSection が2つ同時に存在しない | コード: TcgLineImportPage の filter |
| resolve 成功後にリロードしても解決済み状態が保たれる | コード: refreshUnresolved() → currentUnresolvedNames |

---

## 修正1: supplier_code を Optional 化

### 変更前

```python
# backend/app/routers/tcg_line_import.py:105
supplier_code: str  # 必須フィールド
```

### 変更後

```python
supplier_code: Optional[str] = None  # create 時は不要
```

```python
if body.action == "assign":
    if not body.supplier_code:
        raise HTTPException(status_code=400, detail="action='assign' のとき supplier_code は必須です")
```

**根拠:** create アクションでは code を採番するため supplier_code は不要。  
フロントエンドが送らないのは正しい動作。バックエンドが必須として弾いていたのが誤り。

**影響範囲:** `POST /tcg/line-import/{id}/resolve` のみ。assign 動作は変わらない。

**弊害:** なし。assign で supplier_code を省略するとより明確な 400 が返るようになり、デバッグが容易になる。

**戻し方:** `Optional[str] = None` → `str` に戻す。

---

## 修正2: 二重解決を冪等に

### 変更前

```python
if body.display_name not in current_names:
    raise HTTPException(status_code=404, ...)
```

### 変更後

```python
if body.display_name not in current_names:
    # 既解決（二重クリック・二重 mount 等）: 冪等に現状を返す
    return ResolveResponse(success=True, remaining_unresolved=current_names)
```

**根拠:** resolve の事後状態は「display_name が unresolved_names にない」こと。  
既にその状態なら 404 ではなく成功を返すべき（HTTP の冪等性原則）。  
DB への不要な commit も発生しない。

**影響範囲:** 二重クリック・二重マウント時のエラー表示が消える。

**弊害:** 「削除済み job_id」と「解決済み name」の両方が 404 ではなく別の応答で区別される。  
job_id 不在は引き続き 404（L421）で返るため区別は維持される。

---

## 修正3: TcgLineImportPage 二重マウント防止

### 変更前

アップロード後に result と pending_jobs の両方に同じ job_id が表示可能。

### 変更後

```tsx
pendingJobs.filter(
  (job) => !(result?.review_status === "pending_review" && result.import_job_id === job.id)
)
```

**根拠:** アップロード直後は result セクションに ReviewSection が表示される。  
同じ job_id の ReviewSection が pending 一覧にも開かれると、2インスタンスが  
同じ DB 行に対して並行して resolve を呼ぶ。

**弊害:** アップロード直後、pending 一覧から同じジョブの「確認する」ボタンが  
一時的に非表示になる。result を閉じる（commit 完了）と再び表示される。

---

## 修正4: resolve 成功後の DB 再取得

### 変更前

resolve 成功 → ローカル `resolved` Set にのみ追記。  
ページリロードで状態消滅。`unresolvedNames` prop はマウント時固定。

### 変更後

```tsx
const [currentUnresolvedNames, setCurrentUnresolvedNames] = useState<string[]>(unresolvedNames);

const refreshUnresolved = useCallback(async () => {
  const data = await api.get<JobDetail>(`/tcg/line-import/${importJobId}`);
  setCurrentUnresolvedNames(data.unresolved_names);
}, [importJobId]);

// handleAssign / handleCreate 成功後:
setResolved((prev) => new Set([...prev, displayName]));
await refreshUnresolved();
```

**根拠:** DB が正規状態の持ち主。UI の `resolved` Set はオプティミスティック表示用に残すが、  
DB 再取得後は `currentUnresolvedNames` が正となる。  
`allResolved = currentUnresolvedNames.length === 0` により「抽出を開始」ボタンが  
DB 状態と一致して有効化される。

**弊害:** resolve 成功後に GET が1回追加発生（軽微）。  
失敗時は catch でスキップし、ローカル Set で動作継続する。

---

## 外部・過去事例の参照と我々への応用

該当なし：本修正は HTTP 冪等性（RFC 7231）と React state の単一ソース・オブ・トゥルース原則に基づくバグ修正。外部事例の参照は不要と判断（422/404の仕様上の誤りと二重マウントの設計上の誤りの修正のみ）。

---

## 維持の仕組み

守り手: `backend/tests/test_tcg_line_import.py`（create/assign バリデーション + 冪等性を常時 CI 検証）  
守り手: `frontend/src/pages/super-admin/TcgLineImportPage.tsx`（二重マウントのフィルタを集約・ReviewSection 側に漏れない設計）
