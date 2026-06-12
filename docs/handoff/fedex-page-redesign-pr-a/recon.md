# recon — fedex-page-redesign-pr-a

**仕事名**: FedEx連携ページ改善 PR-A（設定タブUI整理＋タブ改名）  
**日付**: 2026-06-12  
**対象ADR**: ADR-129  
**担当**: Generator

---

## 既存ADR検索結果

- `git grep -i "fedex\|carrier\|label.validation" docs/adr/` で確認
- **ADR-129**: `docs/adr/ADR-129-fedex-sandbox-and-label-validation.md` — FedEx 本番/Sandbox 切り替え + Label Validation タブ追加（本PRの直接の対象）
- **ADR-125**: `docs/adr/ADR-125-fedex-account-number.md` — FedEx/UPS アカウント番号フィールド追加
- 他に関連ADRなし

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/pages/integrations/CarrierIntegrationPage.tsx:73` | `EMPTY_ENV_DATA` 定数（view/edit分離の状態管理基盤） |
| `frontend/src/pages/integrations/CarrierIntegrationPage.tsx:121` | `handleSaveAndTest` — 保存→自動接続テスト→バッジ更新ロジック |
| `frontend/src/pages/integrations/CarrierIntegrationPage.tsx:180` | `handleDeleteConfirmed` — 削除確認後の実行ロジック |
| `frontend/src/pages/integrations/CarrierIntegrationPage.tsx:203` | `tabIntegrationGuide` キー参照（タブ改名） |
| `frontend/src/pages/integrations/CarrierIntegrationPage.tsx:227` | `renderCard` 関数（view/edit/empty 3状態を分岐描画） |
| `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:49` | `FedexLabelValidationTab` — PR-A では変更なし（タブ参照のみ） |
| `frontend/src/locales/ja.json:225` | `tabIntegrationGuide: "連携ガイド"` — 新規i18nキー |
| `frontend/src/locales/ja.json:229` | `envCardTitleProd: "本番環境"` — カードタイトル |
| `frontend/src/locales/ja.json:231` | `statusOk: "接続OK"` — ステータスバッジラベル |
| `frontend/src/locales/ja.json:239` | `saveAndTest: "保存して接続テスト"` — 保存ボタンラベル |
| `frontend/src/locales/ja.json:243` | `deleteConfirmTitle: "認証情報を削除"` — 削除確認モーダルタイトル |
| `frontend/src/pages-layout.css:608` | `.carrier-env-card__header` — カードヘッダーレイアウト |
| `frontend/src/pages-layout.css:640` | `.carrier-env-card--empty` — 未登録カードスタイル |
| `frontend/src/pages-layout.css:649` | `.carrier-env-info-row` — 情報行レイアウト |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | `client_id_hint` のフォーマット（先頭4+末尾4か否か） | コード確認: バックエンドが返す hint をそのまま表示する仕様（フル値は送らない） | ✅ 解消済み |
| 2 | 他キャリア（DHL/UPS）への影響範囲 | `SUPPORTS_ENV_SELECT` set による分岐確認 — FedEx のみ2カード表示 | ✅ 解消済み |
| 3 | 既存E2Eテストの存在有無 | `frontend/tests-e2e/` 検索 — carrier/fedex 統合テストなし | ✅ 解消済み（更新不要） |

**未解決ゼロ確認**: 全て解消済み
