# design: ETD セットアップガイド スクリーンショットはみ出し修正

参照 recon: docs/handoff/etd-guide-screenshot-fix/recon.md
対象 ADR: ADR-129, ADR-067

## 対応方針

### A: コンテンツ幅上限（根本対策）
`.etd-guide` に `max-width: var(--max-width-setup-guide)` + `margin-inline: auto` を追加。
`--max-width-setup-guide: 900px` を `frontend/src/tokens.css` の Layout constraints セクションに追加（ADR-067準拠）。

### B: 縦横比保険
`.etd-guide__screenshot` に `max-width: 100%` + `height: auto` を追加。
`width: 100%` と `display: block` は既存のまま維持。

### 触らない範囲
`.etd-stepper`（sticky 進捗バー）は変更しない。PR #2530 の固定挙動を維持。

## 受け入れ基準

| 基準 | 検証方法 |
|------|----------|
| 画面幅変更で横スクロール・はみ出しが発生しない | ブラウザ幅を 800px〜1920px で変化させ確認 |
| スクリーンショット内文字が読める大きさを保つ | 900px 幅でスクショを目視確認 |
| `.etd-stepper` の sticky 固定が維持されている | セットアップガイド画面でスクロールして進捗バーが追従することを確認 |
| lint: 0 errors / build: success | `npm run lint` + `npm run build` をローカル実行 |
| ADR-067: 生 px 値を使わない | `--max-width-setup-guide` トークン経由で var() 参照 |

## 外部・過去事例の参照と我々への応用

CSS の `max-width` + `margin-inline: auto` によるコンテンツ幅制限はブラウザ標準パターン。
MDN "max-width" ドキュメントおよび Bootstrap/Tailwind の `.container` 実装と同一手法。
`height: auto` + `max-width: 100%` はレスポンシブ画像の定番（MDN "Responsive images" に記載）。
本プロジェクトでは同様のパターンを `--max-width-form: 560px` (アカウント設定) / `--max-width-page: 1200px` (ページ全体) で採用済み。今回は専用トークン `--max-width-setup-guide: 900px` を追加して同一パターンを適用。
