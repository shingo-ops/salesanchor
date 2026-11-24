# design — お客様の住所フォームの並びと、送り先の住所の決まり（customer-address-form）

- 書いた人: Claude Opus（設計担当）・2026-11-24
- 改訂: 審査2回目 REVISE（[review-architect-2.md](review-architect-2.md)）の R1'・R2' と L1〜L4 を反映（2026-11-24）
- 改訂: 審査1回目 REVISE（[review-architect-1.md](review-architect-1.md)）の R1〜R4 と L2〜L5・L7〜L13 を反映（2026-11-24）
- 基準: `origin/main` = `a12741e7234b7fe2ec40a790a8aa3422e0d6eaa4`
- 親: KGI [kgi.md](../../specs/customer-address-form/kgi.md)（K1〜K14・PO 承認 2026-11-24）／あるべき姿 [ideal-state.md](../../specs/customer-address-form/ideal-state.md)／決定 [decisions.md](decisions.md)（D1〜D6）／事実 [recon.md](recon.md)／外部の実測 [evidence-local.md](evidence-local.md)
- 関わる ADR: ADR-126（登録フォームの入力契約。§8 で追補）・ADR-144（UI の金型）・ADR-067（色・寸法の変数）・ADR-027（翻訳キー）・ADR-135/136（main 合流＝本番投入）

## 1. 目的と範囲

- 目的: お客様が登録フォームを迷わず埋められる並びにし、FedEx の伝票に載らない住所（1行35文字超え・英字等以外）が新しく入らないようにする（D2・D5・D6）。
- 対象: 公開フォーム3つ（/register・/register/address・/register/change-billing）、社内の会社の住所の窓（送り先）、注文ごとの発送の欄、見積書の PDF の宛名、決まりの受け口3つ。
- 対象外: スマホ幅の見た目（PC 先行。スマホは崩れていないことだけ確かめる）、社内の画面の国の部品（`frontend/src/components/CountryCombobox.tsx`）、請求先の住所の決まり（自由のまま。D2）、今ある住所の書き換え（D6）、DB の列・migration、FedEx の伝票を出す受け口（recon §9）。
- migration・`.github/workflows/deploy.yml`・本番 `scripts/` に触らない → ADR-136 の危険 PR に当たらない。

## 2. 決まりの中身（K6・K7・K13 の正本）

| 項目 | 決まり |
|---|---|
| 対象 | `address_type = delivery` の住所1〜3（会社の住所）、注文ごとの発送の address1〜3 |
| 長さ | 35文字まで（36文字で断る）。空欄・未入力は通す |
| 文字 | 印字できる英字・数字・記号・空白だけ（文字コード 0x20〜0x7E）。改行・タブ・日本語・「é」などは断る |
| 両方に当たる時 | 文字の種類を先に見る（「東京」を36個並べたら「英字・数字・記号で…」が出る） |
| 置き場所 | 受け口: `backend/app/schemas/base.py` の `validate_delivery_address_line` 1つ。画面: `frontend/src/utils/addressRules.ts` の `deliveryAddressLineError` 1つ（K13） |

## 3. 受け口（backend）の変更

### 3-1 `backend/app/schemas/base.py` — 決まりの1か所（K13）

`validate_email_loose` の直後に足す（`re` は 10 行目で import 済み）:

```python
# 送り先の住所1行の決まり（customer-address-form design §2・FedEx Ship API streetLines 1行35文字）
DELIVERY_ADDRESS_LINE_MAX = 35
_DELIVERY_ADDRESS_LINE_RE = re.compile(r"^[\x20-\x7E]*$")


def validate_delivery_address_line(value: str | None) -> str | None:
    """送り先の住所1行を確かめる。英字・数字・記号・空白だけ、35文字まで。"""
    if value is None:
        return None
    if not _DELIVERY_ADDRESS_LINE_RE.match(value):
        raise ValueError("address_line_non_ascii")
    if len(value) > DELIVERY_ADDRESS_LINE_MAX:
        raise ValueError("address_line_too_long")
    return value
```

### 3-2 `backend/app/schemas/registration_token.py` — お客様のフォーム（K6・K7・K8）

- import を `from app.schemas.base import validate_delivery_address_line, validate_email_loose, validate_phone` に変える。
- `AddressInput` の最後の validator の後に足す:

```python
    @model_validator(mode="after")
    def check_delivery_address_lines(self) -> "AddressInput":
        """送り先だけ住所1〜3に決まりを当てる（請求先は自由・D2）。"""
        if self.address_type == "delivery":
            for field in ("address_line_1", "address_line_2", "address_line_3"):
                validate_delivery_address_line(getattr(self, field))
        return self
```

