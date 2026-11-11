# 実装カード — 必須チェックの「まとめ役」が、変更の判定に失敗したら赤を出すようにする

- 設計: docs/handoff/ci-aggregator-gate/design.md（§3 C1〜C9・§6 K1〜K5）・recon.md
- PO 承認: 2026-11-11 PO「1」（この設計で作る）
- 起点: origin/main 5dc69e7ab3b6eb5b37b2c24a0be96812ba813d28。作業枝 release/ci-aggregator-gate-impl（このカードはこの枝の先頭の commit にある）
- 触るファイル（これ以外は触らない）:
  - .github/workflows/test.yml（まとめ役 pytest の job だけ。§1 と §7）
  - .github/workflows/e2e.yml（まとめ役 lint と visual-language の「Report results」の run だけ。§2・§3）
  - .github/workflows/migration-test.yml（まとめ役 migration-test の「Report results」の run だけ。§4）
  - .github/workflows/schema-check.yml（まとめ役 schema-check の「Report results」の run だけ。§5）
  - .github/workflows/karte-gate.yml（まとめ役 karte-gate の「Report results」の run だけ。§6）
  - scripts/ci/check_ci_aggregators.py（新規。§8）
  - scripts/tests/test_check_ci_aggregators.py（新規。§9）
  - .claude-pipeline/active-work.d/release-ci-aggregator-gate-impl.md（台帳。状態の行だけ）
- 読んだ節（docs/handoff/design-partner-card-ops/guards/）と照合:
  - guards/00-common.md: 手順のコマンドは作業台のフルパスへの cd から始める。出力には tail を付ける。push や commit は git log で実在を確かめてから報告する。
  - guards/03-file.md: 書き換えは「変更前の全文」を逐語で目印にして 1 か所ずつ置き換える。目印が見つからなければ停止する。
  - guards/04-worktree.md: 作業台は scripts/new-worktree.sh で作る（この枝はもう作ってある）。push は git push -u origin HEAD を単独で流す。
  - guards/10-executor.md・guards/11-lint.md: 着手前に ./scripts/dev/executor-preflight.sh を流す。commit 前に下の §11 の確かめを全部流す。
- 受領確認: 着手の前に、作業枝の HEAD がクラウドへの依頼文に書いた sha と同じかを確かめ、最初の報告の行に書く。違えば停止して BLOCKED: で報告する。
- 停止の報告: 迷った・目印が無い・想定外の失敗が出たときは、その場で停止し、BLOCKED: か NEEDS_DECISION: で始まる最後の報告に生の出力を貼る。推測で進めない。
- 触らない: `.github/workflows/workflow-lint.yml`・`docs/specs/rule-enforcement/required-checks.txt`・Ruleset・まとめ役の `name:` `needs:` `if: always()` `runs-on:`・実行役のジョブ（pytest-run・lint-backend・lint-run・unit-run・visual-language-run・migration-registration-exists・migration-registration-exists-regression・migration-test-run・migration-full-dryrun・schema-check-run・karte-gate-run）・detect-changes ジョブ・`on:` の節・migrations/・deploy.yml・backend/・frontend/・ほかの全部
- PR を作らない。PR・審査・GO 記録・合流は Opus がする。あなたの仕事は commit と push まで。

## 0. 6 つのまとめ役に共通の決まり（設計 §3 C1）

判定ジョブ = detect-changes。答え = `needs.detect-changes.outputs.<鍵>`。
「判定に従う実行役」= needs に挙げたジョブのうち、自分の `if:` が `needs.detect-changes.outputs.<鍵> == 'true'` のもの。
「毎回動く実行役」= needs に挙げたジョブのうち、`if:` を持たないもの（今は migration-registration-exists-regression だけ）。

（１）判定ジョブの結果が success でなければ赤。
（２）答えが true でも false でもなければ赤。
（３）毎回動く実行役は、success でなければ赤。
（４）答えが true なら、判定に従う実行役は全部 success でなければ赤（skipped も赤）。
（５）答えが false なら、判定に従う実行役は全部 skipped でなければ赤。
（６）karte-gate だけ: 手動の実行（`github.event_name` が `workflow_dispatch`）では、karte-gate-run は答えに関係なく success でなければ赤（`.github/workflows/karte-gate.yml:36` の `|| github.event_name == 'workflow_dispatch'` のため）。

