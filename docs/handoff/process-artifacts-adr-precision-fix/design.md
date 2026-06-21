# design.md — process-artifacts ADR precision fix

**対象ADR**: 無し（新規不要）  
**recon**: docs/handoff/process-artifacts-adr-precision-fix/recon.md  
**日付**: 2026-06-21  
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 事例1: Markdown リンク切れ検証ツール（例: markdownlint / dead-link checker）→ 参照先の**実在確認**を本文の文字列一致だけで済ませず、対象集合を全件走査して存在確認する。
- 事例2: CI での manifest / lockfile 照合 → 「名前が似ている別物」を拾わないため、接頭辞一致ではなく**境界付き一致**にする。

---

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 実在する ADR 参照は pass | `node scripts/tests/test-process-artifacts.js` |
| 実在しない ADR 参照は fail | `node scripts/tests/test-process-artifacts.js` |
| 複数 ADR 参照は全件確認される | `node scripts/tests/test-process-artifacts.js` |
| `ADR-10` 参照が `ADR-1000-*.md` を拾わない | `node scripts/tests/test-process-artifacts.js` |

---

## 技術 How・KPI

- KPI: ADR 参照の誤検知 0
- 技術選択: PR 本文の `対象ADR:` を全件抽出し、`docs/adr/` の実ファイル名を境界付きで照合する

---

## 弊害・トレードオフ

- より厳密な照合により、曖昧な ADR 記述は fail しやすくなる
- ただし誤った別番号の取り込みを防ぐため、保守上は厳密化が必要

---

## 計画票

| ステップ | 内容 | 担当 |
|---|---|---|
| 1 | gate 本体の ADR 抽出を複数対応にする | Generator |
| 2 | 境界付き照合と複数 ADR テストを追加する | Generator |
| 3 | ローカルテストで pass/fail を確認する | Evaluator |

---

## 継続

- 完了後の監視: process-artifacts gate の実行結果で誤検知が増えていないか確認
- 次フェーズへの引き継ぎ: なし
