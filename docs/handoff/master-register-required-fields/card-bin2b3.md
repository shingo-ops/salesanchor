<!-- rules-ack: 607cd6e7 -->
# 実装カード 便2b-3 — 解析レビューからの商品登録に、細分類・除外ワード・「調べたが存在しない」の印を足す（ADR-1020）

> この文書は何か：共用商品マスタの9項目必須化（ADR-1020）の便2b-3の作業指示書です。解析レビューから新しい商品を登録する入口は2つあります。両方に次の4つを足します。①細分類を選ぶ欄（選んだ作品に紐づくものだけ）。②除外ワードの欄（無い入口だけ）。③英語名・型番・発売日・除外ワードの「調べたが存在しない」の印。④まだ入っていない項目の案内。あわせて、登録フォームの選択肢を返す API の応答の形も直します。今は細分類の「使えるゲーム」が応答から落ちています。保存はまだ止めません（止めるのは便3）。

- 設計: docs/handoff/master-register-required-fields/design.md:59（解析レビューの登録ドロワー）・§7（KGI と3便は PO 承認 2026-10-16「y」）
- 前提の便: 便2a（#4412）・便2b-1（#4414）が main にマージ済み・本番反映済み。§10 手順1 で確かめる
- 対象ADR: ADR-1020（本テーマ）、ADR-027（i18n。文言は `t()` だけ・ja/en 同じキー）、ADR-144（金型。`AsyncCombobox`・`Checkbox`・`Callout`・`Textarea` を使い、生の input/select・色の直値・新しい `style=` を書かない）
- 状態: 設計は Opus 自己審査 APPROVE。§2-2 の細部は Opus の技術判断（設計の目的・範囲は変えない。2つの入口の今の動き〔付け替えの有無〕は変えない）
- 危険便: いいえ（`migrations/`・`deploy.yml`・本番 `scripts/` を含まない）。担当はマージしない
- 担当: 実装 Sonnet／コード審査・マージ・反映確認 Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（下書きにしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（解析レビューからの登録だけ） |
| 5 | 起点と作業場所を明示 | ○（§10 手順1） |
| 6 | 書式は実例で示した | ○（§4 に完成形のコード） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-2） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実物から | ○（origin/main 5f3cca95b の実物） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§12） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない | ○ |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○ |
| guards/04-worktree.md | 新しい作業場所は `scripts/new-worktree.sh` で作る | ○（§10 手順1） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh`。触るファイル・削除するファイルは同一行カンマ区切り | ○（§10） |
| guards/08-vps.md | 本番には触らない | ○（§8） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード ADR-1020 便2b-3 の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. `backend/app/routers/tcg_product_master.py`: 登録フォーム応答の `lookups` を明示の形にし、細分類の `is_active`・`game_ids` を落とさない（§4-1）
2. `backend/tests/test_tcg_product_master.py`: 試験 1 本（§4-1）
3. `frontend/api-contract/openapi.json`: 再生成（§4-1）
4. `frontend/src/features/tcg-analysis-review/reviewActions.ts`: 型と送る形（§4-2）
5. `frontend/src/features/tcg-analysis-review/ReviewRegisterProductForm.tsx`: 細分類・除外ワード・印・案内（§4-3）
6. `frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx` の `RegistrationSection`: 細分類・印・案内。API の呼び出しを `reviewActions.ts` の関数に寄せる（§4-4）
7. `frontend/src/locales/ja.json`・`en.json`: 5 キー（§4-5）
8. 試験: `ReviewRegisterProductForm.test.tsx`・`ProductMasterDrawer.test.tsx`・`reviewActions.test.ts`（§4-6）
9. このカードを `docs/handoff/master-register-required-fields/card-bin2b3.md` に置く

入れない:
- 保存を止めること（便3）。今ある「入力してください」（5項目）と、ドロワーのボタンを押せなくする条件は変えない
- 登録の後の付け替えの有無（`ReviewRegisterProductForm` は付け替える・`RegistrationSection` は付け替えない、のまま）
- `RegistrationSection` 以外の `ProductMasterDrawer.tsx` の部分（検索ワード追記・除外表示・割り当て変更）、`SearchSelect` の見た目
- `backend/app/services/`、`check-duplicates` と `POST /tcg/products` の受け口、商品詳細（便2b-1）、細分類マスタ（便2b-2）、CSV（便2c）

## 2. 前提の事実と設計の細部

### 2-1. 事実

| # | 事実 | 出典 |
|---|---|---|
| F1 | 登録フォームの応答モデルは `lookups: dict[str, list[LookupOption]]` で、`LookupOption` は `id`・`name` だけ。そのため、サービスが細分類に付けた `is_active`・`game_ids` は応答で捨てられる | `backend/app/routers/tcg_product_master.py:43-45`・`:56-58`、`backend/app/services/tcg_product_master_svc.py:102-117`・`:245` |
| F2 | `POST /tcg/products` は `product_format_id: int \| None` と `blank_confirmations: list[Literal["name_en","mark","release_date","exclude_keywords"]]` を受け、作成時に印を保存する。空文字の `product_format_id` は型違いで 422 になる | `tcg_product_master.py:95-110`・`:229-246`、`tcg_product_master_svc.py:453-571` |
| F3 | `check-duplicates` の受け口は余計なキーを無視する（`model_config` なし） | `tcg_product_master.py:77-88` |
| F4 | 作成される商品は `tenant_id` を入れない（共用マスタ）。検索ワード・除外ワードはカンマで分けて保存する | `tcg_product_master_svc.py:527-536`・`:575-600` |
| F5 | 登録の入口は2つ。`ReviewRegisterProductForm`（`ReviewFixWizard.tsx:14` から。登録の後に付け替える）と、`ProductMasterDrawer.tsx` の `RegistrationSection`（`SupplierDetailView.tsx:135` から。付け替えない・`api.get`/`api.post` を直接呼ぶ :112・:133・:146） | 各ファイル |
| F6 | `ReviewRegisterProductForm` の `exclude_keywords` は固定で `""`（:146）。除外ワードの欄が無い | 同 :136-147 |
| F7 | 細分類の絞り込み・印の判定は `frontend/src/features/tcg-product-import/productDetailModel.ts` にある（`formatOptionsFor`・`formatAfterWorkChange`・`blankConfirmable`・`blankCodeOf`・`missingFields`・`FormatOption`・`BlankCode`）。機能をまたぐ import を禁じる lint は無い | 同 :7-11・:50-75、`frontend/eslint.config.js:120-131` |
| F8 | 文言 `productDetail.notFound`（「{{field}}：調べたが存在しない」）・`productDetail.formatNeedsWork`（「先に作品を選んでください」）と、9項目の名前 `productDetail.japanese_title` ほか（日本語名・英語名・型番・発売日・検索キーワード・除外キーワード・作品・細分類・商品区分）は既にある | `frontend/src/locales/ja.json`・`en.json` の `productDetail` |
| F9 | `Callout` は `variant="info"` で `role="status"`（`warning` は `role="alert"`）。`Checkbox` は `label`（t() 済み）・`size`・input の属性を受ける。`AsyncCombobox` は `disabled` を受ける | `frontend/src/components/Callout.tsx:25-33`・`Checkbox.tsx:16-26`・`AsyncCombobox.tsx:23-30` |
| F10 | `ProductMasterDrawer.test.tsx` は `input[list]` の順で 4 分類を入れる（`fillLookups`）。`.pmd-field input:not([type=checkbox])` を 8 個と数える試験と、`getByRole("checkbox")` で1つだけの印を押す試験がある | 同 :56-61・:81-92・:110-122 |

### 2-2. 設計の細部（Opus の技術判断）

- D1 判定は `productDetailModel.ts` の関数をそのまま使う（判定を2か所に書かない）。`RegistrationValues` を `Draft` と同じ項目の形にし、`missingFields(values)` に渡せるようにする
- D2 送る形の変換（`product_format_id` の `""` → `null`、数字の文字列 → 数）は `reviewActions.ts` の1か所（`registrationBody`）で行い、2つの入口はこの関数を通す（API の型と送る形は reviewActions.ts だけに置く、の方針どおり）
- D3 細分類は作品を選ぶまで押せない（「先に作品を選んでください」）。選択肢は選んだ作品に紐づくものだけ。作品を変えて紐づかなくなったら細分類を空に戻す
- D4 印は値が入っている項目には付けられない（押せない）。値を入れたら、その項目の印を外す（便2b-1 と同じ）
- D5 案内は `Callout`（info）1つで「まだ入っていない項目：…」と 9 項目の名前（`productDetail.*`）を並べる。保存は止めない
- D6 `ReviewRegisterProductForm` の除外ワードは検索キーワードと同じく 1 行 1 語（`joinKeywordLines`）。`RegistrationSection` の除外ワード欄は今のまま（入力をそのまま送る）

## 3. 触るファイル

1. `backend/app/routers/tcg_product_master.py`
2. `backend/tests/test_tcg_product_master.py`
3. `frontend/api-contract/openapi.json`
4. `frontend/src/features/tcg-analysis-review/reviewActions.ts`
5. `frontend/src/features/tcg-analysis-review/ReviewRegisterProductForm.tsx`
6. `frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx`
7. `frontend/src/locales/ja.json`
8. `frontend/src/locales/en.json`
9. `frontend/src/features/tcg-analysis-review/ReviewRegisterProductForm.test.tsx`
10. `frontend/src/features/tcg-analysis-review/ProductMasterDrawer.test.tsx`
11. `frontend/src/features/tcg-analysis-review/reviewActions.test.ts`
12. `docs/handoff/master-register-required-fields/card-bin2b3.md`（このカード）

## 4. 実装

### 4-1. バックエンド

(a) `tcg_product_master.py` の `class LookupOption` の直後に足し、`RegistrationFormResponse` の `lookups` の型を置き換える:

```python
class FormatLookupOption(BaseModel):
    """ADR-1020: 細分類の選択肢。紐づくゲーム（作品）の id を落とさない"""
    id: str
    name: str
    is_active: bool
    game_ids: list[str]


