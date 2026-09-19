# recon — 柱1 検査結果の取り違え・マージ経路

> この文書は何か（専門用語なしの1行）:
> 「直したのに古い検査結果が残る」問題が、なぜ起きるかを実物で確かめた記録。

**対象ADR**: ADR-121
**設計**: docs/specs/process-hardening/kgi.md
**親（あるべき姿）**: docs/specs/process-hardening/ideal-state.md

---

## file:line 引用表

| 引用先 | 確認内容 |
|---|---|
| `scripts/gh-pr-merge-safe.sh:41` | マージ前に .pr-number ファイルの存在を要求する |
| `scripts/gh-pr-merge-safe.sh:48` | .pr-number が無い場合はマージを中断する |
| `scripts/gh-pr-merge-safe.sh:92` | not up to date 時の自動追従が実装済み |
| `scripts/gh-pr-merge-safe.sh:120` | 判定待ち時の同一HEAD再マージが実装済み |
| `scripts/register-pr.sh:2` | .pr-number と台帳PR番号列を更新する専用スクリプトが存在する |
| `scripts/register-pr.sh:5` | 目的として安全マージが確実に動く状態にすると明記されている |
| `.github/workflows/process-artifacts-gate.yml:10` | edited を含む発火設定。本文編集でも再走する |
| `.github/workflows/process-artifacts-gate.yml:15` | cancel-in-progress により古い実行が cancelled になる |

---

## 実測した現象（本セッション 2026-07-21〜23）

| 対象SHA | 同名 gate の結果 |
|---|---|
| eaf60f49 | success 03:23 / failure 02:59 / cancelled 02:58 の3件が同一SHAに併存 |
| 11aa179d | success 06:56 / cancelled 06:51 の2件が同一SHAに併存 |

判明した要点: 問題は古いSHAの結果を見ることではなく、同一SHA上に複数の採点が積み重なり古い採点を読むことである。

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|---|---|---|
| 1 | 安全ラッパーが使われていない理由 | 全 worktree に .pr-number が存在しないことを実測 | 解消済み |
| 2 | 机作成時にメモが自動生成されるか | new-worktree.sh に pr-number の記述が無いことを実測 | 解消済み |
| 3 | 柱1と柱4の重複 | kgi.md の柱1と柱4を対照し、同一問題の検査側と経路側と確認 | 解消済み |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- 実測は refs/remotes/origin/main を明示参照して行った（ローカルに同名ブランチが存在し曖昧なため）。
