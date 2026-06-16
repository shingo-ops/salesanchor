# FedEx Label Validation 申請 — 準備チェックリスト

**作成日**: 2026-06-16  
**参照 recon**: docs/handoff/fedex-label-validation-readiness/recon.md  
**参照 ADR**: ADR-123 / ADR-125 / ADR-129  
**ETD ステータス**: APAC 回答待ち（`docs/handoff/fedex-etd-adr-draft/fedex-apac-questions.md`）

---

## 凡例

| マーク | 意味 |
|---|---|
| ✅ 完了 | 実装・設定済み（file:line 確認済み） |
| 🟡 ETD 非依存・未完了 | 今すぐ着手できる |
| 🔴 ETD 依存 / APAC 待ち | APAC 回答 or Shingo 判断後に着手 |
| 🔑 Shingo 操作必須 | CC では完結しない（外部操作・法務等） |

---

## 今すぐ準備できるもの（ETD 非依存）

### グループ A: バックエンド API（実装追加が必要）

| # | 作業 | 根拠 | ファイル（変更予定） |
|---|---|---|---|
| A1 | サンプルラベル PNG 発行 — lv_issue_sample_labels に label_image_type="PNG" 呼び出しを追加 | `backend/app/services/fedex_ship.py:69` — create_shipment() は PNG 対応済み。エンドポイント未ワイヤリング（`backend/app/routers/shipping.py:691`） | backend/app/routers/shipping.py |
| A2 | サンプルラベル ZPL 発行 — lv_issue_sample_labels に label_image_type="ZPLII" 呼び出しを追加 | 同上。ZPL は印刷機テスト（V6）に必須。バイナリのため Content-Type: application/zpl に注意 | backend/app/routers/shipping.py |
| A3 | LVSamplesResponse に png_base64 / zpl_base64 フィールド追加（または形式別 endpoint 分割） | 現状 pdf_base64 のみ（`backend/app/routers/shipping.py:681-688`）。ZPL はバイナリ → Base64 でも可 | backend/app/routers/shipping.py |

### グループ B: フロントエンド（実装追加が必要）

| # | 作業 | 根拠 | ファイル（変更予定） |
|---|---|---|---|
| B1 | Step 2: PNG / ZPL ダウンロードボタン追加 | `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:92-98` — 現状 PDF ダウンロードのみ | frontend/src/pages/integrations/FedexLabelValidationTab.tsx |
| B2 | EULA / Disclaimer テキスト UI の追加（ADR-123 D5） | 申請スクショ V5 に必須。ETD 非依存。EULA 本文は法務レビュー後に確定 | frontend/src/pages/integrations/ 以下（新規 or 既存） |
| B3 | FedEx サービス表示スクリーン（申請スクショ用） | 申請スクショ V5 に必須。現状 FedExRateModal.tsx（`frontend/src/components/FedExRateModal.tsx`）はあるが申請専用スクショ画面は未整備 | 要検討 |

### グループ C: Shingo 操作（今すぐ着手可）

| # | 作業 | 根拠 |
|---|---|---|
| C1 | FedEx Sandbox アカウント番号を CarrierIntegrationPage の Sandbox タブに登録 | `frontend/src/pages/integrations/CarrierIntegrationPage.tsx:64` — Sandbox タブ実装済み。tenant_4 で操作可 |
| C2 | 物理ラベル印刷 + 600DPI スキャン（V6） | `docs/research/fedex-integrator-provider-application-2026-06-09.md:111` — 実機必須。PDF/PNG/ZPL を実際に印刷してスキャン |
| C3 | EULA 本文の法務確認 | ADR-123 D5 — "EULA 本文は法務レビュー前提" |
| C4 | PIW / Integrator Validation Cover Sheet 記入内容の最終確認 | cover sheet 自動生成あり（`backend/app/services/label_validation.py:109`）。Shingo が内容承認してから送付 |

### グループ D: 実装済み（確認のみ）

