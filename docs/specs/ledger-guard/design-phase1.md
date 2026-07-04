# design 第1弾 — commitガード拡張（差分設計）

## 変更点（3つ・原本は artifacts/worktree-only-guard.v2.sh）
1. ルール1の対象ブランチに main を追加
   旧: feature/* fix/* release/* ／ 新: ＋ main（本店では書けない、の実装）
2. ルール1のBash遮断パターンに git commit を追加
   旧: '(git push|gh pr merge)' ／ 新: '(git push|gh pr merge|git commit)'
3. mainブランチ遮断時は専用メッセージ（worktree自動作成を試みない）＋
   ケース3案内文の「git checkout develop」→「git checkout main」修正

## 変えないもの
worktree内の無条件許可／ルール2／WORKTREE_BYPASS=1／イベントログ／自動リカバリー
（feature系のみ）。既存挙動の縮小はしない＝後方互換。

## 適用手順（手作業カード・PR不可領域）
①現行をバックアップ（.bak-日付） ②配布原本をcp ③diffで逐語検収（原本一致）
④bash -n 構文検査 ⑤機能実測: 本店mainでcommit注入→exit=1／git status注入→exit=0／
worktree内でcommit注入→exit=0／案内文にdevelopが0件

## ロールバック
バックアップを書き戻すのみ（1コマンド）。

## 先に言う弊害
本店でのcommitが全面禁止になるため、緊急の管理作業はWORKTREE_BYPASS=1を
明示して行う必要がある（ログに記録が残る）。
