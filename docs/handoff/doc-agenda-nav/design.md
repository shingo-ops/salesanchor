---
mode: handoff
adr: ADR-1040（Proposed 2026-10-22。段0で起案済み。ADR-076 を一部改める。§8 段0）
status: 草案（審査9回目 REVISE を反映済み（§22）。最新の判定は末尾の審査記録を正とする。審査7回目 APPROVE on 084764bf3・§10-2 PO 回答済み（90行）・§10-4〜§10-7 と §11 の安全寄りの3文は PO「fableにまかせてくれ」で Fable が判断し反映済み（§20）・PO 判断待ちなし。KGI 合格ライン・測り方修正・K8〜K10 は PO 承認済み 2026-10-22。K8 を物差しにしない・K11・K12 の追加・K12 の測り方は PO 承認済み 2026-10-23。段0b・段0c の基準値は baseline.md）
---

# design — AI向け指示文書の「入口→目次→章→末端ページ」化（設計草案）

> この文書は何か（専門用語なしの1行）:
> AI が会話のたびに読まされる文書を「短い入口」だけにし、手順書は目次を辿って必要なときだけ読む形に組み替える設計の草案。製品コード・DB・本番・設定の実物には触れていない。

**対象ADR**: ADR-1040（本テーマ・Proposed）・ADR-076（改める対象）・ADR-113（書式）・ADR-1029（マージ前審査）
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
| KGI-4 | 入口から目次を辿って届かない docs/specs・docs/ai-agents の文書数 | specs 35・ai-agents 19（unreachable-list.md §1 で specs 17・ai-agents 19 に訂正。元の 35 は再現できない） | **0** | reach.py（unreachable-list.md §1 の定義。今はリポジトリ外 ~/CC報告ファイル-keep/agenda-nav-20261022/unreach/reach.py、段2で docs/handoff/doc-agenda-nav/ に入れる）の幅優先探索（CI 化後は CI の出力）。旧 raw/reachability.txt を出した Python は保存されておらず使わない（§11・審査9回目 直1） |
| KGI-5 | 入口から末端ページまでの段数 | 最深14段（同 §1 で最深15段に訂正） | **入口→目次→章→末端 = 3段以内**（docs/handoff は対象外） | 同上の depth 出力。**注**: 今の構造図（§4）では各テーマの表紙（specs の各 README）が3段目、その子（例 kgi.md）が4段目になる。**PO 承認（2026-10-22 原文「1」）で「末端＝各テーマの表紙」と数える**（docs/specs/doc-agenda-nav/kgi.md K5） |
| KGI-6 | 目次の各項目に「いつ読むか」1行が付いている割合 | 索引 docs/specs/README.md は状態列はあるが「いつ読むか」列なし | **100%** | 目次ファイルの表に「いつ読むか」列が空欄なし（CI で空欄を数える） |
| KGI-7 | 安全の決まり（不可逆操作の PO 確認・VPS 鍵制限・main 直 push 禁止）が入口に残っているか | CLAUDE.md:26-40 に在る | **入口に残る（移さない）** | 入口（段3以後は AGENTS.md。CLAUDE.md は 「@AGENTS.md」 で取り込む）で「不可逆操作は必ず PO 確認」「VPS 直作業禁止」「直接コミット禁止」を grep し各1件以上 |
| KGI-8〜10 | 守られた回数・会話の始まりに読む量・目次を開いた割合 | K8 不採用（PO 決定 2026-10-23 原文「1」）・K9 65.2k・K10 0/20（baseline.md） | K8 なし。K9 は MEMORY.md を除く Memory files 6.5k 以下（9.3k から3割減）・K10 は ~~10/20 以上（PO 決定 2026-10-23 原文「1,…」）~~ → 参考の数字・合否に使わない（PO 決定 2026-10-25 原文「1」。kgi.md） | §14-2・docs/specs/doc-agenda-nav/kgi.md K8〜K10（PO 承認済み 2026-10-22 原文「1」） |
| KGI-11 | 入口から外した決まりの行が移した先に在る割合 | 該当なし（まだ移していない） | **100%** | 段3a・3b・3c・4 のマージ前に §5-2 の表の行ごとに移動先を grep（kgi.md K11。PO 承認済み 2026-10-23 原文「1」） |
| KGI-12 | 練習問題10題×2回で必要な手順書まで開いた割合 | 1/20（baseline.md §K12） | **10/20 以上**（PO 決定 2026-10-23） | docs/handoff/doc-agenda-nav/k12-tasks.md の条件で実行し k12/count.py で数える（kgi.md K12。PO 承認済み 2026-10-23 原文「1」） |

KPI は各段（§8）の完了ごとに上表の該当行を再測定する。

## 3. 範囲／範囲外

- 範囲: リポジトリ salesanchor の AI 向け指示文書（CLAUDE.md・AGENTS.md・frontend/backend の同2種・docs/STANDARD-WORKFLOW.md・docs/ai-agents/・docs/specs/README.md・docs/adr/FEATURE-INDEX.md）、~/.claude/scripts/master-register-rules-guard.py の正規表現1行（段1）と免除の置き場1行 :23（段1b）（いずれも origin/main の同名スクリプトと一緒に）、新設する CI 1本（段2）と既存 CI .github/workflows/check-claude-size.yml の変更判定パス（段2a）、ユーザー側 ~/.claude/CLAUDE.md の重複2行 :12-13 の削除（段6）と ~/.claude・~/kb の短縮（段7。§10-8 で本テーマに追加。PO の実装承認待ち）（審査9回目 直2）。
- 範囲外: docs/handoff（便の記録・1,809件。索引化しない。理由: 作業記録であって手順書ではない）、docs/adr（README.md 自動生成で既に全件辿れる）、MEMORY.md（auto memory。別便。ただし KGI-1 の分母から外して測る理由は recon §2-1 #5: 16,298字で自動読込の 56%）、~/.claude と ~/kb のうち段6・段7 に挙げた以外（ユーザー個人設定）、フロントエンド（画面は触らない。触る場合はデザイントークンと components/ の金型に従う。本設計では該当なし）。

## 4. 構造図（前→後）

