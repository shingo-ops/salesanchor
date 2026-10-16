# AY-5c 設計: 色見本の「現在」の直書きを翻訳キーへ

- 作成: 2026-10-16 Opus（Planner・Architect を兼ねる自己審査）
- 現在地: docs/handoff/ay5c-swatch-current-i18n/recon.md
- 対象 ADR: ADR-027（i18n）

## 1. 目的

ロール編集で、今の色がパレットの外のとき、色見本の下に「現在」と出る。この文字は CSS に直接書いてあり、英語画面でも日本語で出る。これを翻訳キー経由にして、英語画面では「Current」と出るようにする。日本語画面の見た目と文字は変えない。2026-10-16 PO「y」。

## 2. 対象と対象外

- 対象: frontend/src/pages-layout.css:331、frontend/src/pages/roles/RolesPage.tsx:466-470、frontend/src/locales/ja.json・en.json（roles に1キー）、docs/specs/design-system/design.md（§AY-5c）。
- 対象外: ::after の位置・大きさ・色の宣言、ほかの色見本、CSS の日本語を自動で止める仕組み（今は1件だけで、その1件を今回なくすため）。

## 3. 変更前後

### 3-1 ロケール

- ja.json の "roles" の中、"currentColorTitle"（2046 行）の次に `"currentColorBadge": "現在",` を足す。
- en.json も同じ位置に `"currentColorBadge": "Current",` を足す。
- 前後の行のカンマの付き方を崩さない（JSON として正しいことを確かめる）。

### 3-2 RolesPage.tsx:466-470

```tsx
// 前
<label
  className="color-swatch selected color-swatch-legacy"
  style={{ background: roleForm.color }}
  title={t("roles.currentColorTitle", { color: roleForm.color })}
>
// 後（属性を1つ足すだけ）
<label
  className="color-swatch selected color-swatch-legacy"
  style={{ background: roleForm.color }}
  title={t("roles.currentColorTitle", { color: roleForm.color })}
  data-current-label={t("roles.currentColorBadge")}
>
```

- 実物の書き方（改行・引用符）に合わせる。ほかの行は触らない。

### 3-3 pages-layout.css:331

- `content: "現在";` → `content: attr(data-current-label);`
- 前例は frontend/src/components.css:470 `content: attr(data-tooltip);`。
- ほかの宣言（:332-338）は触らない。

### 3-4 docs/specs/design-system/design.md

- §AY-5b の後に `#### AY-5c 色見本の「現在」を翻訳キーへ（2026-10-16）` を足す。内容は PO 決定・変更（3-1〜3-3）・確認結果・設計リンク。§AY-5 の残件②は書き換えない（その時点の記録）。

## 4. 影響範囲

- `.color-swatch-legacy` は RolesPage.tsx:467 の1か所だけ（recon）。ほかの画面は変わらない。
- 日本語画面: 出る文字は「現在」のまま。位置・大きさ・色も同じ。
- 英語画面: 「現在」が「Current」になる。文字の幅が変わるが、white-space nowrap と中央寄せ（left 50%・translateX(-50%)）のままなので、色見本の下の中央に出る。
- API・DB は変わらない。

## 5. 代替案

- CSS をやめて JSX に span を置く: DOM と CSS の両方が変わり、見た目の前後確認が大きくなる。attr() は既存の前例があり、変更が最小で済む。

## 6. リスクと対処

- 属性を付け忘れると、::after が空になって「現在」が消える。→ 3-2 と 3-3 は同じコミットにする。実画面相当の描画で ::after の文字を確かめる（§7）。

## 7. 受入条件

| 基準 | 検証方法 |
|---|---|
| 日本語で ::after の文字が「現在」、英語で「Current」 | Playwright で色見本（label.color-swatch-legacy に data-current-label を付けたもの）を描き、`getComputedStyle(el, '::after').content` を ja と en で取得する。ビルドした CSS を使う（手本: docs/handoff/design-system-recon/evidence-20260910/ay5-measure.cjs の描き方） |
| 日本語で ::after の位置・大きさ・色が前後で同じ | 同じ描画で、前（origin/main の CSS）と後の ::after の font-size・color・bottom・left・transform を比べる。差は 0 |
| CSS の content に日本語が 0 件 | git grep（recon 02b と同じ条件） |
| ja.json と en.json のキーが一致 | npm run check:i18n-missing-keys など既存の i18n チェック |
| tsc・lint・build・check:all が exit 0 | 各コマンド |
| CI が緑 | PR の checks |

## 8. 維持の仕組み

- ADR-027 と、既存の i18n チェック（ja・en のキー一致）。CSS の日本語を止める専用の仕組みは作らない（今回で0件になるため）。
- 切り戻し: この PR の merge commit を revert する。

## 9. 外部・過去事例

- 外部事例: 不要。CSS の attr() は標準の書き方で、社内に前例（components.css:470）がある。
- 過去事例: data-tooltip（components.css:463-470）。

## 10. 設計審査（Opus 自己審査）

- 判定: APPROVE。
- 根拠: 変更前後を行番号付きで書いた。影響は1か所だけ。受入条件はすべて測定や grep で○×が決まる。PO の判断が要る点は無い（日本語の見た目と文字は変えず、英語の訳語「Current」は既存キー companies.currentValue・superAdmin の currentLabel の en と同じ）。
- 未解決事項: なし。
