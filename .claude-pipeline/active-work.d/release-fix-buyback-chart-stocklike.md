# release/fix-buyback-chart-stocklike

**Status**: IN_PROGRESS
**Branch**: release/fix-buyback-chart-stocklike
**Created**: 2026-09-22

## KGI
買取価格チャートが株チャートと同様に動作する（時系列データ蓄積・昇順表示・全グレード表示）

## 変更内容
1. 常にprice_logをINSERT（diff-onlyガード削除）
2. historyエンドポイントのORDER BY を ASC に変更
3. フロントエンドにAM・Cグレードを追加