### 今（recon §2-1〜2-3）
```
会話開始
 ├ ~/.claude/CLAUDE.md 84 ─@→ ~/kb/AGENTS.md 32
 ├ ~/.claude/rules/common/{agents,git-workflow}.md 77
 ├ MEMORY.md 149
 └ CLAUDE.md 120 ──「必ず read」→ STANDARD-WORKFLOW 175 ─→ specs/README 100 ─→ 各仕様書 … 最深14段（recon 時点。数え直しで最深15段＝unreachable-list.md §1）
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
| CLAUDE.md（120行） | 前提・ブランチ運用・不可逆・VPS・標準フロー要約・i18n・UI統治・ルール追加判定木 | **入口に残す**（段3で AGENTS.md へ移し、CLAUDE.md は取り込む）: 前提・安全の決まり・目次リンク。**移す**: それ以外。**行ごとの行き先は §5-2 を正とする**（審査4回目 直4。本表は方針の要約のみ） | 公式「under 200 lines」、ADR-076 の分割方針、STANDARD-WORKFLOW:156 |
| AGENTS.md（281行） | CLAUDE.md と6節同文＋Codex 固有（役割分担・AEON・Codex UI 補助・引き継ぎ・カード定型文）。「VPS 直作業禁止」節は無い（見出し実測: `git show origin/main:AGENTS.md \| grep -n '^#'`、2026-10-22） | **全 AI 共通の入口（正本）にする**（§10-3 解決・構造は PO 承認済み 2026-10-22）。本文 = 前提・安全の決まり（不可逆操作・VPS 鍵制限・直 push 禁止。CLAUDE.md から移して1か所に）・「作業の型は目次から辿る」1行・目次リンク。Codex 固有節（役割分担・AEON・Codex UI 補助・引き継ぎ）は docs/ai-agents/codex-operations.md（新設・移動のみ）へ移し、目次の章A から辿る。カード定型文（:259-281）は削除し、逐語原本 docs/ai-agents/executor-preamble.md（design-partner.md:223 が原本と明記）を目次の章A から辿る（§5-2） | PO 2026-10-22「どのAIを使っても指示が届くように指示をＳＳＯＴしている」。Codex は AGENTS.md を根から作業場所まで連結して読み、合計 32 KiB で打ち切る（project_doc_max_bytes 既定。公式 https://learn.chatgpt.com/docs/agent-configuration/agents-md 取得 2026-10-22）。取り込み記法（@path）は同公式に記載なし＝**Codex は @ を展開しない前提で、本文は AGENTS.md 側に置く** |
| CLAUDE.md（入口化後） | — | 「@AGENTS.md」 の1行＋Claude Code だけに要る決まり（new-worktree.sh の --claude・.claude/agents 変更前の pull・個人設定への案内）のみ。行数上限の文（:117）は docs/INDEX.md 末尾章へ移す（§5-2。二重扱いを解消） | Claude Code 公式「put an 「@AGENTS.md」 import in a `CLAUDE.md` … Add any Claude-specific instructions below the import」（https://code.claude.com/docs/en/memory 取得 2026-10-22。取り込みも起動時に読み込まれ文脈量は減らない、は前回取得時の読み取りで今回の外部調査では再確認していない＝未確認。KGI-1 は保守側に倒して CLAUDE.md＋AGENTS.md の合計で数える） |
| frontend/AGENTS.md・backend/AGENTS.md | CLAUDE.md と同文 | 本文の正本を AGENTS.md 側に一本化し、同ディレクトリの CLAUDE.md は 「@AGENTS.md」＋Claude 固有のみ（ルートと同じ向き） | 同上 |
| docs/STANDARD-WORKFLOW.md（175行） | 正本 | **そのまま**（章A の末端）。§7:157「CLAUDE.md に要約＋リンク」の「要約」を「リンクのみ」に改める1行修正（SSOT） | :156 |
| docs/ai-agents/executor-checklist.md | 必読 | そのまま（章A の末端）。「いつ読むか: 便の作業前・commit前・PR前」 | :5 |
| docs/ai-agents/design-partner.md（438行） | 設計セッション必読 | 章A の末端として残す。§0.5 の必読リストは目次へのリンク1本に置換（必読の重複宣言を無くす） | :44-53 |
| docs/specs/README.md（100行） | 仕様書索引 | 章B のページとして流用。表に「いつ読むか」列を追加（KGI-6）。辿れない specs 17本（数え直し後。一覧と扱いは docs/handoff/doc-agenda-nav/unreachable-list.md §3。15本は登録・2本は移動） | STANDARD-WORKFLOW:32 |
| docs/adr/FEATURE-INDEX.md | ADR 索引 | 章C のページ。変更なし | — |
| docs/ai-agents/ の辿れない19件 | 孤立 | 19本とも lessons.d の教訓メモ。目次に lessons.d のフォルダとして1行で登録（読み方 scripts/lessons-view.sh）。§10-4 で確定（unreachable-list.md §4） | recon §2-5 |
| specs/product-master/registration-rules.md | フックで毎回注入 | 章E の末端。フックは正規表現を狭め、PreToolUse（登録操作の直前）は現状維持 | recon §2-2 |
| ~/.claude/CLAUDE.md:13「AGENTS.md も同時更新」 | 二重化を要求 | **範囲外だが矛盾**: 本文の正本が AGENTS.md 1か所になれば「同時更新」は不要になる（AGENTS.md だけ直せば Claude にも届く）。削除に確定（§10-5。段4の本番反映後に段6で実行） | recon §2-4 |

### 5-2. 入口2本の全行の行き先（審査3回目 直すべき2・3 の反映。基準 `git show origin/main:CLAUDE.md`／`git show origin/main:AGENTS.md`、2026-10-22）

入口の案文を実際に書いて数えた: docs/handoff/doc-agenda-nav/draft/AGENTS.entry.md **45行**・docs/handoff/doc-agenda-nav/draft/CLAUDE.entry.md **9行**＝**54行**（審査4回目の反映後に、§20 の判断で CLAUDE.md:51 の1行を足した）（`wc -l`、2026-10-22）。K7 の3文字列と「直push禁止」「暗号化済シークレット」は案文 AGENTS.entry.md に各1件、CLAUDE.entry.md に「@AGENTS.md」1行（grep 実測）。段3c はこの案文を写すだけにする（Generator は文面を考えない）。

**CLAUDE.md（120行）**

| 行 | 中身 | 行き先 |
|---|---|---|
| :1-5 | 表題・個人設定への案内 | 案文 CLAUDE.entry.md（表題と案内1行） |
| :7-16 | 前提 | 案文 AGENTS.entry.md「プロジェクト前提」（:10 Dev 行は AGENTS.md :10 と食い違うため codex-operations.md の役割分担へ。:15 仕様書は docs/INDEX.md 章A へ。:16 の generate-adr-index.js の手順は docs/adr/README.md の生成元の説明として INDEX 章A へ） |
| :20-24 | VPS コンテナの落とし穴 | docs/ops/runner-commands.md に節を足して移す（AGENTS.md :165-169 と同文＝1か所に） |
| :26-32 | VPS 直作業禁止 | 案文 AGENTS.entry.md（:30 の読み取りの例・変更を伴う作業の範囲・GO 転記まで入口に残す＝審査4回目 直1(b)。:29 の PO 決定日付は経緯なので入口から外す（記録は docs/handoff/claude-md-vps-key-rule/design.md:4 と git 履歴に残る）） |
| :36-40 | 不可逆操作 | 案文 AGENTS.entry.md（そのまま） |
| :46-47 | release ブランチ・new-worktree.sh | 案文 AGENTS.entry.md に1行（例外なし・~/worktrees 配下を含む）。`--claude` は Claude Code の起動だけなので案文 CLAUDE.entry.md に1行。詳細は docs/specs/branch-operations/README.md |
| :48 | .claude/agents 変更前の pull | 案文 CLAUDE.entry.md のみ（Claude 固有。§5 旧記載の「移す」からは外す） |
| :49・:52 | 直接コミット禁止・直push禁止 | 案文 AGENTS.entry.md に1行 |
| :51 | shingo-ops 名義でのコード変更 PR 作成禁止 | 案文 AGENTS.entry.md「ブランチと作業場所」に1行（機械で強制されていないため入口に残す。scripts/gh-pr-create-safe.sh:120 は素の gh pr create に効かない。§20） |
| :50・:53-55・:58 | PR の作り方・Draft・確認済みコメント・break-glass・リリース PR（:58 後半の「危険パスで停止」は check-process-artifacts.js が強制済み。§20） | docs/specs/branch-operations/README.md（現物に該当記述なし＝移動で重複は生じない、`git show origin/main:docs/specs/branch-operations/README.md \| grep` 実測） |
| :56-57 | ADR-135・ADR-136 危険 PR の GO | 要点1行を案文 AGENTS.entry.md（ADR-1003 の「例外を除き」と「委譲停止で解除」を含む＝審査4回目 直1(a)。例外7種の本文は docs/adr/ADR-1003-go-delegation-to-opus.md:31-41 が正）、手順本文は docs/specs/branch-operations/README.md |
| :60-66 | 長命ブランチ消失防止 | 要点1行を案文 AGENTS.entry.md、残りは docs/specs/branch-operations/README.md |
| :70-80 | 標準フロー要約 | 1行を案文 AGENTS.entry.md、本文は docs/STANDARD-WORKFLOW.md（正本）。:75（フルパス:行番号）・:77（PR 本文の「標準ワークフロー確認」必須）・:78（recon/design を git add）は STANDARD-WORKFLOW に現物の記述が無い＝段3b で足す（審査4回目 参考3） |
| :84-86 | 実行役 preflight | 案文 AGENTS.entry.md（AGENTS.md :97-99 と同文＝1か所に） |
| :90-92 | i18n | frontend/AGENTS.md（既に :27 に ESLint 節あり。段4で frontend/CLAUDE.md は @AGENTS.md になるので最初から1か所へ＝審査4回目 参考1） |
| :96-98 | ADR-025 | 「常時厳禁」の文を案文 AGENTS.entry.md の不可逆操作の節へ。前半（開発フェーズ中の扱い）は docs/adr/ADR-025_meta_integration_operational_hardening.md を正とし入口から消す |
| :102-103 | ADR 優先原則 | 案文 AGENTS.entry.md「プロジェクト前提」 |
| :105-117 | ルール追加の判定木・行数上限の文 | docs/INDEX.md の末尾章（:117 の上限の文はここ1か所。§5 旧記載の「Claude 固有として残す」は撤回） |
| :118-119 | UI ガバナンス（ADR-144） | frontend/AGENTS.md（Claude 固有ではない。段4で frontend/CLAUDE.md は @AGENTS.md になるため最初から1か所へ＝審査5回目 参考5。現物に ADR-144 の記述なし＝重複は生じない） |
| :120 | executor-checklist | 案文 AGENTS.entry.md「作業の型」 |

**AGENTS.md（281行）**

| 行 | 中身 | 行き先 |
|---|---|---|
| :1-3 | 表題 | 案文 AGENTS.entry.md |
| :7-10・:44-50 | 前提（CLAUDE.md と重複） | 案文 AGENTS.entry.md に1つにまとめる。:10 の Dev 行（役割の一覧）は docs/ai-agents/codex-operations.md の役割分担へ。:46 venv の決まりは docs/ai-agents/dev-commands.md、:50 KPI 正本は INDEX 章A |
| :14-38 | 役割分担・エビデンス要件 | docs/ai-agents/codex-operations.md（新設・移動のみ） |
| :40-42 | 廃止の注記（ADR-082） | 削除（ADR-082 に履歴あり） |
| :54-93 | AI Agent Pipeline・AEON | docs/ai-agents/codex-operations.md |
| :97-99 | 実行役 preflight | 案文 AGENTS.entry.md（CLAUDE.md :86 と1つに） |
| :103-126 | セットアップ & 実行コマンド | docs/ai-agents/dev-commands.md（新設・移動のみ） |
| :130-146 | ブランチ運用 | 要点は案文 AGENTS.entry.md、:133 Codex のブランチ名は codex-operations.md、:137-138 は docs/specs/branch-operations/README.md |
| :150-154 | 不可逆操作（CLAUDE.md より古い文面） | 案文 AGENTS.entry.md の新しい文面に置き換え |
| :158-161 | i18n | frontend/AGENTS.md（同じ決まりは frontend 側で1か所。frontend の CLAUDE.md/AGENTS.md の重複は段4） |
| :165-169 | VPS コンテナの落とし穴 | docs/ops/runner-commands.md（CLAUDE.md :20-24 と1つに） |
| :173-194 | Codex app UI/UX 補助 | docs/ai-agents/codex-operations.md |
| :198-203 | サブディレクトリ別ルール | 案文 AGENTS.entry.md「作業の型」1行 |
| :207-209 | ADR 一覧 | 案文 AGENTS.entry.md「設計判断」 |
| :213-218 | 自動更新ルール | 正本1か所化で不要になるため削除（~/.claude/CLAUDE.md:12-13 側は段6で削除。§10-5） |
| :222-257 | 引き継ぎルール | docs/ai-agents/codex-operations.md |
| :259-281 | 実装役の常設ルール・定型文 | **削除**。逐語原本は既に docs/ai-agents/executor-preamble.md にあり AGENTS.md 版より新しい（design-partner.md:223 が「コピペ元はこのファイルに限る」と明記）。目次の章A から executor-preamble.md を辿る（写しを増やさない＝審査4回目 直3） |

## 6. 守りの仕組み（機械強制）

| 守るもの | 仕組み | 既存との重なり |
|---|---|---|
| 入口の行数（KGI-1） | 既存 CI「CLAUDE.md line count check」の LIMITS（frontend/scripts/check-claude-size.js:22-28）を直す: §10-2 の回答値（入口の合計）を **AGENTS.md と CLAUDE.md の個別上限の和として登録**する（check-claude-size.js:46-61 はファイルごとに判定するため、和を合計値にすれば合計も機械で守られる。90 の場合 AGENTS.md 80・CLAUDE.md 10、60 の場合 AGENTS.md 50・CLAUDE.md 10。案文の実測は 45・9＝§5-2）、docs/INDEX.md を limit 60 で登録。**あわせて .github/workflows/check-claude-size.yml:23 の変更判定パス 「'**/CLAUDE.md'」 に `CLAUDE.md`（root）・`AGENTS.md`・「**/AGENTS.md」・docs/INDEX.md を足す**（今のパスは root の CLAUDE.md にも AGENTS.md にも一致せず、検査が飛ばされる＝審査4回目 直2。`git diff --name-only 283a53328^ 283a53328 -- '**/CLAUDE.md'` が空の実測あり。root CLAUDE.md が今も検査されていない既存の穴なので、段0 の ADR に記載し段1の次に単独の段2a で直す）。同スクリプトの案内文 :58「ファイル名は必ず CLAUDE.md にすること」は本設計（本文を AGENTS.md に置く）と食い違うため段3で書き換える（ADR-076 の一部改訂・段0の ADR に記載） | 既存必須チェックを流用。新規 required check 追加なし＝Branch Protection 変更なし |
| 目次から辿れる（KGI-4/5/6） | 新設 .github/workflows/doc-index-reachability.yml（名称仮）: docs/INDEX.md を起点に docs/specs・docs/ai-agents の .md を幅優先で辿り、①届かない文書 ②4段以上 ③「いつ読むか」空欄 を列挙（K5 の末端＝docs/specs/<テーマ>/README.md と docs/ai-agents/*.md。docs/specs/<テーマ>/ の README.md 以外は子文書として段数を数えない。K6 の目次＝docs/INDEX.md と docs/specs/README.md の表）。**初期は警告のみ。昇格条件は期間ではなく「警告段階の出力が連続5回の PR で 0 件」**（§14 の C21: GitLab は違反0の確認後に error 化。C22/C23: 止めない設定のまま固定化した失敗例。旧案「2週間」は根拠なしのため改めた）。リポジトリ内リンクの行き先が実在するかも同じ走査で検査（外部 URL は対象外。C20） | reachability の実装は reach.py（unreachable-list.md §1 の定義。今はリポジトリ外 ~/CC報告ファイル-keep/agenda-nav-20261022/unreach/reach.py、段2で docs/handoff/doc-agenda-nav/ に入れる）を流用（Python 3.12・標準ライブラリのみ。旧 raw/reachability.txt を出した Python は保存されておらず使わない＝§11・審査9回目 直1）。目次にフォルダとして登録された場所の直下の文書は届くとみなす（unreachable-list.md §4） |
| 同じ決まりを2か所に書かない（KGI-3） | 同 CI に「CLAUDE.md と AGENTS.md の本文が同一見出しを持たない」検査（見出し行の集合の交差 = 0）と「各 CLAUDE.md に 「@AGENTS.md」 行がある」検査を追加（root・frontend・backend） | 既存の scripts/check-doc-heading-duplicates.sh（.github/workflows/process-artifacts-gate.yml:47 で実行中）を流用できるかを段2のカード作成時に実物で確認し、流用を優先する |
| 関係ない注入ゼロ（KGI-2） | master-register-rules-guard.py:25 を re.compile(r"マスタ[^。\n]{0,40}登録|登録[^。\n]{0,20}マスタ") に変更（raw/prompt-regex-test.txt 案2: 無関係 5/5→0/5、関係あり 2/2 維持、別マスタ「顧客マスタに登録」は一致＝許容）。origin/main の scripts/agent-hooks/ と ~/.claude/scripts/ の両方（diff 同一を recon で確認済み）。PreToolUse 側（:53-84）は本便では変更なし。ただし本便で「監視語を引用した調査記録の Write」が止まった実測（raw/hook-block-event-20261022.txt）があるため、EXEMPT_PATHS に調査記録の置き場2つ（文字列 /CC報告ファイル-keep/ と /tmp/CC報告ファイル/）を足すのは段1b（§10-7 解決済み） | 既存テスト scripts/agent-hooks/test_master_register_rules_guard.sh（T1〜T8）が在る。CI からは呼ばれていない（.github/workflows/agent-hooks-test.yml:24 は review-gate のみ）→ 段1では手元実行を必須にする |
| 安全の決まりが入口から消えない（KGI-7） | 同 CI に「入口（段3までは CLAUDE.md、段3以後は AGENTS.md）に『不可逆操作は必ず PO 確認』『VPS 直作業禁止』『直接コミット禁止』の3文字列が各1件以上ある」検査（3文字列は受け入れ基準 K7 と同一。実物は origin/main CLAUDE.md:36・:26・:49）。CI の守りとしては『直push禁止』（CLAUDE.md:52）と『暗号化済シークレット』（ADR-025 常時厳禁・:98）も同じ検査に足す（K7 の合格ラインは変えない） | — |
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

日常語の全体図と順番は §20。

| 段 | 変更 | 測定（KGI） | 戻し方 |
|---|---|---|---|
| 0 | 親仕様書と specs/README.md への1行登録は **済み**（f6d8a0be6・#4638）。残り: 新規 ADR を Proposed で起案し `node scripts/generate-adr-index.js` で docs/adr/README.md を再生成。ADR には ADR-076 との衝突点を列挙する: ①ADR-076:55「上限が小さすぎると具体例が削除され判断精度が低下」を理由に上限を据え置いた点（本設計は上限を §10-2 で決め直す）②check-claude-size.js:58「ファイル名は必ず CLAUDE.md」（本設計は本文を AGENTS.md に置く）③check-claude-size.yml:23 の変更判定パスが root の CLAUDE.md に一致せず、root CLAUDE.md が今も行数検査されていない既存の穴（段2a で直す）。ADR-076 本体（docs/adr/ADR-076-claude-md-hierarchy.md。ADR-076 は2本あるのでファイル名で指定）には「一部改訂: 新 ADR」の1行だけ足す。上限の数値は §10-2 の PO 回答どおり 90行（AGENTS.md 80・CLAUDE.md 10）と ADR に書く（審査9回目 参考1） | — | PR revert |
| 0b | **K8・K9 の変更前の値を測る（段1より前。審査3回目 直すべき8・審査4回目 直5）**。K8 の**集団**: head が release/ で始まり main へマージされた PR を、マージ時刻の新しい順に10件（変更後は段3c マージ後の最初の10件。同じ条件）。変更前の基準時点（測った時刻と最後の PR 番号）を baseline.md に書き、本テーマ自身の PR（head が release/doc-agenda-nav で始まるもの）は前後とも集団から除く（審査5回目 参考8）。K8 の**項目の選び方**: ①案文 AGENTS.entry.md の決まりを1行ずつ並べる ②各決まりが機械で強制されているかを、次の4か所すべてで確かめ表にする: CI（.github/workflows/）／GitHub の Ruleset・Branch Protection（`gh api repos/shingo-ops/salesanchor/rules/branches/main` を読むだけ（rulesets の一覧はルールの中身を返さない。main に Branch Protection は無く 404＝審査6回目 参考1）。PR 経由必須・merge commit のみ・ブランチ削除禁止が強制済み＝recon2/c10-rules.txt）／フック（~/.claude/settings.json と リポジトリの .claude/settings.json の hooks）／git フック（frontend/.husky/）。したがって「直接コミット禁止」「直push禁止」「main/develop を消さない」は強制済みで効果の項目にしない（審査5回目 直1） ③強制されていない・かつ gh や git で数えられるものだけを効果の項目にする（例の「PR 本文の標準ワークフロー確認欄」は process-artifacts gate が強制しているので効果の項目にしない。強制済みの項目は別枠で記録だけする）④効果の項目が0件なら「K8 は入口の効果測定に使えない」と baseline.md に書き PO へ戻す。各項目の判定コマンドと結果を記録。K9: 新しい会話の直後に /context の表示値を記録。記録先 docs/handoff/doc-agenda-nav/baseline.md（手順も保存）。項目は kgi.md K8 の「等」の範囲内で選ぶ（合格ラインは基準値の後に PO と決める＝承認済みの手順どおり） | K8/K9 基準値 | 記録の削除 |
| 0c | **K10・K12 の変更前の値を測る（2026-10-23 追加。PO 原文「1」）**。練習問題10題（docs/handoff/doc-agenda-nav/k12-tasks.md。測定前に固定）を origin/main の detached な写しで各2回 AI に計画だけ答えさせ、docs/handoff/doc-agenda-nav/k12/count.py で数える。結果 K12 1/20・K10 0/20（baseline.md §K12）。K11 は移す段（3a・3b・3c・4）のマージ前に測るので基準値は「該当なし」 | K10/K12 基準値 | 記録の削除 |
| 1 | master-register-rules-guard.py:25 の正規表現（scripts/ の変更なので check-process-artifacts.js の危険パスに当たり、PR 本文に `### GO記録` が要る。ADR-1003 の委譲範囲で Opus が出せる。カードに書く）。**変更前**（実物）: `(マスタ|商品).*登録|登録.*(マスタ|商品)`（re.S）／**変更後**: §6 の KGI-2 行。repo 側 scripts/agent-hooks/ を PR で審査 → ~/.claude/scripts/ へは前例 docs/handoff/master-register-rules-hook/design.md:37 の型（PO が `!` で写す→写す前に .bak を作る→repo 版と diff 一致を確認）。例文は raw/prompt-regex-test.txt の7本（無関係4本＋境界1本＋関係あり2本）をカードに全文で写す。新しい式は「マスタ」を含まない「商品を登録して」を拾わなくなる → この例文を試験に足し「拾わない」を期待値とし、PreToolUse 側（登録操作の直前に止める）が残ることを前提として明記する。既存テスト T1〜T8 を手元で実行 | KGI-2 | 1行を戻す（.bak から戻す） |
| 1b | master-register-rules-guard.py:23 の EXEMPT_PATHS に `/CC報告ファイル-keep/` と `/tmp/CC報告ファイル/` の2つの文字列を足す（:66 の判定は file_path（絶対パス）への部分一致で `~` は展開されないため、`~/` 付きで書くと効かない＝審査8回目 直6）（§10-7。段1とは別 PR。触る行も測るものも別）。写し方は段1と同じ型（repo の scripts/agent-hooks/ を PR で審査→PO が `!` で ~/.claude/scripts/ へ写す。.bak を作る）。scripts/ の変更なので PR 本文に `### GO記録` が要る。PO の実装承認が別に要る | 試験2本を scripts/agent-hooks/test_master_register_rules_guard.sh に足し手元実行: ①免除パスへ監視語入りの Write が通る（試験の file_path は絶対パスで書く。例 /Users/tanizawashingo/CC報告ファイル-keep/x.md と /tmp/CC報告ファイル/x.md）②Bash の登録コマンドは止まる（Bash は fpath が空で免除判定 :66 を通らない＝:60-61）。段1の T1〜T8 も通ること。段1と同じ試験ファイルに足すので、後に出す方は先の PR のマージ後に作る（審査8回目 参考2） | :23 の1行を .bak から戻す（写しはファイルごとなので、戻した後に repo 版との diff で確かめる＝審査8回目 参考3） |
| 2a | check-claude-size.yml:23 の変更判定パスに root の `CLAUDE.md`・`AGENTS.md`・「**/AGENTS.md」・docs/INDEX.md を足す（1行。CI 設定の変更なので PO の実装承認が要る。不可逆操作リストの workflow-lint.yml には当たらない） | マージ前: 過去コミット 283a53328・93ca3e8e8 で新しいパス指定の `git diff --name-only` を手元実行し、root CLAUDE.md・AGENTS.md が出ること。マージ後: 次に CLAUDE.md を変える PR で「Check CLAUDE.md sizes」が skip でなく実行されること（試しの PR は作らない。変更後の :23 の1行はカードに全文で書く） | PR revert |
| 2 | docs/INDEX.md 新設（章A〜F・「いつ読むか」列）＋ specs/README.md に「いつ読むか」列＋ docs/handoff/doc-agenda-nav/unreachable-list.md の決定どおり、specs 15本を各表紙に1行で登録・2本を docs/handoff/fix-unify-type-mismatch/ へ移動・lessons.d をフォルダ1行で登録（K4 基準値は specs 17・ai-agents 19。§10-4） | KGI-4/5/6（警告段階の CI で観測） | ファイル削除 |
| 3a | §5-2 の表で docs/ai-agents/codex-operations.md・docs/ai-agents/dev-commands.md へ行く行すべてを移すだけ（Codex 固有節に加え、CLAUDE.md:10・AGENTS.md:10 の Dev 行、AGENTS.md:133 の Codex のブランチ名、AGENTS.md :46 の venv、:103-126 のセットアップ & 実行コマンドを含む。審査6回目 直1）（新設2本・移動のみ。AGENTS.md には目次への1行を残す。審査5回目 直2）。§10-3 の構造承認後 | KGI-3 途中値 | PR revert |
| 3b | CLAUDE.md・AGENTS.md の「移す」行（**§5-2 の表が正**）を既存の移動先へ移す（1PR1移動先。移動先は §5-2 の表のうち段3a の2本以外: docs/specs/branch-operations/README.md・docs/STANDARD-WORKFLOW.md・frontend/AGENTS.md・docs/ops/runner-commands.md、および段2で新設済みの docs/INDEX.md） | KGI-1 途中値 | PR revert |
| 3c | 入口の入れ替え（**文面は §5-2 の案文 draft/AGENTS.entry.md・draft/CLAUDE.entry.md をそのまま写す**。写す前に、§5-2 の表で入口以外へ行く行が移動先に在ることを行ごとに grep で確かめ、1行でも無ければ止める＝審査6回目 参考3）: 安全の決まり・前提を CLAUDE.md から AGENTS.md へ移し、CLAUDE.md を 「@AGENTS.md」＋Claude 固有のみにする ＋ LIMITS（§6）＋ STANDARD-WORKFLOW §7:157-159（入口を「ターミナル＝CLAUDE.md」と定めている箇所）を「AGENTS.md が正本・CLAUDE.md が取り込む」に書き換え | KGI-1/3/7（ルート分）。/memory 表示で AGENTS.md の本文が会話に入ったことを確認 | PR revert（2ファイル＋STANDARD-WORKFLOW） |
| 4 | frontend/backend の同2種を同じ向き（AGENTS.md が正本、CLAUDE.md は 「@AGENTS.md」＋固有のみ）に揃える | KGI-3（全体） | PR revert |
| 5 | **§26 で3つに分けた（2026-10-25）**。5a: 手元の記録（commit）でも行数の上限超えで止める＋AGENTS.md の未登録も見つける。5b: 古さの見張り（claude-md-staleness-check.yml）に AGENTS.md を足す。5c: doc-index-reachability CI を警告→失敗へ昇格（条件: 連続5回の PR で 0 件。起点では broken_link=8・warnings=10・deep=2 で条件を満たさないので保留）。必須チェック（ruleset）への登録は Branch Protection／Ruleset の変更＝CLAUDE.md の不可逆操作リスト該当のため PO 確認を別にとる | 5a・5b は §26 の表。5c は KGI-4/5/6 が0であること | 5a・5b は PR revert。5c は警告に戻す |
| 6 | ~/.claude/CLAUDE.md:12-13（「AGENTS.md も同時に更新」の節）を削除（§10-5 確定。段4の本番反映後。変更前の写しを ~/CC報告ファイル-keep/ に保存してから消す）（ユーザー側。PO の実装承認が要る） | KGI-3 再測 | 写しから2行を貼り戻す |
| 7 | **ユーザー側の常時読込を短くする（§10-8 解決で追加）**。対象と実測（recon2/autoload-user.txt、2026-10-22）: ~/.claude/CLAUDE.md 84・~/kb/AGENTS.md 32・~/.claude/rules/common/agents.md 53・git-workflow.md 24 ＝ 193行（paths 付きの rules 10本は条件付き読込で対象外）。方法: 節ごとの行き先案（残す／paths 付き rules へ移す／リポジトリ側の正本へのリンクに置換）を一覧で PO に提示し、承認された分だけ変える。~/kb 側の記録（commit）は ~/kb/AGENTS.md:29 により PO が `!` で実行。上限の数値はプロジェクト側入口の行数（§10-2）と合わせて K1 ≤ 200 に収まるよう段7の開始時に一覧で示す | KGI-1（全体）・K8/K9（§14、PO 承認済み） | 各ファイルを変更前の写し（リポジトリ外 ~/CC報告ファイル-keep/ に保存）から戻す |

## 9. 外部・過去事例と我々への応用

| 出典 | 内容（測定値・日付） | 応用 | 限界 |
|---|---|---|---|
| Claude Code 公式 memory（https://code.claude.com/docs/en/memory 取得 2026-10-22） | 「target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence」／サブディレクトリ CLAUDE.md と paths rules は on demand／import は文脈を減らさない | 入口を短く、領域別は on demand に任せる（章D）。import で目次を取り込まない | 「遵守率低下」の数値は公式には無い |
| Claude Code 公式 skills（同 /skills） | 「a skill's body loads only when it's used」「Keep SKILL.md under 500 lines」 | 章E（商品マスタ登録）は将来スキル化の候補（description だけ常駐、本文は呼び出し時）。本設計では採らない。別便で検討する（§10-6 の着手条件3つ） | リポジトリに .claude/skills 無し（新機構導入は architect 判断が要る） |
| Anthropic「Effective context engineering for AI agents」（https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents 2025-09-29） | 「find the smallest set of high-signal tokens」「progressive disclosure」「just in time context」 | 本設計の原理そのもの（入口最小・必要時に辿る） | 定量の効果値は記事に無い |
| 自リポジトリ ADR-076（2026-05-28） | 外部エビデンス表「471行→61行（87%削減）で一貫性改善」「OpenAI AGENTS.md は150行以下目標」 | 上限引き下げの前例**ではない**（ADR-076:24 はルート上限 120→120 据え置き。審査3回目 参考5） | **未確認**: 表の出典 URL・日付が ADR に無い |
| 自リポジトリ PR #3358（2026-09-08） | design-partner.md の guards を節ごとに分割し目次化 | 同じ発想の先行例。効果測定の記録は PR に無い（**未確認**） | — |
| 自リポジトリ 本便 recon（2026-10-22） | 自動読込 462行/29,290字、無関係注入 5/5、辿れない文書 1,880 | KGI の「今」の値 | — |

## 10. PO に聞くこと（業務判断。番号で答えられる形）

1. **解決済み（PO 2026-10-22「土台の文書を作成して設計や仕様書まで作成をさせる」）**: 親仕様書（docs/specs/doc-agenda-nav/ の3ファイル）を**段0で先に作る**か、本 design.md を仕様書代わりにして段1から始めるか。
   - 1. 段0で作る【おすすめ】→ STANDARD-WORKFLOW §1.5/§1.8 どおり。PR が1本増える
   - 2. 段1から始める → 早いが、索引に親が無いまま進む（§1.8 違反）
2. **解決済み（PO 2026-10-22 原文「1」→ 90行。個別上限 AGENTS.md 80・CLAUDE.md 10）**: 入口（段3以後は AGENTS.md と CLAUDE.md の合計）の上限を 90 行にしてよいか（今 CLAUDE.md 120）。
   - 1. 90行【おすすめ】→ 入口の案文を実際に書いて数えると 53行（AGENTS.md 44・CLAUDE.md 9、§5-2）（PO に示した時点の値。その後 §20 の判断で1行足し、今は 54行＝45・9）。個別上限は AGENTS.md 80・CLAUDE.md 10。残す範囲の元の行は §5-2 の表のとおり。K1 ≤ 200 にはユーザー側 193行を段7で 110行以下にする必要がある（§10-8）。外部根拠は §14-4（90行を直接示す一次資料は無く、K1 の予算配分として決める）
   - 2. 120行のまま → 行数は減らず、重複削減だけになる
   - 3. 60行 → 案文 53行は収まる（AGENTS.md 50・CLAUDE.md 10）が、AGENTS.md の余地は6行
3. **解決済み（PO 2026-10-22・原文「2,どのAIを使っても指示が届くように指示をＳＳＯＴしている」、構造は同日 PO 原文「1」で承認）**: Codex は今も AGENTS.md を読んで動いているか。
   - 1. 動いていない → 段4で AGENTS.md を薄い入口にする
   - 2. 動いている → Codex 固有節を残す形に変える（本文は移動、リンクで辿る）← **PO 回答**
   - 反映（構造は PO 承認済み 2026-10-22）: 本文の正本を AGENTS.md（全 AI 共通の入口）に置き、CLAUDE.md は 「@AGENTS.md」 で取り込む向きに変更（§4・§5・§6・§7・§8 段3/4）。旧案「AGENTS.md を 「@CLAUDE.md」 だけにする」は、Codex の公式説明に取り込み記法の記載が無く Codex に本文が届かないため不採用。
   - 審査（2026-10-22 2回目）の指摘: 選択肢2の文面は「Codex 固有節を AGENTS.md に残し本文は移動」で、採用した構造（本文を AGENTS.md に置き Codex 固有節を移す）と向きが逆。PO の補足（SSOT）からの解釈であり、構造そのものの承認記録は無い → 構造を PO に確認した。Opus が「本文は『どのAIも最初に読む共通の入口』1か所に置き、Claude の入口はそれを読み込む1行と Claude 専用の決まりだけにする」を選択肢1として示したのに対し、**PO 原文「1」（2026-10-22）で承認**。