## 1. .github/workflows/test.yml — まとめ役 pytest の「Report results」の run（起点で :269〜:281）

変更前（`run: |` の下の全文。字下げ 10 文字）:

```yaml
          pr="${{ needs.pytest-run.result }}"
          lint="${{ needs.lint-backend.result }}"
          echo "pytest-run: $pr / lint-backend: $lint"
          if [[ ("$pr" == "success" || "$pr" == "skipped") && \
                ("$lint" == "success" || "$lint" == "skipped") ]]; then
            echo "OK: all checks passed or backend not changed"
            exit 0
          else
            echo "FAIL: pytest-run=$pr lint-backend=$lint"
            exit 1
          fi
```

変更後:

```yaml
          det="${{ needs.detect-changes.result }}"
          out="${{ needs.detect-changes.outputs.backend }}"
          pr="${{ needs.pytest-run.result }}"
          lint="${{ needs.lint-backend.result }}"
          echo "detect-changes: $det (backend=$out) / pytest-run: $pr / lint-backend: $lint"
          if [[ "$det" != "success" ]]; then
            echo "FAIL: detect-changes is not success (detect-changes=$det)"
            exit 1
          fi
          case "$out" in
            true)
              if [[ "$pr" == "success" && "$lint" == "success" ]]; then
                echo "OK: backend changed and all checks passed"
                exit 0
              fi
              echo "FAIL: backend changed but checks did not succeed: pytest-run=$pr lint-backend=$lint"
              exit 1
              ;;
            false)
              if [[ "$pr" == "skipped" && "$lint" == "skipped" ]]; then
                echo "OK: backend not changed and checks were skipped"
                exit 0
              fi
              echo "FAIL: backend not changed but checks were not skipped: pytest-run=$pr lint-backend=$lint"
              exit 1
              ;;
            *)
              echo "FAIL: detect-changes output is not true/false: backend='$out'"
              exit 1
              ;;
          esac
```

## 2. .github/workflows/e2e.yml — まとめ役 lint の「Report results」の run（起点で :132〜:145）

変更前:

```yaml
          r="${{ needs.lint-run.result }}"
          u="${{ needs.unit-run.result }}"
          echo "lint-run: $r"
          echo "unit-run: $u"
          ok() { [[ "$1" == "success" || "$1" == "skipped" ]]; }
          if ok "$r" && ok "$u"; then
            echo "OK: lint and unit tests passed or no frontend changes"
            exit 0
          else
            echo "FAIL: lint-run=$r unit-run=$u"
            exit 1
          fi
```

変更後:

```yaml
          det="${{ needs.detect-changes.result }}"
          out="${{ needs.detect-changes.outputs.frontend }}"
          r="${{ needs.lint-run.result }}"
          u="${{ needs.unit-run.result }}"
          echo "detect-changes: $det (frontend=$out) / lint-run: $r / unit-run: $u"
          if [[ "$det" != "success" ]]; then
            echo "FAIL: detect-changes is not success (detect-changes=$det)"
            exit 1
          fi
          case "$out" in
            true)
              if [[ "$r" == "success" && "$u" == "success" ]]; then
                echo "OK: frontend changed and lint and unit tests passed"
                exit 0
              fi
              echo "FAIL: frontend changed but checks did not succeed: lint-run=$r unit-run=$u"
              exit 1
              ;;
            false)
              if [[ "$r" == "skipped" && "$u" == "skipped" ]]; then
                echo "OK: frontend not changed and checks were skipped"
                exit 0
              fi
              echo "FAIL: frontend not changed but checks were not skipped: lint-run=$r unit-run=$u"
              exit 1
              ;;
            *)
              echo "FAIL: detect-changes output is not true/false: frontend='$out'"
              exit 1
              ;;
          esac
```

## 3. .github/workflows/e2e.yml — まとめ役 visual-language の「Report results」の run（起点で :236〜:246）

変更前:

```yaml
          r="${{ needs.visual-language-run.result }}"
          echo "visual-language-run: $r"
          if [[ "$r" == "success" || "$r" == "skipped" ]]; then
            echo "OK: 画面検査が通過、またはフロントエンド変更なし"
            exit 0
          else
            echo "FAIL: visual-language-run=$r"
            exit 1
          fi
```

