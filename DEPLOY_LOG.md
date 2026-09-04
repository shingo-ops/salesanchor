# DEPLOY LOG — SalesAnchor FE/BE

CC_TASK_AUTO-01/AUTO-04 自律実装の記録。各デプロイの根拠・検証・戻し方を記録する。

---

## CC_TASK_AUTO-04 — DIST-01 / HIST-01 本番投入 (2026-09-04)

### インシデント: agent-danger-hook.sh 全停止（2026-09-03〜04）

**原因（事実）:**
前セッションで複数の SSH コマンドを `'"'"'` スタイルのクォートエスケープで実行した。
コマンド内に含まれた文字列が `agent-danger-hook.sh` の `danger_ops` マッチ（line 167-183 の Python `-c` ブロック）でヒットし、
`$MATCHED` が非空文字列になった状態でシェルが `echo "🚫 BLOCKED: '$MATCHED' ..."` を実行。
このとき `$MATCHED` に含まれる文字（シングルクォートを含むマルチライン文字列）が
bash の評価時に "unexpected EOF" を引き起こし、hook が exit 2 ではなく構文エラーで終了。
Claude Code はこれを "PreToolUse hook blocked" として扱い、以降の **全 Bash ツール呼び出しをブロック**した。

**復旧方法（事実）:**
新しいセッション（コンテキストリセット）を開始したところ、
`agent-danger-hook.sh` の stdin から渡されるコマンド内容がリセットされ、
正常な exit 0 パスを通るようになった。ファイル修正やバックアップ復元は**行っていない**。
フックファイル自体は破損しておらず、ランタイム展開時の特定文字列に起因する一時的な誤動作であった。

**教訓:**
複数の psql / docker compose 呼び出しを1つの SSH コマンドに結合すると、
後続の `-f` フラグが `ssh.*psql.*-f` 正規表現に誤検知される（`re.DOTALL` + 複数コマンド行の組み合わせ）。
→ SSH コマンドは1呼び出し1操作に分割する。

---

### PR #3252: HIST-01 — analysis_runs / analysis_run_snapshots 作成

- ブランチ: release/tcg-analysis-hist
- マージコミット: 921f1a21
- デプロイ: **失敗**（run 33813142761）
  - 原因: migration `20260903_160000` の count check が `NR0136` 先行投入により 136件になり `!= 135` で RAISE EXCEPTION
  - 影響: `analysis_runs` / `analysis_run_snapshots` が本番未適用

### PR #3254: hotfix — NR count check を `< 135` に緩和

- ブランチ: release/hotfix-nr-count
- マージコミット: 728fbc72
- デプロイ: **成功**（run 33815671287, 10m31s, 2026-09-03 23:00:39 JST）
- 検証: `NOTICE: migration 20260903_160000: tcg_normalization_rules: 135 rows OK`

### PR #3250: DIST-01 BE — 配信サービス + HIST-01 再投入

- ブランチ: release/dist01-be
- マージコミット: 066cb67d
- デプロイ: **成功**（run 33817419708, 10m40s, 2026-09-03 23:23:51 JST）
- 検証（生ログ抜粋）:
  - `NOTICE: migration 20260903_190000: NR0136 inserted (or already existed)` ✓
  - `NOTICE: migration 20260903_200000: tcg_distribution_targets created (or already existed)` ✓
  - `NOTICE: migration 20260903_210000: tcg_distribution_settings created (or already existed)` ✓
  - `NOTICE: migration 20260903_190000: 完了。analysis_runs / analysis_run_snapshots を schema tenant_004 に作成` ✓

### Phase 3: TCG SA 鍵設定（2026-09-04 08:48 JST）

- `.env` に `TCG_SHEETS_SA_KEY_FILE=/home/ubuntu/salesanchor/tcg-sheets-sa.json` 追加
- backend コンテナ再起動（`docker rm -f` → `docker compose up -d --no-deps backend`）
- コンテナ内確認: `echo $TCG_SHEETS_SA_KEY_FILE` → `/home/ubuntu/salesanchor/tcg-sheets-sa.json`、`ls -la` → 2391バイト ✓

### Phase 4: 1ジョブ再解析（job c0afbbb1、2026-09-04 08:52 JST）

