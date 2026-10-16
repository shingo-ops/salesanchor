# AY-5c recon: 色見本の「現在」の直書きを翻訳キーへ

- 作成: 2026-10-16 Opus / 基点 origin/main 91310d6db（AY-5b #4375 マージ後）
- 調査は Sonnet。生出力は /tmp/CC報告ファイル/ssot-radio/ay5c/（00〜02f）

## 既存 ADR 検索

- docs/adr/ADR-027-ui-internationalization.md: 画面の文字はすべて t("key") を通す。ja.json と en.json は同じキーを持つ。
- docs/specs/design-system/design.md §AY-5 の残件②「pages-layout.css の `.color-swatch-legacy::after` の直書き『現在』（ADR-027）」が今回の対象。

## 現在地

- frontend/src/pages-layout.css:330-339 `.color-swatch-legacy::after`。:331 が `content: "現在";`。ほかの宣言は position absolute・bottom -14px・left 50%・transform translateX(-50%)・font-size var(--font-2xs)・color var(--text-muted)・white-space nowrap。英語画面でも「現在」と出る。
- frontend/src の CSS で、日本語を content に持つ行はこの1件だけ（02b.txt）。
- frontend/src/pages/roles/RolesPage.tsx:465 は、色がパレットの外にあるときだけ描く。:466-470 は `<label className="color-swatch selected color-swatch-legacy" style={{background: roleForm.color}} title={t("roles.currentColorTitle", {color: roleForm.color})}>`。data-* の属性は無い。:471-476 は RadioControl。
- `.color-swatch` を使うのは RolesPage.tsx:467・:482 だけ。
- CSS の `content: attr(...)` の前例: frontend/src/components.css:470 `content: attr(data-tooltip);`。
- ロケール: frontend/src/locales/ja.json・en.json はネスト構造。"roles" は 2012 行。roles.color は 2022 行、roles.currentColorTitle は 2046 行（ja「現在の色（{{color}}）」/ en「Current color ({{color}})」）。roles の中に「現在」だけを値に持つキーは無い。
- 自動チェック: ESLint の no-japanese-literal は JSX と JS の文字列だけを見る。CSS は見ない。check:i18n-missing-keys も CSS を見ない（02f-scripts.txt）。
- RolesPage の試験・stories は無い。

## 未確認

- なし。