- 「Ship to the same address.」の時は画面が請求先を `delivery` として足して送る（`frontend/src/pages/register/RegisterPage.tsx:200-207`）ので、受け口でも K8 が成り立つ。`/register/address` は `address_type: "delivery"` 固定（`frontend/src/pages/register/RegisterAddressPage.tsx:44`）。`/register/change-billing` は `billing` 固定（型 `frontend/src/pages/register/RegisterChangeBillingPage.tsx:28`・初期値 `:46`）で決まりは効かない。

### 3-3 `backend/app/routers/companies.py` — 社内の住所の窓（K11・K12）

会社の住所は「全部消して全部入れ直す」ので（recon §2）、型には付けず、受け口で **今ある送り先と住所1〜3が同じ行は確かめない**（今ある決まり外の住所を消さず、別の住所を直す保存を止めない＝K12）。

ファイルの中の `_replace_addresses` の定義の直前に足す:

```python
def _addr_lines(a) -> tuple:
    """住所1〜3を比べる形にする（空欄 "" と None は同じとみなす）。"""
    get = a.get if isinstance(a, dict) else (lambda k: getattr(a, k))
    return tuple((get(k) or None) for k in ("address_line_1", "address_line_2", "address_line_3"))


async def _check_new_delivery_lines(db: AsyncSession, company_id: int | None, addresses) -> None:
    """送り先のうち、今ある送り先と住所1〜3が違う行だけ決まりを当てる（D6・K12）。"""
    existing: set[tuple] = set()
    if company_id is not None:
        rows = await db.execute(
            text(
                "SELECT address_line_1, address_line_2, address_line_3 FROM company_addresses "
                "WHERE company_id = :cid AND address_type = 'delivery'"
            ),
            {"cid": company_id},
        )
        existing = {_addr_lines(dict(r)) for r in rows.mappings().all()}
    for a in addresses:
        a_type = a.get("address_type") if isinstance(a, dict) else a.address_type
        if getattr(a_type, "value", a_type) != "delivery" or _addr_lines(a) in existing:
            continue
        for field in ("address_line_1", "address_line_2", "address_line_3"):
            value = a.get(field) if isinstance(a, dict) else getattr(a, field)
            try:
                validate_delivery_address_line(value)
            except ValueError as e:
                raise HTTPException(status_code=422, detail=str(e))
```

- import に `from app.schemas.base import validate_delivery_address_line` を足す（既に `app.schemas.base` から import があればそこへ足す）。
- `create_company`: `await _replace_addresses(db, new_id, data.addresses)`（`:479`）の直前に `await _check_new_delivery_lines(db, None, data.addresses)`。会社の INSERT の後で断ることになるが、`get_db`（`backend/app/database.py:70-79`）が例外で巻き戻すので何も残らない（審査 L2）。`_replace_addresses` の定義は `backend/app/routers/companies.py:227`。
- `update_company`: `addresses = update_data.pop("addresses", None)`（`companies.py:550`）の直後、`if update_data:` の UPDATE より前に `if addresses is not None: await _check_new_delivery_lines(db, company_id, addresses)`。会社本体の UPDATE より前に断るので、途中まで書いた状態が残らない。
- 会社の併合（`:852-915`）は住所の文字を書かないので触らない。

### 3-4 `backend/app/schemas/order_shipping_detail.py` — 注文ごとの発送（K11）

本番は 0 件（recon §3）なので作る・直すたびに必ず確かめる。読み出し（`Response`）には付けない。

- import に `field_validator` と `from app.schemas.base import validate_delivery_address_line` を足す。
- `OrderShippingDetailBase` の直後に足し、`OrderShippingDetailCreate` と `OrderShippingDetailUpdate` の親を `(_DeliveryAddressLinesCheck, OrderShippingDetailBase)` にする:

```python
class _DeliveryAddressLinesCheck(BaseModel):
    """書き込みだけ住所1〜3に送り先の決まりを当てる（読み出しの Response には付けない）。"""

    @field_validator("address1", "address2", "address3", check_fields=False)
    @classmethod
    def _check_delivery_line(cls, v: str | None) -> str | None:
        return validate_delivery_address_line(v)
```

- `Update` は `exclude_unset` で送られた列だけ直すが、validator も送られた値にしか走らないので、住所を送らない更新は今までどおり通る。

### 3-5 `backend/app/routers/invoices.py` — 見積書の宛名に住所3（K10・D4）

