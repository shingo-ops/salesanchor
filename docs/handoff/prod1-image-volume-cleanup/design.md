# prod1 Playwright Image Cleanup Design

## 概要

prod1（本番）に置き忘れられた未使用イメージ `mcr.microsoft.com/playwright:v1.61.0-noble` を 1 件だけ named 個別削除で片付ける。
一回限りの手動作業。F2（週次自動お掃除 #2675）とは別物。

## 触るファイル

- `docs/handoff/prod1-image-volume-cleanup/recon.md`
- `docs/handoff/prod1-image-volume-cleanup/design.md`

## 削除するファイル

- なし

## 削除する本番リソース

- `mcr.microsoft.com/playwright:v1.61.0-noble`
- Image ID: `57b65fdc9cea`
- Size: 3.45GB
- `CONTAINERS=0`
- 再 pull 可

## 標準ワークフロー

`recon` → 設計 → dry-run → PO 手書き GO → named 個別削除 → KGI 検証 の順を厳守する。

`recon.md` / `design.md` は `docs/handoff/prod1-image-volume-cleanup/` に配置済み。
危険変更（本番 image 削除）のため CI は GO 記録を要求する。

## 非対象

- volume は一切削除しない
- 本番 DB volume は触らない
- Redis volume は触らない
- 監視系 volume / image は触らない
- astro-webapp 自前イメージは触らない

## KGI（合格条件）

| # | 条件 |
|---|------|
| a | 削除後も現役コンテナ 11 本が全数 Up |
| b | 本番 DB volume / Redis volume が無傷 |
| c | 監視系 volume / image が 1 つも消えていない |
| d | 消えたのは playwright 1 件のみ（実体 36 → 35） |
| e | ディスクが約 3.45GB 減少 |

## 実行メモ

- dry-run は削除候補の表示のみ
- 実削除は `docker image rm mcr.microsoft.com/playwright:v1.61.0-noble` のような named 個別コマンドに限定する
- `rmi --force`、`volume rm`、`prune`、`system prune` は使わない

## GO 記録

PO 手書き欄。ここは空のままにしておく。

## 11. 結果

dry-run 時点で playwright (57b65fdc9cea) は既にデプロイ付随処理で削除済み。当方の rmi 実行は不要だった。
KGI a〜e すべて実データで○（現役11・本番DB/Redis無傷・監視系全種残存・playwright消失・ディスク約3GB減）。
無差別pruneの巻き込みなし（監視系全種残存・volume数171維持で確認）。記録（recon/design/結果）を資産として main に取り込む。
