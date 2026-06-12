# ADR-129: テナント向け FedEx Label Validation 申請支援ウィザード

**ステータス**: 採用  
**日付**: 2026-06-12  
**起案者**: Hikky-dev  
**承認者**: Shingo (PO)  

---

## 背景

FedEx 国際配送（IP / IE / IPE / FICP）を本番利用するには **Label Validation** 申請が必要。
現状、テナントは「サンドボックスでラベルを発行 → 印刷 → スキャン → カバーシートと共に FedEx へ申請」という
手順をすべて手動で行う必要があり、申請ハードルが高い。

新規テナントが **アプリ内だけで申請準備を一式完結** できる仕組みを整備する。

---

## 決定（J1〜J5）

### J1: 既存 FedEx 連携ページに環境セレクタを追加
- FedEx の連携設定ページ（`CarrierIntegrationPage`）に「本番 / Sandbox」タブを追加。
- テナントは **本番用・Sandbox 用の認証情報を個別に登録** できる。
- DHL / UPS は Label Validation 不要のため、本番固定のまま変更なし。

**却下案**: FedEx を別ページに分離 → 実装コスト大・UX 断片化のためナシ。

### J2: DB 一意制約を `(tenant_id, carrier, environment)` へ変更
- 旧制約: `UNIQUE (tenant_id, carrier)` → テナントあたり 1 キャリア 1 レコードしか持てない。
- 新制約: `UNIQUE (tenant_id, carrier, environment)` → 本番 / Sandbox を別行で保持。
- 移行: 既存行はすべて `environment = 'production'` のため重複なし（安全）。
- **本番デプロイ前に migration を必ず適用すること**（ADR-025 確認済み）。

### J3: カバーシートはブラウザ直接ダウンロード
- カバーシート PDF は **Google Drive に保存しない**（Label Validation 専用の一時文書）。
- `Content-Disposition: attachment` でブラウザに直接ストリーミング。

### J4: Label Validation ウィザードは既存 FedEx ページ内タブとして実装
- ページ上部に「API 連携設定」「Label Validation 申請支援」の 2 タブを追加（FedEx のみ）。
- DHL / UPS はタブなしで従来どおり。

### J5: Pilot テナントは tenant_4 のみ（初期）
- `require_permission("shipping.manage")` で admin ユーザーのみアクセス可。
- 汎用展開は Sandbox 動作確認後に別 ADR で判断。

---

## スコープ（3.1〜3.5）

| スプリント | 内容 |
|-----------|------|
| 3.1 | DB migration + 登録経路の環境対応（`carrier_credentials.py` / `integrations.py`） |
| 3.2 | テストラベル一括発行 UI（Sandbox 4 サービス） |
| 3.3 | カバーシート PDF 自動生成（reportlab / テナントプロフィール参照） |
| 3.4 | メール文面自動生成 |
| 3.5 | 9 ステップガイド統合（`FedexLabelValidationTab.tsx`） |

---

## 技術的制約

- `create_shipment` の `customs_clearance` は **国際便必須**（IP / IE / IPE / FICP はすべて国際便）。
- IPE のサービスタイプコードは `FEDEX_INTERNATIONAL_PRIORITY_EXPRESS`（`FEDEX_` プレフィックス必須）。
- カバーシート用日本語フォントは `po_renderer.register_japanese_font()` を再利用。
- `get_credentials` / `get_status` のデフォルト環境は `"production"` → 既存 Ship/Pickup ルーターへの後方互換を保つ。

---

## 関連 ADR

- ADR-021: キャリアアダプタ層設計
- ADR-025: 本番運用フェーズの手動 DB 操作禁止
- ADR-072: テナントコンテキスト reset ルール
- ADR-125: FedEx Account Number / environment 固定（本 ADR で environment 制約を緩和）
- ADR-128: FedEx Ship API / Pickup API
