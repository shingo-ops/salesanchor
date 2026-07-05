# design — B+C便（agent設定整合＋鮮度フック修理）

- recon: docs/handoff/agent-guardrails/recon-bc.md
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

## 検証（○×基準・全5項目でKGI達成）
- B-1: generator.md に「card overrides / カードが優先」の一文が1件存在。
- B-2: 「remove your row ... deletion」が0件、「DONE」を含む新文が1件。
- B-3: 「カード実行時の応答様式」見出しが1件＋「生ログ」「要約」「再実行」語が各1件以上。
- B-4: design-partner.md §6内に「カード設計の規約」見出しが1件＋規約6要素の各語が1件以上。
- C: check-freshness.sh に origin/develop が0件・origin/main が1件以上。かつ**動作実測**＝古いSHAのクローンでフック実行→警告が標準出力に出る（別カードで実測）。
