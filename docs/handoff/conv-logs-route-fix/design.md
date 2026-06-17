# 設計 — conv-logs-route-fix

**対象ADR**: ADR-096  
**recon**: docs/handoff/conv-logs-route-fix/recon.md  
**日付**: 2026-06-17  
**担当**: Terminal CC

---

## 外部・過去事例の参照と我々への応用

該当なし：FastAPI ルーターのパス文字列ミス（1行修正）のため外部事例参照は不要と判断。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `GET /api/v1/companies/6/conv-logs` が 404 ではなく 200 を返す | `pytest tests/test_company_conv_logs.py::test_conv_logs_route_path_is_companies_prefixed` |
| 既存の関数レベルテスト3件が引き続き PASS | `pytest tests/test_company_conv_logs.py` |
| 他の companies エンドポイント（CRUD）が壊れていない | `pytest tests/test_companies.py` |

---

## 技術 How・KPI

- KPI: 会社詳細「会話履歴」タブのエラー表示が解消される（HTTP 404 → 200）
- 技術選択: `companies.py:1032` の `"/{company_id}/conv-logs"` を `"/companies/{company_id}/conv-logs"` に変更（1行修正）

---

## 弊害・トレードオフ

- 既存クライアントが旧パス `/api/v1/6/conv-logs` を直接叩いていた場合は 404 になる → 調査済み、該当なし（フロントの呼び出し箇所は `CompanyConvLogsTab.tsx:49` の1箇所のみ）

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `companies.py:1032` ルートパス修正 | Generator |
| 2 | `test_company_conv_logs.py` にルートパス検証テスト追加 | Generator |

---

## 継続

- 完了後の監視: 本番で会話履歴タブが正常表示されることを確認（companyId=6）
- 次フェーズへの引き継ぎ: なし（単発バグ修正）
