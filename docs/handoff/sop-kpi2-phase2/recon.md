# recon.md — SOP KPI2 Phase 2（②測定 実コード裏取り）

**対象**: ADR-121 process-artifacts gate の②測定フェーズで「何が実際に測れるか」を確定する
**調査日**: 2026-06-09
**手法**: 実コード file:line 参照 + gh API 実証クエリ

---

## 1. 自己申告免除

### 免除判定の file:line

- 免除マーカー検出: `scripts/check-process-artifacts.js:86`
  ```
  const isExempt = /- \[x\]\s*免除/i.test(section);
  ```
- 免除でのearly exit: `scripts/check-process-artifacts.js:395-398`
  ```javascript
  if (declaration && declaration.isExempt) {
    console.log('✅ 自律クラフト免除宣言あり — pass（記録）');
    process.exit(0);
  }
  ```

### 正確なマーカー書式

PR本文の `### 標準ワークフロー確認` セクション内に以下を記載:
```
- [x] 免除（理由を記述）
```
- セクション検出正規表現: `scripts/check-process-artifacts.js:80-81`
  `/###\s*標準ワークフロー確認\s*\n([\s\S]*?)(?=\n###|\n##|\n#|$)/`
- `[x]` は大文字小文字不問（`/i` フラグ）

### マージ済みPR本文 — 集計可否

**測れる。** `gh api repos/{owner}/{repo}/pulls?state=closed` は `.body` フィールドを返す。
実証:
```sh
gh api "repos/shingo-ops/salesanchor/pulls?state=closed&per_page=3" \
  --jq '[.[] | {number, body_excerpt: .body[0:100]}]'
# → body_excerpt に本文先頭100文字が入ることを確認済み
```
- per_page 最大100、pagination で全件取得可能
- `免除` を含む body をフィルタすれば免除PR件数が取れる

### 変更規模（diff行数/ファイル数） — 集計可否

**測れる。** `gh api repos/{owner}/{repo}/pulls/{n}` は `additions`, `deletions`, `changed_files` を返す。
実証（PR #1802）:
```json
{"additions":1191, "changed_files":13, "deletions":1}
```
- 大型変更（例: changed_files > 20 or additions > 500）の免除 = 乱用検知に利用可能

---

## 2. 危険承認

### 危険経路の判定 — file:line

DANGEROUS_PATTERNS 定義: `scripts/check-process-artifacts.js:43-51`
```javascript
const DANGEROUS_PATTERNS = [
  /^migrations\//,                              // :44
  /^\.github\/workflows\/deploy\.yml$/,         // :45
  /^scripts\/.*migrat/i,                        // :46
  /^scripts\/.*deploy/i,                        // :47
  /^scripts\/aeon-dispatch\.sh$/,               // :48
  /^scripts\/run_all_migrations\.sh$/,          // :49
  /^scripts\/smoke_test_post_deploy\.sh$/,      // :50
];
```
判定処理: `scripts/check-process-artifacts.js:63-64`（DANGEROUS を最初にチェック）

### 承認の判定 — file:line

- 承認取得: `scripts/check-process-artifacts.js:364-369`
  `gh api "repos/${repo}/pulls/${prNumber}/reviews" --jq '[.[] | select(.state == "APPROVED") | .user.login]'`
- 認可済み承認者リスト: `scripts/check-process-artifacts.js:29`
  `const AUTHORIZED_APPROVERS = ['shingo-ops', 'Hikky-dev'];`
- 承認有無チェック: `scripts/check-process-artifacts.js:375`
  `const hasAuth = approvals.some(a => AUTHORIZED_APPROVERS.includes(a));`

### 誰がどのPRを承認したか — API集計可否

**測れる。** `gh api repos/{owner}/{repo}/pulls/{n}/reviews` は `user.login` + `state` を返す。
- AUTHORIZED_APPROVERS に照合すれば「承認者別・危険PR承認件数」が取れる
- 全closedPR × reviews の掛け算クエリは rate limit 5000/h 内で現実的（PRが1000件未満なら問題なし）

---

## 3. 緊急モード+宿題

### 宣言方法 — file:line

- 緊急モード解析: `scripts/check-process-artifacts.js:90`
  `const modeMatch = section.match(/モード:\s*(些細|緊急)/);`
- PR本文記載方式: `### 標準ワークフロー確認` 内に `モード: 緊急`
- 緊急でのpass+起票: `scripts/check-process-artifacts.js:385-388`

### 宿題issue label/title書式 — file:line

- ラベル: `sop-followup` — `scripts/check-process-artifacts.js:211`
- タイトル書式: `scripts/check-process-artifacts.js:183`
  `[sop-followup] PR #${prNumber} 緊急承認 — 宿題期限: ${deadline}`
- 期限の持ち方: タイトル内に埋め込み（`宿題期限: YYYY-MM-DD`）
- 期限抽出正規表現（monitor側）: `.github/workflows/sop-followup-monitor.yml:36`
  `grep -oP '(?<=宿題期限: )\d{4}-\d{2}-\d{2}'`
- 期限 = マージから48時間後: `scripts/check-process-artifacts.js:182`
  `const deadline = new Date(Date.now() + 48 * 60 * 60 * 1000).toISOString().split('T')[0];`

### 集計可否