4. **回答済み（PO 2026-10-22 原文「1、推測は禁止して事実確認を怠らずに…」→ 一覧を出してから1本ずつ決める。各文書の事実（最終更新・参照元・状態の語）を集めた一覧を PO に提示し、登録か移動かを1本ずつ確定する。確定まで段2は始めない。一覧と推奨は docs/handoff/doc-agenda-nav/unreachable-list.md。数え直しで K4 の基準値は specs 17・ai-agents 19・最深15段に訂正（元の specs 35 は再現できない。同ファイル §1）**: docs/ai-agents の辿れない19件と specs の35件を「目次に登録」か「handoff へ移動（記録扱い）」か、1件ずつ表を出して確認してよいか（段2の前に一覧を提示）。
   - 1. 一覧を出してから決める【おすすめ】
   - 2. 全部登録する
5. **解決済み（PO 2026-10-22 原文「fableにまかせてくれ」→ Fable の判断。全文 ~/CC報告ファイル-keep/agenda-nav-20261022/fable/decisions.md（リポジトリ外）。Opus が根拠の file:line を実物で照合済み） → 削除する。実行は段4の本番反映後（frontend/backend の AGENTS.md が正本になる前に消すと、その間だけ同時更新の穴が再発するため）。書き換えて残す案は採らない（正本は案文 AGENTS.entry.md:3 が伝え、重複は段2の CI が検査する）**: ~/.claude/CLAUDE.md:13「AGENTS.md も同時に更新」を段6で消してよいか（3 の答えに依存）。
6. **解決済み（PO 2026-10-22 原文「fableにまかせてくれ」→ Fable の判断。全文 ~/CC報告ファイル-keep/agenda-nav-20261022/fable/decisions.md（リポジトリ外）。Opus が根拠の file:line を実物で照合済み） → 選択肢1（別便で検討）。着手条件: ①段1が本番反映され K2 が測れた後 ②PreToolUse 側は残し、置き換えるのは UserPromptSubmit 側だけ ③.claude/skills は新しい仕組みなので architect の判断を通す**: 章E（商品マスタ登録）を将来スキル化する検討を別便で起こすか（本便では正規表現修正のみ）。
   - 1. 別便で検討【おすすめ】
   - 2. 検討しない
7. **解決済み（PO 2026-10-22 原文「fableにまかせてくれ」→ Fable の判断。全文 ~/CC報告ファイル-keep/agenda-nav-20261022/fable/decisions.md（リポジトリ外）。Opus が根拠の file:line を実物で照合済み） → 選択肢1。足すのは ~/CC報告ファイル-keep/ と /tmp/CC報告ファイル/ の2つ（置き場所の名前としての書き方。足す文字列の正は §8 段1b＝`~` は判定で展開されないため /CC報告ファイル-keep/ と書く＝審査9回目 参考3。Fable の判断文書の書き込み自体が同じフックに止められた＝2件目の実例）。段1とは分けて段1b（§8）**: 登録ルールのフック（PreToolUse 側）が、監視語を「説明として引用」した文書の書き込みでも止まる件（本便で実測）。
   - 1. 免除パスに ~/CC報告ファイル-keep/ を足す【おすすめ】→ 調査記録は止まらなくなる。登録操作そのものは引き続き止まる
   - 2. 今のまま → 規則を説明する文書を書くたびに ack 行が要る
8. **解決済み（PO 2026-10-22・原文「1,fableに相談、外部での導入事例と成功事例と成功要因、失敗事例と失敗要因を徹底的に調査してエビデンスを取得してくれ…」）→ 選択肢1（ユーザー側を短くする段を本テーマに足す。200行は保つ）。外部事例の調査と Fable への相談・レビュアー審査・定着の仕組みの検証を追加で指示された（§14・§15・維持の仕組みに反映済み）。** （引き継ぎ後に Opus が発見・2026-10-22）K1 の 200行は、本便の範囲（プロジェクト側）だけでは届かない。** 実測（2026-10-22 `wc -l`）: ユーザー側 ~/.claude/CLAUDE.md 84・~/kb/AGENTS.md 32・常時読込の rules（agents.md 53＋git-workflow.md 24）77 ＝ **193行**、プロジェクト側 CLAUDE.md 120行、計313行。ユーザー側が今のままだと、プロジェクト側の入口を7行以下にしないと200行に入らない。前セッションの設計で、K1 の分子にユーザー側を含めながら範囲外にしていた（入れ忘れ）。
   - 1. 個人用の決まり（ユーザー側）を短くする便を、本テーマの段として足す（200行は保つ）
   - 2. K1 をプロジェクト側の入口だけで数える形に改め、合格ラインを付け直す（KGI の再承認が要る）
   - 3. 200行をやめ、プロジェクト側を減らした結果の行数を合格にする

## 11. 未確認・開いている論点

- **解決済み（PO 2026-10-22 原文「fableにまかせてくれ」→ Fable の判断。全文 ~/CC報告ファイル-keep/agenda-nav-20261022/fable/decisions.md（リポジトリ外）。Opus が根拠の file:line を実物で照合済み） → :51 は入口に残す（機械強制なし）。:58 後半と :66 は機械強制済み（check-process-artifacts.js・executor-preflight.sh:69-75）なので §5-2 どおり移す**: 入口から branch-operations へ移す安全寄りの文（CLAUDE.md:51 shingo-ops 名義でのコード変更 PR 作成禁止・:58 後半 危険パスが含まれたら停止して PO 確認・:66 main/develop 欠落時は止めて PO に報告）を入口に残すか。K7 の範囲外で §5-2 に行き先はある。§10-2 の回答と合わせて PO に確かめる（審査5回目 参考7）
- @AGENTS.md で取り込んだ本文が圧縮（compaction）後も再注入されるか（§7 の「公式 :627」は root CLAUDE.md の記述。§7 の :435・:627 は https://code.claude.com/docs/en/memory を取得したときの行番号）。段3c の測定で圧縮後の /memory 表示を確認する（審査3回目 参考4）
- 過去会話記録に同じ構想の議論があるか（recon §1。Grep ツールのあるセッションで再実行）
- （2026-10-22 一部解消: 定義を recon §2-5 どおりに固定して数え直し、specs 17・ai-agents 19・最深15段。スクリプトは ~/CC報告ファイル-keep/agenda-nav-20261022/unreach/reach.py。段2で docs/handoff/doc-agenda-nav/ に入れて CI に使う）K4/K5 の基準値（raw/reachability.txt）を出した Python が design/・recon2/ に保存されていない（審査 2026-10-22）。旧基準値（specs 35・最深14段）は再現しない（unreachable-list.md §1）ため、段2の CI は reach.py の定義を正とし、新しい基準値（specs 17・ai-agents 19・最深15段）を段2の CI で再現できることを確かめてから使う（審査8回目 直5）
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

- 【事実】（審査3回目で訂正）短くして確実に減るのは「会話の始まりに自動で読む行数・トークン」（作り方から確実。K1・K9 で測る）。「費用が減る」は外部の根拠が弱い: S3（Gloaguen）は長さと費用に明確な関係なし、S4（Lulla）は有無の比較で行数ではない、S1 は1人の自己申告。「守られる率・精度」が上がる数値は無く、むしろ差が出ないという研究（C2・C5）がある。
- したがって本設計の効果は **「軽く・速く・安く・同じ決まりが1か所」** として約束し、**「精度が上がる」は自分たちで測るまで約束しない**。PO のあるべき姿（「精度も向上する」）を確かめるには、KGI に次を足した（**PO 承認済み 2026-10-22 原文「1」**。合格ラインは基準値を測った後に PO と決める。正本は docs/specs/doc-agenda-nav/kgi.md）:
  - K8 守られた回数: 集団と項目の選び方は §8 段0b（CI・フックで強制済みの決まりは効果の項目にしない）→ 段0b の実測で効果を示せないと分かり、**物差しにしない（PO 決定 2026-10-23 原文「1」）**。比較は K9・K10・K12 で行う
  - K9 会話開始直後の読込量（トークン）: /context の表示値を前後で記録
  - K10 目次を開いた割合: ~~手順を要する便で docs/INDEX.md を Read した割合（フックで記録）~~ → 2026-10-23 に K12 の練習問題と同じ実行で数える方式へ変更（過去の会話記録は見張りで Bash から読めず、開くべきページも決まっていないため。baseline.md §K10・§K12）。フックの新設は不要になった
  - K11・K12（**PO 承認済み 2026-10-23 原文「1」**。PO 原文「どこまで減ったかも重要だが漏れなくキャッチアップしているかも重要」）: K11 は入口から外した決まりが移した先に在る割合（合格 100%）、K12 は練習問題で必要な手順書まで開いた割合（基準値 1/20）。K11 は「移して消えていない」、K12 は「AI が必要な所まで辿れている」を確かめる。K12 は測り方の性質上、実際の作業そのものではなく固定した練習問題での値
- 【事実】昇格条件「2週間」は根拠なし → 「連続5回 0 件」に改めた（§6・§8 段5）。**「5回」の数値に外部の出典は無い**（C21 は「違反0を確かめてから失敗化した」という順序の根拠で、Opus 未照合）。回数は Opus の決めで、段5の前に見直せる。
- 【事実】登録ルールのフックには既存テスト scripts/agent-hooks/test_master_register_rules_guard.sh があるが、CI から呼ばれていない（recon2/item9.txt、agent-hooks-test.yml:24 は review-gate のみ）→ 段1のカードで手元実行を必須にし、CI への配線は CI 変更として PO 承認を別にとる。

### 14-3. 開発ルールの確認（recon2/dev-rules.txt・design-check-run.txt）

- 本 design.md は scripts/check-process-artifacts.js の validateDesignDoc・validateMaintenanceSection で エラー0（Sonnet が読み取り専用で実行。作業場所は origin/main より13コミット遅れの時点）。PR 前に origin/main へ追従して再実行する。
- ADR-113 の手順（recon→設計確定→Architect 整合検査1回→実装→CI）に従う。カード検査は scripts/card-lint.sh（カード作成時に実行）。
- 行数の記載: origin/main では CLAUDE.md:117「120 行を超えたら」と check-claude-size.js:23 の上限 120 が一致（382d3bff5 で解消済み。§13 と同じ）。手元の古い checkout だけが「90 行」のまま。段3で上限を変えるときは本文と LIMITS を同じ PR で直す。

### 14-4. 入口の上限（§10-2）の外部根拠（2026-10-22 PO 指示「外部での導入事例…5w2h化」・Sonnet 調査、Opus が全文読了。審査3回目の指摘で訂正済み）

保存先: ~/CC報告ファイル-keep/agenda-nav-20261022/research/linelimit/agenda-nav-linelimit-20261022.md（数値あり8件・数値なし4件・未確認4件・公式4件・公開19リポジトリ実測）。

- 【事実】行数を変えて守られる率を比べた管理実験は1件（McMillan arXiv 2605.10039、1,650 セッション）。25行 60.0%／100行 65.2%／250行 67.7%／500行 64.0% で**差は検出されず**。ファイル無しは 0/524。同じ会話で作業が1つ進むごとに守られるオッズが約5.6%下がる（行数と無関係）。
- 【事実】長さと課題解決率・費用に明確な関係は見られない（Gloaguen arXiv 2602.11988）。常時読込と必要時読込で正答率は同じ。必要時読込では cache-creation トークンが 11/11 課題で減る（Khatri arXiv 2607.27250。比べたのは読み方で、行数ではない）。
- 【事実】守られる率が下がるのは「指示の本数」が増えたとき（IFScale arXiv 2507.11538: claude-sonnet-4 で100本 94.4%→250本 77.2%→500本 42.9%。ManyIFEval: 10本を同時に全部守る率 0.19〜0.48、旧世代モデル）。行と本数の換算は論文に無い。
- 【事実】公式の数値: Anthropic「1ファイル200行未満を目標」（低下量の数値の記載なし）、Codex 合計32KiB、Cursor 1ルール500行未満。Copilot の「2ページ以内」は公式文書内のサンプルプロンプトの文で、推奨値ではない。**60／90／120行を直接示す一次資料は見つからなかった**。
- 【事実】公開19リポジトリ（非無作為）の最長ファイルの中央値162行。60行以下6、61〜90行1、91〜120行0、121〜200行6、201行超6。
- **結論**: 上限の数字そのものが守られる率を決めるという根拠は無い。確実に言えるのは ①会話の始まりに自動で読む行数・トークンは短いほど減る（作り方から確実。K1・K9 で測る）②指示の本数が増えると守られにくい（S7・S8）③Anthropic の目安は1ファイル200行未満。「費用が減る」は外部の根拠が弱い（S3 は長さと費用の関係なし）。したがって §10-2 の上限は「守られる率を上げる数字」ではなく、**K1（会話の始まりの合計200行以下・PO 承認済み）を満たすための予算**として決める。90行の根拠は「入口案文の実測 54行（§5-2。審査時点は 53行、§20 の判断で1行足した）＋増える余地」と「K1 の予算配分（ユーザー側110行＋入口90行＝200行）」の2つだけで、外部の数値ではない。守られる率は K8 で測る予定だったが物差しにしないことになった（PO 決定 2026-10-23）。必要な手順書まで辿れているかを K10・K12 の練習問題で前後に測って確かめる。

## 維持の仕組み

- 守り手: （既存・必須チェック。ruleset 実測 recon2/c10-rules.txt）.github/workflows/check-claude-size.yml（job「CLAUDE.md line count check」）、process-artifacts-gate.yml（「process-artifacts gate」）、adr-index-check.yml（「ADR index is up to date」）
- 追加予定の守り手（段2で新設、まだ存在しない）: doc-index-reachability.yml（名称仮。目次到達・段数・「いつ読むか」空欄・リポジトリ内リンクの行き先実在・CLAUDE.md↔AGENTS.md 見出し重複・各 CLAUDE.md の 「@AGENTS.md」 行・安全見出しの存在を検査。段2で警告、連続5回0件で段5に失敗化し、必須チェック登録は PO 確認）
- 担当と数え方: 担当は本テーマの台帳（.claude-pipeline/active-work.d/ の本テーマの1枚）を持つ Opus セッション。昇格の判定は `gh run list --workflow doc-index-reachability.yml --event pull_request --limit 5` の5件すべてで警告0件であることを、各段の完了時に台帳へ記録して数える（警告件数は job の要約に1行で出す作りにする・段2のカードに書く）
- リポジトリ外（CI が見えない）の守り手（段7で新設案・PO の実装承認待ち）: ~/kb/scripts/patrol.sh（毎週月曜 09:00 に Discord 通知。今の点検4項目は recon2 c11）に「会話開始時に自動で読まれるユーザー側ファイルの合計行数」を1項目足す
- 対象: 入口が再び太ること／目次から辿れない手順書が増えること／同じ決まりが2か所に戻ること／安全の決まりが入口から消えること／ユーザー側の常時読込が再び増えること
- 今ない仕組み（事実）: 指示文書の行数・リンク・索引を点検する定期 job は無い（STANDARD-WORKFLOW.md:167「governance が定期的に点検」に対応する定期 workflow は見つからず。governance 検証 2026-10-22）。近いものとして .github/workflows/claude-md-staleness-check.yml（四半期ごと・CLAUDE.md の最終更新が90日超なら Issue 化 :45-56）があるが、見るのは更新日だけ。上の2つで埋める
- 関所なしの部分: 「AI が目次を実際に辿ったか」→ CI では見えない（Read の有無は CI に残らない）。担当の Opus が段3c・段4 の後に K10・K12 を baseline.md の手順で測り直す（練習問題20回）。実際の作業の常時記録は持たない

## 15. 審査2回目（2026-10-22・PR #4649 HEAD 5c5758bee）と反映

- 審査役（model opus・新規起動）: **REVISE**（止めるべき0・直すべき9・任意3）。全文 /tmp/CC報告ファイル/agenda-nav-review-20261022.md（リポジトリ外）。
- 定着の検証（governance）: **MONITOR**（BLOCK 条件なし）。全文 /tmp/CC報告ファイル/agenda-nav-governance-20261022.md（リポジトリ外）。
- 反映したもの: K1 の数え方（段3以後は AGENTS.md を足す）／K7 の3文字列を受け入れ基準・§6 で統一し、:49 を入口に残す行として明記／§5 の行番号を origin/main の実測に修正／§6 の LIMITS に AGENTS.md を登録・:58 の案内文を書き換える計画／テストの有無の食い違い（在る・CI 未配線）／§13・§14-3 の古い記述／段0（済み分と ADR の衝突点）／段1（変更前・写し方・例文・取りこぼし前提）／段3 を 3a〜3c に分割／基準値 Python の未保存を §11 に／守り手の担当と「連続5回」の数え方／claude-md-staleness-check.yml の切り分け／見出し重複検査の流用候補／「5回」に外部出典が無いこと。
- PO 確認: ①§10-3 の構造は **PO 原文「1」（2026-10-22）で承認済み**（§10-3）。②（**PO 原文「1」2026-10-22 で承認・kgi.md に反映済み**）K5 の「末端」の数え方と K7 の判定対象（kgi.md:18 は「CLAUDE.md」）の修正、K8〜K10 の追加（KGI 表の修正＝再承認）。
- 段1は上の反映でカード化できる状態。段0は ADR の向き（新規＋ADR-076 一部改訂）を決めたのでカード化できる。段3・段4は ① の承認により、§10-2 の回答後にカード化できる。

## 16. 審査3回目（2026-10-22・PR #4649 HEAD 3f981c51d）と反映

- 審査役（model opus・新規起動）: **REVISE**（止めるべき0・直すべき8・参考6）。全文 /tmp/CC報告ファイル/agenda-nav-review3-20261022.md（リポジトリ外）。段0・段1はこのままでもカード化できるとの判定。
- 反映（直すべき）: ①§14-4 の「約60行」を案文の実測52行（当時。審査4回目の反映後は53行）へ（§5-2）②CLAUDE.md・AGENTS.md の全行の行き先を §5-2 に表で記載・入口の案文2本を draft/ に作成 ③:48 は CLAUDE.entry のみ、:117 は docs/INDEX.md のみに一本化 ④入口の合計を個別上限の和で機械的に守る（§6）⑤「費用が減る」を「会話の始まりに読む行数・トークンは確実に減る／費用は根拠が弱い」に分離（§14-2・§14-4）⑥PR 本文の触るファイルに docs/specs/README.md と draft 2本を追加 ⑦docs/specs/doc-agenda-nav/README.md:24 の「PO 未承認」を訂正 ⑧段0b（K8・K9 の基準値測定、記録先 baseline.md）を §8 に追加。
- 反映（参考）: ManyIFEval の値域・Copilot「2ページ」はサンプル文・Anthropic は「数値の記載なし」（§14-4）／K7 の守りに「直push禁止」「暗号化済シークレット」を追加（§6）／K5・K6 の CI 定義（§6）／@ で取り込んだ本文の圧縮後の再注入を §11 に未確認として追加／§9 の ADR-076 は前例ではないと訂正。UI governance gate の失敗はブランチの遅れによるもので本 PR と無関係（審査役の判定）。

## 17. 審査4回目（2026-10-22・PR #4649 HEAD 4e7ef9f63）と反映

- 審査役（model opus・新規起動）: **REVISE**（止めるべき0・直すべき5・参考11）。全文 /tmp/CC報告ファイル/agenda-nav-review4-20261022.md（リポジトリ外）。§14-4 の数値は外部調査本体と全件一致。手元の process-artifacts gate は PASSED。
- 反映（直すべき）: ①案文の安全の決まりを現行と同じ強さに戻した（GO 委任の「例外を除き」「委譲停止で解除」、VPS の読み取りの例と変更を伴う作業の範囲）②行数検査の CI が root CLAUDE.md・AGENTS.md の変更で動かない穴を段2a として追加（§6・§8）③カード定型文は既存の逐語原本 executor-preamble.md を正とし、AGENTS.md 側は削除（写しを増やさない）④§5 の旧表は方針の要約に縮め、行ごとの行き先は §5-2 を正、段3b の参照先も §5-2 に ⑤段0b に K8 の集団と項目の選び方（強制済みの決まりは効果に数えない）を定義。
- 反映（参考）: i18n の行き先を frontend/AGENTS.md 1か所に／AGENTS.md :10 の行き先／STANDARD-WORKFLOW に無い3行は段3b で足す／`--claude` を CLAUDE.entry へ／KGI-7 の行番号／守り手の書式／@ 取り込みの文脈量を未確認に／README の件数と PR 本文の規模・変更点。参考4（:29・:30 の行き先）は :30 を入口に残し、:29 の日付は経緯として外した。参考11（runner-commands.md の題）は目次から辿れれば K4 上は問題ないため据え置き。

## 18. 審査5回目（2026-10-22・PR #4649 HEAD 81cea94f2）と反映

