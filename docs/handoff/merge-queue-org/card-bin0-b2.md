# 実装カード merge-queue-org 便0-B2 — 列で確かめ直す必須の確かめ 10 本に、列の起動を足す

> この文書は何か：merge-queue-org 便0（下準備）の 3 枚目の作業指示書です。順番待ちの列は、必須の確かめが列の commit に届かないと Pending のまま止まります。設計 §5 で「甲（列で確かめ直す）」とした 11 件のうち、gitleaks（便0-B3 で作り直す）を除く 10 本の workflow に `merge_group` の起動を足します。比べる範囲を PR の値だけから取っている 5 本は、列の値も読む形にします。今の個人名義の倉庫では `merge_group` が起きないので、今の動きは変わりません。

- 設計: docs/handoff/merge-queue-org/design.md §5（90〜119 行目。表と「`github.event.pull_request.*`・head_ref・base_ref を使う甲の workflow」の行）
- 状態: 設計は PO 承認済み（2026-11-11「1」承認して、下準備から始める）。設計審査 15 回目 APPROVE。本カードは設計の範囲を変えない
- 危険便: いいえ（触るのは `.github/workflows/` の 10 本だけ。`scripts/check-process-artifacts.js:1023-1041` の DANGEROUS_PATTERNS に当たらない。`.github/workflows/workflow-lint.yml`・`.github/workflows/deploy.yml` は触らない）
- 担当: 実装 Sonnet（クラウド）／PR 作成・審査・マージ Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は Opus が作る（担当は push まで）と明記 | ○（§8） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§9） |
| 4 | 1便1目的 | ○（甲 10 本を列で報告させる） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○（release/merge-queue-bin0-b2-impl） |
| 6 | 書式は実例で示した | ○（§4 に 10 本の変更前後） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-1 の 2・3・4 は名前と値を出す） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○（§9） |
| 11 | 期待値は実物から | ○（行番号は origin/main a7fbffdfe で確かめた） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§10） |

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md（1 手順 1 コマンド・出力に上限・プレースホルダなし）・11-lint.md（L01〜L33）。照合: `cd` 始まりの手順なし（L01）・`gh pr create` なし（L08）・`rm ` なし（L11）・`gh run view` なし（L21）・`--admin` `--auto` なし（L18）・`timeout ` なし（L16）。

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード merge-queue-org 便0-B2 の実行結果である」と書くこと。

## 1. 範囲

入れる（10 本。どれも `on:` に `merge_group` の 3 行を足す。5 本は比べる範囲の行も直す）:
1. `.github/workflows/test.yml`（必須 `pytest (SQLite + PostgreSQL RLS)`）
2. `.github/workflows/schema-check.yml`（必須 `テナントスキーマ整合性チェック`）＋ 38 行目
3. `.github/workflows/migration-test.yml`（必須 `マイグレーションSQL 実行テスト（実DB）`）＋ 1197〜1198 行目
4. `.github/workflows/lint-tenant-schema.yml`（必須 `ADR-072 tenant schema lint (strict mode)`）＋ 53 行目
5. `.github/workflows/e2e.yml`（必須 `Lint & Dark Mode Check (ADR-067)`）
6. `.github/workflows/check-claude-size.yml`（必須 `CLAUDE.md line count check`）＋ 22 行目
7. `.github/workflows/adr-index-check.yml`（必須 `ADR index is up to date`）＋ 18〜19 行目
8. `.github/workflows/dangling-route-gate.yml`（必須 `dangling-route gate`）＋ 30〜31 行目
9. `.github/workflows/api-contract-check.yml`（必須 `API contract is up to date`）
10. `.github/workflows/doc-index-reachability.yml`（必須 `doc index reachability`）

入れない:
- `.github/workflows/secret-scan.yml`（gitleaks。便0-B3 で作り直す）
- 乙 5 件（便0-B1 で済み）・`scripts/` の台本（`scripts/ci/check_ci_aggregators.py` を含む。§2 の最後）・jobs の if・concurrency
- 製品コード・設定・secrets・倉庫の設定・ruleset

