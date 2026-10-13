# 設計再審査（Fable）: design-v4.md「危険でない変更は1件ごとの PO 承認をなくす」

- 審査日: 2026-10-14 / 読み取りのみ（repo・本番・GitHub への書き込みなし。gh は `gh api repos/.../pulls/N` と `pulls/N/files`、`gh pr list` の読み取りだけ）
- 審査対象: /tmp/CC報告ファイル/devflow-switch/design-v4.md、baseline-v4.md、classify-v4.py、_v4-cand.py、_v4-judge.json、_v4-rows.json
- 前回審査: review-fable-v3.md（REVISE、HIGH-A〜E・MEDIUM-A〜E・LOW-A・LOW-B）
- 実物の照合先: 本店 `git fetch` 後の origin/main = e0355ceef6（`git rev-parse origin/main`）。GitHub の PR 本文・patch は gh api で取得
- 生出力（抜き取りの patch 比較・集計）: /tmp/CC報告ファイル/devflow-switch/_fable-v4/（out_cause_*.txt＝原因4組、out_other_*.txt＝人手別件5組、out_mach_*.txt＝機械別件7組、content_match.txt、population.txt、extra_pairs.txt、prefix_checks.txt）

## 判定: REVISE（HIGH 1 件・MEDIUM 3 件・LOW 4 件）

PO への結論（1行）: 実現できる。ただし S3 の合格ライン 9.9% は「試行で B になる集団」の実績（約 6.9%）より緩いので、数字を直してから始める。

v3 の HIGH 5 件のうち 4 件は直った。残る 1 件（HIGH-B の「分母の中身」）が HIGH-1 として残る。他はいずれも文書・集計の手直しで足り、コード・CI・権限の変更は要らない。

---

## 1. v3 指摘の解消状況（指摘ごと）

| v3 | 状態 | 根拠 |
|---|---|---|
| HIGH-A 台帳 PR が「どちらでもない」 | 直った | design-v4.md:55「L 台帳: 変更が `.claude-pipeline/` だけ。B-3 として扱い、S3 の分母には入れない」。classify-v4.py:29 で L を分ける。_v4-rows.json: L 37件。S3 分母 101 は L を除く（baseline-v4.md:8-9）。注意: 台帳ファイル名に auth 等の語が入ると A になる例が1件（#3940。MEDIUM-1） |
| HIGH-B S3 基準値 7.7% の数え方 | 一部 | 数え方は直った: 明示参照方式をやめ、同一ファイルを触る fix 305組を「行範囲の交差 or 本文参照」で 65組に絞り人手判定、240組は機械で別件（baseline-v4.md:29-33）。抜き取り 16組（原因4・人手別件5・機械別件7）はすべて判定どおり（§2）。240組の機械判定に対して「fix の削除行が B の追加行と一致するか」を全組で照合し、不一致は 1組だけ（#3736→#3793、MEDIUM-2）。**直っていない部分**: 分母 B 101 に「試行では A になる PR」が入っている（HIGH-1） |
| HIGH-C S2 が測れない | 直った | design-v4.md:9,:22（PR 本文の「区分」「PO承認」欄と §3 のパス条件を突き合わせる）、:31、:77（PR テンプレートに3欄）。【事実】origin/main の `.github/PULL_REQUEST_TEMPLATE.md` と `scripts/dev/validate-pr-body.sh`（検査1〜5）は「### 標準ワークフロー確認」節と recon/設計/対象ADR/触るファイル/削除するファイルを見るだけで、欄の追加と衝突しない |
| HIGH-D 認証ファイルが B に落ちる | 直った | design-v4.md:42、classify-v4.py:17-18。v3 で挙げた 9 本を isA に通すと 9/9 が A（本審査で再実行。_fable-v4 の最終コマンド出力）。`frontend/src/tokens.css` は A にならない（`.css` 除外）。tokens.css を含む 8 PR のうち tokens.css だけが理由で A になる PR は 0（baseline-v4.md:18、本審査の「word/token/deploy だけが理由の A」一覧にも tokens.css なし）。副作用: 語の部分一致が docs/handoff・台帳のパスにも当たる（MEDIUM-1）。`TokenSection.tsx` は A のまま（LOW-2） |
| HIGH-E ideal-state.md／kgi.md が1階層のみ | 直った | design-v4.md:43「全階層」、classify-v4.py:16（`docs/specs/` 配下でファイル名が ideal-state.md／kgi.md）。v3 の実例 #3927 は v4 で A（_v4-rows.json、理由 `docs/specs/design-system/visual-language/ideal-state.md`） |
| MEDIUM-A B-2「API 契約変更なし」 | 直った | design-v4.md:53「`frontend/api-contract/` を含まない」。classify-v4.py:9 で `frontend/api-contract/` は A |
| MEDIUM-B／LOW-A tools・tasks・scripts | 直った | design-v4.md:41、classify-v4.py:8-9。例: #3718（`backend/app/tasks/buyback_scraper.py` を含む）は A |
| MEDIUM-C B-1 の正本 | 直った | design-v4.md:51（ADR 番号＋What/Decision 節の file:line＋引用文の3点、Fable が `git show origin/main:<path>` で確認） |
| MEDIUM-D Fable 審査の記録先 | 直った | design-v4.md:30,:31（`docs/handoff/<仕事名>/review-fable.md`、PR 本文に1行） |
| MEDIUM-E S1 の「前」が実測でない | 直った | design-v4.md:21（試行前3営業日に同じ数え方で実測）。数え手が PO から Opus に変わった点は LOW-3 |
| LOW-B 新 ADR 番号 | 直った | design-v4.md:70「今の最大は ADR-1014」。【事実】`git ls-tree origin/main docs/adr/` の最大は ADR-1014 |

