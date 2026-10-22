---
mode: handoff
adr: 未起案（段0で新規 ADR として起案し ADR-076 を一部改める。§8 段0）
status: 草案（審査 REVISE 2回目反映済み・PO 判断待ち: §10-2・§10-4〜§10-7。KGI 合格ライン・測り方修正・K8〜K10 は PO 承認済み 2026-10-22）
---

# design — AI向け指示文書の「入口→目次→章→末端ページ」化（設計草案）

> この文書は何か（専門用語なしの1行）:
> AI が会話のたびに読まされる文書を「短い入口」だけにし、手順書は目次を辿って必要なときだけ読む形に組み替える設計の草案。製品コード・DB・本番・設定の実物には触れていない。

**対象ADR**: ADR-076（改める対象）・ADR-113（書式）・ADR-1029（マージ前審査）
**recon**: docs/handoff/doc-agenda-nav/recon.md（基準 origin/main 16000c2d5、2026-10-22）
- 親（あるべき姿）: [docs/specs/doc-agenda-nav/README.md](../../specs/doc-agenda-nav/README.md)（2026-10-22 作成。PO が「土台の文書を作成」と指示＝§10-1 は解決）
- 関連 ADR: ADR-076（CLAUDE.md 階層化・行数上限）／ADR-027（i18n）／ADR-113（本書の書式: mode: handoff）／ADR-1029（マージ前審査）
- 形式: docs/STANDARD-WORKFLOW.md §1〜§2・§1.7 と ADR-113 pattern 2 に従う

---

## 1. 目的

PO の言葉（2026-10-22）: 「マニュアルのようにアジェンダがあり、章ごとに分類されていて指定の手順書や作業方法などは再分類された末端ページに辿り着くまで読めない仕様にすれば無駄な情報がなくなり、精度も向上する…都度アジェンダから末端ページまでたどり着くフロー」

これを文書の SSOT（同じ決まりは1か所）と、Claude Code の読み込み仕様（recon §2-7）に合わせて実現する。

## 2. KGI / KPI（PO が画面・出力で○×を一義に判定できる粒度）

| # | 指標 | 今（recon 実測） | 後（合格ライン） | 測り方 |
|---|---|---|---|---|
| KGI-1 | 会話開始時に自動で入る行数（ユーザー側＋プロジェクト側の指示＋rules。MEMORY.md を除く） | 313行/12,992字 | **200行以下** | raw/autoload-sizes.txt と同じコマンド（wc -l -m）を実行し合計。段3以後は CLAUDE.md が取り込む AGENTS.md の行数も足す（取り込みは文脈を減らさない・§5） |
| KGI-2 | 関係ない入力（raw/prompt-regex-test.txt の無関係例文5本）で商品マスタ登録ルールが注入される回数 | 5/5 | **0/5**（関係あり例文2本は 2/2 のまま） | python3 -I で正規表現に例文を通す（同ファイルの手順） |
| KGI-3 | 同じ決まりが2ファイル以上に本文として書かれている件数（recon §2-4 の9語） | 9語すべて複数ファイル | **プロジェクト側（CLAUDE.md/AGENTS.md/frontend/backend）で 0 語**（ユーザー側 ~/.claude は本便の範囲外） | raw/duplicates.txt と同じ grep |
| KGI-4 | 入口から目次を辿って届かない docs/specs・docs/ai-agents の文書数 | specs 35・ai-agents 19 | **0** | raw/reachability.txt と同じ幅優先探索（CI 化後は CI の出力） |
| KGI-5 | 入口から末端ページまでの段数 | 最深14段 | **入口→目次→章→末端 = 3段以内**（docs/handoff は対象外） | 同上の depth 出力。**注**: 今の構造図（§4）では各テーマの表紙（specs の各 README）が3段目、その子（例 kgi.md）が4段目になる。**PO 承認（2026-10-22 原文「1」）で「末端＝各テーマの表紙」と数える**（docs/specs/doc-agenda-nav/kgi.md K5） |
| KGI-6 | 目次の各項目に「いつ読むか」1行が付いている割合 | 索引 docs/specs/README.md は状態列はあるが「いつ読むか」列なし | **100%** | 目次ファイルの表に「いつ読むか」列が空欄なし（CI で空欄を数える） |
| KGI-7 | 安全の決まり（不可逆操作の PO 確認・VPS 鍵制限・main 直 push 禁止）が入口に残っているか | CLAUDE.md:28-40 に在る | **入口に残る（移さない）** | 入口（段3以後は AGENTS.md。CLAUDE.md は 「@AGENTS.md」 で取り込む）で「不可逆操作は必ず PO 確認」「VPS 直作業禁止」「直接コミット禁止」を grep し各1件以上 |
| KGI-8〜10 | 守られた回数・会話の始まりに読む量・目次を開いた割合 | 未測定 | 記録のみ（合格ラインは基準値を測った後に PO と決める） | §14-2・docs/specs/doc-agenda-nav/kgi.md K8〜K10（PO 承認済み 2026-10-22 原文「1」） |

KPI は各段（§8）の完了ごとに上表の該当行を再測定する。

## 3. 範囲／範囲外

- 範囲: リポジトリ salesanchor の AI 向け指示文書（CLAUDE.md・AGENTS.md・frontend/backend の同2種・docs/STANDARD-WORKFLOW.md・docs/ai-agents/・docs/specs/README.md・docs/adr/FEATURE-INDEX.md）、~/.claude/scripts/master-register-rules-guard.py の正規表現1行（と origin/main の同名スクリプト）、新設する CI 1本。
- 範囲外: docs/handoff（便の記録・1,809件。索引化しない。理由: 作業記録であって手順書ではない）、docs/adr（README.md 自動生成で既に全件辿れる）、MEMORY.md（auto memory。別便。ただし KGI-1 の分母から外して測る理由は recon §2-1 #5: 16,298字で自動読込の 56%）、~/.claude/CLAUDE.md と ~/kb（ユーザー個人設定。別便）、フロントエンド（画面は触らない。触る場合はデザイントークンと components/ の金型に従う。本設計では該当なし）。