DB を読まずに試せるよう、住所をつなぐ所を小さい関数に分ける（審査 R3）。

- `_fetch_address_snapshot` の定義の直前に足す:

```python
def _join_address_lines(row) -> str:
    """見積書の宛名の住所: 住所1〜3を空白でつなぐ（空・None は飛ばす）。"""
    return " ".join(
        filter(None, [row["address_line_1"], row["address_line_2"], row["address_line_3"]])
    )
```

- `:105-107` の `"address": " ".join(` から `),` までの3行を `"address": _join_address_lines(row),` の1行にする。

請求書の PDF は分けた値で住所1〜3 を描くので見た目は変わらない（recon §7）。

## 4. 画面（frontend）の変更

### 4-1 変数と幅の金型（K2・K14）

`frontend/src/tokens.css`:
- `:198`（`--field-w-lg-max`）の次の行に `  --field-w-xs:        80px;    /* 入力部品 幅金型 xs（国番号「+000」など4文字の欄） */`
- `:334`（`--max-width-form`）の次の行に `  --max-width-public-form:   600px;  /* お客様向けの登録フォームの最大幅（/register 系・今の 600px と同じ） */`

`frontend/src/components/field-size.css` の幅の段の先頭（`.field-w-sm,` の前）に足す:

```css
.field-w-xs,
.comp-select__control.field-w-xs,
.comp-field__input.field-w-xs { width: var(--field-w-xs, 80px); }
```

- 80px の根拠: 入力欄の中の余白は左右 12px×2（`FormField.css` の `padding: var(--space-2) var(--space-3)`）と枠 1px×2 で、文字が入る幅は 54px。「+000」は 14.4px（`--font-base`）の数字4つ。191 か国の番号が欠けないことは K2 の試験（§6）で毎回確かめる。足りなければ試験が赤になる。
- 設計書 `docs/specs/design-system/component-ssot/field-size/design.md` §1 の幅の表に xs の行を足す（この設計の PR で足した）。

### 4-2 決まりの画面側の1か所（K13）

新しいファイル `frontend/src/utils/addressRules.ts`:

```ts
/** 送り先の住所1行の決まり（customer-address-form design §2）。受け口の validate_delivery_address_line と同じ。 */
export const DELIVERY_ADDRESS_LINE_MAX = 35;
const PRINTABLE_ASCII = /^[\x20-\x7E]*$/;

export type AddressRuleError = "addressRule.ascii" | "addressRule.maxLength";

/** 決まりに合わなければ翻訳キーを返す。合えば null。空欄は null。 */
export function deliveryAddressLineError(value: string | null | undefined): AddressRuleError | null {
  if (!value) return null;
  if (!PRINTABLE_ASCII.test(value)) return "addressRule.ascii";
  if (value.length > DELIVERY_ADDRESS_LINE_MAX) return "addressRule.maxLength";
  return null;
}
```

- 文の表示は `t(key, { max: DELIVERY_ADDRESS_LINE_MAX })`。

### 4-3 翻訳キー（K14・ADR-027）

`frontend/src/locales/ja.json` と `frontend/src/locales/en.json` の一番上の階層に同じキーを足す（公開フォームと社内の画面の両方で使うので `registration` の中に入れない）:

| キー | ja | en |
|---|---|---|
| `addressRule.ascii` | 英字・数字・記号で入力してください | Please use English letters, numbers and symbols only. |
| `addressRule.maxLength` | {{max}}文字以内で入力してください | Please enter {{max}} characters or fewer. |

### 4-4 公開フォームの国の部品 `frontend/src/pages/register/CountryCombobox.tsx`（K2・K4）

- 足す引数: `optionLabelFn?: (c: CountryEntry) => string`（一覧の行の字。省けば `displayFn`）。
- 一覧の行は `{(optionLabelFn ?? displayFn)(c)}` を出す。選んだ時に返す値は今と同じ `displayFn(c)`。
- 直書きを新しいファイル `frontend/src/pages/register/CountryCombobox.css` へ移す（未定義の変数は正しい変数へ）:

```css
/* 公開フォームの国の部品（customer-address-form design §4-4）。ADR-067: 色・寸法は変数だけ */
.register-combobox { position: relative; }
.register-combobox__list {
  position: absolute;
  z-index: var(--z-dropdown);
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  max-height: var(--dropdown-max-h);
  min-width: var(--min-width-dropdown);
  width: 100%;
  overflow: auto;
  margin: 0;
  padding: 0;
  list-style: none;
}
.register-combobox__option { padding: var(--space-2) var(--space-3); cursor: pointer; }
```

