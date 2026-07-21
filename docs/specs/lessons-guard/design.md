# design（技術How・差分設計）

> この文書は何か（専門用語なしの1行）:
> 教訓を「1便1ファイル」で書き、機械が束ねて1つに見せる仕組みの設計図。

- 親: [README.md](./README.md)／KGI: [kgi.md](./kgi.md)
- recon: docs/handoff/lessons-guard/recon.md（配置は便1で実施）
- 関連ADR: ADR-114（消さず残す原則を踏襲）

## 1. 構成

- 置き場: docs/ai-agents/lessons.d/（.gitkeepで常設）
- ポスト書式: 1便=1ファイル。ファイル名 YYYYMMDD-<短い英語スラッグ>.md。
  冒頭に「分類: 6-1〜6-5」「出所: （YYYY-MM-DD PR #NNNN）」の2行＋教訓本文（箇条書き可）。
- 束ね: scripts/lessons-view.sh — design-partner.md §6本文の後に lessons.d/ の
  全ポストを分類タグ順→ファイル名順で連結表示（ledger-view.sh の型を流用）。
- 還流: ポストが概ね20枚を超えたら「清書便」で本体§6へ逐語移植し、
  移植済みポストは lessons.d/archive/ へ移動（削除しない・ADR-114踏襲）。
- 過渡期ルール: §6本文への直接追記は原則禁止（清書便のみ例外）。
  違反検知は便2の警告ワークフロー（初期は警告のみ、停止化は別GO）。

## 2. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| L1 置き場常設 | git show origin/main:docs/ai-agents/lessons.d/.gitkeep |
| L2 相互接触ゼロ | 2ブランチ同時ポスト作成→各PRのdiff --stat照合 |
| L3 束ね表示動作 | bash scripts/lessons-view.sh の出力に本体＋ポスト件数の合算行 |
| L4 読み動線切替 | grep "lessons-view" docs/ai-agents/design-partner.md |
| L5 直接追記の警告 | 検知ワークフローのPRコメント実測 |

## 3. 弊害・トレードオフ

- 教訓が2箇所（本体＋ポスト）に分かれる期間が常態化する。束ね表示を経由しない
  読み方だとポストを見落とす。対策: L4で読み動線を正本に固定。
- 清書便が滞るとポストが溜まる。対策: 閾値20枚を束ね表示の末尾に警告表示。

## 4. 外部・過去事例の参照と我々への応用

- Debian/Nginx/systemd の conf.d / drop-in 方式（共有1枚を分割ファイル＋機械結合に置換）。
- 本リポジトリの ledger-guard（台帳で同型を実証: G3/G5実測PASS・PR #2939/#2953）。
  台帳との差: 台帳は行の機械追記、教訓は文章＝人が書く。ゆえに束ねは表示のみで
  自動マージはしない（意味の衝突は清書便の人間判断に残す）。

## 4.5 停止化とラベル例外（2026-07-21・便2a）
- lessons-guard は §6本文への箇条書き追記（`^+- ` 検知）を exit 1 で停止する。
- 例外: PRに `lessons-cleanup` ラベルが付く場合のみ通す（清書便＝ポストの§6本文移植）。清書便はこのラベルを必須とする。
- 物理的マージ阻止は便2bで ruleset の必須チェックに warn-direct-lesson-edit（job名）を登録して完成する。便2a単独では赤表示のみ（必須未登録）。

## 5. 維持の仕組み

- 守り手: scripts/lessons-view.sh（束ね表示の実体。壊れると読み動線が切れる）
- 守り手: 便2の直接追記検知ワークフロー（.github/workflows/ 配下・便2で命名確定）
- 対象: 「1便1ファイル」の書き先と束ね表示が壊れると、共有1枚への逆流＝衝突が再発する。
