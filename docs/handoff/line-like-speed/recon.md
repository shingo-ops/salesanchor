# recon: 全画面を LINE のような使い心地にする（現在地）

作成: 2026-10-31 Claude Opus（設計担当）。基準: origin/main 8c6f52813。
PO の依頼: 「LINEみたいな使い心地は出来る？」→ 意味は「押した瞬間に開く速さ」（PO 選択「1」）→ 進め方は「135画面すべての作り方を先に設計する」（PO 選択「2」）。同日、全画面の基準は一律2秒（PO 選択「3」）。

## 1. 既存 ADR の検索
- 命令: `git grep -il -E "cache|キャッシュ|stale|楽観|optimistic|prefetch|先読み|即時反映" -- docs/adr/` と FEATURE-INDEX の同じ語。結果 19 件。画面のデータの持ち方に関係するのは 1 件だけ。
- ADR-1016（Accepted・即時反映の標準）: 書き込みが成功したら「変わった合図」を 1 本の SSE（GET /api/v1/events/stream）で送る。画面は useRealtimeRefresh(topics, reload) で受け、表を残したまま読み直す（docs/adr/ADR-1016-realtime-change-signal-standard.md 決定1〜7）。→ 本件の「前の中身をすぐ出し、裏で取り直す」は、この合図で古い中身を取り直す形にそろえる必要がある。
- そのほかの 18 件は DB の prepared statement・nginx・監視などで、画面のデータの持ち方とは無関係。

## 2. 画面のデータの取り方（事実）
- 画面の部品一覧に、取ったデータを手元に残す部品（TanStack Query・SWR など）は無い。`frontend/package.json` を `react-query|tanstack|swr|zustand|workbox|vite-plugin-pwa` で探して 0 件（react-router-dom ^7.0.0 だけが当たった・frontend/package.json:89）。
- 通信は `frontend/src/lib/api.ts` の `request()` 1 か所（frontend/src/lib/api.ts:13-76 相当）。GET は 0.5・1・2 秒待って最大 3 回まで送り直す。結果は残さない。`api` の出口は get/post/put/patch/delete/getBlob/postForm（frontend/src/lib/api.ts:240-252）。
- `lib/api` を読み込むファイルは 245（`git grep -lE "lib/api['\"]" -- frontend/src`）。pages の中で useEffect を使うファイルは 118。→ 画面ごとに「開いたら useEffect で api.get、終わるまで読み込み中」の形が多い（件数は数えた。全部がその形かは まだ確かめていない）。
- 即時反映の合図を受けている画面は 3 か所だけ: frontend/src/pages/inventory/InventoryPage.tsx・frontend/src/features/inventory/InventoryRowDrawer.tsx・frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx。
- 画面の読み込み: frontend/src/App.tsx は pages を 94 個ふつうに import（lazy・Suspense は 0 件）。Route は 110。→ 画面の部品は最初に全部読み込まれていて、画面を移るときに部品のダウンロードは無い。
- Service Worker・PWA の登録は 0 件（frontend/src に serviceWorker・registerSW なし、frontend/public に manifest なし）。
- ログアウト: frontend/src/lib/firebase-auth.ts:142 `signOut`。手元に残すデータを作るなら、ここで消す必要がある。

## 3. 今の速さ（事実）
- 毎朝の記録（.github/workflows/prod-ui-check.yml の速さの段、2026-10-31 04:33 UTC の手動実行 41169062594 ほか）で 135 画面すべて測れ、いちばん遅いのは在庫表 1.4 秒（本線・見本データ入り）。
- この秒は「初めて開いて、通信が全部終わり読み込み中の印が消えるまで」（docs/handoff/page-speed-record/design.md 5-3）。一度見た画面に戻ったときの秒・押してから最初に何か変わるまでの秒は、今は測っていない。
- 測る場所は GitHub の機械（外のコンピューター）。PO のスマホでの秒は まだ確かめていない。

## 4. 未確認
- U1: 118 ファイルのうち、何画面が「開くたびに読み込み中の印を出して表を消す」形か。
- U2: PO が実際によく使う画面と、PO のスマホでの体感の秒。
- U3: 手元にデータを残すときの容量と、会社を切り替える操作があるか（super admin の会社切替）。
