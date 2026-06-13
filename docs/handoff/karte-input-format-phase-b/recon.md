# カルテ入力項目・入力形式 Phase B Recon

**前提**: Phase A（#2125）implement 済み。  
**正本参照**: `docs/handoff/karte-input-format/recon.md` / `design.md`  
**日付**: 2026-06-14  
**ブランチ**: feature/morimoto/karte-phase-b-recon

---

## 1. KGI

| 目標 | 内容 |
|-----|------|
| 実装可否判断 | Phase B 各候補について「即実装可能 / PO確認必要 / ADR必要 / 対象外」を確定する |
| PR分割判断 | 1 PR にまとめるか 4分割するかを recon 根拠で決める |
| 業務語彙の非推測 | country 正規値 / sales_form 選択肢は PO 確認なしに決定しない |
| DB 書き込み禁止 | 既存値確認は読み取り専用 SQL 案の提示のみ。実行は PO 確認後 |

---

## 2. ADR 検索結果

```
git grep -i "country|sales_form|competitor_check|dirty|handleCardFieldBlur|karte|lead|i18n|enum" docs/adr/
```

| 検索語 | 該当 ADR | 備考 |
|-------|---------|------|
| `country` | ADR-126（registration form）| `company_addresses.country_code`（ISO 3166-1 alpha-2）**← leads.country とは別テーブル・別カラム** |
| `sales_form` | 該当なし（grep 済み） | leads.sales_form に関する設計 ADR は存在しない |
| `competitor_check` | ADR-108（フィールドリスト記載のみ） | 型・UI 挙動に関する ADR は存在しない |
| `dirty` / `handleCardFieldBlur` | 該当なし（grep 済み） | 保存方式に関する ADR は存在しない |
| `karte` | ADR-108（再設計）/ ADR-110（reference alignment） | Phase B 変更はいずれも Proposed/Accepted 範囲内 |
| `i18n` | ADR-027（全 UI 文字列 t() 必須） | country/sales_form を select にしても選択肢ラベルは t() 必須 |
| `enum` | ADR-109（status SSOT・不変コード化） | status 以外の enum 化に関する ADR は存在しない |
| `lead` | ADR-015 / ADR-119 / ADR-098 / ADR-059 等多数 | カルテ Phase B 範囲に直接影響する ADR は ADR-108 / ADR-110 のみ |

**ADR-126 注意点**: 登録フォームの country（`company_addresses.country_code`、ISO alpha-2）はカルテの `leads.country`（自由テキスト）と**別フィールド**。登録フォームの設計をカルテに直接流用すると型・スキーマが不整合になる。

---

## 3. 現コード file:line 調査

### 3-1. country

| 調査項目 | 内容 | file:line |
|---------|------|-----------|
| UI 入力形式 | `text input`（自由入力） | InboxKartePanel.tsx:437-439 |
| state 更新 | `handleCardFieldChange("country", e.target.value)` | InboxKartePanel.tsx:439 |
| 保存経路 | onBlur → handleCardFieldBlur → PATCH /leads/{id} | useInboxState.ts:382-402 |
| payload | 全 cardForm フィールドを送信（dirty-only でない） | useInboxState.ts:387-391 |
| backend schema | `country: str \| None = Field(default=None, max_length=100)` | backend/app/schemas/lead.py:120 |
| _UPDATABLE_COLUMNS | ✅ 含まれる | backend/app/routers/leads.py:76 |
| prospect_rank 影響 | なし（rank_fields に含まれない） | backend/app/routers/leads.py:369 |
| Discord sync 影響 | なし（estimated_scale のみトリガー） | backend/app/routers/leads.py:411 |
| 既存 DB 値への影響 | select 化した場合、既存の自由入力値（"Japan" / "日本" / "JP" 等の揺れ）が選択肢外になるリスク | — |
| audit log | record_audit_log で記録される | backend/app/routers/leads.py:396-400 |
| SSE/cache invalidation | db.commit() → invalidate_dashboard_cache → publish_leads_update | backend/app/routers/leads.py:401-407 |

