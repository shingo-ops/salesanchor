<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# 設計 — extraction-hide-excluded

**対象ADR**: ADR-027  
**recon**: docs/handoff/extraction-hide-excluded/recon.md  
**日付**: 2026-09-28  
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

該当なし：SQLのWHERE句1行追加のみで、類似するオープンソース実装や外部設計事例を参照する必要のない最小変更のため。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 直近ジョブテーブルに empty/filtered が表示されない | 抽出タブを目視確認 |
| 正常性カードの集計値（total, success rate, error count）が変わらない | 画面上の集計値を確認 |

---

## 技術 How・KPI

- KPI: empty/filtered ステータスのジョブが直近ジョブテーブルに表示されない（0件）
- 技術選択: SQLのWHERE句追加（`WHERE ej.status NOT IN ('empty', 'filtered')`）。正常性カードの集計クエリは別クエリのため影響なし

---

## 弊害・トレードオフ

- 直近ジョブが10件未満になる可能性がある（empty/filtered が多い場合）→ 許容。ノイズより実データを優先

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `backend/app/services/tcg_analysis_dashboard_svc.py` のWHERE句1行追加 | Generator |

---

## 継続

- 完了後の監視: 直近ジョブテーブルの表示内容を目視確認
- 次フェーズへの引き継ぎ: なし

---

## 維持の仕組み

守り手: `backend/app/services/tcg_analysis_dashboard_svc.py`
