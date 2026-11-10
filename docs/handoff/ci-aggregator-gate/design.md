# design — 必須チェックの「まとめ役」が、変更の判定に失敗したら赤を出すようにする

- 状態: PO 承認済み（2026-11-11 PO「1」）。実装カード card.md で実装に入る。
- 根拠: docs/handoff/ci-aggregator-gate/recon.md（行番号は origin/main ae8def4d3）。
- 関係する決まり: ADR-135・ADR-136（必須チェックと危険なパス。この設計は migrations・deploy.yml に触らない。実装 PR は scripts/ci/ と scripts/tests/ を新しく作るので、scripts/check-process-artifacts.js:1025 の危険なパスに当たり、GO 記録が要る。実装カードにもそう書く）・ADR-1003（GO の委任。例外の 7 種のうち Ruleset と workflow-lint.yml には触らない）・ADR-1047（決まり台帳）・docs/specs/rule-enforcement/README.md。

## 1. 目的（KGI）

必須チェック 4 つ（pytest・Lint & Dark Mode Check・マイグレーションSQL 実行テスト・テナントスキーマ整合性チェック）が、「変更の判定ジョブが失敗した／判定の答えが true でも false でもない」ときに、緑ではなく赤を出す。普段の PR（試験を流す PR・流さない PR）では今と同じく緑のまま。

- PO に見える変化: 普段は何も変わらない。判定ジョブが壊れた日にだけ、PR の画面で上の 4 つのどれかが赤になり、試験を流していない PR が合流できなくなる。
- ○× の判定: §6 の K1〜K5 が全部 ○。

## 2. 対象と対象外

| 区分 | 中身 | 理由 |
|---|---|---|
| 対象 | `.github/workflows/test.yml:263-281` まとめ役 pytest の判定の式 | 必須・穴あり（recon §1） |
| 対象 | `.github/workflows/e2e.yml:126-145` まとめ役 lint の判定の式 | 同上 |
| 対象 | `.github/workflows/migration-test.yml:2130-2152` まとめ役 migration-test の判定の式 | 同上 |
| 対象 | `.github/workflows/schema-check.yml:222-238` まとめ役 schema-check の判定の式 | 同上 |
| 対象 | `.github/workflows/e2e.yml:230-246` visual-language・`.github/workflows/karte-gate.yml:121-137` karte-gate の判定の式 | 必須ではないが同じ型。型をそろえ、§3 C7 の検査で 1 つの決まりとして守る |
| 対象 | 新しい検査 scripts/ci/check_ci_aggregators.py（新規） と試験 scripts/tests/test_check_ci_aggregators.py（新規） | 同じ穴が新しいまとめ役で再び生まれないように機械で止める |
| 対象 | test.yml のまとめ役 pytest に、上の検査と試験を流す段を足す | 毎回動く必須チェックの中で流すため（recon §4） |
| 対象外 | まとめ役の `if: always()` | workflow-lint.yml が文字の一致で確かめている（recon §4）。変えると PO だけが直せる検査が落ちる |
| 対象外 | `.github/workflows/workflow-lint.yml`・Ruleset・`docs/specs/rule-enforcement/required-checks.txt` | PO だけが変えられる（CLAUDE.md「不可逆操作」）。この設計は必須チェックの名前を変えない |
| 対象外 | 実行役のジョブ（pytest-run・lint-run など）の中身と動く条件・変更の判定の対象のパス | 判定の式だけを直す。試験の中身は変えない |
| 対象外 | 外の部品 re-actors/alls-green の採用 | §4 の案 B |

## 3. 変更前と変更後

### C1 test.yml のまとめ役 pytest（`.github/workflows/test.yml:268-281` の run）

変更前（要点）:

```bash
pr="${{ needs.pytest-run.result }}"
lint="${{ needs.lint-backend.result }}"
if [[ ("$pr" == "success" || "$pr" == "skipped") && ("$lint" == "success" || "$lint" == "skipped") ]]; then exit 0; else exit 1; fi
```