変更後:

```yaml
          det="${{ needs.detect-changes.result }}"
          out="${{ needs.detect-changes.outputs.frontend }}"
          r="${{ needs.visual-language-run.result }}"
          echo "detect-changes: $det (frontend=$out) / visual-language-run: $r"
          if [[ "$det" != "success" ]]; then
            echo "FAIL: detect-changes is not success (detect-changes=$det)"
            exit 1
          fi
          case "$out" in
            true)
              if [[ "$r" == "success" ]]; then
                echo "OK: frontend changed and visual checks passed"
                exit 0
              fi
              echo "FAIL: frontend changed but visual checks did not succeed: visual-language-run=$r"
              exit 1
              ;;
            false)
              if [[ "$r" == "skipped" ]]; then
                echo "OK: frontend not changed and visual checks were skipped"
                exit 0
              fi
              echo "FAIL: frontend not changed but visual checks were not skipped: visual-language-run=$r"
              exit 1
              ;;
            *)
              echo "FAIL: detect-changes output is not true/false: frontend='$out'"
              exit 1
              ;;
          esac
```

## 4. .github/workflows/migration-test.yml — まとめ役 migration-test の「Report results」の run（起点で :2136〜:2152）

変更前:

```yaml
          r="${{ needs.migration-test-run.result }}"
          d="${{ needs.migration-full-dryrun.result }}"
          e="${{ needs.migration-registration-exists.result }}"
          g="${{ needs.migration-registration-exists-regression.result }}"
          echo "migration-test-run: $r"
          echo "migration-full-dryrun: $d"
          echo "migration-registration-exists: $e"
          echo "migration-registration-exists-regression: $g"
          if [[ "$e" == "success" || "$e" == "skipped" ]] && [[ "$g" == "success" || "$g" == "skipped" ]] && [[ "$r" == "success" || "$r" == "skipped" ]] && [[ "$d" == "success" || "$d" == "skipped" ]]; then
            echo "OK: all migration tests passed or no migration changes"
            exit 0
          else
            echo "FAIL: migration-registration-exists=$e, migration-registration-exists-regression=$g, migration-test-run=$r, migration-full-dryrun=$d"
            exit 1
          fi
```

変更後:

```yaml
          det="${{ needs.detect-changes.result }}"
          out="${{ needs.detect-changes.outputs.migrations }}"
          r="${{ needs.migration-test-run.result }}"
          d="${{ needs.migration-full-dryrun.result }}"
          e="${{ needs.migration-registration-exists.result }}"
          g="${{ needs.migration-registration-exists-regression.result }}"
          echo "detect-changes: $det (migrations=$out)"
          echo "migration-test-run: $r"
          echo "migration-full-dryrun: $d"
          echo "migration-registration-exists: $e"
          echo "migration-registration-exists-regression: $g"
          if [[ "$det" != "success" ]]; then
            echo "FAIL: detect-changes is not success (detect-changes=$det)"
            exit 1
          fi
          if [[ "$g" != "success" ]]; then
            echo "FAIL: migration-registration-exists-regression runs every time and must succeed: $g"
            exit 1
          fi
          case "$out" in
            true)
              if [[ "$e" == "success" && "$r" == "success" && "$d" == "success" ]]; then
                echo "OK: migrations changed and all migration tests passed"
                exit 0
              fi
              echo "FAIL: migrations changed but tests did not succeed: migration-registration-exists=$e, migration-test-run=$r, migration-full-dryrun=$d"
              exit 1
              ;;
            false)
              if [[ "$e" == "skipped" && "$r" == "skipped" && "$d" == "skipped" ]]; then
                echo "OK: migrations not changed and migration tests were skipped"
                exit 0
              fi
              echo "FAIL: migrations not changed but tests were not skipped: migration-registration-exists=$e, migration-test-run=$r, migration-full-dryrun=$d"
              exit 1
              ;;
            *)
              echo "FAIL: detect-changes output is not true/false: migrations='$out'"
              exit 1
              ;;
          esac
```

## 5. .github/workflows/schema-check.yml — まとめ役 schema-check の「Report results」の run（起点で :228〜:238）

変更前:

