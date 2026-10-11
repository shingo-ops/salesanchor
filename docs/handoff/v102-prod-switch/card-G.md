# 実装カード G: v102 は Gemini の抽出を採用し、システムの上書きをやめて「確認役」にする（便G）

設計者: Opus（2026-10-11）。PO 決定（原文）:
- 「A4,A6,A7,A11,A12,は不要なので廃止する」
- A4 は残す・A11 は上書きをやめて確認役（食い違ったら理由を添えて要確認）にする案に「y」
- A15「理由も付ける」、A16「全件停止でなくズレた部分だけ分析して特定することは出来る？」→ できると回答
- A17「残す」
- 「確立したなら進める…PRマージ、デプロイまで完走させてくれ」
A10（名前の無い件をさかのぼって取る）は「数えてお見せしてから決める」と回答済み＝本便の対象外。

根拠の調査（社外秘を含むため repo 外）:
- /tmp/CC報告ファイル/v102-system-decisions/list.md（システム判断の一覧 A1〜A17・B1〜B10・C1〜C6、基準 origin/main 994543744）
- /tmp/CC報告ファイル/v102-swap-rca/（状態入れ替わりの原因: reassign_ambiguous の並び方の証拠、再現 repro.py）
- /tmp/CC報告ファイル/v102-kw-kenpin/（「検品のため開封済み」追加と再解析の前後 diff6.txt）
社外秘の原文はリポジトリ・PR に書かない（テストは合成した文で作る）。

## 0. 着手前の実物確認（必須。ずれたら NEEDS_DECISION で止まる）
origin/main で次の file:line が下の説明どおりかを確かめ、結果を報告の先頭に書く。
- gemini_raw_copy_v101.py: reassign_ambiguous :555-590（呼び出し :1347）、_apply_f1 :958-980（呼び出し :1265）、_extract_one :853 付近の resolve_price_quantity 呼び出し :883-887 と _fill_from_copy :843-850/:888-890、_single_number :829-840、_quantity_not_in_text :795-806、_item_reasons（:1200-1212 付近、price_unresolved / quantity_unresolved を付ける所）、parse_v101_response :184-240（accepted の件に gemini_index が無い）
- line_analysis_v102_svc.py: run_v102_pipeline :243-（:260 で extract_items(..., reassign=True, v102_fixes=True, ...)）、_bounded_number :514-521、_analysis_values :543-565、_map_to_rows :492-511、_lines_agree :473-489、run_v102_analysis の try/except :922-949
- extraction_judgement_svc.py: resolve_price_quantity :599-680（price_reasons に gemini_disagrees を入れる :673-676）

## 1. 変更（v102 経路だけ。v6・v10・v10.1（v102=False）・shadow の挙動は変えない）
共通の切り替え: v102 の呼び出し（line_analysis_v102_svc.run_v102_pipeline → extract_items/extract_v101_items の v102=True 経路）でだけ効くようにする。既存の引数（reassign・v102_fixes・v102）で分けられるならそれを使い、新しい引数を足す場合は v102 経路からだけ渡す。

### 1-1. A6 廃止（迷う行の付け直し）
- v102 経路では reassign_ambiguous を呼ばない（svc :260 の reassign=True を False にする等）。迷う行は Gemini の付け方のまま使う。
- reassign_ambiguous が作っていた「決まらない迷う行」の要確認（review の kind ship / condition）も v102 では出なくなる。これは PO 決定（Gemini を採用）どおり。
- 関数本体は v10.1 等が使うので消さない。

### 1-2. A7 廃止（F1 親の見出しを外す）
- v102 経路では _apply_f1 を呼ばない（F2・F3・F5 は残す）。

### 1-3. A11・A12 → Gemini の数字を採用し、原文の読み直しは確認役
- v102 経路の _extract_one で:
  - price_normalized = _single_number(item["price"])、quantity_normalized = _single_number(item["quantity"])（Gemini の写しから数字1つ。万・千・億・k は None、0個・2個以上は None。既存 _single_number をそのまま使う）。
  - pq = resolve_price_quantity(...) は従来どおり計算するが、値には使わない（確認役）。
  - 確認: Gemini の値と pq の値が「両方とも数」で「違う」とき、理由 price_source_mismatch / quantity_source_mismatch を付ける。pq が None の時は比べない（理由を付けない）。比較は数として（Decimal か float の == で、カンマ除去後の数）。
  - _fill_from_copy は v102 では使わない（A12 廃止。上の採用で置き換わる）。関数を使う場所が無くなるなら削除してよい（テストも合わせる）。