変更後（要点。説明の echo は残す）:

```bash
det="${{ needs.detect-changes.result }}"
out="${{ needs.detect-changes.outputs.backend }}"
pr="${{ needs.pytest-run.result }}"
lint="${{ needs.lint-backend.result }}"
echo "detect-changes: $det (backend=$out) / pytest-run: $pr / lint-backend: $lint"
if [[ "$det" != "success" ]]; then echo "FAIL: 変更の判定ジョブが success でない"; exit 1; fi
case "$out" in
  true)  [[ "$pr" == "success" && "$lint" == "success" ]] || { echo "FAIL: 変更ありなのに試験が success でない"; exit 1; } ;;
  false) [[ "$pr" == "skipped" && "$lint" == "skipped" ]] || { echo "FAIL: 変更なしなのに試験が skipped でない"; exit 1; } ;;
  *)     echo "FAIL: 判定の答えが true/false でない: '$out'"; exit 1 ;;
esac
echo "OK"
```

- 決まり（6 つのまとめ役で同じ）:
  （１）判定ジョブの結果が success でなければ赤。
  （２）判定の答えが true なら、判定に従って動く実行役は全部 success でなければ赤（skipped も赤）。
  （３）判定の答えが false なら、判定に従って動く実行役は全部 skipped でなければ赤。
  （４）判定の答えが true でも false でもなければ赤。
  （５）判定に関係なく毎回動く実行役は、いつも success でなければ赤。
- `if: always()`・`name:`・`needs:` は変えない。

### C2 e2e.yml のまとめ役 lint

C1 と同じ形。答えは `needs.detect-changes.outputs.frontend`、実行役は lint-run・unit-run。

### C3 migration-test.yml のまとめ役 migration-test

C1 と同じ形。答えは `needs.detect-changes.outputs.migrations`。判定に従う実行役は migration-registration-exists・migration-test-run・migration-full-dryrun（recon §1）。migration-registration-exists-regression は毎回動くので（５）。

### C4 schema-check.yml のまとめ役 schema-check

C1 と同じ形。答えは `needs.detect-changes.outputs.relevant`、実行役は schema-check-run。

### C5・C6 e2e.yml の visual-language・karte-gate.yml の karte-gate

C1 と同じ形。答えは frontend。karte-gate-run の条件には `|| github.event_name == 'workflow_dispatch'` がある（`.github/workflows/karte-gate.yml:36`）。手動の実行では答えが false でも実行役が動くので、karte-gate では「workflow_dispatch のときは実行役が success なら緑」を足す。

### C7 新しい検査 scripts/ci/check_ci_aggregators.py（新規）（標準ライブラリと PyYAML だけ）

.github/workflows の直下にある拡張子 .yml のファイルだけを全部読み（README.md と _archive/ は対象外）、`if` が `always()` で needs に `detect-changes` を含むジョブ（まとめ役）ごとに、次を確かめる。1 つでも外れたら、ファイル名・ジョブ名・足りないものを書いて終了コード 1。

- run の中に `needs.detect-changes.result` がある。
- run の中に `needs.detect-changes.outputs.` がある。
- needs に挙げた detect-changes 以外の全部のジョブについて、run の中に `needs.<そのジョブ>.result` がある（実行役を足したのに判定に入れ忘れたら赤）。
- 真理値表の試験: run を取り出し（名前が「Report results」の段の run だけを取り出す。今の 6 つのまとめ役は全部この名前の段を持つ。名前の段が無ければ赤）、`${{ ... }}` を値に置き換えて bash で流し、次の全部の組で終了コードが §3 C1 の決まりどおりかを確かめる。判定ジョブの結果 4 通り（success・failure・cancelled・skipped）× 答え 3 通り（true・false・空）× 実行役の結果（success・failure・skipped・cancelled）。workflow_dispatch の扱い（C6）も組に入れる。

### C8 試験 scripts/tests/test_check_ci_aggregators.py（新規）

