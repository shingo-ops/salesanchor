# Design: 指差呼称＋機械照合（触るファイル宣言 vs 実diff）

ステータス: Draft（①KGI承認済み / ②recon確定済み / ③設計＝本書）
日付: 2026-06-23
正本: docs/STANDARD-WORKFLOW.md（矛盾時は正本優先）
参照 recon: 確定後 docs/handoff/sop-touch-files-guard/recon.md としてコミット＋CI緑にし相互参照を確立
関連 ADR: 該当ADRなし（関所機能の拡張。process-artifacts gate / ADR-136 GO手順に準拠）
先行: PR #2521（①共用=許可制・実証済み #2527）

> local-only注意: 本doc・recon・実装は「コミット＋CI緑」で初めて成果物。

---

## 0. 一行サマリ

PRが「触るファイル」を宣言し、宣言に無いファイルを変更していたら process-artifacts gate を赤にする（＝指差呼称＋機械照合）。宣言の仕組みは既存の `### 標準ワークフロー確認` セクションに相乗りし、照合は `scripts/check-process-artifacts.js` に追加する。PR番号2600以上で義務化（それ未満の作りかけは止めない＝猶予）。自動生成ファイルは誤爆防止のため照合から除外する。

---

## ① KGI（PO承認済み）

**KGI（観測可能な事象）:**
- PR番号2600以上のPRが「### 触るファイル」宣言を持ち、宣言に無いファイル（除外対象を除く）を変更していたら、process-artifacts gate が赤になる
- 宣言が無くても赤になる
- PR番号2600未満は本チェックをスキップする（猶予）

**KPI（数値・道のり）:**

| KPI | 測定目標 |
|---|---|
| PR≥2600で宣言外ファイルを変更しpassしたPR数 | CIログ 0件 |
| 宣言と実diffが一致するPRの誤爆ブロック数 | PR確認 0件 |
| 除外対象（lock/snapshot/active-work）による誤爆数 | PR確認 0件 |
| planted violation（宣言外混入→赤）の実証 | 手動PR 1回・赤確認 |

**○×最終確認:** PR≥2600で「Aだけ触る」と宣言したPRにBファイルを混入 → CIが赤になるのを目視。緑なら未達。

---

## ② recon サマリ（file:line・実引用 / 要 recon.md 確定）

### 既存の宣言・照合の現状

- 宣言パーサ `parseSOPDeclaration`（`scripts/check-process-artifacts.js:127`）は `### 標準ワークフロー確認` を読み、`isExempt`/`adrs`/`reconPath`/`designPath`/`mode` を抽出。「触るファイル」は抽出していない
- `runFullCheck` は ADR/recon/設計docの存在を検証するが、宣言ファイルと実diff（`changedFiles`）の照合は一切していない。`changedFiles` も `runFullCheck` に渡っていない
- PRテンプレート `.github/PULL_REQUEST_TEMPLATE.md:26-33` に `### 標準ワークフロー確認` はあるが「触るファイル:」行は無い

### 利用できる既存部品（追加配線不要）

| 変数 | 場所 | 備考 |
|---|---|---|
| `prBody` | `scripts/check-process-artifacts.js:571`（`let` 宣言）〜`:583`取得〜`:585`以降利用 | `main()` 内ローカル＝新チェックから参照可 |
| `changedFiles` | 同`:520`宣言〜`:531`確定 | `main()` 内ローカル＝参照可 |
| `PR_NUMBER` | `process.env.PR_NUMBER`（同`:547`） | 既にワークフローから渡り済み |

**挿入位置候補:** `:584`直後（`prBody`・`changedFiles`確定済み、`hasDangerous`の`exit`前＝危険PRにも適用）

### 誤爆防止：除外対象（git管理下で実在確認済み）

| 種別 | パス | 理由 |
|---|---|---|
| ロック | `frontend/package-lock.json`, `lp/package-lock.json` | npm自動更新 |
| スナップショット | `frontend/tests-e2e/**/*-snapshots/*.png` | ビジュアルテスト自動生成 |
| パイプライン台帳 | `.claude-pipeline/active-work.md` | worktree作成・PR open・マージで自動追記（作業者が宣言不能） |

既存の除外パターンはゼロ（`scripts/check-process-artifacts.js` に `ignore`/`exclude`/`skip` 無し）。

---

## ③ 設計（技術How・Generatorは判断ゼロで実装可）

### 変更1: `.github/PULL_REQUEST_TEMPLATE.md`（`### 標準ワークフロー確認` 内）

既存セクションに1行追加:

```markdown
- 触るファイル: <!-- 変更するファイルをリポジトリ相対パスで改行orカンマ区切りで列挙。PR番号2600以上で必須 -->
```

### 変更2: `parseSOPDeclaration`（`scripts/check-process-artifacts.js:127`付近）

既存抽出（`adrs`等）と同型で `touchFiles` を追加:

```js
// 触るファイル: 行以降を取得し、改行/カンマで分割、空白trim、コメント(<!-- -->)とプレースホルダ除去
const touchFilesMatch = section.match(/触るファイル:\s*([^\n]*(?:\n(?![-*#])[^\n]*)*)/);
let touchFiles = [];
if (touchFilesMatch) {
  touchFiles = touchFilesMatch[1]
    .replace(/<!--[\s\S]*?-->/g, '')   // HTMLコメント除去
    .split(/[\n,]/)
    .map(f => f.trim())
    .filter(f => f.length > 0);
}
return {
  isExempt,
  adr: adrs.length > 0 ? adrs[0] : null,
  adrs,
  reconPath: reconMatch ? reconMatch[1].trim() : null,
  designPath: designMatch ? designMatch[1].trim() : null,
  mode: modeMatch ? modeMatch[1] : null,
  touchFiles,   // ← 追加
};
```

