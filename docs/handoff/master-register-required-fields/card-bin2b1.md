<!-- rules-ack: 607cd6e7 -->
# 実装カード 便2b-1 — 商品詳細の画面で細分類と「調べたが無い」の印を扱う（ADR-1020）

> この文書は何か：共用商品マスタの9項目必須化（ADR-1020）の便2b-1（画面だけ）の作業指示書です。商品マスタ画面の「商品詳細・編集」ドロワー（新規作成と編集の両方）に、①細分類の選択欄（選んだ作品に紐づく細分類だけ）、②英語名・型番・発売日・除外キーワードの「調べたが無い」のチェック欄、③9項目のうち未入力の欄への「未入力」の案内、を足します。**保存を止めるのは便3**（この便では止めない）。細分類マスタ画面は便2b-2、解析レビューからの登録は便2b-3、CSV は便2c。

- 設計: docs/handoff/master-register-required-fields/design.md §4「便2 の分け方」・§7（KGI と3便は PO 承認 2026-10-16「y」）
- 前提の便: 便2a（API が細分類の選択肢 `lookups.product_format_id`（`game_ids` 付き）と、詳細の `product.blank_confirmations` を返す）が **main にマージ済み・本番反映済み**であること。§10 手順1 で確かめる
- 登録ルール: docs/specs/product-master/registration-rules.md
- 対象ADR: ADR-1020（本テーマ）、ADR-027（i18n。文言は `t()` だけ・ja/en 同じキー）、ADR-144（金型。`Select`・`TextField`・`Textarea`・`Checkbox` を使い、生の input/select・色の直値を書かない）、ADR-156（分類の3層）
- 状態: 設計は Opus 自己審査 APPROVE。§2-2 の細部は Opus の技術判断（設計の目的・範囲は変えない）
- 危険便: いいえ（`migrations/`・`deploy.yml`・本番 `scripts/` を含まない）。担当はマージしない
- 担当: 実装 Sonnet／コード審査・マージ・反映確認 Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（下書きにしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（商品詳細ドロワーだけ。細分類マスタ画面・解析レビュー・CSV・保存の停止は別便） |
| 5 | 起点と作業場所を明示 | ○（§10 手順1。origin/main から新しい作業場所を作る） |
| 6 | 書式は実例で示した | ○（§4 に完成形のコード） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-2） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実物から | ○（行番号は origin/main 449a77166 の実物で確かめた） |
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

作業を始める前に、報告の冒頭へ「本報告はカード ADR-1020 便2b-1 の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. `frontend/src/features/tcg-product-import/productDetailModel.ts`: 下書きに細分類と印を足す。細分類の絞り込みと未入力の判定の関数（§4-1）
2. `frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx`: 細分類の選択欄・印のチェック欄・未入力の案内・作成の送信に細分類と印（§4-2）
3. `frontend/src/locales/ja.json` と `frontend/src/locales/en.json` の `productDetail` に 5 キー（§4-3）
4. `frontend/src/features/tcg-product-import/TcgProductDetailDrawer.test.tsx`: 既存の試験の下ごしらえを新しい形に合わせ、試験を 7 本足す（§4-4）
5. このカードを `docs/handoff/master-register-required-fields/card-bin2b1.md` に置く

入れない:
- 保存を止めること（必須の欠けで送信しない・422 を返す）は便3
- 細分類マスタ画面（`ProductFormatsMasterPanel.tsx`）は便2b-2
- 解析レビューからの登録（`features/tcg-analysis-review/`）は便2b-3
- CSV（便2c）、バックエンド、`frontend/api-contract/openapi.json`
- 既存の4つの分類欄（`classificationFields`）の動きの変更（`draftFrom` が作品などを文字列に変えない点も今のまま）

## 2. 前提の事実と設計の細部

### 2-1. 事実（origin/main 449a77166 と便2aのカード）

