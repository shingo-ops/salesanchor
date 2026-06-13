# カルテ入力項目・入力形式 Design — Phase A（i18n 修正）

**recon 参照**: `docs/handoff/karte-input-format/recon.md`  
**ADR 参照**: ADR-027（i18n 強制）/ ADR-108（タブ設計）/ ADR-110（visual 真実）  
**日付**: 2026-06-14  
**フェーズ**: A（低リスク i18n 修正のみ）  
**実装者**: Hikky-dev

---

## 1. 目的 / KGI

| 基準 | 検証方法 |
|-----|---------|
| カルテ内の英語ハードコード表示文字列をゼロにする（3箇所） | `grep` で JSX 表示文字列として残らないことを確認（受け入れ基準 §6 参照） |
| DB 値・保存形式・API 仕様を変更しない | option value 属性は既存値のまま維持。schema/routers/migrations 変更なし |
| 既存カルテ視覚ゲートを壊さない | `npx playwright test karte-visual-gate.spec.ts` が全パス（差分あれば内容確認 → baseline 更新要否を記録） |

**外部事例**: なし（既存 i18n パターンの踏襲のみ。customerType_trust / responseSpeed_24h 等の先行実装を参考にする）

---

## 2. 対象範囲（Phase A）

### 2-1. `temperature` option label の t() 化

**問題**: `InboxKartePanel.tsx:524-526` にて option の表示文字列が英語ハードコード。

```tsx
// 現状（InboxKartePanel.tsx:524-526）
<option value="Hot">Hot</option>
<option value="Warm">Warm</option>
<option value="Cold">Cold</option>
```

```tsx
// 修正後（value は変えない）
<option value="Hot">{t("leads.temperature_hot")}</option>
<option value="Warm">{t("leads.temperature_warm")}</option>
<option value="Cold">{t("leads.temperature_cold")}</option>
```

**追加キー**:

| キー | ja.json | en.json |
|-----|---------|---------|
| `leads.temperature_hot` | `"高"` | `"Hot"` |
| `leads.temperature_warm` | `"中"` | `"Warm"` |
| `leads.temperature_cold` | `"低"` | `"Cold"` |

> 和訳選定理由: 「高/中/低」は温度感の意味として自然。「ホット/ウォーム/コールド」はカタカナで残してもよいが PO 確認が必要なため design 段階ではニュートラルな訳を採用。**実装時に PO へ訳の確認を取ること。**

---

### 2-2. `estimated_scale` option label の t() 化

**問題**: `InboxKartePanel.tsx:554-556` にて option の表示文字列が英語ハードコード。

```tsx
// 現状（InboxKartePanel.tsx:554-556）
<option value="Small">Small</option>
<option value="Medium">Medium</option>
<option value="Large">Large</option>
```

```tsx
// 修正後（value は変えない）
<option value="Small">{t("leads.estimatedScale_small")}</option>
<option value="Medium">{t("leads.estimatedScale_medium")}</option>
<option value="Large">{t("leads.estimatedScale_large")}</option>
```

**追加キー**:

| キー | ja.json | en.json |
|-----|---------|---------|
| `leads.estimatedScale_small` | `"小"` | `"Small"` |
| `leads.estimatedScale_medium` | `"中"` | `"Medium"` |
| `leads.estimatedScale_large` | `"大"` | `"Large"` |

> 和訳選定理由: 「小/中/大」はシンプルかつ既存 UI の規模感表現と整合。

---

### 2-3. `target_titles` placeholder の t() 化

**問題**: `InboxKartePanel.tsx:458` にて placeholder がハードコード英語。

```tsx
// 現状（InboxKartePanel.tsx:458）
onBlur={handleCardFieldBlur} placeholder="Pokemon, One Piece, ..." />
```

```tsx
// 修正後
onBlur={handleCardFieldBlur} placeholder={t("leads.targetTitlesPlaceholder")} />
```

**追加キー**:

| キー | ja.json | en.json |
|-----|---------|---------|
| `leads.targetTitlesPlaceholder` | `"例: ポケモン、ワンピース..."` | `"e.g. Pokemon, One Piece..."` |

---

### 2-4. ja.json / en.json への追加位置

