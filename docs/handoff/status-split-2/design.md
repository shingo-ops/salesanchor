# status 2分割 便2 設計

親 recon: docs/handoff/status-split/recon.md

## 目的

`lead_out_of_scope` / `negotiating_out_of_scope` のフロント表示（バッジ・絞り込み・受信箱処理）を対応する。

## 前提（便1完了済み）

- enum 2分割・サーバー振り分け（`out_of_scope` 受信→`old_status` で振り分け）は便1完了
- `out_of_scope` は enum に残置（フロント互換用）。フロントは引き続き `status: "out_of_scope"` を送る
- i18n（`leads.statusCode.lead_out_of_scope` 等）は便1完了

## 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `frontend/src/utils/statusPresentation.ts` | `lead_out_of_scope` / `negotiating_out_of_scope` のバッジ設定を追加（danger/lost 相当） |
| `frontend/src/pages/inbox/inbox.types.ts:26` | アーカイブタブ statuses を `["lost","lead_out_of_scope","negotiating_out_of_scope"]` に変更 |
| `frontend/src/pages/inbox/inbox.types.ts:37` | `FOLLOWUP_EXCLUDED` を2値に変更 |

## 変更しないファイル

- `useInboxState.ts` — 「対象外にする」操作は `status: "out_of_scope"` を送信し続ける。便1サーバーが振り分けるため変更不要
- `leads.py` / `lead.py` — 便1完了
- `analytics.py` / `dashboard.py` / `tasks/dashboard.py` — 便3で別途

## 便1整合確認

便1の `leads.py:544-551`:
```python
if new_status == "out_of_scope":
    if old_status in (LeadStatus.lead_out_of_scope.value, LeadStatus.negotiating_out_of_scope.value):
        new_status = old_status
    elif old_status in _PRE_DEAL_STATUSES:
        new_status = LeadStatus.lead_out_of_scope.value
    else:
        new_status = LeadStatus.negotiating_out_of_scope.value
```

`LeadStatus.out_of_scope` は enum に残置（`# フロント互換用・受信のみ・DB保存しない`）。
Pydantic `LeadUpdate.status: LeadStatus | None` は `"out_of_scope"` を受理 → 振り分け → DB 保存前に2値のどちらかになる。
**齟齬なし: フロント送信値変更不要。**

## KGI / KPI

| 基準 | 検証方法 |
|------|---------|
| `lead_out_of_scope` のリードにバッジ「対象外（商談化前）」が表示される | statusPresentation.ts の labelKey 参照 |
| `negotiating_out_of_scope` のリードにバッジ「対象外（商談化後）」が表示される | statusPresentation.ts の labelKey 参照 |
| アーカイブタブに2値のリードが表示される | STATUS_TABS の statuses 確認 |
| フォローアップフィルターから2値が除外される | FOLLOWUP_EXCLUDED の Set 確認 |

## 外部事例

ADR-109 の status SSOT 化パターンに準拠。status 追加時のフロント対応は statusPresentation.ts への entry 追加が定跡。

## 対象 ADR

- ADR-109: `docs/adr/ADR-109-lead-status-immutable-codes.md`
- ADR-121: `docs/adr/ADR-121-tenant-migration-pattern.md`
