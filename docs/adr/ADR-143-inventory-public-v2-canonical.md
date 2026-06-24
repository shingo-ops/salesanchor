# ADR-143: public.inventory(B在庫) は v2形を正典とし、repoフル実行も末尾収束で v2 に到達する

- Status: Accepted
- Date: 2026-06-24
- Related: recon-D1-inventory-drift-formalize.md / design-D1-inventory-drift-formalize-v2.md / ADR-093(offer_type/ship_timing) / migrations 081,20260602_180000,20260623_020000/030000/050000,20260624_140000

## Context
public.inventory(全テナント共有・RLS無効・B在庫) は本番で v2形（condition列なし・
uq_inventory_offer_key なし・uq_inventory_offer_v2 のみ・22列・92件）に手当て済み。
一方 repo の migration をフル実行すると旧形（condition列あり・uq_inventory_offer_key あり）に
到達し、設計図と実物がズレている（drift）。放置すると新基盤を立てた際に旧形で在庫テーブルが
生成される。

run_all_migrations.sh は記載順に実行される（タイムスタンプ順ではない）。実行順上、
uq_inventory_offer_key を作成する 20260602_180000 は L221 にあり、これを削除する
20260623_030000(HELD,L176) / condition を削除する 20260623_050000(HELD,L178) より後ろにある。
したがって HELD の封印解除では収束せず、むしろ白紙DBで「condition削除後にcondition参照INDEXを
作成」してエラー停止する。uq_inventory_offer_key の作成は 180000 の1か所、削除は 030000 の1か所
のみで、L221 以降に condition へ触れる在庫migrationは無い（capture-3 で確認）。

## Decision
- 適用済みmigration（081 等）は改変しない（案ア）。
- 全在庫migration完了後の**末尾**に冪等な収束migration
  `migrations/20260624_140000_converge_inventory_v2.sql` を1本追加し、
  `DROP INDEX IF EXISTS uq_inventory_offer_key` と
  `ALTER TABLE public.inventory DROP COLUMN IF EXISTS condition` を実行する。
- 既存 HELD（030000/050000）は本番手動GO用の履歴として温存し、run_all からは引き続き未実行とする。
- migration-guard は新規追加ファイルのみ判定するため、未使用タイムスタンプ採用で衝突なし
  （リネーム不要）。

## Consequences
- フレッシュ環境のフル実行が本番と同一の v2形（22列・condition無し・offer_key無し・v2有り）に
  収束する。
- 本番は既に v2 のため収束migrationは no-op（IF EXISTS）。デプロイ毎に再実行されても無害。
- 列のordinal順は追加履歴差により本番と異なり得るが、列集合・型・制約・インデックスは一致する
  （論理スキーマ等価）。
