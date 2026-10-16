# KGI(○×で測る・数値化)

この文書は何か(専門用語なしの1行): このテーマの合格条件を、○×で判定できる数字にした一覧。

親: [README.md](./README.md)

状態: PO 承認済み（2026-10-16 チャット「y」）。正本は [design.md §1・§5](../../handoff/vm-test-on-gha/design.md)。食い違えば design.md を直してから本表を合わせる。

| # | 合格条件 | 測り方 | 合格ライン | 結果 |
|---|---|---|---|---|
| K1 | GitHub 上で仮想マシンの要る試験が動く | Actions 画面で `sandbox-test` を `test=smoke` で手動実行 | 緑。ログに postgres の `select 1` の結果 `1` | 未 |
| K2 | 新しい手順書が Mac で仮想マシンを作らせようとすると止まる | 捨て PR で docs に `colima start --profile x` を1行足す | `no-mac-vm-guard` が赤。同じ行に `vm-guard-allow: 理由` を付けると緑 | 未 |
| K3 | PR の検査が遅くならない | 導入前後で main の Ruleset の必須チェック数を数える。PR のチェック一覧に `sandbox-test` が出ないこと | 必須チェック数が前後で同じ・`sandbox-test` 0 件 | 未 |
| K4 | 秘密の情報を使わない | `.github/workflows/sandbox-test.yml` と `tests/sandbox/` で `secrets.` を数える | 0 件 | 未 |
| K5 | Mac に一時的な仮想マシンが作られなくなる | 導入から 14 日後（目安 2026-10-31）に `colima list` | `default`・`sa-private-ci` 以外の profile 0 件 | 未 |

KPI: 合格した KGI の数 ◯/5。
