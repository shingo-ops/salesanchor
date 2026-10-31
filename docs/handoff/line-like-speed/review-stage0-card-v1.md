HEAD: 74ed6470964fb8429741bb5190d42082980f1dab（origin/release/line-like-speed-stage0。依頼どおり 74ed64709）
判定: REVISE

# 段 0a 実装カード 第 1 版の審査（クラウドの Claude Opus・設計審査役）

- 基準: origin/main = 9e202335936921ad6a7f83bee0847cd09e987776（カードの S=9e2023359 と同じ）。
- 審査した物: docs/handoff/line-like-speed/stage0-card.md（全 564 行）、`git diff 9e2023359 HEAD -- docs/handoff/line-like-speed/design.md`（§3-4 段 0・§3-5 K1・K3 の 3 行）、design.md §1〜§3-4、ADR-1051・ADR-1053・ADR-1054。
- 実際に動かして確かめたこと（本番には繋いでいない。秘密情報の環境変数 SMOKE_E2E_EMAIL・SMOKE_E2E_PASSWORD が空であることを確かめてから流した）:
  - カードの §4-A 全文と §4-B の直しを、作業用の写し（スクラッチの置き場。リポジトリの外）に当てて tsc --strict（lib dom）で型検査 → 誤り 0。
  - 同じ写しで playwright test（page-speed.config.ts と同じ設定に、置いてある chromium の場所だけ足した写し）→ 5 回とも「記録係の精度」1 passed・本体 1 skipped。
  - 精度の試しの値と、わざと壊した記録係で落ちるか、描かれた時刻（Element Timing）との差、を別の試しで測った（数は各項目に書く）。
  - 作業用の写しはリポジトリに入れていない。

## 1. カードの S の行番号の引用 — × （ずれ 1 件・範囲の不足 1 件。ほかは一致）

| カードの引用 | 実物 | 判定 |
|---|---|---|
| page-speed.spec.ts :1-323 | 323 行 | ○ |
| :13（settle の import） | :13 `import { isTrackedApi, trackApi, waitSettled ...} from "./settle"` | ○ |
| :21 | :21 `const OUT_FILE` | ○ |
| :30 Status・:31-42 Row | :30・:31-42 | ○ |
| :72-79 goInApp | :71 は説明の行、:72-79 が本体 | ○ |
| :106-118 emptyRow | :106-118 | ○ |
| :156-199 render・:170-197・:181・:197 | :156-199・:170 `const line`・:181 最後の説明の行・:186-187 見出しと区切り・:197 `ログイン関係の 429` | ○ |
| :201 test・:203 skip | :201・:203 | ○ |
| :216-242 関所・:225-232 判定・:233-235 数える行・:242 終わり | 同じ | ○ |
| :252 403 を数える行 | :252 | ○ |
| :291-312・:311 秒の式・:312/:313・:319・:321 | :291 navStart・:311 式・:312 else の閉じ・:313 rows.push・:319 for の閉じ・:321 render 呼び出し | ○ |
| settle.ts:13-14 LOADING_SELECTOR | :13-14 | ○ |
| page-speed.config.ts :5・:27・:34-37・:36 | :5 動画を作らない旨・:27 `video: "off"`・:34-39 projects（:34-37 は途中まで）・:36 name 行、`devices["Desktop Chrome"]` は :37 | △（:36 は :37。中身は合う） |
| page-speed-targets.ts 135 件・kind "" 95 件 | 135 件 ○。kind "" は **94 件**（"" 94・section 25・needs-id 10・carrier 3・redirect 3）。95 は :8 の型の行 `kind: "" \| "carrier" \| "section"` を数えた数と一致 | **×**（カード :21・:44） |
| DesktopShell.tsx:400 main.app-content | :400 | ○ |
| DesktopShell.tsx:228-322 a.sidebar-item | :228 最初の NavLink〜:322。ただし a.sidebar-item は :329 /sales・:342 /commissions・:353 /management-center・:365-378 SaaS 管理者の項目まで続く | △（範囲が足りない。:228-378） |
| :87-94 a.sidebar-sub-item・:70-74 button・:84 isExpanded && isOpen | 同じ | ○ |
| :148-152 leave・:154-158 enter | 同じ | ○ |
| MobileShell.tsx:201 main.mobile-content | :201 | ○ |
| ADR-1051:25 | :25 trace・スクリーンショット・html レポートを作らない | ○ |
| prod-ui-check.yml:146 | :146 `continue-on-error: true` | ○ |

