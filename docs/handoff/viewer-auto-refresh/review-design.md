# 設計審査 — 閲覧ページを再読み込みなしで1分ごとに新しくする

- 対象: `docs/handoff/viewer-auto-refresh/design.md`・`docs/handoff/viewer-auto-refresh/recon.md`（ブランチ release/viewer-auto-refresh、HEAD ee0a8b74a）
- 審査: Architect（Opus）、2026-10-22
- 判定: **REVISE**（Blocking 3件。方式 A そのものは妥当。直しは文書と §3-3 のコード1行、K6 の定義だけ）

---

## 照合できた事実（問題なし）

- recon の引用は、次の1か所（B3）を除き実物と一致した。
  - `frontend/src/pages/viewer/ViewerApp.tsx:65-80`（load）・`:71`（loading にする）・`:75-77`（clearToken）・`:78`・`:38-47`（screenForError）
  - `frontend/src/pages/viewer/InventoryView.tsx:1`・`:55`・`:57-71`・`:99`・`:104`・`:205`・`:323`
  - `frontend/src/hooks/useExpiryRefresh.ts:13-46`、`frontend/src/pages/viewer/api.ts:76-80`（fetchInventory）・`:35-43`（ViewerApiError）
  - `backend/app/routers/viewer.py:234-246`（Cache-Control no-store、503 viewer_inventory_not_ready）
  - `backend/app/middleware/rate_limit.py:30`・`:34`、`backend/app/auth/viewer_tokens.py:39-44`（claims に email なし）
  - `backend/app/celery_app.py:188-192`、`nginx/nginx.conf:8`・`:217-219`、`backend/app/routers/realtime_events.py:58-71`
  - `docs/adr/ADR-1019-inventory-viewer-separate-accounts.md:23`・`:25`、`docs/handoff/gas-viewer-fresh-fast/design.md:217`・`:328`・`:331`・`:590`、`docs/handoff/realtime-standard/design.md:116`、`frontend/src/locales/viewer/ja.json:11`、`frontend/src/pages/viewer/viewerFilter.ts:83`、`backend/app/services/tcg_distribution_svc.py:45`
- §3-1 のフックと §3-2 の refresh を ViewerApp.tsx に差し込んだ写しを、本店 checkout の eslint（eslint-plugin-react-hooks 7.1.1、`frontend/eslint.config.js` で有効なのは rules-of-hooks と exhaustive-deps だけ）で stdin 検査した。警告0・エラー0。render 中の `refreshRef.current = refresh` は前例 `frontend/src/hooks/useExpiryRefresh.ts:19-20` と同じで、この設定では指摘されない。
- InventoryView の state は残る。描画は `frontend/src/pages/viewer/ViewerApp.tsx:135-139` で key なし・同じ位置の条件付き描画なので、`{name:"inventory"}` のまま data だけ替われば再マウントされない。ページは `frontend/src/pages/viewer/InventoryView.tsx:104` で丸められる。mobile の Drawer（`:346-399`）の開閉も state なので残る。
- `setScreen((prev) => ...)` の関数形式で、途中でログアウト等により画面が替わっていれば上書きしない。`refreshing` は useRef なので再描画をまたいで重複を防ぎ、finally で戻る。React 18 では unmount 後の setState は警告も害も無い。
- 他の画面では止まる。`useViewerAutoRefresh(screen.name === "inventory", …)` なので passwordChange・notice・loading・login では enabled=false、effect の片付けで clearInterval される。401 で login に替わった時点でも止まる。

---

## Blocking

### B1. §3-3 の `useMemo(() => Date.now(), [data])` は lint 警告になり、コミットできない
- 根拠（実測）: 変更後の InventoryView.tsx を `eslint --stdin` で検査した結果
  `55:41 warning React Hook useMemo has an unnecessary dependency: 'data'. Either exclude it or remove the dependency array react-hooks/exhaustive-deps`