- TSX 側の変更（審査 R2。これが無いと CSS が当たらない）:
  - (a) 先頭の import の後に `import "./CountryCombobox.css";`
  - (b) 外枠の `<div style={{ position: "relative" }}>`（`CountryCombobox.tsx` では `:46` 付近。`frontend/src/pages/register/RegisterAddressPage.tsx` の写し元では `:116`）を `<div className="register-combobox">` に
  - (c) 一覧の `<ul style={{ position: "absolute", … }}>`（`:62-75` 付近）を `<ul className="register-combobox__list">` に（`style` は丸ごと消す）
  - (d) 行の `<li … style={{ padding: "var(--spacing-2) var(--spacing-3)", … }}>`（`:81` 付近）を `className="register-combobox__option"` に。`style` の中に選んだ行の背景など上の CSS に無い宣言があれば、消さずに止めて報告する
  - (e) このファイルに `style={{` が残らない
- 一覧の重なりの順が `zIndex: 10` から `--z-dropdown`（`tokens.css:127`）に変わる（§7）。
- 一覧は欄（80px）より広い `--min-width-dropdown`（180px）まで広がるので、国番号の欄でも国の名前が読める。
- `RegisterAddressPage.tsx:75-` の写しの `function CountryCombobox` を消し、`import { CountryCombobox } from "./CountryCombobox";` に替える（同じ部品が2つある状態をなくす・recon §4）。

### 4-5 3つの公開フォームで共通に直すこと

対象: `frontend/src/pages/register/RegisterPage.tsx`（請求先と `ShippingAddressFields`）・`frontend/src/pages/register/RegisterChangeBillingPage.tsx`・`frontend/src/pages/register/RegisterAddressPage.tsx`。

| # | 直すこと | 前 | 後 |
|---|---|---|---|
| a | 外枠（K5） | `style={{ maxWidth: "600px", margin: "0 auto", padding: "var(--spacing-6)" }}` | `style={{ maxWidth: "var(--max-width-public-form)", margin: "0 auto", padding: 0 }}`（今の `--spacing-6` は未定義で、計算すると 0。0 と書いて今と同じにする・審査 R1） |
| b | 言語切替（K1） | 右寄せの `<div>` の中の `Button` ＋ その下の `<h1>` | `<div className="page-header"><h1>…</h1><Button …/></div>`（`company-forms.css:17-31` の見出しの行の型。`frontend/src/App.tsx:137` で全画面に読み込み済み） |
| c | 国番号（K2） | 外枠 `<div style={{ width: "140px", flexShrink: 0 }}>`・`displayFn={(c) => \`${c.dial} ${c.code}\`}`・`onChange` で `COUNTRIES.find(...)` | 外枠 `<div className="field-w-xs" style={{ flexShrink: 0 }}>`・`displayFn={(c) => c.dial}`・`optionLabelFn={(c) => \`${c.dial} ${c.name}\`}`・`onChange={(val) => update…("telephone_dial", val)}`（`find` は消す） |
| d | City・State・ZIP（K3・D1） | 3つの `<label>` が縦 | City の `<label>` はそのまま1行。その下に `<TwoColumn ratio="1:1" gap="4">` で State と ZIP の `<label>` を並べる |
| e | 未定義の変数（K14） | `--spacing-N`・`--border-default`・`--color-red-500`・`--color-primary`・`--font-size-xs`・`--font-size-sm` | 幅を決める宣言（3フォームのすべての `<fieldset>`＝`RegisterPage.tsx:299, :482, :492`・`RegisterAddressPage.tsx:311`・`RegisterChangeBillingPage.tsx:245` の5つ。外枠は各ファイルの読み込み中・エラー・期限切れ・本体の4つとも §4-5 a と同じに の `border` と `padding`）は、今の計算の結果と同じ `border: "none"`・`padding: 0` と書く（K5 を守る・審査 R1）。それ以外（間隔 `gap`・`margin`・色・字の大きさ）は `--space-N`・`--border`・`--danger`・`--accent`・`--font-xs`・`--font-sm` へ名前を置き換える |

