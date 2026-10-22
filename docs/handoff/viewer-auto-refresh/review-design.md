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

---

## r2

- 対象: 同じ2文書（HEAD cc06febde）
- 審査: Architect（Opus）、2026-10-22
- 判定: **REVISE**（Blocking 2件。どちらも文書だけの直し。コードの形と方式は合格）

### r1 の Blocking の確かめ

- B1 解消（実測）。§3-1〜§3-3 のコードを写しに当て、本店 checkout の eslint で stdin 検査した。
  - 写し: `frontend/src/pages/viewer/ViewerApp.tsx`（import・STOP_DETAILS・refresh・フック呼び出しを足したもの）、`frontend/src/pages/viewer/InventoryView.tsx`（:55 を §3-3 の変更後に置き換えたもの）、新規の useViewerAutoRefresh.ts。
  - 結果: 3つとも `--max-warnings=0` で警告0・エラー0（exit 0）。
  - 対照として、disable の1行だけを抜いた InventoryView の写しでは `57:41 warning React Hook useMemo has an unnecessary dependency: 'data'` が出た。検査が効いていることも確かめた。
  - 型: 写しを入れた frontend の複製で `tsc --noEmit -p .` を実行した。`src/pages/viewer` のエラーは0件。出たエラー5件は、viewer の外にある生成物の未作成（api/generated/schema）と本店 node_modules に無い @xyflow/react によるもの。複製の環境が原因で、今回の変更とは関係ない。`screenForError` の戻り値は Screen（`frontend/src/pages/viewer/ViewerApp.tsx:38`）で、`setScreen((prev) => (prev.name === "inventory" ? next : prev))` は Screen を返すので型が合う。
- B2 一部解消。起点（解析待ち0件の時刻）と合格の線（終点−起点 ≦ 120秒、1件以上）は1つに決まった（`docs/handoff/viewer-auto-refresh/design.md:207`）。§7（`docs/handoff/viewer-auto-refresh/design.md:217-218`）と ADR 文案 7-2（`docs/handoff/viewer-auto-refresh/design.md:149`）にも、ほかの解析が続く間は作り置きが書かれない、という条件が入った。ただし測り方が書かれていない（下の B2-r2）。
- B3 一部解消。r1 で挙げた services 側のパスは3か所とも tasks 側に直っていた。ただし recon に、ゲートで落ちる引用が1つ残っている（下の B3-r2。r1 の審査で見落とした）。

### Blocking

#### B3-r2. recon.md のワイルドカード入りパスがゲートで落ちる
- 根拠（実測）: `scripts/check-process-artifacts.js:412-470` の関数をそのまま読み込んで recon.md に当てた。結果は `❌ frontend/src/pages/viewer/*.test.tsx — ファイルが存在しません`。recon.md:51 のバッククォート内のワイルドカード（*.test.tsx）を、実在するファイル名として調べるため。recon の引用検査は `scripts/check-process-artifacts.js:682` で必ず走る。
- 直し方: recon.md:51 のバッククォートを外す（例: frontend/src/pages/viewer/ の *.test.tsx）。または実在するファイル（`frontend/src/pages/viewer/InventoryView.test.tsx` など）を並べる。
- design.md で同じ検査に引っかかるのは、新しく作る3ファイル（useViewerAutoRefresh.ts・useViewerAutoRefresh.test.ts・ViewerApp.test.tsx）だけ。どれもこの PR で作るので、PR の段では実在する。design.md の冒頭注記（:1-3）の決まりにも合っている。review-design.md の引用は全部実在した（`git ls-files` と照合）。

#### B2-r2. K6 の測り方（起点と終点の時刻をどう取るか、誰が測るか）が書かれていない
- 根拠: `docs/handoff/viewer-auto-refresh/design.md:207` は起点と終点の定義だけで、時刻の取り方が無い。r1 B2 の直し方で求めた「DB の読み取りで起点時刻を取る（前例 `docs/handoff/gas-viewer-fresh-fast/design.md:328`）」が入っていない。
  - 起点は、未完了の analysis_runs（completed_at IS NULL）と extraction_jobs（pending・running・extracted）が0件になった瞬間（`backend/app/services/tcg_distribution_svc.py:897-935`）。後から1回 DB を読んでも、0件になった瞬間は分からない。決めずに測ると、測る人によって起点がずれる。
  - 終点の「最終更新の時刻がその起点より後になった時刻」も、画面を見て時刻を書くのか、通信記録の応答時刻を使うのかが決まっていない。
