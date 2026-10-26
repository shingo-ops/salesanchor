# design: 画面検査の実行環境を ubuntu-24.04 に固定する（CI 修理便）

> この文書は何か（1行）: CI の画面検査が「Playwright が ubuntu-26.04 に対応していない」で1件も走らずに赤くなる状態を、社内の先例と同じ1行の固定で直す便の設計。

**日付**: 2026-10-26
**recon**: `docs/handoff/ci-pin-e2e-runner/recon.md`
**由来**: PR #4780（Popover 金型・宿題 C2）の CI で発覚。PO 決定（2026-10-26・3案から選択）＝**「別便で先に直す」**
**対象ADR**: ADR-044（CI 健全性の回復）

## ① 区分：B（仕組み・CI の変更。画面の見た目は変わらない）

| 項目 | 内容 |
|---|---|
| PO 決定（2026-10-26） | 3案（別便で先に直す／#4780 に同梱／待つ）から **「別便で先に直す」** を選択 |
| 変えるもの | `.github/workflows/e2e.yml` の Playwright を使う2ジョブの `runs-on` を `ubuntu-latest` → `ubuntu-24.04` |
| 変えないもの | テストの中身・spec・`@playwright/test` の版・キャッシュ鍵・他のワークフロー |

## ② KGI（PO が ○× を判定できる粒度）

| # | 確かめること | ○× の基準 |
|---|---|---|
| K1 | この PR の CI | `画面検査（内部）` が**緑になり、テスト件数が報告される**（いまは0件で赤） |
| K2 | PR #4780 の CI（本便マージ後に main を取り込んで再実行） | 画面検査が走り、新 spec の**18件が結果に出る** |
| K3 | 他の検査 | 既存の検査が**1つも赤くならない** |

## ③ KPI（機械で測る値）

| 指標 | 測り方 | 合否 |
|---|---|---|
| 画面検査で実行されたテスト件数 | CI の `画面検査（内部）` のログ | **1件以上**（いまは0件） |
| 画面検査の結果 | 同 | **失敗0** |
| 変更行数 | `git diff --stat` | `.github/workflows/e2e.yml` のみ・**6行追加 2行削除**（うち4行はコメント） |

## ④ 設計（How）

`.github/workflows/e2e.yml` の2か所を、**先例 `.github/workflows/karte-gate.yml:37-38` と同じ形**（理由コメント＋`ubuntu-24.04`）に揃える。

| 場所 | ジョブ | 変更 |
|---|---|---|
| `:148-152` | `visual-language-run`（`画面検査（内部）`） | `runs-on: ubuntu-latest` → `ubuntu-24.04`＋理由コメント2行 |
| `:245-248` | `playwright`（`Playwright E2E (chromium)`・`if: false` で停止中） | 同じ（**再開した瞬間に同じ赤になる**ので今のうちに揃える） |

**やらないこと**:

- `@playwright/test` の版上げ。基準画像（スクリーンショット比較）の食い違いを招き得るため。karte-gate が固定を選んだのと同じ判断。
- `.github/workflows/brand-asset-monitor.yml`・`.github/workflows/qa-smoke.yml` の固定。定期実行・手動実行で PR を塞がないため別件（⑫）。
- キャッシュ鍵への OS 版の追加（⑫）。

## ⑤ Acceptance Criteria

| # | 基準 | 検証方法 |
|---|---|---|
| C1 | YAML が壊れていない | `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/e2e.yml'))"` |
| C2 | 変更は `runs-on` の2行＋コメント4行だけ | `git diff` |
| C3 | この PR の CI で `画面検査（内部）` が緑・**テストが1件以上実行**される | CI（一次情報。この端末では Playwright のブラウザが動かない） |
| C4 | 他の必須検査が赤くならない | CI |
| C5 | 固定先 `ubuntu-24.04` が実在し Playwright が動く | 同一 run 40274501029 の `karte-gate-run`（`ubuntu-24.04`）が**緑**＝実証済み |

## ⑥ 触るファイル

| ファイル | 変更 |
|---|---|
| `.github/workflows/e2e.yml` | `runs-on` 2か所＋理由コメント |
| `docs/handoff/ci-pin-e2e-runner/recon.md`・`docs/handoff/ci-pin-e2e-runner/design.md` | 本書類（新設） |
| `.claude-pipeline/active-work.d/release-ci-pin-e2e-runner.md` | 台帳 |

## ⑦ 戻し方

本 PR の revert 1回（`runs-on` が `ubuntu-latest` に戻るだけ）。

## ⑧ 削除するファイル

なし。

## ⑨ 外部・過去事例の参照と我々への応用

- **社内の先例をそのまま横に広げる**: `.github/workflows/karte-gate.yml:38` が 2026-10-24（コミット `da513ba49`）に
  同じ理由・同じ値で固定済み。**新しい流儀を増やさない**。
- その先例が有効であることは**同一 CI 実行（run 40274501029）の中で実証**されている
  （`karte-gate-run` は緑／`画面検査（内部）` は赤）。推測ではなく一次情報。
- GitHub の `ubuntu-latest` は時期で中身が変わる＝**版を固定しない参照はいつか必ず壊れる**。
  画像比較やブラウザ依存の検査では固定が定石（Playwright 公式も OS ごとに依存を配る形）。

## ⑩ 弊害・トレードオフ

| 弊害 | 程度・対応 |
|---|---|
| `ubuntu-24.04` はいつか提供終了する | その時は `@playwright/test` を上げて固定を外す。期限は GitHub のアナウンス次第（⑫） |
| 新しい OS での動作確認が後回しになる | 画面検査は「見た目の回帰を止める関所」で、OS の新しさを確かめる場ではない |

## ⑪ 維持の仕組み

守り手: CI の `画面検査（内部）`（`.github/workflows/e2e.yml` の `visual-language-run`。毎 PR・3幅）

| 守ること | 関所 | 外すと |
|---|---|---|
| 画面検査が実際に走っている（0件でない） | 同ジョブのテスト件数 | 件数0＝実質ノーガードになる（今回の事故そのもの） |

## ⑫ 継続（この便の後）

| # | 項目 | 状態 |
|---|---|---|
| D1 | `.github/workflows/brand-asset-monitor.yml`・`.github/workflows/qa-smoke.yml` の Playwright ジョブも同じ固定が必要か点検 | 起票のみ |
| D2 | Playwright キャッシュ鍵に OS 版を含める（`playwright-${{ runner.os }}-…` では 24.04/26.04 を区別できない） | 起票のみ |
| D3 | `@playwright/test` を ubuntu-26.04 対応版へ上げて固定を外す（基準画像の引き直しが必要） | 起票のみ |
| D4 | 「テストが0件なのに緑/赤」を見分ける仕組み（件数0を失敗にする） | 起票のみ。今回は人が気づいた |
