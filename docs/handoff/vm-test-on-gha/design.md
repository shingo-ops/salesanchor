# 設計: 仮想マシンが要る試験を GitHub で行う（vm-test-on-gha）

この文書は何か(専門用語なしの1行): Mac で試験用の仮想マシンを作るのをやめ、GitHub のコンピュータで試すための作り方・合格条件・見張りを決めた設計書。

親: [docs/specs/vm-test-on-gha/README.md](../../specs/vm-test-on-gha/README.md)／recon: [recon.md](./recon.md)
区分（ADR-1015）: **A**（scripts/ と正本文書 AGENTS.md を触る）。PR は Draft・GO 記録必須（ADR-136。GO は ADR-1003 により POの委任に基づくClaude Opus発行で可。workflow-lint.yml は触らない）。
版: v1（2026-10-16）。状態: 設計案作成済み・Opus 自己審査 APPROVE（§10）・KGI は PO 承認待ち。

## 1. 目的と成功条件
- 目的: 8GB の Mac で一時的な仮想マシン（4GB 等）を作らないようにして、開発中の重さを減らす。試験の質は落とさない。
- KGI: [kgi.md](../../specs/vm-test-on-gha/kgi.md) K1〜K5（本書 §5 が正本）。

## 2. 対象と対象外
- 対象（新規 5・変更 2）:
  1. 新規 `.github/workflows/sandbox-test.yml` — 手動起動だけの試験場。
  2. 新規 `tests/sandbox/smoke.sh` — 最初の試験（postgres:16 を起動して `select 1`）。K1 の確認用。
  3. 新規 `tests/sandbox/README.md` — 試験の置き方（1 ファイル＝1 試験、名前は英小文字・数字・ハイフン）。
  4. 新規 `scripts/ci/no-mac-vm-guard.sh` ＋ `scripts/tests/test-no-mac-vm-guard.sh` — 新しく足した行に「Mac で一時 VM を作る命令」があれば止める。
  5. 新規 `.github/workflows/no-mac-vm-guard.yml` — 上の見張りを PR ごとに動かす（必須チェックには登録しない）。
  6. 変更 `docs/ops/runner-commands.md` — 新節「仮想マシンが要る試験（GitHub で行う）」。**規則の正本はこの節 1 か所**。
  7. 変更 `AGENTS.md` — 開発手順の近く（:117-124 付近）に 1 行「仮想マシンが要る試験は Mac で作らず docs/ops/runner-commands.md の該当節に従う」（参照のみ・規則の本文は書かない）。
  - 付随: docs/specs/README.md に索引 1 行（本 PR で追加済み）。
- 対象外（触らない）: Ruleset／必須チェック登録、workflow-lint.yml、colima-idle-stop 一式、Mac の profile `default`・`sa-private-ci`、他テーマのカード（docs/handoff/ai-ops-247/card-stage3-bin-d.md 等。実装中の他セッションの作業）、既存 workflow。

## 3. 変更前後
| 項目 | 変更前 | 変更後 |
|---|---|---|
| 一時的な試験環境 | カードが `colima start --profile ... --memory 4` を Mac で指示（card-stage3-bin-d.md:308） | `gh workflow run sandbox-test.yml --ref <ブランチ> -f test=<名前>` で GitHub 上に作る。終われば消える |
| 規則の置き場 | なし | docs/ops/runner-commands.md の新節 1 か所（AGENTS.md は参照 1 行） |
| 守り | なし | PR の追加行を no-mac-vm-guard が検査 |
| PR の必須チェック | 現状 | 変化なし（sandbox-test は PR で動かない。no-mac-vm-guard は任意チェック） |

