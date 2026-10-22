# recon: 閲覧ページを再読み込みなしで新しくする

基準: `origin/main` 0a22b62a8（2026-10-22 fetch 後）。調査は Sonnet、要点の照合は Opus（ViewerApp.tsx・InventoryView.tsx・useExpiryRefresh.ts は Opus が実物を読んだ）。生出力: /tmp/CC報告ファイル/viewer-live/recon/・/tmp/CC報告ファイル/viewer-live/recon2/（summary.md）。

## PO の依頼と承認（原文）
- 2026-10-21「新規投稿があり解析が完了した後に画面を再読込しなくても情報が更新される仕組みに出来る？」
- 対象の画面は閲覧ページ（/viewer/）。PO「1」（2026-10-22）。
- 目標の時間は「解析が終わってから2分以内」。案「1分ごとに新しくなったかを確かめる」に PO「1」（2026-10-22）。

## 既存の決め（ADR・設計）
- ADR 検索: `git grep -il "viewer\|閲覧ページ" origin/main -- docs/adr` → ADR-1019（閲覧ページ）。ほかに ADR-1016（即時反映）。`docs/adr/FEATURE-INDEX.md` に viewer・realtime の行は無い。
- `docs/adr/ADR-1019-inventory-viewer-separate-accounts.md:23`（決定5）: 閲覧者が呼べる入口は7本。
- `docs/adr/ADR-1019-inventory-viewer-separate-accounts.md:25`（決定7）: 作り置きは1分に1回だけ作り直して Redis から全員に配る。
- `docs/handoff/gas-viewer-fresh-fast/design.md:217`・`:590`: 更新ボタンは付けない（PO 2026-10-15「y」）。:590 には「最新はページの再読み込みで出る」とある。本件でこの1文が古くなるので書き直す。
- `docs/handoff/gas-viewer-fresh-fast/design.md:328`: updated_at は60秒以内。:331 は「20回/分で429なし」。
- ADR-1016 に「ポーリング禁止」の文は無い。`docs/handoff/realtime-standard/design.md:116` は、本体アプリについてポーリングを「不採用（開いている間ずっと負担がかかる）」としている。閲覧ページは本体アプリの即時通知（`/api/v1/events/stream`）を使えない。認証が本体アプリのトークンで、閲覧者のトークンは 401 になる（ADR-1019 決定4、`backend/app/routers/realtime_events.py:58-71`）。

## 画面（frontend/src/pages/viewer/）
- `frontend/src/pages/viewer/ViewerApp.tsx:65-80`: load() が在庫を取る唯一の入口で、呼ばれるのは起動時とログイン後だけ。
  - :71 で `{ name: "loading" }` にする。そのため load() を繰り返し呼ぶと InventoryView が一度消え、検索・タブ・ページが初期値に戻る。
  - 失敗時は :78 で screenForError（:38-47）の画面に置き換わる。401 はログイン画面、503 は準備中の案内。
  - トークンを消すのは detail が "invalid viewer token" のときだけ（:75-77）。
- `frontend/src/pages/viewer/InventoryView.tsx:57-71`: 検索・タブ・絞り込み・並べ替え・ページ・絞り込み Drawer は InventoryView の useState にある。InventoryView が画面に残ったまま `data` だけが替われば消えない。
  - タブの初期値（:57-59）は初回だけ決まる。
  - ページは :104 で範囲内に丸められる。
- `frontend/src/pages/viewer/InventoryView.tsx:55`: `const [now] = useState(() => Date.now())` は初回だけ決まる。24時間以内の絞り込み（:99 → viewerFilter.ts:83）に使うため、データを差し替えても今のままでは古い時刻で判定される。
- `frontend/src/pages/viewer/InventoryView.tsx:205`: 最終更新の時刻は `data.updated_at` から出す。
- `frontend/src/pages/viewer/InventoryView.tsx:323`: rowKey は配列の位置（idx）。
- `frontend/src/pages/viewer/InventoryView.tsx:1`: 冒頭の注記に「更新ボタンは無い」とある。
- 前例のフック `frontend/src/hooks/useExpiryRefresh.ts:13-46`: setTimeout と visibilitychange を使う。裏のタブでは保留し、表に戻ったら1回だけ呼ぶ。汎用のポーリングフックは無い。
- `frontend/src/pages/viewer/api.ts`: fetchInventory(token) は `GET /api/v1/viewer/inventory`。失敗は ViewerApiError(status, detail)。

## API（backend）
- `backend/app/routers/viewer.py:234-246`: GET /api/v1/viewer/inventory。
  - 応答は `{updated_at, fresh_window_hours, rows}`。
  - キャッシュが無ければ 503 "viewer_inventory_not_ready"。
  - ETag や軽い確認用の入口は無く、毎回全文を返す。
- `backend/app/tasks/viewer_inventory_cache.py:87`: updated_at は作り直しが成功するたびに今の時刻になる（中身が同じでも毎分変わる）。
- `backend/app/tasks/viewer_inventory_cache.py:79-84`: 解析待ちがある間は書かない（前の値と時刻のまま）。
- `backend/app/celery_app.py:188-192`: 作り直しは60秒ごと。
- 行数の上限は `backend/app/services/tcg_distribution_svc.py:45` の DIST_ROW_LIMIT=5000。1行は15キー。応答のバイト数は実測していない【未確認】。

## 回数の制限
- `backend/app/middleware/rate_limit.py`:
  - 認証済みは 300回/分（:30）。
  - 未認証は IP 単位で 60回/分（:34）。
  - 閲覧者の JWT に email が無い（`backend/app/auth/viewer_tokens.py:39-44`）ので、閲覧者は IP 単位 60回/分の枠で数えられる。
- nginx は api zone が 30r/s、/api/ の burst は50（`nginx/nginx.conf:8`、`:217-219`）。

## テスト
- vitest: `frontend/src/pages/viewer/*.test.tsx`。ViewerApp のテストは無い。実行は `cd frontend && npm run test:unit`。
- 閲覧ページの e2e は無い。

## i18n
- `frontend/src/locales/viewer/ja.json:11` viewer.lastUpdated（「最終更新 {{time}}」の形）。時刻の表示が変わるだけなら新しいキーは要らない。
