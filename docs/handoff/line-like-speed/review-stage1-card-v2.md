HEAD: d66cdd34053f8d1f384101e39eb592bcd0aaf962（origin/release/line-like-speed-stage1-card。S=dc99a062e）
判定: REVISE

# 段 1 実装カード 第 2 版の審査（設計審査役・2026-10-31）

- 審査した文書: docs/handoff/line-like-speed/stage1-card.md（以下「カード」）。照合: 前回の審査 origin/release/line-like-speed-stage1-review-v1 の review-stage1-card-v1.md・design.md §3-2・ADR-1054。
- 試した場所: リポジトリの外の写し（`git archive HEAD frontend backend` を scratchpad に展開）。製品コード・設計文書は変えていない。本番には接続していない。
- 行番号: 「カード:N」は stage1-card.md の行。「試験:N」は §4-F の全文を当てたファイルの行（試験:N = カード:181+N）。

## 項目 1. 前回の直す点 1〜8 が入ったか

| # | 前回の直す点 | 結果 | 根拠 |
|---|---|---|---|
| 1 | tree を呼ぶたびに作る関数に | ○ | カード:296・:301・:311・:316（T4）、:333・:338・:342（T5）、:358・:365・:368（T6）、T8・T9 も同じ形（:386・:392・:396・:412・:417・:422） |
| 2 | resetQueries → 各写しの Query.reset() | ○ | カード:140-144（§4-C）、V1-5 カード:20-21、§4-E カード:177 |
| 2' | design.md §3-2 の消す順の行 | ○ | design.md:44 が「cancelQueries → 各写しの Query.reset()（…取り直さない）→ queryClient.clear() → getMutationCache().clear()」になった（`git diff dc99a062e HEAD -- design.md` で 1 行だけの書き換え）。design.md:120 の X4 の行「cancel→reset→clear」は Query.reset と読めるので矛盾しない |
| 3 | T8・T9 を足す | ○ | カード:383-407（T8）・:409-429（T9）。前回の審査の全文と同じ |
| 4 | 件数 7 → 9 | ○ | カード:12（V1-1 に T8・T9）・:13（V1-2 に T8）・:31・:183・:486（9 passed・T8・T9 の中身）・:501（9 件中 9 件）。「T1〜T7」「7 件」「7 passed」の残りは 0（grep で確かめた） |
| 5 | 行の指し方 | ○ | カード:26・:45 が package.json「S :71-91」（S で :71 `"dependencies": {`・:91 `},`）。カード:45 が api.ts「:81-167」（S :81 fetchWithReauth・:104 request・:167 閉じ） |
| 6 | peer に @types/react | ○ | カード:15・:47。S frontend/package.json:85 react ^18.3.1・:101 @types/react ^18.3.18。注: カード:15 は react を「:86」・@types/react を「:102」と書くが、S では :85・:101（:86 は react-big-calendar、:102 は @types/react-dom）。直す点 2 |
| 7 | 手順4 の先頭で型を作る | ○ | カード:453-455。前回の条件つきの注は消えた（「落ちる時」の grep 0 件） |
| 8 | 起動前の確かめ | △ | カード:442-444 に行と分岐は入った。ただしこのクラウドでは分岐の想定と違う FAIL が出る（項目 4）。直す点 1 |

## 項目 2. 全文を当てて流した結果 — ○（9 件中 9 件）

§4-B（カード:58-115）・§4-C（カード:120-150）・§4-F（カード:182-429）を切り出して置き、§4-D のとおり App.tsx を直した。node v22.23.4・npm 10.9.9。

| 命令 | 結果 |
|---|---|
| npm ci | 終了コード 0 |
| npm view @tanstack/react-query@5.104.4 version peerDependencies --json | version 5.104.4・peer は react `^18 \|\| ^19`・@types/react `^18 \|\| ^19` |
| npm install @tanstack/react-query@5.104.4 --save-exact | 0。package.json の差は `"@tanstack/react-query": "5.104.4",` の 1 行足しだけ（S の :78 の次）。package-lock.json は足した行 33 |
| npm run generate:api-types | 0（`api-contract/openapi.json → src/api/generated/schema.d.ts`） |
| vitest（src/lib/query） | Test Files 1 passed (1)・**Tests 9 passed (9)** |
| npm run test:unit | Test Files 171 passed (171)・Tests 1942 passed (1942) |
| tsc --noEmit -p . | 0 |
| eslint --max-warnings=0 src/lib/query src/App.tsx | 0 |
| npm run build | 0（大きい chunk の警告だけ） |

- T1〜T9 の合否: 合格 9・不合格 0。
- App.tsx の `git diff -w`（S の App.tsx と比べた）: 足した行 7・消えた行 0。中身は import 3 行・コメント 1 行・`<QueryClientProvider …>`・`<QueryAuthSync />`・`</QueryClientProvider>` の 3 行。カード:40・:172 の「包む 4 行」（合計 8 行）と 1 行合わない。直す点 3。

## 項目 3. 歯 — ○（4 つとも落ちる）

| 壊し方 | 落ちた試験 | 落ちた場所 |
|---|---|---|
| M1 消す 4 行（カード:143-146）を外す | T4・T5・T8（3 failed / 6 passed） | 試験:132（カード:313）・試験:163（カード:344）・試験:217（カード:398）で `expected 1 to be +0`（A の写しの数） |
| M2 useLayoutEffect → useEffect | T8（1 failed / 8 passed） | 試験:216（カード:397）で `expected '' to be 'uid-B:/companies'` |
| M3 retry: 0 を外す | T3（10 秒で時間切れ）・T7（2 failed / 7 passed） | — |
| M7 Query.reset の行を `void queryClient.resetQueries();` に戻す | T9（1 failed / 8 passed） | 試験:245（カード:426）で `expected "get" to not be called at all, but actually been called 1 times` |