class RegistrationLookups(BaseModel):
    product_kind_id: list[LookupOption]
    work_id: list[LookupOption]
    manufacturer_id: list[LookupOption]
    product_category_id: list[LookupOption]
    product_format_id: list[FormatLookupOption]
```

```python
class RegistrationFormResponse(BaseModel):
    item: RegistrationFormItem
    lookups: RegistrationLookups
```

(b) 試験の前提データ `_FORM_DATA`（`test_tcg_product_master.py:30` 付近）の `lookups` に、まだ無いキー（`product_kind_id`・`work_id`・`manufacturer_id`・`product_category_id`・`product_format_id` のうち欠けているもの）を足す。足す値は `[]`、`product_format_id` は `[{"id": "7", "name": "Box", "is_active": True, "game_ids": ["2"]}]`。既存の値は変えない。

(c) 同じファイルの `test_registration_form_ok` の直後に1本足す:

```python
async def test_registration_form_keeps_format_games(super_admin_override):
    """ADR-1020: 細分類の is_active と game_ids が応答に残る"""
    from app.main import app
    with patch(
        "app.routers.tcg_product_master.fetch_registration_form",
        new=AsyncMock(return_value=_FORM_DATA),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.get(
                "/api/v1/tcg/products/registration-form",
                params={
                    "extraction_item_id": "aaaaaaaa-0000-0000-0000-000000000001",
                    "source_message_id": "bbbbbbbb-0000-0000-0000-000000000001",
                },
            )
    assert r.status_code == 200
    assert r.json()["lookups"]["product_format_id"] == [
        {"id": "7", "name": "Box", "is_active": True, "game_ids": ["2"]}
    ]
```

(d) `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b3/backend && ENVIRONMENT=test /private/tmp/claude-501/py312-openapi/bin/python -m tools.export_openapi ../frontend/api-contract/openapi.json` を実行し、差分をコミットする（venv が無ければ §6）。

### 4-2. `reviewActions.ts`

(a) 冒頭の import 群に足す:

```ts
import type { BlankCode, FormatOption } from "../tcg-product-import/productDetailModel";
```

(b) `export type RegistrationForm = ...` と `export type RegistrationValues = ...` を置き換える:

```ts
export type RegistrationLookupKey = "product_kind_id" | "work_id" | "manufacturer_id" | "product_category_id";

export type RegistrationForm = {
  item: { extraction_item_id: string; source_message_id: string; raw_name: string };
  /** ADR-1020: 細分類は紐づくゲーム（game_ids）付き */
  lookups: Record<RegistrationLookupKey, LookupOption[]> & { product_format_id: FormatOption[] };
};

export type RegistrationValues = {
  product_kind_id: string;
  work_id: string;
  manufacturer_id: string;
  product_category_id: string;
  mark: string;
  japanese_title: string;
  english_title: string;
  release_date: string;
  search_keywords: string;
  exclude_keywords: string;
  /** ADR-1020: 細分類（未選択は ""） */
  product_format_id: string;
  /** ADR-1020: 「調べたが存在しない」の印 */
  blank_confirmations: BlankCode[];
};
```

(c) `checkProductDuplicates` の直前に足し、`checkProductDuplicates` と `createProduct` の本文を `registrationBody` を使う形にする:

```ts
/** 登録・確認で送る body。細分類は未選択なら null、選んでいれば数にする（ADR-1020） */
export function registrationBody(item: ReviewActionTarget, values: RegistrationValues) {
  return {
    extraction_item_id: item.extraction_item_id,
    source_message_id: item.source_message_id,
    ...values,
    product_format_id: values.product_format_id ? Number(values.product_format_id) : null,
  };
}

/** 似た商品がないか確認する */
export function checkProductDuplicates(item: ReviewActionTarget, values: RegistrationValues) {
  return api.post<{ candidates: DupCandidate[] }>("/tcg/products/check-duplicates", registrationBody(item, values));
}

/** 商品マスタに登録する。force=true は「似た商品を確認済みで新規登録」 */
export function createProduct(item: ReviewActionTarget, values: RegistrationValues, force: boolean) {
  return api.post<CreateProductResult>("/tcg/products", { ...registrationBody(item, values), force });
}
```

### 4-3. `ReviewRegisterProductForm.tsx`

(a) import: `import { Callout } ...` の直後に `import { Checkbox } from "../../components/Checkbox";` を足す。`import "./review-fix-wizard.css";` の直前に足す:

```ts
import {
  formatAfterWorkChange,
  formatOptionsFor,
  missingFields,
  type BlankCode,
} from "../tcg-product-import/productDetailModel";
```

(b) state: `const [keywordsText, ...]` の直後に足す:

```ts
  // ADR-1020: 細分類・除外ワード・「調べたが存在しない」の印
  const [format, setFormat] = useState<AsyncComboboxOption | null>(null);
  const [excludeText, setExcludeText] = useState("");
  const [blanks, setBlanks] = useState<BlankCode[]>([]);
```

(c) `values()` の `exclude_keywords: "",` を次の3行に置き換える:

```ts
    exclude_keywords: joinKeywordLines(excludeText),
    product_format_id: format?.value ?? "",
    blank_confirmations: blanks,
```

(d) `invalidateCheck` の直後に足す:

```ts
  /** 値を入れたら、その項目の「調べたが存在しない」を外す（ADR-1020） */
  const clearBlankIfFilled = (code: BlankCode, value: string) => {
    if (value.trim()) setBlanks((current) => current.filter((item) => item !== code));
  };

  const toggleBlank = (code: BlankCode, checked: boolean) => {
    setBlanks((current) => (checked ? [...current.filter((item) => item !== code), code] : current.filter((item) => item !== code)));
    invalidateCheck();
  };
```

(e) `const lookups = form?.lookups ?? {};` を `const lookups = form?.lookups;` にし、`const options = lookups[key] ?? [];` を `const options = lookups?.[key] ?? [];` にする。その直後に足す:

```ts
  const formatChoices = formatOptionsFor(lookups?.product_format_id ?? [], selected.work_id?.value ?? "");
  const missingNow = missingFields(values());
  const blankBox = (code: BlankCode, value: string, labelKey: string) => (
    <Checkbox
      size="sm"
      label={t("productDetail.notFound", { field: t(labelKey) })}
      checked={blanks.includes(code)}
      disabled={busy || value.trim() !== ""}
      onChange={(event) => toggleBlank(code, event.target.checked)}
    />
  );
```

(f) 4分類の `AsyncCombobox` の `onSelect` を次にする（作品を変えたら、紐づかない細分類を空に戻す）:

```tsx
              onSelect={(option) => {
                setSelected((current) => ({ ...current, [key]: option }));
                setMissing((current) => current.filter((missingKey) => missingKey !== key));
                if (key === "work_id") {
                  setFormat((current) =>
                    current && formatAfterWorkChange(lookups?.product_format_id ?? [], option.value, current.value) ? current : null,
                  );
                }
                invalidateCheck();
              }}
```

(g) `SELECT_FIELDS.map(...)` の閉じ `})}` の直後（日本語名の `TextField` の前）に、細分類の欄を足す:

```tsx
      <div className="comp-field comp-field--full">
        <label htmlFor={`review-register-${item.extraction_item_id}-product_format_id`} className="comp-field__label">
          {t("reviewItem.wizard.register.format")}
        </label>
        <AsyncCombobox
          id={`review-register-${item.extraction_item_id}-product_format_id`}
          ariaLabel={t("reviewItem.wizard.register.format")}
          value={format?.label ?? ""}
          disabled={busy || !selected.work_id}
          loadOptions={(query) => filterLookup(formatChoices, query)}
          debounceMs={searchDebounceMs}
          onSelect={(option) => {
            setFormat(option);
            invalidateCheck();
          }}
          noResultsText={t("needsReview.inline.noResults")}
          loadingText={t("common.loading")}
          errorText={t("needsReview.inline.searchError")}
        />
        {!selected.work_id && <p className="comp-field__hint">{t("productDetail.formatNeedsWork")}</p>}
      </div>