## 2. 前提の事実（origin/main a7fbffdfe）

- 必須の名前と workflow の対応（`docs/specs/rule-enforcement/required-checks.txt` と実物を突き合わせた。どれも job の `name:`）:
  - `pytest (SQLite + PostgreSQL RLS)` … `.github/workflows/test.yml:264`（まとめ役 `pytest`・`if: always()`・266 行目）
  - `テナントスキーマ整合性チェック` … `.github/workflows/schema-check.yml:223`（まとめ役 `schema-check`。48 行目の `テナントスキーマ整合性チェック（実行）` は別の job で、完全一致しない）
  - `マイグレーションSQL 実行テスト（実DB）` … `.github/workflows/migration-test.yml:2131`
  - `ADR-072 tenant schema lint (strict mode)` … `.github/workflows/lint-tenant-schema.yml:40`
  - `Lint & Dark Mode Check (ADR-067)` … `.github/workflows/e2e.yml:127`
  - `CLAUDE.md line count check` … `.github/workflows/check-claude-size.yml:12`
  - `ADR index is up to date` … `.github/workflows/adr-index-check.yml:9`
  - `dangling-route gate` … `.github/workflows/dangling-route-gate.yml:13`
  - `API contract is up to date` … `.github/workflows/api-contract-check.yml:9`
  - `doc index reachability` … `.github/workflows/doc-index-reachability.yml:16`
- 比べる範囲を PR の値だけから取っている行（列では空になる）:
  - `.github/workflows/schema-check.yml:38`・`.github/workflows/lint-tenant-schema.yml:53` … `BASE="${{ github.event.pull_request.base.sha || 'HEAD~1' }}"`。列では `HEAD~1` に落ちる。列の commit の 1 つ前を基準にするのは「列に入った分」と同じとは限らないので、`merge_group.base_sha` を間に挟む
  - `.github/workflows/migration-test.yml:1197-1198` … `BASE`・`HEAD` を PR の base/head から取る。空なら 1205 行目の `git diff` が失敗して落ちる（fail-closed）。列では赤になるので `merge_group.base_sha`・`head_sha` を足す。この job の取り出しは `fetch-depth: 0`（121〜123 行目）
  - `.github/workflows/check-claude-size.yml:22` … `BASE_SHA` が空だと 23 行目の `git diff` が失敗し `|| echo ""` で「変更なし」になり、調べずに緑になる。`merge_group.base_sha` を足す（取り出しは `fetch-depth: 0`・16〜17 行目）
  - `.github/workflows/adr-index-check.yml:19` … `origin/${{ github.base_ref }}...HEAD`。`github.base_ref` は pull_request でだけ入る値で、列では `origin/...HEAD` になり失敗し、`|| echo changed=false` で調べずに緑になる。列では `merge_group.base_sha` を使う（取り出しは `fetch-depth: 0`・13〜14 行目）。PR では今と同じ `origin/main` の文字列になるよう、式で分ける
  - `.github/workflows/dangling-route-gate.yml:30-31` … `BASE_SHA`・`HEAD_SHA` を PR から取る。空なら `scripts/check-dangling-routes.js:336-337` が「BASE_SHA と HEAD_SHA 環境変数が必要です」で落ちる。`merge_group.base_sha`・`head_sha` を足す（台本は git だけを使い、PR の API は読まない・同 js:55,68）
- 直さなくてよい 5 本の理由:
  - `test.yml`・`migration-test.yml`（detect-changes 37 行目）・`e2e.yml` は変更の判定に `dorny/paths-filter@v4` を使う。この部品は `merge_group` では `base`・`ref` を指定しなければ `merge_group.base_sha`・`head_sha` を使い、git で判定する。浅い取り出しでも、必要な分を少しずつ取りに行く（Context7 `/dorny/paths-filter` の README「Supported workflows」と `getChangesSinceMergeBase`。3 本とも `base`・`ref` を指定していない）
  - `api-contract-check.yml`・`doc-index-reachability.yml` は event の値を読まない（全体を作り直して比べる・全体を走査する）
