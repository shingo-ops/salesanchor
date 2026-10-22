# recon — AI向け指示文書の「目次→章→末端ページ」化（現在地把握）

> この文書は何か（専門用語なしの1行）:
> 「AIが会話のたびに自動で読まされている文書は何行あるか・同じ決まりが何か所に重なっているか・目次から辿れない文書がいくつあるか」を実測した記録。設計（design.md）の土台。

- 親（仕様書）: [docs/specs/doc-agenda-nav/README.md](../../specs/doc-agenda-nav/README.md)
- 兄弟（設計）: [design.md](./design.md)
- 先行報告: リポジトリ外 ~/CC報告ファイル-keep/agenda-nav-20261022/report.md（2026-10-22 調査便）
- 基準: origin/main `16000c2d52b93f72e5d332c8f6ee506920104a6c`（`git fetch origin` 後、2026-10-22）
- 生出力: リポジトリ外 ~/CC報告ファイル-keep/agenda-nav-20261022/design/raw/（本文の「raw/…」はこのフォルダを指す。本文の数字はすべて raw の実測から転記）
- Claude Code 版: 2.1.307（raw/settings-flags.txt）
- 既存 ADR 検索: `docs/adr/FEATURE-INDEX.md:3` と `git grep -i` で「CLAUDE.md 階層／文書／索引」を検索 → 該当 ADR-076（CLAUDE.md 階層化・行数上限）、ADR-027（i18n）、ADR-113（2モード開発フロー）。「目次を辿らないと手順書を読めない」仕様を決めた ADR は **無し**（先行報告と同じ結論。raw/prior-prs.txt・prior-branches.txt）。

---

## 1. 過去に同じ構想が議論された記録（課題1）

