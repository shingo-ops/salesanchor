# カルテ入力項目・入力形式 Phase B Design

**recon 参照**: `docs/handoff/karte-input-format-phase-b/recon.md`  
**Phase A 参照**: `docs/handoff/karte-input-format/design.md`  
**ADR 参照**: ADR-027 / ADR-108 / ADR-110  
**日付**: 2026-06-14  
**フェーズ**: B（4候補のうち B-3 は除外確定）  
**実装者**: Hikky-dev（PO確認後）

---

## 外部・過去事例の参照と我々への応用

**既存事例 — Phase A（#2125）の option value 維持パターン**:  
Phase A では temperature / estimated_scale の option label を `t()` 化する際、`option value=""` 属性（DB保存値）を一切変更しなかった。この「表示と保存値を分離する」パターンを Phase B でも適用する。sales_form / country を select 化する場合も同様に「UI 表示ラベルは t() 経由、保存値は DB 制約の範囲内で PO が定義した正規値」とする。

**ADR-126 の参考事例**:  
登録フォームの Country 欄は「検索つきコンボボックス（自由入力で候補絞り込み→リスト選択）、保存は ISO 3166-1 alpha-2」（ADR-126 §2-1）。ただしこれは `company_addresses.country_code` 列（VARCHAR, 別テーブル）の設計であり、カルテの `leads.country`（VARCHAR 100）とは別物。直接流用せず、PO 確認後に方針を決める。

**外部サービス・外部ライブラリ**: Phase B では新規ライブラリ導入なし。国リスト実装が必要な場合は i18n-iso-countries 等が候補になるが、PO が ISO コード採用を決めた後に検討する。

---

## 推奨 PR 分割

recon の分類結果から以下とする：

| Phase | 内容 | 優先順位 | 前提条件 |
|-------|------|---------|---------|
| B-1 | sales_form 選択肢化 | 1位 | PO から正規選択肢リストの提供を受けること |
| B-2 | country プルダウン化 | 2位 | PO から①表示/保存方針②既存値の扱い③正規値リストの提供を受けること |
| B-3 | competitor_check 型整合 | **除外** | 現状正常動作。改修不要 |
| B-4 | dirty-only 保存 | 3位（後回し可） | PO が「やる」と判断した場合のみ実装 |

**B-1 を先行する理由**: country より選択肢が少なく（販売形態は有限）、PO から選択肢を得さえすれば技術的工数が最小。既存値リスクも country より小さい（国名の揺れより販売形態の揺れの方が少ないと推測されるが、確認 SQL 実行後に判断）。

---

## Phase B-1: sales_form 複数選択 + その他自由記述 + テナント別カスタム

> **⚠️ 2026-06-14 PO方針変更**: 下記の「単一 select 暫定案」は採用しない。  
> PO 判断により「複数選択可能なチェックボックス付きドロップダウン」へ再設計する。  
> 本セクションは追補設計であり、旧暫定案（単一 select）は廃止する。

---

### 旧暫定案（廃止・参照のみ）

~~単一 `<select>` で sales_form 文字列を保存する案。migration なし。~~  
**採用しない。** PO が複数選択 + テナント別カスタムを要件として定義したため、単一 select では対応不可。

---

### 目的 / KGI

| 基準 | 検証方法 |
|-----|---------|
| sales_form を複数選択可能な制御語彙に統一する | UI で複数選択できること |
| 「その他」選択時に自由記述欄が表示される | E2E で「その他」チェック → テキスト欄出現を確認 |
| 選択内容が正しく保存・復元される | PATCH → GET で同じ選択状態が返ること |
| 既存 sales_form 値を失わない | 移行方針を実装前に確定する（SQL 確認 → PO 判断） |
| テナントごとに選択肢追加が将来可能な設計にする | D 案のスキーマが選択肢マスタを分離していること |

---

### 保存方式 比較

> **現状の `leads.sales_form`**: `VARCHAR(100)` のフリーテキスト。複数選択を表現できない。  
> 複数選択を実現するには保存方式の変更が必要であり、**いずれの案でも migration が発生する**。

