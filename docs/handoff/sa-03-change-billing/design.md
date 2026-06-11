# 設計 — sa-03-change-billing

**対象ADR**: ADR-127  
**recon**: docs/handoff/sa-03-change-billing/recon.md  
**日付**: 2026-06-12  
**担当**: Terminal CC

---

## 外部・過去事例の参照と我々への応用

- 事例1: Stripe の billing address 変更API — 旧 billing source を is_default=false に降格し新しいカードを default に昇格するパターン → 我々への応用: 旧billing行を UPDATE is_default=false 後に新行 INSERT is_default=true（案B）で同一トランザクション内で安全に切替
- 事例2: SaaS 請求先変更フォームの標準パターン — token-gated URL でテナント分離し、ワンタイムトークンで再送防止 → 我々への応用: HMAC-SHA256 トークン + used_at NOT NULL で使用済み無効化済み

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| TokenType.change_billing が Enum に存在する | `pytest tests/test_registration_token_schema.py::TestTokenTypeEnum::test_change_billing_valid` |
| ChangeBillingRequest スキーマが正常に動作する | `pytest tests/test_registration_token_schema.py::TestChangeBillingRequest` |
| POST /public/register/change-billing が旧行降格+新行INSERT する（案B） | CI pytest + `backend/app/routers/registration_tokens.py` のエンドポイント確認 |
| DB CHECK制約に change_billing が含まれる | `migrations/20260612_090000_extend_registration_tokens_change_billing.sql` の CI migration 実行 |
| /register/change-billing フロントルートが存在する | `frontend/src/App.tsx:119` ルート確認 |
| CompanyDetailPage に3種発行ボタンが表示される | 登録済み会社で add_address / change_billing ボタン表示確認（Playwright） |
| InboxKartePanel overflow menu に3種ボタンが表示される | overflow menu クリック → 3ボタン確認 |
| エラー時にエラーコードが返却される（日本語ハードコードなし） | invalid_token → 403 + `{"detail": "invalid_token"}` |

---

## 技術 How・KPI

- KPI: change_billing 経路でテナントがトークン以外から確定される件数 = 0
- 技術選択: 案B（降格+INSERT）— 案A（UPDATE only）より履歴保持 + is_default 一意性問題を回避
- ADR-072 準拠: db.commit() 直後に reset_tenant_context() 必須

---

## 弊害・トレードオフ

- 旧 billing 行は is_default=false で残るため addresses テーブルが肥大化する → 対策: 過去の請求書スナップショット（ADR-101 bill_to_snapshot）が保護されるため削除不要・設計上意図的

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | Backend: TokenType / ChangeBillingRequest / エンドポイント | Terminal CC |
| 2 | Frontend: RegisterChangeBillingPage / ルート / CompanyDetailPage / InboxKartePanel | Terminal CC |
| 3 | Migration: CHECK制約拡張 + run_all_migrations.sh 登録 | Terminal CC |
| 4 | Tests: スキーマユニットテスト追加（42テスト） | Terminal CC |

---

## 継続

- 完了後の監視: 本番反映後に `registration_tokens.type = 'change_billing'` のレコードが正しく登録されることを確認
- 次フェーズへの引き継ぎ: ソフトオープン（docs/plans/sa-progress/soft-open-announcement.md）は Shingo の告知 GO 後に実施
