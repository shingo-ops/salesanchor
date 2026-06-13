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

## Phase B-1: sales_form 選択肢化

### 目的 / KGI

| 基準 | 検証方法 |
|-----|---------|
| sales_form を制御語彙（PO 定義の正規選択肢）に統一する | grep で free-text input が残らないことを確認 |
| 既存 DB 値を壊さない | option value は既存 DB 値と一致する文字列を使用 |
| i18n 対応（ADR-027） | 選択肢ラベルを t() 経由にする |

### 対象範囲

- `frontend/src/pages/inbox/InboxKartePanel.tsx:461-463` — `text input` → `select`
- `frontend/src/locales/ja.json` — 選択肢ラベルキー追加
- `frontend/src/locales/en.json` — 選択肢ラベルキー追加

### 対象外

- backend schema 変更（`str | None max_length=100` のまま）
- migration
- 既存 DB 値の一括変換（PO 判断・別作業）

### 技術 How

```tsx
// 現状（InboxKartePanel.tsx:461-463）
<input className="right-panel-field" type="text" value={cardForm.sales_form ?? ""}
  onChange={(e) => handleCardFieldChange("sales_form", e.target.value)} onBlur={handleCardFieldBlur}
  placeholder={t("leads.targetTitlesPlaceholder")} />

// 修正後（PO から選択肢を受け取った後に実装）
<select className="right-panel-field" value={cardForm.sales_form ?? ""}
  onChange={(e) => handleCardFieldChange("sales_form", e.target.value || null)} onBlur={handleCardFieldBlur}>
  <option value="">—</option>
  <option value="[PO定義値1]">{t("leads.salesForm_[key1]")}</option>
  <option value="[PO定義値2]">{t("leads.salesForm_[key2]")}</option>
  {/* PO 確認後に埋める */}
</select>
```

**option value は PO 定義の正規 DB 値をそのまま使う（Phase A と同パターン）**。

### 変更対象ファイル

| ファイル | 変更内容 |
|---------|---------|
| `frontend/src/pages/inbox/InboxKartePanel.tsx` | text input → select（:461-463） |
| `frontend/src/locales/ja.json` | `leads.salesForm_*` キー追加（選択肢数 × 1） |
| `frontend/src/locales/en.json` | 同上 |

migration なし / deploy.yml 変更なし。

### 受け入れ基準 / 検証方法

```bash
# sales_form が text input でなくなること
grep -n 'type="text".*sales_form\|sales_form.*type="text"' frontend/src/pages/inbox/InboxKartePanel.tsx
# → 0件

# ja/en キー対称確認
npm run lint

# 視覚ゲート
npx playwright test tests-e2e/karte-visual-gate.spec.ts --project=chromium
# → karte-customer-company.png に差分が出る場合は文言/構造変化を確認し baseline 更新
```

### 想定リスク

| リスク | 影響 | 対策 |
|-------|-----|------|
| 既存 DB 値が選択肢外 | 保存済みの sales_form が select でハイライトされず `""` 扱いになる | 確認 SQL 実行 → PO 判断（一括変換 or そのまま） |
| PO 定義の選択肢変更 | 再実装が必要 | 実装前に選択肢を確定してもらう |
| visual gate baseline ズレ | 次 PR がブロック | ubuntu-latest で --update-snapshots（Mac 禁止） |

### ロールバック方針

select → text input に戻すだけ。migration なしのため即時ロールバック可。

### PO確認事項

1. sales_form の正規選択肢は何か（例: "卸販売" / "小売" / "代理販売" 等）
2. 各選択肢の日本語・英語表示ラベルは何か
3. 既存 DB の sales_form 値（確認 SQL 実行後）にある自由入力値の扱いは？
   - 選択肢に追加する
   - null に変換する（要別作業）
   - そのまま残す（select で表示は崩れるが DB 値は保持）

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