---

## 2. baseline-v4.md と classify-v4.py の実物照合

### 2-1. 原因 12組のうち 4組（gh api の patch と PR 本文で照合）
| 組 | 結果 | 根拠（_fable-v4/out_cause_*.txt） |
|---|---|---|
| #3717→#3730 | 原因で正しい | B が `central_masters.py` に `class SupplierSourceMessage: id: int` を追加（hunk @@ -438）。fix は同じ行を `id: UUID` に変更し、本文「Pydantic スキーマが int で定義されていたため…500」 |
| #3752→#3756 | 原因で正しい | B が `buyback_prices.py:410-436` に `UPPER(p.category)` を4箇所追加。fix は同じ4箇所を `bsp.card_game` に差替え、本文「UPPER(p.category) で GROUP BY しても同一ゲームが別タブに分かれる」 |
| #3818→#3819 | 原因で正しい | B が `tcg_analysis_dashboard_svc.py:187-225` に `sc.channel_name` を含む SQL を追加。fix（EMERGENCY）が `sc.channel AS channel_name` に修正、本文「PR #3818 で sc.channel_name と誤ってクエリを記述」 |
| #3746→#3749 | 原因で妥当 | B が `.searchField { max-width }` と `--size-search-field-max: 200px` を追加。fix は同じ `.searchField` に `margin-bottom: 0; flex-shrink: 0` を足し、トークンを 320px に変更。本文の原因は `.comp-field` の margin だが、崩れた検索欄の配置そのものは B が置いたもの |

### 2-2. 人手で「別件」とした 5組
| 組 | 結果 | 根拠（_fable-v4/out_other_*.txt） |
|---|---|---|
| #3663→#3681 | 別件で正しい | fix 本文「PR #3663 でスキーマ参照を直した後も…原因は supplier_channels の行が無い（9/21 の public 移行で引き継がれず）」。B の変更は TCG_SCHEMA の定数化と docstring のみで、チャネル取得ロジックは触っていない |
| #3704→#3734 | 別件で正しい | fix 本文「PR #3718 で…name_ja と誤記」。B #3704 の変更行に `name_ja` は無い。#3718 は `backend/app/tasks/` を含み A（_v4-rows.json）なので B の原因には数えない |
| #3776→#3780 | 別件で正しい | fix が直した `border: 2px dashed var(--color-border)`（:39）と `1px solid var(--color-border)`（:75）は B #3776 の変更行（:41-71 の padding・transition・hover 等）に無い。この行は #3774 が追加（#3774→#3780 は原因として数えられている） |
| #3911→#3916 | 別件で正しい | fix 本文「`/api/v1/fx-rate/{currency}` が invoices と fx_rate_admin の2系統登録…invoices が先に登録されるため到達不能」。衝突はバックエンドのルート登録で、B #3911 は frontend で URL を呼んだだけ。fix 自体は `docs/adr/` を含むので A |
| #3740→#3756 | 別件で正しい | `UPPER(p.category)` は #3752 の追加行。B #3740 の変更は検索・変動フィルタ（:73-263）で別箇所 |

