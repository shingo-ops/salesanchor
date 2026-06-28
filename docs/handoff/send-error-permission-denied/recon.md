# Recon: 送信エラー permission_denied 分類追加

base: origin/main @ 3df9015b  
branch: release/morimoto/send-error-permission-denied

## R1: subcode 2534044 の確定根拠

便D-2第1段（#2652）のデプロイ後、実機 lead_id=1047 で再送信したログ:

```
Meta Send API error for lead 1047: type=OAuthException code=10 subcode=2534044
  msg=(#10) アプリに人間エージェントタグのアクセス許可がありません。 trace=AfeU2AHy-Ky4KD-gUV2wkJ8
```

→ subcode 2534044 = HUMAN_AGENT タグの Meta App Review 未承認による権限エラー。  
  "outside allowed window" ではなく、24h〜7d のウィンドウ内で HUMAN_AGENT タグ必須時に発生。

## R2: leads.py の window_closed 分岐位置

`backend/app/routers/leads.py:1686-1691`（変更前）:
```python
if e.error_code == 10 and e.error_subcode in (2018278, 2534022):
    send_error_reason = "window_closed"
elif e.error_code in (4, 32, 613, 17):
    send_error_reason = "rate_limited"
else:
    send_error_reason = "generic"
```

## R3: InboxMessageThread.tsx の表示分岐位置

`frontend/src/pages/inbox/InboxMessageThread.tsx:495-499`（変更前）:
```tsx
{sendErrorReason === "window_closed"
  ? t("inbox.sendError.windowClosed")
  : sendErrorReason === "rate_limited"
    ? t("inbox.sendError.rateLimited")
    : t("inbox.sendError.generic")}
```

## R4: i18n 既存キー位置

`frontend/src/locales/ja.json:1087-1092` / `en.json:1087-1092`:
`inbox.sendError.{windowClosed,rateLimited,generic,codeSuffix}` の4キー確認済み。
`permissionDenied` を追加する。
