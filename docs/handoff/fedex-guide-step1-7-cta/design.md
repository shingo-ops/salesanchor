# design: fedex-guide-step1-7-cta

- recon 参照: `docs/handoff/fedex-guide-step1-7-cta/recon.md`
- 対象 ADR: ADR-027（UI 文字列 i18n 強制）

## KGI

| 基準 | 検証方法 |
|------|---------|
| 1-7 保存成功後（バッジ表示時）にCTAテキストが表示される | 目視確認 |
| ja/en 両方のキーが存在し非対称なし | CI i18n-check |
| 既存ロジック（フォーム・ボタン・進捗バー）に変更なし | コードレビュー |

## 設計

- 変更スコープ: FE のみ（バッジ直下に `form-hint` テキスト追加）
- 新規CSS不要: `form-hint` は既存クラスを流用
- migration/workflow 含まない

## 外部・過去事例の参照と我々への応用

UI の次ステップ誘導テキストは SaaS オンボーディング UX の定石。Stripe / Shopify 等の設定ウィザードでは各ステップ完了後に次のアクションを明示することで離脱率が低減される。本実装は同パターンの最小適用（バッジ直下に 1 行 CTA）。ADR-027 i18n 規約に従い ja/en 両キー必須。