## 2. V0-1（動画をやめ、試しのページで差 50 ms 以内） — 一部 ×

- ADR-1051 と矛盾しないか: ○。試しのページは page.setContent だけで通信が無い（カード :193-195・:203）。動画・trace・スクリーンショットを作らない（ADR-1051:25、page-speed.config.ts:25-27）。
- 測っている物: 「ページの中の時計で書き換えた時刻 → 記録係が見たコマの時刻」と「pointerdown の時刻 → MutationObserver の時刻」。どちらもページの中の performance.now だけで比べている: ○（カード :220・:225・:243・:129）。
- 合格線 50 ms の厳しさ（実測）:
  - カードのままの試し: 9 回流して 4/4 合格、いちばん大きい差 8.8〜24 ms。headless の requestAnimationFrame は 500 ms で 31 コマ（約 60 コマ/秒）。
  - 歯があるか: 記録係の毎コマを setTimeout 200 ms に変えると 1/4 合格（差 112 ms）。pointerdown の時刻を Date.now に変えると 3/4 合格。→ 見る間隔の粗さと時計の取り違えは捕まえる。甘すぎではない。
  - **捕まえられない物（×）**: 書き換えた時刻は「描かれた時刻」ではない。記録係の時刻は requestAnimationFrame の中（描く前）。重い DOM（影とぼかし付きの要素 20000 個）で、記録係は書き換えの 13 ms 後と出したが、Element Timing の描かれた時刻（renderTime）は 4184 ms 後だった。200 個で 35〜46 ms、2000 個で 259〜296 ms 後。設計 §3-4 の段 0 の元の線（動画のコマ＝描かれた時刻と比べる）の目的「記録係の時刻が正しいこと」に対して、カードの試しは描く時間を見ていない。
  - 直す形（実測済み）: 試しの正解を Element Timing の renderTime（描かれた時刻・本番に繋がない試しのページでだけ使う）にし、記録係のコマの時刻を requestAnimationFrame の中から MessageChannel で投げた後の時刻（その回の描く手順の後）にする。この形で 4 回流して 4/4 合格、差 3〜4.5 ms（記録係が描かれた時刻より 2〜4.5 ms 早い）。→ 直す点 4。
- カード :9 の見出し「作る物と合格の線は変えない」は、V0-1 が段 0 の合格線を書き換えている（design.md diff の §3-4 段 0）ことと食い違う。→ 直す点 11。
- 同じページで runRecorderProbe を 2 回続けて呼ぶと 2 回目は 3/4（4 回とも再現）。`if (window.__saRec) return;`（カード :90）が setContent の後も残るため（推測を含む。原因の行は未確認）。カードは毎回新しいページで呼ぶので今の手順では起きない。→ 直す点 13。

## 3. §4-A の TypeScript と記録係の文字 — ○（型検査・実行とも通る。注意 2 点）

