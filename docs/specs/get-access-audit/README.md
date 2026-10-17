# get-access-audit — 一覧の全件取得・ファイル出力の記録と、閲覧の大量取得の検知

- あるべき姿: [ideal-state.md](ideal-state.md)
- KGI: [kgi.md](kgi.md)
- 現在地・設計・審査・実装カード: [docs/handoff/s6-get-access-audit/](../../handoff/s6-get-access-audit/)
- コードの正本: backend/app/middleware/audit.py（記録対象の判定・閾値・INSERT）
- 守り手: backend/tests/test_get_access_audit.py

## 状態

- 2026-10-17 設計（Opus 確定・PO の一任に基づく）
- 2026-10-17 本番反映（PR #4411、2026-10-16 16:23Z マージ・deploy 成功）。K1・K2 は CI で○、K3・K4 は本番で○。本番の data_export 行は利用待ち
- 2026-10-17 追補1 本番反映（PR #4421: 401・403 になった閲覧を数えない。PO「y」）。F1〜F3 は本番で○