- 安全網（便PQ）はそのまま: Gemini の写しに数字があるのに値が None → price_unresolved / quantity_unresolved（:1200-1212 付近の既存判定）。
- quantity_not_in_text（A13）は従来どおり理由を付ける（Gemini の数量の数字が件の行の原文に無い）。値は Gemini の数のまま（要確認で配信されない）。
- 価格の行（A4）・A1〜A3 の落とす判定は変えない。

### 1-4. A15 理由を付ける
- svc の _bounded_number で入力が非 None なのに範囲外・変換例外で None にした時、理由 value_out_of_range を付け、needs_review=True にする（_analysis_values で reasons に足す。既存の reasons の連結の書き方に合わせる）。

### 1-5. A16 ずれた件だけ要確認
- parse_v101_response（keep_rejected=True のとき）で、受理した件にも gemini_index（応答の中の位置 index）を持たせ、v102 の件まで運ぶ（途中で dict を作り直す所で落ちないことをテストで確かめる）。
- _map_to_rows を「gemini_index で対応」に変える。_response_from_rows は rows の順に応答を作るので、応答の位置 index i は rows[i] に当たる（rows は gemini_index 昇順で読む :922-923）。
- 対応する件が無い行、または _lines_agree が偽の組は、その行だけ「値は空（product_id・unit・condition・価格・数量 None、condition は既存の未解決の扱い）＋ 理由 item_mapping_mismatch ＋ needs_review=True」で書く。他の行は通常どおり書く。
- それ以外の例外（プログラムのエラー）は従来どおり投稿全体を止めて extract_exception（A17・try/except はそのまま）。

### 1-6. 理由コード4つ（SSOT は public.review_reason_codes。値はここ1か所）
- price_source_mismatch / quantity_source_mismatch / value_out_of_range / item_mapping_mismatch（source=system, fix_stage=analysis）
- コード側の定数（既存の理由コード定数と同じ場所・書き方）と tests/test_review_reason_codes_consistency.py の _code_side_constants に追加。
- frontend/src/locales/ja.json・en.json の reviewReason に:
  - price_source_mismatch: 「価格がGeminiと原文で違う」／"Price differs between Gemini and source"
  - quantity_source_mismatch: 「数量がGeminiと原文で違う」／"Quantity differs between Gemini and source"
  - value_out_of_range: 「数値が大きすぎる」／"Value out of range"
  - item_mapping_mismatch: 「件の対応が合わない」／"Item mapping mismatch"
- docs/handoff/v102-prod-switch/data/review_reason_codes/ に便PQ（seed_20261010_quantity_unresolved.sql と qu_*.sql）と同じ型で: seed_20261011_gemini_trust.sql（4行）、gt_precheck.sql（ROWS|31・HAS_NEW|0・PRECHECK_DONE）、gt_dryrun.sql（4行 INSERT→CHECK_OK 4→ROLLBACK・DRYRUN_OK）、gt_commit.sql、gt_verify.sql（ROWS|35・VERIFY_DONE）、gt_rollback.sql（その4コードだけ削除）。README.md に「追加（便G）」節。SQL に $ と二重引用符を使わない（ssh -c で渡すため）。DO ブロックは使わず、前例 kw_commit.sql の「WITH … RETURNING → CASE で件数検査（違えばゼロ除算）」型にする。ファイルは Write ツールで作る。
- migration は作らない（ADR-1007）。

### 1-7. 前の作業の記録を同じ PR に含める
- /Users/tanizawashingo/worktrees/salesanchor/release-condition-kw-kenpin-kaifu/docs/handoff/v102-prod-switch/data/conditions/（kw_*.sql・README.md。「検品のため開封済み」追加、本番 COMMIT 済み 2026-10-10T21:2xZ）を新しい worktree の同じパスへ写す。README の記録欄に本番実行の結果（/tmp/CC報告ファイル/v102-kw-kenpin/kw_commit.log・kw_verify.log の内容）と「再解析で状態の入れ替わりが起きた→原因は A6、便G で廃止」を追記。