```

(h) 英語名・記号・発売日の `TextField` の `onChange` に、`invalidateCheck();` の前で `clearBlankIfFilled("name_en", event.target.value);`（英語名）・`clearBlankIfFilled("mark", event.target.value);`（記号）・`clearBlankIfFilled("release_date", event.target.value);`（発売日）を足す。各 `TextField` の直後にそれぞれ `{blankBox("name_en", englishTitle, "reviewItem.wizard.register.englishTitle")}`・`{blankBox("mark", mark, "reviewItem.wizard.register.mark")}`・`{blankBox("release_date", releaseDate, "reviewItem.wizard.register.releaseDate")}` を足す。

(i) 検索キーワードの `Textarea` の直後に、除外ワードの欄と印を足す:

```tsx
      <Textarea
        size="sm"
        label={t("reviewItem.wizard.register.excludeKeywords")}
        fullWidth
        value={excludeText}
        disabled={busy}
        onChange={(event) => {
          setExcludeText(event.target.value);
          clearBlankIfFilled("exclude_keywords", event.target.value);
          invalidateCheck();
        }}
      />
      {blankBox("exclude_keywords", excludeText, "reviewItem.wizard.register.excludeKeywords")}
```

(j) `{errorNotice && <Callout variant="warning" title={errorNotice} />}` の直前に、案内を足す:

```tsx
      {missingNow.length > 0 && (
        <Callout
          variant="info"
          title={t("reviewItem.wizard.register.missingFields", {
            fields: missingNow.map((field) => t(`productDetail.${field}`)).join(t("reviewItem.wizard.register.listSeparator")),
          })}
        />
      )}
