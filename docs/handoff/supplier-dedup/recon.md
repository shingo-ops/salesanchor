# recon — supplier-dedup

**仕事名**: 仕入元マスタ重複防止（LINE解析システム）  
**日付**: 2026-09-19  
**対象ADR**: ADR-085（仕入元プロンプト）、新規ADR起案予定  
**担当**: architect

---

## 既存ADR検索結果

| ADR | 関連性 |
|-----|--------|
| ADR-085-supplier-prompts.md | 仕入元の命名・プロンプト規約。直接の重複防止規約なし |
| ADR-072-tenant-schema-prefix-enforcement.md | テナントスキーマ規約。public.suppliers のスキーマ参照に関連 |
| ADR-090-products-central-unification.md | 商品の共用マスタ統一。仕入元の共用マスタ方針の先行例 |

line_name に関する ADR: **なし**（新規起案が必要）  
dedup/duplicate に関する ADR: 直接仕入元を扱うものは **なし**

---

## file:line 引用表

### INSERT INTO public.suppliers（LINE解析システム — 修正対象）

| 引用先 | 確認内容 |
|---|---|
| backend/app/services/tcg_line_import_svc.py:580 | 自動登録INSERT。line_name=display_name で挿入。ON CONFLICT なし |
| backend/app/routers/tcg_line_import.py:486 | 手動resolve endpoint。line_name=display_name で挿入。ON CONFLICT なし |

### INSERT INTO public.suppliers（管理系 — 影響確認対象）

| 引用先 | 確認内容 |
|---|---|
| backend/app/routers/super_admin_suppliers.py:122 | 管理者画面からの新規作成。line_name あり。ON CONFLICT なし。IntegrityError catch あり |
| backend/app/routers/super_admin_suppliers.py:479 | 管理者CSVインポート。line_name あり。ON CONFLICT なし |

### INSERT INTO suppliers（テナント側 — 影響確認対象）

| 引用先 | 確認内容 |
|---|---|
| backend/app/routers/suppliers.py:266 | テナント新規作成。line_name **なし**（PO確認済み：テナント側はLINE解析に使用しないため正常） |
| backend/app/routers/suppliers.py:472 | テナントCSVインポート。line_name あり。ON CONFLICT なし |

### 仕入元検索（解決ロジック）

| 引用先 | 確認内容 |
|---|---|
| backend/app/services/tcg_line_import_svc.py:547 | 仕入元フェッチ: SELECT supplier_code, line_name FROM public.suppliers WHERE is_active = TRUE AND line_name IS NOT NULL |
| backend/app/services/tcg_line_import_svc.py:236 | マッチング辞書: line_name で完全一致 |
| backend/app/services/tcg_line_import_svc.py:243 | ルックアップ: 見つからなければ unresolved |

### 既存制約・インデックス

| 引用先 | 確認内容 |
|---|---|
| backend/migrations/056_add_suppliers_type_and_promote_public.sql:47 | supplier_code に UNIQUE 制約あり |
| backend/app/routers/suppliers.py | line_name VARCHAR(255) 追加。UNIQUE 制約 **なし**、INDEX **なし** |
| backend/migrations/056_add_suppliers_type_and_promote_public.sql:91-93 | idx_public_suppliers_active, idx_public_suppliers_type, idx_public_suppliers_name のみ |

---

## 根本原因の事実確認

### 重複発生の経路（観測事実）

1. **LINE トーク履歴のアップロード時**（tcg_line_import_svc.py:580）:
   - resolve_suppliers() が line_name で既存仕入元を検索（L547）
   - 見つからない → unresolved リストへ（L243）
   - unresolved → INSERT INTO public.suppliers (name, line_name, ...) VALUES (:name, :line_name, ...) で新規作成（L580）
   - **ON CONFLICT なし** → 同じ line_name が複数回 INSERT される

2. **重複が発生する条件**:
   - 同じ仕入先名で複数回アップロード（Android + PC、または同一プラットフォームで複数回）
   - 前回の INSERT が commit 前に次の resolve が走る（同一トランザクション内でも unresolved → INSERT のループで重複は起きないが、別リクエストでは起きる）

3. **line_name の検索は正しく設計されている**（L547）。問題は INSERT 時に既存 line_name をチェックせず無条件に INSERT する点

### 現在の重複データ（本番DB観測値）

10グループ・21レコードの重複が存在（2026-09-19 時点）。代表例:
- RAITO: 3レコード（messages: 0/6/7件）
- 他9グループ: 各2レコード

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|---|---|---|
| 1 | テナント側 CSV インポート（suppliers.py:472）で line_name 重複は起きうるか | UNIQUE 制約は WHERE tenant_id IS NULL なのでテナント側は対象外。テナント側の line_name 重複は別件 | ✅ 対象外と判断 |
| 2 | super_admin の IntegrityError catch（:122）は line_name 重複を防げるか | catch はあるが UNIQUE 制約がないため line_name 重複では発火しない。supplier_code 重複等の他制約用 | ✅ 防げない |
| 3 | 並行リクエストでの race condition | READ COMMITTED では SELECT → INSERT の間に他トランザクションが INSERT 可能。UNIQUE 制約なしでは防げない | ✅ UNIQUE 制約で解決 |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

### INSERT 箇所の分類

| 箇所 | テーブル | line_name | ON CONFLICT | UNIQUE制約の影響 | 修正要否 |
|------|---------|-----------|-------------|-----------------|---------|
| tcg_line_import_svc.py:580 | public.suppliers | ✅ あり | ❌ なし | ✅ 影響あり | ✅ UPSERT化 |
| tcg_line_import.py:486 | public.suppliers | ✅ あり | ❌ なし | ✅ 影響あり | ✅ UPSERT化 |
| super_admin_suppliers.py:122 | public.suppliers | ✅ あり | ❌ なし | ✅ 影響あり | ✅ UPSERT化 |
| super_admin_suppliers.py:479 | public.suppliers | ✅ あり | ❌ なし | ✅ 影響あり | ✅ UPSERT化 |
| suppliers.py:266 | suppliers (tenant) | ❌ なし | ❌ なし | ❌ 対象外 | ❌ 不要 |
| suppliers.py:472 | suppliers (tenant) | ✅ あり | ❌ なし | ❌ 対象外（tenant_id≠NULL） | ❌ 不要 |
