# design: 共用商品を新しく登録するとき、登録ルールを必ず読ませるフック

> この文書は何か: AI（Opus・Sonnet）が共用商品マスタに新しく商品を登録しようとしたとき、登録ルールの文書を必ず目に入れさせる仕組み（フック）の設計と実装カード。
> ルール文書: [docs/specs/product-master/registration-rules.md](../../specs/product-master/registration-rules.md)（本 PR で新設・草案）
> 親テーマ: docs/handoff/master-register-required-fields/design.md（ADR-1020 案、別ブランチ release/master-register-required-fields）
> 状態: 設計案作成済み・Opus 自己審査済み（同一 AI の審査であり独立レビューではない）・実装未着手
> 起案: 2026-10-16

## 0. PO の言葉（原文）
- 2026-10-16「新規で商品を登録するときは必ず読ませるルールもhookで作成してほしい」

## 1. KGI
| KGI | 判定（○×） | 測り方 |
|---|---|---|
| H1 | AI が create_product を呼ぶ台本を書こうとすると、ルール文書の全文が AI に示され、確認の印（`rules-ack: <8文字>`）が無い台本は書けない | 試験スクリプト（§6 T1〜T3）＋実機で1回 |
| H2 | PO がチャットで「マスタ」「商品」と「登録」を含む依頼をすると、ルール文書の全文が AI の文脈に入る | 試験スクリプト（§6 T4）＋実機で1回 |
| H3 | ルール文書を直すと印の8文字が変わり、古い印の台本は再び止まる（読み直しを強制） | 試験スクリプト（§6 T5） |

## 2. 現在地（recon。生出力 /tmp/CC報告ファイル/master-required-fields/hook/）
- 【事実】登録の値の決め方を1か所にまとめた文書は無い。規則は ADR-1020 案・handoff 文書（sword-shield-catalog.md §4、onepiece-catalog.md §8 ほか）・memory に散らばっている（q1_*.txt）。→ registration-rules.md に集約した。
- 【事実】AI の本番登録は、リポジトリ外の使い捨て台本（例 /tmp/CC報告ファイル/inventory-6checks/box-priority/unreg/reg4/create.py:217）が backend/app/services/tcg_product_master_svc.py:331 の create_product を呼ぶ形。直接 INSERT ではない（q2_*.txt）。
- 【事実】「文書を読ませる」「読んでいないと止める」既存フックは無い（q3_grep_gates.txt）。
- 【事実】公式（https://code.claude.com/docs/en/hooks 、2026-10-16 取得）:
  - PreToolUse は deny と permissionDecisionReason（"For "deny", shown to Claude."）を返せる。
  - UserPromptSubmit は additionalContext を足せる。上限は 10,000 文字。
  - 設定ファイルのフックはサブエージェントのツール呼び出しにも発火する（"Hooks from settings files … also run inside subagents"）。
  - Write の tool_input に content、Edit の tool_input に new_string が入る。
  - 【未確認】サブエージェント内の PreToolUse で transcript_path がどちらの記録を指すかは書かれていない → 記録（transcript）を読んで「読んだか」を判定する方式は採らない。
- 【事実】本店 /Users/tanizawashingo/salesanchor は origin/main より 2766 コミット遅れている（preflight、/tmp/CC報告ファイル/master-required-fields/hook/wt.txt）。セッションは本店のプロジェクト設定（.claude/settings.json）を読むので、リポジトリの .claude/settings.json に足しても本店を更新するまで効かない。

## 3. 代替案と選択
| 論点 | 案 | 採否と理由 |
|---|---|---|
| 「読んだ」の判定 | A 会話の記録を読み、ルール文書を Read したかを見る | 不採用。サブエージェントで記録の場所が未確認（§2） |
| | **B 止めるときの理由欄にルール全文を出し、全文から計算した8文字の印を台本に書かせる** | **採用**。止められた時点で AI は全文を受け取る。印は文書の中身から作るので、文書が変われば読み直しになる（H3）。記録の場所に依存しない |
| フックの登録先 | C リポジトリの .claude/settings.json | 不採用。本店が古く、本店を更新するまで効かない（§2） |
| | **D ~/.claude/settings.json（他のガード類と同じ場所）** | **採用**。全セッション・サブエージェントにすぐ効く。台本の中身はリポジトリの scripts/agent-hooks/ に置いて PR で審査し、~/.claude/scripts/ へ写す |
| ルール文書の読み先 | 本店のファイル | 不採用（古い） |
| | **`git -C /Users/tanizawashingo/salesanchor show origin/main:docs/specs/product-master/registration-rules.md`** | **採用**。マージ済みの最新版を読む。読めなければ止める（安全側） |