- 審査役（model opus・新規起動）: **REVISE**（止めるべき0・直すべき2・参考9）。全文 /tmp/CC報告ファイル/agenda-nav-review5-20261022.md（リポジトリ外）。案文の安全の決まりは origin/main CLAUDE.md と文字列で一致（緩くなっていない）。段2a の記述は実物と一致。手元の process-artifacts gate は PASSED・警告なし。
- 反映（直すべき）: ①段0b で強制を確かめる先に Ruleset・Branch Protection・リポジトリの .claude/settings.json・git フックを追加（直接コミット禁止・直push禁止・ブランチ削除禁止は効果の項目にしない）②dev-commands.md の新設と AGENTS.md :46・:103-126 の移動を段3a に追加し、段3b の移動先の一覧を §5-2 に合わせた。
- 反映（参考）: :29 の記録先を docs/handoff/claude-md-vps-key-rule/design.md:4 に訂正／段0 の ADR に衝突点③（root CLAUDE.md が行数検査されていない穴）／段2a の測り方を過去コミットでの手元実行＋マージ後の最初の CLAUDE.md 変更 PR に固定（試しの PR は作らない）／段1 の PR に GO記録が要る旨／ADR-144 の行き先を frontend/AGENTS.md に／kgi.md K8 の見方を段0b の集団定義へ寄せた（合格ラインは不変）／段0b の基準時点と本テーマの PR の除外／§5 の Claude 固有の列挙に --claude。参考7（入口から移す安全寄りの3文）は §11 に PO 確認事項として追加。

## 19. 審査6回目（2026-10-22・PR #4649 HEAD 3a6eaa611）と反映

- 審査役（model opus・新規起動）: **REVISE**（止めるべき0・直すべき1・参考6）。全文 /tmp/CC報告ファイル/agenda-nav-review6-20261022.md（リポジトリ外）。案文の安全の決まり・K8 の数え方・kgi.md の合格ラインは問題なし。段0・段1はカードを書ける。
- 反映（直すべき）: 段3a を「codex-operations.md・dev-commands.md へ行く行すべて」に（Dev 行2本・Codex のブランチ名が段から漏れていた）。
- 反映（参考）: 段0b で読む先を rules/branches/main に／段3b の docs/INDEX.md は段2で新設済みと明記／段3c の前に全行の移動を grep で確かめる手順／kgi.md K8 の例に「強制済みの例は効果に数えない」注記（合格ラインは不変）／PR 本文に §16〜§19 を反映。参考5（develop の ruleset に PR 必須が無い）は K8 が main へのマージだけを数えるため影響なし。

## 20. 全体図（PO 向け・日常語）と Fable 判断の反映（2026-10-22）

PO 原文（2026-10-22）「仕様書と設計図はどうなったの？逐一停止しているけど全体図書いてないの？fableにまかせてくれ」を受け、残りの設計判断（§10-4〜§10-7・§11 の安全寄りの3文）を Fable が決めた。全文 ~/CC報告ファイル-keep/agenda-nav-20261022/fable/decisions.md（リポジトリ外・151行）。Opus が根拠の file:line を実物で照合した（spec.md §Version・handoff/fix-unify-type-mismatch/design.md:42-43・gh-pr-create-safe.sh:120・executor-preflight.sh:69-75・master-register-rules-guard.py:23・:60-66）。PO に戻す判断は無し。実行（フック・設定・CI・個人設定の変更）は段ごとに PO の実装承認が要る。

| 段 | 何をするか | PO が確認できること |
|---|---|---|
| 0 | この取り組みの「決めごと」を正式な記録（設計判断の文書）として1枚起こす | 設計判断の一覧に新しい1件が増えている |
| 0b | 変える前の「今の値」を測って残す（決まりが守られた回数・会話の始まりに読む量） | 測った日時と数字が1枚にまとまっている |
| 1 | 商品を登録する決まりが「関係ない話でも毎回出てくる」のを、関係ある話だけに絞る | 関係ない例文5本で出てこない（0/5）・関係ある例文2本では出る（2/2） |
| 1b | 決まりを「説明として引用しただけ」の調査メモの保存で止まるのをやめる（登録そのものは今までどおり止まる） | 調査メモが保存できる／登録の操作は止まる |
| 2a | 入口ファイルの行数検査が、肝心の入口で動いていなかった穴をふさぐ | 入口を変えた次の PR で検査が「飛ばされず」に動く |
| 2 | 手順書の「目次」を1枚作り、届かなかった文書36本を章の下に並べる（2本は作業記録の置き場へ移す） | 目次から辿れない文書 0・3段以内・「いつ読むか」の空欄 0（検査の出力） |
| 3a | Codex 専用の手順と開発コマンドを、入口から専用ページ2枚へ移す（中身は変えず移すだけ） | 入口から消えた分が新しい2枚に丸ごと在る |
| 3b | 入口に書かれていた手順の本文を、それぞれの正しい置き場へ移す（中身は変えず移すだけ） | 移した先に同じ文が在り、入口と二重になっていない |
| 3c | 入口を入れ替える: 安全の決まり・前提・目次への案内だけの短い入口にする（AI 共通の1枚＋Claude 専用の数行） | 入口の合計が 90行以下・安全の決まりが残っている・会話の始まりに読む量が減っている |
| 4 | 画面側・サーバー側の入口も同じ形（共通1枚＋Claude 専用）に揃える | 同じ決まりが2か所に書かれている件数 0 |
| 5 | 目次の検査を「注意だけ」から「違反なら止める」に格上げする（連続5回 0 件を確かめてから） | 検査が赤になると PR が止まる |
| 6 | しんごさんの個人設定から「AGENTS.md も同時に更新」の節を消す（正本が1か所になるため不要） | 個人設定からその節が無くなっている |
| 7 | しんごさんの個人設定・ルールを短くする（残す／条件付きで読む形へ／リポジトリ側への案内に置換、の案を一覧で出し承認分だけ変える） | 会話の始まりに自動で読む行数が合計 200行以下 |

順番: 0 → 0b → 1 → 1b → 2a → 2 → 3a → 3b → 3c → 4 → 5 → 6 → 7。1b と 2a は他と独立で前後してよい。6 は 4 の後。フック・CI・個人設定を触る段（1・1b・2a・5・6・7）は、それぞれ着手前に PO の実装承認が要る。

反映した箇所: §5（~/.claude/CLAUDE.md:13 の行）・§5-2（:51 を入口へ、案文 45行・合計 54行）・§6（KGI-2 行の免除パス）・§8（段1b 追加・段2・段6）・§9（skills）・§10-5〜§10-7・§11 先頭・docs/handoff/doc-agenda-nav/unreachable-list.md（§3 #7・#16・#17、§5）・draft/AGENTS.entry.md（:51 の1行）。

参考（判断は不要）: lessons.d の直下は 22枚で scripts/lessons-view.sh:37 の警告の目安 20 を超えている（清書は本テーマの範囲外）。docs/specs/master-ssot-migration/ には表紙が無い（K4 には影響しない。段2で docs/specs/README.md に1行足すのは任意）。

## 21. 審査8回目（2026-10-22・PR #4649 HEAD 487f25c56）と反映

- 審査役（model opus・新規起動）: **REVISE**（止めるべき0・直すべき6・参考6）。全文 /tmp/CC報告ファイル/agenda-nav-review8-20261022.md（リポジトリ外）。Fable の根拠は実物と一致、案文の安全の決まりは緩んでいない（45・9＝54行）、CI は失敗0。
- 反映（直すべき）: ①K4・K5 の「今」の値に訂正の注記（design §2・kgi.md）②案文の行数を 45・9＝54 に ③docs/specs/README.md の状態列を更新 ④docs/ai-agents 19件の行を決定（lessons.d をフォルダ1行）に合わせた ⑤§11 の「旧基準値を再現してから」を「新しい基準値を再現してから」に ⑥段1b で足す文字列を `/CC報告ファイル-keep/` に（`~` は判定で展開されない）・試験は絶対パスで書く。
- 反映（参考）: 段7の「承認待ち」を実装承認と明記／段1と段1b の試験ファイルの順番／.bak から戻した後の diff 確認／ADR-076 をファイル名で指定。参考5・6 は変更不要。

## 22. 審査9回目（2026-10-22・PR #4649 HEAD 857de7b45）と反映

- 審査役（model opus・新規起動）: **REVISE**（止めるべき0・直すべき2・参考5）。全文 /tmp/CC報告ファイル/agenda-nav-review9-20261022.md（リポジトリ外）。審査8回目の直すべき6件・参考1〜4 は反映済みと確認。段1b の免除文字列は判定式の再現で効くことを確認。案文の安全の決まりは緩んでいない（45・9＝54行）。CI は失敗0。段0・段1・段1b のカードは書ける。
- 反映（直すべき）: ①KGI-4 の測り方と §6 の到達検査の実装を reach.py（unreachable-list.md §1 の定義）に合わせた（保存されていない旧スクリプトを指していた）②§3 の範囲と docs/specs/doc-agenda-nav/README.md の境界を今の段（1b・2a・6・7）に合わせた。
- 反映（参考）: 段0 の ADR に上限の決定値 90行を書く／status に最新の審査を明記／§10-7 の書き方は置き場所の名前で、文字列の正は §8 段1b と明記／§4 の「最深14段」に訂正の注記。参考5（§20 の日常語の要約）は審査役の判断どおり変更なし。


## 23. 段3c の分け方と、移り先の隙間の判断（2026-10-24・Opus 設計判断。PO 承認「1」2026-10-23＝段3c に進む）

- 照合（起点 50d7f52da）: 入口2本の空行以外 128 行のうち、案文に一字一句ある 21・ほかの場所に一字一句ある 51・一致なし 56（/tmp/CC報告ファイル/an-stage3c/recon/11-line-map.tsv・12-missing.txt、リポジトリ外）。一致なし 56 の多くは案文に同じ意味の行がある（見出し・言い回しの違い）。
- 移り先が本当に無いもの（隙間）と判断:
  - G1 i18n（CLAUDE.md:71・:73、AGENTS.md:57-60）と G2 UI ガバナンス（CLAUDE.md:86・:87）: §5-2 の行き先は frontend/AGENTS.md だが、段4の前は Claude が frontend/AGENTS.md を読み込まない（frontend/CLAUDE.md が @AGENTS.md になるのは段4）。そこで**段4までは案文 AGENTS.entry.md に CLAUDE.md:71・:73・:86・:87 を一字一句写して残し、段4で frontend/AGENTS.md へ移す**。段3b-4 カード §1「frontend/AGENTS.md へ移すのは段4の後」と同じ向き。
  - G3 仕様書 docx（CLAUDE.md:15）: 目次 docs/INDEX.md の章B に1行足す。
  - G4 KPI の正本（AGENTS.md:23）: 目次の章A に1行足す（docs/ai-agents/kpi.md は存在する）。
- 入れ替えると指す先が消える参照（`git grep` 実測、/tmp/CC報告ファイル/an-stage3c/recon/16-refs.txt・21-code-refs.txt）:
  - scripts/check-process-artifacts.js:356「→ 詳細: CLAUDE.md §ブランチ運用ルール」→ docs/specs/branch-operations/README.md §8（GO 手順はそこにある）。^scripts/ に当たるので GO 記録が要る。
  - docs/runbooks/adr-019-english-ui-temporary-deploy.md:186 の CLAUDE.md へのリンク → 同 README へ。
  - docs/onboarding/claude-code.md:145・docs/STANDARD-WORKFLOW.md:160・.claude/hooks/check-freshness.sh:25（見張る文書の一覧に AGENTS.md・docs/INDEX.md が無い）は、入れ替えと同じ PR で直す。
  - 直さないもの: 「不可逆操作は必ず PO 確認」の見出しは AGENTS.md に残り CLAUDE.md が取り込むので、workflow-lint.yml（変更禁止）・scripts/agent-hooks/cloud/rules.md の参照は有効のまま。ADR・research・audit の行番号参照は経緯の記録なので直さない。scripts/setup_tenant.py:31・:474 の「新規テナント作成後の必須チェックリスト」は今の CLAUDE.md にも無い（入れ替え前から切れている。本テーマの範囲外）。
- 便の分け方:
  - 段3c-1（準備）: 案文への i18n・UI ガバナンスの写し、目次への2行、上の参照2件、この節。カード docs/handoff/doc-agenda-nav/card-stage3c-prep.md。
  - 段3c-2（入れ替え）: AGENTS.md・CLAUDE.md を案文どおりにする。check-claude-size.js の LIMITS（AGENTS.md 80・CLAUDE.md 10・docs/INDEX.md 60）とエラー文、docs/INDEX.md:28・:40、STANDARD-WORKFLOW:160、onboarding:145、check-freshness.sh:25、ADR-1040 の Accepted 化と README の作り直し。入れ替えの前に全 128 行を「案文の行／移り先の行／意味の対応表」で 100% 結ぶ（K11）。

## 24. 段3c-2 の前に見つけた隙間 G5・G6 と、K11 の確かめ方（2026-10-24・Opus 設計判断。起点 d298ab129＝段3c-1 #4708 のマージ後）

- §23 の LIMITS の数値（AGENTS.md 80・CLAUDE.md 10・docs/INDEX.md 60）は、段3c-2 で check-claude-size.js に**設定する値**であり、起点ではまだ CLAUDE.md 120 だけが登録されている（frontend/scripts/check-claude-size.js:22-28。段3c-1 の審査の参考指摘）。
- G5（ADR-025 の前半）: CLAUDE.md:79 の前半「**本番運用フェーズ移行後に effective**（現在は開発フェーズのため直接INSERT/UPDATE は継続）」は ADR-025 の本文に無い（`grep -n 'effective\|開発フェーズ\|本番運用フェーズ\|フェーズ' docs/adr/ADR-025_meta_integration_operational_hardening.md` が0件）。§5-2 の「前半は ADR-025 を正とする」という前提が成り立たないため、**案文 draft/AGENTS.entry.md:21 を CLAUDE.md:79 の全文に置き換える**（一字一句・行数は変わらない）。この便の最初のコミットで Opus が直す。
- G6（並行作業の手引きへの道）: CLAUDE.md:41 の「詳細: `docs/PARALLEL_TERMINAL_GUIDE.md`」は案文に無く、目次 docs/INDEX.md・docs/specs/branch-operations/README.md からも指されていない（`git grep -n PARALLEL_TERMINAL_GUIDE -- docs ':!docs/handoff' ':!docs/adr'` は evidence-registry の3件だけ）。目次の到達検査（check_doc_index.py:130）の対象は docs/specs/・docs/ai-agents/ だけなので、この欠けは検査に出ない。そこで**目次の章A（ブランチ運用の行の直後）に1行足す**。
- 入れ替え後の到達検査: 起点の写し（detached worktree）で AGENTS.md・CLAUDE.md を入れ替え後の文面に置いて check_doc_index.py を回し、SUMMARY は入れ替え前と同じ（unreached=0 deep=2 blank_when=0 no_when_column=0 broken_link=8 warnings=10。/tmp/CC報告ファイル/an-stage3c/swap-recon/cdi-before.txt・cdi-after.txt、リポジトリ外）。
- K11 の確かめ方（この便のマージ前）: 起点の CLAUDE.md・AGENTS.md の空行以外 128 行それぞれを、①入れ替え後の AGENTS.md・CLAUDE.md ②`git ls-files docs ':!docs/handoff'` の全文、の順に完全一致で探す。**grep には -a を付ける**（全文をつないだファイルは macOS の grep で binary と判定され、一致しても見つからない扱いになる。実測: CLAUDE.md:73 が -a なしで不一致・-a ありで一致）。一致しない行は、すべて意味の対応表 docs/handoff/doc-agenda-nav/k11-map.md に載っていること。Opus の試算（G5 反映後の案文で実施）は 入口に一致 27・docs に一致 51・一致なし 50 で、一致なし 50 行はすべて対応表に載せた。
- 対応表で「移り先なし（削除）」としたもの: AGENTS.md:14・:16（ADR-082 の廃止済みの節。経緯は ADR-082 と git の履歴）、AGENTS.md:79-84（AGENTS.md を正本1か所にしたので「CLAUDE.md の決定を AGENTS.md にも写す」決まりは不要になる。ユーザー側 ~/.claude/CLAUDE.md の同じ決まりは段6で扱う）、AGENTS.md:3・CLAUDE.md:3 の旧冒頭文（入口の役割は案文 :3・CLAUDE.entry:9 が言い直す）。
- この便で変えないもの（確かめただけ）: .github/PULL_REQUEST_TEMPLATE.md:65-67「CLAUDE.md 変更時」の欄（危険パス。CLAUDE.md は残るので有効）、claude-md-staleness-check.yml（CLAUDE.md だけを見る。AGENTS.md の鮮度は見ていない＝保守の穴として記録し、段5で扱う）、frontend/AGENTS.md・backend/AGENTS.md の LIMITS 登録（段4）。
- G7（手元のコミット時の行数検査が別のファイルを数えている。段3c-2 の実装中に担当が見つけ、Opus が再現）: frontend/.husky/pre-commit:38 は frontend/ に移ってから :52 で check-claude-size.js を実行する。フックの中では git が GIT_DIR を設定するため、check-claude-size.js:16 の `git rev-parse --show-toplevel` は作業場所の根ではなく frontend/ を返し、LIMITS の `CLAUDE.md` として frontend/CLAUDE.md（78行）を数える（再現: frontend/ で `GIT_DIR=$(git rev-parse --git-dir) git rev-parse --show-toplevel` が …/frontend を返し、同じ条件で check-claude-size.js が「❌ CLAUDE.md: 78行（上限10行）」・exit 1。/tmp/CC報告ファイル/an-stage3c/swap-recon/hook-repro.txt、リポジトリ外）。上限 120 の間は 78 < 120 で表に出ず、入口の CLAUDE.md は手元では一度も数えられていなかった。CI（.github/workflows/check-claude-size.yml:40）はフックの外なので正しく数える。**直し方: check-claude-size.js の根の求め方を、スクリプト自身の場所から2つ上（`frontend/scripts/` → 根）に変える**（pre-commit:34-36 が同じ理由で $0 から根を求めているのと同じ考え方）。この便で直す。
- G7 の残り（この便では直さない）: pre-commit:52 は check-claude-size.js の終了コードを見ていないので、手元では上限を超えても commit は止まらない（担当の commit が exit 0 だった）。docs/INDEX.md の「コミットをブロックする」は CI のマージ止めとしては正しいが手元では正しくない。止めるかどうかは frontend/.husky の変更になるため、段5で扱う。

## 25. 段4 frontend・backend の入口をそろえる（2026-10-25・Opus 設計判断。PO 承認「1」2026-10-25＝段4に進み、画面側とサーバー側の入口の文書も同じ形にそろえる。起点 d7924ae70）