| # | 事実 | 出典 |
|---|---|---|
| F1 | 詳細保存の受け口は `product_format_id: int \| None` と `blank_confirmations: list[Literal["name_en","mark","release_date","exclude_keywords"]] \| None` を受ける。送ったときだけ使う | `backend/app/routers/tcg_product_import.py:289-290`・`:313-315` |
| F2 | 印を送ると、その商品の印は「空の項目 ∩ 送った印」に置き換わる。送らなければ値の入った項目の印だけが消える | `backend/app/services/tcg_product_master_svc.py` の `save_blank_confirmations`（`:88-125`） |
| F3 | 新規作成の受け口 `POST /tcg/products/create` は `product_format_id: int \| None` と `blank_confirmations`（既定は空）を受ける | `backend/app/routers/tcg_product_import.py:385-386` |
| F4 | 便2aで、詳細の `product` に `blank_confirmations`（項目名の配列）が、`lookups` と `GET /tcg/products/lookups` に `product_format_id`（`{id: 文字列, name, is_active, game_ids: 文字列の配列}`）が入る。`product.product_format_id` は数（`row_to_json`）か null | card-bin2a.md D4・D5、`backend/app/services/tcg_product_detail_svc.py:48-60` |
| F5 | `buildUpdateBody` は `...draft` を広げて送る。除外ワードを足す処理（`addExcludeWord`）も同じ関数で詳細を保存する | `productDetailModel.ts:39-47`・`:55-63` |
| F6 | 金型の `TextField`・`Select`・`Textarea` は `error` を渡すと `role="alert"` の文を出す。`helperText` は役割なし | `frontend/src/components/TextField.tsx:98-101`、`Select.tsx:173-176`、`Textarea.tsx:100-103` |
| F7 | 金型の `Checkbox` は `label`（t 済みの文字列）・`size`（`sm`/`md`/`lg`）・`checked`・`disabled`・`onChange` を受け、`label` 要素で input を包む | `frontend/src/components/Checkbox.tsx:18-26`・`:28-66` |
| F8 | 既存の試験は `findByRole("alert")` で重なりの警告を1つだけ探す | `TcgProductDetailDrawer.test.tsx:25`・`:35` |
| F9 | 商品詳細ドロワーを使う画面は `ProductMasterPanel.tsx:131-132` だけ。`addExcludeWord` は `TcgProductImportPreview.tsx:5` からも呼ばれる | `git grep` の結果 |
| F10 | 新規作成は `tenant_id` を入れずに products に入れる（共用商品になる） | `tcg_product_master_svc.py:490` 付近の INSERT |

### 2-2. 設計の細部（Opus の技術判断）

- D1 未入力の案内は `helperText` で出す（`error` は使わない）。理由: F6・F8。`error` だと未入力の欄ごとに警告の役割が付き、読み上げがうるさく、既存の試験も壊れる。赤字で止めるのは便3で決める
- D2 案内を出すのは共用商品だけ。作成モードは常に（F10）。編集モードは `detail.product.tenant_id` が null か無いとき
- D3 細分類の選択肢は `lookups.product_format_id` のうち `game_ids` に `String(draft.work_id)` を含むものだけ（紐づけ表が正。画面に別の対応表を持たない）。作品が空なら選択欄は使えず、案内「先に作品を選んでください」を placeholder に出す
- D4 作品を変えて、今の細分類が新しい作品に紐づかなくなったら、細分類を空に戻す。編集で開いた古い値が選択肢に無いときは、既存の分類欄と同じ `missingClassification` の選択肢（使えない状態）で表示し、利用者が変えない限りそのまま送る（便2aは、細分類か作品が変わったときだけ照合する）
- D5 印のチェック欄は、値が入っている項目では使えない。値を入れたら、その項目の印は自動で外す
- D6 **印の消失を防ぐ**: 詳細に `blank_confirmations` が配列で無い、または `lookups.product_format_id` が配列で無いときは、`draftFrom` が「Invalid product detail」で止める（読み込みエラーを出し、保存しない）。空の配列とみなして送ると、F2 により保存済みの印を消してしまうため
- D7 編集の保存と除外ワードの追加は、下書きの印（開いたときの値＋利用者の変更）と細分類（数か null）を毎回送る