```

### 4-4. `ProductMasterDrawer.tsx`（`RegistrationSection` と `SearchSelect` の型だけ）

(a) import を次にする（`api` は他の節が使うので残す）:

```ts
import { Callout } from '../../components/Callout';
```
を `import { Checkbox } ...` の直前に足し、`./reviewActions` の import に `checkProductDuplicates, createProduct, fetchRegistrationForm,` を足す。その直後に足す:

```ts
import {
  blankCodeOf,
  blankConfirmable,
  formatAfterWorkChange,
  formatOptionsFor,
  missingFields,
  type BlankCode,
} from '../tcg-product-import/productDetailModel';
```

(b) `// ── 共通 UI 部品` の直前に足す:

```ts
type TextKey = Exclude<keyof RegistrationValues, 'blank_confirmations'>;
```

`SearchSelect` の `lookupKey: keyof RegistrationValues;` と `onChange: (key: keyof RegistrationValues, value: string) => void;` の `keyof RegistrationValues` を `TextKey` にする（中身は変えない）。

(c) `RegistrationSection` の `useState<RegistrationValues>({...})` に `product_format_id: '',` と `blank_confirmations: [],` を足す。

(d) `setValue` を置き換え、直後に `toggleBlank` を足す:

```ts
  const formats = form?.lookups.product_format_id ?? [];
  const setValue = (key: TextKey, value: string) => {
    setValues((c) => {
      const next = { ...c, [key]: value };
      // ADR-1020: 値を入れたら、その項目の「調べたが存在しない」を外す。作品を変えたら紐づかない細分類を空に戻す
      const code = blankCodeOf(key);
      if (code && value.trim()) next.blank_confirmations = c.blank_confirmations.filter((x) => x !== code);
      if (key === 'work_id') next.product_format_id = formatAfterWorkChange(formats, value, c.product_format_id);
      return next;
    });
    setCandidates([]);
    setConfirmed(false);
  };

  const toggleBlank = (code: BlankCode, checked: boolean) => {
    setValues((c) => ({
      ...c,
      blank_confirmations: checked
        ? [...c.blank_confirmations.filter((x) => x !== code), code]
        : c.blank_confirmations.filter((x) => x !== code),
    }));
    setCandidates([]);
    setConfirmed(false);
  };
```