- GitHub の決まり（Context7 /github/docs で確認・便0-B1 と同じ）: 必須の確かめを Actions で出しているなら `merge_group` を足さないと列で報告が出ない。`merge_group` の種類は `checks_requested` だけ。`branches` で行き先の枝を絞れる。`actions/checkout` は列の commit（`GITHUB_SHA`）を取り出す
- 式 `a || b` は、`a` が空でなければ `a` になる。PR では `github.event.pull_request.*` が入っているので、§4 の直しで PR の動きは変わらない
- `e2e.yml` の concurrency は `e2e-${{ github.ref }}`（34〜36 行目）で、列の枝ごとに分かれる。直さない（設計 §5 の表）。ほかの 9 本に concurrency は無い
- `scripts/ci/check_ci_aggregators.py` の真理値表（:198-224）は直さない。理由: 起動の種類で答えが変わるのは「まとめ役が待つ job の if に `|| github.event_name == 'workflow_dispatch'` がある」ときだけ（:31-34,:159）。本カードは jobs の if を変えず、まとめ役の Report results も event を読まない（`.github/workflows/test.yml:280-311` ほか）。今の main で `合計 まとめ役 6 組 3648 外れ 0 問題 0`（Opus が a7fbffdfe の写しで実行）。§5-1 の 5 で、直した後も同じ値であることを確かめる

## 3. 触るファイル

| ファイル | 変更 |
|---|---|
| `.github/workflows/test.yml` | §4-1（3 行を足す） |
| `.github/workflows/schema-check.yml` | §4-2（3 行を足す・1 行を直す） |
| `.github/workflows/migration-test.yml` | §4-3（3 行を足す・2 行を直す） |
| `.github/workflows/lint-tenant-schema.yml` | §4-4（3 行を足す・1 行を直す） |
| `.github/workflows/e2e.yml` | §4-5（3 行を足す） |
| `.github/workflows/check-claude-size.yml` | §4-6（3 行を足す・1 行を直す） |
| `.github/workflows/adr-index-check.yml` | §4-7（3 行を足す・2 行を足す・1 行を直す） |
| `.github/workflows/dangling-route-gate.yml` | §4-8（3 行を足す・2 行を直す） |
| `.github/workflows/api-contract-check.yml` | §4-9（3 行を足す） |
| `.github/workflows/doc-index-reachability.yml` | §4-10（3 行を足す） |
| `docs/handoff/merge-queue-org/card-bin0-b2.md` | §11 の報告欄だけ |

## 4. 変更前後（行の字下げは空白。タブは使わない）

足す 3 行は 10 本とも同じ（字下げは `on:` の下の 2 つ）:
```yaml
  merge_group:
    types: [checks_requested]
    branches: [main]
```

### 4-1 `.github/workflows/test.yml`

12〜13 行目 変更前:
```yaml
    # backend 変更がない場合は pytest ジョブを即時成功終了させる。
  push:
```
変更後:
```yaml
    # backend 変更がない場合は pytest ジョブを即時成功終了させる。
  merge_group:
    types: [checks_requested]
    branches: [main]
  push:
```

### 4-2 `.github/workflows/schema-check.yml`

15〜17 行目 変更前:
```yaml
  pull_request:
    branches: [main, develop]
  push:
```
変更後:
```yaml
  pull_request:
    branches: [main, develop]
  merge_group:
    types: [checks_requested]
    branches: [main]
  push:
```

38 行目 変更前:
```yaml
          BASE="${{ github.event.pull_request.base.sha || 'HEAD~1' }}"
```
変更後:
```yaml
          BASE="${{ github.event.pull_request.base.sha || github.event.merge_group.base_sha || 'HEAD~1' }}"
```

### 4-3 `.github/workflows/migration-test.yml`

