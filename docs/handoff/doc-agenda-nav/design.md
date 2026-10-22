---
mode: handoff
adr: 未起案（段0で起案。ADR-076 を改める形か新規かは段0で決める）
status: 草案（Opus 審査 REVISE・PO 判断7件待ち・PO 未承認）
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
| KGI-1 | 会話開始時に自動で入る行数（ユーザー側＋プロジェクト側の指示＋rules。MEMORY.md を除く） | 313行/12,992字 | **200行以下** | raw/autoload-sizes.txt と同じコマンド（wc -l -m）を実行し合計 |
| KGI-2 | 関係ない入力（raw/prompt-regex-test.txt の無関係例文5本）で商品マスタ登録ルールが注入される回数 | 5/5 | **0/5**（関係あり例文2本は 2/2 のまま） | python3 -I で正規表現に例文を通す（同ファイルの手順） |
| KGI-3 | 同じ決まりが2ファイル以上に本文として書かれている件数（recon §2-4 の9語） | 9語すべて複数ファイル | **プロジェクト側（CLAUDE.md/AGENTS.md/frontend/backend）で 0 語**（ユーザー側 ~/.claude は本便の範囲外） | raw/duplicates.txt と同じ grep |
| KGI-4 | 入口から目次を辿って届かない docs/specs・docs/ai-agents の文書数 | specs 35・ai-agents 19 | **0** | raw/reachability.txt と同じ幅優先探索（CI 化後は CI の出力） |
| KGI-5 | 入口から末端ページまでの段数 | 最深14段 | **入口→目次→章→末端 = 3段以内**（docs/handoff は対象外） | 同上の depth 出力 |
| KGI-6 | 目次の各項目に「いつ読むか」1行が付いている割合 | 索引 docs/specs/README.md は状態列はあるが「いつ読むか」列なし | **100%** | 目次ファイルの表に「いつ読むか」列が空欄なし（CI で空欄を数える） |
| KGI-7 | 安全の決まり（不可逆操作・PO 確認・VPS 鍵制限）が入口に残っているか | CLAUDE.md:28-40 に在る | **入口に残る（移さない）** | CLAUDE.md の該当見出しの存在を grep |

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
会話開始（自動）= 入口のみ
 └ CLAUDE.md ≤ 90行
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
   AGENTS.md = @CLAUDE.md 相当の薄い入口（Codex 用。本文を持たない）