- 形: frontend・backend とも AGENTS.md を正本にし、CLAUDE.md は表題と 「@AGENTS.md」 の3行だけにする（ルートと同じ向き。§8 段4）。案文は docs/handoff/doc-agenda-nav/draft/frontend-AGENTS.md（77行）・frontend-CLAUDE.md・backend-AGENTS.md（70行）・backend-CLAUDE.md（各3行）。
- 取り込みの根拠（Context7 は月の上限で使えず、公式資料を直接確認。抜き書き /tmp/CC報告ファイル/an-s4/claude-docs-memory.txt、リポジトリ外）: https://code.claude.com/docs/en/memory「Relative paths resolve relative to the file containing the import」。下の階層の CLAUDE.md は、その階層のファイルを読み書きしたときに読み込まれる。よって frontend/CLAUDE.md の 「@AGENTS.md」 は frontend/AGENTS.md を指し、frontend/ を触るときに本文が届く（今と同じ時点）。
- Codex の読み込み範囲（公式 https://learn.chatgpt.com/docs/agent-configuration/agents-md、2026-10-25 確認）: 「Codex walks from the project root toward your working directory」「Codex stops searching once it reaches your current directory」。根で起動した Codex は frontend/AGENTS.md を自動では読まない（段4の前から同じ。PageLayout・CSS・アイコンの決まりは既に frontend/AGENTS.md だけにある）。段4で i18n・UI ガバナンスを根から外すと、根で起動した Codex には案内の1行（AGENTS.md:45）だけが残る。対処: ①AGENTS.md:45 を「触る前に開いて読む」と、自動で読まれない理由つきに書き直す（行数は変わらない）②i18n は ESLint `local/no-japanese-literal`（frontend/scripts/eslint-rules/no-japanese-literal.cjs）、UI ガバナンスは .github/workflows/ui-governance-gate.yml が機械で止める（ルートの判定木1番「CI / ESLint が既に強制しているか」に当たる）。
- 根から外すもの: AGENTS.md:46-53（空行と i18n・UI ガバナンスの2節）。frontend/AGENTS.md:21-36 へ移す（§23 G1・G2 で「段4で frontend/AGENTS.md へ移す」と決めた行）。AGENTS.md:49 の末尾「grep セルフチェック: `frontend/CLAUDE.md`」は移り先のファイル自身を指すので外し、確かめ方は同じ節の `npm run lint`。根は 45行になる。
- 行数の上限（frontend/scripts/check-claude-size.js:24-32 の LIMITS）: ADR-076 の frontend 90・backend 70 は本文の置き場所に付ける上限なので、本文と一緒に AGENTS.md へ移す（`frontend/AGENTS.md` 90・`backend/AGENTS.md` 70 を足す）。CLAUDE.md 2本はルートと同じ 10。未登録を見つける処理（:34-46）は CLAUDE.md だけを探す。AGENTS.md の未登録検出は段5で扱う。
- backend を 70行に収めた方法: 中身は削らない（ADR-076「具体例を削ると判断精度が落ちる」）。bash の囲み（6行）を1行の箇条に、参考ファイルの行（2行）を箇条の中に入れた。DO $$ の SQL 例は一字一句そのまま。migration-guard.yml が名前で指す見出し「## Migration 適用経路」「## Migration は additive-only（追加専用）」は残す（backend-AGENTS.md:30・:24）。
- K11: 対象 172行（起点の4本の空行等を除く 170行と、書き直す AGENTS.md:45・CLAUDE.md:7）。まとめた後の5本（ルート AGENTS.md と frontend・backend の4本）に部分一致で探すと、一致 129・不一致 43（案文での試算。/tmp/CC報告ファイル/an-s4/sim/、リポジトリ外）。不一致 43行はすべて docs/handoff/doc-agenda-nav/k11-map-stage4.md に載せた（表は 45行。frontend・backend の CLAUDE.md:1 の表題2行は CLAUDE.md に残るので一致側に入る）。削除は0行。
- 一緒に直す参照（指す先が「本文の在る AGENTS.md」に変わる）: docs/INDEX.md:22・:23（リンクを AGENTS.md の1本に）・:36・:37（判定木の追加先を AGENTS.md に）・:38（例「i18n 等」は frontend に移るので「不可逆操作・ブランチ運用 等」に）、.claude/hooks/check-freshness.sh:25（見張る一覧に frontend/AGENTS.md・backend/AGENTS.md を足す）、.claude/agents/governance.md:72（grep の対象を4本の AGENTS.md 系に）、docs/onboarding/design-system.md:100、ADR-1040 Consequences（上限の置き場所の追記）。
- CLAUDE.md:7（ルート）: 上の K3 の判断で書き直す。新しい文は実装カード card-stage4.md §4。
- 直さない参照（取り込みで行き先が変わらない・経緯の記録）: .github/workflows/migration-guard.yml:63・160・337・381・388（見出しは残る。CI ファイル）、frontend/eslint.config.js:149、frontend/scripts/check-css-fixed-position.js:71、frontend/scripts/check-page-layout.js:107・119（frontend/CLAUDE.md から本文へ取り込みで届く）、migrations/ のコメント、ADR-034:79・ADR-076・ADR-141:30、backend/tenant/CLAUDE.md:3、docs/recon・docs/audit。claude-md-staleness-check.yml は段5。
- K3 の測り方: recon §2-4 の9語（i18n・ハードコード・不可逆・推測・executor-preflight・squash・worktree・日本語・file:line。生データ ~/CC報告ファイル-keep/agenda-nav-20261022/design/raw/duplicates-summary.txt）を、ルートと frontend・backend の CLAUDE.md・AGENTS.md の6本に `grep -alF` し、2ファイル以上に出る語を数える。起点 d7924ae70 では 4語（i18n 3本・ハードコード 3本・worktree 2本・日本語 4本）。
- K3 で見つけた残り（案文での試算）と判断:
  - worktree: ルート AGENTS.md:34（作業場所を必ず作る・作り方）と CLAUDE.md:7（同じコマンドに `--claude` を付けた形）。作り方のコマンドが2か所にあるので本当の重なり。**CLAUDE.md:7 をコマンドを書かずに AGENTS.md を指す文に書き直す**（Claude だけの部分＝`--claude` の意味は残す。行数は変わらない）。
  - 日本語: frontend/AGENTS.md:23・:24・:31（画面の文字を日本語で直書きしない＝i18n）と backend/AGENTS.md:66（DB の列の説明は日本語で書く）。語は同じだが決まりは別（recon §2-4 の行の名前は「日本語で応答」で、どちらもそれではない）。重なりではないと判断し、文は変えない。報告では grep の数（2本）と判断を並べて書く。
  - 段4の後の見込み: grep で 2本以上に出る語は「日本語」1語だけ。同じ決まりの重なりは 0語。
- 戻し方: この PR の revert。

## 26. 段5 見張りを強める（2026-10-25・Opus 設計判断。PO 承認「1」2026-10-25＝見張りを強める段へ進む：文書の行数が上限を超えたら手元で記録するときにも止まる。決まりの文書が古いまま放っておかれていないかも見張る。起点 origin/main 6a5047685＝段4 #4726 のマージ）

### 26-1. 現状（実物。生出力 /tmp/CC報告ファイル/an-s5/recon1〜5.txt、リポジトリ外）

- 手元の記録で止まらない理由: 作業場所のフックの置き場は `frontend/.husky`（scripts/new-worktree.sh:113-115 が husky の `frontend/.husky/_` を上書きして直接指す。この作業場所の `git config --get core.hooksPath` も `frontend/.husky`）。husky の起動役を通らないので、frontend/.husky/pre-commit は `#!/bin/sh`（:1）のまま `set -e` なしに動く。:52 の `node "$REPO_ROOT/frontend/scripts/check-claude-size.js"` が exit 1 でも次の行へ進み、最後の if（:74-77）の結果で終わる。§24 G7 の残り（担当の commit が exit 0）と同じ。
- 同じ理由で :43 `npx lint-staged`・:48 `check-dark-parity.js` の失敗も手元では止まらない（frontend/AGENTS.md:25「コミット前に自動ブロック」と食い違う）。**段5では直さない**（PO 承認の範囲は行数の見張り。この作業場所には frontend/node_modules が無い。lint-staged を止める側にすると、入れていない作業場所の commit が止まるおそれがあり、別に設計が要る）。§26-5 に残す。
- 未登録の見つけ方: check-claude-size.js:39-46 は `-name "CLAUDE.md"` だけを探す。:40 の `-not -name "./CLAUDE.md"` は名前に `/` を含むので何にも当たらない（根の CLAUDE.md は :44 の `p !== 'CLAUDE.md'` で外れている）。除外は `./node_modules/*` だけで、本店の写しには frontend/node_modules/recharts/AGENTS.md がある（`find frontend/node_modules \( -name AGENTS.md -o -name CLAUDE.md \)` が1件）。AGENTS.md を探す形にすると、除外を足さなければ本店で誤った警告が出る。
- 起点のリポジトリにある同名ファイル（`git ls-files`）: AGENTS.md 3本（根・frontend・backend。3本とも LIMITS に登録済み）、CLAUDE.md 6本（根・frontend・backend・backend/scripts・backend/tenant・tools/claude-channels/intake）。tools/claude-channels/intake/CLAUDE.md は未登録で、今も警告が出る（この作業場所で `node frontend/scripts/check-claude-size.js` が警告1件・PASSED・rc=0）。
- 古さの見張り: .github/workflows/claude-md-staleness-check.yml:45-48 は `find . -name "CLAUDE.md"` だけ。段4で本文は AGENTS.md へ移り、CLAUDE.md は3行の取り込みだけになったので、本文の古さは見ていない。起点での日数（origin/main の最終 commit から）: backend/scripts/CLAUDE.md 146日・backend/tenant/CLAUDE.md 144日、ほかの7本は12日以内。直近の実行は 2026-10-01 の定期実行（success）で、Issue #3904（OPEN）を作った。このワークフローは同じ Issue があっても新しく作る（:84-86 に重複の確かめが無い）。
- 危険パスの判定（scripts/check-process-artifacts.js:76-115）: frontend/.husky/pre-commit・frontend/scripts/check-claude-size.js は区分なし（本検査へ）、.github/workflows/claude-md-staleness-check.yml は実コード。どれも DANGEROUS_PATTERNS・PO 本人の GO の例外（:10-12 workflow-lint.yml だけ）に当たらない。workflow-lint.yml は触らない。必須チェック・Ruleset は変えない。

### 26-2. 分け方（1便1つ。変更→反映→測定→次）

| 便 | 変えるもの | 触るファイル |
|---|---|---|
| 5a | 手元の記録でも行数の上限超えで止める。あわせて AGENTS.md の未登録も見つける（止まる対象が LIMITS の表で決まるので、表から漏れたファイルを見つける側も同じ便で直す） | frontend/.husky/pre-commit:52、frontend/scripts/check-claude-size.js:21-46 |
| 5b | 古さの見張りの対象に AGENTS.md を足す | .github/workflows/claude-md-staleness-check.yml |
| 5c | 到達検査を警告から失敗へ上げる | 保留（§8 段5。条件を満たしていない） |

### 26-3. 5a の作り方と受け入れ基準

- pre-commit:52 を `node "$REPO_ROOT/frontend/scripts/check-claude-size.js" || exit 1` にする（1行。ファイル全体に `set -e` は入れない＝:43 などの扱いを変えないため）。
- check-claude-size.js の未登録探し: find を `\( -name "CLAUDE.md" -o -name "AGENTS.md" \)` にし、`-not -path "*/node_modules/*"` を足し、何にも当たらない `-not -name "./CLAUDE.md"` を外す。:44 の根の除外は `p !== 'CLAUDE.md' && p !== 'AGENTS.md'`。警告の文は「CLAUDE.md・AGENTS.md」にする。警告のまま（失敗にしない。ADR-076 からの扱いを変えない）。:21-23・:36 の説明コメントも AGENTS.md を含む形に直す。
- 止まるのは「作業場所のファイル」の行数（:52-68 は index ではなく作業場所を読む）。記録しない別の変更が上限を超えていても止まる。CI（check-claude-size.yml:37-40）も同じファイルを数えるので、手元で通って CI で落ちる差は縮まる。`git commit --no-verify` で抜けられるのは今と同じ。

| 基準 | 検証方法 |
|---|---|
| T1 上限超えで手元が止まる | 作業場所で backend/AGENTS.md の写しを取り、1行足して `sh frontend/.husky/pre-commit; echo rc=$?` を変更前・変更後で実行。変更前 rc=0、変更後 rc=1 で「❌ backend/AGENTS.md: 71行（上限70行）」が出る。写しから戻し `git diff --exit-code backend/AGENTS.md` が rc=0 |
| T2 上限内なら止まらない | 変更後に何も足さず同じ実行で rc=0。この便の commit 自体がフックを通って成功する |
| T3 AGENTS.md の未登録を見つける | tools/s5probe/AGENTS.md（1行）を置いて `node frontend/scripts/check-claude-size.js`。変更前は出ない、変更後は「tools/s5probe/AGENTS.md: LIMITS 未登録」が出て rc=0。消した後は intake の警告1件だけ |
| T4 node_modules の中は数えない | frontend/node_modules/s5probe/AGENTS.md を置いて同じ実行。変更後は警告に出ない。置いたものを消す |
| T5 文法 | `sh -n frontend/.husky/pre-commit` rc=0、`node --check frontend/scripts/check-claude-size.js` rc=0 |
| T6 CI | check-claude-size.yml は AGENTS.md・CLAUDE.md・docs/INDEX.md の変更時だけ動く。この便はどれも触らないので skip になる（想定どおり）。ほかの CI が緑 |

- 戻し方: PR revert（2ファイル）。

### 26-4. 5b の作り方と受け入れ基準（5a のマージ後に作る）

- :45-48 の find を `\( -name "CLAUDE.md" -o -name "AGENTS.md" \)` と `-not -path "*/node_modules/*"` にする。名前・見出し・Issue の文（:1・:18・:29・:57・:71・:85）を「CLAUDE.md・AGENTS.md」にする。日数（90）・実行の時期・Issue の作り方は変えない。
- 確かめ方: run の中身を手元の bash で origin/main の写しに対して回す。THRESHOLD_DAYS=90 で2本（backend/scripts・backend/tenant の CLAUDE.md）、THRESHOLD_DAYS=-1 で9本（AGENTS.md 3本を含む）が出ること。`actionlint` が0件。
- 手動実行（workflow_dispatch）はしない: Issue #3904 が開いたままで、実行すると同じ内容の Issue がもう1本できる（:84-86）。本番での確認は次の定期実行 2027-01-01 09:00（日本時間）で、それまでは「まだ確かめていない」と記録する。
- 戻し方: PR revert。

### 26-5. 残すもの（この段で直さない）

- pre-commit:43 lint-staged・:48 dark-parity の失敗が手元で止まらない（§26-1）。frontend/AGENTS.md:25 の「コミット前に自動ブロック」と食い違う。直すなら作業場所の frontend/node_modules の有無を先に決める設計が要る。PO に報告して扱いを決めてもらう。→ PO「1」（2026-10-25）で段5d として設計した（§27）。
- tools/claude-channels/intake/CLAUDE.md の LIMITS 未登録（起点から警告あり）。別の道具の文書なので、この段では登録しない。
- 5c の昇格（broken_link=8・warnings=10・deep=2 が残る）。
- フックの置き場が共有の設定で、`frontend/.husky/_` に書き換わる間は作業場所によって pre-commit が動かない（§26-7）。直すなら作業場所ごとの設定（worktreeConfig）か husky の prepare の扱いを決める設計が要る。PO に報告して扱いを決めてもらう。

### 26-6. 審査（Architect、同じ AI による自己審査）

- 判定: **APPROVE**（5a の実装カードへ進める）。
- 根拠: 変えるのは2ファイルで、§26-1 の行番号を実物で確かめた。止まる対象は CI と同じ LIMITS の表なので、新しい決まりは作らない。危険パス・Ruleset・必須チェックに当たらない。T1〜T5 は変更前と変更後の差で判定でき、推測を含まない。
- 未解決: なし（§26-5 は範囲外として残す。5b は 5a のマージ後に同じ形で進める）。

### 26-7. 5a の結果と 5b へ（2026-10-25）

- 5a: PR #4733 マージ（mergeCommit 01e53da6b、2026-10-25 13:22 JST）。T1〜T5 は担当の生出力（/tmp/CC報告ファイル/an-s5/impl/）で全て期待どおり、審査は 777c2f94d・main 取り込み後 680b0fcc7 とも APPROVE。CI の guard-authoring/evaluation は PR が main から遅れていた間 error になり（scripts/run-guard-evaluation.js:25 の `merge-base --is-ancestor base head` が失敗する）、main 取り込み後に pass。
- 審査で見つかった範囲外の事実（§26-5 に足す）: フックの置き場 `core.hooksPath` は本店の .git/config に1つしかなく（worktreeConfig は無効）、scripts/new-worktree.sh:115 の `git config core.hooksPath frontend/.husky` も共有の設定に書く。審査の途中で一度 `frontend/.husky/_` になっていた（書き換えうる仕組みとして husky の prepare＝frontend/package.json:47 `cd .. && husky frontend/.husky` が在る。いつ何が書いたかは未確認）。`_` の間は、その中身（husky の起動役）が無い作業場所では pre-commit 自体が動かない。2026-10-25 13:2x の確認では `frontend/.husky` に戻っている。
- 5b: §26-4 のとおり。起点 origin/main 01e53da6b で、新しい find が出すのは9本（AGENTS.md 3本・CLAUDE.md 6本）、90日を超えるのは backend/scripts/CLAUDE.md（146日）・backend/tenant/CLAUDE.md（144日）の2本。カードは card-stage5b.md（card-lint rc=0）。

## 27. 段5d 手元で止まらない検査2つ（2026-10-25・Opus 設計判断。PO 承認「1」2026-10-25＝直し方を別の段で設計する。起点 origin/main 00a8e3c38＝#4741 のマージ）

### 27-1. 現状（実物。生出力 /tmp/CC報告ファイル/an-s5d/、試しは t2/。リポジトリ外）

- frontend/.husky/pre-commit:43 `npx lint-staged` と :48 `node scripts/check-dark-parity.js` は、終わりの値（rc）を見ていない。フックは `set -e` なし（§26-1）で、最後の if（:74-77）の値で終わる。frontend/AGENTS.md:25「`lint-staged` により **コミット前に自動ブロック**（`--max-warnings=0`）。」と食い違う。
- 試し（41ed133be の使い捨ての作業場所で `npx lint-staged` を直接実行。t2/trial.sh）:
  - B＝本店の frontend/node_modules を symlink した作業場所: (i) 違反なし rc=0、(ii) tsx に日本語の文字列 → `local/no-japanese-literal`・「ESLint found too many warnings (maximum: 0).」rc=1、(iii) index.css の :root だけに変数を足す → dark-parity FAILED rc=1。
  - A＝frontend/node_modules が無い作業場所: (i)・(ii) とも「✖ Task failed to spawn: eslint --max-warnings=0 / ENOENT」rc=1（違反を見つけたのではなく、eslint を起動できない）。(iii) rc=1。
  - dark-parity を直接: 変更なし rc=0、(iii) rc=1。使うのは node の標準部品だけ（check-dark-parity.js:13-15）なので、node_modules が無くても正しく動く。
  - `npx lint-staged` は node_modules が無くてもネットから取って動く（17.6.0）。`npx eslint` は v10.13.0、stylelint は 17.16.0 を取ってくる（package.json は eslint ^9.39.4・stylelint ^16.26.1・lint-staged ^17.0.5。本店の node_modules は 9.39.4・16.26.1・17.0.5）。
- 作業場所 49 件のうち frontend/node_modules を持つのは 3 件（実体 2・symlink 1）、46 件は持たない（5-count.txt）。scripts/new-worktree.sh は node_modules を扱わない（:113-115 はフックの置き場の設定だけ）。
- つまり今は、46 件の作業場所で frontend の commit のたびに lint-staged が rc=1 になっているが、rc を見ないので誰も気づかない。本当の関所は CI の必須チェック「Lint & Dark Mode Check (ADR-067)」（.github/workflows/e2e.yml:121-122。:57 の lint-run が `npm ci` → `npm run check:all`。check:all は package.json:46 で eslint・dark-parity・css 系・stylelint を含む）。
- 範囲の外で見つけたこと（記録だけ。直さない）: pre-commit:56 のコメント「ruff 未インストールの場合は警告のみ」に対し、:61-67 は ruff が無いと exit 1、:62 は `--exit-zero` で違反があっても止まらない。:76 lint_tenant_schema.py の rc はフック全体の rc になる（最後の if のため）。

### 27-2. 代替案と選んだ理由

| 案 | 中身 | 判断 |
|---|---|---|
| A | :43・:48 に `\|\| exit 1` を足すだけ | 退ける。46 件の作業場所で frontend の commit が「eslint を起動できない」で全部止まる（違反が無くても） |
| B | new-worktree.sh で本店の node_modules を symlink する | 退ける。本店の部品の版と作業場所の package.json がずれうる・共有の部品を作業場所が書き換えうる。部品の手当ては別の課題 |
| C | npx に任せる | 退ける。ネットから版の違う道具（eslint 10・stylelint 17）を取ってきて、CI と違う結果になる |
| **D（採用）** | dark-parity は `\|\| exit 1`。lint-staged は部品（`node_modules/.bin/` の lint-staged・eslint・stylelint）が揃っているときだけ直接呼んで `\|\| exit 1`。揃っていなければ「飛ばした・CI で検査される」と警告を出して先へ進む | 部品がある作業場所では文書どおり止まる。無い作業場所では今と同じく通るが、飛ばしたことが目に見える。ネットから道具を取らない。CI の関所は変えない |

### 27-3. 作り方（2ファイル）

- frontend/.husky/pre-commit:42-49 を次にする（:37-41・:50 以降は変えない。`set -e` は入れない）。

```sh
# lint-staged で変更ファイルのみチェック（ADR-1040 段5d）
# 部品（frontend/node_modules）が揃っていれば違反で止める。揃っていなければ飛ばして知らせる
# （npx でネットから版の違う道具を取らない。CI の必須チェック「Lint & Dark Mode Check (ADR-067)」で検査される）
if [ -x node_modules/.bin/lint-staged ] && [ -x node_modules/.bin/eslint ] && [ -x node_modules/.bin/stylelint ]; then
  node_modules/.bin/lint-staged || exit 1
else
  echo "⚠️  frontend/node_modules が無いため、書き方の検査（lint-staged）を飛ばしました。CI の Lint & Dark Mode Check で検査されます"
fi

# index.css が変更された場合はパリティチェック
if git diff --cached --name-only | grep -q "frontend/src/index.css"; then
  echo "📋 index.css 変更検出 → ダークモード変数パリティチェック実行"
  node scripts/check-dark-parity.js || exit 1
fi
```