`formats` は `form` の state 宣言より後に置く。

(e) `useEffect` の `api.get<RegistrationForm>(...)` を `fetchRegistrationForm(item)` にする（`params` の行は消す。`.then`・`.catch` の中身は変えない）。`checkDuplicates` の `api.post<{ candidates: DupCandidate[] }>('/tcg/products/check-duplicates', {...})` を `checkProductDuplicates(item, values)` に、`save` の `api.post<...>('/tcg/products', {...})` を `createProduct(item, values, confirmed)` にする（`.then`・`.catch` の中身は変えない）。

(f) `optionName` を置き換える:

```ts
  const optionName = (key: 'product_kind_id' | 'work_id' | 'manufacturer_id' | 'product_category_id' | 'product_format_id') => {
    const list: LookupOption[] = form?.lookups[key] ?? [];
    return list.find((o) => o.id === values[key])?.name || t('tcgAnalysisReview.productMasterDrawer.unselected');
  };
  const missingNow = missingFields(values);
  const blankLabels: Record<BlankCode, string> = {
    name_en: 'fieldEnglishTitle', mark: 'fieldMark', release_date: 'fieldReleaseDate', exclude_keywords: 'fieldExcludeKeywords',
  };
```

(g) `fieldCategory` の `SearchSelect` の直後（5つ目の `input[list]` になる位置）に足す:

```tsx
            <SearchSelect key={`format-${values.work_id}`} label={t('tcgAnalysisReview.productMasterDrawer.fieldFormat')} lookupKey="product_format_id" options={formatOptionsFor(formats, values.work_id)} value={values.product_format_id} onChange={setValue} />
```

（`key` は作品が変わったときに入力欄の文字を消すため）

(h) 除外キーワードの `label` の閉じ `</label>` の直後（`.pmd-fields` の `div` の中）に、印を足す:

```tsx
            {blankConfirmable.map(([code, field]) => (
              <Checkbox
                key={code}
                size="sm"
                label={t('productDetail.notFound', { field: t(`tcgAnalysisReview.productMasterDrawer.${blankLabels[code]}`) })}
                checked={values.blank_confirmations.includes(code)}
                disabled={Boolean(values[field].trim())}
                onChange={(e) => toggleBlank(code, e.target.checked)}
              />
            ))}
```

(i) 確認欄の `fieldCategory` の `<p>` の直後に `<p>{t('tcgAnalysisReview.productMasterDrawer.fieldFormat')}: {optionName('product_format_id')}</p>` を足す。`</section>`（確認欄の閉じ）の直後に足す:

