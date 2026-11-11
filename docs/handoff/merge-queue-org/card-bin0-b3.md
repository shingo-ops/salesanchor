# 実装カード merge-queue-org 便0-B3 — gitleaks を部品から本体に替え、列の起動漏れを機械で止める

> この文書は何か：merge-queue-org 便0（下準備）の 4 枚目の作業指示書です。必須の確かめ `gitleaks（シークレット漏洩検出）` が使う部品 `gitleaks/gitleaks-action@v2` は、順番待ちの列（`merge_group`）では必ず失敗し、会社名義では有料の鍵が無いと全 PR で失敗します（設計 §13 U21）。部品をやめ、版と sha256 を固定した本体 `gitleaks`（MIT）を workflow の中で直接動かします（PO 2026-11-11「1」）。あわせて、必須の確かめが列の起動を持つか・部品を使っていないかを毎回機械で確かめる見張りを足し、固定した版の古さを四半期の点検で知らせます。今の個人名義の倉庫では `merge_group` は起きず、PR と push での検出の決まり（本体の版 8.24.3・`.gitleaks.toml`）は今と同じです。

- 設計: docs/handoff/merge-queue-org/design.md §5-1（120〜140 行目）・§5-2・§11（247 行目の便0-B3 の行）・§12（273 行目）・§13 U21（282 行目）・§14（300 行目）
- 状態: 設計は PO 承認済み（2026-11-11「1」承認して、下準備から始める／U21 は 2026-11-11「1」本体に替える）。本カードは設計の範囲を変えない
- 危険便: はい（`scripts/ci/check_queue_triggers.py`・`scripts/tests/test_check_queue_triggers.py` が `scripts/check-process-artifacts.js:1022-1041` の DANGEROUS_PATTERNS の `scripts/` に当たる）。PR に GO記録が要る（Opus が付ける）。`.github/workflows/workflow-lint.yml`・`.github/workflows/deploy.yml`・`.gitleaks.toml` は触らない
- 担当: 実装と試験 Sonnet（クラウド）／PR 作成・審査・GO記録・マージ Opus
- 起点: origin/main に便0-B2（PR #5391）が合流した後の main。§2 の行番号はその形（便0-B2 の枝 d162f7d21 で確かめた）

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は Opus が作る（担当は push まで）と明記 | ○（§8） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§9） |
| 4 | 1便1目的 | ○（gitleaks を列と会社名義で動く形にし、その形を見張る） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○（release/merge-queue-bin0-b3-impl） |
| 6 | 書式は実例で示した | ○（§4 に新しいファイルの全文と、直すファイルの変更前後） |
| 7 | 合格基準を出力まで縛った | ○（§5 は sha256 と終了コードまで） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-1 の 4 は名前ごとに OK 行を出す） |
| 9 | 出力量に上限のないコマンドを使わない | ○（§5-3 の記録は `tail` で切る） |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○（§9） |
| 11 | 期待値は実物から | ○（Opus が便0-B2 の枝の写しに §4 を当てて §5-1 を流した値） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§10） |

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md（1 手順 1 コマンド・出力に上限・プレースホルダなし）・11-lint.md（L01〜L33）。照合: `cd` 始まりの手順なし（L01）・`gh pr create` なし（L08）・`rm ` なし（L11）・`gh run view` なし（L21）・`--admin` `--auto` なし（L18）・`timeout ` なし（L16）。

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード merge-queue-org 便0-B3 の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. `.github/workflows/secret-scan.yml` を §4-1 の全文に置き換える（部品をやめ、本体 8.24.3 を sha256 で確かめて動かす。列の起動を足す。job の名前は変えない）
2. `scripts/ci/check_queue_triggers.py`（新規・§4-2）: 必須の名前ごとに、列の起動を持つかを確かめる見張り。部品 `gitleaks/gitleaks-action` を使う workflow があれば失敗
3. `scripts/tests/test_check_queue_triggers.py`（新規・§4-3）: 2 の試験 7 本
4. `.github/workflows/test.yml`（§4-4）: まとめ役 `pytest` の job で 2 と 3 を毎回流す
5. `.github/workflows/nodejs-version-audit.yml`（§4-5）: 四半期の点検に「固定した gitleaks の版と最新の版を比べる」を足す。今ある不具合（113 行目が作られないファイル `outdated.txt` を読み、Issue が作れない）を直す
6. 設計 §11 の便0-B3 の試験 (1)〜(4)・(6)・(7) を §5-3 で流す（(5) は Opus が PR で確かめる）

入れない:
- 本体の版を上げること（8.30.1 は四半期の点検が知らせた後の別の変更。設計 §5-1「版を上げるのは別の変更で 1 つずつ」）
- `.gitleaks.toml`・`docs/B-11_credential_management_policy.md`・ADR-075（`secret-scan.yml` の名前を書いているだけで、中身の説明に部品が出てこない）
- ほかの必須の確かめ・`docs/specs/rule-enforcement/required-checks.txt`・倉庫の設定・ruleset・secrets・製品コード

## 2. 前提の事実（便0-B2 合流後の main。便0-B2 の枝 d162f7d21 で確かめた）