## 4. 作り方（実装者向け）
### 4-1. `.github/workflows/sandbox-test.yml`
前例 line-import-operations.yml:3-22 に揃える。
```yaml
name: Sandbox test (manual)
# 仮想マシン（Docker）が要る試験を GitHub 上で行う手動の試験場。規則: docs/ops/runner-commands.md「仮想マシンが要る試験」
# 公開リポジトリのためログは公開される。secrets・本番データは使わない。
on:
  workflow_dispatch:
    inputs:
      test:
        description: tests/sandbox/<test>.sh の <test>（英小文字・数字・ハイフン）
        type: string
        required: true
permissions:
  contents: read
concurrency:
  group: sandbox-test-${{ github.ref }}-${{ inputs.test }}
  cancel-in-progress: false
jobs:
  run:
    if: github.actor == 'shingo-cc' || github.actor == 'shingo-ops'
    runs-on: ubuntu-latest
    timeout-minutes: 60
    steps:
      - uses: actions/checkout@v5
        with:
          persist-credentials: false
      - name: Validate test name
        env:
          TEST_NAME: ${{ inputs.test }}
        run: |
          [[ "$TEST_NAME" =~ ^[a-z0-9-]{1,64}$ ]] || { echo "invalid test name"; exit 1; }
          test -f "tests/sandbox/${TEST_NAME}.sh" || { echo "tests/sandbox/${TEST_NAME}.sh not found"; exit 1; }
      - name: Disk before
        run: df -h /
      - name: Run
        env:
          TEST_NAME: ${{ inputs.test }}
        run: bash "tests/sandbox/${TEST_NAME}.sh"
      - name: Disk after
        if: always()
        run: df -h /
```
- 入力は必ず env 経由で渡す（`${{ }}` を run に直書きしない＝命令の差し込み防止）。
- `--ref` に指定したブランチの tests/sandbox が使われる。workflow ファイル自体は main に入ってから一覧に出る（GitHub の仕様: docs.github.com manually-running-a-workflow）。

### 4-2. `tests/sandbox/smoke.sh`
`set -euo pipefail`。`docker run -d --name sb-pg -e POSTGRES_PASSWORD=sandbox postgres:16` → `pg_isready` を最大 60 秒待つ → `docker exec sb-pg psql -U postgres -Atc 'select 1'` の出力が `1` でなければ exit 1 → trap で `docker rm -f sb-pg`。パスワードは試験専用の固定値（秘密ではない）。

### 4-3. `scripts/ci/no-mac-vm-guard.sh`
- 入力: 比較元（既定 `origin/main`）。`git diff --unified=0 <base>...HEAD` の **追加行（`+` で始まる行）だけ**を見る。
- 止める形（拡張正規表現、行内のどこか）: `colima[[:space:]]+(start|create)` の後に `--profile`／`-p`／位置引数の profile 名が続き、その名前が `default` でないもの。`limactl[[:space:]]+(start|create)`。
- 通す: 同じ行に `vm-guard-allow:` と理由（空でない）がある行。除外パス: `docs/specs/vm-test-on-gha/`・`docs/handoff/vm-test-on-gha/`・`scripts/ci/no-mac-vm-guard.sh`・`scripts/tests/test-no-mac-vm-guard.sh`。
- 出力: 当たった行を `ファイル:行番号: 内容` で全部表示し exit 1。無ければ `no-mac-vm-guard: OK` exit 0。
- 試験 `scripts/tests/test-no-mac-vm-guard.sh`（一時 git リポジトリで）: ①`colima start --profile x` 追加→1 ②`colima start -p x`→1 ③`colima start x`→1 ④`colima start`（default）→0 ⑤`colima start -p default`→0 ⑥`limactl start foo`→1 ⑦①に `vm-guard-allow: 理由` →0 ⑧`vm-guard-allow:` だけで理由なし→1 ⑨除外パス内→0 ⑩既存行（追加でない）に命令→0。

### 4-4. `.github/workflows/no-mac-vm-guard.yml`
`on: pull_request: branches: [main]`、`permissions: contents: read`、`actions/checkout@v5` with `fetch-depth: 0`・`persist-credentials: false`、`bash scripts/ci/no-mac-vm-guard.sh "origin/${{ github.base_ref }}"`（base_ref は env 経由）。timeout 5 分。secrets 不使用。