- lint-staged は `eslint --max-warnings=0`（`frontend/package.json:54-56`）なので、この警告1件でコミットが止まる。§4 の想定分岐「lint が useMemo(Date.now) を指摘した → 停止」が必ず起きる。Generator が確実に止まる設計はカードとして未完成。
- 直し方（Planner が1つ選んで §3-3 に変更後コードを書く）:
  - 案a: 1行上に `// eslint-disable-next-line react-hooks/exhaustive-deps -- data が替わるたびに「今」を取り直すため` を付ける（同じ書き方の前例: `frontend/src/pages/viewer/InventoryView.tsx:100`）。
  - 案b: ViewerApp で受け取った時刻を screen に持たせ（`{ name: "inventory", data, fetchedAt: Date.now() }` を非同期の中で作る）、InventoryView に `now` を props で渡す。render 中に Date.now() を呼ばないので純粋。ただし load() にも手が入るので §3-2「load() は変えない」を書き直すことになる。
  - どちらでも T8 はそのまま使える。

### B2. K6（KGI）の「解析が終わってから」の起点が決まっておらず、○×で判定できない
- 根拠: 作り置きは、未完了の analysis_runs（安全装置 #8）か未完了の extraction_jobs（pending・running・extracted、安全装置 #8b）が1件でもあると書かれない（`backend/app/services/tcg_distribution_svc.py:894-935`、`backend/app/tasks/viewer_inventory_cache.py:79-84`、`docs/adr/ADR-1019-inventory-viewer-separate-accounts.md:25`）。
  - そのため「ある投稿の解析が終わった時刻」から数えると、ほかの投稿の解析が続いている間は2分を超える。この画面側の変更では縮められない。
  - 作り置きの時刻は、書き込みに成功した時刻（`backend/app/tasks/viewer_inventory_cache.py:87`）。60秒ごとの起動に作り直しの所要時間が足されるので、理屈の最大は「60秒＋作り直しの時間＋60秒」で、120秒をわずかに超えうる【推測：作り直しの所要時間は実測していない】。
- K6 の検証方法に「和で判定する」と「照らし合わせる」の2つが並んでいて、合格の線が書かれていない（`docs/handoff/viewer-auto-refresh/design.md:186`）。
- 直し方:
  - K6 の起点を「解析待ち（未完了の analysis_runs と extraction_jobs）が0件になった時刻」と定義する。合格の線（例: その時刻から、その行が画面に出るまで120秒以内、を1件以上）を1つに決める。測り方（DB の読み取りで起点時刻を取る。前例 `docs/handoff/gas-viewer-fresh-fast/design.md:328`）も書く。
  - §7 リスクに「解析が続いている間は作り置きが止まるため、2分を超える。画面側では縮められない」を足す。ADR-1019 改訂 7-2 の文案（`docs/handoff/viewer-auto-refresh/design.md:135`）の「最大2分」にも同じ条件を付ける。
  - PO が承認した成功条件の意味が「ほかの解析が続いていても2分」だった場合は、この方式だけでは届かない。その場合は進めずに PO に確認する（KGI は PO の決め事）。

### B3. 実在しないファイルを引用している（ゲートが落ちる）
- recon.md:38-39 と design.md:26 が backend/app/services/viewer_inventory_cache.py（無いファイル）を引用している。実物は `backend/app/tasks/viewer_inventory_cache.py`（`git ls-files` で確認。services 側は無い）。行番号（:87 updated_at、:79-84 hold）は tasks 側の中身と一致する。
- バッククォート内のパスは `scripts/check-process-artifacts.js:436-469` が実在を確かめ、無ければエラーにする。PR の段で必ず赤になる。
- 直し方: 3か所のパスを `backend/app/tasks/viewer_inventory_cache.py` に直す。

---

## Non-blocking