```tsx
          {missingNow.length > 0 && (
            <Callout
              variant="info"
              title={t('reviewItem.wizard.register.missingFields', {
                fields: missingNow.map((field) => t(`productDetail.${field}`)).join(t('reviewItem.wizard.register.listSeparator')),
              })}
            />
          )}
```

(j) `RegistrationSection` で使わなくなった import（`RegistrationForm`・`DupCandidate` など）は、他で使っていなければ外す。ボタンを押せなくする条件（`required`・`candidates.length && !confirmed`）は変えない。

### 4-5. 文言（ja と en で同じキー）

`reviewItem.wizard.register` の中、`"keywords"` の後に:

| キー | ja | en |
|---|---|---|
| `format` | 細分類 | Format |
| `excludeKeywords` | 除外キーワード（1行に1つ） | Exclusion keywords (one per line) |
| `missingFields` | まだ入っていない項目：{{fields}}。入力するか、存在しないときは「調べたが存在しない」に印を付けてください。 | Not entered yet: {{fields}}. Enter them, or tick “checked, none exists” if there is none. |
| `listSeparator` | 、 | , （カンマと半角空白） |

`tcgAnalysisReview.productMasterDrawer` の中、`"fieldCategory"` の後に:

| キー | ja | en |
|---|---|---|
| `fieldFormat` | 細分類 | Format |

ハードコードの日本語を tsx に書かない。

### 4-6. 試験

`ReviewRegisterProductForm.test.tsx`:
- 前提データ `form.lookups` に `work_id` の2件目 `{ id: "9", name: "Yugioh" }` と、`product_format_id: [{ id: "7", name: "Box Set", is_active: true, game_ids: ["2"] }, { id: "8", name: "Pack Set", is_active: true, game_ids: ["9"] }]` を足す
- `BODY` に `product_format_id: ""` と `blank_confirmations: []` を足す（既存の試験の期待はこれで合う）

| # | 名前 | 中身 |
|---|---|---|
| 1 | `asks for the work first and offers only formats of that work` | 描画直後、`Format` の combobox が disabled で `Choose a work first` が出る。`Title / series` で Pokemon を選び、`Format` に `set` と入れる → option `Box Set` があり、`Pack Set` が無い |
| 2 | `clears the format when the work changes to one it does not belong to` | Pokemon → `Box Set` を選んだ後、`Title / series` で Yugioh を選ぶ → `Format` の combobox の値が `""` |
| 3 | `sends the format, the exclusion keywords and the blank marks` | 必須を入れ、`Format` で `Box Set`、除外キーワードに `a\nb`、`English name: checked, none exists` の印を押す → 確認・登録 → `createProduct` が `(item, { ...BODY, product_format_id: "7", exclude_keywords: "a,b", blank_confirmations: ["name_en"] }, false)` |
| 4 | `lists what is still missing and drops a field once it is marked or filled` | 描画直後の `role="status"` の文に `English name` と `Exclusion keywords` を含む。英語名の印を押すと `English name` が消える。英語名に `X` を入れると印が外れて押せなくなる |

`ProductMasterDrawer.test.tsx`:
- 前提データ `form.lookups` に `product_format_id: [{ id: "7", name: "Box Set", is_active: true, game_ids: ["w1"] }, { id: "8", name: "Pack Set", is_active: true, game_ids: ["w9"] }]` を足す
- `uses the shared control classes ...` の `expect(inputs.length).toBe(8);` を `9` にする（細分類の欄が1つ増えるため）
- `asks for confirmation when duplicates are found` の `screen.getByRole("checkbox")` を `screen.getByRole("checkbox", { name: "重複候補を確認しました（新規商品です）" })` にする（印の4つが増えるため）

| # | 名前 | 中身 |
|---|---|---|
| 5 | `offers only the formats of the chosen work and sends the format and blank marks` | 日本語で描画し `fillLookups()`。`#lookup-product_format_id` の datalist の option が `Box Set` だけ。5つ目の `input[list]` に `Box Set` を入れ、`英語タイトル：調べたが存在しない` の印を押し、`商品マスタに登録` を押す → `api.post` が `("/tcg/products", expect.objectContaining({ product_format_id: 7, blank_confirmations: ["name_en"], force: false }))` で呼ばれる |

`reviewActions.test.ts`:

| # | 名前 | 中身 |
|---|---|---|
| 6 | `sends the format id as a number, or null when none is chosen` | `createProduct(item, { ...values, product_format_id: "7" }, false)` の body の `product_format_id` が `7`、`checkProductDuplicates(item, { ...values, product_format_id: "" })` の body の `product_format_id` が `null`（`values` は `RegistrationValues` を全部埋めた試験用の値） |

バックエンドの試験は §4-1 (c) の1本（7本目）。

## 5. 確かめ方（担当が実行し、出力を報告に貼る）