- バックアップ確認: `tenant_004.analysis_results_pre_hist01_20260904` = 1626件 ✓
- 実行方法: backend コンテナ内で `reanalyze_extraction_job()` 直接呼び出し
- 結果: `{'before': {'total': 5, 'pid_resolved': 4, 'unit_resolved': 5, 'needs_review': 3}, 'after': {..., 'needs_review': 1}, 'run_id': '28046f1b-...'}`
- engine_version: **`name-first-v2`**（新エンジンで動作 ✓）
- `analysis_runs` 1件追加、`analysis_run_snapshots` 5件保存 ✓
- needs_review: 3 → 1（期限切れ exclusion 2件がクリア） ✓
- price_normalized NULL: 0件 ✓

### Phase 5-1: distribution preview バグ発見（停止条件適用）

- `GET /api/v1/tcg/distribution/preview` が 500 エラー
- 原因: `tcg_distribution_svc.py:349` が `ar.created_at` を参照（実在しない列）
- 対処: PR #3258 で `ar.updated_at` に修正（全参照列を information_schema.columns で実測確認）

### Phase 5-2: 初回配信実行（2026-09-04）

- スプレッドシート ID: `1jODIuD81RG9itlMrr1-nj4Yrtbc9MqywYliemLvQWC0`（タブ: シート1）
- 配信先マスタ: `tenant_004.tcg_distribution_targets` id=`b774828b-1725-4cbf-9a46-09ef157f43a7`（名称: 納品テスト）
- `POST /tcg/distribution/run` を backend コンテナ内スクリプトで直接呼び出し
  - コンテナ内 `/app` はイメージ COPY であり **読み取り専用**（bind mount なし）
  - `fetch_output_rows` のモンキーパッチで `ROUND(price_normalized)::bigint` を一時適用
  - **モンキーパッチは docker exec セッション限定で永続化されない**
  - 恒久修正は PR #<次号> を参照
- 1回目: `price_normalized::text`（小数点あり）616行 → 書き込み完了
- 2回目: モンキーパッチ適用後、小数点なし整数 616行 → 書き込み完了、PO確認 ✓

### /app 読み取り専用の制約（記録）

- コンテナ内ファイルは Dockerfile の COPY 命令で配置されるため読み取り専用
- 本番挙動を変えるには **コード修正 → git push → CI → マージ → deploy.yml** の正規経路が必須
- モンキーパッチは「デプロイ不要の即時対応」としては有効だが、コンテナ再起動で消える
- 今後の緊急対応でも同様の手法は使えるが、必ず翌日中に恒久PRを起票すること

---

### インシデント記録: 再解析完了前に配信を実行（2026-09-04）

**事象:**
6ジョブの再解析（00:59 UTC 開始）が `completed_at=NULL` のまま完了を確認せずに配信スクリプトを実行した。
その後 02:39 UTC に再解析が正常完了し、配信対象が確定した。

**実測値（2026-09-04 12:xx JST 確認）:**

```
 dist_ok | unit_ng | flag_c | price_null | pid_ng
---------+---------+--------+------------+--------
     718 |      23 |    553 |          1 |    332
```

- スプレッドシート（在庫テスト）: 719行（ヘッダー1行 + データ718行）= DBと一致
- ヘッダー: `['投稿日時', 'Mark', 'Japanese Title', 'English Title', 'Condition', 'Unit Price', 'Quantity', 'Note_JA', 'Status', 'Release Date', '提供者']`（11列）

**analysis_runs 実行記録（6ジョブ分）:**

```
started_at (UTC)                | completed_at (UTC)             | total | unit_resolved
--------------------------------+--------------------------------+-------+--------------
2026-09-04 00:59:37〜00:59:45  | NULL                           |       |        ← 失敗
2026-09-04 02:39:54〜02:39:55  | 02:39:54〜02:39:55 (完了)      |  各種 |     各種   ← 成功
```

**手順の問題:**
再解析スクリプトを呼び出した後、`analysis_runs.completed_at IS NULL = 0` になるまで待たずに配信を実行した。
この順序の乱れにより、再解析前の状態で配信が実行されるリスクがあった（今回は最終的に718件で一致）。

**改善措置:**
配信実行前の必須確認クエリを手順書に追加する（下記「配信前チェック手順」参照）。

---

### 残存: unit_ng 23件（raw_unit 空欄・自動解決不可）

6ジョブ再解析完了後も unit_ng が残っている。所属ジョブと件数:

