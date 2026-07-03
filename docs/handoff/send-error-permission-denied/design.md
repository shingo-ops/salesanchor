# Design: 送信エラー permission_denied 分類追加

base: origin/main @ 3df9015b  
branch: release/morimoto/send-error-permission-denied  
recon: docs/handoff/send-error-permission-denied/recon.md  
ADR: ADR-110

## KGI / KPI

| 基準 | 検証方法 |
|---|---|
| subcode 2534044 のとき「24時間を過ぎたため…」と表示される | lead 1047 で再送信 → UI 確認 |
| window_closed / rate_limited / generic は従来通り | 既存 36件テスト PASS |
| migrationなし・送信本体変更なし | diff --stat で確認 |

## 変更一覧

### 変更1: `backend/app/routers/leads.py:1686-1691`

```python
# 変更前
if e.error_code == 10 and e.error_subcode in (2018278, 2534022):
    send_error_reason = "window_closed"
elif e.error_code in (4, 32, 613, 17):
    send_error_reason = "rate_limited"
else:
    send_error_reason = "generic"

# 変更後
if e.error_code == 10 and e.error_subcode in (2018278, 2534022):
    send_error_reason = "window_closed"
elif e.error_code == 10 and e.error_subcode == 2534044:
    send_error_reason = "permission_denied"
elif e.error_code in (4, 32, 613, 17):
    send_error_reason = "rate_limited"
else:
    send_error_reason = "generic"
```

### 変更2: `frontend/src/pages/inbox/InboxMessageThread.tsx:495-499`

```tsx
# 変更後（permission_denied 分岐を window_closed の次に追加）
{sendErrorReason === "window_closed"
  ? t("inbox.sendError.windowClosed")
  : sendErrorReason === "permission_denied"
    ? t("inbox.sendError.permissionDenied")
    : sendErrorReason === "rate_limited"
      ? t("inbox.sendError.rateLimited")
      : t("inbox.sendError.generic")}
```

### 変更3: i18n キー

| キー | ja | en |
|---|---|---|
| `permissionDenied` | 24時間を過ぎたため送信できません。Instagram/Messengerから直接返信してください | More than 24 hours have passed, so this message cannot be sent. Please reply directly from Instagram / Messenger. |

## 触らない範囲

- window_closed (2018278/2534022) / rate_limited / generic の既存分岐
- 便D-2第1段で追加した message ログ追記
- 送信本体・送信前ブロック・audit_log・正常系

## 外部・過去事例の参照と我々への応用

Meta HUMAN_AGENT タグは 2019年以降の24h messaging window 緩和策として導入（Meta for Developers ポリシー）。App Review を経ないと code=10/subcode=2534044 が返る。この subcode の分類は実機ログ（便D-2第1段デプロイ後の msg 原文確認）による実証ベースであり、ドキュメント値ではなく観測値から確定した。