## 3. 触るファイル

1. `frontend/src/features/tcg-product-import/productDetailModel.ts`
2. `frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx`
3. `frontend/src/locales/ja.json`
4. `frontend/src/locales/en.json`
5. `frontend/src/features/tcg-product-import/TcgProductDetailDrawer.test.tsx`
6. `docs/handoff/master-register-required-fields/card-bin2b1.md`（このカード）

## 4. 実装

### 4-1. `productDetailModel.ts`

(a) `export type Classification = ...` の行の直後に足す:

```ts
/** ADR-1020: 「調べたが無い」の印を付けられる項目（API の項目名 → 下書きの項目名） */
export const blankConfirmable = [
  ["name_en", "english_title"], ["mark", "mark"], ["release_date", "release_date"], ["exclude_keywords", "exclude_keywords"],
] as const;
export type BlankCode = typeof blankConfirmable[number][0];
export type FormatOption = { id: string; name: string; is_active: boolean; game_ids: string[] };
```

(b) `Detail` を次に置き換える（`product` に3つ、`lookups` に細分類を足す）:

```ts
export interface Detail {
  revision: string;
  product: Record<Classification, string | null> & {
    id: string; code: string; japanese_title: string; english_title: string | null;
    mark: string | null; release_date: string | null; search_keywords: string[]; exclude_keywords: string[];
    required_output_value: string | null; category_class: string; is_active: boolean; created_at: string;
    product_format_id: number | string | null; blank_confirmations: string[]; tenant_id?: string | null;
  };
  lookups: Record<Classification, { id: string; name: string; is_active: boolean }[]> & { product_format_id: FormatOption[] };
  code_collisions?: CodeCollision[];
}
```

(c) `Draft` を次に置き換える:

```ts
export type Draft = Record<Classification, string> & {
  japanese_title: string; english_title: string; mark: string; release_date: string;
  search_keywords: string; exclude_keywords: string;
  product_format_id: string; blank_confirmations: BlankCode[];
};
```

(d) `draftFrom` の検査の条件に2つ足し（D6）、返す値に2つ足す。完成形:

```ts
export function draftFrom(result: Detail): Draft {
  const p = result.product;
  if (!/^[0-9a-f]{64}$/.test(result.revision) ||
      typeof p.japanese_title !== "string" || !Array.isArray(p.search_keywords) ||
      !Array.isArray(p.exclude_keywords) ||
      ![...p.search_keywords, ...p.exclude_keywords].every(word => typeof word === "string") ||
      !classificationFields.every(field => Array.isArray(result.lookups?.[field])) ||
      // ADR-1020: 印と細分類の選択肢が無い応答では開かない（空とみなして送ると保存済みの印を消すため）
      !Array.isArray(p.blank_confirmations) || !Array.isArray(result.lookups?.product_format_id)) {
    throw new Error("Invalid product detail");
  }
  return { japanese_title: p.japanese_title, english_title: p.english_title ?? "", mark: p.mark ?? "",
    release_date: p.release_date ?? "", product_kind_id: p.product_kind_id ?? "", work_id: p.work_id ?? "",
    manufacturer_id: p.manufacturer_id ?? "", product_category_id: p.product_category_id ?? "",
    search_keywords: p.search_keywords.join("\n"), exclude_keywords: p.exclude_keywords.join("\n"),
    product_format_id: p.product_format_id == null ? "" : String(p.product_format_id),
    blank_confirmations: blankConfirmable.map(([code]) => code).filter(code => p.blank_confirmations.includes(code)) };
}
```

(e) `buildUpdateBody` の返す値の `product_category_id: ...,` の行の直後に1行足す（D7）:

```ts
    product_format_id: draft.product_format_id ? Number(draft.product_format_id) : null, blank_confirmations: draft.blank_confirmations,
```

(f) `export const words = ...` の行の直後に足す:

```ts
/** 選んだ作品（ゲーム）に紐づく細分類だけを返す。正は product_format_game_links（API の game_ids） */
export const formatOptionsFor = (options: FormatOption[], workId: string) =>
  workId ? options.filter(option => option.game_ids.includes(String(workId))) : [];

/** 作品を変えた後の細分類。新しい作品に紐づかなければ空に戻す */
export const formatAfterWorkChange = (options: FormatOption[], workId: string, formatId: string) =>
  formatOptionsFor(options, workId).some(option => option.id === formatId) ? formatId : "";

/** 下書きの項目名 → 印の項目名（印を付けられない項目は undefined） */
export const blankCodeOf = (field: keyof Draft): BlankCode | undefined =>
  blankConfirmable.find(([, draftField]) => draftField === field)?.[0];

const requiredDraftFields = [
  "japanese_title", "english_title", "mark", "release_date", "search_keywords", "exclude_keywords",
  "work_id", "product_format_id", "product_category_id",
] as const;
export type RequiredDraftField = typeof requiredDraftFields[number];

/** ADR-1020 の9項目のうち、未入力で印も無い項目（案内の表示に使う。便2では保存を止めない） */
export function missingFields(draft: Draft): RequiredDraftField[] {
  return requiredDraftFields.filter(field => {
    if (String(draft[field] ?? "").trim()) return false;
    const code = blankCodeOf(field);
    return !(code && draft.blank_confirmations.includes(code));
  });
}
```

### 4-2. `TcgProductDetailDrawer.tsx`

(a) import: `import { Select } from "../../components/Select";` の直後に `import { Checkbox } from "../../components/Checkbox";` を足す。`./productDetailModel` の import を次に置き換える:

```ts
import {
  addExcludeWord, blankCodeOf, buildUpdateBody, classificationFields, draftFrom, formatAfterWorkChange,
  formatOptionsFor, missingFields, words,
  type AddWordResult, type BlankCode, type Classification, type Detail, type Draft, type FormatOption,
  type RequiredDraftField,
} from "./productDetailModel";
```

(b) 型と空の下書き（16〜22行目）を次に置き換える:

```ts
type LookupOption = { id: string; name: string };
type LookupsMap = Record<Classification, LookupOption[]> & { product_format_id: FormatOption[] };
const emptyDraft: Draft = {
  japanese_title: "", english_title: "", mark: "", release_date: "",
  product_kind_id: "", work_id: "", manufacturer_id: "", product_category_id: "",
  search_keywords: "", exclude_keywords: "", product_format_id: "", blank_confirmations: [],
};
```

(c) 185〜187行目の `const activeLookups ...`（3行）を消し、同じ3行を 47行目 `const isOpen = ...` の直後へ移す（`change` から使うため。中身は変えない）。

(d) `function change(...)`（93〜96行目）を次に置き換え、直後に `toggleBlank` を足す:

```ts
  function change(field: Exclude<keyof Draft, "blank_confirmations">, value: string) {
    setDraft(previous => {
      if (!previous) return previous;
      const next: Draft = { ...previous, [field]: value };
      // ADR-1020: 値を入れた項目の「調べたが無い」の印は外す
      const code = blankCodeOf(field);
      if (code && value.trim()) next.blank_confirmations = previous.blank_confirmations.filter(item => item !== code);
      // 作品を変えて細分類が新しい作品に紐づかなくなったら、細分類を空に戻す
      if (field === "work_id" && activeLookups) {
        next.product_format_id = formatAfterWorkChange(activeLookups.product_format_id, value, previous.product_format_id);
      }
      return next;
    });
    setSaved(false);
  }
  function toggleBlank(code: BlankCode, checked: boolean) {
    setDraft(previous => previous ? {
      ...previous,
      blank_confirmations: checked
        ? [...previous.blank_confirmations.filter(item => item !== code), code]
        : previous.blank_confirmations.filter(item => item !== code),
    } : previous);
    setSaved(false);
  }
```

