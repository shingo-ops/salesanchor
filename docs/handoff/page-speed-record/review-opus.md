# Opus 審査記録: 本番の全画面の速さを毎日記録する

- 審査者: Claude Opus（設計担当とは別に、クラウドで起動した設計審査役）
- 範囲: 便0（今の点検の待ち方を直す）。便1 は別に審査する

## 設計 1 回目（HEAD 92ab926・2026-10-31）
- 判定: REVISE
- M1: 開いたままの通信は 1 本ではなく 3 本（`/api/v1/events/stream`・`/api/v1/conversations/stream`・`/api/v1/leads/stream`）。道すじの一覧で除くと漏れる
  - 直し: 頭書き `Accept: text/event-stream` で見分ける形にした（design.md 5-0・5-3）
- M2: 点検用の人が `messaging.view` を持たなければ、S3 が 403 の console error で落ちうる
  - 直し: 便0 の手動実行の結果を見てから、待ち方とは別に直す形にした（design.md 5-0）
- M3 以降: 審査の記録が途中で切れ、読めなかった（未確認）

## 設計 2 回目（HEAD dec5d948f・2026-10-31）
- 判定: APPROVE（must 0 件・should 3 件）
- 確かめた事実（審査役の報告から）
  - 開いたままの通信 3 本と、そのつなぎ直しは、同じ頭書きで送られる（`frontend/src/hooks/useSSE.ts:45-51`・`frontend/src/lib/realtime/RealtimeProvider.tsx:77-84`）
  - S3〜S6 の画面で動く定期の読み直しは、10 分ごとの `fetch("/")` だけで `/api/` の外（`frontend/src/hooks/useAppUpdateCheck.ts:59`）
  - S5 の検索に入力待ちは無い（`frontend/src/pages/companies/CompaniesPage.tsx:221`）。S6 の転送は `frontend/src/App.tsx:126-129,189`
  - 未確認: Playwright の `request.headers()` に Accept が出るか。便0 の手動実行で分かる
- should の取り込み（HEAD dec5d948f の次の commit）
  - should 1: G0 を「0 failed。S6 の『会社 0 件』の skip は可」に直した
  - should 2: S3 が 403 で落ちたときは、同じ PR に別の commit で数え方を直し、もう 1 回手動実行してからマージする、と 5-0 に書いた
  - should 3: 打ち切りの失敗文に、終わっていない通信の数と読み込み中の印の数を出す（`expectSettled`）
