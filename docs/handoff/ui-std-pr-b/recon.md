# recon — UI標準化 PR-B (Company系3ファイル)

## ブランチ
`feature/morimoto/ui-std-pr-b`

## 対象ファイルと置換ポイント

### 1. frontend/src/components/MergeCompanyModal.tsx

| 行 | 現行要素 | 置換先 | 備考 |
|----|---------|--------|------|
| 155 | `<input type="text" placeholder=...>` | `<TextField>` | 検索フィールド |
| 217-225 | `<input type="radio">` | **残置** | ラジオボタン — PR-A方針に従い残置 |
| 243 | `<textarea rows={2}>` | `<Textarea>` | reason入力 |
| 253 | `<button type="button">` (cancel) | `<Button variant="secondary">` | |
| 256 | `<button type="button" className="btn-primary">` | `<Button>` (default=primary) | |
| 315 | `<button type="button">` (back) | `<Button variant="secondary">` | |
| 322 | `<button type="submit" className="btn-danger">` | `<Button variant="danger">` | |

### 2. frontend/src/pages/company-detail/CompanyAddressModal.tsx

| 行 | 現行要素 | 置換先 | 備考 |
|----|---------|--------|------|
| 81-85 | `<select>` (billing/delivery) | `<Select options={[...]}>` | options配列インライン定義 |
| 89-90 | `<input>` branch_name | `<TextField>` | |
| 92-94 | `<input>` name | `<TextField>` | |
| 96-98 | `<input type="email">` email | `<TextField type="email">` | |
| 100-103 | `<input>` telephone + `<span class="field-error">` | `<TextField error={addrPhoneError ?? undefined}>` | エラーをTextFieldのerror propに統合 |
| 105-107 | `<input>` tax_id | `<TextField>` | |
| 109-111 | `<input>` address_line_1 | `<TextField>` | |
| 113-115 | `<input>` address_line_2 | `<TextField>` | |
| 117-119 | `<input>` address_line_3 | `<TextField>` | |
| 121-123 | `<input>` city | `<TextField>` | |
| 125-127 | `<input>` state | `<TextField>` | |
| 129-131 | `<input>` zip | `<TextField>` | |
| 133-137 | `<input maxLength={2}>` country_code | `<TextField maxLength={2}>` | |
| 140 | `<input type="checkbox">` is_default | **残置** | チェックボックス — PR-A方針に従い残置 |
| 146 | `<button type="button">` (cancel) | `<Button variant="secondary">` | |
| 147 | `<button type="submit" className="btn-primary">` | `<Button>` (default=primary) | |

### 3. frontend/src/pages/company-detail/CompanyDetailPage.tsx

| 行 | 現行要素 | 置換先 | 備考 |
|----|---------|--------|------|
| 75 | `<button>` (back, no-data state) | `<Button variant="secondary">` | |
| 148 | `<button className="btn-sm">` (header back) | `<Button size="sm" variant="secondary">` | |
| 154-159 | `<button className="btn-sm btn-primary">` (reg link) | `<Button size="sm">` (default=primary) | title prop保持 |
| 164-169 | `<button className="btn-sm">` (addr link) | `<Button size="sm" variant="secondary">` | |
| 171-175 | `<button className="btn-sm">` (change billing) | `<Button size="sm" variant="secondary">` | |
| 189-192 | `<button className="btn-sm">` (copy reg link) | `<Button size="sm" variant="secondary">` | style CSS変数保持 |
| 198-201 | `<button className="btn-sm">` (copy addr link) | `<Button size="sm" variant="secondary">` | style CSS変数保持 |
| 207-210 | `<button className="btn-sm">` (copy billing link) | `<Button size="sm" variant="secondary">` | style CSS変数保持 |
| 217 | `<button className="tab ...">` (basic tab) | `<Button variant="ghost" className="tab ...">` | |
| 220 | `<button className="tab ...">` (addresses tab) | `<Button variant="ghost" className="tab ...">` | |
| 223 | `<button className="tab ...">` (contacts tab) | `<Button variant="ghost" className="tab ...">` | |
| 226 | `<button className="tab ...">` (channels tab) | `<Button variant="ghost" className="tab ...">` | |
| 229 | `<button className="tab ...">` (discord tab) | `<Button variant="ghost" className="tab ...">` | |
| 232 | `<button className="tab ...">` (convHistory tab) | `<Button variant="ghost" className="tab ...">` | |

## 参照コンポーネント

- `frontend/src/components/Button.tsx` — variant=primary(default)/secondary/ghost/danger, size=sm/md(default)/lg, className マージ済み
- `frontend/src/components/TextField.tsx:54` — `{label != null && ...}` によりlabelなし使用可（form-row外部labelと共存）
- `frontend/src/components/Select.tsx:17-21` — `SelectOption = { value: string; label: string }`が必須
- `frontend/src/components/Textarea.tsx` — TextareaHTMLAttributes を継承

## 既存ADR確認

- `docs/adr/ADR-027`: i18n強制 — 本PR変更なし（既存のt()呼び出しをそのまま維持）
- `docs/adr/ADR-067`: デザイントークン強制 — style prop の CSS変数(`var(--spacing-2)`, `var(--spacing-4)`)はトークン準拠のため保持

## 残置理由（checkbox / radio）

PR-A (Contact系) と同方針。`<input type="checkbox">` / `<input type="radio">` は標準コンポーネントに対応する専用金型が未実装のため残置。ADR-067 既知負債として記録。
