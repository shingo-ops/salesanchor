# recon: 全画面を LINE のような使い心地にする（現在地）

作成: 2026-10-31 Claude Opus（設計担当）。基準: origin/main 8c6f52813。
PO の依頼: 「LINEみたいな使い心地は出来る？」→ 意味は「押した瞬間に開く速さ」（PO 選択「1」）→ 進め方は「135画面すべての作り方を先に設計する」（PO 選択「2」）。同日、全画面の基準は一律2秒（PO 選択「3」）。

## 1. 既存 ADR の検索
- 命令: `git grep -il -E "cache|キャッシュ|stale|楽観|optimistic|prefetch|先読み|即時反映" -- docs/adr/` と FEATURE-INDEX の同じ語。結果 19 件。画面のデータの持ち方に関係するのは 1 件だけ。
- ADR-1016（Accepted・即時反映の標準）: 書き込みが成功したら「変わった合図」を 1 本の SSE（GET /api/v1/events/stream）で送る。画面は useRealtimeRefresh(topics, reload) で受け、表を残したまま読み直す（docs/adr/ADR-1016-realtime-change-signal-standard.md 決定1〜7）。→ 本件の「前の中身をすぐ出し、裏で取り直す」は、この合図で古い中身を取り直す形にそろえる必要がある。
- そのほかの 18 件は DB の prepared statement・nginx・監視などで、画面のデータの持ち方とは無関係。

## 2. 画面のデータの取り方（事実）
- 画面の部品一覧に、取ったデータを手元に残す部品（TanStack Query・SWR など）は無い。`frontend/package.json` を `react-query|tanstack|swr|zustand|workbox|vite-plugin-pwa` で探して 0 件（react-router-dom ^7.0.0 だけが当たった・frontend/package.json:89）。
- 通信は `frontend/src/lib/api.ts` の `request()` 1 か所（frontend/src/lib/api.ts:104 から。審査 1 回目の指摘で行番号を直した）。GET は 0.5・1・2 秒待って最大 3 回まで送り直す。結果は残さない。`api` の出口は get/post/put/patch/delete/getBlob/postForm（frontend/src/lib/api.ts:240-252・get は :241）。
- `lib/api` を読み込むファイルは 245（`git grep -lE "lib/api['\"]" -- frontend/src`）。pages の中で useEffect を使うファイルは 118。→ 画面ごとに「開いたら useEffect で api.get、終わるまで読み込み中」の形が多い（件数は数えた。全部がその形かは まだ確かめていない）。
- 即時反映の合図を受けている画面は 3 か所だけ: frontend/src/pages/inventory/InventoryPage.tsx・frontend/src/features/inventory/InventoryRowDrawer.tsx・frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx。
- 画面の読み込み: frontend/src/App.tsx は pages を 94 個ふつうに import（lazy・Suspense は 0 件）。`<Route` は 127 か所（`grep -o "<Route" frontend/src/App.tsx | wc -l`）。→ 画面の部品は最初に全部読み込まれていて、画面を移るときに部品のダウンロードは無い。
- Service Worker・PWA の登録は 0 件（frontend/src に serviceWorker・registerSW なし、frontend/public に manifest なし）。
- ログアウト: frontend/src/lib/firebase-auth.ts:142 `signOut`。手元に残すデータを作るなら、ここで消す必要がある。

## 3. 今の速さ（事実）
- 毎朝の記録（.github/workflows/prod-ui-check.yml の速さの段、2026-10-31 04:33 UTC の手動実行 41169062594 ほか）で 135 画面すべて測れ、いちばん遅いのは在庫表 1.4 秒（本線・見本データ入り）。
- この秒は「初めて開いて、通信が全部終わり読み込み中の印が消えるまで」（docs/handoff/page-speed-record/design.md 5-3）。一度見た画面に戻ったときの秒・押してから最初に何か変わるまでの秒は、今は測っていない。
- 測る場所は GitHub の機械（外のコンピューター）。PO のスマホでの秒は まだ確かめていない。

