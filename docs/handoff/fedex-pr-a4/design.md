# Phase A-4 設計 — 接続テスト結果の保存・表示

**対象ADR**: ADR-123（キャリア連携基盤）/ 新規 ADR 起案必要  
**recon**: `docs/handoff/fedex-pr-a4/recon.md`  
**日付**: 2026-06-14  
**担当**: Hikky-dev  
**実装待ち**: PO GO 必要（migration あり）

---

## 外部・過去事例の参照と我々への応用

該当なし。接続テスト結果の永続化は既存 additive migration（ADR-125: account_number_encrypted 追加）の踏襲。外部ライブラリ・新規設計パターン調査は不要。前例として migrations/20260612_200000_fedex_creds_unique_env.sql の命名方式と deploy.yml 登録方式を踏襲する。

---

## 1. KGI

- 接続テスト実行後、最終テスト時刻・結果・メッセージが DB に保存される
- ページ再読み込み後も最終テスト結果が表示される
- 成功 / 失敗 / 未テストの3状態がユーザーに分かる
- 既存の FedEx 認証情報保存・接続テスト動作を壊さない

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 接続テスト実行後に last_tested_at / last_test_ok / last_test_message が DB に保存される | pytest: test_connection 後 SELECT で確認 |
| ページリロード後も最終テスト結果が表示される | Playwright: テスト実行 → reload → 表示確認 |
| FedEx / DHL / UPS の3キャリア全てで保存される | pytest キャリア別ケース |
| sandbox / production 環境別に独立して保存される | pytest 環境別ケース |
| 未テスト状態では「未テスト」表示 | Playwright: 新規登録後リロードで確認 |
| 既存の接続テスト機能（POST）が壊れない | 既存 pytest が PASS のまま |
| migrations / deploy.yml の登録漏れがない | CI migration-guard.yml が PASS |
| DHL / UPS / PayPal ページに影響なし | 各ページを目視確認 |

---

## 2. DB設計案

以下の migration が必要（実装 PR 前に PO GO 必要）。

ファイル名例: migrations/20260614_HHMMSS_add_carrier_test_result.sql

```sql
-- public.tenant_carrier_credentials に接続テスト結果列を追加（additive-only）
ALTER TABLE tenant_carrier_credentials
  ADD COLUMN IF NOT EXISTS last_tested_at    TIMESTAMP NULL,
  ADD COLUMN IF NOT EXISTS last_test_ok      BOOLEAN   NULL,
  ADD COLUMN IF NOT EXISTS last_test_message TEXT      NULL;
```

注意:
- migration ありのため、実装 PR 前に PO GO が必要
- 既存行は全て NULL → データ消失リスクなし
- カラム追加（additive-only）→ backend/CLAUDE.md の migration 原則に適合
- deploy.yml への追記必須（migration-guard.yml が CI ブロック条件）
- このdocs-only PRでは migration は作成しない

---

## 3. Backend設計案

### save_test_result() 関数を carrier_credentials.py に追加

```python
async def save_test_result(
    db, tenant_id: int, carrier: str, environment: str,
    ok: bool, message: str
) -> None:
    """接続テスト結果を tenant_carrier_credentials に保存する。"""
    await db.execute(
        text("""
            UPDATE tenant_carrier_credentials
               SET last_tested_at = NOW(),
                   last_test_ok = :ok,
                   last_test_message = :msg
             WHERE tenant_id = :tid AND carrier = :c AND environment = :env
        """),
        {"tid": tenant_id, "c": carrier, "env": _norm_env(environment),
         "ok": ok, "msg": message},
    )
    await db.commit()
    reset_tenant_context()  # ADR-072 必須
```

### get_status() の拡張

返り値に last_tested_at / last_test_ok / last_test_message を追加。

### integrations.py の拡張