| 探した場所 | 語 | 結果 | 根拠 |
|---|---|---|---|
| GitHub PR（全状態） | アジェンダ | 0件 | raw/prior-prs.txt |
| 同上 | 目次・末端・索引・必要なときだけ・階層 | 構想そのものは0件。近い PR: #3358「docs(design-partner): guards を節ごとに分割し目次化」(2026-09-08)、#1070/#1415（ADR-076 CLAUDE.md 階層化） | raw/prior-prs.txt |
| origin の release/* 1,930本 | 同上（main より先の追加行） | 0件 | raw/prior-branches.txt |
| ~/CC報告ファイル-keep | 同上 | 3件ヒットはすべて gap-range-20261011/recon-src 内の CSS 設計文（「必要なときだけ次行を使い」等）で無関係 | raw/prior-keep-kb.txt, raw/baseline2.txt 末尾 |
| ~/kb（00-rules/02-facts/04-records/05-tasks） | 同上 | 0件 | raw/prior-keep-kb.txt |
| 過去会話 ~/.claude/projects/…/*.jsonl | 同上 | **未確認**。Bash での grep は見張り（agent-danger-hook consent-guard「会話記録…を Bash で触ることはできません」）に止められ、Grep ツールは本環境に無い（ToolSearch「select:Grep」該当なし。委任した探索担当も同じ理由で0回）。言い換え・迂回はしていない | 会話記録（本セッション） |

【事実】リポジトリ・PR・ブランチ・報告ファイル・kb には、この構想を決めた記録は無い。
【未確認】過去会話記録（jsonl）の中は調べられていない。`[?]` 必要なら Grep ツールを持つセッションで再実行。

---

## 2. ベースライン測定（課題2）

### 2-1. 会話のたびに自動で読み込まれるもの（起動時）

公式仕様（raw/official-memory-page.md）: ユーザー CLAUDE.md と @import、作業ディレクトリ以上の CLAUDE.md、`paths` の無い `.claude/rules/*.md`、MEMORY.md 先頭200行/25KB、が起動時に読み込まれる。サブディレクトリの CLAUDE.md と `paths` 付き rules は、該当ファイルを触ったときだけ読み込まれる（同 :64, :88, :585）。

| # | ファイル | 行 | 文字 | 根拠（読み込まれる理由） |
|---|---|---|---|---|
| 1 | ~/.claude/CLAUDE.md | 84 | 3,025 | ユーザー指示（公式 :61 表） |
| 2 | ~/kb/AGENTS.md | 32 | 1,316 | ~/.claude/CLAUDE.md:84 `@~/kb/AGENTS.md` の import（import は文脈を減らさない: 公式 :104 周辺） |
| 3 | ~/.claude/rules/common/agents.md | 53 | 1,712 | `paths` 無し＝常時読込（raw/rules-frontmatter.txt） |
| 4 | ~/.claude/rules/common/git-workflow.md | 24 | 622 | 同上 |
| 5 | MEMORY.md（auto memory） | 149 | 16,298 | 公式 :547「先頭200行または25KB」。149行/16,298字は上限内＝全文読込 |
| 6 | salesanchor/CLAUDE.md | 120 | 6,317 | プロジェクト指示（ADR-076 上限120行ちょうど） |
| **計** | | **462** | **29,290** | raw/autoload-sizes.txt |

読み込まれない（よくある誤解）:
- `AGENTS.md`（281行/8,651字）: CLAUDE.md が在るため読まれない（公式 :357「An AGENTS.md and a CLAUDE.md … → Your CLAUDE.md files only」。`pluginConfigs` 未設定＝既定 `claude-md-or-agents-md`: raw/settings-flags.txt）。CLAUDE.md に `@AGENTS.md` も無い。
- `docs/` 配下の全文書・ADR: 自動ロードされない（FEATURE-INDEX.md:3 も同旨）。

条件付き（該当ファイルを触ったとき）:
- frontend/CLAUDE.md 78行、backend/CLAUDE.md 70行、backend/scripts/CLAUDE.md 30行、backend/tenant/CLAUDE.md 57行、tools/claude-channels/intake/CLAUDE.md 30行（raw/autoload-sizes.txt）
- ~/.claude/rules の残り10ファイル（`paths: **/*.py,ts,tsx,js,mjs,sh` 等。raw/rules-frontmatter.txt）

### 2-2. 入力のたび／セッション開始時に、フックが文脈へ流し込むもの

| イベント | フック | 流し込む量 | 条件 | 根拠 |
|---|---|---|---|---|
| UserPromptSubmit | ~/.claude/scripts/master-register-rules-guard.py | `docs/specs/product-master/registration-rules.md` 全文 76行/11,423字 → 9,000字で切り詰め（:26 `PROMPT_LIMIT = 9000`） | :25 `PROMPT_RE = re.compile(r"(マスタ\|商品).*登録\|登録.*(マスタ\|商品)", re.S)` に入力が一致 | raw/hooks-detail.txt, raw/hook-scripts-home.txt；設定: ~/.claude/settings.json UserPromptSubmit[2] |
| UserPromptSubmit | ~/.claude/scripts/card-lint-hook.sh | 0（「END OF CARD」を含む入力のみ検査） | — | raw/hooks-inventory.txt |
| UserPromptSubmit | agent-console activity-hook.mjs（async） | 0 | — | 同上 |
| SessionStart(startup) | ~/.claude/scripts/token-health-check.sh | 正常時0（警告時のみ） | — | raw/hook-scripts-home.txt |
| SessionStart(startup/resume/clear) | .claude/hooks/check-freshness.sh | 遅れがある時だけ警告数行 | — | raw/hooks-detail.txt |
| SessionStart(同上) | .claude/hooks/stop-log-digest.sh | 前日の digest 数行または「ログなし」 | — | 同上 |
| PreToolUse Write/Edit/Bash | master-register-rules-guard.py :53-84 | 拒否理由として規則全文 | 書く内容・コマンドに監視語（:16-21 TARGETS。商品作成関数名・products への挿入 SQL・登録 API パス）を含む。免除は :22 EXEMPT_PATHS（/backend/ /frontend/ /docs/ /migrations/ /tests/） | raw/hook-scripts-home.txt |

【事実】「関係ない入力に商品マスタ登録ルール約100行が入る」の原因は PROMPT_RE の `re.S` 付き `.*`。「商品」か「マスタ」と「登録」が入力のどこかに（順不同・距離無制限で）在れば一致する。raw/prompt-regex-test.txt の実測: 無関係な例文5本中5本が一致（例「在庫表の商品名の列幅を直して。あとログイン登録画面のバグも見て」→ True）。設計文書 docs/handoff/master-register-rules-hook/design.md:60 も同じ条件を仕様として書いている（raw/docs/master-register-rules-hook_design.md）。
【事実】PreToolUse 側も同種の過剰一致がある。本便で recon.md（調査記録）を書こうとした Write が、監視語を「説明として引用」しただけで止められ、規則全文が表示された（raw/hook-block-event-20261022.txt）。保存先 ~/CC報告ファイル-keep/ は EXEMPT_PATHS に無い。
【事実】`if` フィールドは UserPromptSubmit では評価されない（公式 hooks「Only evaluated on tool events」raw/official-hooks-skills-quotes.txt）。条件を狭めるなら正規表現側で行う。

### 2-3. 「必読」と宣言されて全文を読む文書

| 宣言箇所 | 読む文書 | 行 | 文字 |
|---|---|---|---|
| CLAUDE.md:72「作業開始前に docs/STANDARD-WORKFLOW.md を必ず read すること」 | docs/STANDARD-WORKFLOW.md | 175 | 7,822 |
| CLAUDE.md:120「executor-checklist.md（正本・必読）」 | docs/ai-agents/executor-checklist.md | 52 | 1,959 |
| STANDARD-WORKFLOW.md:25「着手前に必ず既存 ADR を検索… FEATURE-INDEX.md」 | docs/adr/FEATURE-INDEX.md | 63 | 4,592 |
| STANDARD-WORKFLOW.md:67「索引 docs/specs/README.md で…確認」 | docs/specs/README.md | 100 | 11,256 |
| design-partner.md:4「設計セッションはまずこれを読んでから」＋§0.5（:44-53） | design-partner.md 本体 ＋ STANDARD-WORKFLOW ＋ CLAUDE.md ＋ specs/README | 438 | 25,942 |
| AGENTS.md:209「docs/adr/README.md（自動生成）…必ずここから」 | docs/adr/README.md | 228 | 25,631 |

（raw/baseline2.txt）
【事実】ターミナル作業1件で宣言どおりに読むと、自動読込 462行 ＋ 必読 390行（STANDARD-WORKFLOW＋checklist＋FEATURE-INDEX＋specs/README）= **852行 / 約55,000字** が、作業内容に関係なく入る。設計セッションはさらに design-partner 438行。

### 2-4. 同じ決まりが何か所に重なっているか（SSOT 違反の実測）

対象13ファイル（自動読込6＋条件付き読込 frontend/backend の CLAUDE.md/AGENTS.md ＋必読3）。raw/duplicates.txt（file:line 全件）・raw/duplicates-summary.txt。

| 決まり（検索語） | 出現ファイル数 | 行数 | 重なりの例（file:line） |
|---|---|---|---|
| i18n | 5 | 9 | CLAUDE.md:90, AGENTS.md:158, frontend/CLAUDE.md:25, frontend/AGENTS.md:27, ~/.claude/CLAUDE.md:13 |
| ハードコード禁止 | 5 | 7 | CLAUDE.md:92, AGENTS.md:161, frontend/CLAUDE.md:27, frontend/AGENTS.md:29 |
| 不可逆操作は PO 確認 | 5 | 7 | CLAUDE.md:36, AGENTS.md:150, STANDARD-WORKFLOW.md:166 |
| 推測禁止 | 5 | 16 | CLAUDE.md:72, STANDARD-WORKFLOW.md:14/25/116, design-partner.md, ~/.claude/CLAUDE.md |
| executor-preflight | 2 | 4 | CLAUDE.md:65/86, AGENTS.md:99/145 |
| squash 禁止 | 3 | 4 | CLAUDE.md:50, AGENTS.md:135/137, design-partner.md:210 |
| worktree 必須 | 3 | 7 | CLAUDE.md:47, design-partner.md:176/254/301/359/374 |
| 日本語で応答 | 7 | 8 | （raw 参照） |
| file:line 必須 | 4 | 14 | STANDARD-WORKFLOW, executor-checklist, design-partner, ~/.claude/CLAUDE.md |

【事実】CLAUDE.md と AGENTS.md は「プロジェクト前提／ブランチ運用／不可逆操作／i18n／VPS 落とし穴／preflight」の6節がほぼ同文で二重化している（CLAUDE.md:9-16,36-66,86,90-92 ↔ AGENTS.md:9,44-48,97-99,130-154,158-169）。frontend と backend も CLAUDE.md ↔ AGENTS.md で同文（例 frontend/CLAUDE.md:25-27 ↔ frontend/AGENTS.md:27-29）。
【事実】~/.claude/CLAUDE.md:13 は「AGENTS.md も同時に更新せよ」と二重化を**要求**している（重なりの発生源）。

### 2-5. 索引から辿れない文書の数

入口6ファイル（CLAUDE.md, AGENTS.md, frontend/・backend/ の CLAUDE.md・AGENTS.md）から Markdown リンクを幅優先で辿った結果（raw/reachability.txt）:

| 範囲 | 総数 | 辿れる | 辿れない |
|---|---|---|---|
| docs/ ＋入口 の .md 全体 | 2,995 | 1,115 | **1,880** |
| docs/specs | 305 | 270 | 35 |
| docs/adr | 203 | 203 | 0（docs/adr/README.md 自動生成が網羅） |
| docs/handoff | 2,340 | 531 | 1,809 |
| docs/ai-agents | 34 | 15 | 19 |
| 最深の段数 | 14段（例 docs/specs/db-ssot/implementation-plan/design.md） | | |

【事実】辿れない 1,880 のうち 1,809 は docs/handoff（便ごとの recon/design/カード）。specs の README で辿れないもの: discord-reaction, doc-parent-child, process-hardening/proof-of-behavior（raw/reachability.txt）。
【事実】先行報告で「未確認」だった9階層（management-center/* 8件、inventory-management/dropship-procurement・market-history）は、親 README からリンク済み（docs/specs/management-center/README.md:22-29、inventory-management/README.md:17,19。raw/orphan9.txt）→ **解消**。

### 2-6. 既存の強制の仕組み（何が機械で守られ、何がお作法か）

| 仕組み | 守っているもの | 根拠 |
|---|---|---|
| CI「CLAUDE.md line count check」（必須チェック） | 5つの CLAUDE.md の行数上限（root120/frontend90/backend70/backend-scripts70/backend-tenant70） | .github/workflows/check-claude-size.yml:12,40; frontend/scripts/check-claude-size.js:22-28 |
| 同スクリプト | 未登録サブ CLAUDE.md の警告のみ（:30-42） | 同上 |
| STANDARD-WORKFLOW §1.6 | 親子リンク・1行説明は「お作法であり機械強制ではない」 | docs/STANDARD-WORKFLOW.md:53 |
| design-partner §4 | 「索引を唯一の入口とし、どこに置いても索引から辿れる状態を保つ」（お作法） | docs/ai-agents/design-partner.md:113 |
| STANDARD-WORKFLOW §7 | 「正本はこのファイル1つ。各入口はコピーせず、ここを指す」 | docs/STANDARD-WORKFLOW.md:156 |
| executor-checklist 冒頭 | 「CLAUDE.md / AGENTS.md から参照される唯一の本文（ここ以外に複製しない）」 | docs/ai-agents/executor-checklist.md:5 |

【事実】「索引から辿れること」「同じ決まりを2か所に書かないこと」を機械で検査するものは **無い**。
【事実】リポジトリに `.claude/rules/`・`.claude/skills/` は無い（raw/baseline2.txt「.claude/skills in repo」0件）。`.claude/agents/` は7ファイル。

### 2-7. 公式仕様で設計に効くもの（出典: raw/official-*.txt、取得 2026-10-22）

- CLAUDE.md は「target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence」（memory :88）
- サブディレクトリ CLAUDE.md は「load on demand」（:64）。`paths` 付き rules も該当ファイルを触ったときだけ（:88）
- `@import` は最大4段。文脈コストは減らない（:104、ADR-076「否定した選択肢」と一致）
- スキルは「a skill's body loads only when it's used」「descriptions are loaded into context」「Keep SKILL.md under 500 lines」「supporting files … only when needed」（skills）
- UserPromptSubmit の `additionalContext` は system reminder として毎回挿入。`if` はツールイベント専用（hooks）
- `/doctor prompt-audit` が CLAUDE.md・rules・skills の古い記述・矛盾を点検する（memory :94-96）
- 圧縮後も root CLAUDE.md は再注入、サブ CLAUDE.md と paths rules は再び on demand（memory :627）

### 2-8. Opus 審査で追加した事実（2026-10-22）

- 【事実】行数上限は root CLAUDE.md が120行（`frontend/scripts/check-claude-size.js:23`）で、`CLAUDE.md:117` の本文「120 行を超えたら … ブロックする」と一致している。現在 CLAUDE.md はちょうど120行。入口を90行にする場合（design §10-2）は、この2か所を同じ便で揃える。
- 【事実】近い既存テーマ docs/specs/doc-parent-child/README.md（2026-07-01、文書の親子リンクを人がたどれる形にする）がある。本テーマは「AI が読む順番と量」を扱うため別テーマとし、README から相互にリンクする。doc-parent-child は §2-5 の「索引から辿れない specs」に含まれる。
- 【事実】本 recon を書いた会話（2026-10-22）でも、商品登録と無関係な入力に登録ルール全文が差し込まれた（§2-2 の再現）。

---

## 3. まとめ（設計へ渡す事実）

1. 自動読込は 462行/29,290字（うち MEMORY.md が 16,298字＝56%）。「必読」まで含めると 852行/約55,000字。
2. 関係ない入力への約100行注入は、正規表現1行（master-register-rules-guard.py:25）が原因。`if` では直せない。PreToolUse 側（:53-84）も「監視語の引用」で止まる過剰一致あり（本便で実測）。
3. 同じ決まりの二重化は CLAUDE.md↔AGENTS.md（6節）、frontend/backend 同様、設計文書間（推測禁止16行・file:line 14行）。~/.claude/CLAUDE.md:13 が二重化を要求している。
4. 索引から辿れない文書 1,880（handoff 1,809）。機械検査なし。
5. AGENTS.md は現状 Claude Code に読まれていない（CLAUDE.md 併存のため）。Codex 用の意味しか無い。

【未確認】過去会話記録の中の議論（§1）。
【未確認】Codex（AGENTS.md の読者）が現在も稼働しているか（AGENTS.md:42「現在の主 Generator は Claude Code」。Codex 稼働の実測は本便の範囲外）。
