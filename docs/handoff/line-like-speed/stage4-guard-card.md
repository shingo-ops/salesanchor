# 段 4 の実装カード（見張り: 「読み込み中に中身を消す形」の数を増やさない検査を CI に足す）

- 対象: docs/handoff/line-like-speed/design.md の §3-4 の段 4（「読み込み中に中身を消す形」の数を数える検査を CI に足し、数が増えたら赤（減るのは可）。段 3 の最後で 0 にして固定。合格の線「CI に検査があり、わざと 1 本足すと赤」）・§3-8（段 4 の戻し方）・§3-9（維持の仕組み）・§3-4-22（このカードの場所と基準）。ADR-1054（Accepted）。
- 根拠の写し: S=origin/main bbf873a5dfd578f0f9fd56a9f7bcf7dbd92399f4（PR #5093 の合流の後）。行番号と数はすべてこの sha。2026-11-04 に設計担当が `git -C <本店> grep` で origin/main を直接読んだ。実装の前に最新の origin/main で数を合わせ直す（§3(a)）。
- 読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・guards/03-file.md・guards/04-worktree.md・guards/05-pr.md・guards/10-executor.md・scripts/agent-hooks/cloud/rules.md（段 3 のカードと同じ節。照合も同じ: 全命令は cd <W> で始める・出力は tail/head で上限・新しいファイルは丸ごとの全文・作業場所は new-worktree.sh で作り出力をパイプに通さない・PR は実行役が作らない・出力をファイルに残す命令と tail で読む命令は別の行）。
- 実行役はクラウドの Sonnet。作業場所の作り方はクラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）を正とする。.pr-number・gh-pr-create-safe.sh は使わない。出力には上限を付ける。待つために sleep を使わない。
- 状態: 第 2 版（2026-11-04 設計担当 Claude Opus）。第 1 版のカード審査（クラウドの審査役 Opus・REVISE）の指摘を入れた: `setLoadingList(true)` のように Loading の後ろに名前が続く書き方（S で 4 ファイル・6 行。例: pages/super-admin/SupplierExtractionRulesPage.tsx:173 は描く所 :934 の `{loadingList ? (` で中身を消す）を数えていなかった。数える形を広げ、基準を 51 ファイル・69 行に数え直した。
- 受領確認: 実装役は着手の最初の報告に「段 4 のカード 第 2 版を受け取った・S=bbf873a5d」と書く。

## 0. 設計からの直し・詳しくした点（V4。設計の合格線は変えない）
- V4-1 何を数えるか: frontend/src の .ts・.tsx（名前が .test.ts・.test.tsx で終わるファイルを除く）で、`set〇〇Loading(true)`・`set〇〇Loading〇〇(true)`（正規表現 `set[A-Za-z0-9]*Loading[A-Za-z0-9]*\(\s*true\s*\)`）を書いた行の数を、ファイルごとに数える。理由:
  - 段 3 で直してきた「中身を消す形」は、読み込みを始める時に `setLoading(true)` などで読み込み中の印を立て、描く所で `{loading ? <LoadingState/> : 中身}` と中身を消すもの（段 3 の 1〜7 回目のカードの「変更前」の行）。直した後の画面は、読み込み中の印を初回（写しが無い時）だけ useApiQuery の isPending から作るので、この行が無くなる（例: 予定表は #5093 で S frontend/src/pages/schedule/SchedulePageImpl.tsx から 0 行になった）。
  - 段 0b の u1-count.py の分け方（中身を消す 62 など）は、描く所の `{loading ?` を見るため、直した後の「初回だけ印を出す」画面と直す前の画面を見分けられない（2026-11-04 に S で流すと「中身を消す」34 本のうち、直し済みの画面が多く残る。生の出力は設計担当の手元の /tmp/CC報告ファイル/u1-lines.txt）。数を増やさない見張りには、直す前にだけある「印を立てる行」を数える方が、直した画面を数えない。
  - 行の数（同じ行に 2 つあっても 1）にするのは、`git grep -c` と同じ数え方にして、人が手で同じ数を出せるようにするため。