5-1. 型と lint: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b3/frontend && npx tsc --noEmit -p tsconfig.json 2>&1 | tail -20` と `npx eslint src/features/tcg-analysis-review/reviewActions.ts src/features/tcg-analysis-review/ReviewRegisterProductForm.tsx src/features/tcg-analysis-review/ProductMasterDrawer.tsx src/features/tcg-analysis-review/ReviewRegisterProductForm.test.tsx src/features/tcg-analysis-review/ProductMasterDrawer.test.tsx src/features/tcg-analysis-review/reviewActions.test.ts 2>&1 | tail -20` がどちらもエラー 0（`src/api/generated/schema.d.ts` が無くて落ちるときは、先に `npm run generate:api-types 2>&1 | tail -3`。生成物はコミットしない）。

5-2. 試験の名前: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b3 && git diff origin/main -- frontend/src/features backend/tests | grep -nE "^\+\s*(it\(|async def test_|def test_)" | head -10` の出力（7 行、名前が §4-6 と §4-1 (c) のとおり）。

5-3. 画面の試験: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b3/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/features/tcg-analysis-review/ 2>&1 | tail -30` が全部合格（このフォルダの既存の試験も含む）。

5-4. バックエンドの試験: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b3/backend && /private/tmp/claude-501/py312-openapi/bin/python -m pytest tests/test_tcg_product_master.py -q -p no:cacheprovider 2>&1 | tail -20` が全部合格（DB の要る試験が skip になるときは「手元では skip・CI で実行」と書く。pytest が venv に無ければ §6）。

5-5. 金型と i18n: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b3/frontend && npm run check:i18n-missing-keys 2>&1 | tail -10` が合格。`cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b3 && git diff origin/main -- frontend/src/features | grep -nE "^\+.*(<input|<select|#[0-9a-fA-F]{3,6}\b|style=)" | head -10` が 0 行。`git diff origin/main -- frontend/src/features | grep -nP "^\+(?!.*//).*[\x{3040}-\x{30ff}\x{4e00}-\x{9fff}]" | grep -v "\.test\.tsx" | head -10` が 0 行（コメント以外の日本語なし。試験ファイルは既存の除外コメントの範囲）。

5-6. API 契約: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b3 && git diff origin/main --stat -- frontend/api-contract/openapi.json | tail -2` が 1 ファイルの変更、`git diff origin/main -- frontend/api-contract/openapi.json | grep -c "FormatLookupOption\|RegistrationLookups"` が 1 以上。

