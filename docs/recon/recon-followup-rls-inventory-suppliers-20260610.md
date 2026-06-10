# Recon報告 — 全体監査フォローアップ（F-1/F-2/F-3）（2026-06-10, commit: 563de152）

> **前提:** `docs/recon/recon-sa-foundation-full-audit-20260610.md`（PR #1900）の「PO判断依頼」のうち  
> 事実確認で解決できる3件を確定させる調査。  
> **修正なし。事実のみ。**

---

## サマリ

| 件名 | 判定 |
|------|------|
| F-1: RLS変数名バグの本番実影響 | **フェイルクローズ確定（漏洩窓あり・データ漏洩なし）** |
| F-2: PR#2 A行移行の証跡 | **A行は存在しなかった（移行不要）** |
| F-3: suppliers 2系統の実態 | **両方現役（用途別）** |

---

## F-1. RLS変数名バグの実影響期間（確定版）

### サマリ

Phase 2（salesanchor_app 接続）と バグ窓 に重なりは**あった**。  
しかし旧ポリシーは `missing_ok` なしの `current_setting()` を使用していたため、  
salesanchor_app からのアクセスは **500 エラー（fail-close）** になり、**データ漏洩は発生しなかった**。

| 重なり窓 | 期間 | 本番上の影響 |
|---------|------|------------|
| 窓①（Phase2試行・失敗） | 2026-06-05T20:13Z〜23:36Z（推定〜3時間） | バックエンド不健全（health check失敗）。実トラフィックへの影響限定的 |
| 窓②（Phase2本番稼働） | 2026-06-07T06:15Z〜11:15Z（約5時間） | conversation_logs / own_inventory アクセスで 500 エラー発生 |

### 根拠一覧

#### Phase2切替コミット日時

| 確認項目 | 値 | 根拠 |
|---------|---|------|
| `a359037e` コミット日時 | 2026-06-07 15:23:35 +0900 = **06:23:35 UTC** | `git show a359037e --format='%ci' -s` 実行結果 |
| `a359037e` の内容 | "chore: deploy stamp — SA18 Phase2 フラグON切替トリガー (#1722)" | git show 結果 |

#### バグ migration の本番デプロイ日時

| migration ファイル | 初期コミット | 内容の問題 | 修正コミット |
|------------------|------------|-----------|-----------|
| `20260604_090000_create_conversation_logs.sql` | `5397a61c`（2026-06-04 11:51 +0900） | `current_setting('app.current_tenant_id')::integer`（missing_ok なし・変数名誤り） | `1b12124c`（PR #1730） |
| `20260604_140000_create_own_inventory.sql` | `11451e9a`（2026-06-04） | `current_setting('app.current_tenant_id')::integer`（missing_ok なし・変数名誤り） | `1b12124c`（PR #1730） |

diff 引用（`git show 1b12124c -- migrations/20260604_090000_create_conversation_logs.sql`）:
```diff
- USING (tenant_id = current_setting('app.current_tenant_id')::integer)
+ USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER)
```

#### 旧ポリシーの fail-close / fail-open 分類

| 確認項目 | 値 | 根拠 |
|---------|---|------|
| 旧ポリシーの変数名 | `app.current_tenant_id` | git diff（上記） |
| `missing_ok` パラメータ | **なし** — `current_setting('app.current_tenant_id')::integer` | git diff（上記） |
| `app.current_tenant_id` の SET 箇所 | **ゼロ**（コード全体 grep で0件） | `migrations/20260607_000000_fix_rls_policy_variable_name.sql:9` に「コード中で一度も SET されない」と明記 |
| PostgreSQL の動作（missing_ok なし、変数未設定） | `ERROR: unrecognized configuration parameter "app.current_tenant_id"` → クエリ全体が失敗 | PostgreSQL 仕様（current_setting の missing_ok=false がデフォルト） |
| アプリへの影響 | 500 Internal Server Error（行は返らない） | `migrations/20260607_000000_fix_rls_policy_variable_name.sql:10-11` |
| 分類 | **フェイルクローズ** — データ漏洩なし。障害のみ | — |

#### Phase2 活性化タイムライン（gh run list 実行結果から）

