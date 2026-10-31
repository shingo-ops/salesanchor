HEAD: 70d3e2d1e70a8fab578c24b986522631ce8b79c5（origin/release/line-like-speed-stage0。依頼どおり 70d3e2d1e）
判定: APPROVE

# 段 0a 実装カード 第 2 版の審査（クラウドの Claude Opus・設計審査役）

- 基準: origin/main = 9e202335936921ad6a7f83bee0847cd09e987776（カードの S=9e2023359 と同じ）。
- 審査した物: docs/handoff/line-like-speed/stage0-card.md（全 689 行）、`git diff 74ed64709 HEAD -- docs/handoff/line-like-speed/design.md`（§3-4 段 0 の行・§3-5 K3 の行の 2 行）、第 1 版の審査（origin/release/line-like-speed-stage0-review-v1 の review-stage0-card-v1.md・直す点 1〜14）、ADR-1053・ADR-1054。
- 実際に動かして確かめたこと（本番には繋いでいない。秘密情報の環境変数 SMOKE_E2E_* が 0 個であることを確かめてから流した）:
  - カードの §4-A 全文と §4-B (a)〜(j) を、S の tests/prod-check の写し（スクラッチの置き場・リポジトリの外）に当てて tsc --strict（lib DOM）→ 誤り 0。--noUnusedLocals --noUnusedParameters を足しても誤り 0。
  - 同じ写しで playwright test を 5 回 → 5 回とも「記録係の精度」1 passed・本体 1 skipped。
  - 別の試し（スクラッチの置き場の exp）で精度の数・歯・.sa-spinner・押した時と命令の違い・waitQuiet を測った（数は各項目）。
  - §4-D の手順1〜6 を、このクラウドで実際の作業場所（/root/worktrees/salesanchor/release-line-like-speed-stage0）に作って流した（§4 参照）。commit と push はしていない。試しに置いた 2 ファイルは git restore と 1 ファイルの削除で戻し、作業場所は残した。

## 1. 第 1 版の直す点 1〜14 — すべて ○

| # | 直す点 | 判定 | 根拠（第 2 版の行） |
|---|---|---|---|
| 1 | kind "" は 94 件 | ○ | stage0-card.md:23・:53。S の page-speed-targets.ts を esbuild で束ねて数えた: 135 件・"" 94・section 25・needs-id 10・carrier 3・redirect 3。「95」はカードに残っていない |
| 2 | K3 の対象（設計担当の決定） | ○ | :23-30（V0-3 (ア)(イ)）、:425-501（measureTap・waitQuiet・measureSwitch）、design.md §3-4 段 0 と §3-5 K3 の行（diff）。案A ではなく (イ) を採った。妥当性は項目 2 |
| 3 | .sa-spinner を構造の印から外す | ○ | :75（SIG_SKIP_SELECTOR）・:105（`if (el.matches(SKIP)) continue;`）・:20（V0-2 の定義）。実測: span.sa-spinner を見出しに足しても印が同じ（same=true）、別のクラスの span では変わる（same=false） |
| 4 | 精度の試しの正解を描かれた時刻にする | ○ | :13（V0-1）・:133-144（MessageChannel）・:240-256（Element Timing）・:55（§3(d) に Element Timing と MessageChannel を足した）。限界も :14 に書いた |
| 5 | requestfinished を入口で同期に読む | ○ | :365-371、A4 の例外 :670 |
| 6 | K1 の時間の上限 | ○ | :322（K1_STAGE_LIMIT_MS）・:536-537・V0-6 :33-34・A7 :673 |
| 7 | B の選び方 | ○ | :21（V0-2）・:390-398（rows を引数に足した measureReturn） |
| 8 | 作業場所と手順1 | ○ | :608-614・§4-E :655-657。このクラウドで流して動いた（§4） |
| 9 | chromium が入らない時の道 | ○ | :57（§3(f)）・:622-641（手順4b）。このクラウドで流して動いた（§4） |
| 10 | test-results を add しない | ○ | :645（手順6）と `--output /tmp/stage0a-results`（:620・:643）。流した後の git status に test-results は出なかった |
| 11 | 言葉の直し | ○ | :9（見出し）・:20（中身の場所が無い）・:331 と :387（ExtraNote と want === ""）・:585-587（403 の行・2 回目以降） |
| 12 | 記録係の重さ | ○ | :16・:588 |
| 13 | 精度の試しの取り回し | ○ | :222（1 回だけ呼ぶ）・:518-529（newPage と close を try の中へ） |
| 14 | 本番の読み取りの量 | ○（言葉の注意 1 点・項目 5） | :35（V0-7）・:323・A10 :676 |