- 今の `.github/workflows/secret-scan.yml`（28 行）: 起動は `pull_request` と `push`（develop・main）。job `gitleaks` の名前 `gitleaks（シークレット漏洩検出）`（16 行目）は必須の名前。手順は `actions/checkout@v5`（`fetch-depth: 0`）と `uses: gitleaks/gitleaks-action@v2`（24 行目）だけ
- 部品 v2 が流している命令（設計 §5-1 128 行目）: 本体は既定の 8.24.3。`gitleaks detect --redact -v --exit-code=2 ... --log-opts=--no-merges --first-parent <最初>^..<最後>`。本カードは同じ版・同じ `.gitleaks.toml`・同じ `--no-merges` で、範囲を GitHub が渡す base と head にする（§4-1）
- 本体 8.24.3 の linux_x64 の sha256 は `9991e0b2903da4c8f6122b5c3186448b927a5da4deef1fe45271c3793f4ee29c`（公式の `gitleaks_8.24.3_checksums.txt` を 2026-11-11 に読んだ値・設計 §5-1 134 行目）。最新の release は 8.30.1（2026-11-11 に `gh api repos/gitleaks/gitleaks/releases/latest` で読んだ）。だから §4-5 の点検は次の回（1 月 1 日）に「8.24.3 → 8.30.1」の Issue を 1 件作る。これは想定どおり
- `.gitleaks.toml:13-19` の allowlist の道に `.env.example` がある（§5-3 の (3) で使う）
- `.github/workflows/test.yml:270-282`（まとめ役 `pytest`・`if: always()`）: `actions/checkout@v5` で `.github` と `scripts` だけを取り出し（275〜277 行目）、`scripts/tests/test_check_ci_aggregators.py` と `scripts/ci/check_ci_aggregators.py` を流してから `Report results`（282 行目）。本カードは同じ所に 2 段を足し、名簿 `docs/specs/rule-enforcement/required-checks.txt` を読むため取り出しに `docs/specs/rule-enforcement` を足す。PyYAML は既に `check_ci_aggregators.py` が使っており、runner に入っている
- `scripts/` に新しい台本を登録する名簿は無い（`scripts/ci/check_ci_aggregators.py` は `.github/workflows/test.yml` から呼ばれるだけ。`git grep check_ci_aggregators origin/main` で確かめた）
- 必須の名前は 16 件（`docs/specs/rule-enforcement/required-checks.txt`）。便0-B1・B2 の後、job の名前で当たる 15 件のうち gitleaks だけが列の起動を持たない。`guard-authoring/evaluation` は status 型で、`.github/workflows/queue-guard-status.yml` が列の commit に写す（便0-B1）
- `.github/workflows/nodejs-version-audit.yml`（139 行）: `Combine scan results`（69 行目）が `combined_issues.txt` を作る。`Create issue`（113 行目）は `OUTDATED_LIST=$(cat outdated.txt)` で、どの手順も `outdated.txt` を作らないので、見つかったときに `bash -e` で落ちて Issue が作られない。題（137 行目）と本文（116〜117 行目）は Node.js だけの文。直したうえで gitleaks の比較を足す
- Opus が便0-B2 の枝の写しに §4 を当てた結果（2026-11-11）: `actionlint` は `secret-scan.yml`・`test.yml` で何も出ない。`nodejs-version-audit.yml` は shellcheck の書き方の注意 SC2129 が 2 件で、元の 139 行の時点と同じ 2 件（増やしていない）。§5-1 の 3〜5 は期待どおり

## 3. 触るファイル

| ファイル | 変更 |
|---|---|
| `.github/workflows/secret-scan.yml` | §4-1 の全文に置き換え（足す 78 行・消す 5 行） |
| `scripts/ci/check_queue_triggers.py` | 新規 §4-2（167 行） |
| `scripts/tests/test_check_queue_triggers.py` | 新規 §4-3（153 行） |
| `.github/workflows/test.yml` | §4-4（足す 5 行） |
| `.github/workflows/nodejs-version-audit.yml` | §4-5（足す 29 行・消す 4 行） |
| `docs/handoff/merge-queue-org/card-bin0-b3.md` | §11 の報告欄だけ |

## 4. 変更前後（行の字下げは空白。タブは使わない）

§4-1〜§4-3 はこの全文と 1 字も違わない形にする（最後の行の後に改行 1 つ）。§5-1 の 1 で sha256 を比べる。

### 4-1（全文に置き換え） `.github/workflows/secret-scan.yml`

