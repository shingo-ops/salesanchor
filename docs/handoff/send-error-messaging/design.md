# Design: 送信エラー表記の改善＋ログ追記

base: origin/main @ 7685902b  
branch: release/morimoto/send-error-messaging  
recon: docs/handoff/send-error-messaging/recon.md  
ADR: ADR-110

---

## KGI / KPI

| 基準 | 検証方法 |
|---|---|
| 送信エラー時にユーザーが原因を日本語/英語で確認できる | 画面で「送信できませんでした」「時間枠を過ぎています」等が表示される |
| ログに error_code / error_subcode / fbtrace_id が出る | `docker compose logs backend \| grep "type=.*code=.*subcode="` で確認 |
| 送信正常系・送信可否ロジックに影響なし | 36件の既存テストが全PASS |

---

## 変更一覧

### 変更1: `backend/app/routers/leads.py`

**ログ追記** (L1681):
```python
# 変更前
logger.warning("Meta Send API error for lead %s: %s", lead_id, e.error_type)
# 変更後
logger.warning(
    "Meta Send API error for lead %s: type=%s code=%s subcode=%s trace=%s",
    lead_id, e.error_type, e.error_code, e.error_subcode, e.fbtrace_id,
)
```

**reason 振り分け** (MetaGraphAPIError handler):
```python
if e.error_code == 10 and e.error_subcode in (2018278, 2534022):
    send_error_reason = "window_closed"
elif e.error_code in (4, 32, 613, 17):
    send_error_reason = "rate_limited"
else:
    send_error_reason = "generic"
```

**reason を HTTP レスポンスに追加**:
```python
detail={
    "detail": "Meta Send API がエラーを返しました",
    "error_code": e.error_code,   # 既存・不変
    "error_type": e.error_type,   # 既存・不変
    "reason": send_error_reason,  # 追加
}
```

**MetaGraphRateLimitError にも reason を追加** (L1658):
```python
rate_detail: dict = {"message": "...", "reason": "rate_limited"}
```

---

### 変更2: `frontend/src/pages/inbox/useInboxState.ts`

- interface: `sendErrorReason: string; sendErrorCode: number | null;` 追加
- state: `useState("")` / `useState<number | null>(null)` 追加
- selectLead / submitSend 開始時にリセット
- catch ブロック: `e.responseDetail` から `reason` / `error_code` を取得

### 変更3: `frontend/src/pages/inbox/InboxPage.tsx`

- `sendErrorReason={state.sendErrorReason}` / `sendErrorCode={state.sendErrorCode}` を InboxMessageThread へ渡す

### 変更4: `frontend/src/pages/inbox/InboxMessageThread.tsx`

- props: `sendErrorReason: string; sendErrorCode: number | null;` 追加
- 表示:
```tsx
{sendErrorReason === "window_closed"
  ? t("inbox.sendError.windowClosed")
  : sendErrorReason === "rate_limited"
    ? t("inbox.sendError.rateLimited")
    : t("inbox.sendError.generic")}
{sendErrorCode != null && t("inbox.sendError.codeSuffix", { code: sendErrorCode })}
```

### 変更5: `frontend/src/locales/ja.json` / `en.json`

新規キー（`inbox.sendError.*`）:

| キー | ja | en |
|---|---|---|
| `windowClosed` | 送信できる時間枠を過ぎています（相手からの受信が必要です） | The messaging window has closed (a reply from the recipient is required). |
| `rateLimited` | 送信が一時的に制限されています。時間をおいて再試行してください | Sending is temporarily limited. Please try again later. |
| `generic` | 送信できませんでした | Failed to send the message. |
| `codeSuffix` | （コード: {{code}}） |  (code: {{code}}) |

---

## 確定エラー番号表（window_closed 分類根拠）

| code | subcode | Meta 意味 | reason |
|---|---|---|---|
| 10 | 2018278 | outside 24h messaging window | `window_closed` |
| 10 | 2534022 | outside 24h messaging window (IG) | `window_closed` |
| 4, 32, 613, 17 | — | rate limit | `rate_limited` |
| その他 | — | — | `generic` |

MetaGraphRateLimitError（code 4/32/613/17）は別ハンドラで 429 を返す。`except MetaGraphAPIError` の `rate_limited` 分岐は code だけで判定できるケースのフォールバック。

---

## 触らなかった範囲

- 送信可否の判定（`messaging_window.compute_state`・`can_send_at_all`）
- 送信本体・成功系・画像送信
- audit_log への書き込み
- 既存 HTTP フィールド（`detail` / `error_code` / `error_type`）の破壊的変更なし

---

## 外部・過去事例の参照と我々への応用

Meta Graph API error codes: https://developers.facebook.com/docs/graph-api/guides/error-handling  
subcode 2018278 / 2534022 = "Message sent outside of allowed window" のドキュメント既知値。

Meta 公式ドキュメントでは error code 10 + subcode 2018278/2534022 を「24時間メッセージングウィンドウ外」と定義しており、エンドユーザーに「相手からのメッセージが必要」と案内するのが標準的対応（例: ManyChat・Chatfuel 等の SMS/Messenger ボット製品の実装例に倣う）。本実装もこの方針を採用。
