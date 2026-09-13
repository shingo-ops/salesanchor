# design — B+C便（agent設定整合＋鮮度フック修理）

**対象ADR**: ADR-042
**recon**: docs/handoff/agent-guardrails/recon.md
- 関連ADR: ADR-042（本フックの導入元・MTG決定C）
- 種別: real-code（.claude配下）。新機能なし・紙とスイッチのみ。

## How（変更5点）
- C: check-freshness.sh の見張り先を origin/develop→origin/main に全面掛け替え（6系統: コメント/fetch/verify/merge-base/blob比較/警告文）。比較ロジックは不変。
- B-1: generator.md「# Critical rules」にルール9「Plannerカードが常設指示に優先」を追加。
- B-2: generator.md:52 の「行を削除」命令を「DONEに更新（行は残す）」へ訂正。PARALLEL_TERMINAL_GUIDE.md:100 に一致。
- B-3: generator.md「# Critical rules」直前に「カード実行時の応答様式」節を新設。
- B-4: design-partner.md「## 7」直前に「カード設計の規約」節を新設（§6末尾）。

## 触らない範囲
generator.md の Codex委任/Step0-8/既存ルール1-8 ／ design-partner.md §0-5,§7-8 ／ settings.json（配線健在） ／ PARALLEL_TERMINAL_GUIDE.md（正の側・不変）。

## 弊害と対策
- develop上の旧worktreeにmain基準の警告が出る→developは新規作業禁止（handoff§4）ゆえ望ましい挙動。
- §6は各セッションが締めに追記する場所→行番号でなく見出し文字列アンカーで挿入・実装直前に再確認。

## 外部・過去事例
- 社内: session-freshness-hook recon（blob直比較の設計根拠）／EV-20260703-001（案内書の古さ＝コードのバグと同格）。
- 外部: Gitのデフォルトブランチ移行（master→main）でhook・CIの参照残りが「静かな機能停止」を招くのは既知の定番事故。本件はその典型。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| B-1: generator.md にカード優先の但し書きが1件 | `grep -c "card overrides\|カード.*優先" .claude/agents/generator.md` = 1 |
| B-2: 台帳「行削除」命令が消え「DONE」新文が1件 | `grep -c "remove your row" ...` = 0 かつ `grep -c "DONE" ...` ≥ 1 |
| B-3: 「カード実行時の応答様式」節が存在 | `grep -c "カード実行時の応答様式" ...` = 1 かつ 「生ログ」「要約」「再実行」各 ≥ 1 |
| B-4: design-partner.md §6に「カード設計の規約」が存在 | `grep -c "カード設計の規約" docs/ai-agents/design-partner.md` = 1 |
| C: フックが main 基準・develop 参照ゼロ | `grep -c "origin/develop" .claude/hooks/check-freshness.sh` = 0 かつ `origin/main` ≥ 1 |
| C-動作: 古いSHAで警告が実際に出る | 別クローンをmainより遅らせフック実行→標準出力に警告（別カードで実測） |

## 検証補足