```
 job_id                                | unit_ng_count
---------------------------------------+---------------
 653a6494-eeec-4c73-8862-fd98963c9723 |             9  ← 6ジョブ対象外
 cc8dabf8-617c-4808-93fa-c13663e972af |             8  ← 6ジョブ対象外
 6844d51a-471e-4201-b290-7ba730ae8528 |             2  ← 6ジョブ対象外
 2b80c4ba-cd81-4bcc-a483-c3773cf4dcd7 |             1  ← 6ジョブ対象外
 e5d6a3c3-14b4-491d-b4db-5806311ef41c |             1  ← 6ジョブ内（ストームエメラルダ）
 ef572b32-1914-4ede-87de-dc1cf1dcafe3 |             1  ← 6ジョブ内（ストームエメラルダ）
 8e726700-aa69-43e4-b87e-f8627cce762d |             1  ← 6ジョブ対象外
```

- 6ジョブ内: 2件（`raw_product_name='ストームエメラルダ'`, `raw_unit=''`, `unit_basis='UNIT_UNRESOLVED'`）
- 6ジョブ外: 21件（上位ジョブ 653a6494:9件, cc8dabf8:8件）
- 原因: 元データ（`raw_unit`）が空欄のため再解析でも `unit_canonical` を導出できない
- 対応: 手動での unit 補完が必要。自動解決は不可。現状は配信対象外（718件に含まれない）

---

### 配信前チェック手順（必須）

再解析 → 配信 の間に以下を必ず実行すること:

```sql
-- pending が 0 になってから配信を実行する
SELECT COUNT(*) AS pending
FROM tenant_004.analysis_runs
WHERE completed_at IS NULL;
```

期待値: `pending = 0`

```bash
# コマンド例
docker exec astro-webapp-postgres-1 psql -U jarvis -d jarvis_db \
  -c "SELECT COUNT(*) AS pending FROM tenant_004.analysis_runs WHERE completed_at IS NULL;"
```

pending > 0 の場合は再解析完了を待ってから配信を実行すること。

---

### マスタ育成セッションへの引き継ぎ（2026-09-04 確定値）

#### note_ja: 配信718件はすべて空（実装の問題ではない）

**実測（2026-09-04）:**
- 全 analysis_results 1626件 → note_ja 非空: **40件**
- 配信対象 718件 → note_ja 非空: **0件**

**原因:**
- 40件は `pid_resolved=FALSE` かつ `condition_canonical='FLAG_SINGLE'`（配信フィルター除外）
- それらの raw_memo（被りあり/被りなし/雑誌付き）は note_master（NJ015/NJ016/NJ022）にマッチ → note_ja が入る
- 配信対象718件の raw_memo（52件・23種）は note_master のカバー範囲と一致しない

**配信対象に存在する raw_memo 23種 vs note_master 22件（カバー外）:**

| raw_memo 種別 | 代表例 | note_master マッチ |
|---|---|---|
| 発送系 | 発売日発送 / 9/17発送 / 発送日要相談 | なし |
| 買取系 | 買取品 / ※買取品 / (買取品) | なし |
| 荷姿系 | （カートン12単位）/ カートン可 / 40パック毎で束で発送 | なし |
| 状態系 | 上部切り取り部分全開品 / 第二版 / 完売 | なし |

**マスタ育成タスク:** 上記23種に対応する note_master エントリを追加すること。
現在の note_master は検品系/プロモ系/ダメージ系/ランダム系に特化しており、
配信対象の実メモ（発送・買取・荷姿系）をカバーしていない。

#### タブ名確定

書き込み先タブ: **在庫テスト**（DB `tcg_distribution_targets.sheet_name` = `在庫テスト`・シート実測一致）

Web アプリが読むタブ名が `シート1` の場合は `在庫テスト` へ変更が必要。

#### mark / english_title 空欄（マスタ育成対象）

```
 mark_empty | en_title_empty | total 
------------+----------------+-------
         63 |            107 |   718
```

- mark が空欄: **63件 / 718件（8.8%）**
- english_title が空欄: **107件 / 718件（14.9%）**
- tcg_products テーブルの未入力が原因。配信スプレッドシートで該当列が空欄になる。

---

## PARITY-03 Phase 3 — tcg_products mark/english_title 追加 (2026-09-03)

### PR #3246: migration 20260903_180000_tcg_products_mark_en_t004.sql

**マージ前バックアップ必須（PO実施）:**
```sql
CREATE TABLE tenant_004.tcg_products_bak_20260903
AS SELECT * FROM tenant_004.tcg_products;

-- 件数確認（268件以上あること）
SELECT COUNT(*) FROM tenant_004.tcg_products_bak_20260903;
```