## 4. 変更内容
1. 新規 `docs/specs/product-master/registration-rules.md`（ルールの集約。草案。未決は U1〜U3）
2. 新規 `scripts/agent-hooks/master-register-rules-guard.py`（python3、標準ライブラリのみ）
   - 入力: 標準入力の JSON（hook_event_name・tool_name・tool_input・prompt）
   - ルール文書: 上の git show で読む。失敗したら PreToolUse は deny（理由「ルール文書が読めない」）、UserPromptSubmit は何もしない。
   - 印: `sha256(文書のバイト列)` の先頭8文字（16進）。
   - **PreToolUse（Write|Edit|Bash）**:
     - 調べる文字列: Write は content、Edit は new_string、Bash は command。
     - 対象: 次のどれかを含むとき。
       - `create_product(`
       - `INSERT INTO public.products`
       - `INSERT INTO products`
       - `/tcg/products/create`
     - 対象外（素通り）:
       - Write・Edit で file_path が `/backend/`・`/frontend/`・`/docs/`・`/migrations/`・`/tests/` を含む（アプリの開発・文書）。
       - Bash で command の先頭の語が `git`・`grep`・`rg`・`cat`・`sed`・`head`・`tail`・`less` のどれか（読むだけ）。
     - 対象で、文字列に `rules-ack: <今の8文字>` があれば allow、無ければ deny。
     - deny の理由欄: 「共用商品の新規登録ルール（必読）」＋ 文書全文 ＋「読んだら台本に `# rules-ack: <8文字>` を書いて、もう一度実行してください」。
   - **UserPromptSubmit**:
     - prompt が正規表現 `(マスタ|商品).*登録|登録.*(マスタ|商品)` に当たれば、additionalContext に「共用商品の新規登録ルール（必読）」＋全文を入れる。
     - 9,000 文字を超えるときは、先頭 9,000 文字と「続きは origin/main の docs/specs/product-master/registration-rules.md」を入れる。
   - そのほかのイベント・対象外は何も出さず exit 0。例外が起きたら、PreToolUse は deny、UserPromptSubmit は exit 0。
3. 新規 `scripts/agent-hooks/test_master_register_rules_guard.sh`（§6 の T1〜T6 を、入力 JSON を流して判定）
4. リポジトリ外（PR 後の取り付け。Sonnet が実行、手順と前後の差分を記録）:
   - `~/.claude/scripts/master-register-rules-guard.py` へ写す。
   - `~/.claude/settings.json` の hooks に足す（既存の項目は変えない。書き換え前に `~/.claude/settings.json.bak-20261016-rules` を作る）。
     - PreToolUse matcher `Write|Edit|Bash`
     - UserPromptSubmit
   - **取り付けは PR マージ後**（origin/main に文書が無い間は、全部の登録台本が止まるため）。

触らない範囲: backend/・frontend/・migrations/・.github/・リポジトリの .claude/settings.json・既存の ~/.claude/scripts/*。

## 5. リスクと対処
| リスク | 対処 |
|---|---|
| 「登録」を含む関係ない依頼でも全文が入る | 文書は約2,000字。害は文脈が少し増えるだけ。実測で多すぎれば正規表現を絞る |
| 印だけ写して読まない | 止められた時点で全文は AI に渡っている（防げるのは「見ずに書く」まで。読んだ上で守るかは候補表の PO 確認＝ルール C3 で担保） |
| 開発中のアプリコードが止まる | §4 の対象外パス。止まったら理由欄で分かるので、対象外を足す |
| ~/.claude/settings.json を壊す | 写す前にバックアップ。書き換え後に `python3 -m json.tool` で形を確かめる。戻し方: バックアップを戻す |

戻し方: ~/.claude/settings.json をバックアップに戻し、~/.claude/scripts/master-register-rules-guard.py を消す。リポジトリ側は PR を revert。

## 6. 受け入れ基準と検証方法
| 基準 | 検証方法 |
|---|---|
| T1 Write の content に `create_product(` があり印なし → deny、理由に文書全文 | 試験スクリプト |
| T2 同じ内容で印が正しい → allow | 試験スクリプト |
| T3 file_path に `/backend/` を含む Write → 素通り（出力なし・exit 0） | 試験スクリプト |
| T4 UserPromptSubmit「この商品をマスタに登録して」→ additionalContext に全文 | 試験スクリプト |
| T5 印が古い8文字 → deny | 試験スクリプト |
| T6 Bash `grep -rn create_product backend` → 素通り | 試験スクリプト |
| T7 取り付け後、実機（このセッションのサブエージェント）で /tmp/CC報告ファイル/ に `create_product(` を含むファイルを書かせると止まる | 実機。生出力を保存 |

## 7. 外部事例
- 該当なし: 自社の AI 運用の手順を守らせる内部の仕組みであり、効果の数値がそろった外部事例は見つけていない。根拠は公式のフック仕様（§2）と、社内で既に使っている同種のガード（~/.claude/scripts/ の worktree-only-guard.sh・pr-body-guard.sh など。ツール呼び出しを止める方式）。

## 8. 自己審査（Architect 役・同一 AI）
- 判定: **APPROVE**（実装可）
- 確かめたこと:
  - 判定に記録の場所（未確認事項）を使っていない。
  - 文書が無い間に取り付けると全部止まる順序の問題は、取り付けをマージ後にすることで避けた。
  - 触らない範囲を書いた。
- 未解決（実装は妨げない）: ルール文書の U1〜U3 は PO 判断待ち。決まれば文書を直し、印が変わって読み直しになる。

## 維持の仕組み
- 守り手: ~/.claude/settings.json の PreToolUse・UserPromptSubmit フック（全セッション・サブエージェント）
- 正本: origin/main の registration-rules.md（直すと印が変わる）
- 試験: scripts/agent-hooks/test_master_register_rules_guard.sh（フックを直したら必ず流す）
- 人手で守るもの: ルール文書の中身（PO の言葉だけを規則にする）