入力のたび: 「マスタ…登録」が同じ文に共起したときだけ注入（KGI-2）
```
段数: 入口(0)→目次(1)→章(2)→末端(3)。KGI-5。

## 5. 各文書の行き先（複製なし。移すときは元に「→目次」のリンクだけ残す）

| 文書 | 今 | 後 | 根拠 |
|---|---|---|---|
| CLAUDE.md（120行） | 前提・ブランチ運用・不可逆・VPS・標準フロー要約・i18n・UI統治・ルール追加判定木 | **残す**: 前提5行・不可逆操作・VPS 鍵制限・直push禁止・目次リンク。**移す**: ブランチ運用の手順詳細（:46-66）→ specs/branch-operations/README.md（既に正典と明記 :47）、標準フロー要約（:72-82）→ STANDARD-WORKFLOW（正本 :156 の方針）、i18n 本文（:90-92）→ frontend/CLAUDE.md（既に ESLint 強制の記述あり :25-27）、ルール追加判定木（:96-115）→ docs/INDEX.md の末尾章 | 公式「under 200 lines」、ADR-076 の分割方針、STANDARD-WORKFLOW:156 |
| AGENTS.md（281行） | CLAUDE.md と6節同文＋Codex 固有（役割分担・AEON・Codex UI 補助・引き継ぎ・カード定型文） | **本文を捨てて @CLAUDE.md ＋ Codex 固有節へのリンクのみ**（≤ 20行）。Codex 固有節は docs/ai-agents/codex-operations.md（新設・移動のみ）へ。カード定型文（:259-281）は design-partner.md §6 が原本と書いてあるので **PO 確認後に**そちらへ一本化 | recon §2-4、公式 :435「@AGENTS.md は二重読込にならない」の逆向き適用。**Codex が本当に AGENTS.md を読むかは未確認**（§10-3） |
| frontend/AGENTS.md・backend/AGENTS.md | CLAUDE.md と同文 | @CLAUDE.md（同ディレクトリ）1行のみ | 同上 |
| docs/STANDARD-WORKFLOW.md（175行） | 正本 | **そのまま**（章A の末端）。§7:157「CLAUDE.md に要約＋リンク」の「要約」を「リンクのみ」に改める1行修正（SSOT） | :156 |
| docs/ai-agents/executor-checklist.md | 必読 | そのまま（章A の末端）。「いつ読むか: 便の作業前・commit前・PR前」 | :5 |
| docs/ai-agents/design-partner.md（438行） | 設計セッション必読 | 章A の末端として残す。§0.5 の必読リストは目次へのリンク1本に置換（必読の重複宣言を無くす） | :44-53 |
| docs/specs/README.md（100行） | 仕様書索引 | 章B のページとして流用。表に「いつ読むか」列を追加（KGI-6）。辿れない specs 35件（discord-reaction, doc-parent-child, process-hardening/proof-of-behavior 等。raw/reachability.txt）を登録 | STANDARD-WORKFLOW:32 |
| docs/adr/FEATURE-INDEX.md | ADR 索引 | 章C のページ。変更なし | — |
| docs/ai-agents/ の辿れない19件 | 孤立 | 章A/章F に登録、または docs/handoff へ移動（便の記録なら）。1件ずつ PO 確認（§10-4） | recon §2-5 |
| specs/product-master/registration-rules.md | フックで毎回注入 | 章E の末端。フックは正規表現を狭め、PreToolUse（登録操作の直前）は現状維持 | recon §2-2 |
| ~/.claude/CLAUDE.md:13「AGENTS.md も同時更新」 | 二重化を要求 | **範囲外だが矛盾**: AGENTS.md が薄い入口になれば同時更新は不要になる。PO 判断で削除（§10-5） | recon §2-4 |

## 6. 守りの仕組み（機械強制）

| 守るもの | 仕組み | 既存との重なり |
|---|---|---|
| 入口の行数（KGI-1） | 既存 CI「CLAUDE.md line count check」の LIMITS を root 120→**90** に下げる（frontend/scripts/check-claude-size.js:23）。docs/INDEX.md を limit 60 で LIMITS に追加（同スクリプトは CLAUDE.md 以外も path 指定で検査できる :46-61） | 既存必須チェックを流用。新規 required check 追加なし＝Branch Protection 変更なし |
| 目次から辿れる（KGI-4/5/6） | 新設 .github/workflows/doc-index-reachability.yml（名称仮）: docs/INDEX.md を起点に docs/specs・docs/ai-agents の .md を幅優先で辿り、①届かない文書 ②4段以上 ③「いつ読むか」空欄 を列挙。**初期は警告のみ、2週間安定後に失敗へ**（STANDARD-WORKFLOW §1.7 と同じ昇格方式） | reachability の実装は raw/reachability.txt を作った Python をそのまま流用（Python 3.12・標準ライブラリのみ） |
| 同じ決まりを2か所に書かない（KGI-3） | 同 CI に「CLAUDE.md と AGENTS.md の本文が同一見出しを持たない」検査を追加（見出し行の集合の交差 = 0） | — |
| 関係ない注入ゼロ（KGI-2） | master-register-rules-guard.py:25 を re.compile(r"マスタ[^。\n]{0,40}登録|登録[^。\n]{0,20}マスタ") に変更（raw/prompt-regex-test.txt 案2: 無関係 5/5→0/5、関係あり 2/2 維持、別マスタ「顧客マスタに登録」は一致＝許容）。origin/main の scripts/agent-hooks/ と ~/.claude/scripts/ の両方（diff 同一を recon で確認済み）。PreToolUse 側（:53-84）は本便では変更なし。ただし本便で「監視語を引用した調査記録の Write」が止まった実測（raw/hook-block-event-20261022.txt）があるため、EXEMPT_PATHS に報告フォルダ（~/CC報告ファイル-keep/）を足すかは §10-7 で PO に聞く | hook のテストは同スクリプトの既存テストがあれば追加。**未確認**: テストの有無 |
| 安全の決まりが入口から消えない（KGI-7） | 同 CI に「CLAUDE.md に見出し『不可逆操作は必ず PO 確認』『VPS 直作業禁止』が存在する」検査 | — |
| 変更そのもの | CLAUDE.md/AGENTS.md/STANDARD-WORKFLOW は executor-checklist §2:29-30 により「危険ファイル変更 PR」＝PO GO 必須。ADR 起案（§9） | ADR-1029 マージ前審査フック |

## 7. 弊害・リスクと対策

| リスク | 対策 |
|---|---|
| 安全の決まりが「目次を辿らないと読めない」場所へ落ち、読み飛ばされる | 安全の決まりは入口に残す（KGI-7・CI 検査）。目次化するのは「手順」だけ |
| 移動時に文が欠ける（SSOT 化の典型事故） | 1段1ファイル。移動前後で git diff --stat と該当節の行数が一致することを PR 本文に貼る。削除行のある PR は「削除するファイル」欄に実測で列挙（executor-checklist §0） |
| AI が目次を辿らず作業に入る（お作法頼み） | 入口に「作業の型は目次から辿る」を残す。辿ったかは機械で検査できない＝**人の確認**（STANDARD-WORKFLOW §1.7「人手で守る」相当）。agent-console のセッション記録で Read の有無を後から数えられる（**未確認**: 記録の粒度） |
| Codex が AGENTS.md の本文を失い動けなくなる | §10-3 で PO に確認してから段4を実行。それまで AGENTS.md は触らない |
| 正規表現を狭めて必要な注入が落ちる | PreToolUse 側の拒否（登録操作そのものを止めて規則を出す）は残るため、最後の砦は維持。狭めた案の取りこぼし例文を raw に積み増して測る |
| 圧縮（compaction）後に目次を忘れる | root CLAUDE.md は圧縮後も再注入される（公式 :627）。入口にリンクがあれば再び辿れる |

## 8. 段取り（1段=1PR。変更→反映→測定→次）

| 段 | 変更 | 測定（KGI） | 戻し方 |
|---|---|---|---|
| 0 | 親仕様書 docs/specs/doc-agenda-nav/{README,ideal-state,kgi}.md 作成＋ADR 起案（Proposed）＋ specs/README.md に1行登録 | — | PR revert |
| 1 | master-register-rules-guard.py:25 の正規表現（repo 側 scripts/agent-hooks/ と ~/.claude/scripts/ の両方） | KGI-2 | 1行を戻す |
| 2 | docs/INDEX.md 新設（章A〜F・「いつ読むか」列）＋ specs/README.md に「いつ読むか」列＋辿れない specs 35件を登録 | KGI-4/5/6（警告段階の CI で観測） | ファイル削除 |
| 3 | CLAUDE.md を入口化（§5 の「移す」を実行。移す先は既存文書）＋ LIMITS 120→90 ＋ STANDARD-WORKFLOW:157 の1行 | KGI-1/7 | PR revert（CLAUDE.md は1ファイルなので差分1つ） |
| 4 | AGENTS.md 系3ファイルを @CLAUDE.md 入口化＋Codex 固有節の移動（**PO 回答後**） | KGI-3 | PR revert |
| 5 | doc-index-reachability CI を警告→失敗へ昇格 | KGI-4/5/6 が0であること | 警告に戻す |
| 6 | ~/.claude/CLAUDE.md:13 の削除（ユーザー側・PO が実行） | KGI-3 再測 | 1行を戻す |

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
3. Codex は今も AGENTS.md を読んで動いているか（AGENTS.md:42「現在の主 Generator は Claude Code」）。
   - 1. 動いていない → 段4で AGENTS.md を薄い入口にする【おすすめ】
   - 2. 動いている → 段4は Codex 固有節を残す形に変える（本文は移動、リンクで辿る）
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

## 11. 未確認・開いている論点

- 過去会話記録に同じ構想の議論があるか（recon §1。Grep ツールのあるセッションで再実行）
- master-register-rules-guard.py にテストが在るか（段1で git grep master-register-rules で確認）
- agent-console のセッション記録から「目次を辿ったか」を数えられるか（§7）
- ADR-076 外部エビデンス表の出典

## 12. 自己審査

判定: **REVISE**（設計の骨格は確定できるが、PO 判断 1〜3 が未回答で段0・段3・段4 の最終形が決まらない）

根拠:
- APPROVE できる部分: 現在地は file:line と生出力で裏付け済み（recon §2）。KGI は全て測定コマンド付き。段1（正規表現1行）は根拠・測定・戻し方が揃い単独で進められる。
- REVISE が要る部分: 親仕様書未作成（§1.8 新規テーマ）、Codex の AGENTS.md 利用実態が未確認のまま段4を書いている、ユーザー側 ~/.claude の矛盾（:13）は範囲外なのに段6に置いている（PO 実行前提と明記したが、範囲の線引きを PO に確認すべき）。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| K1 自動で入る行数（MEMORY.md を除く）が200行以下 | recon §2-1 の6ファイルから MEMORY.md を除いた5ファイルを wc -l で合計 |
| K2 無関係な例文5本で差し込み0、関係ある例文2本で2/2 | 例文7本を python3 -I で新しい正規表現に通し、True/False を表で出す（例文は recon 外の raw/prompt-regex-test.txt と同じ） |
| K3 プロジェクト側4種の入口で9語の重複0 | recon §2-4 と同じ grep を CLAUDE.md・AGENTS.md・frontend・backend に実行 |
| K4 目次から届かない specs・ai-agents の文書0 | 新設 CI の出力（届かない文書の一覧が空） |
| K5 入口から末端まで3段以内 | 同 CI の段数出力の最大値 |
| K6 目次の「いつ読むか」空欄0 | 同 CI の空欄数 |
| K7 入口に安全の決まりの見出しが残る | grep -n "不可逆操作は必ず PO 確認" CLAUDE.md と grep -n "VPS 直作業禁止" CLAUDE.md が各1件 |
| 既存の必須チェックが全部緑 | PR の Checks 画面（CLAUDE.md line count check・process-artifacts gate ほか15件） |

## 13. Opus 審査（2026-10-22）

判定: **REVISE**（Fable の自己審査と同じ）。

- 確かめたこと: K1 の今の値（6ファイル計462行・MEMORY.md 149行）を Opus が wc で再計測し一致。K2 の原因の正規表現が ~/.claude/scripts/master-register-rules-guard.py:25 にあることを実物で確認。案2の例文結果（無関係0・関係あり2/2）を raw で確認。行数上限は検査スクリプトと CLAUDE.md:117 の本文が120行で一致（recon §2-8）。
- 解決したこと: §10-1（親仕様書）は PO 指示で作成済み。
- 残る理由: §10-2〜7 が PO 判断待ち。とくに §10-3（Codex が AGENTS.md を読むか）は段4の形を決めるので、段4の実装カードはこの回答まで書かない。段1（正規表現1行）は ~/.claude 側も触るため、ユーザー設定の変更として PO の実装承認を別にとる。
- 実装可否: 段0（ADR 起案・索引登録）と段1は、PO の実装承認があれば実装カードにできる。段2以降は §10 の回答後。

## 維持の仕組み

- 守り手: .github/workflows/check-claude-size.yml
- 追加予定の守り手（段2で新設、まだ存在しない）: doc-index-reachability.yml（名称仮。目次到達・段数・「いつ読むか」空欄・CLAUDE.md↔AGENTS.md 見出し重複・安全見出しの存在を検査。段2で警告、段5で失敗化）
- 対象: 入口が再び太ること／目次から辿れない手順書が増えること／同じ決まりが2か所に戻ること／安全の決まりが入口から消えること
- 関所なしの部分: 「AI が目次を実際に辿ったか」は機械検査できない → 人手で守る（agent-console の記録で事後確認。理由: Read の有無は CI では見えない）
