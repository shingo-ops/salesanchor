# condition-vocab-ssot design (Phase 1: products.condition / products.unit コード除去)

**対象ADR**: ADR-093  
**recon**: docs/handoff/condition-vocab-ssot/recon.md  
**日付**: 2026-06-28  
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

- 該当なし：本変更は `public.products` の残骸列（condition / unit）をアプリコードから除去するだけの内部整理であり、外部ライブラリや他社事例を参照する必要はないと判断。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `p.condition` / `p.unit` のコード参照がゼロになる | `grep -rnE "\bp\.(condition|unit)\b" backend/` → 空 |
| フロントエンドの型エラーがない | `tsc --noEmit` 変更起因エラー（TS2339 等）がゼロ |
| condition/unit 関連テストが全通過 | `pytest backend/tests/test_condition_vocab.py backend/tests/test_super_admin_inbound_api.py` → passed |
| フロントエンドビルドが成功する | CI `frontend-build` ジョブが green |
| 全 CI ゲートが通過する | `gh pr checks 2660` → すべて green |

---

## 本番反映順序

1. 追加移行 + backfill
   - `raw_condition` / 軸列の追加と既存データの用心深い backfill を先に終える。
   - この段階では `condition` 列を残し、読み手は並行運用する。
2. 新キーの作成
   - `uq_inventory_offer_v2` を本番に作成する。
   - 旧キー `uq_inventory_offer_key` はまだ残す。
   - 本番適用前に read-only 衝突チェックで重複 0 を確認する。
3. 新コードのデプロイ
   - 在庫書き込みの UPSERT は `uq_inventory_offer_v2` に一致する式で行う。
   - 読み手 / フィルタは軸優先 + `condition` fallback の並行運用を維持する。
4. 旧キーの削除
   - 新コードが稼働し、実データで新キーが安定していることを確認してから `uq_inventory_offer_key` を落とす。
   - `run_all_migrations.sh` の自動実行からは除外し、手動 GO でのみ適用する。
   - これは新キー作成とは別 GO。
5. `condition` 列の削除
   - 読み手の完全切替・回帰なし・バックアップ手順確認の後にのみ実施する。

## 2b 分割の理由

- 旧キーを落とすと、旧コードの UPSERT が壊れる。
- 先に新コードへ寄せてから旧キーを削除すれば、共存期間を安全に持てる。
- `CREATE UNIQUE INDEX CONCURRENTLY` と `DROP INDEX` を別 migration に分けることで、失敗時の切り戻し理由を明確にする。
