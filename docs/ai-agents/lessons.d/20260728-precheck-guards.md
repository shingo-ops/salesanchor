分類: 6-2
出所: （2026-07-28 PR #3108・#3127）

- 危険変更・正本変更のカードを組む前に、その変更に効く関所・ガードの適用条件を実コードで確認してから設計する。読まずに走ると連続failで停止を重ねる。本セッションでは reaper修正1行と教訓1行の反映で、削除ファイル欄未宣言・GO記録ラベル略記・§6本文直接編集禁止(lessons-guard)・strict(base not up to date)の順に停止が続いた。いずれも着手前に check-process-artifacts.js（触る/削除ファイルのパース・GO記録の正確なラベル）と lessons-guard.yml（§6本文追記の検出・lessons-cleanupラベル例外）を読んでいれば防げた（2026-07-28 実測。§6教訓は本文直接編集せず lessons.d へポストするのが正）。
- docs変更は check-process-artifacts の「書類のみ=自動スキップ」で手元passでも、lessons-guard は §6本文への箇条書き追記を別途CIで検出する。手元passとCI failが分かれるのはガードが別だから。教訓の追加は §6本文でなく docs/ai-agents/lessons.d/ に新規ファイルで行えばこのガードに当たらない（2026-07-28 PR #3124 fail→#3127 pass で実測）。