## 2. 押した時の (イ)（命令から測る）の妥当性 — ○（注意 2 点）

- 同じ仕組みを通るか: ○。react-router-dom は 7.18.0（frontend/node_modules/react-router/package.json）。BrowserRouter は history.listen に setState を渡し、setState は useTransitions が false でなければ React.startTransition で包む（frontend/node_modules/react-router/dist/development/chunk-4ZMWKKQ3.mjs:10406-10416）。メニューの NavLink を押した時（history.push → listener）も、goInApp の popstate（listener）も、同じ setState を通る。App.tsx:152 は useTransitions を渡していない。→ 中身の場所が最初に変わるまでの React の仕事は (ア) と (イ) で同じ。
- 測る物の違いの大きさ（実測・試しのページ・15 回ずつ）: 押して動かす形（pointerdown → 中身の最初の変化）は 最小 0.7・中央 0.9・最大 3.7 ms。そのうち pointerdown → click は 最小 0.5・中央 0.6・最大 1.4 ms。命令で動かす形（命令の直前 → 中身の最初の変化）は 最小 0.2・中央 0.3・最大 0.5 ms。→ 押す指の動きの差は数 ms で、0.1 秒の線に対して小さい。
- 注意 1（言葉）: (イ) には「押された部品の click の処理」も入らない。横のメニューの項目は押すと handleSidebarNavClick（frontend/src/components/DesktopShell.tsx:160-164）で setSidebarExpanded など 3 つの状態を変え、DesktopShell が同期に描き直す（その中身の場所は変わらない・:400 の className は isInbox だけで決まる）。この描き直しの時間は (ア) に入り (イ) に入らない（大きさは本番で未確認）。(イ) の数は (ア) より小さめに出る向きがある。V0-3 :27 の「押す指の動き（数 ms）は入らない」に「押された部品の click の処理も入らない。(ア) と (イ) の数は並べて比べない」を足すのがよい（申し送り 2）。
- 注意 2（表の読み分け）: 表では (イ) で測れた行は訳の列に「命令で切り替え」が出て、合計の行も分かれる（:595）ので読み分けられる。ただし訳の列は K1 と K3 の訳を「・」でつないだだけ（:582）で、片方が空の時にどちらの訳か字面では分からない（例: 訳が「エラー」1 つだけの行）。秒の列の「—」と組み合わせれば決まるが、読みにくい。また (イ) で失敗した行（「5 秒で変化なし」など）は (ア) か (イ) かが出ない（数を出さない行なので基準の数は誤らない）。申し送り 1 の形にすると読みやすい。
- 設計 §3-5 の K3 の基準として: ○。K3 の目的（押してから画面が反応し始めるまで）の大部分は、道すじの変更から中身の場所が変わるまでの React の仕事で、それは (ア)(イ) で同じ。94 画面すべてに数が出る点で、案A（7 画面）より段 2 以降の比べる相手として役に立つ。

## 3. §4-A 全文と §4-B の直しの実行 — ○

