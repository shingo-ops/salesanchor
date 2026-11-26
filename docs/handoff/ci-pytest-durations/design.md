# design: CI の pytest の記録に遅い試験30件を毎回出す

状態: 設計案作成済み・設計審査済み（Opus 自己審査）。PO の実装承認 2026-11-26「1」。
参照: docs/handoff/ci-pytest-durations/recon.md

## 1. 目的（KGI）
CI で本当に遅い試験を、毎回の記録で読めるようにする。今は CI の記録に試験ごとの時間が出ず、遅い試験を直す順番を決められない（recon.md「未確認」）。
**KGI: この PR 自身の CI の段「Run pytest (full suite + PostgreSQL RLS)」の記録に、`slowest 30 durations` の見出しと、その下の30行が出る。**

## 2. 対象と対象外
- 対象: `.github/workflows/test.yml:259` の1行だけ。
- 対象外（触らない）: `backend/pyproject.toml` の addopts（手元やクラウドの実行まで出力が増えるため）、試験そのもの、製品コード、他のワークフロー、必須チェックの名前、`timeout-minutes`。

## 3. 変更内容
`.github/workflows/test.yml:259`
- 前: `          pytest -q --tb=short`
- 後: `          pytest -q --tb=short --durations=30`

字下げ（空白10個）は変えない。行の追加・削除は他に無い。

## 4. 代替案と選んだ理由
- A（採用）test.yml の実行行に足す: CI だけに効く。1行で戻せる。
- B pyproject.toml の addopts に足す: 手元・クラウドの出力まで増える。不採用。
- C junit を成果物として保存して集計: 段と保存の設定が増える。まず A で順位を見て、足りなければ検討。

## 5. リスクと対処
- 記録が約30〜60行増えるだけ。合否・必須チェックの名前は変わらない。
- 時間の増加: 一覧の表示だけで、試験の実行は増えない。CI の段の時間を、前の回の main の実行と比べて記録する（受け入れ基準 K2）。

## 6. 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| K1: この PR の CI の段「Run pytest (full suite + PostgreSQL RLS)」の記録に `slowest 30 durations` が出て、その下に試験の行が30行ある | `gh run view <run> --log` を保存し、見出しの行と続く行を数える（Opus） |
| K2: 同じ段の所要時間が、直近の main の同じ段から +30 秒以内 | 両方の段の開始・終了時刻を `gh run view --json jobs` で読む（Opus） |
| K3: 差分は `.github/workflows/test.yml` の1行と台帳・本書類だけ | `gh pr diff` で確認（審査役） |
| K4: 必須チェックがすべて pass | `gh pr checks`（Opus） |

## 7. 外部・過去事例の参照と我々への応用
- pytest 公式の使い方「Profiling test execution duration」（Context7 /pytest-dev/pytest、how-to/usage.rst）が `--durations=N` を遅い試験の特定手段として案内している。数値の事例は不要（表示を足すだけで、効果の主張をしないため）。

## 8. 維持の仕組み
- 一覧は毎回の CI 記録に出る。直す順番を決めるときに、PO 報告の前に Opus が直近の main の記録から読む。
- 一覧から直す試験を選ぶのは別テーマ（PO 判断）。

## 9. 実装カード（クラウドの担当へ渡す）
- 作業場所: `bash scripts/new-worktree.sh release/ci-pytest-durations` で作り、`git -C <wt> merge --no-edit origin/release/ci-pytest-durations` で本書類を取り込む。
- 変更: §3 の1行だけ。
- 確かめ: `git -C <wt> diff` が test.yml の1行だけであること。
- commit して push する。PR は作らない（Opus が作る）。

## 審査（Opus 自己審査・2026-11-26）
- 既存 ADR・試験の決まりとの食い違い: なし（recon.md「既存 ADR の検索結果」）。
- 受け入れ基準はすべて記録や差分で ○× を決められる。
- 判定: APPROVE。未解決: なし。
