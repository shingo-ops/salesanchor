# Recon: 送信エラーログに Meta message 文追記

base: origin/main @ 1e4b9c78  
branch: release/morimoto/send-error-message-log

## R1: MetaGraphAPIError.message の存在確認

`backend/app/services/meta_graph.py:85-104`:
```python
# L85 コメント
message: Meta `error.message`（PII を含み得るのでログ前に sanitize すること）
# L91-99 __init__
def __init__(self, message: str, ..., fbtrace_id: Optional[str] = None):
    super().__init__(message)
    ...
    self.message = message   # L104
```

`backend/app/services/meta_graph.py:232`:
```python
message = err.get("message") or "Meta Graph API error (no message)"
```

→ `e.message` は常に str（fallback付き）。PII注記あり → 150文字切り捨てで緩和。

## R2: 変更対象行

`backend/app/routers/leads.py:1682-1683`（before）:
```
"Meta Send API error for lead %s: type=%s code=%s subcode=%s trace=%s",
lead_id, e.error_type, e.error_code, e.error_subcode, e.fbtrace_id,
```