`scripts/tests/test_check_rule_registry.py` と同じ形（`python3 -I` で流す unittest）。

- 緑の見本: C1 の形のまとめ役 1 つの yml → 終了コード 0。
- 赤の見本 1: 今の形（判定ジョブの結果を見ない）→ 1。
- 赤の見本 2: 実行役を 1 つ needs に足したが run で見ていない → 1。
- 赤の見本 3: 答えが false のときに success を許す式 → 真理値表で 1。
- 本物: 本線の `.github/workflows` 全部 → 0。

### C9 test.yml のまとめ役 pytest に段を足す

`Report results` の前に 3 段を足す: `actions/checkout@v5`（`.github` と `scripts` だけを sparse-checkout）→ python3 -I scripts/tests/test_check_ci_aggregators.py -v → python3 -I scripts/ci/check_ci_aggregators.py。どれかが落ちたら pytest のまとめ役は赤になる。pytest のまとめ役は毎回動く必須チェックなので、ワークフローだけを変える PR でも検査が走る。

## 4. 代替案と選んだ理由

| 案 | 中身 | 採否 | 理由 |
|---|---|---|---|
| A | 6 つのまとめ役の判定の式を直し、検査 C7 を必須の pytest の中で流す | 採る | `if: always()` も必須チェックの名前も変えないので、PO だけが変えられる物に触らない。真理値表で全部の組を機械で確かめられる |
| B | 外の部品 re-actors/alls-green に置き換える | 採らない | 外の部品を足すと、その版の固定と中身の見張りが新しく要る。答えが false のときだけ skipped を許す、という条件を書けるかを確かめていない（【未確認】）。自前の 10 行の式で足りる |
| C | まとめ役の `if:` を `!cancelled()` などに変える | 採らない | workflow-lint.yml の has_aggregator_pattern が落ちる（recon §4）。直すには PO だけが変えられるファイルを変える要がある |
| D | 判定ジョブをやめ、実行役を毎回動かす | 採らない | 試験を流さなくてよい PR でも数分かかる（workflow-lint.yml が理由に挙げる PR #1361 の最適化を戻すことになる） |
| E | 検査 C7 を新しいワークフローにして必須チェックに足す | 採らない | Ruleset の変更が要る（PO だけ）。C9 の形で同じことができる |

## 5. 計画（順番に。変更は一度に 1 つ）

| 段 | 中身 | 担当 | 終わりの印 |
|---|---|---|---|
| P0 | この設計と KGI の PO 承認 | PO | PO の返事 |
| P1 | 基準値: recon §3 の数え上げ（直近 300 回ずつ）を記録 | Opus | recon §3 に 4 つのワークフローの値 |
| P2 | C1〜C9 を 1 つの PR で実装（理由: 6 つのまとめ役は同じ決まりで、C7 の検査は 6 つ全部が直っていないと緑にならない） | クラウドの Sonnet（実装カードを渡す） | PR の CI が全部緑、K1・K2・K4・K5 ○ |
| P3 | マージ前の審査役（opus）の審査 → GO 記録 → 合流 | Opus | APPROVE と GO 記録 |
| P4 | 合流の後、最初の「backend を変える PR」と「frontend だけの PR」で、4 つの必須チェックが緑かを見る。7 日後に recon §3 の数え上げを流し直す | Opus | K3 ○ |

- 戻し方: 合流した PR を `git revert` する PR を出す（データも本番も触らないので、戻すとすぐ元の形に戻る）。
- 本番への影響: 無い。CI の判定の式だけで、deploy.yml にも本番のサーバーにも触らない。

## 6. 受入条件（KPI）

