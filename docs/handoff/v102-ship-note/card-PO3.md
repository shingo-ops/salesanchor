# 実装カード PO3: v102 の発送日の文字を「備考」（note_ja）に入れる（便PO3）

設計者: Opus（2026-10-12）。PO 決定（原文）: 「y,発送日の情報は発送日情報に記載する条件で」→ 保存先を問うと「備考に入れる」。
根拠（手元・社外秘）: /tmp/CC報告ファイル/preorder-design/shipnote/（ship_values.csv・note_ja_grep.txt）。

## 背景（事実・確認済み）
- 件の dict の "ship" は backend/app/services/gemini_raw_copy_v101.py:963 `_ship_for`（:809-826）。型は常に str、空は `_NONE = "none"`（:61）。複数は " / " でつなぐ。
- backend/app/services/line_analysis_v102_svc.py:617-648 `_analysis_values` は note_ja を常に None（:645）。upsert は :669 `note_ja = EXCLUDED.note_ja`。
- note_ja を読むのは表示だけ（配信 tcg_distribution_svc.py:265・:313、GAS 備考、レビュー画面 tcg_analysis_review_svc.py:226,:283、取込進捗 tcg_import_progress.py:32,:133）。tcg_condition_review_svc.py:124 はレビュー版のハッシュ材料（computed_at も入っているので失効は増えない）。inventory_aggregation.py は public.inventory を読み analysis_results を読まない。v102 の行に値が入って挙動が変わる箇所は無い。
- 列は TEXT（migrations/20260921_110000_pipeline_tables_public.sql:302）。実測 2,693 件中 空でない 233 件・最大 36 字・改行 0。
- 括弧が片側だけ残る値がある（例「入荷次第注文順に発送）」「発送日要相談（国内のみ」）。

## 0. 着手前の確認
0-1. origin/main で上の file:line が同じこと（ずれたら実物の行で）。_analysis_values の呼び出し元すべて（:896 付近ほか）で item に "ship" があること。"ship" が無い件（作り直し経路・買取単位の加工後など）がありうるなら、その経路を file:line で。
0-2. preflight。worktree は /Users/tanizawashingo/worktrees/salesanchor/release-v102-ship-note（既存。`git pull --ff-only origin main` で最新に）。

## 1. 変更（line_analysis_v102_svc.py と小さな関数1つ＋テストだけ）
1-1. 備考の文字を作る関数 `ship_note(ship: str | None) -> str | None` を line_analysis_v102_svc.py（_analysis_values の近く）に置く:
  - None・空白だけ・gemini_raw_copy_v101 の `_NONE` と同じ値 → None。"none" を文字列で書かない（_NONE を import するか、v101 側に公開名がなければ公開の別名を1つ足す）。
  - " / " でつながった値は、区切りごとに次の括弧直しをしてから " / " でつなぎ直す。
  - 括弧直し（対象の組は定数1つにまとめる: （）・()・【】・「」・［］・[]）: 閉じが足りない開き → 末尾に対の閉じを足す。開きの無い閉じ → その閉じを消す。前後の空白を除く。
1-2. _analysis_values の note_ja を `ship_note(item.get("ship"))` にする。ほかの列は変えない。
1-3. v101・v10・旧 v6（tcg_analyzer_svc.py の build_note_ja）は触らない。

## 2. テスト（既存の作法。line_analysis_v102_svc のテストファイルに追加）
- ship_note: "none"→None、None→None、" "→None、"発送日要相談"→そのまま、"入荷次第注文順に発送）"→"入荷次第注文順に発送"、"発送日要相談（国内のみ"→"発送日要相談（国内のみ）"、"【10/16発送】"→そのまま、"※発送日相談 / ※移し替えて発送予定"→そのまま、"a） / b（c"→"a / b（c）"。
- _analysis_values: ship が値を持つ件 → note_ja にその値。"none" → None。ほかの列が変わらない（既存テストが通る）。

## 3. 置き換え試験（マージ前の証拠・本番に繋がない）
- 前回の作法（scratchpad の sim_ship.py・キャッシュ replay）で、origin/main と本便 HEAD の _analysis_values の出力を 2,693 件比べる。出力 /tmp/CC報告ファイル/preorder-design/shipnote/test/: note_ja が空でない件数（期待 233）、値ごとの件数、note_ja 以外の列の変化 0、括弧を直した件の全件（前→後）。

## 4. 手順
1. 0 → 実装 → テスト → 置き換え試験 → ruff・pytest（line_analysis_v102_svc・v102 系・distribution）。frontend 無変更。
2. このカードを docs/handoff/v102-ship-note/card-PO3.md に置く（recon・design は設計者）。
3. commit（push しない）。

## 停止条件
0 で前提が違う・"ship" が無い経路がある・note_ja 以外が変わる → NEEDS_DECISION。フックに止められたら言い換えず止まる。最終行 DONE / BLOCKED: / NEEDS_DECISION:。
