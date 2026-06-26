# recon: FedEx ETD ガイド Step 1-7 新設（CarrierCredentialForm 埋め込み・第2段）

## 対象ファイル

- `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx`
- `frontend/src/locales/ja.json`
- `frontend/src/locales/en.json`

---

## SubstepPane の現状と変更点

### 現状（第1段完了後）

`frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:74-147`（SubstepPane コンポーネント）:

- `SubstepItem` は `{ label, descriptions, screenshots }` のみ
- サブステップ 1-1 〜 1-6 の 6件
- `isLast`（`activeIndex === substeps.length - 1`）のときだけ「ステップ2へ進む」ボタンを表示
- カスタムコンテンツ（フォーム等）を差し込む拡張ポイントなし

### 変更内容

| 変更箇所 | 種別 | 内容 |
|---|---|---|
| `SubstepItem.children?: ReactNode` | 型追加 | スクリーンショット後に任意コンテンツを差し込む拡張ポイント |
| `SubstepPane.canAdvanceFromLast?: boolean` | prop 追加 | `false` のとき最終ステップの advance ボタンを非表示（デフォルト `true`） |
| サブステップ 1-7 追加 | データ追加 | `children` に `CarrierCredentialForm` を配置 |
| `sandboxFormSaved` / `showCredentialForm` state | state 追加 | フォーム保存後のボタン表示制御 |

---

## 「ステップ2へ進む」の移動

- 旧: 1-6 が `isLast` → ボタン表示
- 新: 1-7 が `isLast` AND `sandboxFormSaved=true` → ボタン表示
- 1-6 のボタン表示は 1-7 追加により `isLast` が false になるため自動的に消える

---

## CarrierCredentialForm の利用方法（第1段との差異）

| prop | 値 | 理由 |
|---|---|---|
| `carrier` | `"fedex"` | ガイドは FedEx 専用 |
| `env` | `"sandbox"` | ステップ1はテスト鍵段階（production 鍵は ETD go-live 後） |
| `envLabel` | `t("carrierIntegration.fedexEtdGuideEnvironmentSandbox")` | 翻訳済みラベルを親から渡す（ADR-027）|
| `onSaved` | sandbox status 再取得 + `setSandboxFormSaved(true)` | 保存成功後に「ステップ2へ進む」を出現させる |
| `onCancel` | `setShowCredentialForm(false)` | 保存後フォームを非表示にし、成功バッジに切り替える |

`tenant_id` はバックエンド `get_current_tenant` で自動セット。フォームから送信しない設計は第1段から不変。

---

## i18n キー追加

`frontend/src/locales/ja.json:344`・`en.json:344` に `fedexEtdGuideStep1_7` を追加（`fedexEtdGuideStep1_6b` の直後）。

---

## E2E・テスト影響

既存の E2E spec に `fedex-setup` ガイド専用 spec なし（`grep` で未検出）。
CarrierCredentialForm は第1段で動作確認済み。手動確認が主な検証手段。