- c の理由: 国番号の欄は番号だけを持つので、番号が同じ国（+1 の米国とバハマなど）でどれを選んでも欄は「+1」と出て、送る電話番号も今と同じ（`combinePhone` は `telephone_dial` だけを使う・`frontend/src/pages/register/RegisterPage.tsx:136-139`）。
- e の注意: 未定義の変数を使った宣言は、計算の時点で無効になり初期値（余白 0・枠なし）になる。幅に効く外枠の `padding` と fieldset の `border`・`padding` は、その初期値を `0`・`none` と書いて今の幅をそのまま保つ。縦の間隔と色（必須の印が赤くなる・段の間が開く）は置き換えで効き始める。目に見える変化として evaluator の撮影で確かめる（§7 弊害）。
- `shippingChoice` の初期値は `"same"`（`frontend/src/pages/register/RegisterPage.tsx:107`）なので、開いた直後から請求先にも決まりが効く（審査 L11）。

### 4-6 住所1〜3の欄（K6・K7・K8・K9）

- 3つのフォームの住所1〜3は、`<label>` で包んだ `TextFieldControl` から `TextField`（金型）へ替える: `<TextField label={t("registration.addressLine1")} required fullWidth value=… onChange=… error={…} />`。`error` は `deliveryAddressLineError(値)` が返したキーを `t(key, { max: DELIVERY_ADDRESS_LINE_MAX })` にしたもの（決まりに合えば `undefined`）。打つたびに赤くなる。
- 決まりを当てる欄:
  - 送り先（`ShippingAddressFields`・`RegisterAddressPage`）の住所1〜3: いつも。
  - `RegisterPage` の請求先の住所1〜3: 送り先の2択が「Ship to the same address.」の時だけ（`:454-476` の2択の状態の変数で分ける）。
  - `RegisterChangeBillingPage` の住所1〜3: 当てない。
- 送信の前（各 `handleSubmit` の必須の確かめの後）: 当てる欄のどれかに決まり違反があれば送らない（`setError` の帯は出さず、欄の赤と文で知らせる）。
- 請求先に住所3を足す（K9・D3）: `frontend/src/pages/register/RegisterPage.tsx` の請求先の住所2（`:394-402`）の後と、`frontend/src/pages/register/RegisterChangeBillingPage.tsx` の住所2（ラベル `:342`）の `</label>` の直後に、住所3の `TextField`（`registration.addressLine3`・任意）。入れ物 `AddressForm` は既に `address_line_3` を持ち、送る中身にも入る（`frontend/src/pages/register/RegisterPage.tsx:39`・`frontend/src/pages/register/RegisterChangeBillingPage.tsx:37`）。受け口は保存済み（`backend/app/routers/registration_tokens.py:575` の INSERT に `address_line_3` がある）。

### 4-7 社内の住所の窓 `frontend/src/pages/company-detail/CompanyAddressModal.tsx`（K11・K12）

- 状態を1つ足す: `const [lineErrors, setLineErrors] = useState<Partial<Record<"address_line_1" | "address_line_2" | "address_line_3", string>>>({});`
- `handleSave` の電話の確かめの後に: `addrForm.address_type === "delivery"` なら住所1〜3を `deliveryAddressLineError` で確かめ、違反があれば `setLineErrors(...)` して `return`。請求先なら確かめない。
- 住所1〜3の `TextField`（`frontend/src/pages/company-detail/CompanyAddressModal.tsx:117-127`）に `error={lineErrors.address_line_1}` などを渡す。欄を打ち直したらその欄の `lineErrors` を消す。
- 窓の種類の選択（`frontend/src/pages/company-detail/CompanyAddressModal.tsx:92` の `onChange`）を `(e) => { setLineErrors({}); handleAddressTypeChange(e.target.value as "billing" | "delivery"); }` に替える（送り先 → 請求先に替えた時に赤を残さない・審査1回目 L3・2回目 R2'）。`handleAddressTypeChange` の本体（`frontend/src/pages/company-detail/useCompanyDetail.ts:224`）は触らない。
- 保存を押した時だけ赤くなる（窓を開いただけでは赤くならない）＝K12「開いて保存しようとした時だけ赤くなる」。

### 4-8 注文ごとの発送の欄 `frontend/src/components/ShippingDetailPanel.tsx`（K11）

- 住所の欄の描画（`frontend/src/components/ShippingDetailPanel.tsx:424-433` の `TEXT_FIELDS.address.map`）で、`f.key` が `address1`・`address2`・`address3` の3つだけ `<TextField label={t(f.labelKey)} value=… onChange=… error=… data-testid={`ship-input-${f.key}`} />` に替える。`error` は `deliveryAddressLineError(form[f.key])` のキーを `t(key, { max })` にしたもの。他の欄は今のまま。`TextField` は `data-testid` を入力欄に渡す（`frontend/src/components/TextField.tsx:95`）ので `frontend/tests-e2e/order-shipping.spec.ts:269` は壊れない（審査 L4）。
- `handleSubmit`（`:277`）の最初で3つのどれかに違反があれば送らない。