- cwd は :38 で frontend なので、`node_modules/.bin/` は frontend/node_modules/.bin を指す。symlink の node_modules でも `-x` は先をたどる。
- 部品があるとき、index.css の変更では dark-parity が lint-staged（package.json:66-68）と :48 の2回動く（今と同じ）。
- frontend/AGENTS.md:25 を次の1行にする（行数は 77 のまま。上限 90）:
  `` `lint-staged` により **コミット前に自動ブロック**（`--max-warnings=0`）。frontend/node_modules が無い作業場所では手元の検査を飛ばして警告だけ出し、CI の必須チェック「Lint & Dark Mode Check (ADR-067)」で検査される。``
- 危険パスの判定: frontend/.husky/pre-commit・frontend/AGENTS.md は DANGEROUS_PATTERNS に当たらない（§26-1 と同じ）。workflow-lint.yml・Ruleset・必須チェックは触らない。

### 27-4. 受け入れ基準

試しは使い捨ての作業場所（`~/worktrees/salesanchor/` の下に detached で作る。フックの :14-25 が作業場所の外を止めるため）で、フック全体 `sh frontend/.husky/pre-commit; echo rc=$?` を変更前（origin/main のフック）と変更後（この便のフックを写したもの）で比べる。

| 基準 | 検証方法 |
|---|---|
| T1 部品なし・違反なしは通る | A で tsx に `// probe` を足して add。変更前 rc=0・変更後 rc=0、変更後は「⚠️ … 飛ばしました」が出て「Task failed to spawn」が出ない |
| T2 部品なしでも暗い画面の色は止まる | A で index.css の :root だけに変数を足して add。変更前 rc=0・変更後 rc=1（dark-parity FAILED） |
| T3 部品ありで書き方の違反は止まる | B で tsx に日本語の文字列を足して add。変更前 rc=0・変更後 rc=1（`local/no-japanese-literal`） |
| T4 部品ありで違反なしは通る | B で T1 と同じ。変更前・変更後とも rc=0 |
| T5 部品ありで暗い画面の色も止まる | B で T2 と同じ。変更後 rc=1 |
| T6 止まったあとも記録しようとした変更は消えない | T3・T5 の後に `git diff --cached --name-only` で足したファイルが残っている |
| T7 ネットから道具を取らない | 変更後の T1〜T5 の出力に npx の取得（`npm warn exec`・`Need to install`）が出ない |
| T8 文法と行数 | `sh -n frontend/.husky/pre-commit` rc=0。`node frontend/scripts/check-claude-size.js` rc=0（frontend/AGENTS.md 77行） |
| T9 CI | この便の PR の CI が緑（Lint & Dark Mode Check は frontend の変更で動く） |

- 戻し方: PR revert（2ファイル）。
- 測り方（反映後）: 部品のある作業場所で frontend の違反を入れた commit が手元で止まること＝T3 が本番の作業場所でも同じになる。46 件の作業場所では警告の行が出るだけで、通り方は今と同じ。

### 27-5. 外部事例

- 使わない。理由: 判断の根拠はこのリポジトリのフック・CI・作業場所の実測（§27-1）で足り、他社の事例は部品の置き方が違うため当てはまらない。lint-staged が失敗で 1 を返し変更を元に戻す動きは、実測（B-ii の「Reverting to original state because of errors」rc=1）で確かめた。

### 27-6. 残すもの

- 作業場所に frontend の部品を入れるかどうか（入れれば 46 件でも手元で止まる）。版・容量・共有の扱いが要る別の課題。
- §27-1 の ruff・:76 の食い違い。
- §26-5 のフックの置き場が共有の設定である件（変わらず PO に扱いを聞く）。

### 27-7. 審査（Architect、同じ AI による自己審査）

- 判定: **APPROVE**（実装カード card-stage5d.md へ進める）。
- 根拠: 変えるのは2ファイルで、行番号と動きを §27-1 の実測で確かめた。部品の有無で分けるので、今通っている 46 件の作業場所の commit を新しく止めない（T1）。止まるのは文書が約束している場合だけ（T2・T3・T5）。CI の関所・Ruleset・危険パスに当たらない。T1〜T8 は変更前と変更後の rc の差で判定でき、推測を含まない。
- 未確認（カードの T で確かめる）: フック全体を通したときの rc（試しは `npx lint-staged` 単体）、stylelint 単体の結果、オフラインでの動き（変更後は npx を使わないので関係しない）。
- 未解決: なし。

## 28. 段7（段6を含む）全員共通のルール集を短くする（2026-10-25・Opus 設計判断。PO 承認「1」2026-10-25＝全員共通のルール集を、目次から詳しい文書へたどる形に組み替える案を作る。予定の段6もここに含める。起点 origin/main c233ec8f6）

### 28-1. 現状（実物。生出力 /tmp/CC報告ファイル/an-k9/・an-gl/。リポジトリ外）

- K9 の測り直し（c233ec8f6 の detached の写しで `claude -p "/context" --no-session-persistence` を1回。claude 2.1.310。2026-10-25 20:46）: Memory files 17.7k − MEMORY.md 10.6k ＝ **7.1k**（前回 4bd48fa42 は 7.2k）。合格ライン 6.5k 以下に 0.6k 足りない。内訳: ~/.claude/CLAUDE.md 2.7k・~/kb/AGENTS.md 1k・rules/common/git-workflow.md 247・agents.md 907・リポジトリの CLAUDE.md 198・AGENTS.md 2k（an-k9/context-c233ec8f6.txt:215-221）。ユーザー側の4本（約4.85k）は本テーマでまだ変えていない。
- K1（`wc -l`）: ユーザー側 193（~/.claude/CLAUDE.md 84・~/kb/AGENTS.md 32・agents.md 53・git-workflow.md 24）＋入口 54（origin/main AGENTS.md 45・CLAUDE.md 9）＝ **247行**。合格ライン 200行以下。
- ~/.claude/CLAUDE.md は通常のファイル（symlink でも git 管理でもない。生成する台本も無い）。節ごとの量（wc -m。推定トークン＝割合×2.7k で、実測ではない。an-gl/sections_table.txt）:

| 行 | 節 | 文字 | 推定トークン | 行き先 |
|---|---|---|---|---|
| 1-2 | 表題 | 16 | 約14 | 残す |
| 3-8 | 認証情報 | 185 | 約165 | 残す（全リポジトリで毎回守る） |
| 9-11 | Context7 | 76 | 約68 | 残す（ほかに同じ決まりが無い） |
| 12-14 | AGENTS.md 自動更新ルール | 205 | 約183 | **消す（段6。§10-5 で確定済み）** |
| 15-36 | 報告の型（PO への型・「詳しく」の型） | 1201 | 約1072 | 残す。PO の最優先の決まり（2026-10-19）で毎回の返事に使う。見張り ~/.claude/scripts/japanese-reply-guard.py:2,:16 と ~/kb/00-rules/chat-format.md:9 がこの節を名指しする |
| 37-56 | 記憶で答えない／出力を省略しない／実行と反映は別／一度に1つ／提案の型／迷ったら止まる | 452 | 約404 | 残す（全リポジトリで毎回守る） |
| 57-74 | GAS / clasp | 582 | 約519 | **~/.claude/rules/gas-clasp.md へ文言そのまま移し、paths で GAS の作業のときだけ読まれるようにする。元の場所には案内1行** |
| 75-83 | 生出力はファイルへ | 309 | 約276 | 残す（全リポジトリで毎回守る） |
| 84 | @~/kb/AGENTS.md | — | （1k は ~/kb/AGENTS.md 側） | 残す（今回は変えない） |

- GAS / clasp の節は Sales Anchor の文書・仕様に1件も出てこない（clasprc・clasp login・tcg-sales-management・列番号の直書き。an-gl/overlap_grep.txt）。GAS を持つリポジトリは ~/crm-app-current・~/ebay-gas-automation・~/tcg-client-viewer・~/tcg-inventory-parser（an-gl/repos_index.txt・gas_repos.txt）。~/tcg-inventory-parser/CLAUDE.md:62,67-70,72 に同じ決まりの一部があるが、:58-64（clasprc の共有・GCP の統一・OAuth の本番）はどのリポジトリにも無い。だから「消す」ではなく「移す」。
- 公式の決まり（https://code.claude.com/docs/en/memory 取得 2026-10-25。Context7 は月の上限で使えなかったので、本起動指示の許可で公式資料を直接読んだ）: 「Rules without a `paths` field are loaded unconditionally」「A path-scoped rule loads when Claude uses the Read, Write, or Edit tool on a matching file」「User-level rules: [patterns are relative to] the session's primary working directory」「Personal rules in `~/.claude/rules/` apply to every project on your machine」。~/.claude/rules/common/coding-style.md:1-5 が同じ形（paths 付き）で既に使われている。

### 28-2. 代替案と選んだ理由

| 案 | 中身 | 判断 |
|---|---|---|
| A | 報告の型（約1.07k、いちばん大きい）を ~/kb/00-rules/ へ移して案内1行にする | 退ける。毎回の返事で使う PO の最優先の決まり。K10 の実測（目次を開くのは 20 回中 7 回）から、案内だけにすると読まれない回が出る。見張り2つも名指ししている |
| B | GAS / clasp を消す | 退ける。clasprc の共有・GCP の統一・OAuth の本番の3つは、ほかに書いてある場所が無い |
| **C（採用）** | 段6の3行を消す＋GAS / clasp を paths 付きの rules へ移す（文言はそのまま）＋案内1行 | 毎回読む量から約0.64k（推定）を外せる。決まりそのものは1つも消えない（GAS の決まりは GAS の作業で読まれる） |
| D | C に加えて「出力を省略しない」と「生出力はファイルへ」を1つにまとめる | 今回は採らない。PO の言葉を書き換えることになる。C を測って足りなければ次の一手として PO に見せる |

- 見込み: 7.1k − 約0.64k（183＋519−案内の約60）＝ **約6.46k**（推定。表示は 0.1k 単位なので 6.4k〜6.5k）。合格ライン 6.5k に対して余裕は小さい。判定は実測だけで行う。
- K1 は 247 → 約227行（84→65）で、**200行以下にはまだ届かない**。残り約27行は ~/.claude/rules/common/agents.md（53行）・git-workflow.md（24行）・~/kb/AGENTS.md（32行）の見直しが要り、次の判断として PO に見せる（今回は触らない）。

### 28-3. 作り方（リポジトリの外。変更は一度に1つ、それぞれ測る）

- 7-0（準備）: 変更前の写しを ~/CC報告ファイル-keep/agenda-nav-stage7-20261025/ に保存（~/.claude/CLAUDE.md・~/.claude/rules/common/ の一覧）。`cmp` で同じことを確かめる。
- 7a（段6）: ~/.claude/CLAUDE.md:12-14（見出し「## AGENTS.md 自動更新ルール」・本文1行・空行1行）を消す。ほかの行は変えない。→ K9 を測る（1回）。
- 7b: ~/.claude/rules/gas-clasp.md を新しく作る。中身は次の frontmatter の後に、元の :57-73（見出し「## GAS / clasp」から「新種は既存と重複しない接頭辞＋4桁連番）」まで）を1字も変えずに写す。

```markdown
---
paths:
  - "**/*.gs"
  - "**/appsscript.json"
  - "**/.clasp.json"
---
```

  そのあと ~/.claude/CLAUDE.md の元の :58-73（見出しの下の本文）を、次の1行に置き換える（見出し「## GAS / clasp」と後ろの空行は残す）。
  `- GAS・clasp の作業の決まりは ~/.claude/rules/gas-clasp.md にある（.gs・appsscript.json・.clasp.json を開くと自動で読まれる）。clasp を実行する前に必ず読む`
  → K9 を測る（1回）。
- 測り方は §28-1 と同じ（origin/main の detached の写し・`claude -p "/context" --no-session-persistence`・Memory files − MEMORY.md）。リポジトリ側は変えないので、差はユーザー側の変更だけになる。
- 担当（Sonnet）がカード card-stage7.md どおりに行う。~/kb は触らない（~/kb の記録は PO が `!` で行う決まりのため、今回は ~/kb を変えない案にした）。

### 28-4. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| T1 写しがある | 7-0 の写しと今のファイルを `cmp`。rc=0 |
| T2 7a は3行だけ消えた | 写しと 7a 後の `diff` が :12-14 の削除だけ。`grep -c "AGENTS.md 自動更新ルール" ~/.claude/CLAUDE.md` が 0 |
| T3 7b で GAS の決まりが1字も欠けていない | 写しの :57-73 と gas-clasp.md の frontmatter の後ろを `diff`。差 0 |
| T4 7b でほかの節は変わっていない | 写しと 7b 後の `diff` が :12-14 の削除と :58-73→案内1行だけ |
| T5 K9 | 7a 後・7b 後それぞれの K9（Memory files − MEMORY.md）。7b 後が **6.5k 以下**なら合格。Memory files の一覧に gas-clasp.md が出ていない（会話の始まりには読まれない） |
| T6 GAS の作業では読まれる | GAS のリポジトリ（appsscript.json を持つもの1つ）で `claude -p` に「appsscript.json を Read で開いてから、指示の中に clasprc の決まりがあれば原文を1行そのまま引用して」と頼み（`--allowedTools Read`・`--no-session-persistence`）、答えに「ホームに1つしかない共有ファイル」が出る。比べるために、同じ問いを appsscript.json を開かせずに聞き、出ないこと |
| T7 K1 | `wc -l` の合計を記録する（合否には使わない。約227行の見込み） |

- 戻し方: 写しから ~/.claude/CLAUDE.md を戻し、~/.claude/rules/gas-clasp.md を消す。
- 測り方（反映後）: T5 の値を kgi.md の K9 と baseline.md に記録する（この便の記録の PR で）。

### 28-5. 外部事例

- 公式資料（§28-1 の引用）だけを使う。paths 付きの rules は公式の決まりで、このMacでも coding-style.md 等が既に使っている。ほかの会社の事例は使わない。GAS の4リポジトリはどれも appsscript.json を持つ（crm-app-current/src・ebay-gas-automation/gas/…・tcg-client-viewer/src・tcg-inventory-parser 直下。`find` 2026-10-25）ので、paths の「**/appsscript.json」で当たる（理由: 何を毎回読ませるかは、この PO の決まりの中身で決まり、他社の数字は当てはまらない）。

### 28-6. 残すもの

- K1 の残り約27行（agents.md・git-workflow.md・~/kb/AGENTS.md の見直し）。agents.md:7-17 の一覧と :23-30 の起動条件が名指しする tdd-guide・code-reviewer・security-reviewer 等は、このリポジトリのセッションで使える担当の一覧に無い（見つけたこと。直していない）。
- 案 D（出力の決まり2つのまとめ）。7b 後に 6.5k を超えたときの次の一手。
- 見張り: design 維持の仕組みにある「~/kb/scripts/patrol.sh にユーザー側の合計行数を足す」は ~/kb の変更なので PO の `!` が要る。今回は入れない。

### 28-7. 審査（Architect、同じ AI による自己審査）

- PO の実装承認: 案（§28-3。PO への説明は「古い決まりを1つ消す」「GAS の決まりを GAS の作業のときだけ読む場所へ文言そのまま移す」）を見せた後、PO 原文「1」（2026-10-25）。PO の質問「gasとは？何を変更するのか教えてくれ」に答えてから受けた。実装カード card-stage7.md。

- 判定: **APPROVE**（PO の実装承認の後、card-stage7.md へ進める）。
- 根拠: 消すのは §10-5 で決まった3行だけ。移す GAS の決まりは文言を変えず、公式の paths の決まりで GAS の作業のときに読まれる（T6 で実物を確かめる）。PO の最優先の報告の型は動かさない。1つずつ変えて測る。戻し方は写しを戻すだけ。リポジトリ・本番・CI・Ruleset に触らない。
- 未確認（T で確かめる）: 「**/.clasp.json」のように点で始まる名前に paths が当たるか（appsscript.json でも当たるので T6 はそちらで見る）。推定トークンと実測の差。
- 未解決: なし。K9 が 6.5k に届かない場合は案 D を PO に見せる（推測で進めない）。

### 28-8. 実装の結果（2026-10-25・Sonnet 実装、Opus が生出力で照合）

生出力: /tmp/CC報告ファイル/an-s7/（リポジトリ外）。写し: ~/CC報告ファイル-keep/agenda-nav-stage7-20261025/。

- 【事実】T1 cmp rc=0。T2 diff-7a.txt は `12,14d11` だけ、「AGENTS.md 自動更新ルール」は 0 件。
- 【事実】T3 `tail -n +7 ~/.claude/rules/gas-clasp.md` と写しの :57-73 の diff は rc=0（Opus が写しから直接比べ直した）。gas-clasp.md は 23 行（frontmatter 6 行＋見出し 1 行＋本文 16 行）。
- 【事実】T4 diff-7b.txt は `12,14d11` と `58,73c55`（本文16行→案内1行）だけ。~/.claude/CLAUDE.md は 84 行から 66 行になった。
- 【事実】T5 K9（origin/main c233ec8f6、claude 2.1.310）:

| 測った時点 | Memory files | MEMORY.md | K9 | ~/.claude/CLAUDE.md |
|---|---|---|---|---|
| 変更前（28-1） | 17.7k | 10.6k | 7.1k | 2.7k |
| 7a 後（22:57 JST） | 17.5k | 10.6k | 6.9k | 2.5k |
| 7b 後（22:59 JST） | 17.1k | 10.6k | **6.5k** | 2.1k |

  ほかの行（~/kb/AGENTS.md 1k・git-workflow.md 247・agents.md 907・CLAUDE.md 198・AGENTS.md 2k）は3回とも同じ。7b の一覧に gas-clasp.md は無い。
- 【事実】T6 ~/tcg-inventory-parser で appsscript.json を開いた回（t6-open.txt）は、claude が「appsscript.json を開いたときに自動で読み込まれた gas-clasp.md」と答え、「- ~/.clasprc.json はホームに1つしかない共有ファイル。」を引用した。開かない回（t6-noopen.txt）は「無い」。
- 【未確認】読み込まれたことの根拠は claude 自身の答えと、開かない回との対比だけで、読み込みの記録（ログ）では確かめていない。T6 の2回の終了コード rc=0 は担当の報告だけで、生出力には残っていない。
- 判定: **K9 合格**（6.5k ≤ 6.5k。合格ラインちょうど、余裕は 0.0k）。
- 【事実】K1 はユーザー側 175 行（~/.claude/CLAUDE.md 66・~/kb/AGENTS.md 32・git-workflow.md 24・agents.md 53）＋入口 54 行（AGENTS.md 45・CLAUDE.md 9）＝ 229 行で、200 行以下にまだ 29 行届かない（28-6 の残り。PO に別に相談する）。
- 【未確認】/context の表示は 0.1k 単位の丸めで、6.5k が丸める前にラインの上か下かは分からない。判定は kgi.md の決まり（表示値で判定）に従う。

## 29. 段8 K1 を合格ラインまで減らす（2026-10-26・Opus 設計判断。PO 承認「1」2026-10-26＝案 A のとおり直して測る。起点 origin/main ce48825e5）

PO 承認の経緯: 段7 の完了報告で Opus が「行数を減らす案を作って見せる」を選択肢1として示したのに対し、PO 原文「１」（2026-10-25）。案を直す前に見せ、Opus が「上の案のとおり直して、行数と読み込む量を測る」を選択肢1として示したのに対し、PO 原文「1」（2026-10-26）。

### 29-1. 現在地（【事実】2026-10-26 実測。生出力 /tmp/CC報告ファイル/an-k1/）