- 直し方: K6 の検証方法に次の3つを足す（Planner が決める。例を書く）。
  - 起点の取り方。例: Evaluator が閲覧用の読み取りで、上の2つの未完了件数を10秒ごとに読み、初めて両方0件になった読み取りの時刻を起点にする（生の出力を残す）。
  - 終点の取り方。例: 開いたままの閲覧ページの通信記録で、updated_at が起点より後の `GET /api/v1/viewer/inventory` 応答を受けた時刻を終点にする。
  - 測る人。K5 と同じく Evaluator。試験アカウントが使えなければ PO の目視に回す。

### Non-blocking の確かめ

- N-1 反映済み（`docs/handoff/viewer-auto-refresh/design.md:25`・`:212`）。引用先の `backend/app/auth/viewer_dependencies.py:47-56` は public.viewer_accounts を id で1行読む処理で、実物と一致した。
- N-2 反映済み。STOP_DETAILS の3つ（viewer_suspended・viewer_trial_expired・password_change_required）は `frontend/src/pages/viewer/ViewerApp.tsx:42-44` の detail 名と1字違わず一致した。行き先を load() と同じ screenForError で決めるので、停止・期限切れの案内とパスワード変更画面に行く。
- N-3 反映済み（`docs/handoff/viewer-auto-refresh/design.md:33`）。
- N-4 反映済み（`docs/handoff/viewer-auto-refresh/design.md:167-172`）。`viewer-pagination-label` は `frontend/src/pages/viewer/InventoryView.tsx:337` にある。`import "./i18n"` は `frontend/src/pages/viewer/InventoryView.test.tsx:13` にある。
- N-5 反映済み（`docs/handoff/viewer-auto-refresh/design.md:186`）。
- N-6・N-8 反映済み（`docs/handoff/viewer-auto-refresh/design.md:219-220`）。
- N-7 反映済み（`docs/handoff/viewer-auto-refresh/design.md:149`）。
- N-9 反映済み（`docs/handoff/viewer-auto-refresh/design.md:25`・`:216`）。`backend/app/middleware/rate_limit.py:97-102` は IP 単位の数え方で、実物と一致した。
- N-10 反映済み（`docs/handoff/viewer-auto-refresh/design.md:125`）。「12時間」は `backend/app/auth/viewer_tokens.py:16`（12 * 3600）と一致した。
- T9（`docs/handoff/viewer-auto-refresh/design.md:181`）: 「NoticeView の suspended」は、kind の型（`frontend/src/pages/viewer/types.ts:56`）と NoticeView の分岐（`frontend/src/pages/viewer/NoticeView.tsx:18`）にある名前と一致した。画面の目印は `viewer-notice-suspended`（`frontend/src/pages/viewer/NoticeView.tsx:30`）で確かめられる。403 では clearToken を通らない（§3-2 の条件は 401 と "invalid viewer token" の両方）ので、T9 の「clearToken は呼ばれない」も設計どおり。

### Non-blocking（r2 で新しく見つけたもの）

1. §3-2 の refresh 冒頭コメント（`docs/handoff/viewer-auto-refresh/design.md:93`）は「トークンが無効（401）ならログイン画面へ戻す」だけで、STOP_DETAILS で案内画面に切り替える場合が書かれていない。コードと食い違うので、「401 と、待っても直らない失敗（STOP_DETAILS）は画面を切り替える」に直すとよい。

### 再審査で見ること（r3）
- B3-r2: recon.md を `scripts/check-process-artifacts.js` の引用検査に当てて、エラーが0件になること。
- B2-r2: K6 の検証方法に、起点の取り方・終点の取り方・測る人が1つずつ書かれていること。
