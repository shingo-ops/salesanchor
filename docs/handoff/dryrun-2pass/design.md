# Phase 3 設計 — dryrun-2pass

**対象ADR**: ADR-135  
**recon**: docs/handoff/dryrun-2pass/recon.md  
**日付**: 2026-06-12  
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

- 2026-06-12 本番デプロイ失敗（run 27419385801）: `20260604_100000_create_company_stats_view.sql` が `CREATE OR REPLACE VIEW`（5列）で `cannot drop columns from view` 失敗。原因は `20260612_120000` が本番に手動先行適用済みで VIEW が 7 列になっていたため。2周目ドライランがあれば PR #2059 の CI で事前検出できた（1周目で 7 列になった直後に 2 周目で 5 列 REPLACE → ERROR）。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| CI に「1周目（新規適用）」「2周目（冪等性チェック）」の 2 ステップが存在する | `.github/workflows/migration-test.yml:860,895` の step name を確認 |
| 2周目が 1 周目完了後の同一 DB に対して同じ SQL を実行する | CI ログで 2 周目の `▶ [2周目 N/M]` 出力を確認 |
| スキップガードを持つ migration（`20260604_100000`）は 2 周目も PASS する | CI ログで 2 周目 ✅ を確認 |
| 2 周目の失敗メッセージが「本番再デプロイ時に同じエラーが発生します」と明記される | migration-test.yml:916 のエラー出力を確認 |

---

## 技術 How・KPI

- KPI: 再デプロイ不安全な migration を PR マージ前に 100% 検出
- 技術選択: 既存の 1 周目ループと同じ SQL リストを 2 周目でも実行。追加インフラ不要。

---

## 弊害・トレードオフ

- CI 実行時間が約 30 秒増加 → timeout-minutes: 30 内に収まるため許容
- 2 周目で失敗する migration は本番で不安全 → 修正（スキップガード追加など）が必要。これは本来あるべき状態

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | migration-test.yml の dryrun ジョブに 2 周目ステップを追加 | Generator |
| 2 | handoff docs 作成 + PR 起票 | Generator |

---

## 継続

- 完了後の監視: 次回 migration PR の CI ログで 2 周目出力を確認
- 次フェーズへの引き継ぎ: 2 周目失敗が出た場合はその migration にスキップガードを追加する運用を確立
