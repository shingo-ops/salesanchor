# Opus 審査記録: 規則12h の設計（同一 AI の自己審査・独立の審査ではない）

- 日時: 2026-11-10
- 対象: `docs/handoff/shime-box-all-states/recon.md`・`docs/handoff/shime-box-all-states/design.md`・`docs/adr/ADR-1073-shime-box-all-states.md`
- 判定: APPROVE（便1 は実装可能）。便4（設定を入れる）は design §6 の未解決（設定を消した後の古い相手の扱い）が片付くまで不可。
- 確かめたこと（origin/main 96a63df05 以降の実物）:
  - `decide_soldout_inherit` の呼び出しは `backend/app/services/gemini_raw_copy_v101.py:1314` の 1 か所だけ（`git grep`）。
  - 設定の読み方の前例 `_KUBUN_ALLOWED_UNITS_SQL`（`backend/app/services/gemini_raw_copy_v102_product_first.py:173`）が在る。
  - 状態の `value_group`・`value_rank` は `public.conditions` から読む（`backend/app/services/tcg_analyzer_svc.py:695-712`）。
  - やり直しの道具 `backend/app/tools/v102_replay_diff.py` に設定の差し込みの前例 `--heading-setting`（`:182`・`:104-105`）が在る。
  - 既存の試験 `backend/tests/test_gemini_raw_copy_v102_soldout_ref.py` が在る。
- 審査で直した点: 状態の表の名前（line_conditions → conditions）。やり直しの道具を main にあるものへ変え、語を本番へ先に入れる順に変えた。ADR の状態の欄の「承認」の語が索引で Accepted と読まれるのを直した。
- 未解決: 本番の `value_group` の今の値（読み取り専用の鍵で読めない。便3 の道具の出力で確かめる）。設定を消した後の古い相手の扱い。