## 5. 触るもの／触らないもの

| 触る | 触らない |
|---|---|
| `backend/app/schemas/base.py`・`backend/app/schemas/registration_token.py`・`backend/app/schemas/order_shipping_detail.py`・`backend/app/routers/companies.py`・`backend/app/routers/invoices.py` | `migrations/`・`.github/workflows/deploy.yml`・本番 `scripts/`・DB の今ある住所 |
| `frontend/src/tokens.css`・`components/field-size.css`・`frontend/src/utils/addressRules.ts`（新）・`frontend/src/locales/ja.json`・`frontend/src/locales/en.json` | `frontend/src/components/CountryCombobox.tsx`（社内の国の部品）・`frontend/src/constants/countries.ts` |
| `frontend/src/pages/register/CountryCombobox.tsx`・`CountryCombobox.css`（新）・`frontend/src/pages/register/RegisterPage.tsx`・`frontend/src/pages/register/RegisterChangeBillingPage.tsx`・`frontend/src/pages/register/RegisterAddressPage.tsx` | `backend/app/routers/registration_tokens.py`（受け口の流れは変えない）・会社の併合 |
| `frontend/src/pages/company-detail/CompanyAddressModal.tsx`・`frontend/src/components/ShippingDetailPanel.tsx` | `frontend/src/pages/company-detail/useCompanyDetail.ts`（送り方は変えない）・社内の画面の請求先の確かめ |
| 試験（§6） | スマホ幅の並び |

## 6. 試験

| 試験 | 場所 | 中身 |
|---|---|---|
| 決まりの関数 | `backend/tests/test_delivery_address_rule.py`（新・DB なし） | 35文字 ○・36文字 ×（too_long）・「東京」×（non_ascii）・「é」×・`"1-2 Main St, #3"` ○・`None`/`""` ○・改行 × |
| お客様の型 | 同上 | `AddressInput(address_type="delivery", address_line_1="x"*36)` が `ValidationError`。`billing` なら通る |
| 発送の型 | 同上 | `OrderShippingDetailCreate(address1="x"*36)` と `Update(address3="東京")` が `ValidationError`。`Response` は36文字でも通る |
| お客様の受け口 | `backend/tests/test_public_register_company.py` に足す | 送り先の住所1が36文字の登録は 422。請求先だけ36文字（送り先は別の正しい住所）は 200 |
| 会社の受け口（K12） | `backend/tests/test_companies.py` に足す（②③は引数に `db_session` を足し、`backend/tests/test_public_register_company.py:144` の SQL で `company_addresses` を入れる書き方を写す・審査 L7） | ①POST で送り先36文字 → 422 ②SQL で会社に40文字の送り先を入れ、PATCH でその行をそのまま＋請求先を直して送る → 200・40文字の行が残る ③同じ行の住所1を別の40文字に変えて送る → 422 |
| 見積書（K10） | `backend/tests/test_invoice_pdf_address.py` に足す | `_join_address_lines({"address_line_1": "Line A", "address_line_2": "Line B", "address_line_3": "Line C"})` が `"Line A Line B Line C"`、住所3が `None`・`""` なら `"Line A Line B"`。さらに `address` が `"Line A Line B Line C"` の dict を `_quote_pdf_address` に通して `render_quote_pdf` で描き、既存の `drawn` の仕掛けで `Line C` が描かれることを確かめる |
| 既存試験の直し | `backend/tests/test_order_shipping_details.py:317-335` | `nasty_addr` に改行が入っていて新しい決まりで断られる（今はこの POST の結果を見ていない）。`nasty_addr = 'Line1, "Quoted" Line2'`、`nasty_recipient = 'Smith, "Jr."\nDept'` に替え、改行の試しは受取人の欄で続ける |
| 画面の決まり | `frontend/src/utils/addressRules.test.ts`（新・vitest） | 受け口の試験と同じ値で同じ答え |
| 社内の窓・発送の欄（K11） | 発送の欄は既存の `frontend/src/components/SharedButtonMigration.test.tsx` に足す（`t` は鍵をそのまま返すモック）。住所の窓は新しい `frontend/src/pages/company-detail/CompanyAddressModal.test.tsx`（vitest・今は試験が無い） | 発送の欄の address1 に「東京」→ 欄に `addressRule.ascii`・送信が呼ばれない。窓の送り先で住所1に36文字 → 保存で `addressRule.maxLength`・保存が呼ばれない。請求先なら呼ばれる |
| 国番号191か国（K2） | `frontend/src/pages/register/CountryCombobox.test.tsx`（新・vitest の画面試験。`frontend/src/components/AsyncCombobox.test.tsx` と同じ置き方） | `COUNTRIES` の全件で `displayFn = c => c.dial` の表示が番号だけ・「+1」を選ぶと欄が「+1」 |
| 画面の並び | `frontend/tests-e2e/register-form-ux.spec.ts` | B-3（「都道府県が市区町村より上」）は今のコードと逆で、CI の Playwright は止まっている（`.github/workflows/e2e.yml:294` `if: false`）。B-3 を K3 の形（City が1行・State と ZIP の上端が同じ）に書き換え、K1・K2（欄の `scrollWidth <= clientWidth` を 191 件）・K5（住所1の幅が変更前と同じ）・K6〜K9 を足す。住所の欄を探す時は `getByLabel` を使う（`TextField` のラベルは `<label for>` で入力欄の外・審査 L10）。CI では走らないので、evaluator がクラウドで `npx playwright test register-form-ux.spec.ts --project=chromium` を流す |