## 2. テスト（合成した文で）
- A6: 「商品名 / 4BOX@17,800円 / ダメージ有り / 5BOX@16,000円」＋ 投稿の別の所に「価格の行 / 状態語の行 / 空行」の形がある投稿で、Gemini が {名前,価格1} と {名前,ダメージ,価格2} に分けた時、v102 は付け直さず、価格2の件だけダメージになる。v10.1 経路では従来どおり付け直すこと（回帰）。
- A7: 発送の言葉のある共有の見出しが v102 では件の lines に残る。v10.1 では従来どおり外れる。
- A11: Gemini price "17,800円"・原文も 17,800 → 17800・理由なし。Gemini price "17,800円"・原文の読み直しが 16,000（合成で作る）→ 値は 17800・price_source_mismatch。pq が None → 理由なし。数量も同様。Gemini "2万"→ None ＋ price_unresolved。
- A15: 10**12 以上 → None ＋ value_out_of_range ＋ needs_review。
- A16: 件が1つ欠けた／行番号が合わない合成ケースで、その行だけ item_mapping_mismatch、他の行は通常どおり書かれる。プログラムのエラーは従来どおり extract_exception。
- 理由コード整合テスト・既存テスト全部（v102 の期待値が変わるものは、変わる理由をコメントに書いて直す。v10.1 側の期待値は変えない）。
- ローカルで動かせるテストは全部ローカルで実行（pytest 関係ファイル・ruff・frontend の npm run check:all）。PG テストは CI。

## 3. 置き換え試験（社外秘・repo 外。マージ前の証拠）
- 本番を読み取り専用で、v102 の is_current がある全ジョブ（engine_version='v102-f_c'）の extraction_items・source_messages.raw_text・必要マスタを取得し、/tmp/CC報告ファイル/v102-gemini-trust/ に保存。
- 変更前（origin/main）と変更後（このブランチ）のシステム段（run_v102_pipeline 相当。DB を使わない形）に同じ入力を通し、件ごとに比べる。DB が要る部分（followup・〆の参照・人の判断）で比べられないものは何かを書く。
- 出すもの（replay.md）:
  - R1 件数: 全件・比べた件・比べられない件
  - R2 状態が変わった件の全件（job8・行・前→後・原文の該当行は手元ファイルにだけ）。a1a120c6 / a100097a の16件が正しい形に戻るか
  - R3 価格・数量の値が変わった件の全件と理由
  - R4 新しい理由（4コード）が付く件数と全件
  - R5 現在配信対象（is_current・needs_review=false・price 有り）の件のうち、変更後に要確認になる件数と割合
  - R6 迷う行を Gemini が両方の件に入れている件の数（A6 廃止で両方に同じ状態が付く件）
- 停止条件（設計者が判断するので、担当は数字を出して止まる）: R5 が 5% を超える、R2/R3 に説明できない変化がある。

## 4. 文書（リポジトリ）
- design.md §16・recon.md §9 は設計者（Opus）が書く。担当はこの card-G.md を docs/handoff/v102-prod-switch/card-G.md に置く。

## 5. 手順
1. `bash scripts/new-worktree.sh release/v102-gemini-trust --claude`（最後の claude --print のエラーは無視してよい。worktree ができたか確認）→ その中で `./scripts/dev/executor-preflight.sh`。Bash の cwd は毎回戻るので `cd <worktree> && …` で実行。
2. 0 の実物確認 → 実装 → テスト → 置き換え試験 → ruff・pytest・npm run check:all。
3. commit（feat:、末尾に Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>）。push・PR 作成はしない（設計者が文書を足してから指示する）。

## 停止条件
- カードの前提と実物が違う、共有経路（v10.1 等）を変えないと実装できない → NEEDS_DECISION。
- フックに止められたら言い換え再試行せず停止報告。本番は読み取りのみ（書き込みはしない）。
- 最終行は DONE / BLOCKED: / NEEDS_DECISION:。