```yaml
name: Secret Scan

# PR・develop/main へのプッシュ・順番待ちの列（merge queue）でシークレット漏洩を自動検知
# 部品（gitleaks-action）は使わず、版と sha256 を固定した gitleaks 本体を直接動かす。
# 会社名義では部品に有料の鍵が要り、列の起動にも部品が対応しないため（docs/handoff/merge-queue-org/design.md §5-1）。
# 設定: .gitleaks.toml（プロジェクトルート）
# ドキュメント: docs/B-11_credential_management_policy.md

on:
  pull_request:
  merge_group:
    types: [checks_requested]
    branches: [main]
  push:
    branches:
      - develop
      - main

permissions:
  contents: read

jobs:
  gitleaks:
    name: gitleaks（シークレット漏洩検出）
    runs-on: ubuntu-latest
    env:
      # 版を上げるときは、公式の gitleaks_<版>_checksums.txt の linux_x64 の値に sha256 も替える。
      # 四半期の点検 .github/workflows/nodejs-version-audit.yml がこの GITLEAKS_VERSION の行を読み、最新版と比べる。
      GITLEAKS_VERSION: "8.24.3"
      GITLEAKS_SHA256: "9991e0b2903da4c8f6122b5c3186448b927a5da4deef1fe45271c3793f4ee29c"
    steps:
      - uses: actions/checkout@v5
        with:
          fetch-depth: 0  # 全コミット履歴を取得（差分スキャンのため）

      - name: Install gitleaks
        run: |
          set -euo pipefail
          TARBALL="gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz"
          curl -fsSL --retry 3 -o "${RUNNER_TEMP}/${TARBALL}" \
            "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/${TARBALL}"
          echo "${GITLEAKS_SHA256}  ${RUNNER_TEMP}/${TARBALL}" | sha256sum -c -
          mkdir -p "${RUNNER_TEMP}/gitleaks-bin"
          tar -xzf "${RUNNER_TEMP}/${TARBALL}" -C "${RUNNER_TEMP}/gitleaks-bin" gitleaks
          echo "${RUNNER_TEMP}/gitleaks-bin" >> "$GITHUB_PATH"
          "${RUNNER_TEMP}/gitleaks-bin/gitleaks" version

      - name: Decide scan range
        id: range
        env:
          EVENT: ${{ github.event_name }}
          PR_BASE: ${{ github.event.pull_request.base.sha }}
          PR_HEAD: ${{ github.event.pull_request.head.sha }}
          MQ_BASE: ${{ github.event.merge_group.base_sha }}
          MQ_HEAD: ${{ github.event.merge_group.head_sha }}
          PUSH_BEFORE: ${{ github.event.before }}
          PUSH_AFTER: ${{ github.event.after }}
        run: |
          set -euo pipefail
          case "$EVENT" in
            pull_request) BASE="$PR_BASE"; HEAD="$PR_HEAD" ;;
            merge_group) BASE="$MQ_BASE"; HEAD="$MQ_HEAD" ;;
            push) BASE="$PUSH_BEFORE"; HEAD="$PUSH_AFTER" ;;
            *) echo "::error::想定外の起動です: ${EVENT}"; exit 1 ;;
          esac
          for v in "$BASE" "$HEAD"; do
            if [[ -z "$v" || "$v" =~ ^0+$ ]]; then
              echo "::error::見る範囲を決められません（${EVENT}: BASE='${BASE}' HEAD='${HEAD}'）"
              exit 1
            fi
            if ! git cat-file -e "${v}^{commit}" 2>/dev/null; then
              echo "::error::commit が手元にありません: ${v}"
              exit 1
            fi
          done
          COUNT=$(git rev-list --count --no-merges "${BASE}..${HEAD}")
          echo "範囲 ${BASE}..${HEAD} の合流以外の commit: ${COUNT} 件"
          {
            echo "base=${BASE}"
            echo "head=${HEAD}"
            echo "count=${COUNT}"
          } >> "$GITHUB_OUTPUT"

      - name: Run gitleaks
        env:
          BASE: ${{ steps.range.outputs.base }}
          HEAD: ${{ steps.range.outputs.head }}
          COUNT: ${{ steps.range.outputs.count }}
        run: |
          set -euo pipefail
          if [ "$COUNT" = "0" ]; then
            if git diff --quiet "$BASE" "$HEAD"; then
              echo "::notice::調べる commit は 0 件です（範囲 ${BASE}..${HEAD} に中身の差がありません）"
              exit 0
            fi
            echo "::error::中身の差があるのに、合流以外の commit が 0 件です。合流の commit だけの変更は調べられないので、合流以外の commit に作り直してください"
            exit 1
          fi
          gitleaks git --redact --verbose --no-banner --exit-code 1 \
            --config .gitleaks.toml \
            --log-opts="--no-merges ${BASE}..${HEAD}" .
```

### 4-2（新規） `scripts/ci/check_queue_triggers.py`

