# 共有 DB の後片付けを札の外で流す試験を止める見張り — 設計

前のテーマ: docs/handoff/ci-test-shared-collisions/（design §10・recon §6-5 で、このテーマを別に回した）。

## 1. 目的（KGI・PO 2026-11-27「1」で承認）

| # | 基準 | 検証方法 |
|---|------|---------|
| G1 | 新しい見張りの試験が main で pass する | 合流後の main の Backend Tests で、その試験が passed |
| G2 | 当たった関数のうち、分類が書かれていないものが0件 | 見張りの試験の中の分類表と、機械で探した一覧の差が0（試験が自分で数える） |
| G3 | わざと札の外で後片付けをする関数を足すと、見張りが赤になる | 見張りの試験の中に、仮の文字列を読ませて落ちることを確かめる試験を置く |
| G4 | 共有 DB で札の外にあったものは、全部札の中へ移す | 分類表に「共有 DB・札の外」が0件 |
| G5 | 変えるのは試験コードだけ | `git diff --name-only origin/main...HEAD` に backend/tests/ と docs と台帳しか無い |
| G6 | passed の数は main と同じ＋見張りの分だけ。skipped は main と同じ | PR の CI の pytest の要約行を main と比べる |

分類は3つ: 使い捨て（own_database・SQLite・文字として読むだけ）／札の中（public_bootstrap_lock か同じ鍵）／直した（札の中へ移した）。

## 2. 現在地（recon.md に書く・クラウドの Sonnet が調べる）
（未記入）