- carrier_test_connection() エンドポイントで test_connection 後に save_test_result() を呼ぶ
- 成功時: last_test_ok=True、短い成功メッセージを保存
- 失敗時: last_test_ok=False、失敗理由の短い文言を保存
- FedEx API 障害時でも失敗結果（ok=False、message 含む）を保存する
- API key / secret はログにも保存しない

### CarrierStatus モデルの拡張

last_tested_at / last_test_ok / last_test_message フィールドを追加。

---

## 4. Frontend設計案

### 表示更新方式: GET /status 再 fetch（第一候補）

- handleTest() 完了後に loadStatus() を呼び直し
- メリット: POST と GET の責務が明確、CarrierTestResponse を汚染しない
- デメリット: 1往復増える（許容範囲）

### CarrierIntegrationPage.tsx の変更

- CarrierStatus interface に last_tested_at / last_test_ok / last_test_message を追加
- 各環境カードに最終テスト結果を表示
- 既存の .carrier-env-card__last-tested（`frontend/src/pages/integrations/CarrierIntegrationPage.css:41`）を活用

### 表示状態

| 状態 | 表示文言 |
|------|---------|
| 未テスト（last_tested_at = NULL） | 未テスト |
| 成功（last_test_ok = True） | 最終テスト: YYYY/MM/DD HH:mm 成功 |
| 失敗（last_test_ok = False） | 最終テスト: YYYY/MM/DD HH:mm 失敗 |

i18n 対応が必要: ja.json / en.json に carrierIntegration.lastTested 系列キーを追加。

---

## 5. テスト方針

Backend（実装 PR で追加）:

- migration idempotency: ALTER TABLE 2回実行でエラーなし
- 成功時に last_tested_at / last_test_ok=true / message が保存される
- 失敗時に last_tested_at / last_test_ok=false / message が保存される
- GET /status に last_tested 系列が含まれる
- テナント分離: 別テナントの結果が混入しない
- conftest.py の tenant_carrier_credentials テーブルに3列追加が必要

Frontend（実装 PR で追加）:

- 未テスト状態の表示確認
- 成功状態の表示確認
- 失敗状態の表示確認
- 接続テスト後に status が再 fetch されることの確認
- リロード後も最終テスト結果が残ることの確認（Playwright）

---

## 6. リスクと対策

| リスク | 対策 |
|--------|------|
| migration ありのため PO GO 必須 | このdocs-only PR では migration を作成しない。実装 PR 前に PO 確認 |
| 本番既存テナントへの影響 | nullable column 追加のみ。既存行は NULL → データ消失なし |
| API key / secret の漏洩 | last_test_message に認証情報を含めない。test_connection() はすでにシークレット非返却（`backend/app/services/carrier_credentials.py:51`） |
| FedEx API 障害時 | 失敗結果（ok=False）を短い文言で保存する。通信エラーも ok=False で記録 |
| 接続テスト失敗時に credentials が削除・無効化されるリスク | save_test_result() は UPDATE のみ。DELETE はしない |

---

## 7. PO GO 待ち事項

実装 PR の前に以下を確認してください。

1. **tenant_carrier_credentials への3カラム追加 migration** を実装してよいか
2. **接続テスト後の表示更新方式**は GET /status 再 fetch でよいか
3. **未テスト状態の表示文言**は「未テスト」でよいか

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | migration SQL 作成 + deploy.yml 登録 | Generator（PO GO後） |
| 2 | save_test_result() 追加 + get_status() 拡張 | Generator |
| 3 | integrations.py エンドポイント拡張 + モデル更新 | Generator |
| 4 | frontend: CarrierStatus 拡張 + 表示追加 | Generator |
| 5 | conftest.py テーブル定義更新 + pytest 追加 | Generator |
| 6 | Playwright: テスト実行 → リロード → 表示確認 | Evaluator |

---

## 継続

- 完了後: /management-center/integrations/fedex の API連携設定タブで最終テスト日時表示を確認
- DHL / UPS は共通コンポーネントのため、同一実装で自動反映される
