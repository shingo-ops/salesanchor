# Phase 3 設計 — line-analysis-tuning-log

**対象ADR**: ADR-100  
**recon**: docs/handoff/line-analysis-tuning-log/recon.md  
**日付**: 2026-10-07  
**担当**: 設計担当（Opus）

---

## 目的
LINE解析 Gemini の指示書・仕入元ルールの調整について、「いつ・何を変えて・精度がどう変わったか」「PO の判断」「事故」を1か所に積み上げる。文書のみ。製品のコード・DB・本番の設定は変えない。

## 置き場所を選んだ理由

| 候補 | 内容 | 判定 |
|---|---|---|
| A | `docs/specs/line-analysis-tuning/` に新規（README＋track-record） | 採用 |
| B | 既存の `docs/handoff/gemini-*` のどれかへ追記 | 不採用 |

- 選んだ理由: 調整記録は版をまたぐ横断の履歴台帳であり、PR 単位の handoff（`docs/handoff/gemini-prompt-e/design.md` など）に追記すると、その版の設計書に他の版の記録が混ざる。
- なぜ既存で足りないか（`docs/ai-agents/design-partner.md:112` の「1行明記」）: 版ごとの設計書は PR 単位に分かれ、版をまたいだ精度の推移と判断の一覧が無い（recon 調査の事実2）。
- 索引への登録: `docs/specs/README.md` に1行（`docs/ai-agents/design-partner.md:112`・`docs/ai-agents/design-partner.md:113`）。
- 書式: `docs/specs/ledger-guard/track-record.md` と `docs/specs/agent-complete-design/track-record.md` の型（表紙リンク行・記帳の決まり・1行1回の表）に合わせた。中身の文言は設計担当の原文のまま。

## 外部・過去事例の参照と我々への応用

- 事例1: `docs/specs/agent-complete-design/track-record.md`・`docs/specs/ledger-guard/track-record.md`（社内の定点観測台帳）→ 応用: 「1回の試験＝1行」の表と記帳の決まりの型を踏襲。
- 事例2: `docs/handoff/line-accuracy-pages/accuracy-evidence.md`（1回分の精度の証拠）→ 応用: 1回分の証拠を版をまたぐ履歴に積み上げる形にした。数字の根拠の生データは手元に置き、sha256 で指す。
- 外部事例: 該当なし（社内の記録の置き場所の整理であり、外部の手法を採用する余地が無いため）。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| README.md と track-record.md が `docs/specs/line-analysis-tuning/` にある | `git diff --name-only origin/main...HEAD` の出力に2ファイルが含まれる |
| 索引から辿れる | `grep -n "line-analysis-tuning" docs/specs/README.md` が1行ヒットする |
| 仕入元の名前・投稿の原文・判定の一覧が無い | 設計担当が下書きを確認済み。実装担当が全文を再読し、社名・原文・一覧が無いことを確認（人手で確認） |
| 文書内のリンクが実在する | `ls docs/handoff/gemini-v8 docs/handoff/gemini-v9 docs/handoff/gemini-v10 docs/handoff/gemini-v101 docs/handoff/gemini-v102 docs/handoff/gemini-prompt-d docs/handoff/gemini-prompt-e docs/handoff/gemini-omit-supplier-field docs/handoff/gemini-supplier-rules-file docs/handoff/gemini-new-system-supplier-rules docs/handoff/deploy-selective-recreate` が全件成功 |
| 危険パス（migrations/・deploy.yml・本番 scripts/）を含まない | `git diff --name-only origin/main...HEAD` の出力を PR 本文に貼る |
| PR の関所（process-artifacts gate・pr-body-guard）を通る | CI の全必須チェックが緑 |

---

## 技術 How・KPI

- KPI: 試験を流すごとに track-record に1行が足されている（記帳の遅れは最大1便）。
- 技術選択: 文書のみ（理由: 記録の置き場所の整理であり、コード・DB に触れる必要が無い）。

## 弊害・トレードオフ

- 記帳が漏れると履歴が欠ける → 対策: 設計担当が試験ごとに1行を足す。未記帳行は次の便に相乗りして記帳する（`docs/ai-agents/design-partner.md:254`）。
- 社外秘の混入 → 対策: 集計値・決まりの文・ファイルの場所と sha256 だけを書く。生データは手元（リポジトリ外）。

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | docs/specs/line-analysis-tuning/ に2文書を置き、索引に1行を足す | 実装担当 |
| 2 | PR・CI・マージ | 実装担当 |

---

## 継続（維持の仕組み）

- 試験ごとに track-record に1行を足す。PO の判断が出たら README の「判断の決まり」に1行、事故が起きたら「事故と直し方」に1行足す。
- 守り手: 設計担当（人手で守る）。入口は索引 `docs/specs/README.md`。
- 次フェーズへの引き継ぎ: 引継ぎ書類に「未記帳の定点観測行」欄を設ける（`docs/ai-agents/design-partner.md:255`）。