- declare global と import の併用: ○（import があるのでモジュール扱い。tsc --strict で誤り 0）。
- page.evaluate に文字を渡す形（カード :204）: ○（実行して記録係が入った）。
- page.waitForFunction(fn, arg, { timeout, polling: 100 })（:157-161・:171-174・:389-397）: ○（型・実行とも通る）。
- MutationObserver の絞り込み（:124-128）: ○。document 全体を見て、中身の場所の中の変化だけ時刻を残す。試しの「押した時」で 4/4。
- pointerdown の Event.timeStamp と performance.now: ○（同じ時計で差 ≤24 ms。Date.now に替えると落ちることで確かめた）。MDN の出典は未確認（実装役の §3(d) に残す）。
- 構造の印が文字・値を読まない: ○（tagName と classList だけ・:106）。外に出るのは「数:要素数」の文字だけで、表には出ない（§4-B(j)）。ただし classList はデータで変わるクラス名を含みうる（数に縮めるだけで外には出ない）。
- 注意 1（×・設計との矛盾）: 設計 §3-2 は「Spinner は LOADING_SELECTOR に入っていないので K1 を邪魔しない」と書く（design.md §3-2 の Spinner の行）。しかし V0-2 の「構造の印が最初と同じ」では、段 2 以降の取り直し中に見出しへ足される span.sa-spinner（frontend/src/components/loading/Spinner.tsx:30・:33）で構造の印が変わり、取り直しが終わって Spinner が消えるまで一致しない。実測: カードの記録係では Spinner 1 個で印が変わる（same=false）。→ 段 2 で K1 が良くなっても数に出ない。→ 直す点 3（.sa-spinner を印から外す。実測で same=true・精度の試し 4/4）。
- 注意 2: 記録係の 1 コマの重さは、400 要素の画面で約 0.8 ms（1000 回の平均）。60 コマ/秒で中の仕事の約 5%。今の「秒」（S :311 の式）は変えないが、値が少し動きうる。→ 直す点 12（説明の行に書く）。

## 4. §4-B の差し込み位置と今の数への影響 — 一部 ×

- 差し込み位置: ○。§4-B の (a)〜(j) を S の行に当てて型検査が通り、今の 9 列・説明の行・秒の式（:311）・関所の判定（:225-232・:236-241）は消えない（差分の消える行は goInApp の 3 行・9 列の見出し 2 行と 1 行の式・:197・:234-235・:252・:321 だけで、どれもカードが書き換えると書いた行）。
- extra.on で数えない形:
  - 関所（:233-235）: ○。数える判定は await より前で同期なので、K1・K3 の間の止めた送信は合計にも行の「止めた送信」（:290・:297 の blockedTotal の差）にも入らない。
  - requestfinished（:252）: **×（小）**。`extra.on` を見るのは `await req.response()`（:248）の後。K1・K3 の通信の終わりが届く前に extra.on が false に戻ると今の合計に入る。普段は measureReturn・measureTap の最後の waitSettled（1 秒静か）で防がれるが、例外で抜けた時（カード :445-449・:471-475）は待たずに false に戻す。→ 直す点 5（入口で同期に読む）。
  - 行ごとの 403・API の数（:298-300）は hits の袋で数えるので、K1・K3 の間（hits = [] の後）は入らない: ○。
- addInitScript を login より前に置く: ○。挿入位置 :242 の次 → :266 の login より前。page.addInitScript はその後のすべての読み込みに効く（Playwright の決まり。出典の確認は実装役の §3(c)）。
- 精度の試しのページ（context.newPage）は関所（context.route）の下にあるが、setContent は通信しない: ○。ただし newPage と close は .catch の外で、失敗すると finally（:320-322）に届かず表が書かれない（:264 の try より前のため）。→ 直す点 13。
- rows と SPEED_TARGETS の 1 対 1: ○。:271-274（時間切れ）・:279-282（番号なし）・:313（測れた）・:314-318（例外）のどの道も 1 件ずつ push。K1 は :313 より前に自分の try/catch で囲む（カード :441-452）。

## 5. measureReturn（K1）と measureTap（K3） — ×

