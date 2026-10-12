# 実装カード PO: 予約の判定に「発売日・先の日付・見出し」を加える（便PO）

設計者: Opus（2026-10-12）。PO 決定（原文）:
- 「商品マスタの発売日から商品の発売日が未来→予約商品と判断することは出来ると考えるがどうか」
- 「10月中旬発送予定や[10/14入荷などは再販商品の予約案内なのだがこういった商品も予約とシステムが判断することは出来る」
- 3つを組み合わせる案に「y,推測は禁止して事実確認を怠らずに確実性を重視して…安全に進めてくれ」
根拠（手元・社外秘）: /tmp/CC報告ファイル/preorder-status/、/tmp/CC報告ファイル/preorder-release/、/tmp/CC報告ファイル/preorder-design/recon/（r1〜r6）。

## 背景（事実・確認済み）
- status は backend/app/services/gemini_raw_copy_v101.py:924 `resolve_status_v2(block, ctx.status_entries, raw_memo=block)`。block は :904 で件の lines だけ。規則は backend/app/services/tcg_analyzer_svc.py:1162-1200（EXCLUDE→OUTPUT 非DEFAULT→DEFAULT）、読込 :1118-1141（public.tcg_status_master、enabled、ORDER BY effect, priority）。
- 予約見出しの下の現行件 281 中 280 が In Stock（recon r6）。予約見出しはどの件の lines にも入っていない（r4: 0件）。件の行番号は raw_text.split('\n') の 1 始まり（q3: 1150/1150）。
- 投稿日は _extract_one に届いていない（backend/app/tasks/tcg_extraction.py:257 ExtractionContext に無し）。release_date は ProductEntry に無い。既存の読込の作法: line_analysis_v102_svc.py:932 _FOLLOWUP_CURRENT_SQL（line_posted_at を読む）、gemini_raw_copy_v102_product_first.py:290 load_product_first_masters・:105 ProductFirstMasters。
- is_current のまとめ方（tcg_analyzer_svc.py:1855 付近）に status は入らない。配信（tcg_distribution_svc.py:266, :291-298）は Pre-order を除外せず status 列に出す。便BB・便UP は status 文字列を見ない。

## 0. 着手前の確認（読み取り。前提と違えば NEEDS_DECISION）
0-1. tcg_status_master に新しい effect 値（HEADING・DATE_AHEAD・RELEASE_AHEAD）と新しい match_type 値（RELEASE）の行が入ったとき、既存の読み手すべてが壊れず・挙動が変わらないか。対象: resolve_status_v2・_match_status_pattern・_sold_out_words（v101.py:367-371）・_is_sold_out・v10（gemini_raw_copy_v10.py:345）・extraction_shadow_svc.py:280,419・tcg_analyzer_svc.py:1278,1567・rule_test（routers/tasks）・prompt_ab・super_admin_status_master.py（一覧・作成・PATCH・export・preview・import の入力/出力の検証。pydantic の Literal 等で落ちないか）・status_master.py・frontend の RuleManagementPanel.tsx / RuleDrawer.tsx / StatusMasterImportPage.tsx / StatusMasterPage.tsx（effect・match_type の選択肢や表示で落ちないか）。file:line で全件。1つでも壊れる・挙動が変わるなら NEEDS_DECISION（別表にするか判断する）。
0-2. exclude_pattern の当て方（_match_status_pattern を exclude にも使うか、match_type に従うか）を file:line で。
0-3. resolve_status_v2 が DEFAULT で決まったかどうかを外から知る方法（戻り値では区別できない）。既存関数のシグネチャは変えない。
0-4. _extract_one を作り直す経路（_apply_context_work・_apply_followup・_apply_soldout_ref 等の build(i, chosen_product_id)）すべてで、新しい引数が同じく渡ること。
0-5. analysis_results に status の根拠を残す列があるか（無ければ列は足さない。根拠は置き換え試験の出力に出す）。
0-6. preflight。

## 1. 変更（v102 経路だけ。v101・v10・旧経路・shadow は挙動不変）
1-1. 新モジュール backend/app/services/v102_status_context.py（小さく）:
  - 規則の取り出し: status_entries から effect が HEADING・DATE_AHEAD・RELEASE_AHEAD の行を priority 順に分ける。該当行が無ければ何もしない（データ投入前は挙動不変）。
  - 発売日（RELEASE_AHEAD）: 件の product_id の release_date が投稿日（line_posted_at の JST の日付）より後 → その行の canonical。
  - 先の日付（DATE_AHEAD）: 件の行（block）に search_pattern（REGEX。名前付きグループ m 必須、d・part 任意）が当たり、exclude_pattern が当たらないとき、日付の終わりを求める: d があれば m月d日、part が 上旬→10日・中旬→20日・下旬/末→月末・頃→月末、どちらも無ければ月末。年は投稿日の年、その月が投稿日の月より前なら翌年。終わりが投稿日より後 → canonical。日付として成り立たない（2/30 等）は当たらない扱い。
  - 見出し（HEADING）: 件の lines の最小行番号から上へ1行ずつ見る。どの件の lines にも入っていない・空でない行で、HEADING 行の search_pattern が当たり exclude_pattern が当たらない最初の行の canonical（priority 順の最初に当たった行）。見つからなければ無し。
  - 適用順と条件: resolve_status_v2 の結果が DEFAULT で決まったときだけ（EXCLUDE の Sold out・既存 OUTPUT の Pre-order は変えない）、RELEASE_AHEAD → DATE_AHEAD → HEADING の順で最初に決まったもの。HEADING の canonical が DEFAULT と同じ（在庫の見出し）なら変えない。
  - 文字列（Pre-order 等）・語・日付の書き方はコードに書かない（すべて表の行から）。旬の日（10/20/月末）だけは定数で名前を付ける。
1-2. 配線: 投稿日（JST の date）と、全件の lines の和集合を _extract_one に渡す。release_date は ProductFirstMasters に既定値付きの項目（例 product_release: Mapping[str, date]、既定は空）を足し、load_product_first_masters で products.release_date を読む（既存の分類 map と同じ作法）。投稿日は run_v102_analysis で job の source_messages.line_posted_at を読み（既存 SQL の作法）、masters 経由で extract_v101_items → _extract_v102 → _extract_one。v102 のときだけ使う。
1-3. 根拠: 0-5 で列が無ければ、件の dict に status_basis（例 "RELEASE_AHEAD:2026-10-16" / "DATE_AHEAD:<当たった文字列>" / "HEADING:<行番号>"）を載せるだけにし、DB には書かない（_analysis_values は変えない）。
1-4. データは入れない。候補の行と SQL を docs/handoff/v102-preorder-context/data/（precheck・dryrun・commit・verify・rollback。$ と二重引用符なし、件数違いはゼロ除算で失敗、id・status_id は既存の採番の作法に合わせる。rollback は enabled=false で行は消さない）に作るだけ。候補（設計者案。置き換え試験で調整してよいが、変えたら全件報告）:
  | canonical | effect | match_type | search_pattern | exclude_pattern | priority |
  |---|---|---|---|---|---|
  | Pre-order | RELEASE_AHEAD | RELEASE | （空） | （空） | 10 |
  | Pre-order | DATE_AHEAD | REGEX | `(?P<m>\d{1,2})/(?P<d>\d{1,2})[^0-9]{0,4}(?:入荷|発送|発売)` | （空） | 10 |
  | Pre-order | DATE_AHEAD | REGEX | `(?P<m>\d{1,2})月(?P<d>\d{1,2})日[^0-9]{0,4}(?:入荷|発送|発売)` | （空） | 20 |
  | Pre-order | DATE_AHEAD | REGEX | `(?P<m>\d{1,2})月(?P<part>上旬|中旬|下旬|末|頃)?[^0-9]{0,4}(?:入荷|発送|発売)` | （空） | 30 |
  | Pre-order | HEADING | REGEX | `予約` | `ご予約可能|集荷予約` | 10 |
  | In Stock | HEADING | REGEX | `在庫|現物|即納` | `在庫なし|ご注文で当日発送|弊社在庫品につき|記載商品以外の在庫|記載していない在庫|在庫・商品の入荷について|保管中` | 20 |

## 2. テスト（合成で。既存 v102 テストの作法）
- 発売日: 未来→Pre-order、当日・過去・無し→不変。
- 先の日付: 投稿 10/11 で「[10/14入荷]」→Pre-order、「10/11入荷」「10/5入荷」→不変、「10月中旬発送予定」→Pre-order（終わり 10/20）、投稿 10/25 の「10月中旬発送」→不変、投稿 10/11 の「2月入荷分」→Pre-order（翌年）、「明日発送予定」「移し替えて発送予定」→不変、「2/30入荷」→不変。
- 見出し: 【予約商品】の下→Pre-order、【予約商品】の後に【ポケカ在庫商品】→その下は不変、「ご予約可能な…」だけ→不変、見出しが件の lines の中→見ない（件の外の行だけ）。
- 優先: Sold out（EXCLUDE）・既存 OUTPUT の Pre-order は不変。表に新しい行が無ければ全て不変。
- 0-1 の読み手が新しい effect/match_type の行で落ちない・挙動不変（代表の単体テスト）。

## 3. 置き換え試験（マージ前の証拠・本番は読み取り）
- 本番の v102 現行行を持つ全ジョブ（recon r1: 110 job）を、変更前のコードと、変更後のコード＋1-4 の候補行を表に足したとみなした状態（本番の表には書かない。読み込んだ status_entries に足す）で通す。前回の作法: /tmp/CC報告ファイル/v102-unit-state-set/ と /tmp/CC報告ファイル/unit-residual5/round5/sim.py。
- 出力（/tmp/CC報告ファイル/preorder-design/test/）: 変わる件の全件 CSV（id8・job8・提供者・商品・release_date・投稿日・前→後の status・当たった規則と根拠・見出しの行の文字列 25字まで・件の価格行 40字まで）と、規則別の件数、status 以外の列の変化が 0 であることの確認、Sold out の件が1件も変わらないことの確認。
- 期待（目安・外れても止まらず全件報告）: 予約見出しの下の In Stock 280件の大半と、発売日が未来の16件・先の日付の件が Pre-order。「明日発送予定」2件・「移し替えて発送予定」1件は不変。
- 停止条件: status 以外の値が1件でも変わる、Sold out が変わる → NEEDS_DECISION。

## 4. 手順
1. `bash scripts/new-worktree.sh release/v102-preorder-context --claude` → preflight。Bash は `cd <worktree> && …` を単独で（リポジトリ外へ cd しない）。
2. 0 → 実装 → テスト → 置き換え試験 → ruff・pytest（v102 関連・status 関連・0-1 の読み手のテスト）・npm run check:all（frontend 無変更なら省略理由）。
3. このカードを docs/handoff/v102-preorder-context/card-PO.md に置く（recon・design は設計者）。
4. commit（push しない）。

## 停止条件
0 で前提が違う・v102 以外の挙動が変わる・置き換え試験で上の停止条件 → NEEDS_DECISION。フックに止められたら言い換えず止まる。本番 DB は読み取りのみ。最終行 DONE / BLOCKED: / NEEDS_DECISION:。
