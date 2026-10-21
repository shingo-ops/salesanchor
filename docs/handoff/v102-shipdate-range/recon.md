# recon: 1行目の発送日行が捨てられ「在庫」になる件（便2 の現在地）

- 実測基準：origin/main 837245a2d（2026-10-19 に worktree を作った時点）。設計下書きの基準は f1497588e。本番は読み取りのみ（ADR-1024 reader 鍵）。
- 社外秘：仕入元名・人名・投稿IDは置き換えた（仕入元A=1行目に発送日の形、仕入元B=範囲入荷の形、仕入元C=予約品見出しの形）。生出力（手元）：/tmp/CC報告ファイル/gemini_shipdate_recon/。
- 設計：[design.md](./design.md)

## 既存 ADR
- `git grep -i "発送日\|入荷次第" origin/main -- docs/adr` に本件を扱う ADR は無し。関係：ADR-100・ADR-1004・ADR-154（docs/adr/ADR-154-tcg-parity02-gas-python-migration.md）。docs/adr/FEATURE-INDEX.md に該当行なし。
- 状態判定の前例：docs/handoff/v102-preorder-context/{card-PO.md,card-PO2.md,design.md,data/*.sql}。

## 本番 id25 の現在値（2026-10-19、ai_ro.public__tcg_status_master を reader 鍵で読む）
- id=25, effect=DATE_AHEAD, enabled=True, note=v102-preorder-context:2, updated_at=2026-10-12 05:10:05+00。search_pattern の md5=93df884baaaa82ee3d9fad744088f9a9・長さ52 は、設計の「前」regex と完全一致。
- DATE_AHEAD の有効行数 = 3（id25・26・27）。

## 現在地（事実）
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


## コードの根拠（origin/main 837245a2d、フルパス:行番号）
- `backend/app/services/v102_status_context.py:28`：CURRENT_YEAR_BACK_MONTHS = 1。`backend/app/services/v102_status_context.py:29`：NEXT_DAY_GRACE_DAYS = 1。
- `backend/app/services/v102_status_context.py:71`：_period_end（月日から期間の終わりを返す。年決めは投稿月との差）。
- `backend/app/services/v102_status_context.py:91`：_date_ahead。:100 付近で名前付きグループ m・d を読む。終わりが投稿日の翌日より後の最初の当たりの文字列を返す。
- `backend/app/services/v102_status_context.py:109`：_heading。:112 で他の件が持つ行（owned）と空行を飛ばす。
- `backend/app/services/v102_status_context.py:120`：context_status。RELEASE_AHEAD → DATE_AHEAD → HEADING の順。:137 で DATE_AHEAD を読む。
- `backend/tests/test_v102_status_context.py:36`：_CONTEXT の id25 相当の行（本便で範囲対応の regex に変えた。変更前は :32 付近）。
- 状態判定の前例の SQL 型：`docs/handoff/v102-preorder-context/data/commit.sql:1`。