## 4. 構造図（前→後）

### 今（recon §2-1〜2-3）
```
会話開始
 ├ ~/.claude/CLAUDE.md 84 ─@→ ~/kb/AGENTS.md 32
 ├ ~/.claude/rules/common/{agents,git-workflow}.md 77
 ├ MEMORY.md 149
 └ CLAUDE.md 120 ──「必ず read」→ STANDARD-WORKFLOW 175 ─→ specs/README 100 ─→ 各仕様書 … 最深14段
                 ──「必読」→ executor-checklist 52
   AGENTS.md 281（Claude には読まれない・CLAUDE.md と6節が同文）
入力のたび: PROMPT_RE 一致で registration-rules.md 76行 を注入（無関係入力でも）
```

### 後
```
会話開始（自動）= 入口のみ（Claude: CLAUDE.md が @AGENTS.md を取り込む／Codex: AGENTS.md を直接読む）
 └ AGENTS.md（全 AI 共通の正本）＋ CLAUDE.md（@AGENTS.md＋Claude 固有のみ）合計 ≤ 上限（§10-2）
     ├ 安全の決まり（不可逆操作・PO確認・鍵制限・ブランチ直push禁止）… 本文のまま残す（KGI-7）
     ├ 「作業の型は目次から辿る」1行
     └ 目次へのリンク1本 → docs/INDEX.md（目次・≤ 60行）
                            ├ 章A 開発の進め方   … いつ読むか: 便を始める前
                            │   └ 末端: STANDARD-WORKFLOW.md / executor-checklist.md / branch-operations/README.md
                            ├ 章B 設計仕様書      … いつ読むか: 新テーマ・索引に載る領域に触れる前
                            │   └ 末端: specs/README.md（既存の索引＝章ページとして再利用）→ 各 README
                            ├ 章C 設計判断（ADR） … いつ読むか: recon で既存設計を探すとき
                            │   └ 末端: adr/FEATURE-INDEX.md → 各 ADR
                            ├ 章D 領域別ルール    … いつ読むか: その領域のファイルを触るとき（自動）
                            │   └ 末端: frontend/CLAUDE.md, backend/CLAUDE.md, backend/*/CLAUDE.md（on demand のまま）
                            ├ 章E 商品マスタ登録  … いつ読むか: 商品マスタに登録するとき
                            │   └ 末端: specs/product-master/registration-rules.md（フックは「登録操作の直前」だけ出す）
                            └ 章F 運用・本番      … いつ読むか: VPS・デプロイ・監視を触るとき
                                └ 末端: docs/ops/*, runbooks/*
   Codex 固有の手順 = docs/ai-agents/codex-operations.md（章A の末端。目次から辿る）
入力のたび: 「マスタ…登録」が同じ文に共起したときだけ注入（KGI-2）
```
段数: 入口(0)→目次(1)→章(2)→末端(3)。KGI-5。

## 5. 各文書の行き先（複製なし。移すときは元に「→目次」のリンクだけ残す）

