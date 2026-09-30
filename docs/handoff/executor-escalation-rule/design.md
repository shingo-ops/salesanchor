# design: 実装者の「迷ったら止まる」ルールと「main の譲り合い」ルール

- recon：`docs/handoff/executor-escalation-rule/recon.md`
- 対象 ADR：`docs/adr/ADR-113-two-mode-dev-flow.md`
- PO 指示（チャット 2026-09-29）
  - 「事実ベースで設計者の判断を仰ぐ仕様にしてほしい」
  - 「PRのmainの取り合いをしないように若いPR番号が更新していたら譲り合いながら進めること」

## 変更
`docs/ai-agents/executor-checklist.md` に、次の2つの節を足す。
1. **迷ったら止まって、設計者の判断を仰ぐ**：止まる条件は5つ。報告の形は「事実／未確認／選択肢」。役割分担は、PO が意思決定、設計者が設計と実務の判断、実装者が指示書どおりに作ること。
2. **main の取り合いを避ける**：番号の若い PR がマージに向けて動いていたら譲る。確かめる手順と、待ち時間の上限を書く。
3. docs/ai-agents/design-partner.md に役割と進め方の節を足す（PO 決定 2026-09-29）

## 基準と検証方法
| 基準 | 検証方法 |
|---|---|
| 2つの節が手順書にある | `grep -n "設計者の判断を仰ぐ\|main の取り合い" docs/ai-agents/executor-checklist.md` |
| 書類だけの変更である | `git diff --stat origin/main...HEAD` が手順書と台帳だけ |

## 外部・過去事例の参照と我々への応用
該当なし。このリポジトリの 2026-09-28〜29 の実際の出来事（recon の事実1〜3）を根拠にする。

## 維持の仕組み
- 守り手：`docs/ai-agents/executor-checklist.md`（実装役は作業の前に必ず読む。CLAUDE.md の末尾で指定されている）