| 案 | 方式 | migration | 概要 | メリット | デメリット |
|----|------|-----------|------|---------|-----------|
| **A** | `leads.sales_form` にカンマ区切り文字列保存 | 不要（既存列を流用） | `"実店舗,ECサイト"` 形式で既存列に保存 | migration ゼロ | SQL での集計・絞り込みが難しい。将来のテナント別カスタムに対応できない |
| **B** | `leads.sales_form_json` JSON 配列カラム追加 | **必要**（新規列 `sales_form_json jsonb`） | `["実店舗","ECサイト"]` 形式。既存 sales_form は残す | SQLで `@>` 演算子使用可。migration 1本 | テナント別マスタと選択の分離ができない。jsonb は RLS・インデックス注意 |
| **C** | `lead_sales_form_selections` 中間テーブル | **必要**（2テーブル追加） | 固定マスタ + lead ごとの選択行 | 正規化。集計・絞り込みが容易 | テナント別カスタム選択肢に対応できない |
| **D** | `tenant_sales_form_options` + `lead_sales_form_selections` | **必要**（2テーブル追加） | テナント別選択肢マスタ + lead ごとの複数選択 | テナント別カスタム対応。正規化。将来の管理 UI に対応可 | migration 工数が最大。API 設計も変わる |

**推奨: D 案**

---

### 推奨案 D の詳細設計

#### スキーマ

```sql
-- テナントごとの販売形態マスタ
CREATE TABLE {schema}.tenant_sales_form_options (
    id          SERIAL PRIMARY KEY,
    tenant_id   INTEGER NOT NULL,
    label       VARCHAR(100) NOT NULL,   -- 表示名（日本語）
    value       VARCHAR(100) NOT NULL,   -- DB 保存値（英数字推奨）
    sort_order  INTEGER NOT NULL DEFAULT 0,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- リードごとの販売形態選択（複数選択）
CREATE TABLE {schema}.lead_sales_form_selections (
    id         SERIAL PRIMARY KEY,
    lead_id    INTEGER NOT NULL REFERENCES {schema}.leads(id) ON DELETE CASCADE,
    option_id  INTEGER NOT NULL REFERENCES {schema}.tenant_sales_form_options(id),
    other_text TEXT,                    -- option.value = 'other' のときのみ使用
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (lead_id, option_id)
);
```

#### 初期データ（テナント初期化時に INSERT）

```sql
INSERT INTO {schema}.tenant_sales_form_options (tenant_id, label, value, sort_order) VALUES
  (:tenant_id, '実店舗',    'physical_store', 1),
  (:tenant_id, 'ECサイト',  'ec_site',        2),
  (:tenant_id, 'ライブ配信', 'live_streaming', 3),
  (:tenant_id, '卸・代理店', 'wholesale',      4),
  (:tenant_id, 'その他',    'other',          5);
```

#### API 変更

- **GET `/leads/{id}`** レスポンスに `sales_form_selections: [{option_id, label, value, other_text}]` を追加
- **PATCH `/leads/{id}`** ボディに `sales_form_selections: [{option_id, other_text?}]` を受け付ける
- 既存 `leads.sales_form`（VARCHAR 100）は migration では削除せず残す（additive-only 原則）。表示は `sales_form_selections` を優先し、`sales_form_selections` が空の場合に既存値をフォールバック表示する

#### フロントエンド

```tsx
// 概念コード（実装は別 PR）
// InboxKartePanel.tsx — company tab
<SalesFormMultiSelect
  options={tenantOptions}            // GET /tenant/sales-form-options
  selected={cardForm.sales_form_selections}
  onChange={(sels) => handleCardFieldChange("sales_form_selections", sels)}
  onBlur={handleCardFieldBlur}
/>

// SalesFormMultiSelect コンポーネント（新規作成）
// - チェックボックス付きドロップダウン
// - 「その他」選択時にテキスト入力欄を表示
// - i18n: option label は t() 経由 or テナントマスタの label を直接表示
```

#### 移行方針（既存 sales_form 値）

1. 確認 SQL を実行して既存値の分布を把握する（recon.md §5 参照）
2. PO が移行方針を決定する:
   - a. 既存値を `lead_sales_form_selections` に移行する（要移行スクリプト）
   - b. 既存値は表示のみ残し、編集時に新方式で上書きする
   - c. 既存値を null にする