| 文書 | 今 | 後 | 根拠 |
|---|---|---|---|
| CLAUDE.md（120行） | 前提・ブランチ運用・不可逆・VPS・標準フロー要約・i18n・UI統治・ルール追加判定木 | **入口に残す**（段3で AGENTS.md へ移し、CLAUDE.md は取り込む）: 前提（:7-18）・VPS 直作業禁止（:26-35）・不可逆操作（:36-42）・直接コミット禁止の1行（:49）・目次リンク。**移す**: ブランチ運用の手順詳細（:44-69 のうち :49 を除く）→ specs/branch-operations/README.md（既に正典と明記）、標準フロー要約（:70-82）→ STANDARD-WORKFLOW（正本 :156 の方針）、i18n 本文（:90-95）→ frontend/CLAUDE.md（既に ESLint 強制の記述あり :25-27）、ルール追加判定木（:105-117）→ docs/INDEX.md の末尾章（行番号は origin/main 2026-10-22 の `git show origin/main:CLAUDE.md` 実測） | 公式「under 200 lines」、ADR-076 の分割方針、STANDARD-WORKFLOW:156 |
| AGENTS.md（281行） | CLAUDE.md と6節同文＋Codex 固有（役割分担・AEON・Codex UI 補助・引き継ぎ・カード定型文）。「VPS 直作業禁止」節は無い（見出し実測: `git show origin/main:AGENTS.md \| grep -n '^#'`、2026-10-22） | **全 AI 共通の入口（正本）にする**（§10-3 解決・構造は PO 承認済み 2026-10-22）。本文 = 前提・安全の決まり（不可逆操作・VPS 鍵制限・直 push 禁止。CLAUDE.md から移して1か所に）・「作業の型は目次から辿る」1行・目次リンク。Codex 固有節（役割分担・AEON・Codex UI 補助・引き継ぎ）は docs/ai-agents/codex-operations.md（新設・移動のみ）へ移し、目次の章A から辿る。カード定型文（:259-281）は design-partner.md §6 が原本と書いてあるので **PO 確認後に**そちらへ一本化 | PO 2026-10-22「どのAIを使っても指示が届くように指示をＳＳＯＴしている」。Codex は AGENTS.md を根から作業場所まで連結して読み、合計 32 KiB で打ち切る（project_doc_max_bytes 既定。公式 https://learn.chatgpt.com/docs/agent-configuration/agents-md 取得 2026-10-22）。取り込み記法（@path）は同公式に記載なし＝**Codex は @ を展開しない前提で、本文は AGENTS.md 側に置く** |
| CLAUDE.md（入口化後） | — | 「@AGENTS.md」 の1行＋Claude Code だけに要る決まり（CLAUDE.md 行数検査・.claude/agents 変更前の pull 等）のみ | Claude Code 公式「put an 「@AGENTS.md」 import in a `CLAUDE.md` … Add any Claude-specific instructions below the import」（https://code.claude.com/docs/en/memory 取得 2026-10-22。取り込みも起動時に読み込まれ文脈量は減らない＝KGI-1 は CLAUDE.md＋AGENTS.md の合計で数える） |
| frontend/AGENTS.md・backend/AGENTS.md | CLAUDE.md と同文 | 本文の正本を AGENTS.md 側に一本化し、同ディレクトリの CLAUDE.md は 「@AGENTS.md」＋Claude 固有のみ（ルートと同じ向き） | 同上 |
| docs/STANDARD-WORKFLOW.md（175行） | 正本 | **そのまま**（章A の末端）。§7:157「CLAUDE.md に要約＋リンク」の「要約」を「リンクのみ」に改める1行修正（SSOT） | :156 |
| docs/ai-agents/executor-checklist.md | 必読 | そのまま（章A の末端）。「いつ読むか: 便の作業前・commit前・PR前」 | :5 |
| docs/ai-agents/design-partner.md（438行） | 設計セッション必読 | 章A の末端として残す。§0.5 の必読リストは目次へのリンク1本に置換（必読の重複宣言を無くす） | :44-53 |
| docs/specs/README.md（100行） | 仕様書索引 | 章B のページとして流用。表に「いつ読むか」列を追加（KGI-6）。辿れない specs 35件（discord-reaction, doc-parent-child, process-hardening/proof-of-behavior 等。raw/reachability.txt）を登録 | STANDARD-WORKFLOW:32 |
| docs/adr/FEATURE-INDEX.md | ADR 索引 | 章C のページ。変更なし | — |
| docs/ai-agents/ の辿れない19件 | 孤立 | 章A/章F に登録、または docs/handoff へ移動（便の記録なら）。1件ずつ PO 確認（§10-4） | recon §2-5 |
| specs/product-master/registration-rules.md | フックで毎回注入 | 章E の末端。フックは正規表現を狭め、PreToolUse（登録操作の直前）は現状維持 | recon §2-2 |
| ~/.claude/CLAUDE.md:13「AGENTS.md も同時更新」 | 二重化を要求 | **範囲外だが矛盾**: 本文の正本が AGENTS.md 1か所になれば「同時更新」は不要になる（AGENTS.md だけ直せば Claude にも届く）。書き換えか削除かは PO 判断（§10-5） | recon §2-4 |

## 6. 守りの仕組み（機械強制）

| 守るもの | 仕組み | 既存との重なり |
|---|---|---|
| 入口の行数（KGI-1） | 既存 CI「CLAUDE.md line count check」の LIMITS（frontend/scripts/check-claude-size.js:22-28）を直す: root CLAUDE.md の上限は §10-2 の回答値に、**AGENTS.md（段3以後の本文の正本）を新たに登録**、docs/INDEX.md を limit 60 で登録。同スクリプトの案内文 :58「ファイル名は必ず CLAUDE.md にすること」は本設計（本文を AGENTS.md に置く）と食い違うため段3で書き換える（ADR-076 の一部改訂・段0の ADR に記載） | 既存必須チェックを流用。新規 required check 追加なし＝Branch Protection 変更なし |
| 目次から辿れる（KGI-4/5/6） | 新設 .github/workflows/doc-index-reachability.yml（名称仮）: docs/INDEX.md を起点に docs/specs・docs/ai-agents の .md を幅優先で辿り、①届かない文書 ②4段以上 ③「いつ読むか」空欄 を列挙。**初期は警告のみ。昇格条件は期間ではなく「警告段階の出力が連続5回の PR で 0 件」**（§14 の C21: GitLab は違反0の確認後に error 化。C22/C23: 止めない設定のまま固定化した失敗例。旧案「2週間」は根拠なしのため改めた）。リポジトリ内リンクの行き先が実在するかも同じ走査で検査（外部 URL は対象外。C20） | reachability の実装は raw/reachability.txt を作った Python をそのまま流用（Python 3.12・標準ライブラリのみ） |
| 同じ決まりを2か所に書かない（KGI-3） | 同 CI に「CLAUDE.md と AGENTS.md の本文が同一見出しを持たない」検査（見出し行の集合の交差 = 0）と「各 CLAUDE.md に 「@AGENTS.md」 行がある」検査を追加（root・frontend・backend） | 既存の scripts/check-doc-heading-duplicates.sh（.github/workflows/process-artifacts-gate.yml:47 で実行中）を流用できるかを段2のカード作成時に実物で確認し、流用を優先する |
| 関係ない注入ゼロ（KGI-2） | master-register-rules-guard.py:25 を re.compile(r"マスタ[^。\n]{0,40}登録|登録[^。\n]{0,20}マスタ") に変更（raw/prompt-regex-test.txt 案2: 無関係 5/5→0/5、関係あり 2/2 維持、別マスタ「顧客マスタに登録」は一致＝許容）。origin/main の scripts/agent-hooks/ と ~/.claude/scripts/ の両方（diff 同一を recon で確認済み）。PreToolUse 側（:53-84）は本便では変更なし。ただし本便で「監視語を引用した調査記録の Write」が止まった実測（raw/hook-block-event-20261022.txt）があるため、EXEMPT_PATHS に報告フォルダ（~/CC報告ファイル-keep/）を足すかは §10-7 で PO に聞く | 既存テスト scripts/agent-hooks/test_master_register_rules_guard.sh（T1〜T8）が在る。CI からは呼ばれていない（.github/workflows/agent-hooks-test.yml:24 は review-gate のみ）→ 段1では手元実行を必須にする |
| 安全の決まりが入口から消えない（KGI-7） | 同 CI に「入口（段3までは CLAUDE.md、段3以後は AGENTS.md）に『不可逆操作は必ず PO 確認』『VPS 直作業禁止』『直接コミット禁止』の3文字列が各1件以上ある」検査（3文字列は受け入れ基準 K7 と同一。実物は origin/main CLAUDE.md:36・:26・:49） | — |
| 変更そのもの | CLAUDE.md/AGENTS.md/STANDARD-WORKFLOW は executor-checklist §2:29-30 により「危険ファイル変更 PR」＝PO GO 必須。ADR 起案（§9） | ADR-1029 マージ前審査フック |

