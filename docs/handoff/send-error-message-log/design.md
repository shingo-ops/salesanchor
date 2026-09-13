# Design: 送信エラーログに Meta message 文追記

base: origin/main @ 1e4b9c78  
branch: release/morimoto/send-error-message-log  
recon: docs/handoff/send-error-message-log/recon.md  
ADR: ADR-110

## KGI / KPI

| 基準 | 検証方法 |
|---|---|
| 送信失敗ログに Meta message 原文が出る | `docker logs backend \| grep "msg="` で文言確認可 |
| PII 漏洩を最小化 | message を 150 文字で切り捨て |
| reason 振り分け・送信本体・正常系に影響なし | 36件テスト全 PASS |

## 変更一覧

### 変更1: `backend/app/routers/leads.py:1682-1683`

```python
# 変更前
logger.warning(
    "Meta Send API error for lead %s: type=%s code=%s subcode=%s trace=%s",
    lead_id, e.error_type, e.error_code, e.error_subcode, e.fbtrace_id,
)
# 変更後
logger.warning(
    "Meta Send API error for lead %s: type=%s code=%s subcode=%s msg=%s trace=%s",
    lead_id, e.error_type, e.error_code, e.error_subcode,
    (e.message or "")[:150], e.fbtrace_id,
)
```

**根拠**: `meta_graph.py:104` で `self.message = message`（Meta `error.message` 直値）。
PII注記（`meta_graph.py:85`）あり → 150文字上限でサニタイズ代替。

## 触らない範囲

- reason 振り分けロジック（subcode はまだ足さない）
- 送信本体・送信可否判定・既存 HTTP フィールド・audit_log・正常系

## 外部・過去事例の参照と我々への応用

Meta Graph API のエラーレスポンスは `error.message` フィールドに人間可読の説明文を含む（例: "This message is sent outside of allowed window."）。これをログに残すことで、subcode が未知の番号（例: 2534044）でも message 原文から枠切れ/権限/スパム等の要因をオペレーターが即判別できる。便D-1の目的はこの "message 原文の可視化" のみ（subcode の分類追加は便D-2で実施）。
