分類: 6-1
出所: （2026-10-15 PR #4296）

# GO記録の転記元は PO 本人の GO だけではない

## 1. 委任の GO も転記してよい。発行者欄に Shingo を入れない（分類 6-1）

§6-1 の「GO記録4欄は、POの `GO #PR番号` 発話を実装役が転記してよい」は、ADR-1003（2026-09-29）より前の書き方。
今は PO 本人の GO に加えて、ADR-1003 に基づく Claude Opus の委任 GO も転記してよい。
委任の GO の発行者欄は `POの委任に基づくClaude Opus発行` だけを書き、`Shingo`・`shingo-ops` の文字を入れない。
scripts/check-process-artifacts.js は発行者欄を部分一致で判定するため、入れると PO 本人の GO と判定され、ADR-1003 の例外（DROP を含む migration 等）でも通ってしまう。
例外の変更は PO 本人の GO が必要。