## 7. 弊害・リスクと対策

| リスク | 対策 |
|---|---|
| 安全の決まりが「目次を辿らないと読めない」場所へ落ち、読み飛ばされる | 安全の決まりは入口に残す（KGI-7・CI 検査）。目次化するのは「手順」だけ |
| 移動時に文が欠ける（SSOT 化の典型事故） | 1段1ファイル。移動前後で git diff --stat と該当節の行数が一致することを PR 本文に貼る。削除行のある PR は「削除するファイル」欄に実測で列挙（executor-checklist §0） |
| AI が目次を辿らず作業に入る（お作法頼み） | 入口に「作業の型は目次から辿る」を残す。辿ったかは機械で検査できない＝**人の確認**（STANDARD-WORKFLOW §1.7「人手で守る」相当）。agent-console のセッション記録で Read の有無を後から数えられる（**未確認**: 記録の粒度） |
| Codex が AGENTS.md の本文を失い動けなくなる | §10-3 の PO 回答（Codex は使用中）を受け、本文は AGENTS.md 側に残す向きに変更（CLAUDE.md が取り込む）。Codex は @ を展開しない前提なので、AGENTS.md を 「@CLAUDE.md」 だけにする案は採らない |
| Claude Code が AGENTS.md を取り込めない環境 | 取り込みは CLAUDE.md 内の 「@AGENTS.md」 行で行う（公式: この形はどの設定値でも二重読込にならない :435）。段3の測定で、会話開始時の文脈に AGENTS.md の本文が入ったことを /memory 表示で確認する |
| 正規表現を狭めて必要な注入が落ちる | PreToolUse 側の拒否（登録操作そのものを止めて規則を出す）は残るため、最後の砦は維持。狭めた案の取りこぼし例文を raw に積み増して測る |
| 圧縮（compaction）後に目次を忘れる | root CLAUDE.md は圧縮後も再注入される（公式 :627）。入口にリンクがあれば再び辿れる |

## 8. 段取り（1段=1PR。変更→反映→測定→次）

| 段 | 変更 | 測定（KGI） | 戻し方 |
|---|---|---|---|
| 0 | 親仕様書と specs/README.md への1行登録は **済み**（f6d8a0be6・#4638）。残り: 新規 ADR を Proposed で起案し `node scripts/generate-adr-index.js` で docs/adr/README.md を再生成。ADR には ADR-076 との衝突点を列挙する: ①ADR-076:55「上限が小さすぎると具体例が削除され判断精度が低下」を理由に上限を据え置いた点（本設計は上限を §10-2 で決め直す）②check-claude-size.js:58「ファイル名は必ず CLAUDE.md」（本設計は本文を AGENTS.md に置く）。ADR-076 本体には「一部改訂: 新 ADR」の1行だけ足す。上限の数値は §10-2 待ちのため ADR では「§10-2 で決める」と書く | — | PR revert |
| 1 | master-register-rules-guard.py:25 の正規表現。**変更前**（実物）: `(マスタ|商品).*登録|登録.*(マスタ|商品)`（re.S）／**変更後**: §6 の KGI-2 行。repo 側 scripts/agent-hooks/ を PR で審査 → ~/.claude/scripts/ へは前例 docs/handoff/master-register-rules-hook/design.md:37 の型（PO が `!` で写す→写す前に .bak を作る→repo 版と diff 一致を確認）。例文は raw/prompt-regex-test.txt の7本（無関係4本＋境界1本＋関係あり2本）をカードに全文で写す。新しい式は「マスタ」を含まない「商品を登録して」を拾わなくなる → この例文を試験に足し「拾わない」を期待値とし、PreToolUse 側（登録操作の直前に止める）が残ることを前提として明記する。既存テスト T1〜T8 を手元で実行 | KGI-2 | 1行を戻す（.bak から戻す） |
| 2 | docs/INDEX.md 新設（章A〜F・「いつ読むか」列）＋ specs/README.md に「いつ読むか」列＋辿れない specs 35件を登録 | KGI-4/5/6（警告段階の CI で観測） | ファイル削除 |
| 3a | Codex 固有節を docs/ai-agents/codex-operations.md へ移すだけ（AGENTS.md には目次への1行を残す）。§10-3 の構造承認後 | KGI-3 途中値 | PR revert |
| 3b | CLAUDE.md の「移す」節（§5）を既存の移動先へ移す（1PR1移動先。branch-operations・STANDARD-WORKFLOW・frontend/CLAUDE.md・INDEX の4本に分けてよい） | KGI-1 途中値 | PR revert |
| 3c | 入口の入れ替え: 安全の決まり・前提を CLAUDE.md から AGENTS.md へ移し、CLAUDE.md を 「@AGENTS.md」＋Claude 固有のみにする ＋ LIMITS（§6）＋ STANDARD-WORKFLOW §7:157-159（入口を「ターミナル＝CLAUDE.md」と定めている箇所）を「AGENTS.md が正本・CLAUDE.md が取り込む」に書き換え | KGI-1/3/7（ルート分）。/memory 表示で AGENTS.md の本文が会話に入ったことを確認 | PR revert（2ファイル＋STANDARD-WORKFLOW） |
| 4 | frontend/backend の同2種を同じ向き（AGENTS.md が正本、CLAUDE.md は 「@AGENTS.md」＋固有のみ）に揃える | KGI-3（全体） | PR revert |
| 5 | doc-index-reachability CI を警告→失敗へ昇格（条件: 連続5回の PR で 0 件）。必須チェック（ruleset）への登録は Branch Protection／Ruleset の変更＝CLAUDE.md の不可逆操作リスト該当のため PO 確認を別にとる | KGI-4/5/6 が0であること | 警告に戻す |
| 6 | ~/.claude/CLAUDE.md:13 の扱い（書き換えか削除かは §10-5）（ユーザー側） | KGI-3 再測 | 1行を戻す |
| 7 | **ユーザー側の常時読込を短くする（§10-8 解決で追加）**。対象と実測（recon2/autoload-user.txt、2026-10-22）: ~/.claude/CLAUDE.md 84・~/kb/AGENTS.md 32・~/.claude/rules/common/agents.md 53・git-workflow.md 24 ＝ 193行（paths 付きの rules 10本は条件付き読込で対象外）。方法: 節ごとの行き先案（残す／paths 付き rules へ移す／リポジトリ側の正本へのリンクに置換）を一覧で PO に提示し、承認された分だけ変える。~/kb 側の記録（commit）は ~/kb/AGENTS.md:29 により PO が `!` で実行。上限の数値はプロジェクト側入口の行数（§10-2）と合わせて K1 ≤ 200 に収まるよう段7の開始時に一覧で示す | KGI-1（全体）・K8/K9（§14、PO 承認済み） | 各ファイルを変更前の写し（リポジトリ外 ~/CC報告ファイル-keep/ に保存）から戻す |