3. 移行スクリプトは **PO GO 後に別 PR** で実装する

---

### B-1 の影響範囲

| 区分 | 内容 |
|-----|------|
| migration | **必要**（2テーブル追加 + 初期データ INSERT）。ADR-045 additive-only 原則に準拠 |
| backend | 新規 router または leads router 拡張（GET/PATCH `/leads/{id}` の response/body 変更） |
| frontend | `SalesFormMultiSelect` 新規コンポーネント + InboxKartePanel.tsx 修正 |
| i18n | 選択肢ラベルはテナントマスタで管理するか、ja/en.json で管理するか PO 確認が必要 |
| visual gate | `karte-customer-company.png` の baseline 更新が必要 |
| deploy.yml | migration ステップの追記が必要（migration-guard.yml が自動検知） |

**B-1 は「軽量 UI 修正」ではなく、DB / API 設計を伴う中規模実装 PR になる。**  
単一 select 案（migration なし）とは工数・リスクが大幅に異なる。

---

### 実装前ゲート（既存データ確認 SQL）

以下を **PO 確認後に実行**すること。本番 DB への書き込みは禁止。

```sql
-- tenant_004 の既存 sales_form 値の分布
SELECT sales_form, COUNT(*) as cnt
FROM tenant_004.leads
WHERE sales_form IS NOT NULL
GROUP BY sales_form
ORDER BY cnt DESC
LIMIT 50;
```

この結果を受けて移行方針を PO と決定してから実装に入る。

---

### ロールバック方針

- **migration**: additive-only のため、追加したテーブルを DROP するには PO 確認が必要（ADR-045）
- **frontend**: `SalesFormMultiSelect` を削除し、text input に戻す
- **API**: `sales_form_selections` フィールドをレスポンスから除去

migration を含むため、ロールバックは Phase A（i18n のみ）より複雑。PO の GO 確認を実装前に必ず取ること。

### PO確認事項（B-1 追補）

1. 初期選択肢（実店舗 / ECサイト / ライブ配信 / 卸・代理店 / その他）でよいか
2. 「卸・代理店」を1つにするか、「卸」と「代理店」に分けるか
3. 「その他」自由記述をどこまで扱うか
   - カルテ内表示のみ（検索・集計対象外）
   - 検索対象にする（full-text index 追加が必要）
   - 集計・分析対象にする（将来の dashboard 機能拡張）
4. テナント管理画面での選択肢追加（CRUD）をいつ実装するか（B-1 同梱か / 別フェーズか）
5. 既存 sales_form 値の移行方針（確認 SQL 実行後に提示する）
6. i18n: 選択肢ラベルをテナントマスタで管理するか（多言語テナント対応）、ja/en.json で固定するか

---

## Phase B-2: country プルダウン化

### 目的 / KGI

| 基準 | 検証方法 |
|-----|---------|
| country を正規値（PO 定義の国リスト）に統一する | 自由テキスト入力の排除 |
| 既存 DB 値を壊さない | 移行方針は PO 判断 |
| i18n 対応（ADR-027） | 選択肢ラベルを t() 経由にする |

### 対象範囲

- `frontend/src/pages/inbox/InboxKartePanel.tsx:437-439` — `text input` → `select`（または検索つきコンボボックス）
- `frontend/src/locales/ja.json` / `en.json` — 選択肢キー追加

### 対象外

- `leads.country` カラムの型変更（VARCHAR(100) のまま）
- migration
- 既存値の一括変換

### 技術 How（方針確定待ち）

PO の回答によって実装が大きく変わる。3パターン：

| PO 方針 | 実装 | 複雑度 |
|--------|------|-------|
| A: シンプル select（10〜20カ国） | `<select>` + `leads.salesForm_*` パターンと同様 | 低 |
| B: 検索つきコンボボックス（全世界） | datalist または react-select 等のライブラリ検討 | 中〜高 |
| C: 表示/保存値分離（表示は日本語、保存は ISO alpha-2） | `option value="JP">日本` 形式。既存値の変換も必要 | 高 |

