# design-draft: 1行目の発送日行が捨てられ「在庫」になる件 — 便1 指示文 f_ct の手順3 ／ 便2 tcg_status_master id25 の範囲日付

- 匿名化注記：仕入元名・人名・投稿IDは社外秘のため置き換えた（仕入元A=1行目に発送日の形、仕入元B=範囲入荷の形、仕入元C=予約品見出しの形、D〜K=その他の仕入元）。
- 作成：2026-10-19 Fable（設計相談役・読み取りのみ）。改訂 v2（Opus 審査 REVISE 5 点を反映）。リポジトリ・本番 DB・Gemini には触れていない。
- 現在地（recon）：docs/handoff/v102-shipdate-range/recon.md
- 位置づけ：docs/STANDARD-WORKFLOW.md の design.md 型の下書き。recon は /tmp/CC報告ファイル/gemini_shipdate_recon/（本文中「recon/」）、呼び出し経路は /tmp/CC報告ファイル/gemini_call_flow/。
- 基準コード：origin/main f1497588e0f4bacfbce3c999e5361a4ef2d952c0（ローカル checkout は古いので使っていない）。
- 変更前の指示文：~/CC報告ファイル-keep/prompts/raw_copy_v101_f_ct.txt（sha256 fe50593fa362…15fd。本番 prompt_version `v102:raw_copy_v101_f_ct:fe50593fa362` と一致：recon/posts.txt）。
- 変更後の案・wc・regex 表の実測はセッション作業用フォルダ（セッション限り。§3-1・§5-2 に全文を載せてあるので再現できる）：
- 関係する ADR：ADR-100・ADR-1004・ADR-154。`git grep -i "発送日\|入荷次第" origin/main -- docs/adr` に本件を扱う ADR は無し（recon/adr_grep_full.txt・feature_index.txt）。状態判定の前例：docs/handoff/v102-preorder-context/{card-PO.md,card-PO2.md,data/*.sql}。
- 記録の正本：docs/specs/line-analysis-tuning/README.md（§3 版表・§5 事故・§6 正解表）。

---

## 1. 目的（KGI）— PO の目的は「在庫表に誤って在庫と出ない」こと
- KGI-1（便1＋便2）：仕入元Aの投稿 <投稿ID>（recon/raw_two.txt：L1「11/3～5入荷次第発送」/ L2「30th celebration」/ L3「1000箱 24,500円」/ L4 空行 / L5 op-17 …）を再解析すると、1件目（30th celebration）の status が **Pre-order**、ship_ja に「11/3～5入荷次第発送」が入る。2件目以降（op-17 ほか、「在庫 70」などの在庫表記）は In Stock のまま。
  - 今：job <投稿ID> は全件 In Stock、lines は [2,3],[5,6],[8,9,10],[12,13,14]（recon/items_results.txt・supplierA_attempt_decoded.txt）。
- KGI-2（便2 単独でも）：仕入元Bの「@174000×1 カートン(10/16〜17入荷)」（投稿日 10/15）が Pre-order になる（今 In Stock：recon/other_suppliers_status.txt）。
- KGI-3（安定性）：便1 で、ほかの投稿の出力（lines・price・quantity）が変わる件数が増えない。同じ投稿の複数回解析のぶれが前後で増えない。「予約」「在庫」の語の見出しがどの件の lines にも入らない（下流 _heading を壊さない：§2-3）。
- KGI-4：指示文の増加を最小にする（§3-2：+4行・+250字）。

## 2. 現在地（事実）
### 2-1. なぜ 1行目が捨てられるか（指示文。keep 控えの行番号）
- 42：`…その行も足す。ただし、投稿の最初の商品より上の行は足さない。` → 手順3で L0001 を足せない。Gemini の思考「L0001 is shipping information and should be excluded」（recon/supplierA_thoughts.txt）。
- 74：`投稿の冒頭・末尾の連絡（あいさつ、締め時刻、送料、発送元、注意事項、…）`／75：まとめ書きの行（例【在庫品】【予約商品】【ポケモン】※9/14発送分…）。発送日が書かれていても外す。／76：親の見出し。発送日が書かれていても外す。（75・76 で重複）
- 152：`手順5で外す行は、仕入元の書き方に書かれていても外す。` → 共通指示文が仕入元追記より優先と、指示文自身が宣言（§4 案B の弱点）。

### 2-2. Gemini の呼び方（コーディネーター共有＋gemini_call_flow/）
- 投稿1件につき1回・毎回独立・キャッシュなし。送る文字列は「指示文全文（DB から毎回）＋仕入元ごとの追記（あれば）＋原文」：backend/app/services/gemini_raw_copy_v8.py:124-139 build_prompt_v8。
- 追記は public.suppliers.extraction_layout_rules／extraction_hard_cases で、その仕入元の投稿にしか載らない：backend/app/services/gemini_raw_copy_v8.py:111-121、backend/app/tasks/tcg_extraction.py:247-248・287-293、backend/app/services/line_analysis_v102_svc.py:195-198。
- 【未確認】仕入元A（supplier_id 伏せ：recon/channels.txt）の2欄の現在値・2欄を使う仕入元数（reader 照会が UndefinedColumn / InsufficientPrivilege：gemini_call_flow/out1.txt・out2.txt）。

### 2-3. 状態判定の仕組み（下流。origin/main backend/app/services/v102_status_context.py）
- context_status（:120-143）：resolve_status_v2 が DEFAULT で決めたときだけ、RELEASE_AHEAD → DATE_AHEAD → HEADING の順。
- DATE_AHEAD（:91-106 _date_ahead）：**件の block（その件の lines の文字）**に search_pattern が当たり、m/d から求めた日付（:71-84 _period_end。年決め CURRENT_YEAR_BACK_MONTHS=1 :28）が投稿日＋NEXT_DAY_GRACE_DAYS=1（:29）より後なら Pre-order。
- HEADING（:109-117 _heading）：件の最初の行から上へ 1 行目まで遡り、**他の件が持つ行（owned）と空行は飛ばし**（:112 `if n in owned or not text_val.strip(): continue`）、最初に HEADING 規則（id28「予約」／id29「在庫|現物|即納」：recon/status_master.txt）に当たった行で決める。見る語はこの 2 規則の語だけ。日付や「発送分」は見ない。
- この 2 点から導かれる下流への影響（コードの行で確認済み）：
  - **仕入元C の投稿**（recon/raw_two.txt <投稿ID>：L1 あいさつ / L2 空 / L3「予約品」/ L4「30th celebration (11/3〜6発送)」/ L5 シュリンク付き / L6 価格 / L7 空 / L8 ONE PIECE DAY 26 …）：今は L3 がどの件にも属さないため、2件目（L8〜）・3件目（L12〜）は _heading が L7 空行→L6・L5・L4（1件目の owned）を飛ばし L3「予約品」に当たって Pre-order。**もし L3 が1件目の lines に入ると owned になり、2・3件目は L2 空→L1 あいさつ（当たらず）→ None → In Stock に落ちる**。→ 便1 の新条件は「予約」「在庫」などの語の行・【 】の行を足さない形にする（§3-1）。
  - **日付だけの全体見出し（※10/19発送分 など）が1件目の lines に入っても**、_heading は id28/id29 の語しか見ないので他の件の状態は変わらない。1件目自身も、投稿日と同じ日付は DATE_AHEAD に当たらない（10/19 は 10/20 より後でない）。→ T2 で「許容・記録のみ」。
- tcg_status_master id25 DATE_AHEAD `(?P<m>\d{1,2})/(?P<d>\d{1,2})[^0-9]{0,4}(?:入荷|発送|発売)` は、d の直後に「～5」「〜17」が来る**範囲表記に当たらない**（§5-2 の表）。仕入元C の [4,5,6] が Pre-order なのは HEADING「予約品」(L3) による（id25 は「11/3〜6発送」に当たらない）。

### 2-4. 頻度（recon/freq_summary.txt・freq_lines.txt：active 投稿 161 件）
- 「入荷次第」の行がある投稿 2 件、範囲日付の発送 3 件（仕入元A・仕入元B・仕入元C）、「※…発送分」型の全体見出し 6 件（仕入元K L5・仕入元H L8・仕入元I L3・仕入元J L8 ほか）。仕入元Aは 1 日 1 件前後（recon/posts.txt）。

### 2-5. 過去の成功・失敗（memory project_supplier_writing_analysis・docs/handoff/gemini-prompt-e/design.md）
- 成功：e（手順ごとの例、まとめ書き誤り 9/25→2/25）、f_b/f_c（禁止にも例）。失敗：f_cv/f_cv2（印の下の商品を「数える」判定、10/12 不合格）。教訓：数えさせない・見れば分かる語と形で書く・例は既存の例の中に足す。

## 3. 便1：指示文（案A：共通の指示文を直す。§4 で案B と比べ A を推奨）
### 3-1. 変更前後（keep 控えの行番号。差分 3 か所＝diff_A2.patch 全文）
```
--- before.txt (raw_copy_v101_f_ct)
+++ after_A2.txt (raw_copy_v101_f_ctf 案)
@@ -39,8 +39,11 @@
 # 3. 件だけに付く行を足す
 - その件だけに付く行（数量・残り・状態・発送日・メモ）を lines に足す。
 - 同じ見出しの下に価格の行が複数あるとき、見出しと最初の価格の行のあいだにある、全部の件にかかる行（例【9/28発送】）は、その全部の件に足す。
-- 見出しのすぐ上に、その商品だけについて書かれた行（例 (12/7発送)）があり、その上が別の商品の行でなければ、その行も足す。ただし、投稿の最初の商品より上の行は足さない。
+- 見出しのすぐ上に、その商品だけについて書かれた行（例 (12/7発送)）があり、その上が別の商品の行でなければ、その行も足す。投稿の最初の商品の上の行も、日付と「入荷・発送・出荷」のどれかが書かれた行で、見出しとのあいだに空行が無ければ、同じように足す。「予約」「在庫」「現物」などの語の行や【 】で囲んだ行は足さない。
 例:
+[L0001] 10/25～27入荷次第発送
+[L0002] ◆ヴィンテージ ブースター VB-03
+[L0003] 1000箱 24,500円
 [L0011] ●デュエル・マスターズ DM26-RP4
 [L0013] 【10/12発送】
 [L0015] @80,000円/在庫数5カートン
@@ -48,7 +51,8 @@
 [L0027] (12/7発送)
 [L0028] ▼デジモン ブースター BT-25
 [L0029] @6,500円 ×300BOX
-出力例（3件。L0013 は同じ見出しの2件にかかるので両方に足す。L0027 は L0028 の商品だけの行）:
+出力例（4件。L0001 は投稿の1行目だが、日付と入荷・発送の行で、空行なしで L0002 の見出しが続くので、L0002 の商品の件に足す。L0013 は同じ見出しの2件にかかるので両方に足す。L0027 は L0028 の商品だけの行）:
+{"lines":[1,2,3],"price":"24,500円","quantity":"1000"}
 {"lines":[11,13,15],"price":"80,000円","quantity":"在庫数5"}
 {"lines":[11,13,17],"price":"3,000円","quantity":"在庫数200"}
 {"lines":[27,28,29],"price":"6,500円","quantity":"300"}
@@ -70,10 +74,10 @@
 # 5. 入れてはいけない行を外す
-- 手順2〜4で足した行のうち、次の行は、どの件の lines からも外す。
+- 手順2〜4で足した行のうち、次の行は、発送日が書かれていても、どの件の lines からも外す。
   - 投稿の冒頭・末尾の連絡（あいさつ、締め時刻、送料、発送元、注意事項、インボイス、買取品 など）。
-  - まとめ書きの行：複数の商品の上にまとめて置かれた行（例【在庫品】【予約商品】【ポケモン】※9/14発送分【大阪発送】━ ワンピースカード (BOX) ━）。発送日が書かれていても外す。
-  - 親の見出しの行：その下に、商品ごとの見出しが並んでいる行。発送日が書かれていても外す。
+  - まとめ書きの行：複数の商品の上にまとめて置かれた行（例【在庫品】【予約商品】【ポケモン】※9/14発送分【大阪発送】━ ワンピースカード (BOX) ━）。
+  - 親の見出しの行：その下に、商品ごとの見出しが並んでいる行。
 - 同じ商品の見出しの下だけにかかる行（手順3の【10/12発送】のような行）は外さない。
```
- 42 行目：「ただし…足さない」を、**観測できる 3 条件**に置き換える。①その行に日付と「入荷・発送・出荷」のどれかが書かれている（語）②見出しとのあいだに空行が無い（位置）③「予約」「在庫」「現物」などの語の行・【 】で囲んだ行は足さない（語・記号。下流 _heading を守る：§2-3）。v1 の「価格の行の次が空行」条件は、全体見出し形も同じ形になり効き目が無いと審査で判明したため**削除**。数えさせない。
- 日付だけの全体見出し（※10/19発送分）は条件①②を満たすので1件目に入り得る。下流への影響は無い（§2-3）ので許容し、T2 で回数を記録する。
- 74・75・76：文言は変えず、75・76 で重複する「発送日が書かれていても外す。」を 73 に 1 回だけ書く（−15字）。
- 例は 1 組だけ（PO 条件②）：既存の手順3の例の先頭に架空の正例 3 行＋出力 1 行。負例（全体見出し・【】）は既存の手順5の例と 75 行目で足りるので足さない。仕入元C 形（同じ行に発送日）は今も取れている（recon/items_results.txt）ので足さない。例の中身は架空（実在の仕入元名・原文なし）。

### 3-2. 文字数・行数の実測（PO 条件①・審査 5。`wc -m -l` の出力そのまま）
```
$ wc -m -l before.txt after_A.txt after_A2.txt B2_layout_rules.txt
     152    5469 before.txt            ← 変更前 raw_copy_v101_f_ct
     156    5695 after_A.txt           ← v1 案（審査前）
     156    5719 after_A2.txt          ← v2 案（この設計書）
       0      90 B2_layout_rules.txt   ← 案B の追記文
$ shasum -a 256 after_A2.txt
9102799f6822a462c79d82109c6df4fd1f847b63fa406e1ff88df35fab2d9ad9  after_A2.txt
```
- v2 は 152→156 行（+4）、5469→5719 字（**+250 字・+4.6%**）。v1 の +226 字から **+24 字増えた**（審査 5 の問いへの答え：増える）。増えた分は審査 2 の「予約・在庫・現物・【 】は足さない」の 1 文（+約 45 字）で、効かない条件②を削って約 20 字戻した差し引き。手順5 の重複は既に 1 回にまとめてあり、これ以上削れる重複は無い。
- 参考：1 回の入力は約 3,600〜5,900 トークン（prompt-fcv-test-20261012/estimate_output.txt）。+250 字はその 2〜3%。

### 3-3. 新しい prompt_key と本番切替・戻し（既存手順の実物）
- 新キー `raw_copy_v101_f_ctf`（V101_PROMPT_NAME_RE の形：backend/app/services/line_analysis_v102_svc.py:166-167）。既存キーの本文は書き換えない（write_fct/README.md）。
1. 控え `~/CC報告ファイル-keep/prompts/raw_copy_v101_f_ctf.txt` を make_fct.py の型（元 sha assert → 置換 → 新 txt → sha 出力）で生成し、sha256 9102799f…9ad9 と一致を確認。
2. 本番 DB に新キー行を追加：write_fctf/run_write.sh（便1 で作る予定の台本）（make_write_fct.py の型）。PO が `!` で precheck→dryrun→commit→verify（失敗時 rollback）。is_active=true（load_prompt_from_db は is_active 行だけ：backend/app/services/line_analysis_v102_svc.py:170-178）。
3. 試験（§6）。本番の既定は f_ct のまま。
4. 切替 PR：backend/app/services/line_analysis_v102_svc.py:93 `V102_PROMPT_KEY` → `"raw_copy_v101_f_ctf"`、:91 `V102_ENGINE_VERSION` → `"v102-f_ctf"`。prompt_version は `v102:raw_copy_v101_f_ctf:9102799f6822`（:182）。README §3 版表に行を足す。
5. 戻し：切替 PR を revert（DB 行は残す。#4128 と同じ）。試験不合格なら切替 PR を作らない。

## 4. 案A と 案B の比較（コーディネーター指示）
案B の追記文（B2_layout_rules.txt・90 字）：`1行目が日付と「入荷・発送」の行で、空行なしで商品の見出しが続くときは、その行を最初の商品の件に足す。「予約」「在庫」の語の行は足さない。`

| 観点 | A＝共通の指示文を直す（§3） | B＝仕入元Aの extraction_layout_rules に書く |
|---|---|---|
| ①文字数 | 全仕入元の毎回の入力 +250字（+4.6%） | 共通文 0。仕入元Aの投稿だけ +90字＋見出し行 |
| ②他仕入元のぶれ | 全投稿に影響し得る → §6 T3（125投稿×2回）で前後比較が必須 | 仕組み上ゼロ（backend/app/services/gemini_raw_copy_v8.py:131-133、backend/app/tasks/tcg_extraction.py:287-293） |
| ③同じ書き方の仕入元が増えたとき | 1 回で全員に効く。形は仕入元に依らない | 仕入元ごとに本番 suppliers を UPDATE。文が仕入元ごとに育つ |
| 効く見込み | 42 行目の禁止文そのものを直す | 42「最初の商品より上は足さない」と 152「共通優先」が残ったまま追記で逆を言う。効くかは試さないと分からず、効いても矛盾を抱える |
| 試験 | fct2 方式がそのまま使える | `--supplier-rules-file`（backend/app/tools/prompt_ab.py:360-380）で DB を変えず試せる。採点は仕入元A 4 投稿だけ |
| 本番反映・追跡 | 新キー追加＋定数 PR、revert で戻せる。prompt_version に残る | suppliers の UPDATE（戻しも UPDATE）。prompt_version に残らず後から辿れない |

**推奨：A**。原因は共通文の禁止文そのもので、仕入元A形は「1行目に日付＋入荷/発送 → 空行なしで商品」という一般の形（仕入元B・仕入元C・仕入元G も範囲日付・入荷次第を書く：recon/freq_lines.txt）。A の弱点②は §6 T3 で数で確かめ、不合格なら切替 PR を作らない（本番不変）。B は A 不合格時の逃げ道。

## 5. 便2：tcg_status_master id25 の範囲日付（コード変更なし・共用マスタの 1 行の search_pattern 更新）
### 5-1. 変更前後の regex
- 前（id25、priority 10、canonical Pre-order、exclude 空：recon/status_master.txt）：
  `(?P<m>\d{1,2})/(?P<d>\d{1,2})[^0-9]{0,4}(?:入荷|発送|発売)`
- 後：
  `(?:\d{1,2}/\d{1,2}[～〜~\-－](?=\d{1,2}/))?(?P<m>\d{1,2})/(?:\d{1,2}[～〜~\-－])?(?P<d>\d{1,2})[^0-9]{0,4}(?:入荷|発送|発売)`
  - 【Opus 審査で差し替え 2026-10-19】Fable v2 案 `(?P<m>\d{1,2})/(?:\d{1,2}[～〜~\-－](?:\d{1,2}/)?)?(?P<d>…)…` は月をまたぐ範囲で m に始まりの月を取る（「10/30～11/2入荷」→ 10/2 で過去扱い→In Stock、「12/28-1/5発送」→ 12/5）。差し替え後は終わりの月を m に取る。Python re で照合済み（11/3～5→11/5、10/16〜17→10/17、11/3〜6→11/6、10/14→10/14、11/3～11/5→11/5、10/30～11/2→11/2、12/28-1/5→1/5、10/19発送分→10/19、「21,000円/3box 発送」→当たらず、2/30→2/30）。
- 意味：「m/d1～d2」「m/d1～m/d2」の範囲は、**終わりの日 d2 を d に取る**（_period_end が返す日付＝期間の終わり。下旬→月末と同じ考え）。範囲でない「m/d」は今と同じ。名前付きグループ m・d の名前と数は変えない（_date_ahead :100 `_group(m,"m")`,`_group(m,"d")` がそのまま読む）。範囲の記号は ～（全角チルダ）〜（波ダッシュ）~ - －。
- id26（○月○日）・id27（○月）は変えない（今回の実例が無い。仕入元F「10月18-19日発送目安」は OUTPUT id5「19日発送」で既に Pre-order：recon/other_suppliers_status.txt）。

### 5-2. 当たり方の表（自前計算。_period_end と同じ年決め（CURRENT_YEAR_BACK_MONTHS=1）・翌日猶予（NEXT_DAY_GRACE_DAYS=1）で判定。regex_table.tsv の全文）
```
文	投稿日	旧 id25	旧 当たった文字	新 id25	新 当たった文字
11/3～5入荷次第発送	2026-10-19	In Stock	-	Pre-order	11/3～5入荷次第発送
(10/16〜17入荷)	2026-10-15	In Stock	-	Pre-order	10/16〜17入荷
30th celebration (11/3〜6発送)	2026-10-18	In Stock	-	Pre-order	11/3〜6発送
[10/14入荷]	2026-10-11	Pre-order	10/14入荷	Pre-order	10/14入荷
11/3～11/5入荷	2026-10-19	Pre-order	11/5入荷	Pre-order	11/3～11/5入荷
10/14〜15入荷	2026-10-14	In Stock	-	In Stock	-
10/5〜6入荷	2026-10-11	In Stock	-	In Stock	-
15時までのご注文で当日発送します	2026-10-19	In Stock	-	In Stock	-
OP-11 21,000円/3box 発送	2026-10-19	In Stock	-	In Stock	-
2/30入荷	2026-10-11	In Stock	-	In Stock	-
10/19発送分	2026-10-19	In Stock	-	In Stock	-
```
- 11/3～5入荷（仕入元A・posted 10/19）：旧 In Stock → 新 Pre-order。10/16〜17入荷（仕入元B・10/15）：旧 In Stock → 新 Pre-order（終わり 10/17 > 10/16）。11/3〜6発送（仕入元C・10/18）：新 Pre-order（今は HEADING「予約品」で Pre-order。便2 後は DATE_AHEAD が先に決める）。10/14入荷・11/3～11/5入荷：Pre-order のまま（当たる文字が範囲全体になるだけ）。
- 誤って当たらせたくない例：「10/14〜15入荷」を 10/14 に投稿 → 終わり 10/15 は翌日猶予の内 → In Stock（今と同じ扱い）。「15時までのご注文で当日発送」「21,000円/3box 発送」「2/30入荷」「10/19発送分（当日）」→ すべて In Stock、前後で変化なし。
- 【注意】この表は自前の Python で同じ規則を再現して計算したもの（実モジュールは未実行）。便2 の PR では §5-4 のテストで実モジュールに通す。

### 5-3. 本番への入れ方（共用マスタ。前例 docs/handoff/v102-preorder-context/data/{precheck,dryrun,commit,verify,rollback}.sql の型）
- tcg_status_master は public の共用マスタ。migration にデータを入れない（memory shared_master_ssot_policy）。
- 5 本の SQL を `docs/handoff/v102-shipdate-range/data/` に置き、PO が `!` で実行（manual-only 鍵・psql）：
  - precheck（読み取り）：id25 の search_pattern が「前」の文字列と一致しなければゼロ除算で止める。effect='DATE_AHEAD' の有効行が 3 行であること。
  - dryrun：BEGIN → UPDATE … WHERE id=25 AND search_pattern=<前> → 1 行でなければゼロ除算 → SELECT で確認 → ROLLBACK。
  - commit：同じ UPDATE（note に 'v102-shipdate-range:1' を付け、updated_at=NOW()）→ 1 行確認 → COMMIT。
  - verify（読み取り）：id25 の search_pattern が「後」と一致・enabled。
  - rollback：search_pattern を「前」に戻す UPDATE（1 行確認）。
- 代替：super-admin の PATCH /api/v1/super-admin/status-master/{id}（backend/app/routers/super_admin_status_master.py:7）で PO が GUI から直す。SQL 型のほうが前後の文字列を一致検査できるので SQL を推奨。
- 反映の観測：UPDATE 後に対象投稿（<投稿ID> は便1 後、<投稿ID> は即）を再解析し、status_basis が `DATE_AHEAD:11/3～5入荷次第発送` / `DATE_AHEAD:10/16〜17入荷` になること（_date_ahead :105 は当たった文字列を返す）。

### 5-4. テスト（backend/tests/test_v102_status_context.py に足す）
- :32 の _CONTEXT の id25 相当の行の pattern を「後」の regex に変える（`_ARRIVAL` :18 はそのまま）。
- test_date_ahead（:107）か新しい parametrize に足すケース（posted は既存の _POSTED=2026-10-11 か個別指定）：
  | suffix | posted | expected |
  |---|---|---|
  | " 11/3～5入荷次第発送" | 2026-10-19 | Pre-order |
  | " (10/16〜17入荷)" | 2026-10-15 | Pre-order |
  | " (11/3〜6発送)" | 2026-10-18 | Pre-order |
  | " 11/3～11/5入荷" | 2026-10-19 | Pre-order |
  | " 10/14〜15入荷" | 2026-10-14 | In Stock（翌日猶予） |
  | " 10/5〜6入荷" | 2026-10-11 | In Stock（過ぎた日） |
  | " [10/14入荷]" | 2026-10-11 | Pre-order（既存・不変） |
  | " 10/30～11/2入荷" | 2026-10-19 | Pre-order（月またぎ。Opus 審査で追加） |
  | " 12/28-1/5発送" | 2026-12-20 | Pre-order（年またぎ。Opus 審査で追加） |
- basis：`_run(f"サンプル拡張\n{_price_line(' 11/3～5入荷')}", [1,2], posted=date(2026,10,19))["status_basis"] == "DATE_AHEAD:11/3～5入荷"`（:135-137 の型）。
- 1行目形：`_run("11/3～5入荷次第発送\nサンプル拡張\n" + _price_line(), [1,2,3], posted=date(2026,10,19))` → Pre-order（block に 1 行目が入る形。便1 の出力を模す）。
- 守り：既存の test_heading_owned_by_other_item_is_skipped（:175）が、§2-3 の 仕入元C の懸念（owned で飛ばす）を固定している。便1 の指示文が「予約」の行を足さないことはテストでは守れないので §6 T2(a) で見る。

### 5-4b. 便2 の受け入れ基準（実装便が確認する）
| 基準 | 検証方法 |
|---|---|
| 範囲日付 9 ケースが期待どおりの status になる | `cd backend && python3 -m pytest tests/test_v102_status_context.py --no-cov` が全件緑（生出力 /tmp/CC報告ファイル/v102_shipdate_bin2/pytest_status_context.txt） |
| テストの regex と SQL の「後」regex が同一文字列 | SQL の commit.sql・dryrun.sql・rollback.sql に「後」が含まれることと、テストの _RANGE_SLASH + _ARRIVAL との完全一致を Python で照合 |
| 本番 id25 が「前」と完全一致 | reader 鍵で ai_ro.public__tcg_status_master の id=25 の md5・長さを照合（93df884b…・52 一致を確認済み） |
| DATE_AHEAD の有効行が 3 行 | 同じ道で件数を数える（3 を確認済み）。PO 実行時は precheck.sql が 3 でなければ止まる |
| 本番DBへ書かない | この PR は SQL を置くだけ。適用は PO が ! で precheck→dryrun→commit→verify |

### 5-5. 便の順序と、単独で入れたときの影響
| 入れ方 | 仕入元A <投稿ID> | 仕入元B <投稿ID> | 仕入元C <投稿ID> | 他 |
|---|---|---|---|---|
| 便1 だけ | 1件目の lines に 1 が入り ship_ja に「11/3～5入荷次第発送」。status は **In Stock のまま**（id25 が当たらない）→ PO の目的は未達 | 変化なし | L3「予約品」は足さない条件なので変化なし（2・3件目 Pre-order 維持） | T3 で確認 |
| 便2 だけ | 変化なし（1 行目が block に無い） | **Pre-order になる**（KGI-2 達成） | 1件目は HEADING→DATE_AHEAD に根拠が変わるだけで Pre-order のまま | 範囲日付が件の行にある投稿だけ変わる（recon/freq_summary.txt 範囲日付 3 件） |
| 便2 → 便1（推奨） | 便1 の T1 で **status が Pre-order に変わる**ことまで観測できる | 便2 時点で達成 | 変化なし | — |
- 推奨順：**便2 を先**（コード変更なし・マスタ 1 行・テスト追加だけで独立に効き、便1 の試験で KGI-1 を status で判定できる）。便1 は §6 の試験を経て切替。

## 6. 便1 の検証計画（prompt_ab で過去投稿を再解析し前後比較）
### 6-1. 共通
- コマンド（fct2_runner.sh の型）：`python -m app.tools.prompt_ab --runs-file <一覧> --config v102 --prompt-key <キー> --thinking-level high --repeat <N> --max-cost-usd <上限> --test-id <ID> --out-dir /tmp/prompt_ab/<ID>`。腕「前」= raw_copy_v101_f_ct、腕「後」= raw_copy_v101_f_ctf。同日・同コード HEAD・便2 反映後に両腕を流す（status を比べるため）。`--supplier-rules-file` は付けない（今の本番の追記のまま）。
- 本番 extraction_items には書かない（出力 JSONL、DB 書込は llm_usage_events 台帳のみ：backend/app/tools/prompt_ab.py:548-556）。JSONL の v102_items に status・ship_ja・status_basis が入る（run_v102_pipeline 共通）。
- 併記：コード HEAD、両腕 prompt_sha256、実行日時、tcg_status_master id25 の updated_at、suppliers 追記 2 欄の更新時刻（取れれば）。
- 費用：1 回 約 0.0095 USD（fct2_tools.py PER_CALL）。T1+T2 = 10 投稿×3 回×2 腕 = 60 回 ≈ 0.6 USD、T3 = 125×2×2 = 500 回 ≈ 4.75 USD。合計 ≈ 5.4 USD。上限は腕ごと 2.6（fct2 と同じ）＋T1/T2 用 0.5。
  - 腕「前」の T3 に 10/10 の fct2-g-merged.jsonl（250 行・sha fe50593f）を再利用できるのは、以後 suppliers 追記 2 欄が変わっていない場合だけ（【未確認】→ 更新時刻で確かめ、確かめられなければ流し直す）。
- 採点：行の一致は score_fct2.py / score_s6.py の score()（gold_G3_v3.tsv・sha 確認）。ぶれ・status は JSONL を投稿ごとに突き合わせる。

### 6-2. 試験と合格基準
| # | 対象 | 回数 | 基準 | 検証方法 |
|---|---|---|---|---|
| T1 仕入元A形 正例 | 仕入元A 4 投稿（<投稿ID>・<投稿ID>・<投稿ID>・<投稿ID>：recon/posts.txt、215〜218 字で同形） | 3回×2腕 | 腕「後」：1件目の lines に 1 が入り、**1件目の status が Pre-order**（便2 反映後）、2件目以降は In Stock のまま、の回数 ≥ 11/12。腕「前」は 0/12 前後 | JSONL の response_text と v102_items（status・ship_ja・status_basis） |
| T2(a) 語の見出し | 仕入元C <投稿ID>（L3「予約品」L17「在庫品」）・仕入元G <投稿ID>・仕入元K <投稿ID>・仕入元H <投稿ID>・仕入元I <投稿ID>・仕入元J <投稿ID> の「予約」「在庫」の語の見出し行 | 3回×2腕 | **腕「後」で、どの件の lines にも入らない（0 回）** | 該当行番号が items[*].lines に無いことを数える |
| T2(b) 下流不変 | T2 の全投稿 | 同上 | **1件目以外のすべての件の status と ship_ja が腕「前」と同じ**（仕入元C の 2・3 件目 Pre-order 維持を含む） | v102_items を件ごとに前後突き合わせ |
| T2(c) 記録のみ | 日付だけの全体見出し（仕入元K L5・仕入元H L8・仕入元I L3・仕入元J L8） | 同上 | 合否に使わない。1件目の lines に入った回数を記録 | 同上 |
| T3-a 正答率 | 正解表 G3 v3 の 125 投稿（runs_fct2.txt） | 2回×2腕 | 行の一致 腕「後」≥ 腕「前」、「余分」「件なし(抜け)」が増えない（fct2 実績 102/2/0：score_fct2_v3.out） | score_fct2.py の型 |
| T3-b ぶれ（PO 条件③） | 同 | 同上 | repeat 1 と 2 で出力（lines・price・quantity の集合）が違う投稿数 腕「後」≤ 腕「前」 | JSONL 突き合わせ |
| T3-c 前後差（PO 条件③） | 同 | 同上 | 腕「後」の出力が腕「前」の 2 回のどちらとも一致しない投稿数 ≤ T3-b の腕「前」の値。超えた投稿は 1 件ずつ原文を見て、意図した変化（1行目の日付行）か否かを分け、意図しない変化が 1 件でもあれば不合格 | 同上 |
- 合格＝T1・T2(a)(b)・T3-a/b/c すべて○。1 つでも×なら切替 PR を作らず、案B（--supplier-rules-file で T1）に移る。

## 7. 対象と対象外
- 便1 対象：指示文 42・73・75・76 行目と手順3の例、新キー raw_copy_v101_f_ctf、切替 PR（定数 2 行）、README §3。
- 便2 対象：tcg_status_master id25 の search_pattern（SQL 5 本）、test_v102_status_context.py のケース追加。
- 対象外：gemini_raw_copy_v101.py・backend/app/services/v102_status_context.py・backend/app/tools/prompt_ab.py ほかコード、id26/id27、suppliers 追記欄、既存キー本文、migrations、deploy.yml、フロントエンド、GAS。

## 8. 外部・過去事例の参照と我々への応用
- Google 公式（gemini-prompt-e/design.md §6 で Context7 確認済みの引用）：明確な決まり・正しくできた姿の例。本案は禁止文を「語と空行」の条件に置き換え、既存の例に正例 1 組を足す。
- 社内前例：e・f_b/f_c（成功）、f_cv/f_cv2（数える判定の失敗＝使わない）。v102-preorder-context（マスタ行の 5 本 SQL 型＝便2 で踏襲）。
- 新たな外部調査はしていない（既存の確認済み資料で足りる）。

## 9. リスク・未確定・PO 判断
- R1：便1 の「日付と入荷・発送・出荷の行」条件に当たる全体見出し（※10/19発送分 型）が1件目に入る。下流への影響は無い（§2-3）が、1件目の ship_ja に「10/19発送分」が入る可能性 → T2(c) で回数を記録し、多ければ 42 行目に「『分』で終わる行は手順5のまとめ書き」を 1 文足す（+約 30 字）か、案B へ。
- R2：手順5の既存例「L0005 ※10/20出荷分 → L0007 ◇ゼクシオンパック」は新 42 行目の条件①②を満たして見える（番号が飛び空行が見えない）。手順5で外す例として残るので Gemini には「足してから外す」と読めるが、ぶれの元になり得る → T3 で崩れたら例の説明に「下に別の商品が続く」を足す。
- R3：ぶれ（5 回に 1 回外れる揺れの前例）→ T1 の 11/12。
- R4：便2 の regex は自前計算のみ（§5-2）→ PR のテストで実モジュールに通す。範囲の記号が ～〜~-－ 以外（「から」「〜頃」等）は当たらない（今と同じ）。
- R5：本番反映は PO の `!`（便2 UPDATE 1 行・便1 新キー INSERT）と定数 2 行の PR。migrations は無い。
- 未確認：仕入元Aの追記 2 欄の現在値／2 欄を使う仕入元数／T3 腕「前」の再利用可否／仕入元K・仕入元H・仕入元I・仕入元J の見出し行の直下の構造（T2 で観測）。
- **PO に決めてほしいこと（1 件）**：便2（id25 の範囲日付、マスタ 1 行＋テスト）→ 便1（案A・共通指示文 +250 字・試験 約 5.4 USD）の順で進めてよいか。y → 便2 の SQL 5 本と PR を用意し PO `!` で反映、続けて新キー控え→DB 追加→試験→合格なら切替 PR。n → 便2 だけ入れ、便1 は案B を `--supplier-rules-file` で T1 だけ試す（約 0.3 USD・本番 DB 不変）。

## 維持の仕組み
- 記録：docs/specs/line-analysis-tuning/README.md §3 版表に f_ctf の行（sha・日付・T1〜T3 結果）。便2 は docs/handoff/v102-shipdate-range/（design・SQL 5 本・verify 出力）。JSONL と採点出力は ~/CC報告ファイル-keep/stage-fctf-<日付>/（社外秘・リポジトリ外）。
- 守り手: 便2＝backend/tests/test_v102_status_context.py の追加ケース（CI）。便1＝prompt_version `v102:<key>:<sha12>`（backend/app/services/line_analysis_v102_svc.py:182）で後から追跡。status_basis（DATE_AHEAD:<当たった文字> / HEADING:<行>）で「指示文の問題か regex の問題か」を分けられる。
- 再発の見張り：「1行目の発送日が捨てられて在庫」が再発したら、prompt_version が f_ctf か → lines に 1 があるか → status_basis が DATE_AHEAD か、の順で見る。

## 審査記録（Opus・Architect。同一AIの自己審査ではなく Fable 案を Opus が審査）
- v1（2026-10-19）：REVISE。①条件「価格の次が空行」は全体見出しと区別できない ②仕入元C L3「予約品」が owned になり 2・3 件目が In Stock に落ちる（backend/app/services/v102_status_context.py:112）③T2 は下流の status で判定 ④便2（範囲日付）が無いと目的未達 ⑤wc 再測。
- v2（2026-10-19）：APPROVE（条件付き修正を Opus が直接反映）。①〜⑤は反映済み。便2 の regex は月・年またぎで誤るため §5-1 を差し替え・§5-4 に 2 ケース追加。
- 未解決（実装前に解く・設計合格を妨げない）：仕入元Aの追記 2 欄の現在値、T3 腕「前」の 10/10 JSONL 再利用可否（実行前に更新時刻で判定、不明なら流し直す）。
- 状態（2026-10-19）：設計審査済み（APPROVE）・PO 承認済み（便2→便1の順）。便2 は本番反映済み（id25、04:19:31Z、verify 合格、PO `!` 実行）・本PRでテストと文書を保存。便1 は未着手。

## 結果と採用案（2026-10-19）

### 便1（共通の指示文の写し raw_copy_v101_f_ctf）の結果
- T1：12/12 ○。T2(a)：○。T2(b)：18 回中 1 回ずれ。
- T3：×。写しのぶれが 41→49 に増え、前後差は 52 > 41、語だけの見出し行が混入した。
- そのため本番には切り替えず、f_ct のまま。DB に f_ctf の行は残っているが、使われていない。

### 試験道具の注意
- prompt_ab はシステム段に投稿日を渡さない。`run_v102_pipeline` を呼ぶ `_v102_row_fields` に投稿日の引数が無い（backend/app/tools/prompt_ab.py:276-281）。本番側は `load_posted_date` で渡している（backend/app/services/line_analysis_v102_svc.py:1435）。
- そのため DATE_AHEAD / RELEASE_AHEAD が効かず、試験の status 列は判定に使えない。lines と ship で測る。

### 採用案B（PO 決定「1」）
- 共通の指示文は変えない。仕入元Aの suppliers.extraction_layout_rules にだけ補足を入れる（231 字、原文の例 1 組と出力の例付き）。
- 注入先は gemini_raw_copy_v8.py の仕入元別補足の欄（`build_new_system_rules_section` 内、backend/app/services/gemini_raw_copy_v8.py:115-117、見出し「この仕入元の書き方（指示書の手順への当てはめ）」）。

### 案Bの試験結果（`--supplier-rules-file` で実施。K1〜K5 すべて ○）
|項目|結果|
|---|---|
|K1|1 行目が lines に入った回 10/10（前は 0/10）|
|K2|ずれ 7（基準 6+2 以下）|
|K3|errors 0/0|
|K4|Pre-order 10/10（prompt_ab の status 列は使わず、出力の lines に投稿日を入れて context_status を手元で再現して判定）|
|K5|語だけの見出し行 0/0|
- 費用：0.588 USD。

### 本番反映
- 2026-10-19 12:42:48Z。対象の仕入元 1 行だけを更新し、他の 293 行の md5 は変わっていない。
- 読み直し 13:36Z：1 件目の lines が {2,3}→{1,2,3} になり、In Stock→Pre-order、発送は 11/3〜11/5 になった（JUDGE OK）。

### 戻し方
- extraction_layout_rules を NULL に戻す（md5 が一致した場合だけ）。

### 残り
- 仕入元Aの新しい投稿で効いているかを観測する。
- prompt_ab に投稿日を渡す改修は、任意の別件にする。