(e) `saveCreate` の POST の body の `exclude_keywords: words(draft.exclude_keywords).join(","),` の直後に2行足す:

```ts
        product_format_id: draft.product_format_id ? Number(draft.product_format_id) : null,
        blank_confirmations: draft.blank_confirmations,
```

(f) `return <><Drawer ...` の直前（移した `activeLookups` の後、`confirmDiscard` などの関数の後）に足す:

```ts
  // ADR-1020: 共用商品だけ、9項目の未入力を案内する（便2では保存を止めない）
  const shared = mode === "create" || (detail?.product.tenant_id ?? null) === null;
  const missing: RequiredDraftField[] = draft && shared ? missingFields(draft) : [];
  const missingHint = (field: RequiredDraftField) => missing.includes(field)
    ? t(blankCodeOf(field) ? "productDetail.requiredMissingConfirmable" : "productDetail.requiredMissing") : undefined;
  const hintWith = (base: string | undefined, field: RequiredDraftField) => [base, missingHint(field)].filter(Boolean).join(" ") || undefined;
  const formatOptions = draft && activeLookups
    ? formatOptionsFor(activeLookups.product_format_id, draft.work_id).map(option => ({ value: option.id, label: option.name, disabled: false }))
    : [];
  if (draft?.product_format_id && !formatOptions.some(option => option.value === draft.product_format_id)) {
    formatOptions.push({ value: draft.product_format_id, label: t("productDetail.missingClassification", { id: draft.product_format_id }), disabled: true });
  }
  const blankBox = (code: BlankCode, field: RequiredDraftField, label: string) => draft && <Checkbox size="sm"
    label={t("productDetail.notFound", { field: label })} checked={draft.blank_confirmations.includes(code)}
    disabled={saving || Boolean(String(draft[field]).trim())} onChange={event => toggleBlank(code, event.target.checked)} />;
```

(g) フォームの中（214〜231行目）を次の順と形にする。変える行だけ示す。`required`・`maxLength`・`disabled`・`fullWidth`・`onChange` は今のまま残す:

- 日本語名の `TextField` に `helperText={missingHint("japanese_title")}` を足す
- 英語名の `TextField` に `helperText={missingHint("english_title")}` を足し、直後に `{blankBox("name_en", "english_title", t("productDetail.english_title"))}`
- 型番の `TextField` に `helperText={missingHint("mark")}` を足し、直後に `{blankBox("mark", "mark", t("productDetail.mark"))}`
- 発売日の `TextField` に `helperText={missingHint("release_date")}` を足し、直後に `{blankBox("release_date", "release_date", t("productDetail.release_date"))}`
- 分類の `Select`（`classificationFields.map` の中）に `helperText={field === "work_id" || field === "product_category_id" ? missingHint(field) : undefined}` を足す
- 分類の map の直後（検索キーワードの前）に細分類の欄を足す:

```tsx
        {activeLookups && <Select label={t("productDetail.product_format_id")} value={draft.product_format_id} options={formatOptions}
          placeholder={t(draft.work_id ? "productDetail.unset" : "productDetail.formatNeedsWork")}
          helperText={missingHint("product_format_id")}
          onChange={e => change("product_format_id", e.target.value)} disabled={saving || !draft.work_id} fullWidth />}
```

- 検索キーワードの `Textarea` の `helperText` を `helperText={hintWith(t("productDetail.wordsHint"), "search_keywords")}` にする
- 除外キーワードの `Textarea` の `helperText` を `helperText={hintWith(t("productDetail.wordsHint"), "exclude_keywords")}` にし、直後に `{blankBox("exclude_keywords", "exclude_keywords", t("productDetail.exclude_keywords"))}`