| # | 確認事項 | 状態 | file:line |
|---|---|---|---|
| D1 | FedEx Ship API（create_shipment）実装 | ✅ 完了 | `backend/app/services/fedex_ship.py:57` |
| D2 | FedEx Pickup API（create_pickup / check_pickup_availability）実装 | ✅ 完了 | `backend/app/services/fedex_ship.py:198` / `backend/app/services/fedex_ship.py:295` |
| D3 | OAuth トークン管理（get_or_refresh_token）実装 | ✅ 完了 | `backend/app/services/fedex_rates.py:230` |
| D4 | Sandbox / Production 認証情報個別管理 | ✅ 完了 | `migrations/20260612_200000_fedex_creds_unique_env.sql:1` |
| D5 | サンプルラベル PDF 発行（lv_issue_sample_labels） | ✅ 完了 | `backend/app/routers/shipping.py:686` |
| D6 | カバーシート PDF 自動生成（generate_cover_sheet_pdf） | ✅ 完了 | `backend/app/services/label_validation.py:109` |
| D7 | FedEx 公式カバーシートテンプレート同梱 | ✅ 完了 | `backend/app/services/label_validation.py:39` |
| D8 | 申請メール文面（generate_email_template） | ✅ 完了 | `backend/app/services/label_validation.py:222` |
| D9 | 9 ステップウィザード UI（FedexLabelValidationTab） | ✅ 完了 | `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:49` |
| D10 | 請求書 PDF（HS コード表示含む） | ✅ 完了 | `backend/app/services/invoice_renderer.py:435` |

---

## APAC 回答待ちのもの

| # | 作業 | ブロッカー | 詳細 |
|---|---|---|---|
| E1 | ETD（etdDetail）の実装（fedex_ship.py 拡張） | APAC Q1: ETD が Label Validation に必須か | `backend/app/services/fedex_ship.py:57-133` に etdDetail なし |
| E2 | レターヘッド / 署名アップロードエンドポイント（POST /ship/v1/shipments/images 呼び出し） | APAC Q2: docId 再利用可否 / APAC Q3: 有効期限 | 設計依拠点: `docs/handoff/fedex-etd-adr-draft/adr-draft.md` |
| E3 | fedex_etd_images テーブル migration | APAC Q2 / Q3 回答 + Shingo GO（G1）| ADR-ETD-draft §J1 |
| E4 | stampType（INCLUSIVE/EXCLUSIVE）実装判断 | APAC Q4 回答 | どちらでも Label Validation 合否に影響しないか不明 |
| E5 | FedEx アカウント側 Paperless Trade 有効化 | APAC Q5 回答 + Shingo 操作（G3）| FedEx.com GUI 操作 — CC では実行不可 |
| E6 | Commercial Invoice（FedEx フォーム 057P）実装要否 | APAC Q6: ETD 有の場合の提出物リスト確認 | 現状 invoice_renderer.py は FedEx CI 未対応 |
| E7 | ETD ADR 正式起案 | E1〜E6 の回答揃い次第 | `docs/handoff/fedex-etd-adr-draft/adr-draft.md` → `docs/adr/ADR-XXX-fedex-etd.md` |
| E8 | Sandbox ETD 動作確認 | E1〜E5 完了後 | Shingo 操作必須（G4）|

---

## 優先着手順（APAC 回答待ちの間に進めるもの）

1. **C1: Sandbox アカウント番号登録**（Shingo 操作・最優先。A1/A2 テストの前提）
2. **A1+A2: PNG/ZPL ラベル発行のワイヤリング**（BE 変更・ETD 非依存・提出物 V2/V3 を埋める）
3. **B1: PNG/ZPL ダウンロードボタン追加**（FE 変更・A1/A2 の UI 側）
4. **C2: 物理ラベル印刷 + スキャン**（Shingo 操作・A1〜B1 完了後に実施）
5. **C3: EULA 本文 法務確認**（Shingo 操作・並行可）
6. **B2+B3: EULA UI / FedEx サービス画面**（C3 法務確認後に実装・ETD 非依存）

---

## APAC 回答後のフロー

```
APAC Q1 回答
  → ETD 必須 → ETD ADR 正式起案 → E1〜E8 順次実施
  → ETD 任意 → E6 のみ判断（CI 要否）→ E7/E8 不要または軽量化
```

---

## 参照元

- recon: docs/handoff/fedex-label-validation-readiness/recon.md
- ADR-123: `docs/adr/ADR-123-carrier-integrator-provider.md`
- ADR-125: `docs/adr/ADR-125-fedex-rates-stage1.md`
- ADR-129: `docs/adr/ADR-129-fedex-label-validation-wizard.md`
- ETD ドラフト: `docs/handoff/fedex-etd-adr-draft/README.md`
- APAC 質問: `docs/handoff/fedex-etd-adr-draft/fedex-apac-questions.md`
- 申請要件: `docs/research/fedex-integrator-provider-application-2026-06-09.md`
