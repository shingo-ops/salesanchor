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

---

## 3 回目（5-0b・HEAD 740624524・2026-10-31 04:36 JST・クラウド Opus 読むだけ・run cse_01W47tdhuGHrzsq1oFQZzemS）

判定: REVISE（must 1）

- 項目 1 ○: 読み込み直しごとに refresh 1 件（`frontend/src/contexts/AuthContext.tsx:104-108`）。ログイン直後は refresh を呼ばない（`frontend/src/lib/auth/selfAuth.ts:103-106`・`frontend/src/pages/login/LoginPage.tsx:50`）。1 回のログインは 3 件でなく 2 件
- 項目 2 ○: コードから数えると 11 件（13 件の見込みより少ない）。漏れた `/api/v1/auth/` 呼び出しは無い。「90 秒で 15 件戻る」は `burst=5`（`nginx/nginx.conf:145`）と合わない説明
- 項目 3 ○（公式文書による）: 再試行で作業者が作り直され、beforeAll と authPace の初期化が効く。`browser.newPage()` に config の `use` が引き継がれるかは未確認
- 項目 4 ○: 会社のリンクは react-router の `Link`（`frontend/src/pages/companies/CompaniesPage.tsx:406`・`frontend/src/components/ButtonLink.tsx:3`）で読み込み直しは起きない
- 項目 5 ○: `tests/prod-check/` の中だけで済み、ADR-1051 に反しない
- must: 秘密情報が無いとき S2 だけ飛ばすと、S3〜S6・S8 がログインせずに動いて落ちる。まとめ全体を飛ばす書き方を決める
- should: 件数と制限の説明を直す。beforeAll の page の作り方を決める

対応（同日・設計担当 Opus）: design.md 5-0b に、まとめ全体の skip・beforeAll の guard・page の作り方（`baseURL` を明示して渡す）・件数 11 件・制限の説明の書き直しを入れた。再審査に回す

## 4 回目（5-0b 再審査・HEAD 547e2198b・2026-10-31 04:44 JST・クラウド Opus 読むだけ・run cse_01W47tdhwC95VoY43uEYDSPD）

判定: APPROVE（must 0 件・should 2 件）

- 公式文書（playwright.dev）はクラウドの通信制限で読めなかった（未確認）。代わりに Playwright 1.63.0 の型定義と実装を読んで確かめた
- 1 ○: まとめの本体の `test.skip(条件, 理由)` は、まとめ全体に skip の印を付ける（`playwright/lib/common/index.js` の `_modifier`）
- 2 ○: 手で作る context に `use` の `baseURL`・devices は引き継がれない（引き継ぐのは `context` fixture 専用の `_combinedContextOptions`）。明示して渡す設計は正しい。trace・screenshot・video は作られない
- 3 ○: config が `./login` を読んでも問題は無い
- 4 ○: 11 件で前回と一致
- should 1: 「使う速さは戻る速さを超えない」は 2 件を使う操作では成り立たない。「2 件を使うのは S2・S7 の 2 回だけで、超過は 5 件のまとめ枠が吸収する」に書き直す → design.md 5-0b に反映
- should 2: S9 の置き場所と authPace を明記する → design.md 5-0b に反映

## 5 回目（5-8 便2 と実装カード・HEAD 3d365130b・2026-10-31 10:30 JST・クラウド Opus 読むだけ・run cse_01W47tdfYPP8GkSWSvtuU3gc）

判定: APPROVE（must 0 件・should 4 件）

- 1 ○: 在庫表の印は読み込み後 `visibility: hidden` で残る（`frontend/src/pages/inventory/InventoryPage.tsx:631-636`）。見えている印は visible なので数え落とさない
- 2 ○: 送り直しは 502/503/504 と TypeError だけ（`frontend/src/lib/api.ts:34,108-110,153`）。409 はすぐ止まる。手数料の画面はエラーを出して読み込み中を終える（`frontend/src/pages/commission-settings/CommissionSettingsPage.tsx:113-126`）。fulfill はブラウザの中で答え、本番に届かない
- 3 ○: 移り先 3 つは `frontend/src/App.tsx:198-199・351-352・375-376` と一致。表の並びで直前の行が移り先になる画面は無い
- 4 ○: 5 つの理由の判定順に漏れなし。requestfinished は 4xx でも起きる
- 5 ○: 型は成り立つ。6 ○: 触らない範囲は明確
- should 1: render の引数の順（forbiddenApis は blocked の次）を明記 → カード 4-5・4-14 に書いてある
- should 2: MissReason の値の形 → カード 4-1 に全文の値を書いてある（`番号を拾えず（一覧が 403）` など）
- should 3: blockedBefore は leaveIfSame の後・goInApp の直前で取る → カード 4-12 はその位置
- should 4: redirect の行が別の画面へ移ったときの道すじの欄 → `A → B` のまま状態「別の画面へ移った」とする（カード 4-12・4-13 のとおり）