```python
#!/usr/bin/env python3
"""必須の確かめが、順番待ちの列（merge queue）でも結果を返す形になっているかを確かめる見張り。

目的: 設計 docs/handoff/merge-queue-org/design.md §5-2。
(1) 必須の名前（docs/specs/rule-enforcement/required-checks.txt の 1 列目）と
    job の名前（name: が無い job は job の id）が完全一致する workflow は、起動に merge_group を持つこと。
(2) どの workflow も gitleaks/gitleaks-action を uses で使わないこと（列と会社名義で動かない）。
(3) job の名前に当たらない必須の名前（status で書かれる物）は QUEUE_STATUS_CHECKS に載り、
    写す側の workflow が merge_group で起動し、その名前を書いていること。
どれにも当たらない必須の名前があれば失敗にする。

実行方法:
    python3 -I scripts/ci/check_queue_triggers.py [--workflows-dir DIR] [--required FILE]
終了コード: 問題 0 件なら 0、それ以外（読めないファイル含む）は 1。
標準ライブラリと PyYAML だけを使う。
"""
import argparse
import os
import sys

import yaml

# status で書かれる必須の名前 → 列の commit にその status を写す workflow（.github/workflows 直下のファイル名）
QUEUE_STATUS_CHECKS = {
    "guard-authoring/evaluation": "queue-guard-status.yml",
}
FORBIDDEN_ACTION = "gitleaks/gitleaks-action"
QUEUE_EVENT = "merge_group"


def repo_root():
    return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def triggers(doc):
    """on: の欄を返す。PyYAML は on を真偽値 True と読むので、両方を見る。"""
    if not isinstance(doc, dict):
        return None
    for key in ("on", True):
        if key in doc:
            return doc[key]
    return None


def has_event(on_value, event):
    if isinstance(on_value, str):
        return on_value == event
    if isinstance(on_value, (list, dict)):
        return event in on_value
    return False


def jobs_of(doc):
    jobs = doc.get("jobs") if isinstance(doc, dict) else None
    return jobs if isinstance(jobs, dict) else {}


def job_names(doc):
    names = []
    for jid, job in jobs_of(doc).items():
        name = job.get("name") if isinstance(job, dict) else None
        names.append(name if isinstance(name, str) else str(jid))
    return names


def uses_values(doc):
    values = []
    for job in jobs_of(doc).values():
        if not isinstance(job, dict):
            continue
        if isinstance(job.get("uses"), str):
            values.append(job["uses"])
        steps = job.get("steps")
        if isinstance(steps, list):
            for step in steps:
                if isinstance(step, dict) and isinstance(step.get("uses"), str):
                    values.append(step["uses"])
    return values


def read_required(path):
    names = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            names.append(line.split("\t")[0])
    return names


def main():
    root = repo_root()
    ap = argparse.ArgumentParser(description="列の起動漏れの見張り")
    ap.add_argument("--workflows-dir", default=os.path.join(root, ".github", "workflows"))
    ap.add_argument(
        "--required",
        default=os.path.join(root, "docs", "specs", "rule-enforcement", "required-checks.txt"),
    )
    args = ap.parse_args()

    try:
        required = read_required(args.required)
    except OSError as e:
        print(f"読めない名簿: {args.required}: {e}")
        return 1
    if not required:
        print(f"名簿が空です: {args.required}")
        return 1

    problems = []
    workflows = {}
    try:
        files = sorted(
            n for n in os.listdir(args.workflows_dir)
            if n.endswith((".yml", ".yaml")) and os.path.isfile(os.path.join(args.workflows_dir, n))
        )
    except OSError as e:
        print(f"読めないフォルダ: {args.workflows_dir}: {e}")
        return 1
    for fname in files:
        path = os.path.join(args.workflows_dir, fname)
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
            doc = yaml.safe_load(text)
        except (OSError, yaml.YAMLError, UnicodeDecodeError) as e:
            problems.append(f"読めない workflow: {fname}: {e}")
            continue
        workflows[fname] = (doc, text)
        for u in uses_values(doc):
            if u.split("@")[0] == FORBIDDEN_ACTION:
                problems.append(
                    f"{fname}: {u} を使っています（列と会社名義で動かない。design §5-1）"
                )

    for name in required:
        owners = [f for f, (doc, _) in workflows.items() if name in job_names(doc)]
        if owners:
            for f in owners:
                if has_event(triggers(workflows[f][0]), QUEUE_EVENT):
                    print(f"OK job「{name}」 {f}")
                else:
                    problems.append(f"{f}: 必須の確かめ「{name}」の起動に {QUEUE_EVENT} がありません")
        elif name in QUEUE_STATUS_CHECKS:
            f = QUEUE_STATUS_CHECKS[name]
            if f not in workflows:
                problems.append(f"status 型「{name}」を写す {f} がありません")
            elif not has_event(triggers(workflows[f][0]), QUEUE_EVENT):
                problems.append(f"{f}: status 型「{name}」を写す workflow の起動に {QUEUE_EVENT} がありません")
            elif name not in workflows[f][1]:
                problems.append(f"{f}: status 型「{name}」の名前を書いていません")
            else:
                print(f"OK status「{name}」 {f}")
        else:
            problems.append(
                f"必須の名前「{name}」は、どの job の名前にも QUEUE_STATUS_CHECKS にも当たりません"
            )

    for p in problems:
        print(f"問題: {p}")
    print(f"合計 必須 {len(required)} 件 問題 {len(problems)} 件")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
```

### 4-3（新規） `scripts/tests/test_check_queue_triggers.py`

```python
#!/usr/bin/env python3
"""check_queue_triggers.py の試験（標準ライブラリの unittest）。

実行: python3 -I scripts/tests/test_check_queue_triggers.py -v
"""
import os
import subprocess
import sys
import tempfile
import unittest

CHECK = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "ci", "check_queue_triggers.py"
)

GOOD_JOB = """\
name: Good
on:
  pull_request:
  merge_group:
    types: [checks_requested]
jobs:
  check:
    name: good check
    runs-on: ubuntu-latest
    steps:
      - run: echo ok
"""

NO_QUEUE_JOB = """\
name: No queue
on:
  pull_request:
jobs:
  check:
    name: good check
    runs-on: ubuntu-latest
    steps:
      - run: echo ok
"""

ACTION_JOB = """\
name: Old scan
on:
  pull_request:
  merge_group:
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: gitleaks/gitleaks-action@v2
"""

ID_ONLY_JOB = """\
name: Id only
on: [pull_request, merge_group]
jobs:
  id-only-check:
    runs-on: ubuntu-latest
    steps:
      - run: echo ok
"""

PREFIX_JOB = """\
name: Prefix
on:
  pull_request:
jobs:
  check:
    name: good check (extra)
    runs-on: ubuntu-latest
    steps:
      - run: echo ok
"""

STATUS_COPY = """\
name: Merge queue guard status
on:
  merge_group:
    types: [checks_requested]
jobs:
  copy:
    runs-on: ubuntu-latest
    steps:
      - run: echo "CONTEXT='guard-authoring/evaluation'"
"""


def run(files, required):
    with tempfile.TemporaryDirectory() as d:
        wdir = os.path.join(d, "workflows")
        os.mkdir(wdir)
        for name, body in files.items():
            with open(os.path.join(wdir, name), "w", encoding="utf-8") as f:
                f.write(body)
        req = os.path.join(d, "required-checks.txt")
        with open(req, "w", encoding="utf-8") as f:
            f.write("".join(f"{n}\t-\n" for n in required))
        p = subprocess.run(
            [sys.executable, "-I", CHECK, "--workflows-dir", wdir, "--required", req],
            capture_output=True, text=True,
        )
        return p.returncode, p.stdout


class CheckQueueTriggersTest(unittest.TestCase):
    def test_all_good_passes(self):
        code, out = run(
            {"good.yml": GOOD_JOB, "id.yml": ID_ONLY_JOB, "queue-guard-status.yml": STATUS_COPY},
            ["good check", "id-only-check", "guard-authoring/evaluation"],
        )
        self.assertEqual(code, 0, out)
        self.assertIn("問題 0 件", out)

    def test_required_without_merge_group_fails(self):
        code, out = run({"x.yml": NO_QUEUE_JOB}, ["good check"])
        self.assertEqual(code, 1, out)
        self.assertIn("merge_group がありません", out)

    def test_gitleaks_action_fails(self):
        code, out = run({"good.yml": GOOD_JOB, "scan.yml": ACTION_JOB}, ["good check"])
        self.assertEqual(code, 1, out)
        self.assertIn("gitleaks/gitleaks-action@v2", out)

    def test_unlisted_status_name_fails(self):
        code, out = run({"good.yml": GOOD_JOB}, ["good check", "someone/status"])
        self.assertEqual(code, 1, out)
        self.assertIn("someone/status", out)

    def test_status_copy_without_merge_group_fails(self):
        code, out = run(
            {"queue-guard-status.yml": STATUS_COPY.replace("merge_group:", "pull_request:")},
            ["guard-authoring/evaluation"],
        )
        self.assertEqual(code, 1, out)

    def test_name_match_is_exact(self):
        code, out = run({"p.yml": PREFIX_JOB}, ["good check"])
        self.assertEqual(code, 1, out)
        self.assertIn("当たりません", out)

    def test_missing_required_file_fails(self):
        with tempfile.TemporaryDirectory() as d:
            p = subprocess.run(
                [sys.executable, "-I", CHECK, "--workflows-dir", d,
                 "--required", os.path.join(d, "none.txt")],
                capture_output=True, text=True,
            )
        self.assertEqual(p.returncode, 1)


if __name__ == "__main__":
    unittest.main()
```