| 基準 | 検証方法 |
|---|---|
| K1 真理値表: 6 つのまとめ役の全部の組で、終了コードが §3 C1 の決まりどおり（外れ 0 件。組の数を記録） | C8 の試験の「本物」が CI で緑。CI の記録に組の数と外れ 0 が出る |
| K2 検査が穴を止める: 赤の見本 1〜3 で終了コード 1、本線の全部のワークフローで 0 | C8 の試験が CI で緑 |
| K3 普段の PR が赤にならない: 合流の後、backend を変える PR 1 本と frontend だけの PR 1 本で、4 つの必須チェックが全部 success。合流から 7 日の間、判定ジョブが success で、まとめ役が判定の式のせいで赤になった回 0 | P4 で gh api で実行記録を読む（scan_runs.py を合流の日から数える形にして流す） |
| K4 workflow-lint（CI設定整合性チェック）が実装の PR で緑 | 実装の PR の CI |
| K5 PO だけが変えられる物に触っていない: 実装の PR の変更ファイルに workflow-lint.yml・required-checks.txt が無い。必須チェックの名前 4 つが変わらない | `git diff --name-only origin/main...HEAD` と、4 つの `name:` の行の前後比較 |

## 7. リスクと対処

| リスク | 対処 |
|---|---|
| 判定ジョブがときどき落ちる日に、PR が赤で止まる | それが目的（試験を流さず緑にしない）。赤の文に「変更の判定ジョブが success でない」と出るので、再実行で直るかがすぐ分かる。K3 で 7 日の実数を数える |
| 取り消された回（e2e.yml の concurrency）で赤が出る | 取り消された回は判定ジョブが success でないと赤になる。PR の今の版では新しい回が動いて結果を出す。K3 で、今の版の必須チェックが赤のまま残った件を数える |
| 試験の数が増えて、まとめ役が遅くなる | C9 は sparse-checkout と標準の python3 だけ。数十秒の増え（実装の PR の CI の時間で測り、PR 本文に書く） |
| run の文の書き方の差で、C7 の真理値表の置き換えが壊れる | C7 は `${{ needs.X.result }}` と `${{ needs.detect-changes.outputs.Y }}` と `${{ github.event_name }}` だけを置き換える。ほかの `${{ }}` があれば赤にして、人が見る |
| PyYAML が実行機に無い | workflow-lint.yml が同じ実行機で `import yaml` を使っている（recon §4）。無ければ C9 の段が赤になって気づける |

## 8. 外部・過去事例の参照と我々への応用

2026-11-10 に調べた。GitHub の公式文書は Context7（/websites/github_en_actions）で本文を確かめた（【事実】）。ほかは Opus の WebSearch（standard）が返した要約で、ページ本文は開いていない（【未確認】）。

