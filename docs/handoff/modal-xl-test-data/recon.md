# Modal xl テスト用サンプルデータ

PR #1827 (`feature/morimoto/modal-xl-replacements`) の Evaluator 再検証のために作成。

## 作成したデータ

| 種別 | 内容 |
|------|------|
| テナント | `tenant-review` (tenant_006, id=6) |
| 会社 | デモ商事株式会社（company_code: DEMO-001, id=11） |
| 受注 | DEMO-2026-001（order id=29, ¥150,000, status=completed） |

## データ作成 SQL（冪等・再実行可能）

```sql
-- テナントコンテキストを設定してから実行
SET app.tenant_id = '6';

-- 会社（既存あれば何もしない）
INSERT INTO tenant_006.companies (tenant_id, company_code, name, name_en, status)
VALUES (6, 'DEMO-001', 'デモ商事株式会社', 'Demo Shoji Co.', 'active')
ON CONFLICT (tenant_id, company_code) DO NOTHING;

-- 受注（既存あれば何もしない）
INSERT INTO tenant_006.orders
  (tenant_id, company_id, contact_id, order_number, total_amount, status, notes, currency)
SELECT 6, id, NULL, 'DEMO-2026-001', 150000, 'pending',
       'モーダルUIテスト用サンプル受注', 'JPY'
FROM tenant_006.companies WHERE company_code = 'DEMO-001'
ON CONFLICT DO NOTHING;
```

VPS での実行方法:

```bash
source ~/.claude-access.env
ssh -i ~/.ssh/id_ed25519 ubuntu@$APP_VPS_IP \
  "docker exec astro-webapp-postgres-1 psql -U salesanchor_app -d jarvis_db -c \"<上記SQL>\""
```

## 受注系 UI 検証時の使い方

- **ログイン情報**: `review@salesanchor.jp` / `setup_review_tenant.py` 実行で新パスワード生成
- **受注番号**: DEMO-2026-001 を検索
- **発送詳細ボタン**・**仕入詳細ボタン** → 操作列から開く

## Evaluator 検証結果（PR #1827、2026-06-10）

PR ブランチ `feature/morimoto/modal-xl-replacements` のローカル dev サーバー（port 5201）で Playwright 検証を実施。

### ShippingDetailPanel

| 項目 | 結果 |
|------|------|
| xl Modal で開く | OK（`comp-modal-dialog comp-modal-dialog--xl`） |
| 実測幅 | 880px（`--modal-wide-w` と一致） |
| aria-modal="true" | OK |
| タイトル表示 | "配送 — DEMO-2026-001" |
| Esc で閉じる | OK |
| フッター左: eLogi CSV ダウンロード | OK（無効時は disabled） |
| フッター右: キャンセル・登録 | OK |
| ボディスクロール | auto（overflow: auto） |

### PurchaseDetailPanel

| 項目 | 結果 |
|------|------|
| xl Modal で開く | OK（`comp-modal-dialog comp-modal-dialog--xl`） |
| 実測幅 | 880px |
| aria-modal="true" | OK |
| タイトル表示 | "仕入担当・取引 — DEMO-2026-001" |
| オーバーレイクリックで閉じる | OK |
| フッター: 確定・キャンセル・登録 | OK |

### 判定

**APPROVE** — xl Modal (880px) が正しく適用され、Esc・オーバーレイクリック閉鎖・aria-modal・フッターボタン配置すべて正常。