### 4-5. docs/ops/runner-commands.md 新節（正本）
内容: ①規則「Mac で一時的な仮想マシン（colima profile の新規作成・limactl）を作らない。Docker が要る試験は sandbox-test で行う」②手順（tests/sandbox/<名前>.sh を書いて push → `gh workflow run sandbox-test.yml --ref <ブランチ> -f test=<名前>` → `gh run watch`）③禁止（secrets・本番データ・本番への接続をしない。ログは公開）④例外（Mac 実機でしか試せないもの＝`vm-guard-allow: 理由` を付けて PR に理由を書く）⑤開発用 DB（profile default）は従来どおり・colima-idle-stop が自動停止。

## 5. 受入条件と検証方法
| 基準 | 検証方法 |
|---|---|
| K1 sandbox-test が smoke で緑・ログに `1` | main マージ後 `gh workflow run sandbox-test.yml -f test=smoke` → `gh run view --log` |
| K2 見張りが当たる／例外で通る | `bash scripts/tests/test-no-mac-vm-guard.sh` 全合格＋捨て PR（Draft、確認後 close）で赤→allow 付きで緑 |
| K3 必須チェック数が不変・PR に sandbox-test が出ない | 前後で `gh api repos/shingo-ops/salesanchor/rulesets/15777895 --jq '.rules[]|select(.type=="required_status_checks")|.parameters.required_status_checks|length'`、本 PR のチェック一覧 |
| K4 secrets 0 件 | `grep -c 'secrets\.' .github/workflows/sandbox-test.yml tests/sandbox/*` |
| K5 14 日後に一時 profile 0 件 | 2026-10-31 に `colima list` |
| 既存を壊さない | 本 PR の既存 CI が緑、`git diff --stat origin/main` が §2 のファイルのみ |

## 6. 影響範囲
- PR の流れ: no-mac-vm-guard が 1 ジョブ増える（任意・約 1 分想定）。同時 20 ジョブ枠の消費は PR 1 件あたり 49 → 50（#4400 の check-runs 49 件、2026-10-16 実測）。
- sandbox-test は手動時だけ 1 ジョブ。
- 既存の workflow・Ruleset・Mac の launchd は不変。

## 7. 代替案と選択理由
| 案 | 採否 | 理由 |
|---|---|---|
| A. 同じリポジトリに手動 workflow（本案） | 採用 | コードの写しが不要、公開リポで無料・4CPU/16GB |
| B. 別リポジトリ | 不採用 | 同時実行枠はアカウント共有で速くならない。非公開なら月 2,000 分・2CPU/8GB。コード同期の手間（PO と合意 2026-10-16） |
| C. Mac のまま、使い終わったら削除 | 不採用 | 現状。稼働中の 4GB がスワップ 4.9GB を招いた（recon） |
| D. 自前のサーバー（self-hosted runner） | 不採用 | 公開リポジトリでの self-hosted は危険（monitoring-config-drift.yml:4 の前例どおり PR で動かせない）・保守が増える |
| E. 見張りを必須チェックにする | 見送り | Ruleset 変更は PO 確認が要る。まず任意で運用し、マージ判定（全チェック緑）で効かせる |