**補足**: ADR-126 では登録フォームの country を `company_addresses.country_code`（ISO 3166-1 alpha-2）として保存しているが、カルテの `leads.country` は `VARCHAR(100)` の自由テキスト。スキーマレベルでの制約なし。

### 3-2. sales_form

| 調査項目 | 内容 | file:line |
|---------|------|-----------|
| UI 入力形式 | `text input`（自由入力） | InboxKartePanel.tsx:461-463 |
| state 更新 | `handleCardFieldChange("sales_form", e.target.value)` | InboxKartePanel.tsx:463 |
| 保存経路 | onBlur → handleCardFieldBlur → PATCH /leads/{id} | useInboxState.ts:382-402 |
| backend schema | `sales_form: str \| None = Field(default=None, max_length=100)` | backend/app/schemas/lead.py:115 |
| _UPDATABLE_COLUMNS | ✅ 含まれる | backend/app/routers/leads.py:75 |
| prospect_rank / Discord sync | なし | — |
| 既存 DB 値への影響 | select 化した場合、既存の自由入力値が選択肢外になるリスク | — |
| 業務定義 | 正規選択肢が業務上定義されていない。推測で決定禁止 | — |

### 3-3. competitor_check

| 調査項目 | 内容 | file:line |
|---------|------|-----------|
| UI select value | `""` / `"false"` / `"true"` の文字列 select | InboxKartePanel.tsx:541-543 |
| boolean 変換 | `v === "" ? null : v === "true"` → `handleCardFieldChange("competitor_check", boolean \| null)` | InboxKartePanel.tsx:538 |
| 保存トリガー | `onChange` + `setTimeout(handleCardFieldBlur, 0)`（他フィールドは onBlur） | InboxKartePanel.tsx:536-539 |
| backend schema | `competitor_check: bool \| None = None` | backend/app/schemas/lead.py:116 |
| LeadResponse | `competitor_check: bool \| None = None` | backend/app/schemas/lead.py:168 |
| _UPDATABLE_COLUMNS | ✅ 含まれる | backend/app/routers/leads.py:75 |
| 現状動作 | **正常動作している**。UI が変換処理を行い boolean を API に送信 | — |
| 型整合の問題 | UI 内部は一時的に `"true"/"false"` 文字列だが、API 送信前に boolean 変換済み。挙動上の問題はない | — |
| `competitorValue` 変数 | `cardForm.competitor_check === true ? "true" : cardForm.competitor_check === false ? "false" : ""` | InboxKartePanel.tsx:485-489 |

**評価**: competitor_check の「型整合」は **表面的な不一致であり実害なし**。UI select が文字列を使っているのは HTML select の仕様（value は常に string）。変換処理は UI 側で正確に実装されている。改修優先度は低い。

### 3-4. handleCardFieldBlur（全フィールド送信）

| 調査項目 | 内容 | file:line |
|---------|------|-----------|
| payload 生成 | `Object.entries(cardForm).filter(k != "id" && k != "lead_code" && k != "prospect_rank")` → 全フィールド | useInboxState.ts:387-391 |
| `""` → null 変換 | `.map([k, v] => [k, v === "" ? null : v])` | useInboxState.ts:390 |
| dirty 追跡 | **なし**。どのフィールドが変更されたかの記録機構がない | — |
| 成功後処理 | `setLeadDetail(updated)` + `setCardForm({...updated})` + `localStorage.removeItem` | useInboxState.ts:393-395 |
| 失敗処理 | `setCardSaveStatus("error")` + `setCardSaveError` 表示。retry ボタンなし | useInboxState.ts:398-401 |
| backend の exclude_unset | `data.model_dump(exclude_unset=True)` → **しかし frontend が全フィールドを送信するため全フィールドが "set" 扱いになる** | backend/app/routers/leads.py:358 |
| localStorage draft | `DRAFT_KEY(leadDetail.id)` に cardForm 全体をキャッシュ | useInboxState.ts:374-376 |
| 並行セッションリスク | User A・B 両方がカルテを開いている場合、blur ごとに互いの変更を上書く可能性 | — |
| prospect_rank 再計算副作用 | rank_fields が payload に常に含まれるため、毎 blur で rank が再計算される | leads.py:369-381 |
| audit log | 毎 blur で audit_log に update が記録される（フィールドが変わっていなくても） | leads.py:396-400 |
| Discord sync 副作用 | estimated_scale が payload に含まれるため、estimated_scale が実際に変わっていなくても discord_user_id があると sync が fire-and-forget される | leads.py:411-424 |