- K1 = 229 行（合格ライン 200 行以下。あと 29 行）。内訳: ~/.claude/CLAUDE.md 66・~/kb/AGENTS.md 32・~/.claude/rules/common/git-workflow.md 24・同 agents.md 53・リポジトリの AGENTS.md 45・CLAUDE.md 9。
- ~/.claude/rules/ で paths の無い（常に読まれる）ファイルは agents.md と git-workflow.md の2つだけ（recon/q6_rules_table.txt）。
- agents.md:3-30 は担当9名の表と「必須起動条件」の表。9名のうち tdd-guide・code-reviewer・security-reviewer・build-error-resolver・e2e-runner・refactor-cleaner・doc-updater の7名は、~/.claude/agents/ にもリポジトリにも定義が無い（recon/q1_repo_nine.txt・q2_home_seven.txt）。~/.claude/agents/ に在るのは architect・evaluator・generator・governance・planner・researcher・reviewer の7つ。マージ前の審査で実際に使う reviewer は表に載っていない。
- agents.md:46-53「Multi-Perspective Analysis」の5役も、定義の在る担当ではない。
- 見張り（フック）は agents.md の見出しや担当名を読んでいない（recon/q2_hooks_agentname.txt。agent-console のフック本体は【未確認】：調べる途中で見張りに止められたため）。
- git-workflow.md:12「Attribution disabled globally via ~/.claude/settings.json.」は偽。settings.json に attribution・includeCoAuthoredBy の設定は無い（recon q4）。
- ~/.claude/CLAUDE.md:7 は定義の無い security-reviewer を指している。同名の「/security-review」は Claude Code の組み込みの技能として在る。

### 29-2. 変えること（案 A：おすすめ）

| # | ファイル | 変更前 | 変更後 | 行数 |
|---|---|---|---|---|
| A1 | ~/.claude/rules/common/agents.md | :3-30 担当9名の表と必須起動条件の表（28行） | 5行：「呼べる担当は ~/.claude/agents/ の7名だけ。無い名前を呼ばない」「変更ファイル3つ以上か新規ファイル→planner」「新しい技術・依存追加・DB設計変更→architect」「コードを書いた・直した→マージ前に reviewer の審査（review-gate が強制）」「auth/・*token*・*password*・payment* を触った→/security-review」＋見出しと空行 | −21 |
| A2 | 同 | :46-53 Multi-Perspective Analysis（8行）と直前の空行 | 消す | −9 |
| A3 | ~/.claude/rules/common/git-workflow.md | :12 偽の Note と直後の空行 | 消す | −2 |
| A4 | ~/.claude/CLAUDE.md | :7「security-reviewer を使う」 | 「/security-review を使う」 | 0 |

見込み: K1 229 → 197 行（合格）。

決まりの意味が変わる点（PO の判断が要る点）:
- 「バグ修正・新機能の前に tdd-guide」「CI が落ちたら build-error-resolver」の2行は、担当の定義が無く今も実行できない。代わりの担当を置かずに消す。
- Multi-Perspective Analysis（5役に分けて見る助言）を消す。
- 他は、在る担当名への書き換えと、偽の記述の削除だけ。

### 29-3. 他の案と選ばなかった理由

| 案 | 中身 | 減る行数 | 選ばない理由 |
|---|---|---|---|
| B | agents.md に paths を付け、コードのファイルを開いたときだけ読ませる | −53 | 担当の決まりは作業の種類で要るもので、ファイルの種類と結びつかない。設計の会話では読まれなくなる |
| C | ~/.claude/CLAUDE.md の「出力を省略しない」:38-40 と「生出力はファイルへ」:57-64 を1つにまとめる | −2〜−4 | 単独では足りない。PO 最優先の「報告の型」近くを触る理由が弱い。A で足りるので今回は見送る |
| D | 定義の無い7名を ~/.claude/agents/ に入れる（marketplaces の everything-claude-code から） | 0 | 行数が減らない。担当を増やすのは別の設計判断 |

### 29-4. 触らない範囲

- ~/.claude/CLAUDE.md の「報告の型」:12-32（japanese-reply-guard.py:2,16 と ~/kb/00-rules/chat-format.md:9 が指している）。
- agents.md の Parallel Task Execution・Scope Termination（:32-44）。
- git-workflow.md のコミットの型（根拠がここにしか無い）と PR の手順。
- paths 付きの code-review.md:52,77,78・development-workflow.md:35,42・testing.md:33,40 にも7名の名前が残る。K1 に入らないので今回は触らず、残件として記録する。

### 29-5. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| K1 が 200 行以下 | 29-1 の6ファイルの `wc -l` の合計 |
| K9 が 6.5k 以下のまま | origin/main の使い捨て worktree で `claude -p "/context" --no-session-persistence`、Memory files 合計 − MEMORY.md |
| K7 が残っている | リポジトリの AGENTS.md で「不可逆操作は必ず PO 確認」「VPS 直作業禁止」「直接コミット禁止」を grep し各1件以上（今回触らない） |
| 書き換えた担当名が実在する | agents.md・CLAUDE.md に出る担当名ごとに ~/.claude/agents/<名>.md の有無を ls（/security-review は組み込みの技能） |
| 消した行の一覧が PO 承認の範囲と一致する | 変更前の写しとの diff を保存し、29-2 の表の行だけが変わっていることを照合 |

K11（移した先に在るか）: 今回は移す行が無く、消す行と書き換える行だけなので対象外。消す行は 29-2 に全部書いた。

### 29-6. 戻し方・維持

- 戻し方: 変更前の写しを ~/CC報告ファイル-keep/agenda-nav-stage8-20261026/ に置き、cp で戻す。
- 実施は担当（Sonnet）。リポジトリの外のファイルなので PR の差分には出ない。結果（行数・diff・K9）を本節の後ろと baseline.md に記録する PR を出す。
- 維持: 新しい担当を ~/.claude/agents/ に足したときは agents.md の7名の行も直す（agents.md 自身に書く）。

### 29-7. 外部事例

不要。理由: 自分の環境のファイルに在る、実在しない名前と偽の記述を消す作業で、外部の効果の数字を根拠にしない。行数の効果は 29-5 で直接測る。

### 29-8. 審査（Opus 自己審査。独立の第二者審査ではない）

- 判定: APPROVE（設計として。PO 承認・実施の承認は兼ねない）
- 根拠: 変える行はすべて 29-1 の実測に結びつく。見込み 197 行は A1 −21・A2 −9・A3 −2 の合計で、実施後に wc -l で確かめる。
- 未解決: agent-console のフック本体が agents.md の文言を読んでいないかは【未確認】。実施の直前に担当に grep させ、当たれば止まる。

### 29-9. 結果（2026-10-26 実施。PO 承認「1」2026-10-26＝案 A のとおり直して測る）

実施は担当（Sonnet）。生出力: /tmp/CC報告ファイル/an-k1/s8/。変更前の写し: ~/CC報告ファイル-keep/agenda-nav-stage8-20261026/。

| 基準 | 結果 | 根拠 |
|---|---|---|
| K1 が 200 行以下 | **197 行**（66・32・22・23・45・9）で合格 | s8/k1_wc.txt |
| K9 が 6.5k 以下のまま | Memory files 16.8k − MEMORY.md 10.7k ＝ **6.1k** で合格 | s8/k9_context.txt の Memory files 表 |
| K7 が残っている | 3語とも各1件 | s8/k7.txt |
| 書き換えた担当名が実在する | ~/.claude/agents/ に7名の .md あり。/security-review は組み込みの技能 | s8/agents_ls.txt |
| 変わった行が承認の範囲と一致 | agents.md は 29-2 の A1・A2 の範囲だけ、git-workflow.md は2行削除だけ、CLAUDE.md は7行目だけ | s8/diff_agents.txt・diff_git.txt・diff_claude.txt（Opus が diff_agents.txt を読んで照合） |

- 【事実】事前点検（29-8 の未解決点）: ~/.claude/scripts・~/.claude/hooks・agent-console（*.mjs *.js *.json）で、外した文言を読む行は0件（s8/pre_grep.txt）。担当の Bash からは agent-console の見張りに止められたため、Opus 本体で実行した。
- 【事実】担当は K9 を「前回 6.5k から +10.3k」と報告したが、これは MEMORY.md を含めた合計との比較で、K9 の定義（MEMORY.md を除く）では 6.1k。Opus が表示値で計算し直した。
- 残件（範囲外）: paths 付きの code-review.md・development-workflow.md・testing.md に定義の無い担当名が残る（29-4）。

## 30. 全条件の測り直しと K5 の直し（2026-10-26）

- 30-1 PO 原文「1」（2026-10-26。テーマの合格条件を全部測り直して完了を判定する）を受け、origin/main 9351f2158 で全項目を測った。K1 197行・K2 0/5（関係ある例文 2/2）・K3 0語（grep では「日本語」が2本に出るが §25 の判断どおり別の決まり）・K4 0・K6 100%・K7 残っている・K9 6.1k・K11: 一字一句の照合で 160/186。残り26行を意味で1行ずつ照合し、在る 18・見出しや表の枠 7・欠けている 1 だった（CC報告ファイル-keep/agenda-nav-final-20261026/an-k11sem/table.md）。欠けている1行（CLAUDE.md:92 の「grep セルフチェック」の参照）は、段4より前の frontend/CLAUDE.md で ESLint の自動検出に置き換わっていて、その本文は frontend/AGENTS.md:23-29 に在るので「在る」と判定し直した。さらに2点が移した先に無く、別の文書にだけ在った（ADR 一覧を作り直した後のコミットと CI 必須、ブランチ名を英語で簡潔に）。この2点は §30-6 で移した先に戻した（GAS 16/16）・K12 12/20・K10 9/20（参考）で合格、K5 だけ最深4段で未達。
- 30-2 K5 の原因（親をたどって確認）: docs/ai-agents/adr-template.md は AGENTS.md → docs/adr/README.md → ADR-150 → docs/handoff/agent-complete-design/recon.md 経由でしか届かない（4段）。docs/specs/ledger-guard/README.md は docs/INDEX.md → docs/specs/README.md → docs/specs/dev-continuity/README.md 経由（4段）。どちらも目次・索引に行が無かった。
- 30-3 直し（PO 原文「1」2026-10-26）: docs/INDEX.md に adr-template.md の行、docs/specs/README.md に ledger-guard の行を「いつ読むか」付きで1行ずつ足した。
- 30-4 結果: 検査の最深段数 4 → 3、deep 2 → 0。生出力 /tmp/CC報告ファイル/an-k5/。
- 30-5 戻し方: このPRを revert する。
- 30-6 審査の差し戻し（K11 の数に裏づけが無い）を受け、移した先に無かった2点を戻した: docs/INDEX.md の ADR 一覧の行に「作り直してコミットする。CI「ADR index is up to date」が必須」、AGENTS.md の作業場所の行に「<topic> は作業内容を英語で簡潔に」。これで26行はすべて移した先かその入口に在る（K11 186/186）。生出力は CC報告ファイル-keep/agenda-nav-final-20261026/。

## 31. 段1c 見張りの免除を部分一致から「決まった場所で始まる」に締める（2026-10-26・Opus 設計判断。PO 原文「1」に続けて「,2」2026-10-26＝テーマの外の残り4件をまとめて計画して進める。その3件目 C。起点 origin/main 2d25c719d）

- 31-1 目的: 商品マスタ登録の見張り（scripts/agent-hooks/master-register-rules-guard.py）は、Write/Edit の保存先にリポジトリの段の名前（/docs/ など）や記録の置き場の名前がパスのどこかに含まれれば素通りさせる（:23 `EXEMPT_PATHS` と :66 の部分一致）。段1b で置き場2か所を足したときの審査で、リポジトリの外の ~/x/docs/a.py や置き場に置いた台本 /tmp/CC報告ファイル/x.py（どちらも試験 T22・T23 の例のパス。実在しない）も素通りになることが分かった。登録の命令を書いた台本が見張りを通らずに作れるので、免除を本来の場所だけに締める。
- 31-2 現在地（origin/main 2d25c719d）: :14 `REPO`、:23 `EXEMPT_PATHS`、:66 の判定。`EXEMPT_PATHS` を使う見張りはこの1本だけ（ほかはホームの本体と、その .bak・.new の写し）。試験 T1〜T21 は CI で動かない（.github/workflows/agent-hooks-test.yml:24 は review-gate の試験だけ）。ホームの本体と origin/main の版は同じ（diff 0）。作業場所の置き場は scripts/new-worktree.sh:13 の `~/worktrees/salesanchor/<ブランチ名>/`。
- 31-3 決めたこと: パスを `os.path.normpath` で整えた後に、①`REPO` の直下か `~/worktrees/salesanchor/<名前>/` の直下で、最初の段が backend・frontend・docs・migrations・tests のどれか、②`~/CC報告ファイル-keep/`・`/tmp/CC報告ファイル/`・`/private/tmp/CC報告ファイル/` で始まり .md か .txt で終わる、のどちらかのときだけ素通りさせる。絶対パスでないものは免除しない。
- 31-4 代替案と採らなかった理由: (a) 置き場の免除をやめる → 段1b の誤作動（調査メモの保存が止まる）が戻る。(b) 拡張子を見ず場所だけで締める → 置き場の台本が素通りのまま残る。(c) `os.path.realpath` でつなぎ先までたどる → まだ無いファイルや Mac の /tmp のつなぎで結果が場所ごとに変わる。/tmp と /private/tmp を両方書く方が試験で確かめやすい。
- 31-5 リスクと対処: 作業場所の名前が `~/worktrees/salesanchor` 以外の置き場で作られると、そこの docs への保存が止まる（印を書けば通る＝安全側）。試験 T3 は `CLAUDE_PROJECT_DIR=/repo` を置いて今までの意味を保つ。
- 31-6 受け入れ基準と検証: card-stage1c.md §7 の表（T22〜T28 の追加と、元の部分一致に戻すと T22・T23・T25 が落ちること）。ホームの本体へは PO が `!` で写し、diff の `SAME` で確かめる。
- 31-7 戻し方: PR を revert し、本体は .bak から戻す。
- 31-8 外部事例: 該当なし（この Mac の見張り1本の判定の締め直しで、外の事例の数値が判断を変えないため）。
- 31-9 自己審査（Architect 役・同一 AI）: APPROVE。理由: 触る場所は1ファイルの3か所と試験だけ。今までの試験21本の意味は変えない。締めた後の判定は試験7本で両側（素通り・止まる）を確かめ、元に戻すと落ちる試験も置いた。未解決事項なし。

## 32. 合格した状態を続ける仕組み（定着化）（2026-10-26・Opus 設計判断。設計審査済み（審査6回目 APPROVE on d2f244d70）。PO 実装承認 2026-10-26（PO 原文「1」＝M1〜M3 を作り始める。M4 は PO 本人の操作）。起点 origin/main 840eea949）

- 32-1 PO 原文（2026-10-26）:「この仕組みを標準化して管理定着させて継続させるための仕組みも出来ているか事実ベースでエビデンスを確立してくれ」。目的: K1〜K12 の合格（§30）が、この先の変更で崩れたら自動で止まるか、遅くとも1週間以内に担当へ知らせが届く状態にする。例外は2つ: K12 は90日ごと（D4）、K11 は続けて測らない（D5）。

### 32-2 現在地（governance 検証 2026-10-26・origin/main 840eea949。生出力 /tmp/CC報告ファイル/an-gov/。リポジトリ外）

| 項目 | 今ある仕組み | 必須チェックか | 判定 |
|---|---|---|---|
| K1（リポジトリ内） | .github/workflows/check-claude-size.yml:12 → frontend/scripts/check-claude-size.js:24-34（AGENTS.md 80・CLAUDE.md 10） | 必須（ruleset id 15777895） | 1本ずつの上限は守られるが、合計200行は守れない（上限いっぱいの 80＋10＋外 143＝233行まで CI は通る） |
| K1（リポジトリ外: ~/.claude/CLAUDE.md 66・~/kb/AGENTS.md 32・~/.claude/rules/common/agents.md 23・git-workflow.md 22） | 無い（~/kb/scripts/patrol.sh:12-47 は行数を数えない） | — | 穴。合計 197 行で上限 200 まで残り3行 |
| K2 | scripts/agent-hooks/test_master_register_rules_guard.sh はあるが CI から呼ばれない（.github/workflows/agent-hooks-test.yml:24 は review-gate だけ）。ホームの写しのずれ検知も無い | — | 穴 |
| K3 | 無い | — | 穴 |
| K4・K5・K6 | .github/workflows/doc-index-reachability.yml:26（`--strict` なし＝失敗しない。docs/handoff/doc-agenda-nav/check_doc_index.py:209-210）。pull_request だけ（:6-8） | 必須でない | 警告だけ。直近の実行6回（PR 3本）は警告 0。今の main で `--strict` を付けても exit 0（審査役の実行） |
| K7 | 無い（§維持の仕組みに予定として書いたが check_doc_index.py に実装なし） | — | 穴 |
| K9・K12 | 人が測る。合格後の測り直しの時期・担当の記載が無い（design.md:41・:331 は段ごとだけ） | — | 穴 |
| K11 | 人が照合（186/186） | — | 下の 32-3 D5 |
| 文書 | ADR-1040 に維持の節が無い。「強制の仕組み」表の到達検査が「段2で新設」のまま。本文 §維持の仕組みの「まだ存在しない」が実物と食い違う | — | 古い |

### 32-3 決めたこと（5つ）

- D1 目次の検査を「落とす」検査にする（K4・K5・K6・K7・K3）
  - check_doc_index.py を scripts/ci/check_doc_index.py へ移す（docs/handoff は引き継ぎの置き場。CI の部品を置かない）。元の場所には何も残さない（実行する呼び出し元は doc-index-reachability.yml:26 の1か所だけ）。スクリプト自身の使い方の行（:4）も新しいパスに直す。過去の card の中の旧パスは記録なので直さない。
  - 同じスクリプトに2つの検査を足す。(a) K7: AGENTS.md に「不可逆操作は必ず PO 確認」「VPS 直作業禁止」「直接コミット禁止」が各1件以上、CLAUDE.md・frontend/CLAUDE.md・backend/CLAUDE.md に 「@AGENTS.md」 の行が各1件。(b) K3: design.md:444（本節の上の「K3 の測り方」）の9語（i18n・ハードコード・不可逆・推測・executor-preflight・squash・worktree・日本語・file:line）を、CLAUDE.md・AGENTS.md・frontend/AGENTS.md・backend/AGENTS.md・frontend/CLAUDE.md・backend/CLAUDE.md で数え（grep -F 相当）、2ファイル以上に出る語を数える。今の main で2本以上に出るのは「日本語」だけ（frontend/AGENTS.md:23,24,31・backend/AGENTS.md:66。審査役の実測）。除外は語ごとではなく「ファイル:決まった文言」の組で、§25 の判断（別の決まり）を理由に書く（同じ語がほかの文言で別のファイルに増えたら検出される）。落とす決まり: ある語が2ファイル以上に出て、かつその出現のうち除外の組に当たらないものが1つでもあれば、その語を重複として数える（除外した行を先に取り除いてから数えるのではない）。結果は SUMMARY に `dup_words=<数>`、K7 は `safety_missing=<数>`・`agents_import_missing=<数>` として出し、`--strict` で 0 でなければ exit 1。語と除外の表はスクリプトの先頭に置く（正本は1か所）。旧案（本文 §維持の仕組み）の「CLAUDE.md↔AGENTS.md の見出し重複」は、CLAUDE.md が10行上限で 「@AGENTS.md」 だけになったので K7 の 「@AGENTS.md」 行の検査と行数検査で代える。
  - workflow を `--strict` で動かし、job 名から「(warning only)」を外す。動く時機に `push: branches: [main]` と毎週月曜の `schedule` を足す（PR を通らない変更も拾う）。
  - 必須チェックへの登録は D1 の PR が main で緑になった後に別の操作で行う。Ruleset の変更は CLAUDE.md の不可逆操作の一覧に入り、同意票（ADR-1033）では通せない（ADR-1033:20・conversation-consent/design.md:115 が除外、AGENTS.md:17-19）。PO が `!` で `bash scripts/permit-danger.sh "<op>"` を打った後に Opus が読み取りで確かめながら登録するか、PO が GitHub の画面で登録する。登録しない間も、マージの手順（CI 失敗 0 を確かめてからマージ）で止まる。
- D2 商品登録の見張りの試験を CI で動かす（K2）
  - agent-hooks-test.yml に job「master-register guard test」を足し、test_master_register_rules_guard.sh を動かす。paths には docs/specs/product-master/registration-rules.md だけを足す（見張り本体は既存の `scripts/agent-hooks/**`（:10）に入っている）。
  - 前提（事実）: test_master_register_rules_guard.sh は macOS の写しで 28件すべて PASS・rc=0（審査役の実行 2026-10-26）。段1c で NG だった T1 は別の試験（scripts/agent-hooks/cloud/test.sh の時間切れ試験。card-stage1c.md:652）で、この job には入れない。Linux（CI）では未実行なので、M2 の PR の CI の結果で確かめる。CI で落ちたら担当は原因を調べ、試験側の環境差（パス・python の版）なら同じ PR で直す。見張り本体の判定が変わる直しは止めて Opus に返す。