- V4-2 S での数: 51 ファイル・69 行。設計担当が次の命令で数えた（2026-11-04・S）。
  `git grep -c -E 'set[A-Za-z0-9]*Loading[A-Za-z0-9]*\( *true *\)' origin/main -- 'frontend/src/*.ts' 'frontend/src/*.tsx' ':!*.test.ts' ':!*.test.tsx'`
  この 51 行をそのまま基準の表（§4-B の全文）にする。
- V4-3 数えるものの限り（このカードでは直さない・design §3-4-22 に記録する）:
  - 中身を消さない印（送る・ログインのボタンの印など。例: S pages/login/LoginPage.tsx の 3 行）も数に入る。段 3 の最後で 0 にする時に、1 行ずつ「中身を消す形か」を見て、消さない印には例外の注記（V4-5）を付ける。今は基準に入れたまま数えるだけなので、今の画面は何も変わらない。
  - `setUploading(true)`・`setDownloading(true)` など、Loading が小文字の loading で終わる名前（S で 4 ファイル・5 行）は数えない。送る・取り出すの印で、画面の中身を読み込む印ではないため。
  - 行の中の注記・文字列の中に書かれた `setLoading(true)` も数える（S でそれに当たる行は 0）。数を増やさない見張りなので、多めに数える側に倒す。
  - `setLoading(` と `true)` が 2 行に分かれた書き方は数えない（S で `\( *$` で終わる呼び出しは 0 か所。2 回目の審査で確かめた。数を増やさない見張りなので、分かれた書き方で新しく足すと見逃す。段 3 の最後に数え方を見直す）。
  - 例外の注記（V4-5）は「その行かすぐ上の行」を見るので、注記だけの行のすぐ下の 1 行も外れる。既にある status-ssot-exempt と同じ作り。
  - 名前の前の境目を見ないので、`resetLoadingState(true)` のような名前も数える（S の 69 行はどれも本物の set〇〇Loading）。
  - 読み込み中の印を `useState(true)` の初めの値だけで立て、`setLoading(true)` を書かない画面は数えない（初めの 1 回だけ出す形で、戻った時に中身を消さない）。
- V4-4 赤にする時（基準の表とファイルごとに比べる。基準に無いファイルは基準 0）:
  - 今の数が基準より多い（足した）→ 赤。design の「数が増えたら赤」。
  - 今の数が基準より少ない（直した・消した）→ 赤。同じ PR で基準の表のその行を下げる（0 になったら行を消す）よう、直す場所を出して止める。理由: 下げないまま残すと、あとで同じファイルに 1 本足しても赤にならず、段 3 の最後の「0 にして固定」へ数が戻らない。design の「減るのは可」は、数を減らす変更を止めないという意味で、基準を下げれば緑になるので、減らす変更は通る。基準にあるファイルが無くなった時も、今の数 0 として同じ扱い。
  - 段 3 の残りのカードは、画面を直す PR の中で基準の表の行を下げる手順を持つ（このカードの後に書くカードに入れる）。
- V4-5 例外: その行か、すぐ上の行に `loading-clear-exempt: <理由>` と書き、理由が空でなければ、その行は数えない（S frontend/scripts/check-status-direct-writes.js の `status-ssot-exempt:` と同じ形）。このカードでは例外を 1 つも付けない。
- V4-6 自己点検: 検査は動くたびに、まず作り物のフォルダ（OS の一時フォルダ）で次の 3 つを確かめ、1 つでも違えば赤にする。こうして「わざと 1 本足すと赤」を、CI が動くたびに確かめ続ける（段 4 の合格の線を一度きりの試しにしない）。
  - 基準と同じ数 → 問題 0 件。試験のファイル（.test.tsx）と例外の注記の行は数えない。
  - 1 本足す → 問題 1 件（増えた）。
  - 1 本消す → 問題 1 件（減った）。
