# PARITY-03 ProductMasterDrawer FE — design.md

作成日: 2026-09-03  
ブランチ: release/parity03-product-master-drawer-fe  
参照: docs/handoff/parity03-product-master-drawer-fe/recon.md  
対象ADR: ADR-154（GAS→Python マイグレーション方針）、ADR-067（CSS デザイントークン）

---

## 外部・過去事例の参照と我々への応用

- 今回は GAS ProductMasterDrawer.tsx の直接移植のため、外部設計参照は不要。
  GAS 実装（google.script.run → api.get/api.post 差し替え）を唯一の設計根拠とする。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| PRODUCT_MASTER_UNREGISTERED のアイテムで「修正する」ボタンが表示される | Shingo 画面確認 |
| ボタン押下で商品マスタ新規登録フォームが開く（RegistrationSection） | Shingo 画面確認 |
| PRODUCT_ID_UNRESOLVED のアイテムで検索KW追記フォームが開く（SearchKeywordSection） | Shingo 画面確認 |
| EXCLUDED のアイテムで除外対象メッセージが表示される（ExcludedSection） | Shingo 画面確認 |
| マスタ課題のないアイテムには「修正する」ボタンが表示されない | Shingo 画面確認 |
| バックドロップクリックでドロワーが閉じる | Shingo 画面確認 |
| 登録完了後に「登録が完了しました」メッセージが表示される | Shingo 画面確認（B-3 API 結線後） |
| KW追記完了後に「検索キーワードを追記しました」が表示される | Shingo 画面確認（B-5 API 結線後） |

---

## 技術 How・KPI

- CSS クラスプレフィックス `pmd-*` でスコープ分離（既存 CSS との衝突なし）
- コンポーネントローカルトークン: `--pmd-max-w: 480px`、`--pmd-textarea-min-h: 72px`
- ADR-067: 全 CSS 値を CSS 変数（`var(--...)`）で記述。ハードコード値禁止

---

## 弊害・トレードオフ

- mark / english_title フィールドは BE migration 完了まで空文字列で送信される（nullable）
- Playwright E2E が全停止中（if: false / 2026-06-01〜）のため自動テストなし → Shingo 画面確認で代替

---

## 維持の仕組み

- ADR-067 CSS チェック（CI）で design token 逸脱を自動検出
- stylelint `no-descending-specificity` で CSS 特異度の逆転を自動検出
- BE API 変更時は ProductMasterDrawer.tsx の API パスと型定義を合わせて更新

---

## 将来の差し替え予定（TODO）

### EXCLUDED モードの案内文（ExcludedSection）

現在の文言:
> 除外キーワードの確認・変更は 商品マスタV2 シートの Exclude Keywords 列から直接行ってください。

この文言は GAS 実装の移植どおりだが、**サーバー移行完了後は誤った案内になる**。  
除外キーワードをサーバー側（管理画面 or API）で編集できるようになった時点で  
`ProductMasterDrawer.tsx:373-374` の文言を差し替えること。

差し替えトリガー: 除外キーワード編集 API（`PATCH /tcg/products/:id/exclude-keywords` 相当）が実装されたとき。
