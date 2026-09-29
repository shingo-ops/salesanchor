# 設計 — 台帳DONE化の自動化（main）

> この文書は何か（専門用語なしの1行）:
> マージが終わったら作業記録を機械が自動で更新して片付けるための作り方。

対象ADR: ADR-114
recon: docs/handoff/ledger-auto-done-main/recon.md
親テーマ: docs/specs/ledger-guard/README.md

## 1. あるべき姿

全員が同じ1枚の紙に書くから、消し合いが起きる。だから各自が自分の紙に書く。
台帳の書き先は1ブランチ1ファイルに分かれ、一覧は機械が束ねて表示する。

## 2. recon（実測）

docs/handoff/ledger-auto-done-main/recon.md を参照。要点は次の4つ。

- 既存の active-work-auto-done.yml は develop 向けで main では発火しない。
- cleanup-worktree.sh は DONE 化するが commit / push しない。
- 台帳のみの変更は関所が自動スキップする。GO記録は不要。
- main は ruleset により直接 push できない。PR を経由する必要がある。

## 3. design（技術How）

`.github/workflows/ledger-auto-done-main.yml` を新規作成する。

処理の流れ:

1. main への PR がマージされたら発火する。
2. `release/ledger-done-*` と `release/ledger-auto-*` は対象外にする。
3. `.claude-pipeline/active-work.d/<セーフ形>.md` の存在を確認する。
4. 在れば `ledger-update.sh` で DONE と PR番号を書き込む。
5. 台帳ブランチを作り、PR を作成する。
6. `gh pr merge --auto --merge` で自動マージを予約する。

トークンは `PIPELINE_PAT` を使う。PR作成と push の両方に必要である。

PR本文は `mktemp` でファイルに書き出し `--body-file` で渡す。

## 4. 外部・過去事例の参照と我々への応用

GitHub は無限ループ防止のため GITHUB_TOKEN によるプッシュで
新しいワークフローを起動しない。そのためボットが作ったPRでは
必須チェックが走らず auto-merge が永久に待つ事例が報告されている。
あるリポジトリでは依存更新6件がテスト実行ゼロで main に着地し、
`gh run list --commit <sha>` がどれも空を返すことで事後に判明した。

対処は PAT または GitHub App トークンでPRを作成することである。
本設計は既存の `PIPELINE_PAT` を用いる。

一方で PAT はループ保護を回避するため、
台帳PR自身を対象外にする条件が無いと無限ループになる。
本設計は `startsWith` による除外を2件置いている。

導入の順序として、低リスクの変更（依存更新・書類）から始め、
自信がついてから範囲を広げることが推奨されている。
台帳ファイルはこの「低リスク」に該当する。

また、この仕組みの安全性はCIの質に依存する。
必須チェックが設定されていなければワークフローが承認した瞬間にマージされうる。
本リポジトリには必須チェックが12件あり、失敗すればマージされない。
`--auto` は迂回ではなく、緑になるまで待つ仕組みである。

## 5. 弊害・トレードオフ

- 弊害: 自動マージのため内容を誰も見ない。
  台帳のみの変更に限定することで影響を抑える。
- 弊害: ワークフローにバグがあっても気づきにくい。
  各ステップが失敗時に警告を出して exit 0 するため、
  台帳が更新されないまま静かに終わる可能性がある。
  対処として GitHub Actions のログに warning が残る。
- 弊害: PR本文を run ブロック内に直書きすると YAML 構文エラーになる。
  実際に1度発生した（2026-09-02）。mktemp と --body-file に逃がして解決した。
- トレードオフ: 既存の active-work-auto-done.yml を残す。
  develop 運用が残っている可能性があり、削除の判断には別途 recon が要る。
  結果としてワークフローが2本並存する。

## 6. 受入基準

| 基準 | 検証方法 |
|---|---|
| YAML として妥当である | python3 の yaml.safe_load が例外を出さない |
| PIPELINE_PAT を2箇所で使う | grep -c 'secrets.PIPELINE_PAT' が 2 |
| GITHUB_TOKEN を使わない | grep -c 'secrets.GITHUB_TOKEN' が 0 |
| 台帳PR自身を除外する | grep -n 'startsWith' が 2 件 |
| PR本文をファイルに逃がす | grep -c 'body-file' が 1 |
| 既存ワークフローを壊さない | git diff に active-work-auto-done.yml が現れない |
| 実環境で動作する | 次に main へマージされたPRで台帳PRが自動生成されることを確認 |

## 7. 維持の仕組み

- 守り手: 人手で守る
- 理由: ワークフローの動作は実際のマージを待たないと検証できない。
  自動テストで再現するには GitHub Actions の実行環境が必要であり、
  現時点でその仕組みを持たない。
- 対象: main マージ後に台帳PRが作られなくなること。
- 検知方法: `scripts/ghost-count.sh` が台帳の IN_PROGRESS のうち
  実在しないブランチを数える。閾値超過で警告が出る。

---

## 追補：auto-merge の限定（2026-09-29）

> この節は何か（専門用語なしの1行）:
> 台帳の自動マージを「台帳の記録PRだけ」に限り、それ以外の自動マージは機械が取り消すようにする作り方。

対象ADR: ADR-050（追補先）、ADR-114
recon: docs/handoff/ledger-auto-done-main/recon.md（追補節）

### 追補 1. なぜ必要か