## 9. 外部・過去事例と我々への応用

| 出典 | 内容（測定値・日付） | 応用 | 限界 |
|---|---|---|---|
| Claude Code 公式 memory（https://code.claude.com/docs/en/memory 取得 2026-10-22） | 「target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence」／サブディレクトリ CLAUDE.md と paths rules は on demand／import は文脈を減らさない | 入口を短く、領域別は on demand に任せる（章D）。import で目次を取り込まない | 「遵守率低下」の数値は公式には無い |
| Claude Code 公式 skills（同 /skills） | 「a skill's body loads only when it's used」「Keep SKILL.md under 500 lines」 | 章E（商品マスタ登録）は将来スキル化の候補（description だけ常駐、本文は呼び出し時）。本設計では採らない（§10-6） | リポジトリに .claude/skills 無し（新機構導入は architect 判断が要る） |
| Anthropic「Effective context engineering for AI agents」（https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents 2025-09-29） | 「find the smallest set of high-signal tokens」「progressive disclosure」「just in time context」 | 本設計の原理そのもの（入口最小・必要時に辿る） | 定量の効果値は記事に無い |
| 自リポジトリ ADR-076（2026-05-28） | 外部エビデンス表「471行→61行（87%削減）で一貫性改善」「OpenAI AGENTS.md は150行以下目標」 | 上限引き下げ（120→90）の前例 | **未確認**: 表の出典 URL・日付が ADR に無い |
| 自リポジトリ PR #3358（2026-09-08） | design-partner.md の guards を節ごとに分割し目次化 | 同じ発想の先行例。効果測定の記録は PR に無い（**未確認**） | — |
| 自リポジトリ 本便 recon（2026-10-22） | 自動読込 462行/29,290字、無関係注入 5/5、辿れない文書 1,880 | KGI の「今」の値 | — |

## 10. PO に聞くこと（業務判断。番号で答えられる形）

1. **解決済み（PO 2026-10-22「土台の文書を作成して設計や仕様書まで作成をさせる」）**: 親仕様書（docs/specs/doc-agenda-nav/ の3ファイル）を**段0で先に作る**か、本 design.md を仕様書代わりにして段1から始めるか。
   - 1. 段0で作る【おすすめ】→ STANDARD-WORKFLOW §1.5/§1.8 どおり。PR が1本増える
   - 2. 段1から始める → 早いが、索引に親が無いまま進む（§1.8 違反）
2. 入口（CLAUDE.md）の上限を 90 行にしてよいか（今120）。
   - 1. 90行【おすすめ】→ 安全の決まり＋目次リンクで収まる試算（残す節は :8-16, :20-40, :44-45, :100 前後 ≈ 55行）
   - 2. 120行のまま → 行数は減らず、重複削減だけになる
3. **解決済み（PO 2026-10-22・原文「2,どのAIを使っても指示が届くように指示をＳＳＯＴしている」、構造は同日 PO 原文「1」で承認）**: Codex は今も AGENTS.md を読んで動いているか。
   - 1. 動いていない → 段4で AGENTS.md を薄い入口にする
   - 2. 動いている → Codex 固有節を残す形に変える（本文は移動、リンクで辿る）← **PO 回答**
   - 反映（構造は PO 承認済み 2026-10-22）: 本文の正本を AGENTS.md（全 AI 共通の入口）に置き、CLAUDE.md は 「@AGENTS.md」 で取り込む向きに変更（§4・§5・§6・§7・§8 段3/4）。旧案「AGENTS.md を 「@CLAUDE.md」 だけにする」は、Codex の公式説明に取り込み記法の記載が無く Codex に本文が届かないため不採用。
   - 審査（2026-10-22 2回目）の指摘: 選択肢2の文面は「Codex 固有節を AGENTS.md に残し本文は移動」で、採用した構造（本文を AGENTS.md に置き Codex 固有節を移す）と向きが逆。PO の補足（SSOT）からの解釈であり、構造そのものの承認記録は無い → 構造を PO に確認した。Opus が「本文は『どのAIも最初に読む共通の入口』1か所に置き、Claude の入口はそれを読み込む1行と Claude 専用の決まりだけにする」を選択肢1として示したのに対し、**PO 原文「1」（2026-10-22）で承認**。