**推奨**: PO がシンプルな国リスト（10〜20カ国程度）を定義するなら A が最も安全。

### 変更対象ファイル（方針 A の場合）

| ファイル | 変更内容 |
|---------|---------|
| `frontend/src/pages/inbox/InboxKartePanel.tsx` | text input → select（:437-439） |
| `frontend/src/locales/ja.json` | `leads.country_*` キー追加 |
| `frontend/src/locales/en.json` | 同上 |

migration なし / deploy.yml 変更なし。

### 受け入れ基準 / 検証方法

```bash
grep -n 'type="text".*country\|country.*type="text"' frontend/src/pages/inbox/InboxKartePanel.tsx
# → 0件

npx playwright test tests-e2e/karte-visual-gate.spec.ts --project=chromium
# → karte-customer-company.png 差分確認
```

### 想定リスク

| リスク | 影響 | 対策 |
|-------|-----|------|
| 既存 DB の国名揺れ（"Japan" / "日本" 等） | select で選択肢外になる | 確認 SQL 実行 → PO 判断 |
| 国リスト管理 | 将来の追加・変更が必要になる | シンプルな select なら ja.json/en.json 更新で対応可 |
| visual gate baseline ズレ | 次 PR がブロック | ubuntu-latest で --update-snapshots |

### ロールバック方針

select → text input に戻すだけ。migration なし。

### PO確認事項

1. 正規値を何にするか（例: 日本語国名 / ISO コード / 両方持つか）
2. 表示と保存値を分けるか（例: 表示「日本」、保存「JP"」）
3. 何カ国を選択肢として用意するか
4. 既存 DB 値の扱い（確認 SQL 実行後に提示する）

---

## Phase B-3: competitor_check 型整合（除外）

**recon の評価を踏まえ、Phase B から除外する。**

理由: UI select の value が文字列なのは HTML 仕様上避けられない。変換処理（`InboxKartePanel.tsx:538`）が正確に動作しており、API には boolean が送信されている。実害なし。改修コストに見合わない。

---

## Phase B-4: dirty-only 保存

### 目的 / KGI

| 基準 | 検証方法 |
|-----|---------|
| handleCardFieldBlur の副作用（無駄な audit log / Discord sync）を減らす | audit_log の update 件数が真の変更時のみになること |
| 並行セッションでの上書きリスクを低減する | 仕様上の保証（完全排除は楽観的ロックが必要） |

### 技術 How

```ts
// useInboxState.ts — 追加が必要な state
const [dirtyFields, setDirtyFields] = useState<Set<keyof LeadDetail>>(new Set());

// handleCardFieldChange の変更（370行目付近）
const handleCardFieldChange = useCallback((field: keyof LeadDetail, value: unknown) => {
  setDirtyFields(prev => new Set(prev).add(field));
  setCardForm((prev) => {
    // ...existing code...
  });
}, [leadDetail]);

// handleCardFieldBlur の payload 生成変更（387-391行目）
// 現状: 全フィールド送信
const payload = Object.fromEntries(
  Object.entries(cardForm)
    .filter(([k]) => k !== "id" && k !== "lead_code" && k !== "prospect_rank")
    .map(([k, v]) => [k, v === "" ? null : v])
);

// 変更後: dirty フィールドのみ送信
const payload = Object.fromEntries(
  Object.entries(cardForm)
    .filter(([k]) => dirtyFields.has(k as keyof LeadDetail))
    .filter(([k]) => k !== "id" && k !== "lead_code" && k !== "prospect_rank")
    .map(([k, v]) => [k, v === "" ? null : v])
);

// 成功後のリセット
setDirtyFields(new Set());
```

**注意事項**:
- `dirtyFields` が空の場合は PATCH をスキップする（または空の場合の処理を決める）
- `""` → null のクリア動作が dirty フィールドにのみ適用されることを確認
- competitor_check は `onChange` で即時 blur するため、dirtyFields への追加が先に行われていることを確認（タイミング問題）

### 変更対象ファイル

| ファイル | 変更内容 |
|---------|---------|
| `frontend/src/pages/inbox/useInboxState.ts` | dirtyFields state + handleCardFieldChange + handleCardFieldBlur |

