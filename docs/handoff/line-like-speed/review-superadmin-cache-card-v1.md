HEAD: bf70aeb6db5a11a802f2447173981943bc765a05（origin/release/line-like-speed-superadmin-cache。指示どおり bf70aeb6d）
判定: REVISE

# 運営者判定の写しカード 第 1 版の審査（クラウドの設計審査役・2026-11-01）

- 審査した物: docs/handoff/line-like-speed/superadmin-cache-card.md（第 1 版）・design.md §3-4-9（`git diff 7cc0f25e3 HEAD`）。お手本: perm-cache-card.md・frontend/src/hooks/usePermissions.ts・usePermissions.test.ts。
- 引用の基準 S=7cc0f25e3。`git diff --name-only 7cc0f25e3 HEAD` は .claude-pipeline/active-work.d/release-line-like-speed-superadmin-cache.md・design.md・superadmin-cache-card.md の 3 つだけなので、frontend/・backend/・scripts/ の行番号は HEAD と S で同じ。
- 確かめ方: 審査役の使い捨ての作業場所（scratchpad の git worktree・HEAD 起点・push しない）で npm ci の後、カードの §4-A（カード 47-70 行）・§4-B（カード 76-193 行）を sed で一字も変えずに書き出し、カードの手順 4・5 と同じ命令を流した。製品コード・設計文書は変えていない。

## 1. 行番号の引用（S=7cc0f25e3）

| 引用 | 判定 | 実物 |
|---|---|---|
| useSuperAdmin.ts:19-42 | ○（小さなずれ） | 関数は 19 行目から始まり、43 行目の `}` で終わる（S frontend/src/hooks/useSuperAdmin.ts:19・:43）。19-42 は閉じ括弧を含まない。§1 の「全 43 行」は合う |
| apiQuery.ts:41-44 | ○ | apiQueryKey は 41-44（40 は説明の行） |
| apiQuery.ts:51-73 | ○ | useApiQuery は 51-73 |
| QueryAuthSync.tsx:18-28 | ○ | useLayoutEffect の 18-28 |
| DesktopShell.tsx:112 | ○ | `const { isSuperAdmin } = useSuperAdmin();` |
| AnalysisRulesPage.tsx:101 | ○ | useSuperAdmin の行 |
| AnalysisRulesPage.tsx:116-122 | × | `if (superAdminLoading) {` から閉じ `}` までは 117-123（116 は空行）。S frontend/src/pages/super-admin/AnalysisRulesPage.tsx:117・:123 |
| TcgProductImportPage.tsx:12-14 | ○ | 12 が useSuperAdmin、14 が `loading ? <LoadingBlock />` |
| scripts/agent-hooks/cloud/rules.md:15 | ○ | 「ファイルを変える前に、AGENTS.md「ブランチと作業場所」に従って…」の行 |

ずれは 2 つ: AnalysisRulesPage.tsx:116-122 → 117-123（×）。useSuperAdmin.ts:19-42 → 19-43（閉じ括弧・小）。

## 2. §4-A のコード — ○

- 型: そのまま書き出して `npx tsc --noEmit -p .` が終了 0・出力なし（frontend/tsconfig.json は include ["src"]）。`npm run build`（tsc && vite build）も終了 0・`✓ built in 2.22s`。
- useApiQuery の形と合う: `useApiQuery<T>(path, options?)` が `UseQueryResult<T>` を返す（S frontend/src/lib/query/apiQuery.ts:51-54）。§4-A は `useApiQuery<MePermissionsResponse>("/me/permissions")` から data・isPending を取る（カード 66 行）。
- 返す形 `{ isSuperAdmin, loading }` は同じ（カード 69 行・S useSuperAdmin.ts:42）。
- 意味: 失敗で false（data が無いので `Boolean(undefined)`）・初回 loading true（isPending）。§4-B の 1・4 本目が合格で確かめた（下の 3）。
- 写しの名前: どちらも path が "/me/permissions" なので、apiQueryKey で同じ `["api", uid, "me", "permissions", { query: "" }]` になる（S apiQuery.ts:41-44・:66、S usePermissions.ts:18）。6 本目（usePermissions と並べて通信 1 回）が合格し、データが 1 か所であることを試験で確かめた。
- 型引数が usePermissions は PermissionsResponse（permissions だけ・S usePermissions.ts:13-15）、useSuperAdmin は MePermissionsResponse（is_super_admin を足す）と違うが、同じ写しの中身（API の返り）を別の型で読むだけで、データは 1 つ。害は無い。
- lint: `npx eslint src/hooks/useSuperAdmin.ts src/hooks/useSuperAdmin.test.ts` 終了 0・出力なし（警告 0）。§3(f) は満たす。

