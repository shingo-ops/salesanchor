# Phase 3 設計 — FedEx設定ページ配色統一（PR-A3）

**対象ADR**: ADR-067  
**recon**: docs/handoff/fedex-pr-a3/recon.md  
**日付**: 2026-06-13  
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

- 該当なし：今回は既存デザイントークン（ADR-067）への寄せ作業であり、外部ライブラリや過去事例の調査は不要。受信箱（/lead-chat）の実装を正本とし、FedEx設定ページの非標準 `--color-*` 変数を標準トークンへ機械的に置換する方針。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| FedExRateModal に `--color-*` 変数が残存しない | `grep "color-" src/components/FedExRateModal.tsx` → 0件 |
| CarrierIntegrationPage.css が全カラーをトークン参照 | `npm run check:css-colors` PASSED |
| FedexLabelValidationTab.css が全カラーをトークン参照 | `npm run check:css-colors` PASSED |
| `.success-message` が定義される（以前は未定義） | `grep "success-message" src/components.css` → 定義あり |
| ダークモード変数パリティ合格 | `npm run check:dark-parity` PASSED（113変数対応済み）|
| stylelint 違反ゼロ | `npm run check:stylelint` PASSED |
| ADR-067 ハードコード値チェック合格 | `npm run check:css-values` PASSED |
| ライト/ダーク両モードで色崩れなし | Playwright SS 6枚（/tmp/pr-a3-ss/）で目視確認済み |

---

## 技術 How・KPI

- KPI: PR差分ファイルの `--color-*` 参照ゼロ（達成）
- 技術選択: inline style の変数名置換のみ（構造変更なし）。新規 CSS ファイルで未定義クラスを定義。`components.css` に `success-message` / `form-hint` を追加（広範囲で使用中）。

---

## 弊害・トレードオフ

- `--info-bg` / `--info-text` は `--color-blue-*` より意味的であり、テーマ変更時の一括更新が容易になる
- `success-message` の新定義により、保存完了メッセージが緑背景で表示される（旧来は無スタイルのプレーンテキスト）

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | FedExRateModal.tsx の `--color-*` 全置換 | Generator |
| 2 | CarrierIntegrationPage.css 新規作成（carrier-env-card* 系）| Generator |
| 3 | FedexLabelValidationTab.css 新規作成（lv-* 系）| Generator |
| 4 | components.css に success-message / form-hint 追加 | Generator |
| 5 | 全フロントチェック実行・Playwright SS 取得 | Evaluator |

---

## 継続

- 完了後の監視: 本番デプロイ後に `/management-center/integrations/fedex` の表示確認
- 次フェーズへの引き継ぎ: Part B-1（連携ガイドタブの中身実装）は別PR
