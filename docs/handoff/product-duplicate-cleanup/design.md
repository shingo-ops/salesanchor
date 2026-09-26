# design.md — product-duplicate-cleanup

参照: [recon.md](./recon.md) / ADR-1001（Phase 2a）/ ADR-155（マージ済み）

---

## 目的 (KGI)

`public.products` に混入した重複レコード 203 件を削除し、
FK 参照 5,595 件を正しい keep_id へ付け替えることで、
TCG 商材マスタを単一レコード状態に戻す。

---

## 対象と対象外

| 区分 | 条件 | 理由 |
|------|------|------|
| **削除対象** | `product_code ~ '^PM[0-9]'` かつ同名の非 PM0### レコードが存在する | unify migration で追加されたコピー側 |
| **保持（PM0###）** | `product_code ~ '^PM[0-9]'` だが同名の非 PM0### が存在しない（94 件） | 新規商品として正規に追加されたもの |
| **保持（非 PM0###）** | `S8a` `SS9` 等の旧コード体系、または code なし | 元から存在する正規レコード |
| **対象外** | WS バリアント、同名でも異なる商品実態のもの | name 一致 + 旧コード体系の条件で除外される |

---

## 変更箇所

| ファイル | 変更内容 |
|---------|---------|
| `scripts/one-time/cleanup-product-duplicates.sql` | 新規作成（今回の成果物） |
| `docs/handoff/product-duplicate-cleanup/recon.md` | 新規作成（今回の成果物） |
| `docs/handoff/product-duplicate-cleanup/design.md` | 新規作成（今回の成果物） |
| `public.products`（DB） | 203 行 DELETE（アプリコードの変更なし） |
| `tenant_004.analysis_results`（DB） | ~5,032 行 UPDATE（product_id 付け替え） |
| `tenant_004.product_search_keywords`（DB） | ~430 行 UPDATE（product_id 付け替え） |
| `tenant_004.product_exclude_keywords`（DB） | ~133 行 UPDATE（product_id 付け替え） |

---

## 実装方式

**一回限り SQL スクリプトを SSH 越しに psql で実行する。**

migration ファイルとして `migrations/` に置かない理由:
- CI check 7（`migration-guard.yml`）はマイグレーションを自動本番適用する経路を想定しており、
  一回限りのクリーンアップを通常の migration フローに乗せると
  再実行リスクと review コストが増大する。
- スクリプトは冪等（2 回目実行時は mapping が空のため全操作が 0 行）。

---

## 検証基準

| 基準 | 検証方法 | 合格条件 |
|------|---------|---------|
| 重複ゼロ | Step 4-a: name ごとの dup_count クエリ | 結果 0 行 |
| 総レコード数 | Step 4-b: `COUNT(*) FROM public.products` | 削除前 - 203 = 削除後の数値と一致 |
| 特定商品 1 件確認 | Step 4-c: `name LIKE '%ムニキスゼロ%'` | 厳密に 1 行 |
| FK 整合性 | Step 0 のカウントと Step 2 の GET DIAGNOSTICS 行数が一致 | ずれ 0 件 |
| NULL keep_id なし | Step 1 の安全チェック DO $$ ブロック | EXCEPTION が発生しないこと |

---

## リスクと対処

| リスク | 発生条件 | 対処 |
|--------|---------|------|
| FK 制約違反 | remap 前に DELETE が走った場合 | スクリプト内で Step 2（remap）→ Step 3（delete）の順序を固定 |
| keep_id が NULL | 名前一致する旧コードレコードが存在しない | Step 1 安全チェックで EXCEPTION → 自動 ROLLBACK |
| キーワード重複 | remap 先 keep_id に既に同一キーワードがある | 調査済み: 競合 0 件。万一 UNIQUE 違反が出れば ROLLBACK で安全終了 |
| 誤対象削除 | 条件が広すぎる場合 | Step 0 ドライランで 203 件を目視確認してから BEGIN |
| 実行中のロック | 本番トラフィック下で長時間ロック | 低トラフィック時間帯（JST 深夜）に実行。mapping は TEMP TABLE なので他セッションに影響しない |

---

## 外部・過去事例の参照と我々への応用

自プロジェクト内の過去事例のみ参照。

- **ADR-1001 Phase 2a**（`migrations/unify_tcg_products_to_public.sql`、PR #3503）が本問題の直接原因。
  ON CONFLICT の設計が product_code 一致前提であったため、コード体系が異なる既存レコードと
  衝突できなかった。
- **応用**: 今後同様の cross-schema コピー migration では、product_code だけでなく `name` 正規化
  マッチングを migration 内に組み込むか、事前に重複検知クエリを dry-run する工程を必須化する。

---

## 維持の仕組み（守り手）

**`migration-guard.yml` check 7**（`scripts/` 内の `one-time/` ディレクトリが
`migrations/` に混入しないことを CI で確認）が将来の同種問題を防ぐ。

本スクリプトを `migrations/` 外の `scripts/one-time/` に配置したことで、
guard は通過し、かつ誤って自動適用される経路が存在しない。