### 4-4 `.github/workflows/test.yml` の変更（先頭が `-` の行を消し、`+` の行を足す。空白で始まる行はそのまま。`@@` は便0-B2 合流後の main の行番号）

````diff
@@ -275,10 +275,15 @@
           sparse-checkout: |
             .github
             scripts
+            docs/specs/rule-enforcement
       - name: Test the aggregator checker
         run: python3 -I scripts/tests/test_check_ci_aggregators.py -v
       - name: Check aggregator decision logic
         run: python3 -I scripts/ci/check_ci_aggregators.py
+      - name: Test the queue trigger checker
+        run: python3 -I scripts/tests/test_check_queue_triggers.py -v
+      - name: Check queue triggers of required checks
+        run: python3 -I scripts/ci/check_queue_triggers.py
       - name: Report results
         run: |
           det="${{ needs.detect-changes.result }}"
````

### 4-5 `.github/workflows/nodejs-version-audit.yml` の変更（先頭が `-` の行を消し、`+` の行を足す。空白で始まる行はそのまま。`@@` は便0-B2 合流後の main の行番号）

````diff
@@ -5,6 +5,7 @@
 #
 # 目的: Node.js のEOL・GHA廃止スケジュールによる CI クラッシュを事前に防ぐ。
 # 重複対策: ラベル "ci-maintenance" の open Issue が存在する場合は作成しない。
+# あわせて、secret-scan.yml に固定した gitleaks 本体の版が最新かを比べる（docs/handoff/merge-queue-org/design.md §14）。
 
 on:
   schedule:
@@ -66,6 +67,22 @@
             echo "✅ npm install の使用は検出されませんでした（全て npm ci）"
           fi
 
+      - name: Compare pinned gitleaks version
+        id: scan-gitleaks
+        env:
+          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
+        run: |
+          rm -f outdated_gitleaks.txt
+          PINNED=$(grep -m1 -E '^[[:space:]]+GITLEAKS_VERSION:' .github/workflows/secret-scan.yml | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || true)
+          LATEST=$(gh api repos/gitleaks/gitleaks/releases/latest --jq '.tag_name' | sed 's/^v//' || true)
+          if [ -z "$PINNED" ] || [ -z "$LATEST" ]; then
+            echo "- gitleaks 本体の版を比べられませんでした（固定: '${PINNED}'・最新: '${LATEST}'）。手で確かめてください" > outdated_gitleaks.txt
+          elif [ "$PINNED" != "$LATEST" ]; then
+            echo "- .github/workflows/secret-scan.yml の gitleaks 本体 ${PINNED} → 最新 ${LATEST}（版と sha256 を一緒に替える。上げるのは別の変更で 1 つずつ）" > outdated_gitleaks.txt
+          else
+            echo "✅ gitleaks 本体は最新（${PINNED}）"
+          fi
+
       - name: Combine scan results
         id: scan
         run: |
@@ -83,6 +100,14 @@
             echo "" >> combined_issues.txt
             FOUND=true
           fi
+          if [ -f outdated_gitleaks.txt ]; then
+            {
+              echo "### gitleaks 本体の版"
+              cat outdated_gitleaks.txt
+              echo ""
+            } >> combined_issues.txt
+            FOUND=true
+          fi
           echo "found=$FOUND" >> "$GITHUB_OUTPUT"
 
       - name: Check for existing open issue (重複防止)
@@ -110,11 +135,11 @@
           MONTH=$(date +%-m)
           QUARTER=$(( (MONTH - 1) / 3 + 1 ))
           YEAR_Q="$(date +%Y)-Q${QUARTER}"
-          OUTDATED_LIST=$(cat outdated.txt)
+          OUTDATED_LIST=$(cat combined_issues.txt)
 
           {
-            echo "以下のワークフローで古い Node.js バージョン（20以下）が検出されました。"
-            echo "GitHub Actions の Node.js 20 ランタイムは廃止済みのため、最新 LTS（22）への更新が必要です。"
+            echo "四半期の点検で、更新が要る箇所が見つかりました（内訳は下の「検出箇所」）。"
+            echo "Node.js は 20 以下なら最新 LTS（22）へ更新します。gitleaks 本体は版と sha256 を一緒に上げます。"
             echo ""
             echo "## 検出箇所"
             echo '```'
@@ -134,6 +159,6 @@
           } > issue_body.txt
 
           gh issue create \