```yaml
          result="${{ needs.schema-check-run.result }}"
          echo "schema-check-run: $result"
          if [[ "$result" == "success" || "$result" == "skipped" ]]; then
            echo "✅ テナントスキーマチェック通過（skipped = スキーマ変更なし）"
            exit 0
          else
            echo "❌ テナントスキーマチェック失敗"
            exit 1
          fi
```

変更後:

```yaml
          det="${{ needs.detect-changes.result }}"
          out="${{ needs.detect-changes.outputs.relevant }}"
          result="${{ needs.schema-check-run.result }}"
          echo "detect-changes: $det (relevant=$out) / schema-check-run: $result"
          if [[ "$det" != "success" ]]; then
            echo "FAIL: detect-changes is not success (detect-changes=$det)"
            exit 1
          fi
          case "$out" in
            true)
              if [[ "$result" == "success" ]]; then
                echo "OK: schema-related change and tenant schema check passed"
                exit 0
              fi
              echo "FAIL: schema-related change but tenant schema check did not succeed: schema-check-run=$result"
              exit 1
              ;;
            false)
              if [[ "$result" == "skipped" ]]; then
                echo "OK: no schema-related change and tenant schema check was skipped"
                exit 0
              fi
              echo "FAIL: no schema-related change but tenant schema check was not skipped: schema-check-run=$result"
              exit 1
              ;;
            *)
              echo "FAIL: detect-changes output is not true/false: relevant='$out'"
              exit 1
              ;;
          esac
```

## 6. .github/workflows/karte-gate.yml — まとめ役 karte-gate の「Report results」の run（起点で :127〜:137）

変更前:

```yaml
          r="${{ needs.karte-gate-run.result }}"
          echo "karte-gate-run: $r"
          if [[ "$r" == "success" || "$r" == "skipped" ]]; then
            echo "OK"
            exit 0
          else
            echo "FAIL"
            exit 1
          fi
```

変更後:

```yaml
          det="${{ needs.detect-changes.result }}"
          out="${{ needs.detect-changes.outputs.frontend }}"
          ev="${{ github.event_name }}"
          r="${{ needs.karte-gate-run.result }}"
          echo "detect-changes: $det (frontend=$out) / event: $ev / karte-gate-run: $r"
          if [[ "$det" != "success" ]]; then
            echo "FAIL: detect-changes is not success (detect-changes=$det)"
            exit 1
          fi
          case "$out" in
            true|false) ;;
            *)
              echo "FAIL: detect-changes output is not true/false: frontend='$out'"
              exit 1
              ;;
          esac
          if [[ "$out" == "true" || "$ev" == "workflow_dispatch" ]]; then
            if [[ "$r" == "success" ]]; then
              echo "OK: karte gate ran and passed"
              exit 0
            fi
            echo "FAIL: karte gate had to run but did not succeed: karte-gate-run=$r"
            exit 1
          fi
          if [[ "$r" == "skipped" ]]; then
            echo "OK: frontend not changed and karte gate was skipped"
            exit 0
          fi
          echo "FAIL: frontend not changed but karte gate was not skipped: karte-gate-run=$r"
          exit 1
```

## 7. .github/workflows/test.yml — まとめ役 pytest に段を足す（設計 §3 C9）

目印（変更前。起点で :266〜:269）:

```yaml
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Report results
```

変更後（`steps:` と `- name: Report results` の間に 3 段を足す。ほかは変えない）:

```yaml
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Check out workflow files and checker
        uses: actions/checkout@v5
        with:
          sparse-checkout: |
            .github
            scripts
      - name: Test the aggregator checker
        run: python3 -I scripts/tests/test_check_ci_aggregators.py -v
      - name: Check aggregator decision logic
        run: python3 -I scripts/ci/check_ci_aggregators.py
      - name: Report results
```

- 注意: 目印の 4 行は test.yml の中で pytest のまとめ役（起点 :263 `  pytest:`）の直後にあるものだけを置き換える。同じ 4 行がほかにあれば、:263 の `  pytest:` の下のものを選ぶ。どれか判断できなければ停止する。
- `sparse-checkout` は actions/checkout の公式 README の入力（Context7 /actions/checkout で確認。既定で cone mode・根のファイルも入る）。版は本リポジトリで最も多い `@v5` に合わせる。

## 8. scripts/ci/check_ci_aggregators.py（新規）