- K1 の手順は設計 §3-5（A→B→A・goInApp の時刻から LOADING_SELECTOR 0 個かつ A の部品の最初のコマ）と合う: ○。時計はどちらもページの中の performance.now（カード :315・:120）。
- B の選び方（:338）: △。ほぼすべての画面で B が SPEED_TARGETS の最初の kind "" = "/"（page-speed-targets.ts:16）になる。点検用の人は多くの画面が 403（ADR-1053 Evidence の tradeoff）。"/" と A がともに断りの画面で同じ形なら「見分けられず」が増える（本番で未確認）。また重い画面を 135 回開くことになる（"/" の重さは未確認）。→ 直す点 7（その回で測れた・403 なしの最も速い画面を B にする）。
- 見分けられない時の訳: ○（:339-348・:356-358）。ただし `want === ""`（中身の場所が無い）も「行き先と同じ形」になり訳が合わない。→ 直す点 11。
- 403 の画面の K1 は、中身ではなく断りの画面が戻る秒になる。表は 403 ありの行を別にまとめる（S :167・:189）ので読み分けはできるが、説明の行が無い。→ 直す点 11。
- K3 の横のメニュー: **×**。
  - まとめ（アコーディオン）は今は描かれない: `const moreItems: NavItem[] = [];`（DesktopShell.tsx:201）で、SidebarAccordion は `items.length === 0` なら null（:66）。カード V0-3 の「中の項目は、まとめを開かないと描かれない」の道は今は通らない（コードは害なし）。
  - 押せる項目は a.sidebar-item だけ: / (:227 dashboard.view)・/schedule・/lead-chat・/inventory (:269 products.view)・/orders・/sales・/commissions (:314・:327・:340 orders.view)・/management-center (:351)・SaaS 管理者だけの 4 項目 (:194-199)。このうち kind "" の画面は最大 7 件（/crm・/management-center は kind "" に無い）。点検用の人に権限が無ければさらに減る（未確認）。
  - → 設計 §3-4 段 0 の合格線「135 画面の K1・K3 の基準値が記録に出る」に対し、K3 の数は最大 7 画面で、残り 87 件以上は「メニューに無い」。カードは「合格の線は変えない」と書きつつ、A6（:548）で訳を数に数えて実質線を下げている。→ 直す点 2（設計担当が決めて design §3-4 を直す）。
- 横のメニューの開き方: ホバーで広がる（:154-158）・押した後の抑止（handleSidebarNavClick）・離れると戻る（:148-152）とカードの指の動かし方（:385-386・:405-406）は合う: ○。
- 押す前の静けさの待ち（:388-398）と判定（:411）: ○（同じ 1 秒の決まり）。
- メニューに無い画面の扱い: ○（:381-384）。点検用の人に出ない項目も同じ訳になり、「本当に無い」と「権限で出ない」を分けられない（ゆがみは小さいが説明に書く）。→ 直す点 2 に含める。
- K3 は本体の for の後に回すので、すべて 2 回目以降（部品は読み込み済み）の押した秒になる。設計 §3-5 の K3 に「初回か」の決まりは無いので矛盾ではない。説明の行に書くとよい（直す点 11）。

## 6. 時間 — 未確認（見込みは立つが、守りが無い）

- 「今の段は約 3 分 16 秒」は依頼文の値。リポジトリの中では確かめられなかった（未確認）。この値なら 1 画面平均 約 1.45 秒（196÷135）。
- waitSettled は 1 回につき最短 500 ms、かつ最後の通信から 1000 ms 静か（settle.ts:96-97・:113）。
- 見込み（推測を含む）:
  - K1: 1 画面につき B を開く waitSettled 1 回＋A へ戻る waitMatch と waitSettled 1 回 ≒ 2×1.45 秒 → 135 画面で約 6.5 分。
  - K3: 最大 7 画面 ×（静けさ 1 秒＋押して開き終わり 約 1.5 秒＋変化待ち）≒ 30 秒以内。残りは「メニューに無い」で数ミリ秒〜（まとめが描かれないので 1 秒待ちは起きない）。
  - 合計の見込み 約 10〜11 分。40 分（S :19）・試験の上限 45 分（page-speed.config.ts:19）・段の 46 分（prod-ui-check.yml:149）に収まる。
