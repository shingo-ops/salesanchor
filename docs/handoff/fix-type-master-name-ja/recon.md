# Recon: type_master.name_ja 英語値の修正

## 問題
`public.type_master` の `name_ja` カラムに英語値が2件残存。
買取相場ページのタブ表示名がname_jaから取得されるため、英語タブが混在。

## エビデンス
- `backend/migrations/085_create_tcg_type_master.sql`: seed値 `('one_piece', 'ワンピース', ...)`
- `backend/migrations/086_seed_extra_tcg_types.sql`: seed値 `('xross_stars', 'クロススタァ', ...)`
- 本番DB確認（2026-09-25）: id=2 name_ja='One Piece', id=24 name_ja='Xross Stars'
- seed は `ON CONFLICT (code) DO NOTHING` のため、既存行が英語値で登録済みの場合に上書きされなかった

## 対象
| id | code | 現在 | 修正後 | 根拠 |
|---|---|---|---|---|
| 2 | one_piece | One Piece | ワンピース | migration 085 seed定義値 |
| 24 | xross_stars | Xross Stars | クロススタァ | migration 086 seed定義値 |

## ADR
- ADR-156: 分類マスタ統合（type_master）
- ADR-157: 買取相場機能