1. 「DB は読まない」は事実と違う（`docs/handoff/viewer-auto-refresh/design.md:25`・`:191`）。在庫の取得は `require_viewer_password_ok` を通り、毎回 public.viewer_accounts を主キーで1行読む（`backend/app/auth/viewer_dependencies.py:3-4`・`:47-56`・`backend/app/routers/viewer.py:235`）。負担は小さいので方式は変わらない。ただし文言は「在庫は Redis の作り置きを返す。DB は閲覧者の確認で主キー1行だけ読む」に直す。§6 の「同じ理由は当てはまらない」の根拠もこの形に合わせる。
2. 403 のうち、待っても直らないもの（viewer_suspended・viewer_trial_expired・password_change_required。`frontend/src/pages/viewer/ViewerApp.tsx:42-44`）まで「表を出したまま」にしている。止められた閲覧者が、古い表を開いたまま見続けられる（新しいデータは届かない）。load() と同じく screenForError の画面に切り替えるか、今の扱いのままにするなら「止められた人も表は残る」を §3-2 に明記して PO に見える形にする。どちらにするかは Planner が判断する。
3. §2 の対象に `frontend/src/pages/viewer/InventoryView.test.tsx`（T8 を足す先、§4 の4）が入っていない。足す。
4. T5 の書き方を具体にする。
   - 「読み込み中が一度も出ない」は、2回目の fetchInventory を解決前の Promise にしておき、その間に `queryByTestId("viewer-loading")` が null であることを見る。
   - 2回目にしか無い行は、件数の表示（`viewer-pagination-label`、`frontend/src/pages/viewer/InventoryView.tsx:336-337`）か、その行の文字で確かめる。
   - `import "./i18n"`（前例 `frontend/src/pages/viewer/InventoryView.test.tsx:13`）を入れる。api の vi.mock は `importActual` で ViewerApiError を本物のまま残す（T6・T7 の instanceof のため）。
   - フェイクタイマーでは `await vi.advanceTimersByTimeAsync(60_000)` を使う。
5. この worktree には `frontend/node_modules` が無い（eslint の実行で `eslint-plugin-storybook` が見つからずに落ちた）。§4 の5の前に `cd frontend && npm ci` を足す。
6. HoverCard はモジュール内の state を持つ（`frontend/src/components/HoverCard.tsx:47-54`）。rowKey は位置（`frontend/src/pages/viewer/InventoryView.tsx:323`）なので、マウスを乗せている間に差し替わると、出ているカードの題名が下の行と食い違うことがある【推測：実機で確かめていない】。見た目だけの小さな問題として §7 に1行書いて受け入れるのでよい。
7. ADR-1016 決定1（`docs/adr/ADR-1016-realtime-change-signal-standard.md:14`、即時反映は SSE 1本）との関係が、ADR 側には書かれない。ADR-1019 改訂 7-2 の文案に「本体アプリの即時通知（ADR-1016）は閲覧者のトークンでは使えない（決定4）ため、閲覧ページはその対象外」を一言足すと、後で読む人が迷わない。
8. 裏のタブから戻った直後に保留分で1回読み、そのすぐ後にいつもの60秒ごとの回が来ると、短い間に2回読むことがある（`docs/handoff/viewer-auto-refresh/design.md:64-76`）。害は無い。T3 の期待（戻ったときに1回）とも食い違わない。
9. 回数の制限は人数ではなく、同じ IP の未認証扱いの全リクエスト（タブの数を含む）で数える（`backend/app/middleware/rate_limit.py:97-102`）。§1・§7 の「60人未満」は「同じ IP から開いているタブが合わせて60未満（ログイン等の他の呼び出しを含む）」と書き直す。
10. 開いている間にトークンの期限が切れると、次の読み直しで 401 になり、ログイン画面に自動で戻る。今は再読み込みするまで古い表が残っている。動きが変わることを §3-2 に1行書く。

---

## 他の確認項目

- 受け入れ基準: K1〜K5・K7 は○×で判定できる。K6 は B2 を直せば判定できる。
- テスト: T1〜T4（フェイクタイマーと document.hidden の defineProperty）、T6・T7、T8（`rerender` で新しい data オブジェクトを渡す。freshOnly の既定は true、`frontend/src/pages/viewer/InventoryView.tsx:61`）は今の仕組みで作れる。T5 は Non-blocking 4 を入れれば迷わない。
- ADR との整合:
  - 入口は7本のまま（ADR-1019 決定5）。作り置きは1分ごとのまま（決定7）。backend・nginx は触らない。
  - 新しい UI 部品・文言・色は足さないので、ADR-144・ADR-067・ADR-027 に触れる変更は無い。
  - 「更新ボタンは付けない」（`docs/handoff/gas-viewer-fresh-fast/design.md:217`）も守られている。
- 触らない範囲（§2）は明確。

## 再審査で見ること
- B1: §3-3 の変更後コードが lint 警告0になること（同じ stdin 検査を再実行する）。
- B2: K6 の起点・合格の線・測り方が1つに決まっていること。ADR 文案と §7 に条件が入っていること。
- B3: 引用パスが実在すること。