(h) `addToThis` の中の `change("exclude_keywords", ...)` はそのまま（(d) で印は自動で外れる）。

### 4-3. 文言（`productDetail` の中、`"create"` の前に足す。ja と en で同じキー）

| キー | ja | en |
|---|---|---|
| `product_format_id` | 細分類 | Format |
| `formatNeedsWork` | 先に作品を選んでください | Choose a work first |
| `notFound` | {{field}}：調べたが存在しない | {{field}}: checked, none exists |
| `requiredMissing` | 未入力です（登録に必要な項目です）。 | Not entered yet (required for registration). |
| `requiredMissingConfirmable` | 未入力です。入力するか、存在しないときは下の「調べたが存在しない」に印を付けてください。 | Not entered yet. Enter a value, or tick "checked, none exists" below if there is none. |

JSON の中の `"` は `\"` と書く。ハードコードの日本語を tsx に書かない。

### 4-4. 試験（`TcgProductDetailDrawer.test.tsx`）

(a) 下ごしらえを新しい形に合わせる（既存の試験の期待値は変えない）:
- 7行目の `lookups` を次にする:
  `const lookups = { product_kind_id: [], work_id: [{ id: "3", name: "Game A", is_active: true }, { id: "4", name: "Game B", is_active: true }], manufacturer_id: [], product_category_id: [], product_format_id: [{ id: "7", name: "Booster Box", is_active: true, game_ids: ["3"] }, { id: "8", name: "Starter Deck", is_active: true, game_ids: ["4"] }] };`
- `detailOf` の `product` に `product_format_id: null, blank_confirmations: [] as string[],` を足す

(b) 末尾に `describe("ADR-1020 format and blank confirmations", ...)` を足し、次の 7 本を書く（名前はこのとおり）:

| # | 名前 | 中身 |
|---|---|---|
| 1 | `offers only formats linked to the chosen work and sends them on create` | 作成モード。`Work` で `3` を選ぶ → `Format` の選択肢に `Booster Box` があり `Starter Deck` が無い。`7` を選び、`English name: checked, none exists` に印、日本語名を入れて submit → `api.post` の body の `product_format_id` が `7`、`blank_confirmations` が `["name_en"]` |
| 2 | `clears the format when the work changes to an unlinked one` | 作成モード。作品 `3`・細分類 `7` → 作品を `4` に変える → `Format` の値が `""` |
| 3 | `unticks and disables the confirmation once a value is entered` | 作成モード。`Model number: checked, none exists` に印 → 型番に `ST01` を入れる → そのチェック欄が `checked` でなく `disabled` |
| 4 | `loads saved format and confirmations in edit mode and resends them` | 編集モード。`routeGet(detailOf(...))` で `work_id: "3"`・`product_format_id: 7`・`blank_confirmations: ["mark"]` → `Format` の値が `"7"`、型番のチェック欄が checked。日本語名を変えて保存 → `api.put` の body の `product_format_id` が `7`、`blank_confirmations` が `["mark"]` |
| 5 | `shows the missing notice without blocking save` | 編集モード。英語名 null・印なし → `Not entered yet. Enter a value` を含む文が出る。日本語名を変えて保存 → `api.put` が 1 回呼ばれる |
| 6 | `refuses to open a detail without blank_confirmations` | 編集モード。`blank_confirmations` を消した詳細 → `Could not load the product details` が出て、`api.put` は呼ばれない |
| 7 | `keeps confirmations and format when adding an exclude word` | `addExcludeWord(42, "fixture")` を直接呼ぶ（`./productDetailModel` から import）。`api.get` は `product_format_id: 7`・`blank_confirmations: ["name_en"]` の詳細 → `api.put` の body の `blank_confirmations` が `["name_en"]`、`product_format_id` が `7` |

