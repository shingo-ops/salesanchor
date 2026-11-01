# Phase 3 設計 — 必須でない確かめが赤いままの合流を機械で止める

- 下調べ: docs/handoff/merge-red-check-guard/recon.md
- 実装の指示: docs/handoff/merge-red-check-guard/card.md（変更前後・分岐・手順はカードが正）
- 対象 ADR: ADR-1029（AI のマージをフックで止める）に What 7 を追補する。関連: ADR-121（test-schema-dup gate）・ADR-1011（hooks は AI がパッチ、PO が `!` で反映）
- PO の選択: 2026-11-01「１」＝「同じ見落としを機械で止める仕組みを作る。必須でない確かめが赤いままだと、本線に入れる操作が止まるようになります」。
- KGI（○×）: salesanchor の PR で、確かめが 1 つでも緑でない（fail・cancel・pending）とき、AI の合流の命令は 100% 止まる。全部が pass か skipping なら、今までどおり通る。

## 1. 選んだ案と、選ばなかった案

- 選んだ案 B: 見張り gate.py の resolve（recon §2）で、APPROVE 記録の照合が通った後に `gh pr checks <番号> --repo shingo-ops/salesanchor --json name,bucket` を読む。pass・skipping 以外が 1 つでもあれば止める。止める文に、緑でない確かめの名前を全部書く。
  - 理由1: 赤のまま入った 18 件の道（直接の合流の命令）を、この見張りはすでに全部見つけている（recon §2）。足りないのは色の判定だけ。
  - 理由2: 正規の道 gh-pr-merge-safe.sh と同じ基準になる（CLEAN でなければ止める・recon §1）。道によって基準が違う状態をなくす。
  - 理由3: 今後増える「必須でない確かめ」にも、追加の作業なしで効く。
- 選ばなかった案 A: test-schema-dup gate を GitHub の必須の確かめ（Ruleset）に足す。画面からの合流や自動合流にも効くが、1 つの確かめにしか効かない。Ruleset の変更は不可逆操作の扱いで PO の同意票が要る。PO が選んだのは「必須でない確かめ全部」なので B を採る。A は B の後でも足せる（B と食い違わない）。
- 選ばなかった案 C: 直接の合流の命令を全部禁止し、gh-pr-merge-safe.sh だけにする。別のリポジトリ（kb・作業画面アプリ）の合流と、危険 PR の GO の手順が使う直接の命令まで止まるので採らない。

## 2. 決めごと（実装はカードどおり）

| 項目 | 決め | 理由 |
|---|---|---|
| かける範囲 | owner/repo が shingo-ops/salesanchor の PR だけ（大文字小文字は区別しない） | 作業画面アプリは macOS の赤のまま 8/25 件が入っている運用で、全部にかけると今の運用が止まる（recon §5） |
| 通す色 | pass・skipping | skipping は条件で走らない確かめ（#4967 で 11 件）。止めると全 PR が止まる |
| 止める色 | fail・cancel・pending・その他の値 | pending を通すと、後で赤になっても合流済みになる。知らない値は止める側に倒す |
| 一覧が読めない | 止める（gh の失敗・JSON でない・空の一覧） | 既存の決まり「gh が失敗したら止める」（ADR-1029 What 3）と同じ |
| 終了コード | 見ない。中身だけで判定する | `--json` 付きは pending でも 0（recon §4） |
| かける命令 | 見張りが見つける合流の命令すべて（gh pr merge・--auto・gh-pr-merge-safe.sh・check-pr-merge-ready.py・gh api / curl の merge） | 道で基準を分けない |
| 順番 | APPROVE の照合と --auto の照合の後、allow の記録の前 | 審査が無い PR では今までどおり審査の文で止める |

