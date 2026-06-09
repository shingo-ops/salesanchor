# Phase 3 設計 — <仕事名>

**対象ADR**: ADR-NNN  
**recon**: docs/handoff/<仕事名>/recon.md  
**日付**: YYYY-MM-DD  
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

*（小規模な場合は「該当なし：理由〇〇」でも可。**空欄は不可**。process-artifacts gate が記入確認する）*

- 事例1: 〇〇（参照元）→ 我々への応用: 〇〇
- 該当なし：今回は〇〇のため外部事例の参照は不要と判断

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 〇〇が動作する | `pytest tests/test_xxx.py::test_yyy` |
| UIに〇〇が表示される | Evaluator（Playwright: `xxx.spec.ts`） |
| APIが正しく返る | CI pytest + `test_api_xxx` |

*（各行の「検証方法」は空欄不可。process-artifacts gate が照合する）*

---

## 技術 How・KPI

- KPI: 〇〇（数値目標）
- 技術選択: 〇〇（理由: 〇〇）

---

## 弊害・トレードオフ

- 〇〇のリスク → 対策: 〇〇

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | 〇〇 | Generator |

---

## 継続

- 完了後の監視: 〇〇
- 次フェーズへの引き継ぎ: 〇〇