編集モードの描画は `render(<TcgProductDetailDrawer productId={42} onClose={vi.fn()} onSaved={vi.fn()} />)` の形（`detailOf("42", [])` の `id` と合わせる）。選択は `fireEvent.change(screen.getByLabelText("Work"), { target: { value: "3" } })` の形。ラベルの一致が複数になるときは `getByRole("combobox", { name: ... })` か `getByRole("checkbox", { name: ... })` を使う。

## 5. 確かめ方（担当が実行し、出力を報告に貼る）

5-1. 型と lint: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b1/frontend && npx tsc --noEmit -p tsconfig.json 2>&1 | tail -20` と `npx eslint src/features/tcg-product-import 2>&1 | tail -20` がどちらもエラー 0。

5-2. 試験の名前: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b1 && grep -nE "^\s*it\(" frontend/src/features/tcg-product-import/TcgProductDetailDrawer.test.tsx | wc -l` と `grep -nE "^\s*it\(" frontend/src/features/tcg-product-import/TcgProductDetailDrawer.test.tsx | tail -7` の出力（既存 11 本＋新 7 本＝18、末尾 7 本の名前が §4-4 の表のとおり）。

5-3. 試験: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b1/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/features/tcg-product-import 2>&1 | tail -30` が全部合格。

5-4. 金型と i18n: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b1/frontend && npm run check:i18n-missing-keys 2>&1 | tail -10` が合格。`cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b1 && git diff origin/main -- frontend/src/features | grep -nE "^\+.*(<input|<select|#[0-9a-fA-F]{3,6}\b|style=)" | head -10` が 0 行。`git diff origin/main -- frontend/src/features | grep -nP "^\+(?!.*//).*[\x{3040}-\x{30ff}\x{4e00}-\x{9fff}]" | head -10` の出力（コメント以外の日本語が 0 行）。