## 3. §4-B の 8 本 — ○（そのまま全部合格）

- 単体: `npx vitest run --config vitest.unit.config.ts --project unit src/hooks/useSuperAdmin.test.ts` → `Test Files  1 passed (1)`・`Tests  8 passed (8)`・tests 372ms。
- 区別できるか: 同じ 8 本を S の古い useSuperAdmin.ts で流すと `Tests  3 failed | 5 passed (8)`。落ちたのは 6 本目（通信 1 回）・7 本目（K1）・8 本目（K5）。この 3 本が変更を見分ける試験として効いている。
- vi.hoisted と vi.mock の形: usePermissions.test.ts:7-17 と同じ（カード 83-93 行）。○
- queryClient の export: 有る（S apiQuery.ts:22 `export const queryClient`）。afterEach の `queryClient.clear()` も usePermissions.test.ts:22-27 と同じ。○
- 7 本目（K1）: 2 回目の renderHook の直後に loading false・isSuperAdmin true、その後 2 回目の通信（staleTime 0 の取り直し）を waitFor で待つ。usePermissions.test.ts:145-159 と同じ形で、合格。○
- 8 本目（K5）: uid を user-b に変えて rerender した直後に isSuperAdmin false・loading true。QueryAuthSync を描かない試験でも、写しの名前に uid が入る（S apiQuery.ts:66）ので user-b の写しは空で、前の人の true は出ない。usePermissions.test.ts:161-177 と同じ形で、合格。○
- 6 本目: `toHaveBeenCalledOnce()` 合格。○
- 4 本目（失敗）: retry 0（S apiQuery.ts:26）なので送り直しの待ちは無く、8 本全体で tests 372ms。○
- perm-cache-card の試験で通った形との食い違い: 見つからない。違いは usePermissions に有る reload・hasAny・error の試験が無いこと（useSuperAdmin はそれらを返さないので当然）だけ。

## 4. 使い手と、ほかの試験への影響 — ○（ただしカードの数 2 つが ×）