- 悪い時: 全画面が「10 秒で見分けられず」なら K1 だけで 135×(1.45+10+1.45) ≒ 29 分 → 合計 約 33 分。さらに B や A が 45 秒の上限（S :17）に当たると 40 分を超えうる。
- **×（守りの不足）**: K1 は本体の for の中にあり、40 分の判定（S :271）は各画面の始めだけ。K1 が遅いと、今の秒（K2 の基準）の残りの画面が「時間切れで未測定」になる。今の記録（ADR-1053）を K1 が削る形。→ 直す点 6（K1 に自分の上限を付ける）。

## 7. 秘密と公開 — ○

- 新しい 3 列は sec2 の数・「—」・ExtraNote の決まった言葉だけ（カード :487・:295-305）。構造の印の数は sigNow の中だけで使い、render に渡さない（:337・:345）。
- 精度の試しの行は件数と ms（:492）。メモリは MB の数か「測れず」（:499）。
- needs-id の番号は url の中にあるが、K1 は url を表に出さない（row.route は S :296 の形のまま）。
- 試しのページの文字 "probe"・"x" は試しのページの中だけ。

## 8. card-lint と手順の命令 — 一部 ×

- `bash scripts/card-lint.sh docs/handoff/line-like-speed/stage0-card.md` の出力（そのまま）:
  ```
  L24 警告 1行200字超が 31件（閾値は暫定・止めない）
  ```
  終了コード 0。
- NODE_PATH の形と config の場所: ○。リポジトリの根から `NODE_PATH="$(git rev-parse --show-toplevel)/frontend/node_modules" ./frontend/node_modules/.bin/playwright test --config <設定>` で tests/prod-check/page-speed.spec.ts が読めて 1 skipped（prod-ui-check.yml:152・:156 と同じ形）。
- 手順2 `npm ci`: ○（このクラウドで通った）。
- 手順2 `npx playwright install chromium`: 未確認（このクラウドの決まりで流していない）。このクラウドの @playwright/test は 1.59.1 で chromium_headless_shell-1217 を探すが、置いてあるのは /opt/pw-browsers/chromium_headless_shell-1243 で、何もしないと「Executable doesn't exist」で 2 件とも失敗した（本体の test も page を作る所で落ち、skip にならない）。リポジトリの外に置いた一時の設定で launchOptions.executablePath を 1243 に向けると 1 passed・1 skipped。→ 直す点 9。
- **手順1 は fetch だけで、ブランチへ移っていない**（カード :511）。そのまま作ると main の上に commit し、手順8 の `git push -u origin HEAD:release/line-like-speed-stage0`（:529）は fast-forward でなく断られる。→ 直す点 8。
- §4-E（:533）の「new-worktree.sh は使わない」は、クラウドの決まり scripts/agent-hooks/cloud/rules.md:15（ファイルを変える前に new-worktree.sh で作業場所を作り、push 済みの枝は git switch -C で先頭に合わせる。git worktree add で直接作ると push の前の検査が止める）と食い違う。カード :5 が読んだという guards の文書との照合は未確認。→ 直す点 8。
- 手順6: 試験を流すと tests/prod-check/test-results/.last-run.json ができ、.gitignore に入っていない（`git check-ignore` で無し。.gitignore:97 は frontend/test-results/ だけ）。git status に出る。→ 直す点 10。

## 9. 新しい抜け・矛盾・不明点と、渡せるか