-            --title "CI Node.js バージョン要更新 ${YEAR_Q}（古いバージョン検出）" \
+            --title "CI 四半期点検 要更新 ${YEAR_Q}（古いバージョン検出）" \
             --body-file issue_body.txt \
             --label "ci-maintenance"
````

## 5. 確かめ（担当が行う）

### 5-1 手元の確かめ（作業場所で）

1. `sha256sum .github/workflows/secret-scan.yml scripts/ci/check_queue_triggers.py scripts/tests/test_check_queue_triggers.py .github/workflows/test.yml .github/workflows/nodejs-version-audit.yml` → 期待: 次の 5 つと一致
   - `805a5e050eff53f7ba3ef73bc22db058338fb2253ae59f48057dec4765c56d8e  .github/workflows/secret-scan.yml`
   - `ba74e08a259d25590b8a84082f2426f99d9b0674d2b757cc573a28f13be44e1a  scripts/ci/check_queue_triggers.py`
   - `7259da09ea99d5a2c1ea344ab2a6a602a0e1661301ffd2eebd214b8e32c71400  scripts/tests/test_check_queue_triggers.py`
   - `69bddbda2cdeb196837a144526a8288cd75dc06273f22e5ec4335abbcab81cc3  .github/workflows/test.yml`
   - `63409f043ef8ad252ca95db246b2033ba2f9f0f45be0a4e91773dfa63fcd3ce4  .github/workflows/nodejs-version-audit.yml`
   - 後ろ 2 本は元の main の中身に依る。違ったら `git diff origin/main -- .github/workflows/test.yml .github/workflows/nodejs-version-audit.yml` を報告に貼る（§6）
2. `python3 -c "import yaml; [yaml.safe_load(open('.github/workflows/'+p+'.yml')) for p in ('secret-scan','test','nodejs-version-audit')]; print('YAML_OK')"` → 期待: `YAML_OK`
3. `python3 -I scripts/tests/test_check_queue_triggers.py -v` → 期待: 最後の 2 行が `Ran 7 tests in …` と `OK`
4. `python3 -I scripts/ci/check_queue_triggers.py` → 期待: `OK job「…」` が 15 行・`OK status「guard-authoring/evaluation」 queue-guard-status.yml` が 1 行・`問題:` の行なし・最後の行が `合計 必須 16 件 問題 0 件`。`OK job「gitleaks（シークレット漏洩検出）」 secret-scan.yml` を含む
5. `python3 -I scripts/ci/check_ci_aggregators.py` → 期待: 最後の行が `合計 まとめ役 6 組 3648 外れ 0 問題 0`
6. `git diff --numstat origin/main` → 期待: `78 5 .github/workflows/secret-scan.yml`・`5 0 .github/workflows/test.yml`・`29 4 .github/workflows/nodejs-version-audit.yml` の 3 行（新規 2 本は commit 前なので出ない）
7. `git status --short` → 期待: §3 の直す 3 本が ` M`、新規 2 本が `??`、取り込んだ 2 つ（§8 の 2）が `A ` か ` M`

### 5-2 触ったファイルの確かめ（commit と push の後）

1. `git diff --name-only origin/main...HEAD` → 期待: §3 の 5 本と、カードの枝から取り込んだ 2 つ（`docs/handoff/merge-queue-org/card-bin0-b3.md`・`.claude-pipeline/active-work.d/release-merge-queue-bin0-cards.md`）だけ
2. `git diff origin/main...HEAD --stat` を出す

### 5-3 本体の試験（設計 §11 の便0-B3 の行。作業場所の外の一時フォルダで）

本体はこのカードの workflow と同じ手順・同じ版で入れ、workflow の 2 つの手順（`Decide scan range`・`Run gitleaks`）の中身をそのまま流して確かめる。偽の鍵は試験の中で作り、ファイルにもカードにも報告にも値を書かない（報告に出してよいのは伏せ字の行だけ）。

準備:
1. `uname -m` → 期待: `x86_64`（違ったら §6 で止まる）
2. 作業場所の外に一時フォルダを作る: `mktemp -d` → 出た場所を以後 T と書く（報告には実際の値を書く）
3. 次の 2 本を Write ツールで T に作る（中身はこのとおり）

`T/extract.py`:
```python
import sys, yaml
wf = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
steps = {s.get("name"): s for s in wf["jobs"]["gitleaks"]["steps"]}
for name, out in (("Install gitleaks", "install.sh"), ("Decide scan range", "range.sh"), ("Run gitleaks", "scan.sh")):
    open(sys.argv[2] + "/" + out, "w", encoding="utf-8").write(steps[name]["run"])
print("EXTRACT_OK")
```

`T/scan-range.sh`（引数: 調べる倉庫・BASE・HEAD・設定ファイル。workflow の 2 手順を push の起動として流し、最後に終了コードを出す）:
```bash
#!/usr/bin/env bash
set -u
T="$(cd "$(dirname "$0")" && pwd)"
REPO="$1"; B="$2"; H="$3"; CONF="$4"
cd "$REPO" || exit 9
if test "$CONF" != ".gitleaks.toml"; then cp "$CONF" .gitleaks.toml; fi
OUT="$(mktemp)"
EVENT=push PUSH_BEFORE="$B" PUSH_AFTER="$H" PR_BASE= PR_HEAD= MQ_BASE= MQ_HEAD= GITHUB_OUTPUT="$OUT" bash "$T/range.sh"
rc=$?
if test "$rc" != "0"; then echo "RANGE_EXIT=$rc"; exit 0; fi
BASE="$(sed -n 's/^base=//p' "$OUT")" HEAD="$(sed -n 's/^head=//p' "$OUT")" COUNT="$(sed -n 's/^count=//p' "$OUT")" bash "$T/scan.sh"
echo "SCAN_EXIT=$?"
```

