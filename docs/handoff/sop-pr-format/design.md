# design: sop-pr-format

**対象ADR**: ADR-121
**recon**: docs/handoff/sop-pr-format/recon.md

## 設計方針

docs/ai-agents/executor-preamble.md の末尾に「## PR作成の手順（例外なし）」セクションを追記する。
ADR-121 で設計された process-artifacts gate の検査規則を、実測で確認したまま文書化する。
既存の定型文（1〜30行）は一字も変更しない。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| executor-preamble.md の既存30行が一切変更されていない | `git diff origin/main docs/ai-agents/executor-preamble.md` で先頭30行に差分なし |
| 末尾に「## PR作成の手順（例外なし）」セクションが追記されている | 同 diff に新セクション見出しが含まれる |
| 6つの検査規則が箇条書きで記載されている | diff 内の箇条書き数が6件以上 |
| `process-artifacts gate` が全緑になる | `gh pr checks <PR番号>` で fail = 0件 |

## 設計選択

### 追記のみ（既存行変更なし）
executor-preamble.md はセッション投入用の逐語原本（変更はPR＋PO承認のみ）。
既存行を変更すると写し崩れリスクがあるため、末尾追記のみで対応する。

### 実測ルールの明文化
ADR-121 は gate の存在を定義するが、具体的な書式ルールは scripts/check-process-artifacts.js の
実装に依存している。実測で判明したルールを preamble に明記することで、次便以降の CI 失敗を防ぐ。

## 外部・過去事例

- ADR-121: process-artifacts gate は SOP コンプライアンス保証機構の一部として設計された。
  recon / design の提出と PR 本文の宣言を照合することで、「文書を書かずに実装する」を技術的に防止する。
- docs/handoff/sop-kpi2/design.md は gate の §2〜§4 の正本として参照される。本 design.md はそれに準拠する。

## 維持の仕組み

守り手: 人手で守る（executor-preamble.md の変更は PR＋PO承認のみ。CI は process-artifacts gate で保護）