### 2-3. 機械で「別件」とした 240組のうち 7組 ＋ 全組の内容照合
| 組 | 結果 | 根拠（_fable-v4/out_mach_*.txt） |
|---|---|---|
| #3762→#3789 | 別件で正しい | fix は `AnalysisDashboardPanel.tsx:1018` の `productRanking` の受け取り形。B #3762 は品質サマリの遅延読込（:150-420）で、ランキングは #3787 が追加（#3787→#3789 は原因に計上済み） |
| #3710→#3789 | 別件で正しい | 同上。B #3710 の変更に productRanking なし |
| #3662→#3693 | 別件で正しい | 共有は en/ja.json のみ。B はルールテストのキー、fix は TcgParallelReportPage のキーで無関係 |
| #3767→#3794 | 別件で正しい | fix は成功率の分母（`done/(done+error)`）。B #3767 は期間セレクタで、率の式は触っていない |
| #3753→#3794 | 別件で正しい | B #3753 は ImportTab の severity 差替え（:501-554）、fix は ExtractionTab の率（:1113-1152） |
| #3685→#3734 | 別件で正しい | fix は `pr.name_ja`（#3718 由来）。B #3685 は trigger エンドポイント追加 |
| #3983→#4133 | 別件で正しい | B は配信シートの13列目追加、fix は max_age_hours の読み口統一。共有行なし |

全 240組について「fix の削除行（12文字以上）が B の追加行と文字列一致するか」を照合（_fable-v4/content_match.txt）: 一致したのは **1組**（#3736→#3793）。残り 239組は一致なし。→ 行範囲法の取りこぼしは 1/240（MEDIUM-2）。

### 2-4. classify-v4.py と design-v4.md §3 の一致
| §3 | script | 一致 |
|---|---|---|
| A ディレクトリ 12 種（:41） | classify-v4.py:8-9 の Apre。`backend/app/auth/` は語 `auth` で拾う（:17） | 一致 |
| 「ファイル名」に auth…stripe を含む（:42） | :17 は **パス全体**に対して部分一致 | **不一致**（MEDIUM-1）。ディレクトリ名の supersession／next-session／台帳ファイル名の -auth が当たる |
| token（`.css` と `styles/` の下は除く）（:42） | :18 `.css` と `frontend/src/styles/` を除く | ほぼ一致。【事実】origin/main に `frontend/src/styles/` は無い（`styles/` があるのは `lp/src/styles` のみ）ので除外は空振り（LOW-2） |
| 正本 docs/adr・STANDARD-WORKFLOW・CLAUDE.md/AGENTS.md・ai-agents（lessons.d 除く）・specs の ideal-state/kgi 全階層（:43） | :8,:14-16 | 一致 |
| deploy・docker-compose を含むファイル（:44） | :19 | 一致 |
| 新規ファイルが pages/・routers/・models（:45） | :20（status==added） | 一致 |
| B-1/B-2/B-3 の区別、「B-1 の根拠が書けない変更は A」（:47,:50） | script は B をひとまとめ。B-1 の根拠の有無は判定しない | 機械では判定できない項目。**この差が HIGH-1 の原因** |
| B-3 `frontend/**/*.test.*`・`*.stories.*`（:54） | :23 `frontend/` 配下で `test|spec|stories` を含むパス | script がやや広い（例: `frontend/e2e/*.spec.ts`）。実害なし |
| L（:55） | :29 | 一致 |

### 2-5. 他に確かめた事実
- EMERGENCY 題名の PR（9/22〜10/14 merged, base main）: `gh pr list --search "EMERGENCY in:title merged:2026-09-22..2026-10-14"` → #3819 と #3925。#3925 は題名に「emergency fallback」を含むだけで `EMERGENCY:` 接頭辞ではない。design-v4.md:23「1件（#3819）」は正しい
- v3 で【未確認】だった #3715・#3798 の原因 PR: `SupplierExtractionRulesPage.tsx` の新規追加は #3714（A）、`ExtractionErrorLogPanel.tsx` の新規追加は #3797（A）（_fable-v4/prefix_checks.txt）。いずれも A の後続修正なので B の原因に数えないのは正しい
- CLAUDE.md（origin/main）は 120 行、`frontend/scripts/check-claude-size.js:23` の上限は 120。:53 は Draft 規則、:70-72 は標準開発フローの行。design-v4.md:72-73 の「行を増やさず置き換える」は必要条件として正しい
- STANDARD-WORKFLOW.md:23（KGI の PO承認必須ゲート）、:79（KGI：定量・PO承認済み）、:115-119（不明点プロトコル）は design-v4.md:71 の参照どおり

---

## 3. 指摘