| 事例 | いつ・誰が | 何を | 何が分かるか | 数値 |
|---|---|---|---|---|
| E1 GitHub 公式文書 | GitHub | needs と always() | needs のジョブが失敗か飛ばされると、それを待つジョブは飛ばされる。always() は依存の結果も取り消しも問わず動く。公式は、失敗しうる作業には `!cancelled()` を勧めている | 結果の種類 4 つ【事実】 |
| E2 re-actors/alls-green | 公開の GitHub の部品（Ansible の開発チームの手引きが使う） | まとめ役の判定を部品にした物 | 待つジョブ全部の結果を受け取り、飛ばしてよいジョブを名前で挙げさせる（allowed-skips）。挙げていないジョブが飛ばされたら赤、という作り | 数値なし（[Marketplace](https://www.github.com/marketplace/actions/alls-green)・[Ansible の手引き](https://docs.ansible.com/projects/team-devtools/guides/gha/)）【未確認】 |
| E3 Pants（ビルド道具の開発チーム） | 2022-10-10 の記事 | 条件で飛ばしたジョブと必須チェック | 条件で飛ばされたジョブは、必須チェックでは成功として扱われる。そのため集約のジョブを置いた | 数値なし（[記事](https://v2.pantsbuild.org/blog/2022/10/10/skipping-github-actions-jobs-without-breaking-branch-protection)）【未確認】 |
| E4 自社 Issue #523 / PR #534 | 自社 | paths の絞り込みと必須チェック | 必須チェックが「報告なし」のまま待ち続け、PR を合流できなくなった。この学びで今のまとめ役の型ができた（recon §0） | 自社の記録 |

我々への応用:
- E2 の考え方（飛ばしてよいのは名前で挙げた物だけ）を、我々は「判定の答えが false のときだけ飛ばしてよい」という条件にした。E2 は飛ばしてよいジョブを固定で挙げるので、答えが true のときに飛ばされても通ってしまう（【推測】）。条件つきの方が我々の型に合う。
- E1 の `!cancelled()` の勧めは、workflow-lint.yml の文字の一致のため今は採れない（§4 案 C）。判定の式で「判定ジョブが success でなければ赤」にするので、取り消しでも緑にはならない。
- E4 の学びは守る。まとめ役は今と同じく毎回動いて結果を報告するので、「報告なし」の待ちは起きない。
- 外の数値は設計の成否の証明に使わない。成否は K1〜K5（自社の CI の結果）で決める。

## 9. 維持の仕組み

| 守ること | 仕組み | 今あるか | 根拠 |
|---|---|---|---|
| 6 つのまとめ役が判定ジョブの結果を見続ける | C7 の検査が必須の pytest の中で毎回動く | 実装の後にできる | §3 C7・C9 |
| 新しいまとめ役が同じ穴を持って生まれない | C7 は `.github/workflows` の直下の .yml を全部見るので、新しいまとめ役も対象になる | 実装の後にできる | §3 C7 |
| 実行役を足したのに判定に入れ忘れない | C7 の 3 つ目の確かめ | 実装の後にできる | §3 C7 |
| 検査そのものが壊れても気づく | C8 の赤と緑の見本の試験 | 実装の後にできる | §3 C8 |
| まとめ役の型（detect-changes＋always()）が消えない | workflow-lint.yml の has_aggregator_pattern（migration-test.yml・e2e.yml） | 有り | `.github/workflows/workflow-lint.yml:86-95`・`:148-172` |

- 守り手: .github/workflows/test.yml のまとめ役 pytest（必須チェック「pytest (SQLite + PostgreSQL RLS)」）。実装の後は、この中で scripts/ci/check_ci_aggregators.py が毎回動く。今は .github/workflows/workflow-lint.yml が型の有る無しだけを守っている。
- 足りないもの: test.yml・schema-check.yml・karte-gate.yml の型の有る無しは workflow-lint.yml の対象に入っていない（`.github/workflows/workflow-lint.yml:86-95` は migration-test.yml と e2e.yml だけ）。C7 は「まとめ役がある場合の中身」を見るが、「まとめ役が消えた」ことは見ない。C7 はまとめ役を「needs に detect-changes という名前のジョブを持つ」ことで見つけるので、別の名前の判定ジョブを使うまとめ役は見逃す。workflow-lint.yml に足すのは PO だけができるので、この設計では足さず、PO に示す。

## 10. 自己審査（Architect・同じ AI による。独立した第二者の審査ではない）

- 判定: 審査役（opus）が 2026-11-10 に c85ddd1b6 で APPROVE。止める指摘 0 件。止めない指摘 5 件（危険なパスの GO・C7 の対象と段の名前・行番号の 1 行の差・§10 の古い文・判定ジョブの名前）は、この版で全部直した。
- 確かめたこと: 触るのは CI の判定の式と新しい検査だけ。migrations・deploy.yml・workflow-lint.yml・Ruleset に触らない（K5）。scripts/ の下に新しい検査を作るので、実装 PR は GO 記録が要る。受入条件は全部、CI の結果か gh api の数で ○× が決まる。変更前と変更後の式、触らない範囲を書いた。
- 残る未確認: recon §5（判定ジョブが失敗する頻度・取り消された回のまとめ役の出力）。必須でない 2 つのまとめ役の数え上げ。どちらも設計の形を変えない（穴の仕組みはファイルの中身と公式文書で確かめた）。
