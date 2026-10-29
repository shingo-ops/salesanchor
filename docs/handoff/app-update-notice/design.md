# 新しい版のお知らせ（アプリに戻ったときに版を確かめる）設計

状態: 設計審査済み（Opus 自己審査・APPROVE）／PO 実装承認済み（2026-10-29）／実装中（PR 起票時）

## 1. 目的と PO の決定

- 困りごと: スマホのホーム画面に置いたアプリは、開き直しても前の画面が残る。新しい版を本番に出しても古いまま動き続ける。2026-10-29 に PO の実機で、リードをまとめる操作が出ないことで見つかった。アプリを完全に閉じて開き直すと直ることも PO が確かめた。
- PO の決定（2026-10-29、選択肢「1」と「実装」）: 新しい版が出ていたら、画面の上に「新しい版があります・更新」と小さく出す。押すと新しくなる。自動では読み込み直さない（書きかけの返信を消さないため）。

## 2. 今の姿（下調べ 2026-10-29、origin/main）

- 版を確かめる仕組み・自動で読み込み直す仕組みは無い（location.reload / vite:preloadError / version.json / build id の grep 0件）。
- 入口 /index.html は frontend/nginx.conf:17-20 で `no-cache, must-revalidate`。/assets/*.js は :39-43 で1年 immutable。入口は `/assets/main-<hash>.js` を読む（本番で確認: 10:57 版 main-D5II-XqL.js → 11:09 版 main-CnuEGokh.js）。
- Service Worker・manifest は無い。index.html に apple-touch-icon だけある。
- 画面の上に常駐する知らせの金型は無い。Toast（components/loading/Toast.tsx）は4秒で消えてボタンを持てない。Callout（components/Callout.tsx、ADR-144）は中に Button を入れられる。
- 両方の殻（MobileShell / DesktopShell）の外で共通なのは App.tsx:154 の `<Toaster />` の位置。
- 戻ってきたときに動く流儀は ADR-1016（useRealtimeRefresh.ts:59、useExpiryRefresh.ts:40）にある。

## 3. 変えること（対象）

1. 版の確かめ方: 今の画面が読み込んだ `/assets/main-<hash>.js` の名前と、入口 `/` を `cache: "no-store"` で取り直して見つけた `/assets/main-<hash>.js` の名前を比べる。違えば新しい版がある。
   - 理由: ビルド・Dockerfile・nginx・deploy.yml を変えずに済む。入口は既に no-cache で、ファイル名の hash はビルドごとに変わる。
   - 今の画面の名前は `document.querySelector('script[type="module"][src*="/assets/main-"]')` から取る。取れない（開発サーバーなど）ときは何もしない。
2. 確かめる時: (a) アプリが裏から表に戻ったとき（visibilitychange で visible）、(b) 表に出ている間は10分ごと。どちらも前回から60秒以内なら確かめない。裏にいる間は確かめない。
3. 新しい版を見つけたら確かめるのをやめ、知らせを出したままにする。閉じるボタンは置かない。
4. 知らせ: 画面の上の中央に小さく出す。中身は「新しい版があります」の文と「更新」ボタン（金型 Button）。押すと `window.location.reload()` を1回呼ぶ。
   - 置き場所: App.tsx の `<Toaster />` の隣（PC・スマホ・殻の無い画面すべてに出る）。
   - 見た目: 既存の金型（Callout の info と Button）を組み合わせる。色・余白・z-index は token だけを使う（ADR-067）。新しい色 token は足さない。z-index は var(--z-toast)。上の余白は `calc(env(safe-area-inset-top, 0px) + var(--space-2))`。`position: fixed` には既存例どおり `/* fixed-ok: ... */` を付ける。
   - スマホ幅（〜767px）では左右に余白を取って横いっぱい、ボタンの高さは 44px 以上。
5. 文言（t() 経由、ja/en 同じキー）: appUpdate.message「新しい版があります」/「A new version is available」、appUpdate.reload「更新」/「Reload」。
6. 失敗したとき（通信できない・入口の形が想定と違う）: 何も出さず、次の時を待つ。エラーを画面に出さない。console にも出しすぎない。

## 4. 対象外

- 自動の読み込み直し（PO が選ばなかった）。
- 閲覧ページ（/viewer/、別の入口）。データは既に1分ごとに取り直している。必要なら別に決める。
- Service Worker・manifest の追加、nginx・Dockerfile・deploy.yml・backend の変更。
- コード分割（lazy）を足したときの chunk 読み込み失敗への対処。今は lazy が0件のため要らない。

## 5. 受入条件（○×で判定）

- K1: 今の名前と取り直した名前が違うとき、表に戻った1回目の確かめで知らせが出る（単体試験）。
- K2: 名前が同じなら知らせは出ない。60秒以内の2回目は fetch しない（単体試験で fetch 回数を数える）。
- K3: 裏にいる間は fetch しない。新しい版を見つけたあとは fetch しない（単体試験）。
- K4: 今の名前が取れないとき・fetch が失敗したとき、知らせは出ず、例外も投げない（単体試験）。
- K5: 「更新」を押すと reload が1回呼ばれる。押さない限り reload は呼ばれない（単体試験）。
- K6: 幅 390・1280 の写真で、知らせが上に出て、横のはみ出しが無く、ボタンの高さが 44px 以上（画面試験。写真を PO に見せる）。
- K7: npm run check:all と npm run build が通る。ja.json と en.json のキー数が一致する。
- K8（本番・PO）: この版を入れたあと、スマホのアプリを一度完全に閉じて開き直す（この仕組み自体を受け取るため）。その次に本番へ新しい版が出たとき、アプリに戻ると知らせが出て、押すと新しくなる。

## 6. 変更するファイル（見込み）

- 新規: frontend/src/hooks/useAppUpdateCheck.ts とその試験、frontend/src/components/AppUpdateNotice.tsx とその試験・CSS
- 変更: frontend/src/App.tsx（Toaster の隣に置く）、frontend/src/locales/ja.json、en.json
- 新規の画面試験: frontend/tests-e2e/visual-language/ に1本（幅 390・1280 の写真）
- この設計書: docs/handoff/app-update-notice/design.md

## 7. リスクと対処

- 入口の形が変わり main-*.js の名前が取れなくなる → 取れないときは何もしない（K4）。知らせが出ないだけで、壊れはしない。
- 入口を取りに行く回数が増える → 1人あたり最大で10分に1回と戻ったとき（60秒に1回まで）。入口は 1.3KB 程度。
- 新しい金型に当たるか（ADR-144）→ 既存の Callout と Button の組み合わせで作り、新しい見た目の決まりは足さない。ADR-144 の手続きが必要と分かったら、作業を止めて報告する。
- 最初の1回: この仕組みが入った版は、古い画面のアプリには届かない。PO に一度だけ完全に閉じて開き直してもらう（K8）。

## 8. 戻し方と測り方

- 戻し方: この PR を revert する。DB・サーバーは変えないので画面だけが戻る。
- 測り方: K1〜K7 は CI。K8 は次の本番の版が出たあとに PO の実機で確かめる。

## 9. 根拠となる決まり

- ADR-1016（戻ってきたときに動く流儀）、ADR-067（デザイン token）、ADR-027（文言は翻訳ファイル）、ADR-144（画面の部品の決まり）。

## 10. 設計審査（Opus 自己審査、独立した第二者レビューではない）

- 判定: APPROVE
- 確かめたこと: 既存の仕組みが無いこと（下調べの grep）、入口の no-cache と hash 付きの名前が本番で変わること（10:57 と 11:09 の実測）、置き場所が両方の殻に効くこと（App.tsx:154）、受入条件がすべて試験か実機で ○× にできること。
- 未解決: ADR-144 で新しい金型の扱いになるかは実装担当が条文で確かめ、当たるなら止まる。