既存の命名パターン（`customerType_trust`, `responseSpeed_24h` 等）に倣い、**該当フィールドキーの直後**に option キーを追加する。

**ja.json** — `leads` セクション:

```json
// 追加位置: "temperature": "温度感" の直後（現 line 457）
"temperature": "温度感",
"temperature_hot": "高",
"temperature_warm": "中",
"temperature_cold": "低",

// 追加位置: "estimatedScale": "想定規模" の直後（現 line 458）
"estimatedScale": "想定規模",
"estimatedScale_small": "小",
"estimatedScale_medium": "中",
"estimatedScale_large": "大",

// 追加位置: "targetTitles": "取り扱いタイトル" の直後（現 line 542）
"targetTitles": "取り扱いタイトル",
"targetTitlesPlaceholder": "例: ポケモン、ワンピース...",
```

**en.json** — 同一キー・同一位置（ja.json と常に同期）:

```json
"temperature": "Temperature",
"temperature_hot": "Hot",
"temperature_warm": "Warm",
"temperature_cold": "Cold",

"estimatedScale": "Estimated scale",
"estimatedScale_small": "Small",
"estimatedScale_medium": "Medium",
"estimatedScale_large": "Large",

"targetTitles": "Titles",
"targetTitlesPlaceholder": "e.g. Pokemon, One Piece...",
```

---

## 3. 対象外（Phase B または PO 判断待ち）

| 項目 | 理由 |
|-----|------|
| `country` プルダウン化 | 正規値リスト・ISO 基準の合意が必要（PO 判断） |
| `sales_form` 選択肢化 | 業務定義の制御語彙が未定（PO 判断） |
| `handleCardFieldBlur` dirty-only 送信 | 副作用（rank 再計算・Discord sync）との整合確認が必要（PO 判断） |
| `competitor_check` 型整合 | `"true"/"false"` 文字列 select ↔ bool の変換。現状動作しているため影響範囲確認要 |
| `customer_type` / `response_speed` DB 値 | ADR-109 §enum 化待ち。現在 eslint-disable 付き除外済み |
| `assigned_to` 表示 | ADR-108 scope-out 明記。karte-visual-gate.spec.ts:360 で自動検証済み |
| deprecated フィールド 4件削除 | 別 ADR 起案・PO 確認必須 |

---

## 4. recon 根拠

| 項目 | recon 参照箇所 | ソース |
|-----|--------------|-------|
| `temperature` ハードコード | recon.md §Table1 商談タブ 4行目「⚠️ option value "Hot"/"Warm"/"Cold" が t() 未使用」 | `InboxKartePanel.tsx:524-526` |
| `estimated_scale` ハードコード | recon.md §Table1 商談タブ 7行目「⚠️ option value "Small"/"Medium"/"Large" が t() 未使用」 | `InboxKartePanel.tsx:554-556` |
| `target_titles` placeholder | recon.md §Table1 顧客タブ 4行目「⚠️ placeholder がハードコード英語」 | `InboxKartePanel.tsx:458` |
| i18n キー追加先 | `frontend/src/locales/ja.json:457,458,542` / `en.json:457,458,542` | ローカル grep 確認済み |
| 既存 option キーパターン | `leads.customerType_trust` / `leads.responseSpeed_24h` 等 | `ja.json:486-490` / `en.json:486-490` |
| 視覚ゲートテスト | `toHaveScreenshot` 2本 (karte-lead-deal.png / karte-customer-company.png) | `karte-visual-gate.spec.ts:390-403` |

---

## 5. 技術 How（実装手順）

1. **`frontend/src/locales/ja.json`** — 3セクション計7キーを追加（§2-4 の diff のとおり）
2. **`frontend/src/locales/en.json`** — 同一7キーを追加（ja.json と同時・同位置）
3. **`frontend/src/pages/inbox/InboxKartePanel.tsx`**
   - `:524-526`: `temperature` options を `{t("leads.temperature_hot")}` 等に置換
   - `:554-556`: `estimated_scale` options を `{t("leads.estimatedScale_small")}` 等に置換
   - `:458`: `target_titles` placeholder を `{t("leads.targetTitlesPlaceholder")}` に置換

