# Phase B-1 設計 — FedEx 連携ガイド骨格

**対象ADR**: ADR-129  
**recon**: docs/handoff/fedex-guide-b1/recon.md  
**日付**: 2026-06-13  
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

- 該当なし: 今回は既存コンポーネント（FedexLabelValidationTab）の構造拡張であり、外部ライブラリや新規設計パターンの調査は不要。ADR-129 の J4（既存タブ内実装）と ADR-067（デザイントークン）を正本として、2部構成の骨格を追加するのみ。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 連携ガイドタブに2部構成が表示される | FedEx設定ページで「連携ガイド」タブを開き目視確認 |
| 第1部に「API接続・審査不要」の説明と6プレースホルダ手順がある | タブ内に lv-part 第1部セクションが存在することを目視確認 |
| 第2部に既存9ステップの Label Validation 機能が残っている | タブ内に lv-part 第2部 + Step 1〜9 が存在することを目視確認 |
| 既存ボタン操作が壊れていない（テストラベル発行・DL・カバーシート・メール文面・mailto）| 各ボタンを操作して機能確認 |
| API連携設定タブは既存挙動のまま | タブ切り替え後、認証情報カードが正常表示されること |
| DHL / UPS ページに影響なし | DHL・UPS の各連携ページを開いて崩れなしを確認 |
| Light / Dark 両モードで崩れなし | Playwright SS 6枚で目視確認 |
| migrations / deploy.yml / 本番 scripts 変更なし | PR diff に含まれないことを確認 |
| npm run check:css-colors PASSED | CI または手動実行でPASS |
| npm run check:css-values PASSED | CI または手動実行でPASS |
| npm run check:dark-parity PASSED | CI または手動実行でPASS |
| npm run check:stylelint PASSED | CI または手動実行でPASS |

---

## 技術 How・KPI

- KPI: 連携ガイドタブが2部構成で表示され、既存9ステップが全て残っていること
- 技術選択:
  - `lv-wizard` をルートとして維持し、`lv-part` + `lv-part__header` で2部を区切る
  - 既存 lv-* CSS を一切削除しない（append only）
  - 第1部の各手順は既存 `lv-step card` + `StepHeader` を再利用
  - プレースホルダは `lv-placeholder-card` div + `data-screenshot` 属性で後差し替え可能な DOM 構造
  - CarrierIntegrationPage.tsx は変更しない（対象外）
  - 新規 i18n キーは `carrierIntegration.fedexGuide*` 名前空間で追加（既存 lv* キーは不変）

---

## 弊害・トレードオフ

- Step 6（接続テストを実行）はタブ切り替えコールバックを持たないため、テキスト案内のみ。B-2 以降で CarrierIntegrationPage への prop 追加で改善可能
- Part 1 の 6 ステップと Part 2 の 9 ステップがそれぞれ Step 1〜N を持つため、ページ内に「Step 1」が2つ存在する。セクション見出しで文脈を明示することで対応

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | recon.md / design.md 作成 | Generator |
| 2 | ja.json / en.json に fedexGuide* キー追加 | Generator |
| 3 | FedexLabelValidationTab.tsx を2部構成に更新 | Generator |
| 4 | FedexLabelValidationTab.css に lv-part / lv-placeholder-card 追加 | Generator |
| 5 | 検証コマンド実行 + Playwright SS 取得 | Evaluator |

---

## 継続

- 完了後の監視: /management-center/integrations/fedex の連携ガイドタブで表示確認
- 次フェーズ（B-2）への引き継ぎ: Part 1 Step 6 の「API連携設定タブへ」ボタンの機能化 / 本物スクリーンショット差し替え