- `git grep -n 'useSuperAdmin()' -- frontend/src ':!*.test.*'` は 22 行。ただし 1 行は定義そのもの（frontend/src/hooks/useSuperAdmin.ts:19 `export function useSuperAdmin() {`）。使い手は 21 行。カード §0 P7 の「使い手 22 行」は ×（数え方の説明が要る）。
- 使い手 21 行のうち、カードが名前を挙げない外側の枠がもう 1 つある: frontend/src/components/MobileShell.tsx:78。P6 の「外側の枠と SecretaryChat」に MobileShell も入る（ProtectedRoute の内側かは未確認。perm-cache-card の P5 と同じ根拠ならそこに含まれているはず、とは推測なので書かない）。
- useSuperAdmin を差し替える試験: `git grep -l "useSuperAdmin" -- 'frontend/src/**/*.test.*'` は 13 ファイル（DesktopShell・MobileShell・SecretaryChat・AnalysisRulesPage・ViewerAccountsPage・ViewerTemplatesPage・NeedsReviewTabsPanel の 5 本（acked・drawer・無印・timing・view）・ProductMasterPanel・SoldOutResultsPanel）。13 とも vi.mock で差し替える（例 frontend/src/components/DesktopShell.test.tsx:57）。カード §0 P8 の「11 ファイル」は ×。
- カードが書いていない影響: useSuperAdmin を差し替えずに本物を通す試験が 8 ファイルある。InventoryPage（frontend/src/pages/inventory/InventoryPage.tsx:146 で useSuperAdmin を使う）の試験 InventoryPage.autorefresh・noechopatch・rowdrawer・settings・singlefetch・tablelayout・tabs・toolbar（.test.tsx）。どれも api だけを差し替え、AuthContext と queryClient は差し替えない（例 InventoryPage.rowdrawer.test.tsx:9-15）。変更後はこの 8 ファイルで useApiQuery が動き、試験の間で写しが残る（afterEach で queryClient を消さない）。とくに rowdrawer は試験ごとに is_super_admin を true/false で変える（InventoryPage.rowdrawer.test.tsx:44-55・F1 が true・F2 が false）ので、F2 の最初の描画には F1 の写しの true が出る。
  - 実測: 変更後に `npx vitest run ... src/pages/inventory/ src/hooks/useSuperAdmin.test.ts` を 3 回流し、3 回とも `Test Files  10 passed (10)`・`Tests  49 passed (49)`。全部の試験 `npm run test:unit` も `Test Files  177 passed (177)`・`Tests  1997 passed (1997)`。いまは落ちない。F2 は「/me/permissions の呼び出しを待つ＋30ms 待つ」の後に押すので、取り直しの false が先に届いていると考えられるが、時間に頼った合格であることはカードに書いておくべき（直す点 4）。
- P7 の根拠（運営者の API は backend が断る）: ○。backend/app/auth/dependencies.py:516 `require_super_admin` が :539-543 で `is_super_admin` が偽なら 403 を返す。例: backend/app/main.py:267（/api/v1/admin に router ごと付ける）。main.py:525・633・646・651・694-739・773 の説明行に各ルーターで require_super_admin を使うと書かれている。運営者の画面が呼ぶ API のすべてにこれが付いているかは 1 本ずつは確かめていない（未確認）。

## 5. §0 P1 の根拠（読み込み中の印）— 一部 ×（仮説が外れ得る画面がある）

App.tsx の /super-admin/ の行は 14（frontend/src/App.tsx:311-361。TcgProductImport・FxRate・TcgDistribution・TcgLineImport・AnalysisRules・SupplierExtractionRules・取り込み 6 つ・viewers・viewer-templates）。各画面の、useSuperAdmin の loading の間に出す物:

| 画面 | useSuperAdmin | loading の間 | 判定の後の自分の取り直し |
|---|---|---|---|
| TcgProductImportPage | :12 | LoadingBlock（:14） | パネルの中（未確認） |
| SupplierImportPage | :129 | LoadingBlock（:132） | 同上 |
| UnitImportPage | :129 | LoadingBlock（:132） | 同上 |
| ConditionImportPage | :129 | LoadingBlock（:132） | 同上 |
| StatusMasterImportPage | :129 | LoadingBlock（:132） | 同上 |
| NoteMasterImportPage | :129 | LoadingBlock（:132） | 同上 |
| ProductCategoriesImportPage | :135 | LoadingBlock（:138） | 同上 |
| AnalysisRulesPage | :101 | PageLayout＋LoadingBlock（:117-123） | 区切りの中の部品（NeedsReviewTabsPanel.tsx:79・:113、SoldOutResultsPanel.tsx:44・:55・:80 も自分で useSuperAdmin を読み、判定の後に取る） |
| FxRatePage | :30 | LoadingBlock（:72-74） | 判定の後に load（:51-55） |
| ViewerAccountsPage | :104 | LoadingBlock（:317-319） | 判定の後に load（:148-152） |
| ViewerTemplatesPage | :52 | LoadingBlock（:163-165） | 判定の後に /super-admin/viewer-templates（:71-76） |
| TcgLineImportPage | :74 | PageLayout＋LoadingBlock（:249-254） | 判定の後に履歴など（:146-150） |
| TcgDistributionPage | :19 | LoadingBlock ではなく文字 `t("common.loading")`（:22-28） | 未確認 |
| SupplierExtractionRulesPage | :132 | 何も出さない `return null`（:456） | 判定の後に fetchList（:189-193） |