## 7. 弊害・トレードオフ

- 未定義の変数を正しい名前にすると、今は効いていない縦の間隔・色が効き始める（必須の印の赤・段の間隔）。登録フォームの見た目が少し変わる。→ evaluator が前後の画面を撮って PO 目視の材料にする。
- 幅に効く外枠の余白と fieldset の枠・余白は、今と同じ「0・なし」と書くので、住所1・2 の幅は今と同じ（K5・PO 承認の「今のまま」）。fieldset の枠は今までどおり出ない（審査 R1 の2案のうち、承認済みの K5 を変えない方を選んだ）。
- 住所1〜3の `TextField`（`.comp-field`）は下の間隔 `margin-bottom: var(--space-4)`（`FormField.css:21`）を持つので、住所1〜3の下の間隔だけ他の欄より広い（審査 L5）。evaluator の撮影で PO に見せる。
- 国の一覧の重なりの順が `10` から `--z-dropdown` に上がる（審査 R2）。
- FedEx の伝票を出す受け口（`backend/app/routers/shipping.py` の `POST /shipping/shipments`）は住所をリクエストで直に受けるが、この設計の範囲外で決まりは当てない（decisions.md・審査 L12）。
- 見出しを `page-header` の型にすると見出しの字が今（ブラウザの既定の h1）から社内の画面の見出しの大きさ（`--role-page-title-size` = `--font-2xl`）になる。
- 住所1〜3を `TextField` にすると、その3つだけラベルの字の形が金型の形（`comp-field__label`）になる。他の欄は今のまま。
- 会社の住所の受け口は「今ある送り先と住所1〜3が同じ行は通す」ので、決まり外の住所を別の会社の行にそっくり写して保存すると通らないが、同じ会社で同じ文字のまま他の欄（電話など）を直す保存は受け口では通る。画面（§4-7）が保存の時に赤くして止めるので、画面から入る分は K12 どおり。
- 打つたびに赤くなるので、36文字目を打った瞬間に赤くなる。打ち終わる前に赤が出るのは大手（Stripe・Shopify は文字数の上限を付けていない・evidence-local §2）より厳しいが、FedEx の上限（evidence-local §3）を確実に守るため。

## 8. ADR-126 の追補（この設計の PR で ADR に足す）

`docs/adr/ADR-126-registration-form-input-contract-v2.md` の末尾に「追補: 住所1〜3の決まりと請求先の住所3（2026-11-24）」を足す。中身は D2〜D5 と §2 の表、Section 1 に Address Line 3（任意）を足すこと、正本の置き場所（§2）。Status は変えない。

## 9. 受入基準と検証方法