4. `python3 -I T/extract.py .github/workflows/secret-scan.yml T`（作業場所で。T は実際の値）→ 期待: `EXTRACT_OK`
5. `RUNNER_TEMP=T GITHUB_PATH=T/path.txt GITLEAKS_VERSION=8.24.3 GITLEAKS_SHA256=9991e0b2903da4c8f6122b5c3186448b927a5da4deef1fe45271c3793f4ee29c bash T/install.sh` → 期待: `OK` で終わる sha256 の行と、版 `8.24.3` の行
6. `export PATH="T/gitleaks-bin:$PATH"` の後 `gitleaks version` → 期待: `8.24.3`

試しの倉庫（T/sandbox）を作る:
7. `git init -q -b main T/sandbox`、`git -C T/sandbox config user.email t@t.invalid`、`git -C T/sandbox config user.name t`（1 手順 1 コマンドで 3 回）
8. 作業場所の `.gitleaks.toml` を `T/sandbox/.gitleaks.toml` に写し、`T/sandbox/README.md` に `base` と 1 行書いて commit（文 `c0`）。`git -C T/sandbox rev-parse HEAD` → 以後 C0

試験（各試験は `bash T/scan-range.sh T/sandbox <BASE> <HEAD> <設定>` の出力の最後の 15 行を報告に貼る。`| tail -15` を付ける）:
- (1) 偽の鍵で止まる: `python3 -c "import secrets,string; a=string.ascii_letters+string.digits; print('token = \"ghp_' + ''.join(secrets.choice(a) for _ in range(36)) + '\"')" > T/sandbox/app.txt` → `app.txt` を commit（文 `c1`）→ HEAD を C1。`bash T/scan-range.sh T/sandbox C0 C1 .gitleaks.toml | tail -15` → 期待: `SCAN_EXIT=1`・`REDACTED` を含む行がある・`leaks found: 1`。値そのものが出力に無いこと: `grep -c ghp_ T/sandbox/app.txt` は 1、試験の出力を T/out1.txt に保存して `grep -c -F "$(cut -d'"' -f2 T/sandbox/app.txt)" T/out1.txt` → 期待: `0`
- (2) 鍵の無い commit は通る: `T/sandbox/README.md` に 1 行足して commit（文 `c2`）→ C2。`bash T/scan-range.sh T/sandbox C1 C2 .gitleaks.toml | tail -15` → 期待: `SCAN_EXIT=0`・`no leaks found`
- (3) allowlist の道は通る: (1) と同じ作り方で `T/sandbox/.env.example` に偽の鍵の行を書いて commit（文 `c3`）→ C3。`bash T/scan-range.sh T/sandbox C2 C3 .gitleaks.toml | tail -15` → 期待: `SCAN_EXIT=0`
- (6) 壊れた設定では通らない: `printf '[[rules\n' > T/broken.toml`。`bash T/scan-range.sh T/sandbox C1 C2 T/broken.toml | tail -15` → 期待: `SCAN_EXIT=` の値が 0 でない（この試験の後 `git -C T/sandbox checkout -- .gitleaks.toml` で設定を戻す）
- (7) 合流の commit だけの範囲:
  - `git -C T/sandbox checkout -q -b side C3`、`T/sandbox/side.txt` に `s` と書いて commit（文 `s1`）→ S1、`git -C T/sandbox checkout -q main`、`git -C T/sandbox merge -q --no-ff --no-edit side` → M1（中身の差が無い合流）
  - `bash T/scan-range.sh T/sandbox S1 M1 .gitleaks.toml | tail -15` → 期待: `::notice::` の行と `SCAN_EXIT=0`
  - `git -C T/sandbox checkout -q -b side2 M1`、`T/sandbox/side2.txt` に `s` と書いて commit → S2、`git -C T/sandbox checkout -q main`、`git -C T/sandbox merge --no-ff --no-commit side2`、`T/sandbox/extra.txt` に `x` と書いて `git -C T/sandbox add extra.txt`、`git -C T/sandbox commit -q -m m2` → M2（合流の commit に中身を足した形）
  - `bash T/scan-range.sh T/sandbox S2 M2 .gitleaks.toml | tail -15` → 期待: `::error::` の行と `SCAN_EXIT=1`