4. docs/ai-agents の辿れない19件と specs の35件を「目次に登録」か「handoff へ移動（記録扱い）」か、1件ずつ表を出して確認してよいか（段2の前に一覧を提示）。
   - 1. 一覧を出してから決める【おすすめ】
   - 2. 全部登録する
5. ~/.claude/CLAUDE.md:13「AGENTS.md も同時に更新」を段6で消してよいか（3 の答えに依存）。
6. 章E（商品マスタ登録）を将来スキル化する検討を別便で起こすか（本便では正規表現修正のみ）。
   - 1. 別便で検討【おすすめ】
   - 2. 検討しない
7. 登録ルールのフック（PreToolUse 側）が、監視語を「説明として引用」した文書の書き込みでも止まる件（本便で実測）。
   - 1. 免除パスに ~/CC報告ファイル-keep/ を足す【おすすめ】→ 調査記録は止まらなくなる。登録操作そのものは引き続き止まる
   - 2. 今のまま → 規則を説明する文書を書くたびに ack 行が要る
8. **解決済み（PO 2026-10-22・原文「1,fableに相談、外部での導入事例と成功事例と成功要因、失敗事例と失敗要因を徹底的に調査してエビデンスを取得してくれ…」）→ 選択肢1（ユーザー側を短くする段を本テーマに足す。200行は保つ）。外部事例の調査と Fable への相談・レビュアー審査・定着の仕組みの検証を追加で指示された（§14・§15・維持の仕組みに反映済み）。** （引き継ぎ後に Opus が発見・2026-10-22）K1 の 200行は、本便の範囲（プロジェクト側）だけでは届かない。** 実測（2026-10-22 `wc -l`）: ユーザー側 ~/.claude/CLAUDE.md 84・~/kb/AGENTS.md 32・常時読込の rules（agents.md 53＋git-workflow.md 24）77 ＝ **193行**、プロジェクト側 CLAUDE.md 120行、計313行。ユーザー側が今のままだと、プロジェクト側の入口を7行以下にしないと200行に入らない。前セッションの設計で、K1 の分子にユーザー側を含めながら範囲外にしていた（入れ忘れ）。
   - 1. 個人用の決まり（ユーザー側）を短くする便を、本テーマの段として足す（200行は保つ）
   - 2. K1 をプロジェクト側の入口だけで数える形に改め、合格ラインを付け直す（KGI の再承認が要る）
   - 3. 200行をやめ、プロジェクト側を減らした結果の行数を合格にする

## 11. 未確認・開いている論点

- 過去会話記録に同じ構想の議論があるか（recon §1。Grep ツールのあるセッションで再実行）
- K4/K5 の基準値（raw/reachability.txt）を出した Python が design/・recon2/ に保存されていない（審査 2026-10-22）。段2のカードで作り直し、docs/handoff/doc-agenda-nav/ に保存して基準値（specs 35・ai-agents 19・最深14段）を再現できることを確かめてから CI に使う
- agent-console のセッション記録から「目次を辿ったか」を数えられるか（§7）
- ADR-076 外部エビデンス表の出典

## 12. 自己審査（初版時点の記録。**更新済み**: 最新の判定は §13 を正とする）

> 2026-10-22 追記: 下の指摘のうち「親仕様書未作成」は §10-1 解決で、「Codex の AGENTS.md 利用実態が未確認」は §10-3 解決で解消。残りは §13 を参照。

判定（初版時点）: **REVISE**（設計の骨格は確定できるが、PO 判断 1〜3 が未回答で段0・段3・段4 の最終形が決まらない）

根拠:
- APPROVE できる部分: 現在地は file:line と生出力で裏付け済み（recon §2）。KGI は全て測定コマンド付き。段1（正規表現1行）は根拠・測定・戻し方が揃い単独で進められる。
- REVISE が要る部分: 親仕様書未作成（§1.8 新規テーマ）、Codex の AGENTS.md 利用実態が未確認のまま段4を書いている、ユーザー側 ~/.claude の矛盾（:13）は範囲外なのに段6に置いている（PO 実行前提と明記したが、範囲の線引きを PO に確認すべき）。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| K1 自動で入る行数（MEMORY.md を除く）が200行以下 | recon §2-1 の6ファイルから MEMORY.md を除いた5ファイルを wc -l で合計。段3以後は AGENTS.md（CLAUDE.md が取り込む）を足した6ファイル |
| K2 無関係な例文5本で差し込み0、関係ある例文2本で2/2 | 例文7本を python3 -I で新しい正規表現に通し、True/False を表で出す（例文は recon 外の raw/prompt-regex-test.txt と同じ） |
| K3 プロジェクト側4種の入口で9語の重複0 | recon §2-4 と同じ grep を CLAUDE.md・AGENTS.md・frontend・backend に実行 |
| K4 目次から届かない specs・ai-agents の文書0 | 新設 CI の出力（届かない文書の一覧が空） |
| K5 入口から末端まで3段以内 | 同 CI の段数出力の最大値 |
| K6 目次の「いつ読むか」空欄0 | 同 CI の空欄数 |
| K7 入口に安全の決まり（不可逆操作の PO 確認・VPS 鍵制限・main 直 push 禁止）が残る | 入口ファイル（段3まで CLAUDE.md、段3以後 AGENTS.md）で grep -n "不可逆操作は必ず PO 確認"・grep -n "VPS 直作業禁止"・grep -n "直接コミット禁止" が各1件以上。段3以後は加えて grep -n "^@AGENTS.md" CLAUDE.md が1件 |
| 既存の必須チェックが全部緑 | PR の Checks 画面（必須チェック15件すべて。うち文書に関係するのは CLAUDE.md line count check・process-artifacts gate・ADR index is up to date・guard-authoring/evaluation） |