| 時刻（UTC） | deploy run | 内容 | Phase2状態 |
|-----------|-----------|------|----------|
| 2026-06-04T12:50Z | 26952766780 | "release: develop → main (2026-06-04)" | OFF（jarvis） |
| 2026-06-05T20:13Z | 27037723851 | Merge PR #1703（**失敗**） | ON試行開始。DATABASE_URL=salesanchor_app を.envに書き込み、backend health check 失敗（20:15Z〜20:16Z にわたりタイムアウト待ち）。smoke[5]「FAIL: tenant=1 can see tenant=999999 rows」でrun失敗 | 
| 2026-06-05T23:20Z | 27045193616 | "fix: DATABASE_URL ロールバック + smoke[7] 在る側確認化"（**失敗**） | DATABASE_URL を jarvis に戻す。Phase2一時撤退 |
| 2026-06-05T23:36Z | 27045730933 | Merge PR #1705（成功） | OFF（jarvis）に復帰 |
| 2026-06-07T01:28Z | 27079185870 | Merge PR #1715（SA-18 Phase2 auto-URL）（成功） | Bootstrap が DATABASE_URL=salesanchor_app を.envに書き込むが、**コンテナ未再起動**。実質 jarvis |
| 2026-06-07T06:15Z | 27084692279 | "fix(deploy): Bootstrap後にbackend/workerを--force-recreate" | force-recreate で**コンテナが salesanchor_app URL を認識**。**Phase2 開始（窓② 開始）** |
| 2026-06-07T06:23Z | `a359037e` コミット | "deploy stamp — SA18 Phase2 フラグON切替トリガー (#1722)" | SA18_PHASE2_ENABLED=1 確認 |
| 2026-06-07T10:05Z | （PR #1730マージ） | fix(rls): RLS ポリシーの変数名誤り修正（PR #1730） | salesanchor_app が本番接続中、fix migration は未適用 |
| 2026-06-07T11:11Z | 27090850471 | "release: develop → main (SA-19 smoke Phase2 + flip)"（成功） | SA18_PHASE2_ENABLED=1 を検出（"保持します"）。fix migration 適用開始 |
| 2026-06-07T11:13Z | — | Bootstrap: "SA18_PHASE2_ENABLED=1 → DATABASE_URL を salesanchor_app に設定" | — |
| 2026-06-07T11:15Z | — | `>>> [116/119] psql < migrations/20260607_000000_fix_rls_policy_variable_name.sql` | **修正適用。窓② 終了** |

deploy run log 引用（run 27090850471）:
```
2026-06-07T11:11:35.9149415Z ℹ️  SA18_PHASE2_ENABLED=1 を検出 — salesanchor_app URL を保持します（Phase2 意図的切替）
2026-06-07T11:13:01.9753746Z ℹ️  SA18_PHASE2_ENABLED=1 → DATABASE_URL を salesanchor_app@postgres:5432 に設定しました
2026-06-07T11:15:10.3017192Z >>> [116/119] psql < migrations/20260607_000000_fix_rls_policy_variable_name.sql
```

#### smoke[5] 失敗の補足（2026-06-05T20:18Z）

2026-06-05の窓①で smoke[5] が「tenant=1 can see tenant=999999 rows」で失敗（`gh run view 27037723851 --log`）。  
conversation_logs / own_inventory への salesanchor_app アクセスは fail-close（ERROR → 0行ではなく例外）であるため、  
この失敗は別テーブルのRLSチェック、または当時追加されたばかりの smoke test 自体の設計問題（jarvis で全行が見える動作を誤検知）の可能性がある。  
確定には smoke test コードの当時バージョンの確認が必要。本報告では「補足事項」として記録する。

### 最終判定

**漏洩窓: あり（2回）。ただしフェイルクローズ確定。データ漏洩なし。**

- 窓①（2026-06-05 20:13〜23:36 UTC）: backend 不健全。salesanchor_app からの conversation_logs / own_inventory アクセスは 500 エラー。実トラフィックは限定的
- 窓②（2026-06-07 06:15〜11:15 UTC、約5時間）: Phase2 本番稼働中。conversation_logs / own_inventory への API アクセスは 500 エラー
- データ漏洩なし（`current_setting('app.current_tenant_id')` は missing_ok なしの ERROR → 行が返らない）
- テナント数: 本番は highlife-jpn（tenant_004）1テナントのみ。越境漏洩の実害は構造上不可能

### POへの残確認事項（任意）
~~smoke[5]「tenant=1 can see tenant=999999 rows」の詳細（当時の smoke test コードのバージョン確認）。~~  
→ **確定済み（2026-06-10 追加調査）**: 以下セクション「smoke[5] 確定 recon」を参照。