- tsc --strict（lib ES2022・DOM）: 誤り 0（2 回。未使用の検査を足しても 0）。
- playwright test（S の page-speed.config.ts に置いてある chromium の場所だけ足した写し）: 5 回とも 1 passed・1 skipped。
- 精度の試し（新しいページで 1 回ずつ・10 回）: 10 回とも 4/4。差（ms）は 戻った時 3 形と押した時の順に、最大 7.5・すべて 1.2〜7.5。
- 歯（わざと壊した記録係・各 3 回）: 毎コマを setTimeout 200 ms に替えると 3/4・2/4・2/4（差 93〜108 ms）で落ちる。
- 歯の届かない所（記録のため）: MessageChannel をやめて requestAnimationFrame の中の時刻を残す形（第 1 版の形）も 3 回とも 4/4（差 1.3〜7.5 ms）。試しの形は軽いので、MessageChannel の効き目はこの試しでは見分けられない。カードの V0-1 の限界（:14）の範囲で、誤りではない。
- .sa-spinner を外す形: 項目 1 の 3 のとおり。
- waitQuiet と「押す前も動いていた」: 中身の場所を 300 ms ごとに変え続けると、waitQuiet は 5011・5017 ms 待って抜け、判定は「動いていた」（2 回）。変化が止んだ後は 2334・2342 ms 待って抜け、最後の変化から 1029・1039 ms で「静か」（2 回）。
- requestfinished の counted と extra.apis（:365-371）: ○。判定は await より前で同期。残る小さな穴（記録）: K1・K3 のあいだに始まり、extra.on が false に戻った後に終わる通信は、今の 403 の合計に入りうる。普段は measureReturn・measureTap・measureSwitch の最後の waitSettled（1 秒静か）で防がれ、起きるのは例外で抜けた時だけ。基準の数への影響は小さい（直さなくてよい）。
- B の選び方（measureReturn に rows）: ○。rows は SPEED_TARGETS の順に 1 件ずつ入る（S page-speed.spec.ts:272・:280・:313・:317）ので、最初の画面は rows が空で "/"（SPEED_TARGETS の最初の kind ""）に落ちる。redirect の行は route が「A → B」になる（S :296）ので kindEmpty に入らず B に選ばれない。型・実行とも通る。

## 4. §4-D の手順がこのクラウドで動くか — ○（注意 1 点）

- 手順1: `bash scripts/new-worktree.sh release/line-like-speed-stage0` → rc=0、/root/worktrees/salesanchor/release-line-like-speed-stage0 を作った。続けて fetch・`git switch -C release/line-like-speed-stage0 origin/release/line-like-speed-stage0`・rev-parse → 2 行とも 70d3e2d1e70a8fab578c24b986522631ce8b79c5。
- 手順2: `npm ci` → rc=0。`npx playwright install chromium` は流していない（注意参照）。
- 手順3: §4-A・§4-B を当てた 2 ファイルを置いた。
- 手順4（そのまま）: rc=1、`Executable doesn't exist at /opt/pw-browsers/chromium_headless_shell-1217/...`。
- 手順4b（そのまま・/tmp/stage0a.config.ts・PW_HEADLESS を頭に足す）: `ls /opt/pw-browsers` は chromium・chromium-1243・chromium_headless_shell-1243・ffmpeg-1011。精度の試しだけ → 1 passed（rc=0）。
- 手順5（4b の設定で）: 5 回とも 1 skipped・1 passed（rc=0）。/tmp に置いた設定から @playwright/test が読めた（第 1 版で未実行だった点が解けた）。
- 手順6: git status は ` M tests/prod-check/page-speed.spec.ts` と `?? tests/prod-check/screen-recorder.ts` だけ。test-results は出ない。
- 注意: このクラウドの環境の説明は「playwright install を流さない（置いてある chromium が見つからなくなる）」と言っている。カードの手順2 は install を流させる。§3(f) と手順4b で道はあるので止まらないが、クラウドの実装役が迷う。申し送り 3。
- 精度の試しが通っても /tmp/stage0a-probe.txt には「1 passed」しか出ず、4/4 や差の数は出ない（A1 の検証方法 :667 の「passed」で足りる。数は落ちた時だけ出る・:510）。

## 5. 時間の見込み・25 分の上限・読み取りの量 — ○（言葉の注意 1 点）

