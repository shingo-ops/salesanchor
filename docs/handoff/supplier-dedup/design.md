# Phase 3 設計 — supplier-dedup

**対象ADR**: 新規ADR起案予定（line_name UNIQUE 制約）  
**recon**: `docs/handoff/supplier-dedup/recon.md`  
**日付**: 2026-09-19  
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 該当なし：PostgreSQL の UPSERT（`INSERT ... ON CONFLICT ... DO UPDATE ... RETURNING id`）は標準機能であり、本プロジェクト内の他テーブル（`supplier_aliases` 等）で同パターンの実績がある。外部事例の参照は不要と判断

---

## 受け入れ基準

| # | 基準 | 検証方法 |
|---|------|---------|
| 1 | 既存の重複データ10グループが解消されている（kept=1、他=is_active=FALSE） | `SELECT line_name, COUNT(*) FROM public.suppliers WHERE is_active = TRUE AND tenant_id IS NULL GROUP BY line_name HAVING COUNT(*) > 1` → 0行 |
| 2 | 重複の FK（supplier_channels, source_messages）が kept ID に再割当て済み | `SELECT COUNT(*) FROM source_messages WHERE supplier_id IN (deactivated_ids)` → 0 |
| 3 | 同じ line_name で2回 INSERT しても IntegrityError にならず既存 ID が返る | テスト実装時に確認（UPSERT パターンの検証） |
| 4 | 並行リクエストで同じ line_name を INSERT しても重複行が作られない | UNIQUE 制約による DB 保証（テストは SAVEPOINT + UPSERT のリトライで検証） |
| 5 | line_name が NULL の仕入元は UNIQUE 制約の対象外 | `INSERT INTO public.suppliers (name, supplier_type, is_active) VALUES ('test', 'corporate', TRUE)` が複数回成功する |
| 6 | テナント側仕入元（tenant_id IS NOT NULL）は UNIQUE 制約の対象外 | テナント側 INSERT が制約エラーなく動作する |
| 7 | LINE インポートで unresolved → 自動登録 → 再アップロードで同じ名前が resolved に解決される | 手動テスト: 同一トーク履歴を2回アップロードし、2回目で supplier_id が1回目と同じ |

---

## 技術 How・KPI

### KPI
- 重複仕入元レコード数: **10グループ21件 → 0件**
- LINE インポート後の重複発生: **ゼロ**（UNIQUE 制約で DB レベル保証）

### 技術選択

**1. 部分一意インデックス（Partial UNIQUE Index）**

```sql
CREATE UNIQUE INDEX idx_suppliers_line_name_active_unique
ON public.suppliers (line_name)
WHERE line_name IS NOT NULL AND is_active = TRUE AND tenant_id IS NULL;
```

理由:
- line_name IS NOT NULL: NULL の仕入元（テナント画面からの登録等）は制約対象外
- is_active = TRUE: 論理削除済みレコードは制約対象外（重複解消時に is_active=FALSE にした旧レコードがブロックしない）
- tenant_id IS NULL: テナント固有の仕入元は制約対象外（共用マスタのみ保護）

**2. UPSERT パターン**

```sql
INSERT INTO public.suppliers (name, line_name, supplier_type, is_active)
VALUES (:name, :line_name, 'corporate', TRUE)
ON CONFLICT (line_name) WHERE line_name IS NOT NULL AND is_active = TRUE AND tenant_id IS NULL
DO UPDATE SET line_name = EXCLUDED.line_name
RETURNING id
```

理由:
- DO UPDATE SET line_name = EXCLUDED.line_name: 実質的に何も変えないが、RETURNING id で既存レコードの ID を取得できる
- DO NOTHING は RETURNING が空を返すため不採用（呼び出し元が ID を必要とする）
- エラーで停止しないため、システムの可用性を維持

**3. データクリーンアップ（手動 SQL）**