25〜27 行目 変更前（27 行目は空行）:
```yaml
  pull_request:
    branches: [main, develop]

```
変更後:
```yaml
  pull_request:
    branches: [main, develop]
  merge_group:
    types: [checks_requested]
    branches: [main]

```

1197〜1198 行目 変更前:
```yaml
          BASE=${{ github.event.pull_request.base.sha }}
          HEAD=${{ github.event.pull_request.head.sha }}
```
変更後:
```yaml
          BASE=${{ github.event.pull_request.base.sha || github.event.merge_group.base_sha }}
          HEAD=${{ github.event.pull_request.head.sha || github.event.merge_group.head_sha }}
```

### 4-4 `.github/workflows/lint-tenant-schema.yml`

24〜28 行目 変更前:
```yaml
  pull_request:
    branches:
      - develop
      - main
  push:
```
変更後:
```yaml
  pull_request:
    branches:
      - develop
      - main
  merge_group:
    types: [checks_requested]
    branches: [main]
  push:
```

53 行目 変更前:
```yaml
          BASE="${{ github.event.pull_request.base.sha || 'HEAD~1' }}"
```
変更後:
```yaml
          BASE="${{ github.event.pull_request.base.sha || github.event.merge_group.base_sha || 'HEAD~1' }}"
```

### 4-5 `.github/workflows/e2e.yml`

13〜17 行目 変更前:
```yaml
  pull_request:
    branches:
      - main
      - develop
# NOTE: push トリガーを削除（2026-05-27）。PR 時点で E2E が通っていれば
```
変更後:
```yaml
  pull_request:
    branches:
      - main
      - develop
  merge_group:
    types: [checks_requested]
    branches: [main]
# NOTE: push トリガーを削除（2026-05-27）。PR 時点で E2E が通っていれば
```

### 4-6 `.github/workflows/check-claude-size.yml`

7〜9 行目 変更前（9 行目は空行）:
```yaml
  pull_request:
    branches: [main, develop]

```
変更後:
```yaml
  pull_request:
    branches: [main, develop]
  merge_group:
    types: [checks_requested]
    branches: [main]

```

22 行目 変更前:
```yaml
          BASE_SHA="${{ github.event.pull_request.base.sha }}"
```
変更後:
```yaml
          BASE_SHA="${{ github.event.pull_request.base.sha || github.event.merge_group.base_sha }}"
```

### 4-7 `.github/workflows/adr-index-check.yml`

4〜6 行目 変更前（6 行目は空行）:
```yaml
  pull_request:
    branches: [main, develop]

```
変更後:
```yaml
  pull_request:
    branches: [main, develop]
  merge_group:
    types: [checks_requested]
    branches: [main]

```

17〜19 行目 変更前:
```yaml
        id: adr_changed
        run: |
          git diff --name-only origin/${{ github.base_ref }}...HEAD \
```
変更後:
```yaml
        id: adr_changed
        env:
          DIFF_BASE: ${{ github.event_name == 'merge_group' && github.event.merge_group.base_sha || format('origin/{0}', github.base_ref) }}
        run: |
          git diff --name-only "${DIFF_BASE}...HEAD" \
```

### 4-8 `.github/workflows/dangling-route-gate.yml`

8〜10 行目 変更前（10 行目は空行）:
```yaml
  pull_request:
    branches: [main, develop]

```
変更後:
```yaml
  pull_request:
    branches: [main, develop]
  merge_group:
    types: [checks_requested]
    branches: [main]

```

30〜31 行目 変更前:
```yaml
          BASE_SHA: ${{ github.event.pull_request.base.sha }}
          HEAD_SHA: ${{ github.event.pull_request.head.sha }}
```
変更後:
```yaml
          BASE_SHA: ${{ github.event.pull_request.base.sha || github.event.merge_group.base_sha }}
          HEAD_SHA: ${{ github.event.pull_request.head.sha || github.event.merge_group.head_sha }}
```

### 4-9 `.github/workflows/api-contract-check.yml`