### 変更3: 照合ロジック（`:584`直後に挿入）

```js
// ─── 触るファイル宣言 vs 実diff 照合（PR番号2600以上で義務化） ──────────────
const GRACE_THRESHOLD_PR = 2600;
const TOUCH_FILE_EXCLUDE_PATTERNS = [
  /package-lock\.json$/,
  /-snapshots\/.*\.png$/,
  /^\.claude-pipeline\/active-work\.md$/,
];

if (parseInt(process.env.PR_NUMBER, 10) >= GRACE_THRESHOLD_PR) {
  const targets = changedFiles.filter(
    f => !TOUCH_FILE_EXCLUDE_PATTERNS.some(p => p.test(f))
  );
  if (targets.length > 0) {
    const touchErrors = [];
    if (!declaration || !declaration.touchFiles || declaration.touchFiles.length === 0) {
      touchErrors.push('❌ PR本文に「触るファイル:」の宣言がありません（PR番号2600以上で必須）');
      touchErrors.push('   → 「### 標準ワークフロー確認」の「触るファイル:」にリポジトリ相対パスを記入してください');
    } else {
      const undeclared = targets.filter(f => !declaration.touchFiles.includes(f));
      if (undeclared.length > 0) {
        touchErrors.push(`❌ 宣言外のファイルを変更しています:`);
        undeclared.forEach(f => touchErrors.push(`   - ${f}`));
        touchErrors.push('   → 「触るファイル:」に追記するか、意図しない変更を除去してください');
      }
    }
    if (touchErrors.length > 0) {
      printFailure(touchErrors);
    }
  }
}
// PR番号 < 2600 はこのブロックを通らない＝スキップ（猶予）
```

### 触らない範囲

- 既存の GO記録チェック・ADR/recon/設計doc検証・`classifyFile`・`DANGEROUS_PATTERNS` は変更しない
- `.github/workflows/process-artifacts-gate.yml` は変更しない（`PR_NUMBER` は既に渡っている）

---

## KPI（=KGI検証）

| シナリオ | 期待結果 |
|---|---|
| planted violation（PR≥2600で宣言外混入） | 赤 |
| 宣言一致PR | 緑 |
| 除外対象のみ変更（lock更新等）を宣言せず | 緑（誤爆なし） |
| PR<2600 | スキップ（既存作りかけを止めない） |

---

## 弊害対策

| リスク | 対策 |
|---|---|
| 誤爆 | 除外リストで自動生成系を照合対象外に（①の「誤爆ゼロ」を踏襲） |
| 猶予の正しさ | PR<2600の作りかけは一切止めない（既存作業を妨げない） |
| 大文字小文字・パス表記 | `changedFiles` はリポジトリ相対パス（`git diff --name-only` 準拠）。宣言もリポジトリ相対パスで書く前提をテンプレのコメントに明記 |
| 関所自身への影響 | 本PRは PR番号<2600 で作る限り、この新チェック自体には引っかからない（猶予内）。ただし `scripts/` 変更＝危険な変更でGO必須 |

---

## 計画（段階）

| フェーズ | 内容 |
|---|---|
| P1（本書） | 上記3変更を1PR。PR番号<2600で作成（猶予内＝自分自身は新チェック対象外）。GO必須 |
| P2（実証） | マージ後、PR≥2600相当の planted violation で赤を確認 |
| 将来 | 義務化が定着したら GRACE_THRESHOLD の運用を見直し（常態化防止） |

---

## 継続・再発防止（＋外部・過去事例）

**外部事例（確立済みエビデンス）:**

- **手術安全チェックリスト（WHO/Gawande）:** 着手前の項目確認（指差呼称）で主要合併症が約3分の1、術後死亡が4割超低下。ただし遵守の維持が鍵で、遵守率低下で効果が薄れる＝チェックは機械照合とセットで初めて持続。本設計が「宣言（チェック）＋実diff照合（機械）」の二段にした根拠
- **policy-as-code:** 予防的コントロール（違反時にパイプライン停止＝ERRORモード）が検知のみより有効。本設計の「赤で止める」がこれ
- **Normalization of Deviance（Challenger）:** ルールは緩めると常態化で形骸化。だから猶予（案B的入口）にとどめず、最終ゴールは全PR義務化（案A）。猶予は移行措置

**再発防止:** 本チェック自体が「宣言外の変更（＝#2453のような巻き添え・取りこぼし）」を機械的に止める。

---

## 関所・承認（process-artifacts gate）

- `scripts/check-process-artifacts.js` 変更 = `scripts/`配下 = 危険な変更 → POの GO 記録必須（GO原文 `GO #<PR>` literal）
- recon を `recon.md` としてコミット＋CI緑にし、本 design と相互参照
- 本PRは PR番号<2600 で作成し、自分自身を新チェック対象外にする（猶予内）

### GO記録（PR本文へ転記）

```markdown
### GO記録
- GO発行者: Shingo（shingo-ops）
- 日時: 2026-06-__ HH:MM JST
- GO原文: GO #<PR番号>
- バックアップ確認: 該当なし（scripts/のみ・git管理下で復元可・DB非接触）
```

---

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| PR≥2600で宣言外ファイル変更→赤 | planted violation で目視（○=赤） |
| PR≥2600で宣言なし→赤 | planted violation で目視 |
| 宣言一致PR→緑 | 実証PRで確認 |
| 除外対象のみ変更を宣言せず→緑（誤爆なし） | lock更新等のPRで確認 |
| PR<2600→スキップ（既存作りかけを止めない） | 既存PRで確認 |
| 差分が3ファイルのみ（テンプレ＋scripts） | `git diff --stat` |
| CI全緑（GO記録あり） | CI |