- どの壊し方でも 1 件以上落ちたので、歯の直す点は無い。壊した後は元に戻し、差が無いことを diff で確かめた。

## 項目 4. §4-G 手順1 の後の executor-preflight.sh — ×（このクラウドの実行役は止まる）

- 作業場所 /root/worktrees/salesanchor/release-line-like-speed-stage1-review-v2 で、`git switch -C … origin/release/line-like-speed-stage1-card` の後に HEAD と origin が d66cdd340 で一致。そこで `./scripts/dev/executor-preflight.sh` を流した。終了コード 1。FAIL の行は全部で 3 行:
  - 3 行目: `[FAIL] GitHub API に到達不可。Mac回線ではなく実行役サンドボックスの通信OFFが濃厚。`
  - 7 行目: `[FAIL] gh auth switch --hostname github.com --user shingo-cc に失敗。gh auth status --active で現状を確認。`
  - 13 行目: `PREFLIGHT FAIL — 上の対策を実施し再実行(深追いしない)`
- 1 行目の原因: scripts/dev/executor-preflight.sh:25 は `curl -sf --max-time 8 -I https://api.github.com` で確かめる。このクラウドで同じ URL に `curl -I` を送ると、HTTP の答えは **400**（-f で失敗扱いになる）。一方 [4/4] の `git ls-remote --heads origin main` は OK で、git fetch も通った。つまり GitHub に届かないのではなく、クラウドの通信の通り道が HEAD の問い合わせを 400 で返すため（400 を返したのが通り道か GitHub かは未確認）。
- カード:444 の分岐は「gh auth switch の 1 件と PREFLIGHT FAIL の行だけなら続ける。ほかの FAIL が 1 件でもあれば停止」なので、このクラウドの実行役は **3 行目の FAIL で BLOCKED: を返して止まる**。前回の審査（v1 項目 5）では gh の 1 件だけが出たと書いてあり、通信の段の結果は日により変わり得る（前回の段 1 の出力は手元に無く、未確認）。
- ついでに分かったこと: preflight は mode=fix で `git config user.name shingo-cc` を書く（executor-preflight.sh:57-59）。書き先はリポジトリの .git/config（作業場所の全部で共有）。クラウドの commit の名前が shingo-cc になる。害は確かめていない（未確認）ので直す点にはしない。

## 項目 5. card-lint — ○

- `bash scripts/card-lint.sh docs/handoff/line-like-speed/stage1-card.md` の出力は 1 行で、終了コード 0: `L24 警告 1行200字超が 34件（閾値は暫定・止めない）`。

## 項目 6. 新しい抜け・矛盾と、実装役に渡せるか — 今のままでは渡せない

- 渡せない理由: 項目 4。カードどおりに進むと、手順1 の preflight で止まる。中身（§4-B〜§4-F）はそのまま 9 件合格・歯もあるので、直すのはカード:444 の分岐の文だけでよい。
- 小さな食い違い（直す点 2・3）: カード:15 の package.json の行が 1 ずれ。カード:40・:172 の「包む 4 行」は実際 3 行。A4（カード:489）は「足した行だけ・消えた行 0」で判定するので数の食い違いで落ちはしないが、実行役が 7 行と 8 行の違いで止まる道が残る。
- 参考（直す点にしない）: カード:45 の api.ts「:237-250」は、S では :237 が request の最後の `return res.json();`、:240-253 が `export const api = {…}`。api.get の行（:241）は範囲に入るので確かめには足りる。
- ほかの矛盾は見つけていない。ADR-1054 と design.md:44 とカード §4-C の消す順は合う。

## 直す点（3 件）

1. **カード:444 の分岐に、通信の段の FAIL も足す**。直した後の全文:
   `  （FAIL の行が次の 3 つのうちのどれかだけなら続ける: `GitHub API に到達不可` の 1 件・`gh auth switch --hostname github.com --user shingo-cc` の失敗の 1 件・その結果の `PREFLIGHT FAIL` の行。理由: クラウドには gh の名義が無く、PR は設計担当が手元で shingo-cc 名義を確かめてから作る。またクラウドの通信の通り道は api.github.com への HEAD の問い合わせを 400 で返す（審査 v2 項目 4）が、git の取り寄せと push は通る。続ける時は、同じファイルの `[4/4]` の次の行が `[OK]   origin/main は存在` であることを `grep -n "origin/main は存在" /tmp/stage1-preflight.txt` で確かめ、無ければ停止する。ほかの FAIL が 1 件でもあれば停止し、BLOCKED: で grep の出力を報告する。）`
   あわせてカード:443 の次に 1 行足す: `  cd <W> && grep -n "origin/main は存在" /tmp/stage1-preflight.txt | head -3`
2. **カード:15 の行番号を直す**: 「react ^18.3.1（S frontend/package.json:86）と @types/react ^18.3.18（S frontend/package.json:102）」→「react ^18.3.1（S frontend/package.json:85）と @types/react ^18.3.18（S frontend/package.json:101）」。
3. **カード:40・:172 の行の数を直す**: 「包む 4 行」→「包む 3 行（`<QueryClientProvider client={queryClient}>`・`<QueryAuthSync />`・`</QueryClientProvider>`）」。カード:172 は「足した行（import 3 行・コメント 1 行・包む 3 行の計 7 行）だけが出て、消えた行が 0 であること（§5 A4）」にする。

## 見張りに止められた文面

- なし（この審査の間に止められた命令は無かった）。