| 指標 | 可否 | 方法 |
|------|------|------|
| 緊急PR件数（累計） | **可** | `gh issue list --label sop-followup --state all` |
| 期限超過の宿題 | **可** | タイトルから期限抽出 → `date -d` 比較（monitor実装済み） |
| 期限内完了率 | **可（粗い）** | closed issueをopenと合計で割る（本来「完了PR提出」確認が必要だが自動化困難） |

**注意**: `sop-followup` ラベルは現時点でリポジトリに存在しない（発行件数ゼロ）。初回 `gh issue create --label sop-followup` 時に自動生成される。

---

## 4. モードのラベル — PRに既についているか

**付いていない。**

- `check-process-artifacts.js` 全体を調査: `gh label create` / `gh pr edit --add-label` の呼び出しなし
- `.github/workflows/sop-followup-monitor.yml:15` の permissions は `issues: read`（PR write権限なし）
- 既存ラベル確認: `gh api repos/.../labels` で `sop`/`emergency`/`exempt`/`danger` 系ラベルは0件
- 既マージPR（#1802, #1812）のラベルを実確認: `{"labels": []}` 両件とも空

**→ 設計前提**: ラベルによる集計はゼロから追加が必要。
現状はPR本文（body）のパースでのみモード判別可能。

---

## 5. 誤検知率

### 赤→緑 の件数は測れるか

**測れる（粗い）。**
```sh
gh api "repos/{owner}/{repo}/actions/runs?workflow_id=process-artifacts-gate.yml&per_page=100" \
  --jq '.workflow_runs[] | {conclusion, pr: .pull_requests[0].number}'
```
同一PR番号で `failure` → その後 `success` が存在するパターンを検出可能（実証済み: PR #1814がfailure+successを持つ）。

### 正当な修正 vs 誤検知回避 — 自動区別の可否

**不可能（自動区別は実装困難）。**

- ゲートの pass 理由は標準出力ログに出力される（例: `✅ 自律クラフト免除宣言あり` / `✅ process-artifacts gate PASSED`）
- ただし Actions run log は structured field ではなくテキストであり、API経由で結論の「理由」は取得不可
- `failure → 免除宣言追加 → success` と `failure → recon/design 正当提出 → success` を自動判別するには PR body diff が必要だが、これはAPIで取れない

**代替提案（2択）**:

| 案 | 内容 | 精度 |
|----|------|------|
| A. 粗い摩擦指標 | 「同一PRでfailure runが存在した件数 / 全PR件数」を週次レポート | 粗い（理由不問） |
| B. 免除PR比率 | マージ済みPRのbodyをスキャンして `- [x] 免除` 含有率を集計 | 中（免除の正当性は問わない） |

---

## 6. 取得手段・既存資産・通知先

### gh API アクセス範囲（個人アカウント・Org無し）

| データ | API endpoint | 取得可否 |
|--------|-------------|---------|
| PR本文（closed含む） | `pulls?state=closed` | **可** |
| PR diff stats | `pulls/{n}` → `.additions/.deletions/.changed_files` | **可** |
| PR reviews | `pulls/{n}/reviews` | **可** |
| Issues（label絞込） | `issues?labels=sop-followup` | **可** |
| Actions run conclusion | `actions/runs?workflow_id=...` | **可** |
| PR labels | `pulls/{n}` → `.labels` | **可**（現状全件空） |

- **Rate limit**: 5000/h（認証済み）。残4746確認済み。月次集計程度なら問題なし。
- **PR総数**: 現在約1819件。全件 reviews 取得でも3000リクエスト以内。

### 再利用できる既存パターン

| 既存ファイル | 使えるパターン |
|------------|--------------|
| `.github/workflows/sop-followup-monitor.yml` | cron + `gh issue list --label` + Discord通知の骨格（直接流用可） |
| `.github/workflows/zombie-report.yml` | cron + issue生成 + `gh label create --force` の冪等ラベル作成パターン |
| `.github/workflows/weekly-stale-pr.yml` | `pulls?state=open` pagination + Discord通知パターン |
| `scripts/notify/discord-owner-ping.sh` | Discord webhook送信（パラメータ1つで呼べる） |

### 既存の計測資産

**ゼロ。** SOP gate以外にプロセス遵守を定量計測する既存資産なし（上記は通知インフラのみ）。

### 通知の出し先

- `.github/workflows/sop-followup-monitor.yml:60`: `bash scripts/notify/discord-owner-ping.sh "$MSG"` で Discord 送信
- `secrets.DISCORD_WEBHOOK_SCHEDULED_REPORT` が環境変数として利用可能（monitor/zombie/stale-prで共通）
- → **新規測定スクリプトも同 webhook + 同シェル関数で通知できる**

---

## 分類まとめ

| 指標 | 分類 | 備考 |
|------|------|------|
| 免除PR件数 | **測れる** | closed PR body scan |
| 免除PR差分規模 | **測れる** | pulls/{n}.changed_files |
| 危険PR承認件数・承認者 | **測れる** | pulls/{n}/reviews |
| 緊急PR件数 | **測れる** | sop-followup issues |
| 期限超過宿題件数 | **測れる** | monitor実装済み |
| 期限内完了率 | **測れる（粗い）** | closed/total issues |
| ゲート赤→緑件数 | **測れる（粗い）** | actions/runs |
| 赤→緑の正当性（誤検知か修正か） | **測れない** | ログ解析不可・手動報告か諦め |
| PRへのモードラベル集計 | **要追加** | ゲートにラベル付け追加が前提 |