5-7. 差分: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b3 && git diff origin/main --stat | tail -15` が §3 の 12 ファイルだけ。

5-8. PR の CI は担当が待たない。PR を作ったら URL を報告して終える。

## 6. 分岐ごとの対処

- §10 手順1 で、origin/main の `frontend/src/features/tcg-product-import/productDetailModel.ts` に `formatAfterWorkChange` の文字が無い → BLOCKED:（作業を始めない）
- §4 の目印が実物と違う → 実物の該当行を貼り、同じ意味・同じ位置に合わせて書く。見つからなければ NEEDS_DECISION:
- `/private/tmp/claude-501/py312-openapi/bin/python` が無い、または pytest が入っていない → `ls -1d /private/tmp/claude-501/py312-openapi` と `/private/tmp/claude-501/py312-openapi/bin/python -m pytest --version 2>&1 | tail -2` の出力を貼る。openapi の再生成ができないなら BLOCKED:（3.12 以外の Python で作らない）。pytest だけ無いなら「手元では未実行・CI で実行」と書いて続ける
- `_FORM_DATA` に足しても既存の試験の期待（`product_kind_id` の1件目が `TCG` など）が変わる → 既存の値を変えずに足す方法を原文付きで報告し NEEDS_DECISION:
- `missingFields(values)` が型で通らない → 落ちた行を貼る。`RegistrationValues` 側の型だけで合わせる。`productDetailModel.ts` は変えない。直せなければ BLOCKED:
- husky や CI の自動検査が落ちる → 検査名と原文を貼る。迂回（`--no-verify` など）しない

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 登録フォームの応答に細分類の使えるゲームが残る | 試験 7（バックエンド）、§8 の本番確認 |
| 細分類は作品を選んでから、その作品に紐づくものだけ選べる | 試験 1・5 |
| 作品を変えて紐づかなくなった細分類は空に戻る | 試験 2 |
| 細分類・除外ワード・印が登録の要求に入る | 試験 3・5・6 |
| まだ入っていない項目が案内され、印か値で消える | 試験 4 |
| 保存は止めない（既存の5項目の確認だけ） | 既存の試験（`marks every empty required field ...` が 5 のまま・`registers with no candidates ...` が合格） |
| 文言は ja/en 同じキー、金型だけを使う | §5-5 |

## 8. 反映の前後（Opus が行う。担当はしない）

- CI の緑を確かめ、差分を審査し、「確認済み」のコメントを残してマージ → deploy の成功を Actions の記録で確かめる
- 反映後、本番の `GET /api/v1/tcg/products/registration-form` が未ログインで 401 のまま（受け口が生きている）、本番の画面 JS に新しい文言（`Not entered yet:`）が入っていること、紐づけ表が 69 行のままであることを読み取りで確かめる
- 生出力は /tmp/CC報告ファイル/master-required-fields/bin2b3/ に置く

## 9. 戻し方

- この PR の revert を main にマージ（画面と応答の形が元に戻る。データは変わらない）

## 10. PR

手順1 前提が main にあることを確かめ、新しい作業場所を作る
    cd /Users/tanizawashingo/salesanchor && git fetch -q origin && git grep -c "formatAfterWorkChange" origin/main -- frontend/src/features/tcg-product-import/productDetailModel.ts
期待する出力 1 以上（0 なら §6 の1つ目）
    cd /Users/tanizawashingo/salesanchor && bash scripts/new-worktree.sh release/master-register-required-fields-bin2b3 --claude 2>&1 | tail -5
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b3 && git status -sb | head -3 && git log -1 --oneline
期待する出力 作業場所が origin/main の先頭から作られている。以下のコマンドの作業場所は /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b3
    このカードを /tmp/CC報告ファイル/master-required-fields/bin2b/card-bin2b3.md から Read し、Write ツールで `/Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b3/docs/handoff/master-register-required-fields/card-bin2b3.md` に同じ内容で置く。`cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b3/frontend && ls node_modules | head -1` で依存が無ければ `npm ci 2>&1 | tail -5`

手順2 §4 を Write/Edit ツールで実装し、§5-1〜5-7 を実行する

手順3 commit と push
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b3 && git add backend/app/routers/tcg_product_master.py backend/tests/test_tcg_product_master.py frontend/api-contract/openapi.json frontend/src/features/tcg-analysis-review/reviewActions.ts frontend/src/features/tcg-analysis-review/ReviewRegisterProductForm.tsx frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx frontend/src/locales/ja.json frontend/src/locales/en.json frontend/src/features/tcg-analysis-review/ReviewRegisterProductForm.test.tsx frontend/src/features/tcg-analysis-review/ProductMasterDrawer.test.tsx frontend/src/features/tcg-analysis-review/reviewActions.test.ts docs/handoff/master-register-required-fields/card-bin2b3.md
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b3 && git commit -m "feat: ADR-1020便2b-3 解析レビューの登録に細分類・除外ワード・印を追加"
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b3 && git push -q -u origin release/master-register-required-fields-bin2b3 && git log -1 --oneline && git log origin/release/master-register-required-fields-bin2b3 -1 --oneline
期待する出力 2 つの git log が同じハッシュ

手順4 PR を作る
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b3 && gh auth status 2>&1 | grep -c "Active account: true"

- 名義が `shingo-cc` であることを確かめる
- 本文は Write ツールで英字だけのパスのファイル（/private/tmp/claude-501/bin2b3-pr-body.md）に作り、`scripts/dev/validate-pr-body.sh` に標準入力で渡して exit 0 を確かめる（2 分以上かかるので timeout を長めにする）
- PR は `scripts/gh-pr-create-safe.sh` に本文ファイルを絶対パスで渡して作る（`$変数` を使わない）。base は main。ready で作る（下書きにしない）。担当はマージしない
- 作成後に `.pr-number` と `gh pr list --head release/master-register-required-fields-bin2b3 --json number` の一致を確かめる
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に recon（docs/handoff/master-register-required-fields/recon.md）・設計（docs/handoff/master-register-required-fields/design.md）・このカード・ADR-1020・ADR-027 を書く。区分は M（危険パスなし）。PO承認: に「PO 2026-10-16『y』（KGI G1〜G4・3便）、PO 2026-10-17 チャット『PRマージ、デプロイまで完走させてくれ』（本セッション＝ADR-1020 便2〜便3）」と書く。validate-pr-body.sh が「設計docに参照がない」と ADR を指摘したら、その ADR だけを `対象ADR` から外し、外したことを報告に書く
- `触るファイル:` と `削除するファイル:` は 1 行・カンマ区切り・バッククォートなし・注記なし。触るファイル: は §3 の 12 ファイル。削除するファイル: は既存行を変えたファイル（§3 の 1〜8・10・11。便2b-2 #4415 と同じ書き方）

## 11. 報告

- 完了報告の本文に: 冒頭の受領文／§5-1〜5-7 の出力／PR の URL／生出力のパス（/tmp/CC報告ファイル/master-required-fields/bin2b3/impl/）／判断を要した点（事実のみ）
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか

## 12. 委任の定型

- sleep しない（待ちは Opus が行う）
- ファイルの作成と編集は Write/Edit ツールで行う（ヒアドキュメントで書かない）
- PR を作る前に `scripts/dev/validate-pr-body.sh` で exit 0 を確かめる
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える
- 登録ルールのフック（master-register-rules-guard）に止められたら、言い換えずに報告して終える。ack の行は書かない
- Bash のコマンドに削除の SQL の語（大文字の削除文）を書かない

## 13. 報告欄（担当が追記）

（未記入）

END OF CARD