## 13. Opus 審査（2026-10-22）

判定: **REVISE**（Fable の自己審査と同じ）。

- 確かめたこと: K1 の今の値（6ファイル計462行・MEMORY.md 149行）を Opus が wc で再計測し一致。K2 の原因の正規表現が ~/.claude/scripts/master-register-rules-guard.py:25 にあることを実物で確認。案2の例文結果（無関係0・関係あり2/2）を raw で確認。行数上限は検査スクリプトと CLAUDE.md:117 の本文が120行で一致（recon §2-8）。
- 解決したこと: §10-1（親仕様書）は PO 指示で作成済み。
- 残る理由（初回時点）: §10-2〜7 が PO 判断待ち。§10-3 は PO 回答済みだが構造の承認が残る（§15）。段3・段4の実装カードはその承認まで書かない。段1（正規表現1行）は ~/.claude 側も触るため、ユーザー設定の変更として PO の実装承認を別にとる。
- 実装可否: 段0（ADR 起案・索引登録）と段1は、PO の実装承認があれば実装カードにできる。段2以降は §10 の回答後。

## 14. 外部事例調査と実物確認の反映（2026-10-22 引き継ぎ後・PO 指示「外部での導入事例と成功事例と成功要因、失敗事例と失敗要因を徹底的に調査」）

生出力（リポジトリ外）: ~/CC報告ファイル-keep/agenda-nav-20261022/research/external-cases.md（Fable 調査、事例26件: 成功・数値あり8／失敗・否定・数値あり10／数値なし・未確認8）、同 research/fable-consult.md（Fable の所見）、同 recon2/（Sonnet 実物確認）。

### 14-1. Opus が出典で照合した事例（要旨ページで確認できた範囲だけを書く）

| # | 5W2H（誰が・いつ・どこで・何を・なぜ・どう・どれだけ） | 我々への意味 |
|---|---|---|
| C2 | Damon McMillan／2026-05-11／arXiv 2605.10039／Claude Code CLI 1,650 セッション（関数単位の観察 16,050）・TypeScript 2 コードベース・5 課題・3 モデル／指示ファイルの構造4変数（大きさ等）が指示遵守に効くかを要因実験／要旨原文「None of the four structural variables … produces a detectable contrast after multiple-testing correction」「Size and conflict nulls are supported by affirmative-null Bayes factors (BF10 between 0.05 and 0.10)」「approximately 5.6% lower odds of compliance per step (OR = 0.944)」 | **ファイルを短くしても、守られる率が上がるとは言えない**。守られる率は会話が進むほど下がる。行数別の率（25/100/250/500行で 60.0/65.2/67.7/64.0%）は Fable が本文から取得、Opus は要旨のみ照合 |
| C3 | Gloaguen ほか（ETH Zürich 系）／2026-02-12／arXiv 2602.11988／複数の LLM・コーディングエージェントで AGENTS.md 等の効果を評価／要旨原文「does not generally improve task success rates, while increasing inference cost by over 20% on average」 | 常時読む文書を足しても成功率は上がらず、費用だけ 20% 超増える＝**自動で読む量を減らす方向は費用面で支持**される |
| C4 | Lulla ほか／2026-01-28（v2 2026-03-30）／arXiv 2601.20404／AGENTS.md の有無と効率／要旨「lower median runtime」（28.64% 減）「reduced output token consumption」（16.58% 減） | 入口ファイルが「在る」ことは時間・量を減らす。入口を無くさず短くする本設計と整合 |
| C5 | Prakhar Khatri／2026-07-28／arXiv 2607.27250／実リポジトリ 17 課題・288 実行・2 エージェント（Claude 系・Codex）／要旨「Context strategy does not measurably move correctness on either agent (bounded to <=10-15pp via equivalence testing)」 | 読ませ方の工夫で正しさは大きく動かない（±10〜15pt 以内）。**精度向上を約束する根拠にはできない** |
| C6 | 利用者報告／2026-01-11／anthropics/claude-code Issue #17530／約400行の CLAUDE.md／原文「failing to follow explicit CLAUDE.md instructions in approximately 50% of sessions」（作者の見積もり・未検証、not planned で閉鎖） | 失敗の逸話。数値は見積もりなので**成功・失敗の証明には使わない** |

その他の事例（C1・C14〜C24 等）は Fable 取得のまま。Opus 未照合のものは設計の合否根拠に使わず、方針の参考に留める。

### 14-2. 結論（事実ベース）

- 【事実】行数を減らす効果として外部に数値があるのは「費用・時間・読込量」（C3・C4）。「守られる率・精度」が上がる数値は無く、むしろ差が出ないという研究（C2・C5）がある。
- したがって本設計の効果は **「軽く・速く・安く・同じ決まりが1か所」** として約束し、**「精度が上がる」は自分たちで測るまで約束しない**。PO のあるべき姿（「精度も向上する」）を確かめるには、KGI に次を足した（**PO 承認済み 2026-10-22 原文「1」**。合格ラインは基準値を測った後に PO と決める。正本は docs/specs/doc-agenda-nav/kgi.md）:
  - K8 守られた回数: 入口に書いた決まりのうち機械で数えられるもの（例: 作業場所を new-worktree.sh で作った／PR 本文に必須欄がある）を、同じ種類の便10回ずつ前後で数える
  - K9 会話開始直後の読込量（トークン）: /context の表示値を前後で記録
  - K10 目次を開いた割合: 手順を要する便で docs/INDEX.md を Read した割合。測る仕組み（Read を記録するフック）は新設のフック＝PO の実装承認が要る。公式の InstructionsLoaded フックが目次の Read で発火するかは**未確認**