- (4) 本物の倉庫の直近 5 件で、部品と同じ `detect` と本カードの `git` の結果が同じ（作業場所で。浅い写しなら先に `git fetch --unshallow origin`）。5 件の BASE と HEAD（`gh api repos/shingo-ops/salesanchor/pulls/<番号>` の `base.sha`・`head.sha` を 2026-11-11 に Opus が読んだ値）:
  - #5388 `882a5366bdad6fdfa88d250db6ba6aee2ac21558` `d0129643b26c33f2210606c0580f3a825ce27a1c`
  - #5382 `fab1fa39262ae53e969f4a773e6f01c491b13f7e` `5de14e159823cdd29646d74ebe71165d67b6916c`
  - #5381 `9a2147da047bccfc2e25663e4ef45a88b15d3a78` `fd4b247779630a54847095a93532638ec00100e2`
  - #5380 `8d2c7e1b4bfa3bb39695d7e95b1ec4f31821d448` `8350e34bc3d506d6c35b91bfafaf6296eb840407`
  - #5379 `5dc69e7ab3b6eb5b37b2c24a0be96812ba813d28` `d0e06b45e93f7834793f4b230feab166c6cb4f91`
  - 1 件ごとに次の 3 つを流し、件ごとに「rev-list の数・detect の commits scanned と leaks の行と終了コード・git の同じ 3 つ」を表にする:
    - `git rev-list --count --no-merges BASE..HEAD`
    - `gitleaks detect --redact --no-banner --exit-code 1 --config .gitleaks.toml --log-opts="--no-merges BASE..HEAD" > T/d<番号>.txt 2>&1; echo EXIT=$?` の後 `tail -3 T/d<番号>.txt`
    - `gitleaks git --redact --no-banner --exit-code 1 --config .gitleaks.toml --log-opts="--no-merges BASE..HEAD" . > T/g<番号>.txt 2>&1; echo EXIT=$?` の後 `tail -3 T/g<番号>.txt`
  - 期待: 5 件とも、detect と git の commits scanned が同じで rev-list の数と等しい・leaks の行と終了コードが同じ（どちらも `no leaks found`・0 を想定）

## 6. 止まる条件

- 本番・secrets・倉庫の設定・ruleset・main へのマージに触れる操作が必要になったとき（このカードでは不要）
- §2 の変更前の形が実物と違うとき（例: `secret-scan.yml` が 28 行でない・`test.yml:275-282` が §4-4 の変更前と違う・`nodejs-version-audit.yml:113` が `OUTDATED_LIST=$(cat outdated.txt)` でない）。推測で別の行に足さず、違ったファイルの該当の行の前後 10 行を貼って BLOCKED:
- §5-1 の 1 の sha256 が違い、§4 のとおりに書き直しても直らないとき（`git diff origin/main` を貼る。新規 2 本は `cat -A <ファイル> | head -40` を貼る）
- §5-1 の 3〜5、§5-3 の期待と出力が違うとき。試験を書き換えて合わせない
- `uname -m` が `x86_64` でないとき・本体の取得や sha256 が合わないとき
- push の前の自動の確かめが、§3 以外のファイルを直すよう求めたとき

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 部品を使わず、本体 8.24.3 を sha256 で確かめて動かす | §5-1 の 1（全文一致）・§5-3 の 5〜6 |
| 偽の鍵で止まり、値は伏せ字 | §5-3 (1) |
| 鍵の無い変更・allowlist の道は通る | §5-3 (2)(3) |
| 設定が壊れていたら通さない（調べずに緑にならない） | §5-3 (6) |
| 合流の commit だけに中身があれば止め、差が無ければ 0 件と記録して通す | §5-3 (7) |
| 今の部品（detect）と同じ結果 | §5-3 (4)（5 件） |
| 必須 16 件すべてが列の起動を持ち、部品を使う workflow が無いことを毎回機械で確かめる | §5-1 の 3・4。PR の `pytest (SQLite + PostgreSQL RLS)` の記録（Opus） |
| まとめ役の判定が変わっていない | §5-1 の 5 |
| 四半期の点検が gitleaks の版の古さを Issue にする | §4-5 の差分（Opus が審査）。動くのは次の回（1 月 1 日）か手で起動したとき |
| この PR の `gitleaks（シークレット漏洩検出）` が緑で、記録に `8.24.3` と sha256 の `OK` がある | Opus が PR で確かめる（設計 §11 の (5)） |
| 列で gitleaks が Pending で止まらない | 便2 の後の試しの PR（設計 §11。本カードでは確かめない） |

## 8. 作業場所と push（PR は Opus が作る）

1. クラウドの写しの一番上（`git rev-parse --show-toplevel` の場所）で `git fetch origin && bash scripts/new-worktree.sh release/merge-queue-bin0-b3-impl`（origin/main 起点。`--claude` は付けない）。出力はパイプに通さない。作成後に `git worktree list` で実在を確かめ、以後はその作業場所で行う
2. `git checkout origin/release/merge-queue-bin0-cards -- docs/handoff/merge-queue-org/card-bin0-b3.md .claude-pipeline/active-work.d/release-merge-queue-bin0-cards.md` → `git status --short` で 2 件を確かめる（枝の取り込みは使わない）
3. `git log -1 --format=%s origin/main` と `git merge-base --is-ancestor d162f7d211841cf0f495a87c40b836deb25fa359 origin/main; echo $?` → 期待: `0`（便0-B2 が main に入っている。1 なら §6 で止まる）
4. §4-1〜§4-3 は Write ツールで全文を書く。§4-4・§4-5 は Edit ツールで書く。§5-1 を通す
5. §5-3 を流す
6. commit（`--no-verify` は使わない。文: `ci: run gitleaks from the pinned binary and guard queue triggers`）→ `git log -1 --oneline`
7. `git push -u origin release/merge-queue-bin0-b3-impl` → `git log origin/release/merge-queue-bin0-b3-impl -1 --oneline`
8. §5-2

## 9. 報告

- 冒頭に受領文。1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか
- 本文に: §5-1・§5-2・§5-3 の出力（§5-3 (4) は表）・push した commit・判断を要した点（事実のみ）
- 偽の鍵の値は書かない
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文

## 10. 委任の定型

- sleep は使わない。CI は待たない
- 倉庫の中のファイルの編集は §8 の 4 のとおり Write と Edit ツールで行う。rm は使わない（一時フォルダ T は消さずに置いてよい）
- PR は作らない。main にマージしない。本番と倉庫の設定に触れない
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

## 11. 報告欄（担当が追記）

- （未記入）

END OF CARD