- P3 の「loading の間は中身の代わりに LoadingBlock を出す」は 12 画面で ○、TcgDistributionPage（文字）・SupplierExtractionRulesPage（null）の 2 画面で形が違う。
- P4 の仮説が外れ得る所: FxRate・ViewerAccounts・ViewerTemplates・TcgLineImport・SupplierExtractionRules・AnalysisRules の区切りの部品は、判定が出た後に自分の API を useEffect で取り直し、その間は自分の読み込みの状態になる（行は上の表）。変更後は判定の待ちは消えるが、K1 がこの画面自身の API の秒で決まる可能性がある。カード P1 は「いちばん遅い API は /me/permissions か 0 本」と書くが、その記録（/tmp/CC報告ファイル/stage3/k1-over-0.1.txt）はリポジトリに無いので未確認。仮説が外れた時の扱いは C4 の「誤りと記録して止まる」で決まっているので、カードを止める理由ではないが、外れ得る画面をカードに書いておくべき（直す点 5）。
- P1 の「区切りの行は 21 行と 25 個で数が合わない」はカード自身が「まだ確かめていない」と書いており、記録がリポジトリに無いので審査役も未確認。

## 6. 受入・触らない範囲・手順の矛盾、card-lint — ×（card-lint が違反 2 件）

- §5 C1〜C5 は ○×で判定できる。C1 は「1 file・8 passed」、C2 は 4 つの出力の最後と必須の確認、C3 は gh pr diff --name-only、C4 は「/super-admin/ で始まる行すべて ≤0.1 秒・403・5xx 0 件」、C5 は deploy の結論。○
- §2 と手順 1〜9 の矛盾: 見つからない。手順で変えるのは §1 #1・#2 だけ（手順 3・7）。npm run generate:api-types が作る frontend/src/api/generated/ は .gitignore で除かれる（カード 220 行の説明どおり、審査役の作業場所でも git status に出なかった）。○
- `bash scripts/card-lint.sh docs/handoff/line-like-speed/superadmin-cache-card.md`（リポジトリの最上位から）の出力（全文）:
  ```
  L01 cd接頭辞なし   （落ちた試験があれば、次の命令で名前を出して §3(d) に従う: cd <W> && grep -n -E "FAIL|✗|×" /tmp/sa-unit-all.txt | head -40）
  L24 警告 1行200字超が 26件（閾値は暫定・止めない）
  L29 読んだ節の書き出しなし guards のどれを引いたかを冒頭に書く
  違反 2 件。このカードは投入しない。
  ```
  - L01: カード 227 行。手順の中の「（…」で始まる行に命令が混ざっている。
  - L29: card-lint.sh:180-183 は本文に `guards/` の文字が無いと違反にする。カード 5 行目は「perm-cache-card.md の冒頭と同じ」としか書かず、guards の名前を書いていない（perm-cache-card.md:5 は guards/00-common.md ほかを名前で書いている）。
  - 参考: お手本の perm-cache-card.md も同じ L01（違反 1 件）が出る。L29 はこのカードで新しく出た。

## 7. 新しい抜け・矛盾・不明点、実装役に渡せるか

- コード（§4-A）と試験（§4-B）は、そのままで型・lint・単体 8 本・全部の試験・組み立てが通る。中身は実装役に渡せる。
- 渡す前に直す物: card-lint の違反 2 件（card-lint 自身が「投入しない」と出す）と、カードの数・行番号のずれ。どれも文書の直しだけで、コードは変えない。
- 不明点（未確認のまま）: P1 の測定の記録（リポジトリ外）、MobileShell・SecretaryChat が ProtectedRoute の内側か、運営者の画面が呼ぶ API すべてに require_super_admin が付くか。

## 直す点（REVISE）

