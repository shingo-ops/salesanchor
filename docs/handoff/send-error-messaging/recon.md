# Recon: 送信エラー表記の改善＋ログ永続化

base: origin/main @ 7685902b  
FRESH-RUN: 2026-06-27T23:00:28Z

---

## R1 送信エラーハンドラの出どころ

### バックエンド: `backend/app/routers/leads.py:1679-1700`

```python
except MetaGraphAPIError as e:
    logger.warning("Meta Send API error for lead %s: %s", lead_id, e.error_type)
    raise HTTPException(
        status_code=502,
        detail={
            "detail": "Meta Send API がエラーを返しました",
            "error_code": e.error_code,   # ← 含まれる
            "error_type": e.error_type,    # ← 含まれる
        },
    )
```

`error_subcode` / `fbtrace_id` は audit_log テーブルにのみ入る（HTTP レスポンスには含まない）。

### フロント: `frontend/src/lib/api.ts:99-104`

```ts
const detail = body?.detail;  // dict: { detail, error_code, error_type }
const message = typeof detail === "string"
  ? detail
  : detail?.detail || `HTTP ${res.status}`;  // → "Meta Send API がエラーを返しました"
```

`error_code` / `error_type` は `ApiError.responseDetail` に保持されているが未使用。

### フロント表示: `frontend/src/pages/inbox/InboxMessageThread.tsx:491-494`（変更前）

```tsx
Send error: {sendError}  // ← ハードコード英語・i18n未適用
```

---

## R2 Meta から取得可能なエラーフィールド

`backend/app/services/meta_graph.py:220-243` のパース処理:

| フィールド | 保持 | HTTP レスポンス | audit_log |
|---|---|---|---|
| `error.type` | ✅ | ✅ | ✅ |
| `error.code` | ✅ | ✅ | ✅ |
| `error.error_subcode` | ✅ | ❌ | ✅ |
| `fbtrace_id` | ✅ | ❌ | ✅ |

既知分類コード: `{4, 32, 613, 17}` → `MetaGraphRateLimitError`（分類済み）  
subcode 意味ベース分類（#2018278/#2534022 = outside window）: **新規実装が必要** → 本PRで追加。

---

## R3 ログ永続化

`docker-compose.yml:130-133`（backend）:

```yaml
logging:
  driver: json-file
  options:
    max-size: "20m"
    max-file: "5"
```

- ホスト `/var/lib/docker/containers/<id>/*.log` に保存（コンテナ再起動では消えない）
- `docker-compose down` / コンテナ削除で消える
- 変更前のログ: `error_type` のみ。`error_code` / `error_subcode` / `fbtrace_id` は出ていない

---

## R4 messaging window 判定材料

`backend/app/services/messaging_window.py`:
- `WindowState`: NO_INBOUND / WITHIN_24H / WITHIN_HUMAN_AGENT / EXPIRED
- `compute_state(last_inbound_at)` → leads.py:1556-1569 で送信前判定済み
- EXPIRED → 400「メッセージウィンドウを超過しています（受信から 7 日以上経過）」
- **WITHIN_HUMAN_AGENT 状態で Meta が失敗した場合**（HUMAN_AGENT TAG 未承認等）は failover でエラー。subcode 分類は本PRで追加。