### HIGH-1: S3 の基準値 9.9%（10/101）の分母に「試行では A になる PR」が 29件入り、原因 10件の半分がそこにある。合格ラインが比較対象より緩い
- 【事実】B 101件を題名と変更パスで分けると（_fable-v4/population.txt）:
  - feat/refactor で backend/app/ を触る: 29件、原因 5件（#3710 #3724 #3752 #3787 #3818）
  - fix 題名: 44件、原因 1件（#3717）
  - feat で frontend/src/ のみ: 22件、原因 4件（#3746 #3774 #3811 #3906）
  - コード無し（docs/テストのみ）: 4件、原因 0
- 【事実】design-v4.md:47「B-1 の根拠（下記）が書けない変更」は A。backend を触る feat は B-1（不具合修正）でも B-2（frontend/src/ だけ）でも B-3 でもないので、試行では A になる。つまり上の 29件は試行の B に入らない
- 【推測】試行の B に近い集団は残り 72件（fix 題名 or frontend のみ or コード無し）。その原因率は 5/72＝6.9%。試行で 9.9% まで悪化しても「基準値を超えない」で合格になる。design-v4.md:23 の「取りこぼしがあれば基準値は低く出て安全側」は行範囲法の取りこぼしについては正しいが、分母の集団違いは逆向き（緩い側）に働く
- 【事実】この点は v3 HIGH-B「分母の中身…基準値の集団と試行の集団が別物」で指摘済み。v4 §「v3 からの修正」HIGH-B の行は数え方だけを直し、集団については触れていない
- 直し方（文書のみ）: baseline-v4.md に「§3 で B になる PR（題名 fix／frontend のみ／コード無し）」で絞った再集計を足し、design-v4.md:23 の基準値を 5/72（6.9%）に置き直す。feat frontend-only を B-2 に含めるかどうか（MEDIUM-3）で分母が 72 か 50 かに分かれるので、MEDIUM-3 の決定と同時に行う

### MEDIUM-1: §3「ファイル名」と classify-v4.py「パス全体」が食い違い、docs/handoff・台帳のディレクトリ名の語で 5 PR が A になっている
- 【事実】word/token/deploy の正規表現だけが理由で A になった PR 17件を列挙した（_fable-v4/population.txt の前段「A PRs whose only A-trigger is word/token/deploy regex」）。うち認証・デプロイと無関係なもの:
  - #3755・#3763・#3769（`fix(pipeline)`、`docs/handoff/condition-level-supersession/`・`fix-supersession-timestamp-order/`・`supersession-global-latest/` の **supersession** に `session` が当たる）
  - #3881（`docs/handoff/condition-fallback-count/next-session-prompt.md`）
  - #3940（台帳のみ PR。`.claude-pipeline/active-work.d/release-async-offload-line-parse-auth.md` の **-auth** が当たる）→ HIGH-A の趣旨（台帳 PR で PO に質問を飛ばさない）に反する
  - #3873（`docs/handoff/fix-gemini-token-cost-recording/` の **token**。Gemini の出力トークン数の話で認証ではない）
- 影響: 安全側（A が増える）だが、PO の y の中心にある「不具合修正」3件（#3755/#3763/#3769）が自動で A に押し戻され、S1 を損なう。また §3 の文面どおり「ファイル名」で判定すると #3755/#3763/#3769/#3881/#3873 は B になり、基準値の分母と原因数が動く（#3763→#3769 は fix 本文「旧ロジックは…方向更新だったため…二重TRUE不整合」が #3763 の追加行を指す。_fable-v4/extra_pairs.txt。原因になりうる【推測】）
- 直し方: §3:42 を「変更ファイルのパスのうち `frontend/src/`・`backend/app/`・ルート直下（docker-compose 等）に限って語を見る。`docs/handoff/`・`.claude-pipeline/` は語の対象外」とし、classify-v4.py:17-18 を合わせて baseline を再集計する。認証 9 本はいずれも `frontend/src/`・`backend/app/` 配下なので HIGH-D の効果は変わらない

### MEDIUM-2: 行範囲法の機械判定 240組に取りこぼし 1組（#3736→#3793）
- 【事実】B #3736 が `tcg_analyzer_svc.py` に追加した `_resolve_pid` の `if pid is None or pid == "":`（B 時点 :1217 付近）を、fix #3793（題名「…バグ修正3件」、本文「`-` ガード」）が `or pid == "-"` に変更している（fix 時点 :1271。間の PR で約 50 行ずれたため行範囲が交差しなかった）。_fable-v4/content_match.txt・extra_pairs.txt
- 判定: B が追加した関数のガード漏れを fix が補っている。B 以前は `validate_product_id` に直接渡していたので `-` の扱いが B で変わったかは本文からは断定できない → 少なくとも「判定不能」、原因なら 11/101
- 直し方: baseline-v4.md:33 の注意書きを「全 240組について fix の削除行と B の追加行の文字列一致を照合し、一致 1組（#3736→#3793）は判定不能とする」に置き換える。監査（§4）でも同じ照合を手順に足す（行範囲だけに頼らない）