## 3. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| salesanchor で赤が 1 つあると止まる | 試験 C2: 偽の gh が fail を 1 件返すと exit 2、止める文にその名前が出る |
| salesanchor で走り中があると止まる | 試験 C3: pending を 1 件返すと exit 2 |
| 取り消された確かめで止まる | 試験 C4: cancel で exit 2 |
| 一覧が読めないと止まる | 試験 C5（空の一覧）・C6（JSON でない・終了コード 1）で exit 2 |
| 全部緑なら通る | 試験 C1: pass と skipping だけで exit 0 |
| --auto でも止まる | 試験 C7: --auto --match-head-commit 一致・fail ありで exit 2 |
| 正規の道の命令でも止まる | 試験 C8: gh-pr-merge-safe.sh・fail ありで exit 2 |
| ほかのリポジトリは変わらない | 試験 C9: repo o/r・fail ありでも exit 0。既存の試験が全部 PASS のまま |
| CI が緑 | PR の agent-hooks-test（.github/workflows/agent-hooks-test.yml:25）が success |
| 入れた後に本物で効く | 合流の後、PO が `!` で install.sh を実行し、その出力が INSTALL_OK（install.sh:77 が写した先の台本で試験を流し、FAIL 0 のときだけ出す） |

## 4. 技術 How・KPI

- 足すもの: 定数 2 つ（かける範囲・通す色）、止める文 1 つ、関数 gh_checks（gh_view と同じ書き方）、resolve の中の判定 1 か所。標準ライブラリのみ（gate.py の決まり :10）。
- 試験: 偽の gh に `pr checks` の答えを足す（$FAKE_CHECKS_JSON・$FAKE_CHECKS_RC）。試験 C1〜C9 を足す。
- KPI: 導入後 30 日に、salesanchor で緑でない確かめのまま入った PR の数（台帳の自動合流を除く）。基準値は 10/31 の 18 件。目標 0 件。数え方は recon の merged-gate-status.txt と同じ台本で行う。

## 5. 弊害・トレードオフ

- 本線が赤い間は、関係のない書類だけの PR も合流できなくなる。これは狙いどおり（赤を放置したまま積み上がった 21 件の再発を止める）。本線の赤を先に直す。
- 確かめが壊れて誤って赤を出し続けると、AI は合流できない。その間は PO が画面から合流できる（見張りの外）。今の test-schema-dup gate の誤りは 0 回（recon §3）。
- 合流 1 回ごとに gh の呼び出しが 1 回増える（数秒）。
- 画面からの合流・台帳の自動合流（.github/workflows/ledger-auto-done-main.yml）は止まらない（ADR-1029 の受け入れるリスクと同じ）。台帳の自動合流は台帳だけを変えるので、本線を新しく赤くしない。

## 6. 外部・過去事例の参照と我々への応用

- 外部事例は使わない。理由: 新しい技術の選択が無く、既存の見張り（ADR-1029）と正規の道の基準（check-pr-merge-ready.py:100-101 の CLEAN）をそろえるだけのため。
- 過去事例: 10/31 に赤のまま 22 件が入った件（recon §1）。設計書の作法「必須でない赤も全部読む」（docs/handoff/test-schema-dup-ops-case/design.md の継続欄）だけでは止まらなかったので、今回は機械で止める。

## 7. 計画票

| 段 | 中身 | 担当 |
|---|---|---|
| 1 | 下調べ・設計・カード・ADR-1029 追補の書類 PR | Opus |
| 2 | 設計審査（審査役 opus） | 審査役 |
| 3 | カードどおりの実装と push（PR は作らない） | Sonnet（クラウド） |
| 4 | PR を手元で shingo-cc 名義で作る・CI と審査・合流 | Opus・審査役 |
| 5 | 本物の見張りへの反映（install.sh） | PO が `!` で実行（ADR-1011:39） |
| 6 | 反映後の試験（受け入れ基準の最後の行） | Opus |

## 8. 継続・維持の仕組み

- 守り手: scripts/agent-hooks/review-gate/gate.py（見張り本体）と scripts/agent-hooks/review-gate/test_review_gate.sh（CI .github/workflows/agent-hooks-test.yml で毎回流れる）。
- 決まりの正本: ADR-1029 What 7（このPRで追補）。
- 戻し方: 実装 PR を revert し、PO が install.sh を `!` でもう一度流す（前の gate.py が写る）。急ぐときは rollback.sh で見張りごと外す。本番には触れない。