- 渡せるか: **まだ渡さない（REVISE）**。コードは型・実行とも通り、本番に繋がない試しは歯もあるが、(1) K3 が最大 7 画面で設計の「135 画面の K3」と合わない（設計担当の決定が要る）、(2) 段 2 で Spinner が K1 を隠す、(3) 精度の試しが描く時間を見ない、(4) 手順1 でブランチへ移らない、の 4 点はそのままだと段 0 の目的か作業が成り立たない。
- 本番の読み取りが増える: K1 で 1 画面につき B と A を開き直すので、毎朝の本番への読み取りは今の約 3 倍（推測。各画面の通信の数は未確認）。ADR-1053 の Negative「135 画面ぶんの読み取りがサーバーの記録に混ざる」の量が変わる。ADR の改訂が要るかは設計担当が決める（直す点 14）。
- 点検用の人で 403 になる画面（ADR-1053 の未決 D2）の K1・K3 は中身の秒ではない（直す点 11 で説明に書く）。

## 直す点（REVISE）

1. **kind "" の数**: カード :21・:44 の「95 件」を「94 件」に。§3(b) の確かめる数も 94。
2. **K3 の対象（設計担当の決定）**: 今の横のメニューで押せる kind "" の画面は最大 7 件（DesktopShell.tsx:227-353。まとめは moreItems が空で描かれない :201・:66）。次のどちらかを決めて、カード V0-3・A6 と design.md §3-4 段 0 の合格線を同じ言葉にする。
   - (案A・推奨) K3 の基準は「横のメニューにある画面（点検用の人で最大 7 件）」とし、design §3-4 の段 0 を「135 画面の K1 と、横のメニューにある画面の K3 の基準値」に直す。V0-3 に「まとめ（:70-74）は今は項目が無く描かれない（:201・:66）。まとめの道は将来の項目のために残す」と書く。「メニューに無い」は「メニューに無い（権限で出ない場合を含む）」にする。
   - (案B) 135 画面の K3 を別の押し方で測る道を設計する（画面の中のリンクなど）。この場合は段 0a から外して別の審査に出す。
3. **Spinner を構造の印から外す**（設計 §3-2 との矛盾を解く）。§4-A に足す（実測: Spinner の有無で印が同じ・精度の試し 4/4）:
   ```ts
   /** 構造の印に入れない部品（取り直し中の小さな印・design §3-2 の Spinner） */
   export const SIG_SKIP_SELECTOR = ".sa-spinner";
   ```
   RECORDER_SOURCE の定数に `const SKIP = ${JSON.stringify(SIG_SKIP_SELECTOR)};` を足し、sig の中の `const d = queue[i][1];` の次に:
   ```js
      if (el.matches(SKIP)) continue;
   ```
   V0-2 の定義に「.sa-spinner とその中は印に入れない（design §3-2）」と書き足す。
4. **精度の試しの正解を「描かれた時刻」にする**（V0-1 の目的＝記録係の時刻が描かれた時刻と合うこと）。実測: 下の形で 4 回 4/4・差 3〜4.5 ms。
   - 記録係の tick を、描く手順の後に時刻を取る形にする:
   ```js
     const ch = new MessageChannel();
     let pending = null;
     ch.port1.onmessage = () => {
       if (pending) keep(frames, { t: performance.now(), sig: pending.sig, loading: pending.loading });
       pending = null;
     };
     const tick = () => {
       pending = read();
       ch.port2.postMessage(0);
       requestAnimationFrame(tick);
     };
   ```
   - runRecorderProbe の戻った時の形で、A の中身に目印を足し、正解を Element Timing の renderTime にする（試しのページの中だけ）:
   ```ts
          const mark = '<p elementtiming="probe-a" class="a-mark">x</p>';
          main.innerHTML = mark + htmlA;
          const want = window.__saRec?.sigNow() ?? "";
          main.innerHTML = '<section class="b-page"><p class="b-line"></p></section>';
          const since = performance.now();
          setTimeout(() => {
            main.innerHTML = '<div class="sa-loading-block"></div>';
            setTimeout(() => {
              new PerformanceObserver((list, obs) => {
                for (const e of list.getEntries() as unknown as { identifier: string; renderTime: number }[]) {
                  if (e.identifier === "probe-a") {
                    obs.disconnect();
                    resolve({ since, want, changedAt: e.renderTime });
                  }
                }
              }).observe({ type: "element", buffered: false });
              main.innerHTML = mark + htmlA;
            }, 300);
          }, 200);
   ```
   差は `Math.abs(at - r.changedAt)` にする（記録係が描かれた時刻より数 ms 早く出るため）。
   - 限界を V0-1 に書く: 画面の外の描き（ラスタ）が重い時は記録係より遅れて描かれる（実測: 影とぼかし付き 2000 要素で約 0.24〜0.27 秒の差）。試しは軽い形だけを確かめる。
   - Element Timing が Chromium にあることは実装役の §3(d) に足す（MDN で確かめる）。