## 4. 未確認 → 確かめた結果
- U1（数え直し 2026-10-31・審査 2 回目の指摘で再現できる形にした）: 数え方は docs/handoff/line-like-speed/u1-count.py（リポジトリの根で `python3 docs/handoff/line-like-speed/u1-count.py`。読むだけ）。対象は frontend/src/pages の *Page.tsx（*.test.tsx を除く）96 本（前の版の 93 本は BadgesPage・BuddyPage・BuybackByProductPage の 3 本を数え漏らしていた）。結果（基準 8c6f52813・origin/main 344c08f と frontend/src に差分なし）:
  - 読み込み中は中身を消して印だけ出す（A_clear）: 62 本。正規表現 early `if\s*\(\s*!?\w*[Ll]oading\w*[^)]*\)\s*(\{\s*)?return\b`（中身を消す形でない 3 行は script の NOT_CLEARING に理由付きで除外: ScheduleSettingsPage.tsx:52・ViewerTemplatesPage.tsx:72 は useEffect の中の return、SupplierExtractionRulesPage.tsx:456 は権限確認中の return null）、tern `\{\s*\w*[Ll]oading\w*\s*\?`（58 本）。三項の 1 本ずつの形は まだ確かめていない（段 3 の各便で確かめる）。
  - このファイルに api.get が無い（N_nofetch_in_file。子の部品・hook で取るか、取得しない）: 24 本。ほかの印を出す（X_other_indicator）: 7 本。印なし（C_noindicator）: 3 本。
  - 前の版の分け方（61/13/4/15）は分け方の決まりが残っていないので使わない。
  - 例: frontend/src/pages/admin/ChannelMastersPage.tsx:36 `setLoading(true)`→:79-80 `{loading ? (<LoadingBlock />`。frontend/src/pages/companies/CompaniesPage.tsx:400-401 同じ形。
  - 表を残したまま取り直す例: frontend/src/pages/inventory/InventoryPage.tsx:226 `setLoading(true)`・:282 useRealtimeRefresh・:631-639 で表は消さない。ただし印は金型ではなく生の `<div className="loading-indicator">{t("common.loading")}</div>`（文字だけの印・CC_UI_GOVERNANCE が禁じる形）なので、手本にはしない。在庫表の取り直し間隔は 5 秒＋0〜3 秒のずれ（InventoryPage.tsx:110-121・ADR-1016 改訂 2026-10-18 の PO 決定）。
  - ほかの形の印: 13 本。印なし: 4 本。ファイルの中で取得しない（子の部品か hook で取る）: 15 本。
  - 読み込み中の金型は frontend/src/components/loading/LoadingBlock.tsx:16（components/loading/index.ts:4 から出す）。使うファイル 109。骨組み表示の金型 Skeleton（components/loading/Skeleton.tsx・class sa-skeleton）もある（前の版の「無い」は誤り）。取り直し中の小さな印の金型 Spinner（components/loading/Spinner.tsx・class sa-spinner。部品の説明に「while a table refetches」に使うと書いてある）もある。
- U3（確かめた 2026-10-31）: 会社を切り替える画面の操作は無い。`switchTenant|X-Tenant|impersonat|tenantSelect|setTenant` を frontend/src で探して 0 件。tenant_id は型の項目にだけ出る。
  - ただしログアウトはページを読み直さない: frontend/src/contexts/AuthContext.tsx:139-150 の signOut は自社ログインでは `api.post("/auth/logout")`→`expireSession()` だけ。frontend/src/lib/auth/selfAuth.ts:67-70 の expireSession はメモリの session を null にして notify するだけ。api.ts の 401・期限切れの道（:86・:93・:100）も expireSession を呼ぶ。→ 手元に写しを持つなら、session が変わった知らせ（selfAuth.ts:49 subscribeSession／AuthContext.tsx:90 onAuthStateChanged・:105 subscribeSession）で必ず消す必要がある。
  - ブラウザの保存（localStorage）を使う場所: firebase-auth.ts:74・:77、inbox/useInboxState.ts:488・:508（下書き）・:520（受信箱の設定）、viewer/api.ts:20・:28（閲覧ページの鍵）。画面の中身（DB のデータ）は保存していない。
  - 容量: 写しはメモリだけに持ち（ブラウザの保存に書かない）、使われない写しは 5 分で捨てる既定（TanStack Query gcTime 既定 5 分・/tmp/CC報告ファイル/page-speed/line/lib-docs.md）にすれば、上限はその時開いた画面の分だけ。
- 部品の包み順: frontend/src/main.tsx は `<App/>` だけ。frontend/src/App.tsx:151-155 が AuthProvider > BrowserRouter > UiPrefsProvider > LocaleProvider > ThemeProvider。即時反映の受け口 RealtimeProvider は DesktopShell.tsx:204・MobileShell.tsx:198（ログイン後のシェルの中）。
- 即時反映の合図の名前は今 2 つだけ: backend/app/realtime/topics.py の `tcg.review`・`tcg.inventory`（生: /tmp/CC報告ファイル/page-speed/line/realtime-raw.txt）。合図の受け方は frontend/src/hooks/useRealtimeRefresh.ts（自分の変更は無視・1.5 秒まとめ・裏のタブは保留・再接続で 1 回）。→ 135 画面の多くは今は合図を出す書き込みが無い。
- 測り方: tests/prod-check/page-speed.spec.ts:72-79 の goInApp はページを読み直さずに画面を移る（pushState＋popstate）。秒は :311 で `max(navStart, 最後の通信の終わり, 読み込み中の印が消えた時) - navStart`。→ 同じページの中で 2 回目に開けば K1 を今の仕組みのまま測れる。
- U2: PO が実際によく使う画面と、PO のスマホでの体感の秒。→ まだ確かめていない（K6 で PO に触ってもらうときに聞く）。
- 測る道具の限界（審査 1 回目の指摘）: tests/prod-check/settle.ts の waitSettled は 100 ms ごとに見て、最短 500 ms・静かな時間 1000 ms を待つ。読み込み中の印の目印は `.sa-loading-block, .sa-skeleton, .loading-screen, .loading-indicator, [aria-busy="true"]`（sa-spinner は入っていない）。→ 0.1 秒（K1・K3）は今の道具では測れない。画面の中に置く記録係（毎フレーム見る）が要る。
- 中身の場所: パソコンの枠は frontend/src/components/DesktopShell.tsx:400 `<main className="app-content…">`、スマホの枠は MobileShell.tsx:201 `<main className="mobile-content">`。
