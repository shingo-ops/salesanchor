# recon — PR-A4 接続テスト結果の保存・表示

**仕事名**: fedex-pr-a4  
**日付**: 2026-06-14  
**対象ADR**: ADR-123（キャリア連携基盤）/ ADR-129（FedEx拡張）  
**担当**: Hikky-dev

---

## file:line 引用表

| 引用先 | 確認内容 |
|--------|---------|
| `backend/app/routers/integrations.py:460` | POST /integrations/carriers/{carrier}/test-connection エンドポイント定義 |
| `backend/app/routers/integrations.py:481` | carriers.test_connection() 呼び出し後 CarrierTestResponse を返すのみ。DB書き込みなし |
| `backend/app/routers/integrations.py:488` | return CarrierTestResponse — これで終了。last_tested_at 系列の保存処理なし |
| `backend/app/routers/integrations.py:319` | CarrierTestResponse: ok / status_code / message の3フィールドのみ |
| `backend/app/services/carrier_credentials.py:51` | get_status() — 返すフィールド: configured / environment / client_id_hint / secret_configured / account_number_hint。last_tested 系列なし |
| `backend/app/services/carrier_credentials.py:167` | save_credentials() — INSERT/upsert。last_tested 系列列を含まない |
| `backend/tests/conftest.py:971` | テスト用 tenant_carrier_credentials テーブル定義: id / tenant_id / carrier / client_id_encrypted / client_secret_encrypted / environment / account_number_encrypted / updated_by_user_id / created_at / updated_at。last_tested 系列なし |
| `frontend/src/pages/integrations/CarrierIntegrationPage.tsx:52` | interface TestResult: ok / status_code / message の3フィールドのみ |
| `frontend/src/pages/integrations/CarrierIntegrationPage.tsx:78` | useState<TestResult>(null) — ページリロードで消える揮発状態 |
| `frontend/src/pages/integrations/CarrierIntegrationPage.tsx:125` | handleTest() — POST 後 setResult(res) するのみ。GET /status の再fetchなし |
| `frontend/src/pages/integrations/CarrierIntegrationPage.tsx:331` | result 表示: successMsg / failMsg + message + status_code |
| `frontend/src/pages/integrations/CarrierIntegrationPage.css:41` | .carrier-env-card__last-tested クラス定義あり（TSXでは未使用） |
| `docs/adr/ADR-123-carrier-integrator-provider.md:1` | ADR-123: Phase 0（接続テストページ）完了済み。テスト結果保存は未定義 |
| `docs/adr/ADR-129-fedex-label-validation-wizard.md:1` | ADR-129: Label Validation タブ追加。接続テスト結果保存への言及なし |
| `docs/adr/FEATURE-INDEX.md:17` | FedEx / carrier 関連: ADR-103 / ADR-123 / ADR-128 |

---

## ADR確認結果

```
git grep -i "接続テスト\|test.result\|last_tested" docs/adr/
```

- ADR-123: 接続テストページ（Phase 0）完了の記録あり。テスト結果の永続化は未定義
- ADR-129: 接続テストへの言及なし
- ADR-125: account_number_encrypted 追加（additive migration の前例）
- **接続テスト結果保存を定義する ADR は存在しない** → 今回 A4 で設計起案

---

## 現状のデータフロー（事実）

1. フロント handleTest() が POST /integrations/carriers/{carrier}/test-connection を呼ぶ（`frontend/src/pages/integrations/CarrierIntegrationPage.tsx:125`）
2. エンドポイントが carriers.test_connection() を呼ぶ（`backend/app/routers/integrations.py:481`）
3. CarrierTestResponse を返して終了（`backend/app/routers/integrations.py:488`）
4. フロントが useState に格納（揮発）し、画面に表示（`frontend/src/pages/integrations/CarrierIntegrationPage.tsx:78`）
5. DB への書き込みは一切発生しない
6. ページリロード後、接続テスト結果は消える

---

## POST /test-connection の現状

- DB保存していないこと: `backend/app/routers/integrations.py:488` の return 前に UPDATE/INSERT はない
- 成功・失敗結果はレスポンスで返るだけで永続化されない

## carrier credentials status の現状

- get_status() が返すフィールド（`backend/app/services/carrier_credentials.py:51`）: configured / environment / client_id_hint / secret_configured / account_number_hint
- last_tested_at / last_test_ok / last_test_message は存在しない

## テーブル定義の現状

- tenant_carrier_credentials のカラム（`backend/tests/conftest.py:971`）: id / tenant_id / carrier / client_id_encrypted / client_secret_encrypted / environment / account_number_encrypted / updated_by_user_id / created_at / updated_at
- last_tested 系列カラムは存在しない

## frontend の現状

- テスト結果は useState のみで保持（`frontend/src/pages/integrations/CarrierIntegrationPage.tsx:78`）
- リロード後に接続テスト結果は残らない
- .carrier-env-card__last-tested CSSクラスは存在する（`frontend/src/pages/integrations/CarrierIntegrationPage.css:41`）が、TSXでは未使用

---

## 不明点リスト

| # | 不明点 | 状態 |
|---|-------|------|
| 1 | 実装には tenant_carrier_credentials へのカラム追加 migration が必要か | ✅ 必要（last_tested 系列3カラム追加） |
| 2 | テスト結果は環境（production/sandbox）別に保持するか | ✅ 自動的に環境別（UNIQUE KEY が (tenant_id, carrier, environment)） |
| 3 | フロント表示更新タイミング | PO GO時に確定（設計案: GET /status 再fetch） |
| 4 | 未テスト状態の表示文言 | PO GO待ち |

**未解決: 2件**（実装 PR 前に PO 確認）
