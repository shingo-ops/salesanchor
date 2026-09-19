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