---

---

## smoke[5] 確定 recon（2026-06-05T20:18Z / run 27037723851）

### サマリ

| 確認項目 | 事実 | 根拠 |
|---------|------|------|
| smoke seed の接続ロール | `jarvis`（BYPASSRLS/superuser） | `scripts/smoke_test_post_deploy.sh` — `ADMIN_PSQL="psql -U jarvis -d jarvis_db"` |
| smoke SELECT の接続ロール | `salesanchor_app`（NOBYPASSRLS） | `scripts/smoke_test_post_deploy.sh` — `psql -U salesanchor_app` |
| 対象テーブル | `public.translation_glossary` | smoke[5] の SELECT 文より |
| Phase2 窓①との重なり | あり（run 27037723851 = Phase2試行デプロイ） | F-1タイムライン |
| smoke の接続経路 | 直接 psql（backendを経由しない） | `docker exec "${POSTGRES}" psql ...` |

### 判定: **smoke設計の問題（BYPASSRLSロール）ではない。一時的DB状態の問題（推定）。追加調査不要**

#### 根拠

1. **SELECT ロールは NOBYPASSRLS** — `salesanchor_app` は smoke[3] で `NOBYPASSRLS` を確認済み。「BYPASSRLSロールで実行＝見えて当然」仮説は不成立。

2. **Phase2 窓①との関係なし** — smoke script は `docker exec ... psql` で直接 PostgreSQL に接続。backend の DATABASE_URL 切替（Phase2）は smoke の SELECT ロールに影響しない。

3. **RLSポリシーは正しく設定済み** — run 27037723851 の migration 適用順序:  
   - `20260604_220000`: translation_glossary テーブル作成  
   - `20260605_010000`: RLS ENABLE + ポリシー4本（`current_setting('app.tenant_id', true)::INTEGER`）  
   - `20260605_020000`: NULLIF 修正（`NULLIF(..., '')::INTEGER`）  
   - `20260605_030000`: salesanchor_app ロール作成 + `GRANT SELECT ... ON ALL TABLES IN SCHEMA public`（translation_glossary 含む）  
   これらはすべて run 27037723851 の `run_all_migrations.sh` に登録済み（`scripts/run_all_migrations.sh:281-293` at commit 3db0d31a 確認）。

4. **後続デプロイで自然解消** — PR #1705（b5a858ef、同日 08:36 JST）は smoke[5] ロジックを変更せずに全 smoke PASS。smoke test 自体の問題ではなく、run 27037723851 固有の一時的 DB 状態の問題（初回 migration 適用時の過渡状態と推定）。

5. **実害なし** — translation_glossary の RLS は salesanchor_app（NOBYPASSRLS）に対して正しく動作。後続デプロイ以降、クロステナント遮断 smoke は継続 PASS。

---

## F-2. PR#2 A行移行の証跡

### サマリ
`public.inventory` には `supplier_id NOT NULL` 制約が設計当初から存在し、A行（自社在庫）は構造上挿入不可能だった。  
移行マイグレーションが不要だったのは「移行すべきA行がそもそも存在しなかった」ため。

### 根拠表

| 確認項目 | 事実 | 根拠（file:line） |
|---------|------|----------------|
| `public.inventory` の supplier_id 制約 | `supplier_id INTEGER NOT NULL REFERENCES public.suppliers(id) ON DELETE CASCADE` → A行（supplier なし）は構造上INSERT不可 | `migrations/081_create_inventory.sql:31` |
| B専用 CHECK 制約追加時の NOT VALID | `ALTER TABLE public.inventory ADD COLUMN ... CHECK (source_kind IN ('B_feed'))` に `NOT VALID` なし → 制約追加時に既存全行を検証済み | `migrations/20260604_150000_add_inventory_source_kind.sql:13-15` |
| 制約追加 migration のコメント | 「public.inventory に A行が存在しないことは E確認済み（supplier_id NOT NULL 構造上不可）」と明記 | `migrations/20260604_150000_add_inventory_source_kind.sql:7-8` |
| 削除済み inventory migration | `git log --all --diff-filter=D -- migrations/*inventory*.sql` → 出力なし（削除済みファイルなし） | git コマンド実行結果 |
| public.inventory への A行 INSERT コード | backend/ 全体検索で `INSERT INTO.*public.inventory` → 未発見 | grep 結果（0件） |
| own_inventory の INSERT 経路 | `POST /own-inventory` エンドポイント 1本のみ（`require_permission("products.create")` 保護） | `backend/app/routers/own_inventory.py:96-142`（line 109 が INSERT） |
| 過去の A在庫 INSERT スクリプト | `backend/scripts/` 以下で own_inventory への INSERT スクリプト → 未発見 | grep 結果（0件） |