- 標準ライブラリと PyYAML（`import yaml`）だけ。リポジトリの他のモジュールを import しない。`python3 -I` で動くこと。
- 先頭に docstring: 目的（設計 docs/handoff/ci-aggregator-gate/design.md §3 C7）と実行方法。
- 引数: `--workflows-dir DIR`（既定は、このファイルの位置から 2 つ上のリポジトリ根の `.github/workflows`）・`--json`（結果を JSON 1 つで標準出力へ）。
- 終了コード: 問題が 0 件なら 0、1 件以上なら 1。読めないファイルや YAML の誤りも 1（何が読めなかったかを書く）。

### 8-1. 対象の見つけ方

（１）`--workflows-dir` の直下の拡張子 `.yml` のファイルだけを、名前順に読む（下の階層・`_archive/`・`README.md`・`.yaml` は見ない）。
（２）`yaml.safe_load` で読み、`jobs` の各ジョブについて、`if` の値を文字列にして前後の空白を除いたものが `always()` と一致し、かつ `needs`（文字列か配列。文字列なら 1 要素の配列とみなす）に `detect-changes` を含むものを「まとめ役」とする。
（３）まとめ役が 1 つも無いファイルは、何もしない。

### 8-2. まとめ役ごとの静的な確かめ（1 つでも外れたら問題として記録）

（１）`steps` の中で `name` が `Report results` の段がちょうど 1 つあり、`run` を持つ。無い・2 つ以上なら問題。
（２）その run の中に、`${{ ... }}` の式は次の 3 種類だけ（前後の空白は許す）。ほかの式が 1 つでもあれば問題（「置き換えられない式」として式の文字列を書く）。
  - `needs.<ジョブ名>.result`
  - `needs.detect-changes.outputs.<鍵>`
  - `github.event_name`
（３）run の中に `needs.detect-changes.result` がある。
（４）run の中に `needs.detect-changes.outputs.<鍵>` がちょうど 1 種類の鍵である。0 種類・2 種類以上なら問題。
（５）needs に挙げた detect-changes 以外の全部のジョブ J について、run の中に `needs.J.result` がある（足りない J の名前を書く）。
（６）run が参照する `needs.X.result` の X は全部 needs に挙げてある（無いものの名前を書く）。
（７）needs に挙げた detect-changes 以外の各ジョブ J を、同じファイルの `jobs.J` を見て分ける:
  - `if` が無い → 「毎回動く」。
  - `if` を文字列にし、`${{` `}}` を除き、連続する空白を 1 つにまとめたものが、正規表現 `needs\.detect-changes\.outputs\.([A-Za-z0-9_-]+) == 'true'( \|\| github\.event_name == 'workflow_dispatch')?` に完全一致 → 「判定に従う」。後ろの部分があれば「手動でも動く」の印を付ける。取り出した鍵が（４）の鍵と違えば問題。
  - それ以外（`jobs.J` が無いことも含む）→ 問題（「分けられない if」として if の文字列を書く）。
（８）静的な確かめで問題が 1 つでもあれば、そのまとめ役の真理値表（8-3）は流さない。

### 8-3. 真理値表（設計 §3 C7。K1）

組の作り方:

- 判定ジョブの結果 det: success・failure・cancelled・skipped の 4 通り。
- 答え out: `true`・`false`・空文字 の 3 通り。
- 実行役（判定に従う＋毎回動く）の結果: 各ジョブについて success・failure・skipped・cancelled の 4 通り。全部の組み合わせ（ジョブが n 個なら 4^n 通り）。
- 出来事 ev: 「手動でも動く」の印があるジョブが 1 つでもあれば `pull_request`・`workflow_dispatch` の 2 通り、無ければ `pull_request` の 1 通り。

組ごとの期待（0 = 緑、1 = 赤）は次の関数で決める（§0 の決まりそのまま）:

```text
expected(det, out, results, ev):
  if det != "success": return 1
  if out not in ("true", "false"): return 1
  for J in 毎回動く: if results[J] != "success": return 1
  for J in 判定に従う:
      must_run = (out == "true") or (ev == "workflow_dispatch" and J に「手動でも動く」の印)
      want = "success" if must_run else "skipped"
      if results[J] != want: return 1
  return 0
```

組ごとの流し方:

