# recon — gate-diff-3dot（関所の差分を2点→3点に変更）

**対象ADR**: ADR-121

## 問題の現物確認（file:line）

### 差分生成の実コマンド

`scripts/check-process-artifacts.js:529`
```js
changedFiles = execSync(`git diff --name-only "${base}" "${head}"`, { encoding: 'utf8' })
```
2引数形式（`A B`）= `A..B` の2点形式。

### BASE_SHA の供給元

`.github/workflows/process-artifacts-gate.yml:33`
```yaml
BASE_SHA: ${{ github.event.pull_request.base.sha }}
```
`github.event.pull_request.base.sha` = PRの base ブランチ（develop）の**現時点の先端SHA**。固定SHAでも merge-base でもない。

### checkout の fetch 設定

`.github/workflows/process-artifacts-gate.yml:24`
```yaml
fetch-depth: 0
```
全履歴取得済み。merge-base の計算に必要な追加設定なし。

### 差分の共有範囲

`scripts/check-process-artifacts.js:538`
```js
const { hasDangerous, hasRealCode, hasDocsOnly } = classifyChanges(changedFiles);
```
`changedFiles` はこの1行で全分類（hasDangerous / hasRealCode / hasDocsOnly）の共通入力。

## 不明点リスト

未解決ゼロ確認: 該当なし。全項目を現物コードで確認済み。
