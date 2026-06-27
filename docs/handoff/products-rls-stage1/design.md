# 段階1 設計 — public.products 書き込みパスへの operator context 付与

**対象ADR**: ADR-145
**recon**: docs/handoff/products-rls-stage1/recon.md
**日付**: 2026-06-26
**担当**: Planner / CC

---

## 外部・過去事例の参照と我々への応用

- **前例 1（同リポジトリ）**: `public.translation_glossary` FORCE-RLS（migration `20260605_010000_rls_translation_glossary.sql`）。
  `app.is_operator = 'true'` セッション変数で共有行書き込みを制御するパターンを確立済み。
  我々への応用: `public.products` でも同一変数・同一 `set_operator_context` / `reset_operator_context` 関数を再利用する。
  段階1では is_operator の設定漏れ経路（W-1/W-3）を塞ぐ。
- **前例 2（PostgreSQL 公式）**: `FORCE ROW LEVEL SECURITY` は `rolbypassrls=t` 権限をも上書きする仕様。
  `jarvis` ロール（`bypassrls=t`）に対しても有効であることを translation_glossary の運用実績で確認済み（recon RL-1）。

---

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| `apply_product_candidates` が `set_operator_context` → try → `reset_operator_context`(finally) で囲まれている | `git show HEAD -- backend/app/routers/super_admin_inbound.py` で構造確認 |
| `approve_review` が同様の対称ラップになっている | `git show HEAD -- backend/app/routers/parse_review.py` で構造確認 |
| INSERT/UPDATE の SQL 文字列・`db.commit()` 位置が変更前と同一 | `git diff HEAD^ HEAD -- backend/app/routers/super_admin_inbound.py backend/app/routers/parse_review.py` で差分確認 |
| `inventory_movements.py` が変更されていない | PR #2602 の変更ファイル 2 件のみを `gh pr view 2602 --json files` で確認 |
| `purchase_orders.py` が変更されていない | 同上 |
| `dependencies.py` が変更されていない | 同上 |
| RLS が付与されていない（段階2対象）ため本番挙動が変わらない | `psql -c "SELECT relrowsecurity FROM pg_class WHERE relname='products' AND relnamespace='public'::regnamespace"` → `f` のまま |
| pytest が通過する | CI `Backend Tests (pytest-run-internal)` 緑 |

---

## 変更方針

### 対象 2 ファイルの変更概要

**W-1: `backend/app/routers/super_admin_inbound.py`**
- `apply_product_candidates` に `set_operator_context(db)` → `try` → 既存処理（INSERT + `db.commit()` + return） → `finally: reset_operator_context(db)` を追加
- SQL 文字列・`db.commit()` 位置は変更なし

**W-3: `backend/app/routers/parse_review.py`**
- `approve_review` に `set_operator_context(db)` → `try` → 既存処理（SELECT FOR UPDATE + apply_inbound_items + UPDATE + `db.commit()` + return） → `finally: reset_operator_context(db)` を追加
- SQL 文字列・`db.commit()` 位置は変更なし

### 触らない範囲

| ファイル | 理由 |
|---|---|
| `backend/app/services/inventory_movements.py` | 同一 `db` セッションで呼び出されるため、W-3 の operator context が自動伝播。変更不要。 |
| `backend/app/routers/purchase_orders.py` | W-2 は `tenant_NNN.products` に解決（recon RL-6）。`public.products` を触らないため対象外。 |
| `backend/app/auth/dependencies.py` | `set_operator_context` / `reset_operator_context` は既実装済み。変更不要。 |

---

## 段階構成

| 段階 | 内容 | 本番挙動変化 | 本PR |
|---|---|---|---|
| 段階1（本PR #2602） | W-1/W-3 に operator context ラップを追加 | **なし**（RLS 未有効化） | ✅ |
| 段階2（別PR・PO明示GO必須） | `public.products` に FORCE-RLS + 4ポリシー追加 | あり（select/insert/update/delete 制御開始） | — |

段階2 は ADR-145 §段階構成で定義する。本 PR（段階1）は段階2 の前提条件であり、段階2 なしでも本番への悪影響はない。

---

## 弊害・トレードオフ

- `set_operator_context` / `reset_operator_context` が DB セッションへの追加 `SET` 文を発行するが、通常運用では無視できるオーバーヘッド
- 段階1 単独では is_operator 設定がランタイムで呼ばれるだけ（RLS ポリシーが存在しないため実際の制御は発生しない）

---

## 継続

- 段階2 PR: `public.products` FORCE-RLS + 4ポリシー（translation_glossary パターン移植）。別セッション・別 PR・PO 明示 GO 必須。
- ADR-145 §段階構成で段階2 の recon→設計→dry-run 手順を定義する。