## 8. 外部・過去事例の参照と我々への応用
調査記録: /tmp/CC報告ファイル/vm-test-to-gha/research/cases.md（2026-10-16、Sonnet）。
- 直接の事例なし: 「8GB の手元 PC の Docker 試験を GitHub Actions に移してメモリが何 GB 空いた」と数値つきで書いた事例は見つからなかった。よって成功の証明には外部事例を使わず、本件の実測（スワップ 4880MB→1987MB、recon）と K1〜K5 で判定する。
- 失敗事例から入れた対策:
  - 公開リポのログから秘密が漏れた（tj-actions/changed-files 侵害 CVE-2025-30066、2025-03。数十の公開リポで鍵がログに出た。https://www.wiz.io/blog/github-action-tj-actions-changed-files-supply-chain-attack-cve-2025-30066）→ secrets を一切使わない（K4）、`persist-credentials: false`、第三者 action を使わない（checkout のみ）。
  - runner のディスク不足（標準 SSD 14GB と公式記載。空き 54MB でビルド失敗の報告: https://dev.to/mathio/squeezing-disk-space-from-github-actions-runners-an-engineers-guide-3pjg）→ 前後で `df -h /` をログに残す。足りなくなったら試験側で不要イメージを消す。
  - teardown がログ収集より先に走りログが 162 バイトしか残らず、408 件中 85 件失敗の原因が追えなかった（https://github.com/Plainscope/oidc-provider/issues/31、2026-09-18）→ 試験スクリプトは失敗時に `docker logs` を出してから片付ける（tests/sandbox/README.md に明記）。
  - Docker Hub の取得回数制限（匿名 100 回/6 時間/IP: https://docs.docker.com/docker-hub/usage/pulls/）→ 手動で時々動かす用途なので許容。429 が出たら記録して再実行。
- 公式制約: 公開リポの標準 runner 無料・4CPU/16GB/14GB（https://docs.github.com/en/actions/reference/runners/github-hosted-runners）、1 ジョブ 6 時間・Free 同時 20（https://docs.github.com/en/actions/reference/limits）、同時枠は全リポジトリ共有（https://github.blog/changelog/2019-10-28-github-actions-update-to-job-concurrency-usage-limits）、手動起動には write 権限が必要。

## 9. リスクと対処・戻し方
- 公開ログに試験データが出る → 試験専用の固定値のみ使う規則（§4-5 ③）。
- 見張りの誤検知（例文として書いた命令）→ `vm-guard-allow: 理由`。誤検知が週 2 件を超えたら規則の形を見直す。
- GitHub 障害時は試験できない（例 2026-02-02 約 3 時間 40 分: https://www.githubstatus.com/incidents/xwn6hjps36ty）→ その間は待つ。急ぎは PO 判断で Mac 例外。
- 戻し方: 本 PR を revert（追加ファイルの削除と 2 文書の復元のみ。データ・設定変更なし）。

## 10. 設計審査（Opus 自己審査・同一 AI。独立レビューではない）
判定: **APPROVE**（KGI の PO 承認を条件に実装カード発行可）。
- 既存仕様・ADR との整合: ADR-075（secrets 不使用で整合）、ADR-135/136/1015（A 区分・Draft・GO 記録）、CLAUDE.md 不可逆操作（Ruleset・workflow-lint 不変）。○
- 根拠: recon の file:line を 2 件以上再確認（line-import-operations.yml・check-process-artifacts.js:115-124・postgres services）。○
- 受入条件の検証可能性: K1〜K5 すべてコマンドで ○×。K5 は 14 日後の観測。○
- 実装範囲: §2 の 7 ファイル＋索引。触らない範囲を明記。○
- 未解決: KGI の PO 承認。sa-private-ci の用途は対象外のため影響なし。

## 11. 維持の仕組み
- 守り手パス: `.github/workflows/no-mac-vm-guard.yml`（PR ごと）、`scripts/tests/test-no-mac-vm-guard.sh`（見張りの正しさ）、`.github/CODEOWNERS:22-23`（workflows・scripts の変更は @shingo-ops レビュー対象）。
- 対象: 新しく足される手順書・カード・スクリプトの行。
- 関所なしの部分と理由: no-mac-vm-guard は必須チェックに登録しない（Ruleset 変更は PO 確認が要るため。§7 E）。マージは全チェック緑を Opus が確認する運用で効かせる。Mac 上で人や AI が直接 colima を打つことは PR を通らないため止められない → K5（14 日後の `colima list`）で観測する。
- 人の担当: POの委任に基づく Claude Opus（変更時の審査・K5 観測）。