- V4-7 CI への入れ方: package.json に `check:loading-clear` を足し、`check:all` の並びの最後に足す。Frontend Check（S .github/workflows/frontend-check.yml）が frontend/** の変更のある PR で `npm run check:all` を流すので、.github/workflows は触らない（S frontend-check.yml:3-6 の paths は frontend/**）。
- V4-8 時間: 数えるのは src の .ts・.tsx を 1 回読むだけで、ほかの check-*.js と同じ重さ。

## 1. 触るファイル（変更前→変更後）
| # | ファイル | 変更前 | 変更後 |
|---|---|---|---|
| 1 | frontend/scripts/check-loading-clear.js | 無い | 新しく作る（§4-A 全文） |
| 2 | frontend/scripts/loading-clear-baseline.json | 無い | 新しく作る（§4-B 全文。51 ファイル・69 行） |
| 3 | frontend/package.json | `check:status-direct-writes` が check の最後（S :43）、`check:all` の並びの最後が `\"npm run check:status-direct-writes\"`（S :46） | `check:loading-clear` を 1 行足し、`check:all` の並びの最後に足す（§4-C） |
| 4 | docs/handoff/line-like-speed/stage4-guard-card.md | 無い | このカード（設計担当が書いた。実装役は触らない） |
| 5 | docs/handoff/line-like-speed/design.md | §3-4-21 まで | §3-4-21-a（予定表の受入）と §3-4-22（このカードの場所と基準）を書き足し済み（設計担当。実装役は触らない） |
| 6 | .claude-pipeline/active-work.d/release-line-like-speed-stage4-guard.md | 無い | 作業の札（設計担当。実装役は触らない・commit しない） |

## 2. 触らない範囲
- frontend/src は 1 文字も触らない（数えるだけ。今の画面は変わらない）。
- backend/・migrations/・.github/workflows/・scripts/（リポジトリ直下）・tests/prod-check/ は触らない。
- frontend/scripts の §1 #1・#2 以外のファイル、frontend/package.json の §4-C 以外の行（依存・ほかの script）は触らない。package-lock.json は変わらない（依存を足さない）。

## 3. 実装役が先に確かめること（想定分岐つき）
- (a) 最新の origin/main で V4-2 の命令（`git grep -c -E 'set[A-Za-z0-9]*Loading[A-Za-z0-9]*\( *true *\)' origin/main -- 'frontend/src/*.ts' 'frontend/src/*.tsx' ':!*.test.ts' ':!*.test.tsx'`）を流し、51 行・合計 69 で §4-B と同じか。違えば停止し、BLOCKED: で生の出力と S からの `git diff --stat bbf873a5dfd578f0f9fd56a9f7bcf7dbd92399f4 origin/main -- frontend/src | tail -20` を報告する（基準の表を自分で直さない）。
- (b) frontend/package.json の `"check:status-direct-writes": "node scripts/check-status-direct-writes.js",` が 1 か所、`check:all` の値の最後が `\"npm run check:status-direct-writes\""` で終わること。違えば停止して `grep -n "check:status-direct-writes\|check:all" frontend/package.json` の出力を報告する。
- (c) 手順 3 で検査を流した結果が「✅ loading-clear: 基準どおり（51 ファイル・69 行）」でない時は、基準の表を直さずに停止し、出力を NEEDS_DECISION: で返す（JS の `\s*` と git grep の ` *` の違いで数が変わった時など）。
- (d) 手順 4 で 1 行足した時に赤（終わりの番号 1）にならない時、足した行を消した後に緑に戻らない時は、停止して生の出力を返す。試しに足した行は commit しない（手順 4 の最後で `git status --short` が §1 の #1〜#3 だけ）。

## 4-A. #1 frontend/scripts/check-loading-clear.js（新しく作る・全文）
```js
#!/usr/bin/env node
/**
 * check-loading-clear.js（ADR-1054 段 4・docs/handoff/line-like-speed/stage4-guard-card.md）
 *
 * 「読み込み中に中身を消す形」の数を増やさない見張り。
 *
 * 数えるもの: src の .ts・.tsx（*.test.ts・*.test.tsx を除く）で、
 *   set〇〇Loading(true) を書いた行の数（ファイルごと・同じ行に 2 つあっても 1）。
 * 基準: scripts/loading-clear-baseline.json（src からの道すじ → 行の数）。
 *   基準に無いファイルは基準 0。
 * 赤になる時:
 *   1. 今の数が基準より多い（足した）
 *   2. 今の数が基準より少ない（直した・消した）→ 同じ変更で基準の表を下げる（0 なら行を消す）
 * 例外: その行か、すぐ上の行に `loading-clear-exempt: <理由>` があれば数えない（理由は空にしない）。
 * 自己点検: 動くたびに、まず一時フォルダの作り物で「同じ数は緑・1 本足すと赤・1 本消すと赤」を確かめる。
 *
 * 使い方: node scripts/check-loading-clear.js
 * CI: npm run check:loading-clear（check:all に入っている）
 */

import { mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from 'fs';
import { tmpdir } from 'os';
import { dirname, extname, join, relative, sep } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SRC_DIR = join(__dirname, '../src');
const BASELINE_FILE = join(__dirname, 'loading-clear-baseline.json');
const PATTERN = /set[A-Za-z0-9]*Loading[A-Za-z0-9]*\(\s*true\s*\)/;
const EXEMPT = /loading-clear-exempt:\s*\S/;
const SKIP_DIRS = new Set(['node_modules', 'coverage', 'dist']);

function collectFiles(dir) {
  const results = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      if (!SKIP_DIRS.has(entry)) results.push(...collectFiles(full));
    } else if ((extname(entry) === '.ts' || extname(entry) === '.tsx') && !/\.test\.tsx?$/.test(entry)) {
      results.push(full);
    }
  }
  return results;
}

function countLines(srcDir) {
  const counts = {};
  for (const file of collectFiles(srcDir)) {
    const lines = readFileSync(file, 'utf8').split('\n');
    let n = 0;
    lines.forEach((line, i) => {
      if (!PATTERN.test(line)) return;
      const prevLine = i > 0 ? lines[i - 1] : '';
      if (EXEMPT.test(line) || EXEMPT.test(prevLine)) return;
      n += 1;
    });
    if (n > 0) counts[relative(srcDir, file).split(sep).join('/')] = n;
  }
  return counts;
}

function compare(counts, baseline) {
  const problems = [];
  const names = [...new Set([...Object.keys(counts), ...Object.keys(baseline)])].sort();
  for (const name of names) {
    const now = counts[name] ?? 0;
    const base = baseline[name] ?? 0;
    if (now > base) {
      problems.push(`増えた: src/${name} 基準 ${base} → 今 ${now}`);
    } else if (now < base) {
      problems.push(`減った: src/${name} 基準 ${base} → 今 ${now}（scripts/loading-clear-baseline.json のこの行を ${now} に下げる。0 なら行を消す）`);
    }
  }
  return problems;
}