5-5. 差分: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b1 && git diff origin/main --stat | tail -10` が §3 の 6 ファイルだけ。

5-6. PR の CI は担当が待たない。PR を作ったら URL を報告して終える。

## 6. 分岐ごとの対処

- §10 手順1 で、origin/main の `backend/app/services/tcg_product_detail_svc.py` に `blank_confirmations` の文字が無い（便2aが未マージ） → BLOCKED:（作業を始めない）
- §4 の行の目印が実物と違う → 実物の該当行を貼り、同じ意味・同じ位置に合わせて書く。見つからなければ NEEDS_DECISION:
- 既存の試験が落ちる → 落ちた試験の名前と原文を貼る。直してよいのは §4-4(a) の下ごしらえによる差だけ。期待値を変える必要があれば BLOCKED:
- `Checkbox` の `label` の一致が複数で試験が書けない → `getByRole("checkbox", { name: "..." })` で書く。それでも無理なら NEEDS_DECISION:
- `tsc` が `Exclude<keyof Draft, "blank_confirmations">` の呼び出し元（`classificationFields.map` の `change(field, ...)` など）で落ちる → 落ちた行を貼り、型だけで直す（動きを変えない）。直せなければ BLOCKED:
- husky や CI の自動検査が落ちる → 検査名と原文を貼る。迂回（`--no-verify` など）しない

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 細分類の選択肢は、選んだ作品に紐づくものだけが出る | 試験 1、§8 の画面確認 |
| 作品を変えると、紐づかない細分類は空に戻る | 試験 2 |
| 印は値が入ると外れ、値がある間は付けられない | 試験 3 |
| 保存済みの細分類と印が、編集の保存と除外ワードの追加で消えない | 試験 4・7 |
| 未入力の案内は出るが、保存は止めない（止めるのは便3） | 試験 5 |
| 印の無い応答では開かず、印を消す保存をしない | 試験 6 |
| 文言は ja/en 同じキー、金型だけを使う | §5-4 |

## 8. 反映の前後（Opus が行う。担当はしない）

- CI の緑を確かめ、差分を審査し、「確認済み」のコメントを残してマージ → deploy の成功を Actions の記録で確かめる
- 反映後、本番の画面（app.salesanchor.jp の商品マスタ）で商品詳細を開き、細分類の欄と「調べたが存在しない」の欄が出ることを確かめる（保存はしない）
- 生出力は /tmp/CC報告ファイル/master-required-fields/bin2b1/ に置く

## 9. 戻し方

- この PR の revert を main にマージ（画面だけが元に戻る。API とデータは変わらない）

## 10. PR

手順1 便2aが main にあることを確かめ、新しい作業場所を作る
    cd /Users/tanizawashingo/salesanchor && git fetch -q origin && git grep -c "blank_confirmations" origin/main -- backend/app/services/tcg_product_detail_svc.py
期待する出力 1 以上（0 なら §6 の1つ目）
    cd /Users/tanizawashingo/salesanchor && bash scripts/new-worktree.sh release/master-register-required-fields-bin2b1 --claude 2>&1 | tail -5
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b1 && git status -sb | head -3 && git log -1 --oneline
期待する出力 作業場所が origin/main の先頭から作られている。以下のコマンドの作業場所は /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b1
    このカードを /tmp/CC報告ファイル/master-required-fields/bin2b/card-bin2b1.md から Read し、Write ツールで `/Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b1/docs/handoff/master-register-required-fields/card-bin2b1.md` に同じ内容で置く。`cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b1/frontend && ls node_modules | head -1` で依存が無ければ `npm ci 2>&1 | tail -5`

手順2 §4 を Write/Edit ツールで実装し、§5-1〜5-5 を実行する

手順3 commit と push
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b1 && git add frontend/src/features/tcg-product-import/productDetailModel.ts frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx frontend/src/features/tcg-product-import/TcgProductDetailDrawer.test.tsx frontend/src/locales/ja.json frontend/src/locales/en.json docs/handoff/master-register-required-fields/card-bin2b1.md
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b1 && git commit -m "feat: ADR-1020便2b-1 商品詳細に細分類と調べたが無いの印"
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b1 && git push -q -u origin release/master-register-required-fields-bin2b1 && git log -1 --oneline && git log origin/release/master-register-required-fields-bin2b1 -1 --oneline
期待する出力 2 つの git log が同じハッシュ

手順4 PR を作る
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b1 && gh auth status 2>&1 | grep -c "Active account: true"

- 名義が `shingo-cc` であることを確かめる
- 本文は Write ツールで英字だけのパスのファイル（/private/tmp/claude-501/bin2b1-pr-body.md）に作り、`scripts/dev/validate-pr-body.sh` に標準入力で渡して exit 0 を確かめる（2 分以上かかるので timeout を長めにする）
- PR は `scripts/gh-pr-create-safe.sh` に本文ファイルを絶対パスで渡して作る（`$変数` を使わない）。base は main。ready で作る（下書きにしない）。担当はマージしない
- 作成後に `.pr-number` と `gh pr list --head release/master-register-required-fields-bin2b1 --json number` の一致を確かめる
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に recon（docs/handoff/master-register-required-fields/recon.md）・設計（docs/handoff/master-register-required-fields/design.md）・このカード・ADR-1020 を書く。区分は S か M（危険パスなし）。PO承認: に「PO 2026-10-16『y』（KGI G1〜G4・3便）」と書く
- `触るファイル:` と `削除するファイル:` は 1 行・カンマ区切り・バッククォートなし・注記なし。良い例: 触るファイル: frontend/src/features/tcg-product-import/productDetailModel.ts, frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx, frontend/src/features/tcg-product-import/TcgProductDetailDrawer.test.tsx, frontend/src/locales/ja.json, frontend/src/locales/en.json, docs/handoff/master-register-required-fields/card-bin2b1.md ／ 削除するファイル: なし

## 11. 報告

- 完了報告の本文に: 冒頭の受領文／§5-1〜5-5 の出力／PR の URL／生出力のパス（/tmp/CC報告ファイル/master-required-fields/bin2b1/impl/）／判断を要した点（事実のみ）
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