### 受け入れ基準

- `handleCardFieldBlur` が dirtyFields が空のときに PATCH を送信しない
- 1フィールドだけ変更して blur したとき、そのフィールドのみ payload に含まれること
- 複数フィールドを変更した後に blur したとき、変更済みフィールドのみ payload に含まれること

### 想定リスク

| リスク | 影響 | 対策 |
|-------|-----|------|
| `""` → null クリアが dirty フィールドにのみ適用される | 意図的なクリア操作が送信されない場合がある（例: フィールドを null にするために空文字にした場合） | `""` 入力 → dirty フィールドに追加されるので問題ない |
| competitor_check の onChange+setTimeout タイミング | dirtyFields が空のまま blur される可能性 | setTimeout(handleCardFieldBlur, 0) の前に handleCardFieldChange が呼ばれるため問題ないはず。要 E2E テスト確認 |
| 楽観的ロックがないため並行セッション競合は完全排除不可 | 低頻度なら実用上問題ない | 将来の拡張として楽観的ロック（updated_at チェック）を ADR 起案する |

### ロールバック方針

dirtyFields state 削除 + handleCardFieldBlur を元のコードに戻す。1ファイルのみ変更のため即時ロールバック可。

### PO確認事項

1. dirty-only 保存を今やるか、後回しにするか
2. 毎 blur での audit log 記録が現在問題になっているか（DB 容量・分析用途）
3. 並行セッション競合が実際に問題になっているか（報告はあるか）

---

## PO確認事項まとめ

実装開始前に以下を確認すること（推測で決定禁止）：

| 項目 | 確認内容 | 対象 PR |
|-----|---------|--------|
| sales_form 正規選択肢 | 選択肢の値・ラベル（日本語・英語）のリスト | B-1 |
| 既存 sales_form 値の扱い | 確認 SQL 実行後、一括変換するか／そのまま残すか | B-1 |
| country 正規値の方針 | 日本語 / ISO / 両方か。何カ国か | B-2 |
| country 表示/保存値の分離 | 表示「日本」・保存「JP」のようにするか | B-2 |
| 既存 country 値の扱い | 確認 SQL 実行後、一括変換するか／そのまま残すか | B-2 |
| dirty-only 優先度 | 今やるか / 後回しか | B-4 |
| competitor_check | 現状挙動で問題ないか（除外でよいか） | 除外確認 |

---

## 実装ハンドオフ（次 PR 用）

**前提**: PO から sales_form 選択肢リストを受け取った後、以下の手順で B-1 を実装する。

### B-1 実装手順

1. `frontend/src/pages/inbox/InboxKartePanel.tsx:461-463` を text input から select に変更する
   - value の型は `string | null`（既存のまま）
   - onChange: `handleCardFieldChange("sales_form", e.target.value || null)`（空文字 → null）
   - onBlur: `handleCardFieldBlur`（既存のまま）
   - option value: PO 定義の正規 DB 値をそのまま使用

2. `frontend/src/locales/ja.json` の `leads` セクションに `"salesForm"` キーの直後に選択肢キーを追加
   - 例: `"salesForm_wholesale": "卸販売"`, `"salesForm_retail": "小売"` 等

3. `frontend/src/locales/en.json` に同一キーを追加

4. 検証:
   ```bash
   cd frontend && npm run lint
   cd frontend && npm run check:stylelint
   cd frontend && npm run check:css-values
   cd frontend && npx playwright test tests-e2e/karte-visual-gate.spec.ts --project=chromium
   ```

5. karte-customer-company.png に差分が出た場合: 文言・構造変化を確認し ubuntu-latest で `--update-snapshots`

### B-4 実装手順（PO が優先すると判断した場合）

1. `frontend/src/pages/inbox/useInboxState.ts` に `dirtyFields` state を追加
2. `handleCardFieldChange` で `setDirtyFields(prev => new Set(prev).add(field))` を追加
3. `handleCardFieldBlur` の payload 生成を dirty フィールドのみにフィルタ
4. 成功後 `setDirtyFields(new Set())` でリセット
5. 単体テストを追加（handleCardFieldBlur の payload 生成を検証）