- D3 リポジトリの外を毎週点検する（K1 外・K2 の写し・K9・D1 の CI の最新結果・点検どうしの見張り）
  - 新しいスクリプト scripts/dev/doc-entry-weekly-check.sh（読むだけ）。定期実行は、`git -C ~/salesanchor fetch -q origin` の直後に origin/main の使い捨て写し（`git worktree add --detach`。作業場所の札を残さない）を作り、その写しのスクリプトを動かして、終わったら写しを消す（本店の写しは古く、スクリプトが無いため）。
  - 出す行（1項目1行・`名前=値`）:
    - `K1=<合計>`: 数える範囲は kgi.md の K1 の行の定義（:22）のとおり。~/.claude/CLAUDE.md、そこから `@` で取り込むファイル（今は ~/kb/AGENTS.md）、~/.claude/rules/ の .md のうち先頭の `---` で囲まれた部分に `paths:` が無いもの（今は agents.md・git-workflow.md）、写しの CLAUDE.md・AGENTS.md。各ファイルを `wc -l` で数えて足す。範囲に入れたファイル名も `K1_FILES=` に並べる。
    - `K2_COPY=SAME|DIFF`: ~/.claude/scripts/master-register-rules-guard.py と写しの scripts/agent-hooks/master-register-rules-guard.py を cmp。
    - `K9=<値>k|unreadable|skipped`: 写しで `claude -p "/context" --no-session-persistence`（baseline.md:147・design.md:603 と同じ条件）を実行し、MEMORY.md を除く Memory files の表示値。
    - `DOC_INDEX_CI=success|failure|pending|none`: `gh run list --workflow doc-index-reachability.yml --branch main -L 1 --json status,conclusion` の最新。実行中は pending（NG にしない。次の週に見る）。
    - `K12_LAST=<YYYY-MM-DD>` と `K12_DUE=yes|no`: baseline.md の見出しのうち `## 全条件の測り直し（YYYY-MM-DD）` の型だけを拾った日付の最大値（今は :245 の1本。「段8 の後の測り直し」などは拾わない）。今日から90日を過ぎたら yes。
    - `K12_OPEN_PR=<URL>|none`: `$DOC_ENTRY_GH pr list --state open -L 200 --json headRefName,url -q '.[]|select(.headRefName|startswith("release/doc-entry-k12-"))|.url'` の1件目（`--head` は枝名の完全一致しか拾わないため使わない。審査5回目の実測）。RESULT の判定には使わない。
    - `PEER_LAST=<YYYY-MM-DD>`: 「同意と権限の週次点検」の保存先 ~/CC報告ファイル-keep/consent-weekly/ のうちファイル名が `^[0-9]{8}\.txt$`（YYYYMMDD.txt。今は 20261026.txt）に合うものの一番新しい日付（ファイル名から読む。更新時刻は使わない。「-guard-blocked-analysis.md」 などの付属ファイルは拾わない）。
    - 最後の行 `RESULT=OK` か `RESULT=NG <理由>`。NG にするのは K1>200・K2_COPY=DIFF・K9 が 6.5k 超か unreadable・DOC_INDEX_CI=failure・PEER_LAST が今日から7日以上前（日付の差。正常なら同じ日の 14:00 の分で0日）、のどれか。K12_DUE=yes だけでは NG にしない（D4 で扱う）。合格の線（200・6.5k・90日・7日）はスクリプトの先頭に置く（kgi.md の値の写しであることを注記）。
  - 差し替えの口（試験用。既定は本物）: `DOC_ENTRY_HOME`（既定 $HOME）、`DOC_ENTRY_REPO`（既定 スクリプトの2つ上＝写しの根）、`DOC_ENTRY_GH`（既定 gh）、`DOC_ENTRY_TODAY`（既定 今日 YYYY-MM-DD）、`DOC_ENTRY_SKIP_K9=1`（K9 を `skipped` にし RESULT の判定から外す）。試験 scripts/dev/test_doc_entry_weekly_check.sh で 32-6 の各場合を一時ディレクトリと偽の gh で確かめる（本物の ~/.claude には触れない）。
  - agent-console の定期実行を1本足す（`ac-routine.mjs add`。役割 opus-designer の Opus 本体が打つ。README v0.47.1「ac-routine の使い方」。名前「入口の文書 週次点検」・月曜 16:00・closeWhenIdle true。月曜の有効な定期実行は 09:00・12:00・14:00（Opus が routines.json を 2026-10-26 に読み取り）で、60分未満は関門で拒まれるため 16:00）。定期実行の手順: スクリプトを動かし出力を ~/CC報告ファイル-keep/doc-entry-weekly/<YYYYMMDD>.txt に保存し、全文を読む。RESULT=OK かつ K12_DUE=no なら「入口の文書 週次点検 異常なし（<パス>）」の1行だけを返して終える（closeWhenIdle で閉じる）。RESULT=NG なら PO へ3行の型で報告し、最後の行に `NEEDS_DECISION: 入口の文書 週次点検 NG` を書く（README v0.47.1: 最後の返答に NEEDS_DECISION: があれば閉じずに残す）。K12_DUE=yes なら D4 の手順に進む。
  - 点検どうしの見張り: 「同意と権限の週次点検」（月曜 14:00、既存）の手順に1項目足す（`ac-routine.mjs update`。Opus 本体）: ~/CC報告ファイル-keep/doc-entry-weekly/ のうちファイル名が `^[0-9]{8}\.txt$` に合うものの一番新しい日付が今日から8日以上前なら異常として報告する（正常なら前の週の月曜 16:00 の分で7日。14:00 の点検は 16:00 より先に動くため、こちらは8日を線にする）。逆向きは上の PEER_LAST。知らせが出るまで: 同意の週次点検が止まったら、同じ日の 16:00（約2時間後）。入口の週次点検が止まったら、次の月曜 14:00（約7日後）。どちらも32-1 の「遅くとも1週間以内」に入る。
- D4 人が測る項目の時期を決める（K12）
  - K12_DUE=yes のとき、定期実行の会話（Opus、この Mac）が次の順で進める。
    1. 同じ週に RESULT=NG なら測らない。最後の行は D3 の `NEEDS_DECISION: 入口の文書 週次点検 NG` だけにする（直してから次の週に測る。NG を先に扱う）。
    2. 二重に測らない: スクリプトの `K12_OPEN_PR` が none でなければ測らず、最後の行を `NEEDS_DECISION: K12 測り直し PR マージ待ち <その URL>` にする。
    3. k12-tasks.md の手順（runall.sh。これまでと同じユーザー設定の条件）で測り直す。生出力は ~/CC報告ファイル-keep/doc-entry-weekly/k12-<YYYYMMDD>/ に保存（ファイル名の型 `^[0-9]{8}\.txt$` に合わないので見張りの日付には混ざらない）。
    4. `bash scripts/new-worktree.sh release/doc-entry-k12-<YYYYMMDD>`（origin/main 起点。AGENTS.md:34）で作業場所を作り、結果を `## 全条件の測り直し（YYYY-MM-DD）` の見出しで baseline.md に追記する docs だけの PR を起票する（docs/handoff は危険パスではない）。
    5. 同じ会話で、通常の手順（reviewer を model opus で新規起動して APPROVE・CI 失敗0・「確認済み：」コメント）を済ませてマージする。マージできたら K12_LAST が進むので、次の週は K12_DUE=no に戻る。
    6. 最後の行: 10/20 以上でマージ済みなら `K12 測り直し 合格 <点>/20 <PR の URL>` の1行で終える（closeWhenIdle で閉じる）。10/20 未満なら PO へ3行の型で報告し、最後の行を `NEEDS_DECISION: K12 未達 <PR の URL>` にする（PR は記録として手順5どおりマージする。K12_LAST は進むが、未達の扱いは PO の判断に委ねるので次の知らせは90日後でよい）。審査が REVISE か CI が赤でマージできなければ、最後の行を `NEEDS_DECISION: K12 測り直し PR マージ待ち <URL>` にして会話を残す。
  - クラウドで測る案は、ユーザー設定が無く条件が変わり前の値と比べられないので採らない。
- D5 K11 は続けて測らない
  - 理由: K11 は「入口から外した行が移した先に在るか」を移す段ごとに確かめる条件で、移す段（段3a〜段8）は終わった。この先は新しく移さない。入口に必ず残す決まりは D1(a) の K7 で、目次から届くことは D1 の K4 で毎回確かめる。今後また入口から決まりを移すときは、その段の設計に K11 の照合を書く（ADR-1040 の維持の節に書く）。

### 32-4 文書の直し（その時点の実物だけを書く。便ごとに足す。ADR-1040 を直す便は毎回 `node scripts/generate-adr-index.js` を回し、差が出たら同じ PR に入れる）

- M1: ADR-1040 に「維持の仕組み」の節を足し、「強制の仕組み」表の到達検査の行を実物に合わせる（scripts/ci/check_doc_index.py・`--strict` で失敗する・必須チェックではない）。本文 §維持の仕組みの「追加予定の守り手（…まだ存在しない）」を実物の名前と §32 への参照に書き換える。docs/STANDARD-WORKFLOW.md に1行: 「新しい手順書・仕様書は docs/INDEX.md か docs/specs/README.md に『いつ読むか』付きで1行足す（CI『doc index reachability』で止まる）」。kgi.md の運用方針に「合格後の点検: design.md §32」を1行。`node scripts/generate-adr-index.js` を回す。
- M2: ADR-1040 の「強制の仕組み」表に「登録の見張りの試験 CI（agent-hooks-test.yml の job）」の行を足す。
- M3: 同じ表に「週次点検（scripts/dev/doc-entry-weekly-check.sh・定期実行『入口の文書 週次点検』）」の行を足し、本文 §維持の仕組みの「リポジトリ外の守り手（段7で新設案）」を書き換える。kgi.md の運用方針に「K12 を測り直したら baseline.md に `## 全条件の測り直し（YYYY-MM-DD）` の見出しで書く」を1行。
- M4: PO の登録操作の後、Opus が起票する別の docs だけの PR で、到達検査の行の「必須チェックではない」を「必須チェック（ruleset 15777895）」に直す。

### 32-5 便の分け方（1便＝1PR。変えたら測ってから次へ）

| 便 | 中身 | 危険な場所に触るか |
|---|---|---|
| M1 | D1（スクリプト移動・K3/K7 の検査・--strict・時機の追加）＋ 32-4 の M1 | 危険パス `scripts/`（scripts/check-process-artifacts.js:117）・docs/STANDARD-WORKFLOW.md（同 :121）→ PR 本文に `### GO記録`（ADR-136。GO は委任に基づく Opus 発行・ADR-1003）。CI の workflow（workflow-lint.yml ではない） |
| M2 | D2（試験 job を足す）＋ 32-4 の M2 | CI の workflow。試験を直すなら危険パス `scripts/` → GO記録 |
| M3 | D3・D4（週次点検スクリプトと試験）＋ 32-4 の M3。マージ後に Opus が定期実行を1本足し、同意の週次点検の手順を直す | 危険パス `scripts/` → GO記録。agent-console の定期実行（Opus の許可範囲。README v0.47.1「ac-routine の使い方」） |
| M4 | 必須チェックへの登録（Ruleset の変更。PR ではなく PO の操作）。その後 32-4 の M4 を docs だけの PR 1本で | **不可逆操作の一覧に入り、同意票では通せない（ADR-1033:20）。GO 委任の例外（ADR-1003:31-38）。PO 本人が `!` で permit-danger.sh を打つか画面で操作する** |

### 32-6 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| K4・K5・K6 が崩れたら PR が赤になる | M1 の PR で、目次から1行消した使い捨ての確認用コミットで job が失敗し、戻すと成功する（2回の実行の URL を記録） |
| K7 が崩れたら赤になる | 同じく AGENTS.md の「VPS 直作業禁止」を消したコミットで失敗、戻すと成功 |
| K3 が崩れたら赤になる | 同じく AGENTS.md（ルート。45行・上限80）に「i18n」の本文を1行足したコミットで job「doc index reachability」が失敗（`dup_words=1`）、戻すと成功（今 i18n は frontend/AGENTS.md の1本だけ。backend/AGENTS.md は70行で上限70なので行数検査まで赤になり判定が混ざる） |
| 除外が語ごとでない | 同じく AGENTS.md（ルート）に「日本語」を含む別の文言を1行足したコミットで job「doc index reachability」が失敗 |
| 今の main で全部合格 | M1 の最終 HEAD で job 成功・`SUMMARY` の全項目 0 |
| 登録の見張りの試験が CI で動く | M2 の PR で job「master-register guard test」成功。試験を1本わざと壊したコミットで失敗 |
| 週次点検が今の値を正しく出す | (a) M3 の PR で test_doc_entry_weekly_check.sh が全件 PASS: 一時ディレクトリで K1 の範囲（paths ありの rules は数えない）・DIFF で NG・`## 全条件の測り直し（<DOC_ENTRY_TODAY の91日前>）` で K12_DUE=yes かつ RESULT は OK のまま・同じ日の後に「段8 の後の測り直し（新しい日付）」を足しても K12_DUE=yes・偽の gh が failure で NG・pending で OK・consent-weekly に `<7日前>.txt` だけなら NG・偽の gh が headRefName `release/doc-entry-k12-20270101` の PR を返すと `K12_OPEN_PR=<その URL>`・`release/other` だけなら none・`<6日前>.txt` なら OK・`<7日前>.txt` と 「<今日>-guard-blocked-analysis.md」 なら NG（付属ファイルを拾わない）（K9 は DOC_ENTRY_SKIP_K9=1）。(b) M3 マージ後に Opus 本体が本物で1回動かし、K1 がその時に別に `wc -l` で数えた同じ範囲の合計と一致・K2_COPY=SAME・K9 がその時に同じ条件で手で取った `/context` の値と一致・RESULT=OK |
| 定期実行が登録された | Opus 本体が `ac-routine.mjs list` を打ち（担当からは見張りで止まる）、「入口の文書 週次点検」enabled true・月曜 16:00 を確かめる。月曜の有効な定期実行は 09:00・12:00・14:00（Opus が routines.json を 2026-10-26 に読み取り） |
| 点検どうしの見張り | Opus 本体が `ac-routine.mjs list` で「同意と権限の週次点検」の指示文に doc-entry-weekly の「8日以上前なら異常」の項目が入ったことを確かめる |
| 必須になった | M4 の後、ruleset id 15777895 の required checks に「doc index reachability」がある（読み取りの gh api） |
| 文書が実物と合う | 各便のマージ後、ADR-1040 の「強制の仕組み」表の各行のファイルが origin/main に在る（git ls-tree）。その便でまだ作っていない仕組みの行が無い |

- 32-7 リスクと対処: (1) `--strict` で他のセッションの PR が赤になる → 直近の PR 6回で警告 0、規則も各表の「追加のしかた」に書いてある。赤になった PR は目次に1行足せば通る。(2) K3 の語の数え方が誤検出する → M1 で今の main が 0 になることを受け入れ基準にする。誤検出の語は除外の表に理由つきで足す。(3) 週次点検の `claude -p "/context"` は Claude の版で表示が変わりうる → 読み取れなければ RESULT=NG（値が取れない）として知らせる（黙って合格にしない）。(4) M2 の試験が Linux で落ち、原因が見張り本体だった場合 → M2 を止めて Opus が別に設計する。(5) K1 は CI では1本ずつの上限しか見ないので、合計が200行を超えても最長1週間は知らせが来ない → 週次点検で拾う（目的の1週間以内に入る）。1本ずつの上限を合計から逆算して絞る案（AGENTS.md 47行＝200−外143−CLAUDE.md 上限10）は、PO が決めた入口の上限（ADR-1040 Decision・90行）を変えるので採らない。 (6) agent-console 全体か Mac が止まると、両方の定期実行が止まり、点検どうしの見張りも働かない。これは本節の範囲外（agent-console 停止の見張りは別テーマ）として残る。
- 32-8 代替案と採らなかった理由: (a) ~/kb/scripts/patrol.sh に行数を足す（§維持の仕組みの旧案）→ ~/kb の記録は PO が `!` で打つ決まり（~/kb/AGENTS.md「検査」）で、PO の手が毎回要る。agent-console の定期実行は Opus が足せる。(b) K12 も毎週測る → 1回 20 実行の費用がかかり、入口の文書は毎週は変わらない。90日ごとにする。(c) 必須チェック登録を先にする → `--strict` 化の前に登録しても警告だけなので意味が無い。
- 32-9 戻し方: 各便の PR を revert。定期実行は `ac-routine.mjs disable <id>`。必須の登録は、PO が `!` で permit-danger.sh を打った後に外すか、PO が画面で外す。
- 32-10 外部事例: 該当なし（この会社の CI と手元の定期実行の組み合わせで、外の事例の数値が判断を変えないため）。
- 32-15 審査5回目（審査役 model opus・新規起動・4f4030598）: REVISE（直すべき N1-b・任意 P-a〜P-d。N1 の残り以外と O-a〜O-e は解消、見張りの日付計算も誤報なし・1週間以内と確認）。生出力 /tmp/CC報告ファイル/an-gov/review5/。反映: N1-b→開いている測り直し PR の確認をスクリプトの `K12_OPEN_PR`（枝名の頭で判定。`--head` は完全一致のみ）に移し、32-6 の試験で確かめる、P-a→`<7日前>.txt`＋付属ファイルで NG の組、P-b→10/20 未満でも記録としてマージし PO へ NEEDS_DECISION、P-c→手順4に new-worktree.sh、P-d→M4 の文言の重複を削った。
- 32-14 審査4回目（審査役 model opus・新規起動・040c241b6）: REVISE（直すべき N1・任意 O-a〜O-e。R1〜R4・O1〜O5 は解消と確認、実物との照合はすべて一致）。生出力 /tmp/CC報告ファイル/an-gov/review4/。反映: N1→D4 を6手順にし、NG を先に扱う・開いている測り直し PR があれば測らない・同じ会話で審査と CI を済ませてマージ・マージできなければ NEEDS_DECISION で残す、O-a→日付はファイル名 `^[0-9]{8}\.txt$` から読み付属ファイルを拾わない・保存名を YYYYMMDD に揃えた、O-b→入口側は7日以上・同意側は8日以上で、どちらの停止も1週間以内に知らせる、O-c→32-5 の各便に 32-4 の該当分を明記・M4 は PO 操作＋docs PR 1本、O-d→ADR を直す便は毎回目次を作り直す、O-e→32-7 の番号順。
- 32-13 審査3回目（審査役 model opus・新規起動・d81980f46）: REVISE（直すべき R1〜R4・任意 O1〜O5）。生出力 /tmp/CC報告ファイル/an-gov/review3/。反映: R1→D3 の出す行と RESULT の決まり（K12_DUE は NG にしない）・定期実行の返し方・D4 は定期実行の会話が測って PR まで、R2→32-4 を便ごとに分けた、R3→差し替えの口5つと試験スクリプト、R4→点検どうしの見張り（相互）と残るリスク (6)、O1→範囲は kgi.md:22・先頭の --- の中、O2→47行、O3→:4 の行、O4→pending、O5→K3 の確かめをルートの AGENTS.md に。README v0.47.1 の closeWhenIdle と NEEDS_DECISION の扱いは Opus 本体が読み取りで確かめた（担当は見張りで読めない）。
- 32-12 審査2回目（審査役 model opus・新規起動・e25bc27f8）: REVISE（直すべき A〜D・任意 E〜G・S1 の残り）。生出力 /tmp/CC報告ファイル/an-gov/review2/。反映: S1 残り→32-5 M4 行、A→時刻を 16:00 にそろえた、B→落とす決まりと9語の正本（design.md:444）を D1(b) に、C→K12 の見出しの型を固定し定期実行は知らせるまでに絞った（測るのは Opus がこの Mac で）、D→受け入れ基準を「その時に別に測った値と一致」に、`--no-session-persistence` を足した、E→SUMMARY の項目名、F→M1 に STANDARD-WORKFLOW.md、G→確かめるのは Opus 本体。
- 32-11 審査1回目（審査役 model opus・新規起動・50a359da8）: REVISE（止めるべき2・直すべき5・任意6）。生出力 /tmp/CC報告ファイル/an-gov/review/（リポジトリ外）。反映: S1→D1・32-9 を permit-danger.sh か画面操作に、S2→D2 の前提を事実どおりに、R1→K3 の試験を backend/AGENTS.md に、R2→除外を「ファイル:文言」の組に、R3→32-5 に危険パスと GO記録、R4→32-2 の K1 の判定と 32-7(5)、R5→D3 の写し・④⑤・受け入れ基準・32-1 の例外。任意: paths・6回の内訳・行番号・見出し重複を反映。tools/claude-channels/intake/CLAUDE.md の LIMITS 未登録は K1 の対象外（入口ではない）で、本節では扱わない。ADR-1040 を直す M1 では `node scripts/generate-adr-index.js` を回す。