### MEDIUM-3: B-2 の名前は「文言・見た目」だが条件はパスのみで、frontend だけの新機能が B-2 に入る
- 【事実】baseline の B のうち feat で frontend/src/ のみは 22件、原因 4件（18%。B 全体の 9.9% より高い）。例: #3811「redesign pipeline map as RPG skill tree」→ #3814 で接続修正、#3906「consolidate LLM usage charts」→ #3907 で見出し修正
- design-v4.md:53 の条件（frontend/src/ だけ・api-contract なし・新しい画面ファイルなし・CI 緑）はこれらを B-2 として通す。PO の y の「画面」に frontend の新機能を含めるなら、その旨を §3 に1行書く。含めないなら B-2 を「既存の文言・CSS・配置の変更」に限る条件（例: 変更行数か、tsx の新規 export なし）を書く。どちらでも可、書いていないのが問題。HIGH-1 の分母はこの決定で変わる

### LOW-1: baseline-v4.md:31「候補39組中の全 fix PR」が :23「候補の組: 305」「fix PR は 46件」と合わない
- 数字の書き誤りと見える。305組／B 66件／fix 46件に揃える

### LOW-2: `styles/` 除外は空振り、`TokenSection.tsx` は A のまま
- 【事実】origin/main に `frontend/src/styles/` は無い。`frontend/src/pages/design-preview/sections/TokenSection.tsx` は語 token で A（本審査で isA を直接適用）。9/22〜10/6 に実害は 0 件なので低優先。§3:42 の「`styles/` の下」は削るか `tokens.css`・`TokenSection.tsx` の名指し除外に替える

### LOW-3: S1 の数え手が「Opus が会話記録から数える」に変わった
- design-v4.md:21。Opus が見ていない場所（別セッション・Discord）での PO の返答は数に入らない。試行前3営業日の「前」も同じ条件で数えるなら比較はできるが、「どこの記録を数えるか」を1行書く

### LOW-4: 語の部分一致の副作用は baseline-v4.md:19 に「author 等も拾う」とあるが、実際に当たったのは session／auth／token のディレクトリ名・台帳名（MEDIUM-1）
- 注記の例を実例（supersession／-auth.md／token-cost）に置き換えると監査担当が気づきやすい

---

## 4. 観点ごとの結論

| 観点 | 結論 |
|---|---|
| 1. v3 指摘の解消 | HIGH-A・C・D・E 直った／HIGH-B 一部（数え方は直った、分母の集団は未対応＝HIGH-1）／MEDIUM-A〜E・LOW-A・LOW-B 直った |
| 2. baseline と classify の正しさ | 原因 4/4・人手別件 5/5・機械別件 7/7 が判定どおり。機械 240組の内容照合で取りこぼし 1組（MEDIUM-2）。script と §3 の不一致は「ファイル名／パス全体」1点（MEDIUM-1）と、機械では判定できない「B-1 の根拠」条件（HIGH-1 の原因） |
| 3. 新しく見つかった欠陥 | HIGH-1（基準値の集団違い・緩い側）、MEDIUM-1（docs/handoff・台帳のディレクトリ名で A）、MEDIUM-2（行ずれの取りこぼし 1組）、MEDIUM-3（B-2 に frontend 新機能が入る。原因率 18%） |
| 4. 試行前に足りないもの | (a) B-2 に frontend の新機能を含めるかの決定（MEDIUM-3）(b) その決定に合わせた S3 基準値の再計算（HIGH-1。データは _v4-rows.json・_v4-judge.json に揃っており、再集計は 1 時間以内）(c) 語の対象パスの限定と再分類（MEDIUM-1）(d) #3736→#3793 の扱い（MEDIUM-2） |
| 5. PO への結論 | 実現できる。合格ライン（S3）の数字を比較対象に合わせてから始める |

## 5. 【未確認】
- #3736→#3793 が「原因」か「判定不能」か（B 以前の `validate_product_id` が `-` をどう扱っていたかは patch からは読めない）
- #3763→#3769 が原因か（§3 の文面どおりなら B。fix 本文の記述からは原因の可能性があるが patch だけでは断定しない）
- スマホでのマージ可否（v3 と同じ。design-v4.md:97）
- S1 の「前」3 営業日の実測値（試行前に取る前提。まだ無い）
