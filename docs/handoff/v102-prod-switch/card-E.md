# card-E: 便E（既定を v102 に切替）

- 目的: 本番 LINE解析エンジンを v6 から v102 に切替（PO 承認済み、備考列は空でよい 2026-10-10）
- 変更: docker-compose.yml:218 `${LINE_ANALYSIS_ENGINE:-v6}` → `${LINE_ANALYSIS_ENGINE:-v102}`（コメント行217も追従）
- 触らない: backend/app/services/line_analysis_v102_svc.py:100 の get_engine（未設定は v6 のまま）、テスト（compose の既定値を検査するものは無い）
- 受入条件・戻し方: design.md §14
- 事実: recon.md §7