**注意**: `option value=""` 属性は絶対に変更しない。DB・API の保存値が壊れる。

---

## 6. 受け入れ基準 / 検証方法

### 自動チェック（PR に必須）

```bash
# i18n キー対称チェック（ja/en 同一キー確認）
cd frontend && npm run lint

# CSS 静的チェック（今回変更なし想定）
cd frontend && npm run check:stylelint
cd frontend && npm run check:css-values

# 視覚ゲート（karte 専用 spec 単体）
cd frontend && npx playwright test tests-e2e/karte-visual-gate.spec.ts --project=chromium
```

### grep チェック（手動・PR レビュー時に確認）

```bash
# JSX表示文字列として英語ハードコードが残らないこと
grep -n '"Hot"\|"Warm"\|"Cold"' frontend/src/pages/inbox/InboxKartePanel.tsx
# → option value="" の属性のみ残る（表示文字列ゼロ）

grep -n '"Small"\|"Medium"\|"Large"' frontend/src/pages/inbox/InboxKartePanel.tsx
# → option value="" の属性のみ残る（表示文字列ゼロ）

grep -n 'Pokemon, One Piece' frontend/src/pages/inbox/InboxKartePanel.tsx
# → 0件

# ja/en キー対称確認
node -e "
const ja = require('./frontend/src/locales/ja.json');
const en = require('./frontend/src/locales/en.json');
const jaKeys = Object.keys(ja.leads);
const enKeys = Object.keys(en.leads);
const diff = jaKeys.filter(k => !enKeys.includes(k)).concat(enKeys.filter(k => !jaKeys.includes(k)));
console.log('差分キー:', diff.length === 0 ? 'なし（OK）' : diff);
"
```

### 視覚差分の扱い

| 状況 | 対応 |
|-----|------|
| toHaveScreenshot で diff なし | そのまま Pass |
| diff あり → **文言変更のみ**（option ラベル "Hot" → "高" 等）が原因 | baseline 更新が必要。PR 本文に「baseline 更新: karte-lead-deal.png, karte-customer-company.png（温度感表示ラベル変更のため）」と明記して更新 |
| diff あり → レイアウト崩れ・構造変化が原因 | 実装ミス。修正してから再実行 |

> baseline 更新手順: `workflow_dispatch --update-snapshots` を ubuntu-latest で実行（Mac ローカル生成禁止）。

---

## 7. リスク

| リスク | 影響 | 対策 |
|-------|-----|------|
| `option value=""` を誤って変更すると DB 保存値が壊れる | **CRITICAL** | value 属性は変更禁止。grep でレビュー時確認 |
| ja.json に追加して en.json を忘れると UI 表示崩れ（i18n fallback で英語キー名が出る） | HIGH | 2ファイルを同一コミットで更新。キー対称 grep を必ず実行 |
| toHaveScreenshot で baseline ズレが残ると以降の PR がブロックされる | MEDIUM | baseline 更新を同一 PR で完結させる |
| 和訳（高/中/低）が業務用語と合わない | LOW | 実装前に PO へ訳確認。差し戻しの場合は訳だけ変更すればよい |

---

## 8. Phase B への引き継ぎ

以下は Phase A 完了後に別途 design.md または PO 判断待ちで進める。

| 項目 | 引き継ぎ条件 |
|-----|------------|
| `country` プルダウン化 | PO から正規国リストの提示があってから design |
| `sales_form` 選択肢化 | PO から正規選択肢（業務定義）の提示があってから design |
| `handleCardFieldBlur` dirty-only 化 | 副作用整合確認 + PO 合意後に design |
| `competitor_check` 型整合 | Phase A の diff を確認後、影響が軽微なら Phase B 先頭に追加 |

---

## 変更ファイル一覧（Phase A）

| ファイル | 変更内容 |
|---------|---------|
| `frontend/src/locales/ja.json` | 7キー追加（leads セクション） |
| `frontend/src/locales/en.json` | 7キー追加（leads セクション） |
| `frontend/src/pages/inbox/InboxKartePanel.tsx` | 3箇所を t() 化（行数: :524-526, :554-556, :458） |

migration なし / deploy.yml 変更なし / 本番 scripts 変更なし。
