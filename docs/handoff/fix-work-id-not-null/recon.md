# recon: fix-work-id-not-null

## 調査日: 2026-09-19

## 現状
- `public.products` 全1,627件中7件の `work_id` (INTEGER) が NULL
- 対象: QAテスト商品5件 (id: 127269-127273) + LORCANA本番商品2件 (id: 440585-440586)
- 全7件に `work_id_old_uuid` が存在し、既存商品の同UUID行から INTEGER 値を一意に特定済み
- マイグレーション `migrations/20260916_130000_work_id_not_null.sql` が毎回失敗（未適用）

## UUID→INTEGER 対応（本番DB実測）
| work_id_old_uuid | work_id | シリーズ | 既存同UUID商品数 |
|------------------|---------|---------|----------------|
| 2fe437c0-... | 1 | Pokemon | 218件 |
| c6acce0e-... | 2 | One Piece | 33件 |
| 1129cb04-... | 5 | Yu-Gi-Oh | 3件 |
| 1f8c5b4b-... | 23 | LORCANA | 12件 |

## ADR調査
- ADR-1002: product ID type unification (UUID→INTEGER)
- ADR-155: 共用マスタ migration データ操作禁止 — 本修正は既存未適用ファイルの修正であり新規ファイル追加ではないためチェック7対象外

## 設計参照
設計: docs/handoff/fix-work-id-not-null/design.md
