# 設計 — fix-supplier-channel-name

**対象ADR**: ADR-138  
**recon**: docs/handoff/fix-supplier-channel-name/recon.md  
**日付**: 2026-09-23  
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 該当なし：今回は存在しないカラム名の修正のみ。外部事例を参照する必要はないと判断。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| get_supplier_pipeline() が UndefinedColumnError なく実行される | 本番コンテナでの Python asyncio テスト |
| channel_name フィールドに supplier_channels.channel の値が入る | APIレスポンスのJSON確認 |

---

## 技術 How・KPI

- KPI: `sc.name` エラー発生率 = 0%（修正前 100%）
- 技術選択: SQL の `sc.name` を `sc.channel` に修正（3箇所: SELECT, GROUP BY, ORDER BY）

---

## 弊害・トレードオフ

- リスクなし：SELECT専用クエリのカラム名修正のみ。データ書き込みなし。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `tcg_analysis_dashboard_svc.py` の `sc.name` を `sc.channel` に修正 | Generator |
| 2 | CI 通過確認 | Generator |
| 3 | 本番デプロイ後の API 動作確認 | Generator |

---

## 継続

- 完了後の監視: get_supplier_pipeline() が正常なJSONを返すことを確認
- 次フェーズへの引き継ぎ: なし（一度限りの修正）

---

## 維持の仕組み

- supplier_channels テーブルの正しいカラム名は `channel`（`name` ではない）
- 人手で守る：今後 supplier_channels への SQL 追加時はカラム名を確認すること