（１）run の文字列の中の式を置き換える: `${{ needs.detect-changes.result }}` → det、`${{ needs.detect-changes.outputs.<鍵> }}` → out、`${{ needs.J.result }}` → results[J]、`${{ github.event_name }}` → ev。式の中の前後の空白は許す（正規表現で置き換える）。
（２）置き換えた文を一時ファイルに書き、`bash --noprofile --norc -eo pipefail <一時ファイル>` で流す（GitHub の既定の bash の流し方と同じ）。標準入力は空、作業フォルダは一時フォルダ、1 組 10 秒で打ち切り（打ち切りは外れとして数える）。
（３）終了コードが 0 なら 0、0 以外なら 1 とみなし、期待と比べる。違えば「外れ」として、その組（det・out・results・ev・期待・実際）を記録する（記録は 1 つのまとめ役につき最初の 5 件まで書けば足りる。数は全部数える）。

出力（`--json` が無いとき。人が読む形）:

- まとめ役ごとに 1 行: `OK <ファイル名>:<ジョブ名> 組 <数> 外れ 0` か、`NG <ファイル名>:<ジョブ名> ...`（問題と外れの中身を続く行に）。
- 最後に 1 行: `合計 まとめ役 <数> 組 <数> 外れ <数> 問題 <数>`。

出力（`--json` のとき）: 次の形の JSON 1 つ。

```json
{"ok": true, "aggregators": [{"file": "test.yml", "job": "pytest", "combos": 192, "mismatches": 0, "problems": []}], "total_combos": 0, "total_mismatches": 0, "total_problems": 0}
```

- 起点の 6 つのまとめ役での組の数の見込み（ジョブの数から計算した値。実際の出力と比べて PR 本文に書く）: test.yml:pytest 4×3×4²×1=192、e2e.yml:lint 192、e2e.yml:visual-language 4×3×4=48、migration-test.yml:migration-test 4×3×4⁴=3072、schema-check.yml:schema-check 48、karte-gate.yml:karte-gate 4×3×4×2=96。合計 3648。
- 3648 回 bash を起こす。時間を `time` で測り PR 本文の材料として報告する。1 回の実行が 120 秒を超えたら停止して NEEDS_DECISION: で報告する（並列にする等は Opus が決める）。

## 9. scripts/tests/test_check_ci_aggregators.py（新規）

- scripts/tests/test_check_rule_registry.py と同じ形: 標準ライブラリの unittest、検査を `subprocess.run([sys.executable, "-I", CHECK, "--workflows-dir", <一時フォルダ>, "--json"])` で流す。CHECK は `os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ci", "check_ci_aggregators.py")`。
- 見本の yml は試験の中の文字列で作り、一時フォルダの直下に 1 ファイルとして書く。見本はどれも、detect-changes（outputs に鍵 `frontend`）・実行役 `x-run`（`needs: detect-changes`、`if: needs.detect-changes.outputs.frontend == 'true'`）・まとめ役 `x`（`needs: [detect-changes, x-run]`、`if: always()`、段 `Report results`）の 3 ジョブを持つ。

| 試験 | 見本 | 期待 |
|---|---|---|
| test_green | まとめ役の run が §3（visual-language）と同じ形（変数名だけ x-run に合わせる） | 終了コード 0、JSON の ok が true、combos が 48、mismatches が 0 |
| test_red_current_form | まとめ役の run が §3 の「変更前」と同じ形（判定ジョブの結果を見ない） | 終了コード 1、problems に `needs.detect-changes.result` が無いことの記録がある |
| test_red_missing_need | test_green の見本に 2 つ目の実行役 `y-run`（x-run と同じ if）を足し、まとめ役の needs に y-run を足すが、run では y-run を見ない | 終了コード 1、problems に y-run の名前がある |
| test_red_false_allows_success | test_green の run の `false)` の枝の条件を `[[ "$r" == "skipped" || "$r" == "success" ]]` にする | 終了コード 1、mismatches が 1 以上 |
| test_real_repo | `--workflows-dir` を付けず本物の `.github/workflows` を流す | 終了コード 0、JSON の ok が true、total_mismatches が 0、aggregators の (file, job) の集まりが次の 6 つを全部含む: (test.yml, pytest)・(e2e.yml, lint)・(e2e.yml, visual-language)・(migration-test.yml, migration-test)・(schema-check.yml, schema-check)・(karte-gate.yml, karte-gate) |