5. **requestfinished の数える判定を入口で同期に読む**（§4-B(e) の 2 つ目を差し替え）:
   ```ts
     page.on("requestfinished", async (req: Request) => {
       if (!isTrackedApi(req)) return;
       const bucket = hits;
       const counted = !extra.on;
       const res = await req.response().catch(() => null);
       ...
       if (status === 403 && counted) forbiddenApis.set(shape, (forbiddenApis.get(shape) ?? 0) + 1);
   ```
   （:246-247 と :248 の間に 1 行足し、:252 の条件を counted にする。A4 の「- が無い」は :252 の 1 行だけ例外と書く。）
6. **K1 に自分の時間の上限を付け、今の秒の 40 分を削らない**。§4-B(b) に `const K1_STAGE_LIMIT_MS = 25 * 60 * 1000;` を足し、§4-B(i) の K1 の差し込みを:
   ```ts
        if (row.status === "測れた" && !recorderOk) {
          row.k1Note = "精度の試しが不合格";
        } else if (row.status === "測れた" && Date.now() - stageStart > K1_STAGE_LIMIT_MS) {
          row.k1Note = "時間切れで未測定";
        } else if (row.status === "測れた") {
          extra.on = true;
          try {
            await measureReturn(page, api, rows, url, expected, row);
          } catch {
            row.k1Note = "エラー";
          } finally {
            extra.on = false;
          }
        }
   ```
   時間の見込み（§6 の見込み 約 10〜11 分・悪い時 約 33 分）と根拠（settle.ts:96-97・:113、S :17・:19）をカードに書く。A7 は「今の秒の列に『時間切れで未測定』が 0 行」と「K1 の『時間切れで未測定』の行数」を分けて書く。
7. **B の選び方**: その回で測れた・403 なし・kind "" の中で最も速い画面を B にする（"/" を 135 回開かない・断りの画面同士で同じ形になるのを避ける）。measureReturn の引数に rows を足し、:338 を:
   ```ts
     const kindEmpty = new Set(SPEED_TARGETS.filter((t) => t.kind === "").map((t) => t.route));
     const fast = rows
       .filter((r) => r.status === "測れた" && r.forbidden === 0 && r.seconds !== null && kindEmpty.has(r.route))
       .filter((r) => r.route !== url && r.route !== expected)
       .sort((a, b) => (a.seconds ?? 0) - (b.seconds ?? 0))[0];
     const other = fast
       ? { route: fast.route }
       : SPEED_TARGETS.find((t) => t.kind === "" && t.route !== url && t.route !== expected);
   ```
8. **実装役の作業場所と手順1**: クラウドの決まり（scripts/agent-hooks/cloud/rules.md:15）に合わせ、§4-E を書き直し、手順1 を次にする:
   ```
   cd "$(git rev-parse --show-toplevel)" && bash scripts/new-worktree.sh release/line-like-speed-stage0
   （作られた作業場所の中で）git fetch origin release/line-like-speed-stage0
   （同）git switch -C release/line-like-speed-stage0 origin/release/line-like-speed-stage0
   （同）git rev-parse HEAD origin/release/line-like-speed-stage0   ← 2 行が同じことを確かめる
   ```
   以後の手順の `cd "$(git rev-parse --show-toplevel)"` は作業場所の絶対パスにする。rules.md と guards の文書が違うことを言うなら、どちらが正本かをカードに書く。
