# CC UI ガバナンス遵守テンプレ（ADR-144）

CC（Claude Code）が UI 部品を新設・修正するたびに参照すること。

---

## 必須チェック（UI 部品を実装する前に）

1. **`components/` に金型があるか先に確認する**
   - `<Select>` / `<TextField>` / `<SearchBar>` / `<Tabs>` / `<OverflowTabs>` 等が既に存在するか
   - `frontend/src/components/` を grep または Glob で確認する
2. **あれば必ずそれを使う**（独自実装を重複させない）
3. **無ければ実装しない・止めて報告する**
   - PO 許可を得てから `components/` に金型を登録してから使う
   - 金型作法: `Xxx.tsx` + `Xxx.css`（`var()` のみ）+ `Xxx.stories.tsx`

---

## 禁止事項（CI ゲートが赤にする）

| 禁止 | 理由 |
|------|------|
| 生 `<select>` | `<Select>` 金型を使うこと |
| 生 `<input type="text"\|"search"\|省略>` | `<TextField>` / `SearchBar` 等を使うこと |
| 自作タブ（className に `tab` 語を含む div/nav 等） | `<Tabs>` / `OverflowTabs` を使うこと |
| 色直値（`#xxx` / `rgba()`）のインラインスタイル | CSS 変数 `var(--color-*)` を使うこと（ADR-067）|
| 生 px 数値のインラインスタイル（例 `width: 24`）| デザイントークン `var(--size-*)` を使うこと（ADR-067）|

---

## どうしても生実装が必要な場合の例外コメント

```jsx
{/* ui-allow: <理由> (#<課題番号>) */}
<select value={x} onChange={f}>
```

**書式ルール（両方必須・どちらか欠けると無効＝赤のまま）:**
- `<理由>`: 空でない文字列で理由を明記する
- `(#<番号>)`: GitHub Issue / 課題番号を `#123` 形式で記載する

**番号体系**: 課題番号は GitHub Issue 番号を使用する（例: `#144`）。
仮番 `#0` の使用は禁止。番号が未発番の場合は Issue を立ててから使う。
※ 番号体系は要確認（PR 説明参照）。

---

## 新規 ui-allow の扱い

- 関所は HEAD で新規に増えた `ui-allow` を `⚠️ 新規ui-allow ◯件` として別枠表示する
- 人間（PO/レビュアー）のレビュー必須。CC が貼るだけで素通りはできない

---

## 参照

- ADR 本文: `docs/adr/ADR-144-ui-component-governance.md`
- CIゲート: `scripts/check-ui-governance.js`
- 自動テスト: `scripts/tests/test-ui-governance.js`
- ワークフロー: `.github/workflows/ui-governance-gate.yml`
