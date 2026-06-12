# 設計 — fedex-label-validation-wizard

**対象ADR**: ADR-129  
**recon**: docs/handoff/fedex-label-validation-wizard/recon.md  
**日付**: 2026-06-12  
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

- FedEx Developer Portal: Label Validation プロセス（公式手順）→ 9 ステップをウィザード化
- FedEx 公式 Cover Sheet v7.0（Label-Cover-Sheet-form.pdf）→ pypdf オーバーレイで自動入力、PDF を手動で作らなくて済む
- 既存 fedex-rates-stage1 / fedex-ship-stage2 の環境分離パターン → `environment` カラムを credentials に追加して本番/Sandbox を独立管理

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| FedEx 以外（DHL/UPS）は environment が常に production で保存される | `pytest tests/test_carrier_integrations.py::test_save_forces_production_environment_for_non_fedex` |
| FedEx sandbox 認証情報が独立して保存できる | `pytest tests/test_carrier_integrations.py::test_save_fedex_sandbox_environment` |
| Migration が冪等（2 回実行でエラーなし） | CI Migration SQL Test（冪等性チェック） |
| カバーシート PDF に全フィールドが入力される | サンプル PDF 目視確認（generate_cover_sheet_pdf ローカル実行） |
| テストラベル発行エンドポイントが Sandbox 認証情報なしで 422 を返す | `pytest tests/test_label_validation.py` |
| i18n キーが ja/en で一致する | `pytest tests/test_i18n_keys.py` |

---

## 技術 How・KPI

- KPI: Label Validation 申請ステップをアプリ内で完結（外部ツール不要）
- pypdf + reportlab overlay: AcroForm なし PDF にテキストを正確な座標で描画
- 座標は pdfminer で実測（account_number: y=449, production_api_key: y=426 等）
- 日本語フォントは `po_renderer.register_japanese_font()` を流用

---

## 弊害・トレードオフ

- UNIQUE 制約変更は本番デプロイ前に migration 適用必須 → `run_all_migrations.sh` に登録済み
- pypdf ライブラリ追加（純 Python、MIT）→ イメージサイズ微増（許容範囲）

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | DB migration + carrier_credentials.py 環境分離 | Generator |
| 2 | shipping.py 3 エンドポイント追加 | Generator |
| 3 | FedexLabelValidationTab.tsx 9 ステップウィザード | Generator |
| 4 | FedEx 公式フォーム pypdf 実装 | Generator |
| 5 | CI 修正（ADR index / migration guard / テスト） | Generator |

---

## 継続

- 完了後の監視: /api/health + FedEx 見積もり smoke（quotes=4）でデプロイ後確認
- 次フェーズへの引き継ぎ: Label Validation 申請後の Production Key 有効化確認フローは別タスク