9. **chromium が入らない時の道**: §3(f) を「入れられなければ BLOCKED」ではなく、次の一時の設定（リポジトリの外・commit しない）で流す道を足す（このクラウドで 1 passed・1 skipped を確かめた）。置いてある chromium の場所は `ls /opt/pw-browsers` で確かめる:
   ```ts
   // /tmp/stage0a.config.ts（commit しない）
   import base from "<作業場所の絶対パス>/tests/prod-check/page-speed.config.ts";
   import { defineConfig } from "@playwright/test";
   export default defineConfig({
     ...base,
     testDir: "<作業場所の絶対パス>/tests/prod-check",
     outputDir: "/tmp/stage0a-results",
     projects: base.projects?.map((p) => ({
       ...p,
       use: { ...p.use, launchOptions: { executablePath: "/opt/pw-browsers/chromium_headless_shell-<番号>/chrome-headless-shell-linux64/chrome-headless-shell" } },
     })),
   });
   ```
   （審査役がこの形を、置き場をスクラッチにして、直す前の page-speed.spec.ts で流し 1 skipped を確かめた。設定のファイルの隣に node_modules が無い /tmp に置いた形は未実行。実装役は流して結果を報告に書く。）
10. **手順6**: 「tests/prod-check/test-results/ は試験が作る物。add しない」と書く（または一時の設定の outputDir を /tmp にする＝直す点 9）。
11. **言葉の直し**: カード :9 の「合格の線は変えない」を「段 0 の合格線のうち動画の突き合わせを試しのページに替える（V0-1）。ほかの線は変えない」に。`want === ""` の訳は「中身の場所が無い」を ExtraNote に足して分ける。説明の行（§4-B(j)）に「403 ありの行の戻った時の秒は、中身でなく断りの画面の秒」「押した時の秒は、どの画面も 2 回目以降に開いた時」を足す。
12. **記録係の重さ**: 説明の行かカードの V0 に「記録係は 1 コマ約 0.8 ms（400 要素・審査役の実測）。入れた日から今の秒が少し動きうる。設計担当は入れる前後の日の秒を比べる」と書く。
13. **精度の試しの取り回し**: runRecorderProbe の説明に「新しいページで 1 回だけ呼ぶ（同じページで 2 回目は 3/4 になる・審査役の実測）」と書く。§4-B(i) の `context.newPage()` と `probePage.close()` も try の中に入れる（失敗で表が書かれなくならないように）:
   ```ts
     let probe: ProbeResult = { passed: 0, total: 4, maxDiffMs: Number.POSITIVE_INFINITY };
     try {
       const probePage = await context.newPage();
       try {
         probe = await runRecorderProbe(probePage);
       } finally {
         await probePage.close();
       }
     } catch {
       // 精度の試しが動かなければ不合格として扱う
     }
   ```
14. **本番の読み取りの量**: カードに「K1 で毎朝の本番の読み取りが増える（推測で約 3 倍）」と書き、ADR-1053 の Negative の書き足しが要るかを設計担当が決める（要らなければ、要らない訳を書く）。

## 見張りに止められた文面

- 作業用の写しを作り直そうとした命令（スクラッチの置き場の中の消去）で、次の文面で止められた。消さずに別の名前で作り直して続けた（リポジトリと本番には影響なし）:
  ```
  PreToolUse:Bash hook error: [[ "$CLAUDE_CODE_REMOTE" = "true" ] || exit 0; exec bash "$CLAUDE_PROJECT_DIR/scripts/agent-hooks/cloud/dispatch.sh"]: BLOCKED(cloud): 'rm -rf' は不可逆操作です。クラウドでは行えません。手元で PO の承認を得て実行してください。
  ```