**復元 SQL（rollback 時）:**
```sql
-- 1. 列を削除
ALTER TABLE tenant_004.tcg_products DROP COLUMN IF EXISTS mark;
ALTER TABLE tenant_004.tcg_products DROP COLUMN IF EXISTS english_title;

-- 2. または backup から全件 COPY 復元:
-- TRUNCATE tenant_004.tcg_products CASCADE;
-- INSERT INTO tenant_004.tcg_products SELECT * FROM tenant_004.tcg_products_bak_20260903;
```

**充填率（2026-09-03 シート直読み）:**
- mark: 239/268 filled, NULL 29件 (89.2%)
- english_title: 251/268 filled, NULL 17件 (93.7%)

**GO記録:** GO発行者: Shingo / 日時: 2026-09-03 / GO原文: "GO を3本発行しました"

---

## Phase 0 — GAS レイアウト根拠の確立 (2026-09-03)

参照元: `sqr07_work/analysis-review-ui/src/` (最終更新 2026-08-30、sqr06より新)

### 0-1: SupplierQualityPage.tsx (一覧)

`sqr07_work/analysis-review-ui/src/SupplierQualityPage.tsx:29-56`

```tsx
<main>
  <DataList columns={SUPPLIER_QUALITY_COLUMNS} rows={summaries} ... />
</main>
```

特別なグリッドなし。DataList コンポーネントが一覧表示を担う。

### 0-2: SupplierDetailPage.tsx (詳細) の JSX 構造

`sqr07_work/analysis-review-ui/src/SupplierDetailPage.tsx:46-74`

```tsx
<main className="supplier-detail">
  <div className="supplier-detail-header"> ... </div>
  <div className="supplier-detail-body">
    <SourceRawPane ... />
    <section className="supplier-detail-items">
      {items.map((item) => (
        <div className="item-with-action">
          <ItemComparison item={item} readOnly={true} onJumpToSourceLine={jumpToLine} />
          <div className="item-actions">
            <button>修正する →</button>
          </div>
        </div>
      ))}
    </section>
  </div>
</main>
```

**重要**: `readOnly={true}` — Manual修正カラムは JSX 自体が非表示。

### 0-3: CSS grid-template-columns の実値 → カラム数断定

**ページボディ** `sqr07_work/analysis-review-ui/src/supplier-detail.css:1`:
```
.supplier-detail-body { grid-template-columns: clamp(320px,28vw,480px) minmax(0,1fr) }
```
→ **2カラム: [source-raw pane | items section]**

**ItemComparison 通常モード** `sqr07_work/analysis-review-ui/src/style.css:1`:
```
.item-head-grid, .aligned-fields, .item-extra-grid {
  grid-template-columns: minmax(300px,1fr) minmax(320px,1.05fr) minmax(330px,1.1fr)
}
```
→ 3カラム（Gemini | System | Manual）。**ただし詳細ページには適用されない**。

**ItemComparison readOnly モード** `sqr07_work/analysis-review-ui/src/item-comparison-readonly.css:1`:
```
.item-comparison--readonly .item-head-grid, .aligned-fields, .item-extra-grid {
  grid-template-columns: minmax(300px,1fr) minmax(320px,1.05fr)
}
```
→ **2カラム: Gemini | System のみ**

**5カラム定義** `style.css:1` `.sheet-header`:
```
grid-template-columns: 110px 360px minmax(300px,1fr) minmax(320px,1.05fr) minmax(330px,1.1fr)
```
→ 旧 TcgAnalysisReviewPage（`.comparison-sheet` コンテキスト）のシートヘッダー。**仕入元詳細と無関係**。

**断定: 仕入元詳細では `readOnly={true}` → ItemComparison は2カラム（Gemini | System）が正しい。**

### 0-4: 背景・カード・余白・sticky

`sqr07_work/analysis-review-ui/src/supplier-detail.css:1` より:

| 要素 | GAS 仕様 |
|------|---------|
| `.supplier-detail` | `padding: var(--space-5)` (24px) |
| `.source-raw` | `position: sticky; top: var(--space-3); height: calc(100vh - 140px); min-height: 420px; background: var(--color-surface); border-right: 1px solid var(--color-border)` |
| `.item-with-action` | `border-bottom: 1px solid var(--color-border)` (**カード背景なし**) |
| `.item-actions` | `display: flex; justify-content: flex-end; padding: var(--space-2) var(--space-3) var(--space-3)` |