function selfTest() {
  const root = mkdtempSync(join(tmpdir(), 'loading-clear-'));
  try {
    mkdirSync(join(root, 'pages'));
    const baseline = { 'pages/A.tsx': 1 };
    writeFileSync(join(root, 'pages/A.tsx'), 'setLoading(true);\nsetOpen(true);\n');
    writeFileSync(join(root, 'pages/A.test.tsx'), 'setLoading(true);\n');
    writeFileSync(join(root, 'pages/B.tsx'), '// loading-clear-exempt: 送るボタンの印\nsetSendLoading(true);\n');
    const same = compare(countLines(root), baseline).length === 0;
    writeFileSync(join(root, 'pages/A.tsx'), 'setLoading(true);\nsetListLoading( true );\n');
    const added = compare(countLines(root), baseline).length === 1;
    writeFileSync(join(root, 'pages/A.tsx'), 'setOpen(true);\n');
    const removed = compare(countLines(root), baseline).length === 1;
    return same && added && removed;
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
}

if (!selfTest()) {
  console.log('❌ loading-clear: 自己点検に失敗（数え方が壊れている）');
  process.exit(1);
}

const baseline = JSON.parse(readFileSync(BASELINE_FILE, 'utf8'));
const counts = countLines(SRC_DIR);
const problems = compare(counts, baseline);
const total = Object.values(counts).reduce((sum, n) => sum + n, 0);

if (problems.length === 0) {
  console.log(`✅ loading-clear: 基準どおり（${Object.keys(counts).length} ファイル・${total} 行）`);
  process.exit(0);
}

for (const p of problems) console.log(`❌ ${p}`);
console.log(`\n❌ loading-clear: ${problems.length} 件`);
console.log('   読み込み中に中身を消す形（set〇〇Loading(true)）を増やさない（ADR-1054 段 4）。');
console.log('   新しい読み込みは src/lib/query/apiQuery.ts の useApiQuery を使う。');
console.log('   中身を消さない印（送るボタンなど）は、その行かすぐ上の行に loading-clear-exempt: <理由> を書く。');
process.exit(1);
```

## 4-B. #2 frontend/scripts/loading-clear-baseline.json（新しく作る・全文）
```json
{
  "components/ChannelTypeCombobox.tsx": 1,
  "components/CommissionPanel.tsx": 1,
  "components/CompanyContactSelector.tsx": 1,
  "components/ContactChannelLinks.tsx": 1,
  "components/CountryCombobox.tsx": 1,
  "components/FedExRateModal.tsx": 1,
  "components/InventorySearchBar.tsx": 1,
  "components/MergeCompanyModal.tsx": 1,
  "components/MergeContactModal.tsx": 1,
  "components/MergeLeadModal.tsx": 2,
  "components/OrderFinancialPanel.tsx": 1,
  "components/PurchaseDetailPanel.tsx": 1,
  "components/ShippingDetailPanel.tsx": 1,
  "contexts/UiPrefsContext.tsx": 1,
  "features/supplier-master/SupplierDetailDrawer.tsx": 1,
  "features/tcg-analysis-review/DiagnosticsDrawer.tsx": 1,
  "features/tcg-analysis-review/SupplierDetailView.tsx": 1,
  "features/tcg-analysis-review/V102PostsTab.tsx": 1,
  "features/tcg-import-workflow/useImportWorkflow.ts": 1,
  "features/tcg-product-import/TcgProductDetailDrawer.tsx": 2,
  "hooks/useFeatures.ts": 1,
  "pages/admin/InventoryVisibilityPage.tsx": 1,
  "pages/buyback-prices/BuybackAlertModal.tsx": 2,
  "pages/buyback-prices/BuybackByProductPage.tsx": 1,
  "pages/buyback-prices/BuybackPendingReviewModal.tsx": 1,
  "pages/buyback-prices/BuybackPriceHistoryDrawer.tsx": 2,
  "pages/buyback-prices/BuybackPricesPage.tsx": 1,
  "pages/buyback-prices/BuybackProductHistoryDrawer.tsx": 2,
  "pages/company-detail/CompanyConvLogsTab.tsx": 1,
  "pages/conditions/ConditionsPage.tsx": 1,
  "pages/goal-setting/GoalSettingPage.tsx": 1,
  "pages/inbox/InboxKartePanel.tsx": 2,
  "pages/inbox/OutboundTranslationPreview.tsx": 1,
  "pages/inbox/useInboxState.ts": 3,
  "pages/integrations/FedexEtdSetupGuide.tsx": 1,
  "pages/inventory/InventoryPage.tsx": 1,
  "pages/login/LoginPage.tsx": 3,
  "pages/product-categories/ProductCategoriesPage.tsx": 1,
  "pages/products/ProductEditPage.tsx": 1,
  "pages/quote-detail/QuoteDetailPage.tsx": 1,
  "pages/super-admin/ExtractionPromptConfigTab.tsx": 1,
  "pages/super-admin/SupplierExtractionRulesPage.tsx": 2,
  "pages/super-admin/TcgLineImportPage.tsx": 2,
  "pages/super-admin/components/AiJobsSection.tsx": 1,
  "pages/super-admin/components/AnalysisDashboardPanel.tsx": 6,
  "pages/super-admin/components/DbViewerPanel.tsx": 2,
  "pages/super-admin/components/ExtractionErrorLogPanel.tsx": 1,
  "pages/super-admin/components/LlmUsageSection.tsx": 1,
  "pages/super-admin/components/NeedsReviewTabsPanel.tsx": 1,
  "pages/super-admin/components/ProductMasterPanel.tsx": 1,
  "pages/super-admin/components/SoldOutResultsPanel.tsx": 1
}
```

## 4-C. #3 frontend/package.json（2 か所）
- C1 変更前（S :43・1 行）:
  `    "check:status-direct-writes": "node scripts/check-status-direct-writes.js",`
  変更後（2 行。上の行はそのまま、下に 1 行足す）:
  `    "check:status-direct-writes": "node scripts/check-status-direct-writes.js",`
  `    "check:loading-clear": "node scripts/check-loading-clear.js",`
- C2 変更前（S :46 の `check:all` の値の終わり）: `\"npm run check:status-direct-writes\""`
  変更後: `\"npm run check:status-direct-writes\" \"npm run check:loading-clear\""`
  （`check:all` のほかの部分・`--kill-others-on-fail --max-processes 6` は変えない。値は `concurrently ` で始まったまま＝S scripts/check-concurrently-usage.js が通る。）

## 4-M. 実装役の手順（1 手順 1 命令。<W> は手順1 で作られた作業場所の絶対パス）
手順1. クラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）どおり、作業場所を作り、push 済みの枝の先頭に合わせる（設計担当が §1 #4・#5 を push 済み）。
  cd "$(git rev-parse --show-toplevel)" && bash scripts/new-worktree.sh release/line-like-speed-stage4-guard
  （出力に出た作業場所の絶対パスを <W> として報告に書く。）
  cd <W> && git fetch origin release/line-like-speed-stage4-guard
  cd <W> && git switch -C release/line-like-speed-stage4-guard origin/release/line-like-speed-stage4-guard
  cd <W> && git rev-parse HEAD origin/release/line-like-speed-stage4-guard
  （2 行が同じことを確かめる。違えば停止して BLOCKED: で報告する。main は取り込まない。reset・rebase・force・merge・pull は使わない）
  cd <W> && ./scripts/dev/executor-preflight.sh > /tmp/s4-preflight.txt 2>&1
  cd <W> && grep -n "FAIL" /tmp/s4-preflight.txt | head -20
  cd <W> && grep -n "origin/main は存在" /tmp/s4-preflight.txt | head -3
  （FAIL の行が次の 3 つのうちのどれかだけなら続ける: `GitHub API に到達不可` の 1 件・`gh auth switch --hostname github.com --user shingo-cc` の失敗の 1 件・その結果の `PREFLIGHT FAIL` の行。理由は段 3 の 1 回目のカード §4-M 手順1 と同じ。続ける時は `[OK]   origin/main は存在` の行があることを 2 つ目の grep で確かめ、無ければ停止する。ほかの FAIL が 1 件でもあれば停止し、BLOCKED: で grep の出力を報告する。）
  cd <W> && git fetch origin main
  cd <W> && git grep -c -E 'set[A-Za-z0-9]*Loading[A-Za-z0-9]*\( *true *\)' origin/main -- 'frontend/src/*.ts' 'frontend/src/*.tsx' ':!*.test.ts' ':!*.test.tsx' > /tmp/s4-grep.txt
  cd <W> && wc -l < /tmp/s4-grep.txt
  cd <W> && awk -F: '{s+=$NF} END {print s}' /tmp/s4-grep.txt
  （51 と 69 であること。§3(a)。）
手順2. 依存を入れ、§3(b) を確かめる。
  cd <W>/frontend && npm ci > /tmp/s4-ci.txt 2>&1
  cd <W> && tail -5 /tmp/s4-ci.txt
  cd <W>/frontend && grep -n "check:status-direct-writes" package.json
手順3. §4-A の全文で #1 を、§4-B の全文で #2 を作り、§4-C のとおり #3 を直す。検査を流す。
  cd <W>/frontend && node scripts/check-loading-clear.js > /tmp/s4-run.txt 2>&1; echo "exit=$?" >> /tmp/s4-run.txt
  cd <W> && tail -5 /tmp/s4-run.txt
  （`✅ loading-clear: 基準どおり（51 ファイル・69 行）` と `exit=0`。違えば §3(c)。）
  cd <W>/frontend && npm run check:concurrently > /tmp/s4-conc.txt 2>&1
  cd <W> && tail -5 /tmp/s4-conc.txt
手順4. わざと 1 本足して赤になること、消すと緑に戻ることを確かめる（試しの行は commit しない）。
  cd <W>/frontend && printf '%s\n' 'export const probe = (setLoading: (v: boolean) => void) => setLoading(true);' > src/__loading_clear_probe.ts
  cd <W>/frontend && node scripts/check-loading-clear.js > /tmp/s4-red.txt 2>&1; echo "exit=$?" >> /tmp/s4-red.txt
  cd <W> && tail -6 /tmp/s4-red.txt
  （`❌ 増えた: src/__loading_clear_probe.ts 基準 0 → 今 1` と `exit=1`。違えば §3(d)。）
  cd <W>/frontend && node -e "require('fs').unlinkSync('src/__loading_clear_probe.ts')"
  cd <W>/frontend && node scripts/check-loading-clear.js > /tmp/s4-green.txt 2>&1; echo "exit=$?" >> /tmp/s4-green.txt
  cd <W> && tail -3 /tmp/s4-green.txt
  （`✅ ... （51 ファイル・69 行）` と `exit=0`。）
  cd <W> && git status --short | head -10
  （§1 の #1〜#3 だけ。§3(d)。）
手順5. 全部の点検を流す（CI の Frontend Check と同じ入口）。
  cd <W>/frontend && npm run generate:api-types > /tmp/s4-gen.txt 2>&1
  cd <W> && tail -3 /tmp/s4-gen.txt
  cd <W>/frontend && npm run check:all > /tmp/s4-all.txt 2>&1; echo "exit=$?" >> /tmp/s4-all.txt
  cd <W> && grep -n "loading-clear" /tmp/s4-all.txt | head -5
  cd <W> && tail -15 /tmp/s4-all.txt
  （exit=0。loading-clear の ✅ の行が出ること。ほかの点検で落ちたら、§1 の変更と関係あるかを出力で確かめ、関係ないなら直さずに生の出力を NEEDS_DECISION: で返す。）
手順6. 変わったファイルを確かめる。
  cd <W> && git diff --stat origin/release/line-like-speed-stage4-guard | tail -6
  cd <W> && git diff origin/release/line-like-speed-stage4-guard -- frontend/package.json | head -30
手順7. commit する。
  cd <W> && git add frontend/scripts/check-loading-clear.js frontend/scripts/loading-clear-baseline.json frontend/package.json
  cd <W> && git commit -m "ci: 読み込み中に中身を消す形の数を増やさない検査を足す（ADR-1054 段4）"
手順8. commit が在ることを確かめてから push する（--no-verify は使わない。push の前の検査が × なら直してから push。fast-forward でないと断られたら直さず BLOCKED:）。
  cd <W> && git log -3 --oneline
  cd <W> && git push -u origin release/line-like-speed-stage4-guard
手順9. 報告を返す。PR は作らない（設計担当が手元で作る）。報告の 1 つの発言は 600 文字以内にして、番号付きの発言に分ける。報告には手順ごとの tail の出力（生のまま）と、§3(a)〜(d) の結果を書く。

## 4. GO と承認・PO の操作
- PO の実装承認: 2026-11-03 PO「つぎを進める」（段 3 の 7 回目の受入の後の次の段）。段 4 の中身と合格の線は design §3-4（PO 承認済み 2026-10-31 21:55 JST 選択「1」）のとおりで、このカードは合格の線を変えない（V4-4 の「減った時も基準を下げるまで赤」は、承認済みの「減るのは可」を、基準を下げれば通る形で満たす）。ADR-1054 は Accepted。このカードの審査合格の後に、設計担当がクラウドの Sonnet へ渡す。
- 触るのは frontend の検査 2 ファイルと package.json の 2 か所と書類だけで、migrations・deploy.yml・本番 scripts を含まない（番号付き GO の要る危ない PR ではない）。本番の画面は変わらない（frontend/src を触らない）。マージは PO の委任に基づき設計担当（Claude Opus）が、マージ前の審査役の APPROVE と確認がすべて pass の後に行う。
- PO が操作することはない。

## 5. 受入（○×）
| # | 基準 | 検証方法 |
|---|---|---|
| H1 | 検査が基準どおりで緑（51 ファイル・69 行）。自己点検が通る | /tmp/s4-run.txt の最後と、PR の Frontend Check（check:all）が success で、その記録に `✅ loading-clear: 基準どおり（51 ファイル・69 行）` がある |
| H2 | わざと 1 本足すと赤、消すと緑 | /tmp/s4-red.txt（exit=1・増えたの行）と /tmp/s4-green.txt（exit=0）。CI が動くたびに自己点検（V4-6）でも確かめる |
| H3 | 変わったのは §1 の #1〜#5 だけ（#6 は commit しない）。frontend/src は変わっていない | gh pr diff --name-only |
| H4 | 必須の確認がすべて pass | gh pr checks |
| H5 | マージの後、main の Frontend Check が通る形のまま（次に frontend を触る PR の check:all で loading-clear が緑） | 次に frontend/** を触る PR の Frontend Check の記録（設計担当。段 3 の次のカードの PR で確かめる） |