**dirty-only 化の技術的工数**:
1. `useInboxState.ts` に `dirtyFields: Set<keyof LeadDetail>` state を追加
2. `handleCardFieldChange` で `dirtyFields.add(field)` する
3. `handleCardFieldBlur` の payload 生成を dirty フィールドのみにフィルタ
4. 成功後に `setDirtyFields(new Set())` でリセット
5. **副作用注意**: dirty-only にすると `"" → null` 変換が dirty フィールドにしか適用されなくなる → null クリアが未送信になるケースがないか確認必要

---

## 4. 既存テスト / visual gate 影響

### Phase 5b toHaveScreenshot テスト

| テスト名 | スクリーンショット | country/sales_form select 化の影響 |
|---------|-----------------|----------------------------------|
| `[visual] karte-lead-deal` | `karte-lead-deal.png` | **影響なし**（country/sales_form は company tab。deal tab には表示されない） |
| `[visual] karte-customer-company` | `karte-customer-company.png` | **影響あり**。country が select になると見た目が変わる。sales_form が select になると見た目が変わる。baseline 更新が必要 |

### 機能テスト（karte-visual-gate.spec.ts）

| テスト名 | 影響 |
|---------|------|
| ADR-108-1: Deal tab does not show country field | 影響なし（not visible を検証しているため） |
| ADR-108-1: Deal tab does not show sales_form field | 影響なし（同上） |
| ADR-110-4: Company tab 4 sections | country/sales_form の見た目変化はセクション heading に影響しない |
| ADR-110-8/9: "追加予定" / "担当者" 禁止 | 影響なし |
| ADR-108-8: No URL input | 影響なし |

### dirty-only 化の影響

- toHaveScreenshot: **影響なし**（保存挙動はスクリーンショットに写らない）
- 機能テスト: blur 後の保存結果を検証するテストがあれば影響する可能性。現状 karte-visual-gate.spec.ts は保存 API を mock しているため直接影響はない
- 単体テスト: `handleCardFieldBlur` の payload 生成に関する単体テストが存在しない場合は新規追加が必要

---

## 5. 既存データ影響と確認 SQL 案

**重要**: 以下 SQL は PO 確認後に実行すること。ローカルや本番への書き込みは禁止。

### country 既存値の揺れ確認（読み取り専用）

```sql
-- 本番テナント(tenant_004)での country 値の分布を確認する
SELECT country, COUNT(*) as cnt
FROM tenant_004.leads
WHERE country IS NOT NULL
GROUP BY country
ORDER BY cnt DESC
LIMIT 50;
```

これで "Japan" / "日本" / "JP" / "日本国" 等の揺れが把握できる。  
**select 化後の既存値の扱いについては PO 判断が必要**（既存値を一括変換するか、null または "その他" にするか等）。

### sales_form 既存値の分布確認（読み取り専用）

```sql
-- 本番テナント(tenant_004)での sales_form 値の分布を確認する
SELECT sales_form, COUNT(*) as cnt
FROM tenant_004.leads
WHERE sales_form IS NOT NULL
GROUP BY sales_form
ORDER BY cnt DESC
LIMIT 50;
```

これで実際に入力されている販売形態の種類が把握できる。正規選択肢の決定に活用する。

---

## 6. 変更候補分類