4〜6 行目 変更前（6 行目は空行）:
```yaml
  pull_request:
    branches: [main]

```
変更後:
```yaml
  pull_request:
    branches: [main]
  merge_group:
    types: [checks_requested]
    branches: [main]

```

### 4-10 `.github/workflows/doc-index-reachability.yml`

7〜9 行目 変更前:
```yaml
  pull_request:
    branches: [main]
  push:
```
変更後:
```yaml
  pull_request:
    branches: [main]
  merge_group:
    types: [checks_requested]
    branches: [main]
  push:
```

## 5. 確かめ（担当が行う）

### 5-1 手元の確かめ（作業場所で）

1. `python3 -c "import yaml; [yaml.safe_load(open('.github/workflows/'+p+'.yml')) for p in ('test','schema-check','migration-test','lint-tenant-schema','e2e','check-claude-size','adr-index-check','dangling-route-gate','api-contract-check','doc-index-reachability')]; print('YAML_OK')"` → 期待: `YAML_OK`
2. `python3 -c "import yaml; [print(p, {k: v for k, v in yaml.safe_load(open('.github/workflows/'+p+'.yml'))[True].items() if k not in ('pull_request','push','schedule')}) for p in ('test','schema-check','migration-test','lint-tenant-schema','e2e','check-claude-size','adr-index-check','dangling-route-gate','api-contract-check','doc-index-reachability')]"` → 期待: 10 行で、どれも右に `{'merge_group': {'types': ['checks_requested'], 'branches': ['main']}}`（命令の本文に起動の名前を書かないのは、便0-B1 と同じく手元の見張り review-gate が python3 -c の本文に合流を表す英単語を含むと止めるため。出力には出てよい）
3. `grep -n -E 'pull_request\.(base|head)\.sha|base_ref|_group\.(base|head)_sha' .github/workflows/test.yml .github/workflows/schema-check.yml .github/workflows/migration-test.yml .github/workflows/lint-tenant-schema.yml .github/workflows/e2e.yml .github/workflows/check-claude-size.yml .github/workflows/adr-index-check.yml .github/workflows/dangling-route-gate.yml .github/workflows/api-contract-check.yml .github/workflows/doc-index-reachability.yml` → 期待: 次の 8 行だけ。どの行にも `merge_group` が入っている（PR の値だけの行が残っていない）
   - `.github/workflows/schema-check.yml:41:` … `pull_request.base.sha || github.event.merge_group.base_sha || 'HEAD~1'`
   - `.github/workflows/migration-test.yml:1200:` … `BASE=` の行
   - `.github/workflows/migration-test.yml:1201:` … `HEAD=` の行
   - `.github/workflows/lint-tenant-schema.yml:56:` … `BASE=` の行
   - `.github/workflows/check-claude-size.yml:25:` … `BASE_SHA=` の行
   - `.github/workflows/adr-index-check.yml:22:` … `DIFF_BASE:` の行
   - `.github/workflows/dangling-route-gate.yml:33:` … `BASE_SHA:` の行
   - `.github/workflows/dangling-route-gate.yml:34:` … `HEAD_SHA:` の行
4. `python3 -c "import yaml; [print(p, [j.get('name') or k for k, j in yaml.safe_load(open('.github/workflows/'+p+'.yml'))['jobs'].items() if j.get('name') in n]) for n in [set(l.split(chr(9))[0] for l in open('docs/specs/rule-enforcement/required-checks.txt') if l.strip())] for p in ('test','schema-check','migration-test','lint-tenant-schema','e2e','check-claude-size','adr-index-check','dangling-route-gate','api-contract-check','doc-index-reachability')]"` → 期待: 10 行で、右の一覧にそれぞれ §2 の必須の名前がちょうど 1 つ（名前を変えていないことの確かめ）
5. `python3 -I scripts/ci/check_ci_aggregators.py` → 期待: 最後の行が `合計 まとめ役 6 組 3648 外れ 0 問題 0`
6. `git diff --numstat origin/main -- .github/workflows` → 期待: 10 行で、足した行・消した行が次のとおり
   - `test.yml` 3・0／`schema-check.yml` 4・1／`migration-test.yml` 5・2／`lint-tenant-schema.yml` 4・1／`e2e.yml` 3・0
   - `check-claude-size.yml` 4・1／`adr-index-check.yml` 6・1／`dangling-route-gate.yml` 5・2／`api-contract-check.yml` 3・0／`doc-index-reachability.yml` 3・0