- test_real_repo の「6 つを全部含む」は、まとめ役が消えた・判定ジョブの名前が変わって見つからなくなったことを試験で止めるため（設計 §9 の「足りないもの」の一部を埋める。新しいまとめ役が足されても落ちない）。

## 10. 台帳 .claude-pipeline/active-work.d/release-ci-aggregator-gate-impl.md

状態の行は IN_PROGRESS のまま。PR# は Opus が書く。このカードの作業では台帳に触らない。

## 11. 完了の確かめ（commit の前に全部流し、生の出力の最後の部分を報告に貼る）

（１）`cd <作業台のフルパス> && python3 -I scripts/tests/test_check_ci_aggregators.py -v 2>&1 | tail -30` → 5 本全部 ok。
（２）`cd <作業台のフルパス> && time python3 -I scripts/ci/check_ci_aggregators.py 2>&1 | tail -15` → 6 行の OK と `合計 まとめ役 6 組 3648 外れ 0 問題 0`（まとめ役の数が 6 より多ければ、その名前を報告する。少なければ停止）。
（３）`cd <作業台のフルパス> && python3 -I -c "import yaml,sys; [yaml.safe_load(open(f)) for f in sys.argv[1:]]; print('yaml ok')" .github/workflows/test.yml .github/workflows/e2e.yml .github/workflows/migration-test.yml .github/workflows/schema-check.yml .github/workflows/karte-gate.yml` → `yaml ok`。
（４）workflow-lint の「ポカよけCI・最適化CI の設定を検証」と同じ確かめを手元で流す: `.github/workflows/workflow-lint.yml` のその段の python の文を一時ファイルに写して作業台の根で `python3 -I` で流し、成功の行で終わることを確かめる（workflow-lint.yml 自体は変えない）。
（５）`cd <作業台のフルパス> && git diff --name-only origin/main...HEAD; git status --short | tail -20` → 触るファイルの一覧（台帳を除く 7 つ＋このカード）以外が無い。workflow-lint.yml・required-checks.txt が無い（K5）。
（６）`cd <作業台のフルパス> && git diff origin/main -- .github/workflows | grep -E '^[-+] *(name|needs|if|runs-on):' | tail -20` → 何も出ない（まとめ役の name・needs・if・runs-on を変えていない。K5。§7 で足す段の `- name:` の行は「- 」が前に付くのでこの式には当たらない）。何か出たら停止。

## 12. commit と push

- commit は 1 つ（または C1〜C6・C7〜C8・C9 の 3 つ）。メッセージは英語で `ci: make required aggregators fail when detect-changes fails (design ci-aggregator-gate)` の形。
- push は `git push -u origin HEAD` を単独で流し、`git log origin/release/ci-aggregator-gate-impl --oneline -3` で実在を確かめてから報告する。
- 最後の報告の先頭は DONE / BLOCKED: / NEEDS_DECISION: のどれか。§11 の（１）〜（６）の生の出力の最後の部分、push した sha、§8 の時間を書く。

## 13. 想定の分かれ道

| 起きたこと | すること |
|---|---|
| 変更前の全文が見つからない（起点から誰かが変えた） | 停止して BLOCKED:。今の全文を貼る |
| 真理値表で本物の 6 つのどれかに外れが出る | §1〜§6 の写し間違いを疑い、カードの変更後と 1 文字ずつ比べる。写し間違いで無ければ停止して NEEDS_DECISION:（外れた組を貼る） |
| `import yaml` が手元で失敗する | 停止して BLOCKED:（pip で入れない。CI の実行機には workflow-lint.yml が使っている PyYAML がある） |
| 本物のまとめ役が 6 つより多く見つかる | 外れ 0 なら続けて、名前を報告に書く。外れがあれば停止して NEEDS_DECISION: |
| 8-2（７）の「分けられない if」が本物で出る | 停止して NEEDS_DECISION:（if の文字列を貼る） |
| §11（４）の workflow-lint の確かめが落ちる | 停止して BLOCKED:（workflow-lint.yml は PO だけが変えられる） |
| 3648 組が 120 秒を超える | 停止して NEEDS_DECISION:（測った時間を貼る） |

END OF CARD