1. カード 5 行目（L29）。「読んだ節と照合は権限の写しカード（…の冒頭）と同じ。」を、名前を書いた形に置き換える。直した後の文:
   「- 読んだ節: 権限の写しカード（docs/handoff/line-like-speed/perm-cache-card.md:5）と同じ節（guards/00-common.md・03-file.md・04-worktree.md・05-pr.md・10-executor.md・scripts/agent-hooks/cloud/rules.md）。照合も同じ: 全命令は cd <W> で始める・出力は tail/head で上限・変えるファイルは丸ごとの全文・PR は実行役が作らない・出力をファイルに残す命令と tail で読む命令は別の行。」
   （guards の一覧は perm-cache-card.md:5 から写す。設計担当がこの一覧で良いかを確かめる。）
2. カード 227 行（L01）。説明と命令を別の行に分ける。直した後:
   ```
     （落ちた試験があれば、次の命令の出力で名前を見て §3(d) に従う。）
     cd <W> && grep -n -E "FAIL|✗|×" /tmp/sa-unit-all.txt | head -40
   ```
   直した後に `bash scripts/card-lint.sh docs/handoff/line-like-speed/superadmin-cache-card.md` が違反 0 件になることを確かめる。
3. 引用と数のずれ:
   - カード 13 行（P3）: `AnalysisRulesPage.tsx:101・:116-122` → `AnalysisRulesPage.tsx:101・:117-123`。
   - カード 12 行（P2）: `useSuperAdmin.ts:19-42` → `useSuperAdmin.ts:19-43`。
   - カード 17 行（P7）: 「使い手 22 行（`git grep …` の行数）」→「使い手 21 行（`git grep -n 'useSuperAdmin()' -- frontend/src ':!*.test.*'` の 22 行から定義の useSuperAdmin.ts:19 を除いた数）」。
   - カード 16 行（P6）: 「外側の枠と SecretaryChat」→「外側の枠（DesktopShell・MobileShell.tsx:78）と SecretaryChat」。
   - カード 18 行（P8）: 「試験 11 ファイル」→「試験 13 ファイル」。
4. カード 18 行（P8）の後に 1 行足す（差し替えない試験の扱い）。文:
   「- P8b InventoryPage（S frontend/src/pages/inventory/InventoryPage.tsx:146）の試験 8 ファイル（InventoryPage.*.test.tsx）は useSuperAdmin を差し替えず、api だけを差し替える。変更後はこの 8 ファイルで写しが試験の間に残る（rowdrawer は試験ごとに is_super_admin を変える・InventoryPage.rowdrawer.test.tsx:44-55）。審査で 3 回流して全部合格した。手順 4 の全部の試験でここが落ちたら §3(d) に従い、試験に queryClient.clear() を足すなどの直しを自分で考えずに停止する。」
5. カード 14 行（P4）の後に、仮説が外れ得る画面を 1 行足す。文:
   「- P4b 判定の後に自分の API を取る画面（FxRatePage.tsx:51-55・ViewerAccountsPage.tsx:148-152・ViewerTemplatesPage.tsx:71-76・TcgLineImportPage.tsx:146-150・SupplierExtractionRulesPage.tsx:189-193・AnalysisRules の区切りの NeedsReviewTabsPanel.tsx:113・SoldOutResultsPanel.tsx:55）は、変更後に K1 がその API の秒で決まる見込みがある。C4 で 0.1 秒を超えた行があれば、その行の「いちばん遅い API」を要約から書き写し、仮説の誤りがどの画面かを記録する。また TcgDistributionPage（:22-28 文字の読み込み中）と SupplierExtractionRulesPage（:456 何も出さない）は LoadingBlock を出さない。」
   併せて P3 の「loading の間は中身の代わりに LoadingBlock を出す」を「多くの画面（12/14）は loading の間 LoadingBlock を出す」に直す。
6. 状態の行（カード 7 行）を第 2 版にし、受領確認（カード 8 行）を「第 2 版」に合わせる。

## 見張りに止められた文面

- なし（この報告を書く・審査の命令を流すまでの間）。push の結果は最後の発言に書く。