| 基準 | 検証方法 |
|---|---|
| K1 言語切替が見出しと同じ行の右 | 3フォームで `getBoundingClientRect`：ボタンの縦の中心が h1 の上端〜下端の間・ボタンの左端 > h1 の右端（e2e・本番の Chrome） |
| K2 国番号は番号だけ・191件欠けない・幅は xs | vitest 191 件＋e2e で欄の `scrollWidth <= clientWidth`・欄の幅 80px |
| K3 City 1行・State と ZIP 同じ行 | e2e：City の幅 ＝ 住所1の幅、State と ZIP の上端が同じ（請求先・送り先・3フォーム） |
| K4 「jap」で Japan (JP) | e2e：国の欄に `jap` → 候補に `Japan (JP)` → 選ぶと欄に入る |
| K5 住所1・2 の幅が今と同じ | e2e：変更の前（origin/main を組み立てた画面）と後で、/register の請求先の住所1・2 の `getBoundingClientRect().width` の差が 1px 以内（横幅 1280）。外枠の最大幅は 600px のまま |
| K6 36文字で赤＋断る | e2e：送り先の住所1に36文字 → 赤・文・送信なし。35文字は通る。pytest：受け口に36文字 → 422 |
| K7 「東京」「é」で赤＋断る | 同上（文は「英字・数字・記号で入力してください」） |
| K8 請求先は「同じ」の時だけ | e2e：Proceed で請求先36文字 → 赤くならず送れる（mock 200）。Same で36文字 → 赤 |
| K9 請求先に住所3 | e2e：/register と /register/change-billing に住所3の欄・送る中身に `address_line_3` が入る |
| K10 見積書に住所3 | pytest（§6）＋本番でテナント001 の住所3入りの会社の見積 PDF を目視 |
| K11 社内の窓と発送の欄 | vitest（§6 の2つ）：窓で送り先に36文字 → 保存で赤・請求先は通る。発送の欄で address1 に「東京」→ 赤。pytest：会社 POST/PATCH・発送 POST/PATCH で 422 |
| K12 今ある住所は変わらない | 本番の読み取り専用の道で、反映前後にテナント004 の送り先の決まり外の数（35文字超え5件・英字等以外3件）が同じ。pytest ②③ |
| K13 決まりの置き場所1つ | `git grep -nF 'x20-' -- backend/app frontend/src ':!*.test.*'` が `backend/app/schemas/base.py` 1件と `frontend/src/utils/addressRules.ts` 1件だけ |
| K14 直書きなし・翻訳・CI 緑 | PR の CI 全部緑。差分の追加行で `#[0-9a-f]{3,6}` と `[0-9]+px` が tokens.css・field-size.css 以外に 0 件（`CountryCombobox.css` の `1px solid` の枠を除く。登録フォームの fieldset の枠は §4-5 e で全部 `border: "none"` になるので `2px` も残らない）。`addressRule.*` が ja・en 両方にある |

## 10. 外部・過去事例

- Google Maps の住所フォームの見本・Stripe Address Element: City が1行を占め、State と ZIP が半分ずつ同じ行（evidence-local §1・§2。2026-11-23 実測）。→ K3 の並びの根拠。
- Shopify Checkout（Allbirds）: City・State・ZIP を1行に3等分（evidence-local §2b）。PO は D1 で Google・Stripe の形を選んだ。
- FedEx Ship API 公式の仕様: 住所は1行35文字・最大3行（evidence-local §3）。→ §2 の35文字の根拠。英字等だけの決まりは PO の決定（D5）で、FedEx の資料に文字の種類の記述は無い（未確認のまま）。
- 欄の並びを変えた効果の数値事例は見つかっていない（evidence-local §4）。効果は K1〜K5 の○×で測り、数の効果を主張しない。

## 11. 維持の仕組み

- 守り手: backend/tests/test_delivery_address_rule.py と frontend/src/utils/addressRules.test.ts（決まりの値が変わると赤になる）
- 決まりの値（35・文字の範囲）は受け口と画面に1つずつ。どちらかを変える時はこの設計の §2 を先に直す。`frontend/src/utils/addressRules.ts` の先頭の注記で受け口の関数名を指している。
- 幅の金型 xs は field-size の設計書 §1 に載せる。新しい画面で国番号のような短い欄を作る時はこれを使う（ADR-144）。
- Playwright の CI が止まっている（e2e.yml:294）間は、登録フォームを直す PR のたびに evaluator が `frontend/tests-e2e/register-form-ux.spec.ts` をクラウドで流す。CI が再開すれば自動で守られる。
- 本番の決まり外の住所の数（K12）は反映後に1回数えて記録する。増えていれば受け口の抜けとして直す。

## 12. 段取り

1. この設計 PR（docs のみ）: recon・design・ADR-126 追補・field-size 設計書の xs 行・台帳。
2. 実装 PR（同じ枝に足す・1テーマ）: クラウドの Sonnet が `docs/handoff/customer-form-layout/card.md` で実装 → CI → クラウドの evaluator が e2e と撮影 → 手元の reviewer（opus）→ 確認済みコメント → マージ → 本番反映の確認 → K1〜K14 を本番で確かめる。