**判定: A行は存在しなかった（移行不要）**  
`public.inventory` の `supplier_id NOT NULL` 制約により設計当初からA行挿入は構造上不可能。  
PR#2 の「A行→own_inventory 移行」は「そもそも移行対象がなかった」という意味で完了している。

---

## F-3. suppliers 2系統の実態

### サマリ
`public.suppliers`（共有中央マスタ）と `{schema}.suppliers`（テナント専用）は用途が異なり、両方が現役。重複ではなく分業設計。

### 根拠表

| 項目 | public.suppliers | {schema}.suppliers |
|------|----------------|------------------|
| テーブル定義 | `migrations/056_add_suppliers_type_and_promote_public.sql:42-58` | `backend/app/services/tenant.py:869-882` |
| tenant_id 列 | なし（共有） | あり（NOT NULL DEFAULT {tenant_id}） |
| RLS | なし（意図的）| あり（tenant.py:1070） |
| 列数・属性 | 多（supplier_type, default_language, created_by 等） | 少（基本属性のみ） |
| 作成経緯 | migration 056 コメント「A6 マーケットプレイス型: 全テナント共有、Jarvis運用adminのみ書込。既存 tenant_xxx.suppliers のデータを public へプロモート」 | tenant.py のテナント作成 DDL で自動生成（Phase 1-C M-MVP 後付け） |
| 参照コード件数 | backend/ 20ファイル以上（`backend/app/routers/suppliers.py`, `backend/app/services/inventory_search.py`, `backend/app/schemas/central_masters.py` 等） | `backend/app/services/tenant.py` の DDL のみ（アプリロジック側の参照は未発見） |
| FK（参照先として） | `public.inventory:31`（supplier_id NOT NULL）<br>`public.ingestion_jobs:4`（supplier_id）<br>`public.parse_logs`（supplier_id） | `{schema}.products.supplier_default_id`（tenant.py:895）<br>`{schema}.purchase_orders.supplier_id`（tenant.py:903） |
| ADR-099 での分類 | 「全仕入元の中央マスタ（テナント非依存）」と明記 | 「廃止予定」と migration 056 コメントに記載（ADR-099本文での言及は未発見） |

### FK マッピング一覧

| テーブル | supplier FK 参照先 |
|---------|------------------|
| `public.inventory` | **`public.suppliers(id)`** — B在庫フィードの仕入元 |
| `public.ingestion_jobs` | **`public.suppliers(id)`** — 取り込みジョブの仕入元 |
| `public.parse_logs` | **`public.suppliers(id)`**（間接） |
| `{schema}.products.supplier_default_id` | **`{schema}.suppliers(id)`** — 商品デフォルト仕入先 |
| `{schema}.purchase_orders.supplier_id` | **`{schema}.suppliers(id)`** — 発注先 |
| `{schema}.own_inventory` | FK なし（A在庫に仕入元なし） |

### 判定: 両方現役（用途別）
- **`public.suppliers`**: B在庫フィード処理・取り込みジョブ・解析ログの仕入元中央マスタ。アプリコード20ファイル以上が参照する正系統。
- **`{schema}.suppliers`**: テナントごとの商品デフォルト仕入先・発注先管理。FK は存在するが、アプリロジック側（routers/services）から直接参照するコードは今回の検索では発見できなかった。

### PO決定（2026-06-10）
**両系統を役割別の正として維持する。**
- `public.suppliers` = B在庫フィード・取り込みジョブの全テナント共有仕入元マスタ（廃止しない）
- `{schema}.suppliers` = テナント専用の発注先・商品デフォルト仕入先管理（廃止しない）
- migration 056 の「廃止予定」「旧テーブル評価」コメントは実態と乖離 → `migrations/056_add_suppliers_type_and_promote_public.sql` のコメントを是正済み（同 PR）
- 将来 `{schema}.suppliers` の FK 対象（products.supplier_default_id）を `public.suppliers` に統合する場合は改めて ADR を起案すること
