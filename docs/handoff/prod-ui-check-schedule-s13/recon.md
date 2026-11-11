# recon: 本番の画面点検に予定表の作る小窓と全画面の編集を足す（S13）（2026-11-11）

- 作成: Claude Opus。根拠はすべて origin/main bfe2e4e7a（予定表の全画面の編集の合流後）の実物。
- 発端: 予定表の全画面の編集の本番確かめ（2026-11-11 JST・手作業）の後、PO が「1. 毎日の本番の自動点検に、この画面の動きを足す」を選んだ（2026-11-11）。

## 0. 既存 ADR の検索

- `git grep -il "prod-ui-check\|画面点検" docs/adr` → ADR-1051（本番の画面点検）・ADR-1053（速さの記録）。今回は ADR-1051 を改訂する。
- ADR-1051 の決まりで今回に効くもの（`docs/adr/ADR-1051-prod-ui-black-box-check.md`）
  - :19 点検用の人は管理者ではなく、見るだけの権限だけを持つ役割。
  - :24 点検は SQL・DB 接続を持たない。本番のデータを作らない・変えない・消さない。
  - :27 trace・スクリーンショット・html レポートは作らない。
- ADR-1060（Google Meet は Google をつないだ本人の予定にだけ）。ADR-144（金型 FullScreenDialog）。

## 1. 今の点検（事実）

- 仕組み: `.github/workflows/prod-ui-check.yml:8-12` 毎朝 22:00Z（JST 07:00）と、配備（Deploy to VPS）が成功して終わったあと（workflow_run）に動く。不合格のときだけ Discord に送る（同 :118-155）。
- 点検の中身: `tests/prod-check/prod-ui.spec.ts`
  - :163-176 S12 は予定表を開き、予定の API が 400 未満・`.comp-calendar` が見える・読み込み中/エラーが 0・5 秒の間の console.error が 0 を見るだけ。作る小窓・全画面の編集は触らない。
  - :179-184 S9（通知の試験）は PROD_CHECK_FORCE_FAIL=1 のときだけ。:185 が describe の閉じ。
- 設定: `tests/prod-check/playwright.config.ts` workers 1・retries 1・timeout 60 秒・trace/screenshot/video off。
- ログイン: `tests/prod-check/fixtures.ts` worker で 1 回だけログインし context を使い回す。test の始まり同士を 20 秒空ける。
- 直近の結果: 11/9 の配備の後の実行で S1〜S8・S10〜S12 の 11 件合格（PO の記録・run 42546289435）。

## 2. 予定表の新しい動き（事実）

- 作る小窓を開く道: キー `c` で `openCreate(new Date(), null, SHORTCUT_CREATE_HOUR)`（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1285`、:118 で 9 時）。権限による止めは無い（:940-960）。マス目を押す必要が無く、予定の有無に左右されない。
- 小窓が開いている間は文字キーは効かない（同 :1255 `windowOpen`、:1266 `if (windowOpen) return;`）。`m` は月表示に切り替えるキー（:1283）。
- 「その他のオプション」ボタン（:426）→ `setFullEditOpen(true)`（:1583）。全画面の編集は `open={fullEditOpen && popover?.mode === "create"}`（:1588）。
- 全画面の編集の器: `frontend/src/components/FullScreenDialog.tsx` :89 `role="dialog"`・aria-label、:72-78 Esc で閉じ document で止める（窓の近道まで届かない）、:81 useFocusTrap で Tab を中に閉じ込める。
- Meet の行: `frontend/src/pages/schedule/ScheduleDraftFields.tsx:211` `meetAvailable && !item?.meetUrl` のときだけ出る。`meetAvailable` は `/google-calendar/status` の `meet_available`（SchedulePageImpl.tsx:824）で、この問い合わせは `enabled: isTenantAdmin`（:821）。
  - → 点検用の人は管理者ではない（ADR-1051:19）ので、点検では Meet の行は出ない。Meet の行の押す・外すは本番の点検では確かめられない。単体試験（SchedulePageImpl.test.tsx:468・484・558・571）が守る。
- 画面の文字（`frontend/src/locales/ja.json`）: :3311 タイトルを追加・:3312 その他のオプション・:3346 週・:3354 予定の編集。題名の欄の aria-label は「タイトル」。閉じるボタンは「閉じる」。
- service worker: `frontend/src/lib/webPush.ts:43` は通知の申し込みのときだけ登録し、`frontend/public/sw.js` に fetch の処理は無い → Playwright の page.route で書き込みを止められる。

## 3. 本番での手作業の確かめ（2026-11-11 JST）

- PO のアカウントで G51〜G57 を確かめ 7 件合格。保存は 0 件（GET 以外の fetch/XHR を記録し最後まで空）。記録: 予定表の全画面の編集の作業記録（PO への報告済み）。
- 手作業なので、次の配備で壊れても人が見るまで気づけない。これが今回埋める穴。