- 今の段の時間: GitHub の実行記録で確かめた。prod-ui-check run 41169062594（2026-10-31・main）の段「画面の速さを記録（判定なし）」が 04:37:32〜04:40:48 = 3 分 16 秒。V0-6（:34）の値と一致（第 1 版で未確認だった点が解けた）。
- 見込み 約 14 分（:34）: 推測と書かれており、根拠の分け方（K1 2 回分・K3 94 画面）は妥当。項目 3 の実測で (イ) 1 回の仕事は waitQuiet＋命令＋waitSettled（最短 500 ms・1 秒静か・S tests/prod-check/settle.ts）で、1 画面 2〜3 秒の見込みと合う。
- 25 分の上限: ○。最悪（全画面が 10 秒で見分けられず）は 1 画面 約 13 秒で、25 分で約 115 画面目まで。残りの今の秒 約 20 画面と K3 約 4 分を足して約 30 分。K3 の巡回は 40 分（S page-speed.spec.ts:19）で止まり、最後の 1 画面がはみ出しても最大約 100 秒（leaveIfSame 45 秒＋waitQuiet 5 秒＋変化待ち 5 秒＋waitSettled 45 秒）で、試験の上限 45 分（S page-speed.config.ts:19）と段の 46 分（S .github/workflows/prod-ui-check.yml:149）の中。今の秒（K2）は K1 より前に測るので削られない。
- 読み取りの量（V0-7・ADR を直さない判断）: ○。ADR-1054 の Scope が「測る仕組み（tests/prod-check の記録係）」を含み（docs/adr/ADR-1054-screen-data-cache.md:39）、段 0 で測る仕組みを足すと書く（同 :66）。ADR-1053 の Negative（docs/adr/ADR-1053-prod-page-speed-record.md:52）は種類が変わらない。ただし ADR-1053 の What は「全画面を 1 回ずつ開き」（同 :19）と書く。V0-7 はこの行に触れていない。「1 回ずつ」は K2 の測り方の決まりで、K1・K3 の開き直しは ADR-1054:39 の測る仕組みとして足す、と V0-7 に書くと根拠が閉じる（申し送り 4）。

## 6. 秘密と公開（ADR-1053）— ○

- 新しい 3 列は sec2 の数・「—」・ExtraNote の決まった言葉だけ（:328-339・:582）。構造の印の数は sigNow と waitMatch の中だけで使い、render に渡さない（:377-420）。
- 新しい説明の行・合計の行は件数・ms・MB と決まった言葉だけ（:584-598）。extra.apis は数だけ。
- 番号の入った url（needs-id）は measureReturn・measureSwitch の中だけで、表には row.route（S page-speed.spec.ts:295-296 の形）しか出ない。
- 試しのページの "probe"・"x" は試しのページの中だけ。

## 7. card-lint — ○

```
L24 警告 1行200字超が 53件（閾値は暫定・止めない）
```
終了コード 0。

## 8. 新しい抜け・矛盾と、渡せるか — 渡せる

- 第 1 版の 14 件はすべて直り、型・実行・手順はこのクラウドで動いた。見つけた点は、どれも基準の数を誤らせず、実装役の作業も止めない。→ APPROVE。
- 下の申し送り 1〜4 は、設計担当が実装役へ渡す前にカードへ入れてもよいし、段 0a の PR の後に直してもよい（入れる時は、入れた行だけ審査役に見せれば足りる）。

### 申し送り（APPROVE の条件ではない）

1. 訳の列で K1 と K3 を分ける（§4-B(j)・カード :582 の 1 行の差し替え）:
   ```ts
   ${[r.k1Note && `戻: ${r.k1Note}`, r.k3Note && `押: ${r.k3Note}`].filter(Boolean).join("・") || "—"}
   ```
   見出しはそのまま。説明の行に「訳の列の『戻:』は戻った時、『押:』は押した時の訳」を足す。
2. V0-3 (イ)（:27）と説明の行（:587）に「命令で切り替えた行には、押された部品の click の処理（横のメニューなら閉じる描き直し）も入らない。メニューを押した行と命令で切り替えた行の秒は並べて比べない」を足す。
3. 手順2（:615-617）: クラウドで流す時は `npx playwright install chromium` を流さず、手順4 から手順4b の形で流す、と書く（このクラウドの環境の説明が install を流さないよう求めるため。手元では今の手順のまま）。
4. V0-7（:35）に「ADR-1053:19 の『全画面を 1 回ずつ開き』は今の秒（K2）の決まり。K1・K3 の開き直しは ADR-1054:39・:66 の段 0 の測る仕組みとして足す」と書く。

## 見張りに止められた文面

- なし。