- 【事実】昇格条件「2週間」は根拠なし → 「連続5回 0 件」に改めた（§6・§8 段5）。**「5回」の数値に外部の出典は無い**（C21 は「違反0を確かめてから失敗化した」という順序の根拠で、Opus 未照合）。回数は Opus の決めで、段5の前に見直せる。
- 【事実】登録ルールのフックには既存テスト scripts/agent-hooks/test_master_register_rules_guard.sh があるが、CI から呼ばれていない（recon2/item9.txt、agent-hooks-test.yml:24 は review-gate のみ）→ 段1のカードで手元実行を必須にし、CI への配線は CI 変更として PO 承認を別にとる。

### 14-3. 開発ルールの確認（recon2/dev-rules.txt・design-check-run.txt）

- 本 design.md は scripts/check-process-artifacts.js の validateDesignDoc・validateMaintenanceSection で エラー0（Sonnet が読み取り専用で実行。作業場所は origin/main より13コミット遅れの時点）。PR 前に origin/main へ追従して再実行する。
- ADR-113 の手順（recon→設計確定→Architect 整合検査1回→実装→CI）に従う。カード検査は scripts/card-lint.sh（カード作成時に実行）。
- 行数の記載: origin/main では CLAUDE.md:117「120 行を超えたら」と check-claude-size.js:23 の上限 120 が一致（382d3bff5 で解消済み。§13 と同じ）。手元の古い checkout だけが「90 行」のまま。段3で上限を変えるときは本文と LIMITS を同じ PR で直す。

## 維持の仕組み

- 守り手（既存・必須チェック。ruleset 実測 recon2/c10-rules.txt）: .github/workflows/check-claude-size.yml（job「CLAUDE.md line count check」）、process-artifacts-gate.yml（「process-artifacts gate」）、adr-index-check.yml（「ADR index is up to date」）
- 追加予定の守り手（段2で新設、まだ存在しない）: doc-index-reachability.yml（名称仮。目次到達・段数・「いつ読むか」空欄・リポジトリ内リンクの行き先実在・CLAUDE.md↔AGENTS.md 見出し重複・各 CLAUDE.md の 「@AGENTS.md」 行・安全見出しの存在を検査。段2で警告、連続5回0件で段5に失敗化し、必須チェック登録は PO 確認）
- 担当と数え方: 担当は本テーマの台帳（.claude-pipeline/active-work.d/ の本テーマの1枚）を持つ Opus セッション。昇格の判定は `gh run list --workflow doc-index-reachability.yml --event pull_request --limit 5` の5件すべてで警告0件であることを、各段の完了時に台帳へ記録して数える（警告件数は job の要約に1行で出す作りにする・段2のカードに書く）
- リポジトリ外（CI が見えない）の守り手（段7で新設案・PO 承認待ち）: ~/kb/scripts/patrol.sh（毎週月曜 09:00 に Discord 通知。今の点検4項目は recon2 c11）に「会話開始時に自動で読まれるユーザー側ファイルの合計行数」を1項目足す
- 対象: 入口が再び太ること／目次から辿れない手順書が増えること／同じ決まりが2か所に戻ること／安全の決まりが入口から消えること／ユーザー側の常時読込が再び増えること
- 今ない仕組み（事実）: 指示文書の行数・リンク・索引を点検する定期 job は無い（STANDARD-WORKFLOW.md:167「governance が定期的に点検」に対応する定期 workflow は見つからず。governance 検証 2026-10-22）。近いものとして .github/workflows/claude-md-staleness-check.yml（四半期ごと・CLAUDE.md の最終更新が90日超なら Issue 化 :45-56）があるが、見るのは更新日だけ。上の2つで埋める
- 関所なしの部分: 「AI が目次を実際に辿ったか」→ K10 の記録フックが PO に承認されるまでは人手（agent-console の記録で事後確認）。理由: Read の有無は CI では見えない

## 15. 審査2回目（2026-10-22・PR #4649 HEAD 5c5758bee）と反映

- 審査役（model opus・新規起動）: **REVISE**（止めるべき0・直すべき9・任意3）。全文 /tmp/CC報告ファイル/agenda-nav-review-20261022.md（リポジトリ外）。
- 定着の検証（governance）: **MONITOR**（BLOCK 条件なし）。全文 /tmp/CC報告ファイル/agenda-nav-governance-20261022.md（リポジトリ外）。
- 反映したもの: K1 の数え方（段3以後は AGENTS.md を足す）／K7 の3文字列を受け入れ基準・§6 で統一し、:49 を入口に残す行として明記／§5 の行番号を origin/main の実測に修正／§6 の LIMITS に AGENTS.md を登録・:58 の案内文を書き換える計画／テストの有無の食い違い（在る・CI 未配線）／§13・§14-3 の古い記述／段0（済み分と ADR の衝突点）／段1（変更前・写し方・例文・取りこぼし前提）／段3 を 3a〜3c に分割／基準値 Python の未保存を §11 に／守り手の担当と「連続5回」の数え方／claude-md-staleness-check.yml の切り分け／見出し重複検査の流用候補／「5回」に外部出典が無いこと。
- PO 確認: ①§10-3 の構造は **PO 原文「1」（2026-10-22）で承認済み**（§10-3）。②（**PO 原文「1」2026-10-22 で承認・kgi.md に反映済み**）K5 の「末端」の数え方と K7 の判定対象（kgi.md:18 は「CLAUDE.md」）の修正、K8〜K10 の追加（KGI 表の修正＝再承認）。
- 段1は上の反映でカード化できる状態。段0は ADR の向き（新規＋ADR-076 一部改訂）を決めたのでカード化できる。段3・段4は ① の承認により、§10-2 の回答後にカード化できる。
