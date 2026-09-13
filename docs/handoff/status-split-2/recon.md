# status 2分割 便2 recon

便1 recon 親参照: docs/handoff/status-split/recon.md（release/status-split-1 に存在）

## 便2の調査範囲

便1完了後のフロント表示（バッジ・絞り込み・インボックス処理）の調査。

## 調査したファイルと行番号

| ファイル | 行番号 | 内容 |
|---------|--------|------|
| `frontend/src/utils/statusPresentation.ts:61-70` | STATUS_PRESENTATION_MAP.lead | `out_of_scope` エントリあり・`lead_out_of_scope` / `negotiating_out_of_scope` エントリなし |
| `frontend/src/pages/inbox/inbox.types.ts:26` | STATUS_TABS archive.statuses | `["lost", "out_of_scope"]`（旧値） |
| `frontend/src/pages/inbox/inbox.types.ts:37` | FOLLOWUP_EXCLUDED | `new Set(["lost", "out_of_scope"])`（旧値） |
| `frontend/src/pages/inbox/useInboxState.ts:739` | handleExclude | `status: "out_of_scope"` 送信 |
| `frontend/src/pages/inbox/useInboxState.ts:793` | handleBulkExclude | `status: "out_of_scope"` 送信 |

## 便1整合確認

- `backend/app/schemas/lead.py:39`: `out_of_scope = "out_of_scope"  # フロント互換用（受信のみ・DB保存しない）`
- `backend/app/routers/leads.py:544-551`: `if new_status == "out_of_scope":` → old_status で振り分け
- 結論: フロントは `status: "out_of_scope"` 送信のまま変更不要

## ADR 検索結果

- ADR-109: status SSOT（`docs/adr/ADR-109-leads-status-ssot-immutable-codes.md`）
- ADR-121: process-artifacts gate（`docs/adr/ADR-121-sop-process-artifacts-gate.md`）