GitHub の「Allow auto-merge」はリポジトリ全体の設定で、PR の種類ごとには分けられない。
GO 記録を検査する gate は必須チェックに入っていない。
そのため設定を ON にすると、GO を受けていない PR にも自動マージを予約できてしまう。
台帳ワークフローは既に予約を試みているが、設定が OFF で毎回失敗し、`exit 0` で隠れていた（recon 追補）。

### 追補 2. 設計

- A. 判定は `scripts/ci/is-ledger-done-pr.sh <PR番号>` の1か所。次の4条件をすべて満たすと exit 0、満たさなければ理由を stderr に出して exit 1。
  1. head ブランチ名が `release/ledger-done-` で始まる
  2. タイトルが `^chore\(ledger\): .*DONE 化（自動）$` に一致する
  3. 変更ファイルが1件以上で、すべて `.claude-pipeline/active-work.d/` の下（`..` を含むパスは不可）
  4. 作成者が `shingo-ops`（スクリプト内の定数 `LEDGER_PR_AUTHOR` 1か所）
- B. `ledger-auto-done-main.yml`: 予約の直前に A を実行し、不合格なら `::error::` で失敗。予約失敗の `exit 0` は `exit 1` に変更。`workflow_dispatch` の `mode: backlog` を追加し、open の台帳DONE化PRを1本（`release/ledger-done-backlog-<YYYYMMDDHHMM>`、UTC）にまとめて自動マージを予約し、取り込めた旧PRだけを「#新PR に統合」でクローズする。通常時の起動条件・ブランチ名・タイトルは変えない。
- C. `ledger-done-update-branch.yml`（新規）: main への push で、予約済みかつ BEHIND の台帳DONE化PRに update-branch を実行する。concurrency で1本ずつ。失敗したらジョブを赤にする。
- D. `auto-merge-guard.yml`（新規）: `pull_request_target: auto_merge_enabled` で起動。PR のコードは checkout せず、main 側の A だけを使う。不合格なら `--disable-auto` で取り消し、コメントを残す。失敗したらジョブを赤にする。permissions は `contents: read` のみで、取り消しとコメントは PIPELINE_PAT で行う。

`git grep "ledger-done-"` に残る箇所の意味づけ（判定ではない）:
- ledger-auto-done-main.yml の `startsWith(... 'release/ledger-done-')`: 無限ループ防止の除外（既存）。
- backlog モードの候補列挙: 「候補を集める」ための前段。採否は必ず A が決める。

既知の穴: GITHUB_TOKEN で `--auto` を予約した場合は D が起動しない。今後 GITHUB_TOKEN で `--auto` を使うワークフローの追加を禁止する（ADR-050 追補）。

### 追補 3. 受入基準

| 基準 | 検証方法 |
|---|---|
| 判定の条件が1か所にある | `git grep -n "ledger-done-" .github/workflows scripts/ci` で、4条件の判定を持つのが `scripts/ci/is-ledger-done-pr.sh` だけ（他は除外・候補列挙・呼び出し） |
| 判定が4条件で正しく分かれる | `bash scripts/tests/test-is-ledger-done-pr.sh` が全PASS（合格1・各条件欠4・files0件・パス脱出・引数なし） |
| ワークフローが構文として妥当 | `actionlint` が3本すべてエラーなし |
| 予約失敗・条件外が失敗として見える | `gh pr merge --auto` の失敗分岐が `exit 1` になっている | `grep -n -A3 'gh pr merge --auto' .github/workflows/ledger-auto-done-main.yml` の else 側が `::error::` と `exit 1` |
| マージのたびに DONE化PR が自動で入る | 本PRのマージと Allow auto-merge ON の後、次に通常PRがマージされたとき `release/ledger-done-<番号>` が人手なしで merged になる |
| 台帳以外の予約は取り消される | マージ後のテスト用PRに `--auto` を付ける → 数十秒後に `autoMergeRequest` が null になりコメントが付く |
| 溜まりがゼロ | backlog モード実行後、open の `release/ledger-done-` PR が 0 件 |

### 追補 4. 外部・過去事例の参照と我々への応用

該当なし。理由: 本追補はこのリポジトリの ruleset・ワークフロー・GitHub 公式仕様（recon 追補）の事実だけを根拠にする、リポジトリ固有の許可範囲の限定であり、外部事例に倣う設計判断を含まないため。

### 追補 5. 弊害・トレードオフ

- main が進む回数が、通常のマージ1件につき +1 になる。他のPRが BEHIND になる機会が増える（作業が消えることはない: merge commit のみ・strict）。
- 判定の作成者条件は `shingo-ops` が PO 本人のアカウントでもあるため、単独では決め手にならない。4条件の AND で担保する。
- 予約の失敗を赤にするため、設定 OFF の間は台帳ワークフローが毎回失敗する。これは失敗を可視化するための意図的な変更で、Allow auto-merge の ON 後に解消する。

### 追補 6. 戻し方

- PO が Allow auto-merge を OFF にする（すぐ効く）。
- 3本のワークフローと `scripts/ci/` を元に戻す PR を出す。

## 維持の仕組み（追補）

- 守り手: scripts/tests/test-is-ledger-done-pr.sh（判定の4条件）と .github/workflows/auto-merge-guard.yml（台帳以外の予約の取り消し）
- 対象: 台帳以外の PR に自動マージが予約されたまま main に入ること／判定条件が複数箇所に増えて食い違うこと。
- 検知方法: auto-merge-guard.yml が取り消しに失敗するとジョブが赤になる。判定の変更はテストが赤になる。`test-is-ledger-done-pr.sh` は現状 CI に組み込まれていないため、判定を変える便で手で実行する（CI 組み込みは別便）。