- 各重複グループで最も参照（channels + messages）の多い ID を kept とする
- 他の ID の FK を kept ID に再割当て → is_active=FALSE に変更
- DELETE は行わない（監査証跡の保全）

---

## 弊害・トレードオフ

| リスク | 影響 | 対策 |
|--------|------|------|
| UPSERT の DO UPDATE で意図しないカラム更新 | line_name を同値で上書きするだけなので実害なし | SET 対象を line_name のみに限定 |
| 並行トランザクションで UNIQUE 違反の IntegrityError | UPSERT なら DB が自動で ON CONFLICT 分岐するため発生しない | UPSERT パターンの徹底 |
| テナント側 INSERT で制約に引っかかる | 部分インデックスが tenant_id IS NULL 条件付きのため、テナント側は影響なし | WHERE 条件で保護済み |
| クリーンアップ SQL で FK 再割当て漏れ | deactivated ID を参照する行が残る | クリーンアップ後に残件チェッククエリを実行（受入基準 #2） |
| supplier_code の重複 | kept ID の supplier_code は変更しない。deactivated ID の supplier_code は is_active=FALSE で UNIQUE 制約対象外 | supplier_code の UNIQUE 制約は部分インデックスではないため、deactivated 側の supplier_code を NULL に変更 |

---

## 計画票

| ステップ | 内容 | 担当 | 前提 |
|---------|------|------|------|
| 1 | recon.md + design.md 作成・PO レビュー | Planner | — |
| 2 | クリーンアップ SQL 作成（FK再割当て + deactivate） | Planner | PO 承認 |
| 3 | マイグレーション SQL 作成（部分 UNIQUE インデックス） | Generator | 設計承認 |
| 4 | UPSERT 化（4箇所のコード変更） | Generator | 設計承認 |
| 5 | テスト作成（UPSERT + 重複防止） | Generator | ステップ4 |
| 6 | クリーンアップ SQL の本番実行 | PO（SSH手動） | PO GO |
| 7 | マイグレーション + コード変更のデプロイ | CI/CD | PO GO + CI 緑 |
| 8 | 本番検証（受入基準 #1〜#7） | Evaluator | デプロイ完了 |

---

## 変更対象ファイル

### 触るファイル

| ファイル | 変更内容 |
|---------|---------|
| backend/app/services/tcg_line_import_svc.py | L580: INSERT → UPSERT |
| backend/app/routers/tcg_line_import.py | L486: INSERT → UPSERT |
| backend/app/routers/super_admin_suppliers.py | L122, L479: INSERT → UPSERT |
| backend/migrations/supplier_line_name_unique.sql | 新規: 部分 UNIQUE インデックス |
| backend/tests/test_suppliers_crud.py | UPSERT テスト追加 |
| docs/handoff/supplier-dedup/recon.md | 新規: 調査結果 |
| docs/handoff/supplier-dedup/design.md | 新規: 設計書（本ファイル） |

### 触らないファイル

| ファイル | 理由 |
|---------|------|
| backend/app/routers/suppliers.py | テナント側 INSERT。tenant_id IS NOT NULL のため UNIQUE 制約対象外 |
| フロントエンド全般 | バックエンドのみの変更 |

---

## 継続

### 完了後の監視
- デプロイ後1週間、LINE インポートのたびに重複チェッククエリを実行
- 結果が0行であることを確認

### 守り手
- backend/migrations/supplier_line_name_unique.sql — 部分 UNIQUE インデックスが DB レベルで重複を防止
- UPSERT パターンがコードレベルで IntegrityError を回避

## 維持の仕組み

守り手: `migrations/20260920_020000_supplier_line_name_unique.sql`（部分 UNIQUE インデックス）、UPSERT パターン（4箇所のコード変更）

### 次フェーズへの引き継ぎ
- テナント側仕入元の line_name 重複防止は別件（現時点では問題なし）
- supplier_code の欠番（SERIAL 特性）は運用上問題なし。連番リセットは不要