7. `git status --short` → 期待: §3 の 10 本が ` M`、取り込んだ 2 つ（§8 の 2）が `A ` か ` M`

### 5-2 触ったファイルの確かめ（commit と push の後）
1. `git diff --name-only origin/main...HEAD` → 期待: §3 の 10 本と、カードの枝から取り込んだ 2 つ（`docs/handoff/merge-queue-org/card-bin0-b2.md`・`.claude-pipeline/active-work.d/release-merge-queue-bin0-cards.md`）だけ
2. `git diff origin/main...HEAD --stat` を出す

## 6. 止まる条件

- 本番・secrets・倉庫の設定・ruleset・main へのマージに触れる操作が必要になったとき（このカードでは不要）
- §4 の変更前の形が実物と違うとき。推測で別の行に足さず、違った 1 本の該当の行の前後 10 行（例: `git show origin/main:.github/workflows/adr-index-check.yml | head -35`）を貼って BLOCKED:
- §5-1 の期待と出力が違い、§4 のとおりに書き直しても直らないとき
- push の前の自動の確かめが、§3 以外のファイルを直すよう求めたとき

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 甲 10 本の workflow が `merge_group`（main 行き）で起きる | §5-1 の 2 |
| 比べる範囲を PR の値だけから取る行が残っていない | §5-1 の 3 |
| 必須の名前を変えていない | §5-1 の 4 |
| まとめ役の判定が変わっていない | §5-1 の 5（`外れ 0 問題 0`） |
| ほかの行は変わっていない | §5-1 の 6 |
| 触ったファイルが §3 とカードの 2 つだけ | §5-2 |
| PR の必須の確かめが緑（今の pull_request の動きが変わっていない） | Opus が PR で確かめる |
| 列で甲 10 件が Pending で止まらず、列に入った分を比べる | 便2 の後の試しの PR（設計 §11。本カードでは確かめない） |

## 8. 作業場所と push（PR は Opus が作る）

1. クラウドの写しの一番上（`git rev-parse --show-toplevel` の場所）で `git fetch origin && bash scripts/new-worktree.sh release/merge-queue-bin0-b2-impl`（origin/main 起点。`--claude` は付けない。付けると Claude Code の起動を試みて止まる）。出力はパイプに通さない。作成後に `git worktree list` で実在を確かめ、以後はその作業場所で行う
2. `git checkout origin/release/merge-queue-bin0-cards -- docs/handoff/merge-queue-org/card-bin0-b2.md .claude-pipeline/active-work.d/release-merge-queue-bin0-cards.md` → `git status --short` で 2 件を確かめる（枝の取り込みは使わない）
3. §4-1〜§4-10 は Edit ツールで書く。§5-1 を通す
4. commit（`--no-verify` は使わない。文: `ci: run the ten re-checked required checks in the merge queue`）→ `git log -1 --oneline`
5. `git push -u origin release/merge-queue-bin0-b2-impl` → `git log origin/release/merge-queue-bin0-b2-impl -1 --oneline`
6. §5-2

## 9. 報告

- 冒頭に受領文。1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか
- 本文に: §5-1・§5-2 の出力・push した commit・判断を要した点（事実のみ）
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文

## 10. 委任の定型

- sleep は使わない。CI は待たない
- ファイルの編集は Edit ツールで行う（ヒアドキュメントで書かない）。rm は使わない
- PR は作らない。main にマージしない。本番と倉庫の設定に触れない
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

## 11. 報告欄（担当が追記）

- （未記入）

END OF CARD