### B-1: sales_form 選択肢化

| 項目 | 判断 |
|-----|------|
| 分類 | **PO確認必要** |
| 理由 | 正規選択肢（業務語彙）が未定義。実装前に PO から選択肢リストを提供してもらう必要がある |
| 技術リスク | 低（select に変えるだけ。max_length=100 の制約範囲内） |
| 既存値リスク | 中（既存の自由入力値が選択肢外になる。SQL 確認 → PO 判断が必要） |
| visual gate | karte-customer-company.png の baseline 更新が必要 |
| migration | **不要**（schema は str のまま、max_length=100 以内であれば OK） |

### B-2: country プルダウン化

| 項目 | 判断 |
|-----|------|
| 分類 | **PO確認必要** |
| 理由 | ①正規値を何にするか（日本語表記 / ISO コード / 両方を持つか）②表示と保存値を分けるか③既存値の扱い を PO が決める必要がある |
| ADR-126 参照 | 登録フォームは `company_addresses.country_code`（ISO alpha-2）。カルテは `leads.country`（VARCHAR 100）。別テーブル・別カラムのため直接流用不可 |
| 技術リスク | 中（国リストの実装・i18n・既存値の扱いが絡む） |
| 既存値リスク | 中（同上） |
| visual gate | karte-customer-company.png の baseline 更新が必要 |
| migration | **不要**（VARCHAR(100) は維持。ただし今後 ISO コード採用なら長さ十分） |

### B-3: competitor_check 型整合

| 項目 | 判断 |
|-----|------|
| 分類 | **対象外（現状で正常動作）** |
| 理由 | UI select の value が文字列なのは HTML 仕様上不可避。変換処理（InboxKartePanel.tsx:538）が正確に実装されており、API には boolean が送信されている。挙動上の問題なし |
| リスク | なし |
| 推奨 | 改修不要。Phase B から除外する |

### B-4: handleCardFieldBlur dirty-only 送信

| 項目 | 判断 |
|-----|------|
| 分類 | **PO確認必要（やるかどうかを含めて）** |
| 理由 | 現状でも実害（データ消失・不整合）の報告はない。改修すると audit log / Discord sync の副作用が減る一方で、実装複雑度が上がる。今やるかどうかは PO 判断 |
| 技術リスク | 中（dirty state 追跡 + null クリア動作の整合確認が必要） |
| 副作用軽減効果 | 毎 blur での audit log 記録・Discord sync fire-and-forget が真の変更時のみになる |
| visual gate | 影響なし |
| migration | 不要 |

### 危険変更の有無

- 既存 country / sales_form 値の一括変換: **禁止**（PO 確認なしに実行しない）
- migration: **Phase B 全候補で不要**（schema は str のまま）
- deploy.yml 変更: なし

---

## 7. 参照ファイル一覧

| ファイル | 内容 |
|---------|------|
| `frontend/src/pages/inbox/InboxKartePanel.tsx:437-439,461-463,485-545` | country / sales_form / competitor_check UI |
| `frontend/src/pages/inbox/useInboxState.ts:370-402` | handleCardFieldChange / handleCardFieldBlur 実装 |
| `backend/app/schemas/lead.py:92-135` | LeadUpdate（competitor_check:116, sales_form:115, country:120） |
| `backend/app/routers/leads.py:68-81,348-430` | _UPDATABLE_COLUMNS / PATCH endpoint / 副作用一覧 |
| `frontend/tests-e2e/karte-visual-gate.spec.ts` | 視覚ゲート・機能テスト |
| `docs/adr/ADR-108-inbox-karte-panel-redesign.md` | タブ設計正本（Proposed） |
| `docs/adr/ADR-110-karte-reference-alignment.md` | visual 真実（Accepted） |
| `docs/adr/ADR-126-registration-form-input-contract-v2.md` | 登録フォームの country_code（別テーブル・参考のみ） |
| `docs/adr/ADR-027-ui-internationalization.md` | i18n 強制ルール |