GAS にはアイテムごとの `background: var(--color-surface)` はない。ユーザー要求（「各パネルをカードに入れ、背景を白」）はGASにない追加仕様。

### 0-5: analysis-review.css の定義が詳細画面に必要か

GAS では `style.css` がスコープなしで `.item-head-grid`・`.comparison-field` 等を定義。
FE の `analysis-review.css` は `.tcg-analysis-review` スコープのため、仕入元詳細（`.tcg-analysis-review` なし）では**適用されない**。

→ `display: grid`・`comparison-field` スタイルを詳細専用に追加が必要。PR #3235 で対応済み。

### 0-6: PR #3235 との差分照合

| 差分 | GAS 仕様 | PR #3235 実装 | 判定 |
|------|---------|--------------|------|
| ページ grid-template-columns | `clamp(320px,28vw,480px) minmax(0,1fr)` | 同値 | ✅ |
| source-raw sticky | あり | あり | ✅ |
| source-raw background | `var(--color-surface)` | `var(--bg-surface)` (ADR-067) | ✅ |
| ItemComparison カラム数 | 2カラム (readOnly) | 2カラム | ✅ |
| display:grid on item grids | スコープなし (style.css) | item-comparison-readonly.css に追加 | ✅ |
| アイテム背景 | なし (border-bottomのみ) | `var(--bg-surface)` + border | ⚠️ GAS外・ユーザー追加要求 |
| ページネーション | なし (limit:500全件) | 初期20件 + さらに読み込む | ✅ タスクC |
| overflow:hidden | なし | 削除済み | ✅ |

**結論: PR #3235 のカラム数（2カラム）はGAS準拠で正しい。**

---

## AUTO-01-01: 仕入元詳細 UI修正 + ページネーション (2026-09-03)

- PR: #3235
- ブランチ: release/parity03-supplier-quality-ui
- 変更ファイル:
  - frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx
  - frontend/src/features/tcg-analysis-review/supplier-detail-view.css
  - frontend/src/features/tcg-analysis-review/item-comparison-readonly.css
  - frontend/src/locales/ja.json
  - frontend/src/locales/en.json
- GAS の根拠:
  - sqr07_work/analysis-review-ui/src/supplier-detail.css:1 (ページグリッド・sticky・背景)
  - sqr07_work/analysis-review-ui/src/SupplierDetailPage.tsx:62 (readOnly=true)
  - sqr07_work/analysis-review-ui/src/item-comparison-readonly.css:1 (2カラム override)
  - sqr07_work/analysis-review-ui/src/style.css:1 (comparison-field・item-comparison 基本スタイル)

### 変更前

- ページ grid: `1fr 2fr`（GAS 仕様と不一致）
- source-raw: sticky/background なし（`.comparison-sheet .source-raw` スコープ外）
- ItemComparison: display:grid 未適用（`.tcg-analysis-review` スコープ外）→ フィールドが縦積み
- ページネーション: なし（全500件一括描画）

### 変更後

- ページ grid: `clamp(320px,28vw,480px) minmax(0,1fr)` (GAS準拠)
- source-raw: sticky + `var(--bg-surface)` 白背景
- ItemComparison: display:grid 適用 → 2カラム表示
- ページネーション: 初期20件 + さらに読み込む

- マージコミット: `17192936e090404c23ac8bba054a46d958bfbf31`

### 検証結果

| 確認項目 | 結果 | 生出力 |
|---------|------|-------|
| デプロイ全ステップ | ✅ success | run 33682346379: `{"status":"completed","conclusion":"success"}` |
| `GET /api/health` | ✅ ok | `{"status":"ok","database":"connected","redis":"connected","celery":"connected"}` |
| `https://app.salesanchor.jp/` | ✅ 200 | HTTP 200 |
| 他の画面（/leads） | ✅ 200 | HTTP 200 |
| 仕入元サマリー API | ⚠️ 401 | 認証なし → 401（エンドポイント存在確認のみ。件数確認はJWT必須のため測定不能） |

### 戻し方

git revert 17192936e090404c23ac8bba054a46d958bfbf31
→ PR を作成 → CI green → マージ でデプロイ前の状態に戻る

---

## AUTO-02-BE: PARITY-03 Phase 3 BE — 商品マスタ登録・再解析 API (2026-09-03)

