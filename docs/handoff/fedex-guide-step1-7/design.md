# design: FedEx ETD ガイド Step 1-7 新設（CarrierCredentialForm 埋め込み・第2段）

## 参照

- recon: `docs/handoff/fedex-guide-step1-7/recon.md`
- ADR-027: `docs/adr/ADR-027-ui-internationalization.md`（i18n 強制）
- ADR-067: `docs/adr/ADR-067-design-token-enforcement.md`（CSS 変数強制）

---

## KGI

「第2段完了」= FedEx ETD セットアップガイドのステップ1に 1-7 が追加され、ガイド内で直接テスト鍵を登録できる。1-6 まで完了したユーザーがページ遷移なしに鍵入力フォームへ進め、保存成功後に「ステップ2へ進む」ボタンが現れる。

| 基準 | 検証方法 |
|---|---|
| 1-7 タブが tablist の末尾に表示される | 手動: `/management-center/integrations/fedex?guide=true` でガイド表示 → 1-7 タブを確認 |
| 1-7 の右詳細パネルに CarrierCredentialForm が表示される | 手動: 1-7 タブをクリック → フォームが展開されること |
| フォームに carrier=fedex / env=sandbox が渡る | 手動: フィールドラベルが「API キー」「シークレットキー」「アカウント番号」になること |
| 1-6 の「ステップ2へ進む」ボタンが消えている | 手動: 1-6 タブ表示時にボタンがないこと |
| 保存成功前は「ステップ2へ進む」が非表示 | 手動: 1-7 タブ到達時、フォームのみ表示（ボタンなし）|
| 保存+接続テスト成功後に「ステップ2へ進む」が出現 | 手動: 保存成功 → バッジ表示 → ボタン出現 → クリックでステップ2へ遷移 |
| lint/TS エラーなし | CI: Frontend lint & custom checks |
| tenant_id 未送信（IDOR 対策不変） | コードレビュー: CarrierCredentialForm の API 呼出に `tenant_id` がないこと |

---

## 外部・過去事例の参照と我々への応用

第1段（#2601）で切り出した `CarrierCredentialForm` を再利用する初の事例。
「フォームを独立コンポーネントにしてガイドから呼び出す」パターンは、Notion / Linear 等の SaaS オンボーディングで一般的な手法（セットアップウィザード内にフォームを埋め込む）。
第1段の設計（onSaved/onCancel コールバック分離）がこの再利用を実現しており、第2段は追加実装ゼロでフォーム本体を再利用できている。

---

## 設計詳細

### SubstepPane の拡張（最小変更）

```typescript
// SubstepItem に children を追加（既存フィールドは変更なし）
interface SubstepItem {
  label: string;
  descriptions: string[];
  screenshots: Array<{ src: string }>;
  children?: ReactNode;  // NEW
}

// SubstepPane に canAdvanceFromLast を追加（デフォルト true で後方互換）
function SubstepPane({
  canAdvanceFromLast = true,  // NEW
  ...
})
```

`canAdvanceFromLast` のデフォルトを `true` にすることで、既存の SubstepPane 呼び出し（他のステップ・将来の拡張）への影響ゼロ。

### 保存フロー

```
ユーザー → 「保存してテスト」クリック
  → CarrierCredentialForm.handleSaveAndTest()
    → PUT /integrations/carriers/fedex/credentials (sandbox)
    → POST /integrations/carriers/fedex/test-connection?environment=sandbox
    → onSaved() 呼び出し
      → GET /integrations/carriers/fedex/status?environment=sandbox
      → setSandboxStatus(...)
      → setSandboxFormSaved(true)  ← 「ステップ2へ進む」出現条件
    → onCancel() 呼び出し
      → setShowCredentialForm(false)  ← フォームを非表示に
  → フォーム → 成功バッジ
  → 「ステップ2へ進む」ボタン表示
```

### env = sandbox 固定の根拠

ステップ1は「FedEx Developer Portal でテストプロジェクトを作成し、テスト鍵を取得する」フェーズ。
production 鍵は ETD go-live 時（別フロー）に登録するため、このフォームは sandbox 固定とする。

---

## 影響ファイル一覧

| ファイル | 変更種別 | 内容 |
|---|---|---|
| `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx` | 修正 | SubstepItem 拡張・SubstepPane prop 追加・state 2本追加・1-7 substep 追加・CarrierCredentialForm import |
| `frontend/src/locales/ja.json` | 修正 | `fedexEtdGuideStep1_7` キー追加 |
| `frontend/src/locales/en.json` | 修正 | `fedexEtdGuideStep1_7` キー追加 |

**触れないファイル**:
- `backend/` — 不変（API エンドポイント不変）
- `migrations/` — 不変
- `.github/workflows/` — 不変
- `frontend/tests-e2e/` — FedEx ガイド専用 spec なし（手動確認）
- `frontend/src/pages/integrations/CarrierCredentialForm.tsx` — 不変（第1段の実装をそのまま再利用）