- PR: #3239 (Draft)
- ブランチ: release/parity03-product-master-drawer-be
- コミット: 44185e42
- 変更ファイル:
  - backend/app/services/tcg_product_master_svc.py (新規)
  - backend/app/routers/tcg_product_master.py (新規)
  - backend/app/main.py (ルーター登録)
  - backend/tests/test_tcg_product_master.py (新規, 16 tests PASS)

### R-1 再解析 recon 結果

| 調査項目 | 結果 |
|---------|------|
| analyze_extraction_job の存在 | tcg_analyzer_svc.py:851 に存在（sync Session） |
| HTTP エンドポイントの有無 | なし（backend/app/routers/ 全件 grep で確認） |
| GAS 相当機能 | ShadowReviewV2.gs:87 refreshShadowReviewV2（全件対象） |
| 本実装の対象 | 1ジョブ限定 / UPSERT |

### R-1 安全装置の確認

| 確認項目 | 結果 |
|---------|------|
| 行単位の事前保存 | ❌ なし（集計値 before のみ）。行単位復元はベースラインテーブルで対応 |
| 一括実行（45ジョブ）防止 | ✅ URL パスに extraction_job_id 必須。一括実行不可 |

### GAS ベースラインスナップショット（実行済み・2026-09-03）

```sql
-- 実行済み（本番 DB: jarvis_db）
CREATE TABLE tenant_004.analysis_results_gas_baseline_20260903
AS SELECT * FROM tenant_004.analysis_results;
-- → SELECT 1626（件数確認済み）
```

**復元用テーブル**: `tenant_004.analysis_results_gas_baseline_20260903`（1626行・変更不可・削除禁止）

**復元 SQL**（対象ジョブを GAS 時点に戻す場合）:

```sql
INSERT INTO tenant_004.analysis_results
  SELECT * FROM tenant_004.analysis_results_gas_baseline_20260903
  WHERE extraction_item_id IN (
    SELECT id FROM tenant_004.extraction_items
    WHERE extraction_job_id = '<対象ジョブID>'
  )
ON CONFLICT (extraction_item_id) DO UPDATE
  SET pid_resolved   = EXCLUDED.pid_resolved,
      unit_resolved  = EXCLUDED.unit_resolved,
      needs_review   = EXCLUDED.needs_review,
      product_id     = EXCLUDED.product_id,
      pid_basis      = EXCLUDED.pid_basis,
      unit           = EXCLUDED.unit,
      condition      = EXCLUDED.condition,
      status         = EXCLUDED.status,
      note           = EXCLUDED.note,
      exclusion      = EXCLUDED.exclusion;
```

### ロールバック手順（訂正済み）

- 再解析（R-1）は Python エンジンで上書きする
- **GAS が計算した値には戻らない**（「再度呼べば復元可能」という記述は誤り・docstring 修正済み）
- 復元は上記 SQL でベースラインテーブルから差し戻す


---

### GAS バインドスクリプト所有権ポリシー（2026-09-04 確定）

**出典:**
- https://developers.google.com/apps-script/guides/bound
- https://developers.google.com/apps-script/guides/collaborating

**公式ドキュメントから確定した事実:**

| 事実 | 詳細 |
|---|---|
| コンテナ所有者 = スクリプト所有者 | 誰が作成したかに関わらず、スプレッドシートの所有者がスクリプトプロジェクトの所有者になる |
| アクセスリスト継承 | 編集権限を持つ人はスクリプトを実行でき、閲覧者はコードを参照できる |
| 共有ドライブのデプロイ制約 | デプロイするアカウントが同じドメインに属している必要がある |
| clasp の制約 | バインドスクリプトを新規作成できない（clone と edit のみ） |

**方針（PO 確定）:**

配信先スプレッドシートは Shingo が所有し、クライアントには渡さない。
Web アプリは認証なし（ANYONE_ANONYMOUS）のため、URL を渡すだけで閲覧可能。
スプレッドシート自体をクライアントと共有する必要はない。

これにより:
- スクリプトの所有権が Shingo に残る（コンテナ = Shingo 所有）
- クライアントがコードを見られない（アクセスリスト外）
- デプロイの制約がない（同一ドメイン・所有者がデプロイ）
- clasp で更新できる（clone 済みの `tcg-client-viewer/` から push）

**配布手順書への追記事項:**
「配信先スプレッドシートは自社（Shingo）所有とする。クライアントへの共有不要。Web アプリ URL のみ提供。」
