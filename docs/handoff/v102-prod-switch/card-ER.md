# 実装カード ER: v102 で状態を決められない物は「Error」にし、理由を付けて必ず要確認へ（便ER）

設計者: Opus（2026-10-11）。PO 決定（原文）:
- 「状態が判断できなかった場合は状態はErrorにして理由を添えて要確認に回すようにしたい」
- Error にするのは「状態を決められなかった」場合だけ、PSA・鑑定・プロモ・単品・枚などの語で単品と分かった物は今の FLAG_SINGLE のまま → 「y」
- 「確立したなら進める…PRマージ、デプロイまで完走させてくれ」（2026-10-11）
根拠の調査（手元・社外秘を含む）: /tmp/CC報告ファイル/v102-cond-error-recon/（part2・part3）。社外秘の原文はリポジトリ・PR に書かない（テストは合成した文で）。

## 0. 着手前の実物確認（必須。ずれたら NEEDS_DECISION で止まる）
origin/main で次が説明どおりかを確かめ、報告の先頭に書く。
- backend/app/services/gemini_raw_copy_v102_product_first.py: _resolve_condition :480-493（:490-492 で商品不明＋単位不明のときだけ "不明"＋condition_unknown）、定数 :62 :68-75、resolve_product_first :525-568
- backend/app/services/tcg_analyzer_svc.py: resolve_condition_v2 最終フォールバック :903-904（basis "R4:単位既定:単位不明"）、_find_cond_id :907-912、load_condition_entries :647-725（priority>0）、match_keyword :331-332（search_kw 空なら当たらない）
- backend/app/services/line_analysis_v102_svc.py: _condition_columns :539-550、_analysis_values :558-587、_apply_decisions :646-665、_apply_soldout_targets :673-692（:689 FLAG_ 接頭辞）、CONDITION_UNDECIDED_PREFIX :92、_load_condition_canonicals（:615-621 付近）
- backend/app/services/tcg_condition_review_svc.py: review_joins :84-179（cr の列 :162-177）、condition_options :205-208、save_condition_review :219-295
- backend/app/services/tcg_distribution_svc.py: cond_filter :206-213 と :307-313、WHERE :260-267 と :332-339、除外内訳 :346-366
- backend/app/routers/item_corrections.py: review-ack :177-203。backend/app/services/v102_human_decisions_svc.py:53 _ACTIVE_CONDITIONS_SQL、:257-259 unknown_codes。backend/app/services/review_reason_codes_svc.py（details を作る :34-38）
- frontend/src/features/tcg-analysis-review/ConditionReviewPanel.tsx:22-23（relevant）、ReviewItemDrawer.tsx:81-90（「このままで良い」）

## 1. 変更
### 1-1. Error の状態（データ。SSOT は public.line_conditions、値はここ1か所）
- 1行追加（docs/handoff/v102-prod-switch/data/conditions/ に er_precheck / er_dryrun / er_commit / er_verify / er_rollback .sql と README 追記。kw_*.sql と同じ型: DO ブロックなし・$ と二重引用符なし・件数違いはゼロ除算で失敗。ファイルは Write ツールで作る）:
  - INSERT INTO public.conditions (code, canonical, app_kubun, is_active, priority, search_kw, exclude_kw, match_type, effect, note) VALUES ('CN0012', 'Error', '', true, 99, '', '', 'KEYWORD', 'EXCLUDE', '状態を決められなかった（v102 の最終フォールバック）。配信しない。人が正しい状態を選ぶ（PO 2026-10-11）')
  - precheck: CN0012 と canonical 'Error' が無いこと、行数 13、effect='EXCLUDE' の行 0。verify: 行数 14・CN0012 の全列。rollback: CN0012 だけ削除（ただし analysis_results.condition_id が参照していたら失敗する＝戻す前にコードを戻して再解析が必要、と README に書く）。
  - priority 99・search_kw 空・match_type KEYWORD なので照合には当たらない（match_keyword :331-332）が、cond_entries に入り _find_cond_id と _condition_columns で引ける。
- effect='EXCLUDE' の意味をこの便で「配信しない状態」と定める（今までどこからも読まれていない列。全13行 OUTPUT。設計 docs/handoff/rule-table-unification/design.md の「EXCLUDE=ヒット時に除外」と同じ向き）。

### 1-2. v102 で Error を付ける（v102 経路だけ。resolve_condition_v2 本体・v6・v10.1・shadow は変えない）
- _resolve_condition（product_first）で、resolve_condition_v2 の結果が FLAG_SINGLE かつ basis に BASIS_UNIT_UNKNOWN を含むとき（＝最終フォールバック。商品・単位の区分に関係なく）、状態を Error にし、理由 condition_unknown を付ける。basis は変えない（"R4:単位既定:単位不明" のまま。tcg_supplier_quality_svc の集計と soldout_ref の condition_decided_by_word がこの文字を読むため）。
- Error の canonical 名はコードに直書きしない。定数は code だけ（例 CONDITION_ERROR_CODE = "CN0012"、既存の "CN0008" "CN0011" と同じ型）。canonical は masters（cond_entries）から code で引く（_find_cond_id と同等）。引けない（行が無い）ときは今と同じ "不明"→FLAG_SINGLE＋condition_unknown に倒す（安全側）。
- 語で決まった FLAG_SINGLE（basis "R1:…"）は変えない。
- 箱の再判定分岐（:484-488）も最終フォールバックに落ちた場合は同じ扱い（コード上は箱系で必ず返るが、条件は同じ関数で書く）。

### 1-3. 配信しない（SSOT は effect）
- review_joins の最終 LATERAL（:162-177）に、cr.condition_id の状態の effect を cr.effect として出す（cr_selected / cr_ack_condition 等の既存 JOIN を使うか、public.conditions を condition_id で LEFT JOIN）。
- 配信の cond_filter 2か所（:206-213, :307-313）に `AND cr.effect IS DISTINCT FROM 'EXCLUDE'` を足す（include_flag_single の分岐の外側で常に効く）。除外内訳（:346-366）は既存の FLAG の数え方に EXCLUDE も含めるか、別の数を足すかを、画面の表示文言（i18n キー）を確かめて決め、決めた理由を報告に書く（新しい表示文言が要るなら ja/en に足す）。
- tcg_analysis_review_svc.py:45・tcg_import_progress.py:129 など review_joins の他の利用先が cr.effect の追加で壊れないこと（SELECT * を使っていないか）を確かめる。

### 1-4. 人が状態を選べるようにする
- ConditionReviewPanel.tsx の relevant に「review_reasons に condition_unknown がある」を足す（既存の文言・金型 Select・Button のまま。新しい部品・色・直書きを足さない）。
- 選択肢から effect='EXCLUDE' の状態を外す: condition_options（:205-208）の SQL に `AND effect IS DISTINCT FROM 'EXCLUDE'`。
- 保存の検査: save_condition_review と v102_human_decisions_svc の _ACTIVE_CONDITIONS_SQL で、effect='EXCLUDE' の状態は選べない（422 / 無効扱い）。
- 「このままで良い」で condition_unknown を外せないようにする: ack できない理由コードの一覧をバックエンドの1か所の定数にし（例 NON_ACKABLE_REASON_CODES = {"condition_unknown"}）、review-ack はそれを含む要求を 422 で断る。review_reason_codes_svc の details に ackable（bool）を足し、ReviewItemDrawer.tsx は detail.ackable が false のとき「このままで良い」を出さない（フロントに理由コードを直書きしない）。API 型（frontend の型定義）も合わせる。

### 1-5. 〆の引き継ぎ
- _apply_soldout_targets（:689）の「決まっていない状態」の判定を、canonical の FLAG_ 接頭辞に加えて effect='EXCLUDE' の状態も含める（_load_condition_canonicals で effect も読む）。CONDITION_UNDECIDED_PREFIX のコメントも直す。

## 2. テスト（合成で）
- E1 v102: 最終フォールバックの件 → condition Error（CN0012 の id）・basis "R4:単位既定:単位不明"・review に condition_unknown・needs_review。商品が特定済み・単位あり（Set/Piece）の件でも同じ。
- E2 R1 の語で決まった FLAG_SINGLE は変わらない。
- E3 Error の行（CN0012）がマスタに無い時は従来どおり FLAG_SINGLE＋condition_unknown。
- E4 配信: effect='EXCLUDE' の状態の行は needs_review=false でも出ない（PG テスト）。include_flag_single=true でも出ない。
- E5 review-ack に condition_unknown を含めると 422。details の ackable が false。他のコードは従来どおり ack できる。
- E6 condition_options に EXCLUDE の状態が出ない。EXCLUDE の状態を選んだ保存は 422。
- E7 〆の相手が Error のとき理由と needs_review を変えない。
- E8 v6・v10.1・shadow（resolve_condition_v2 を直接使う経路）の結果が変わらない（回帰）。
- E9 フロント（vitest）: condition_unknown の件で ConditionReviewPanel が出る。ackable=false の理由に「このままで良い」が出ない。
- ローカルで動くテストは全部実行（pytest 関係ファイル・ruff・frontend npm run check:all・関係 vitest）。PG テストは CI。

## 3. 置き換え試験（社外秘・repo 外。マージ前の証拠）
- 便G と同じ手順（/tmp/CC報告ファイル/v102-gemini-trust/ の取得・比較スクリプトを流用、本番は読み取りのみ）で、v102 is_current がある全ジョブを変更前（origin/main）と変更後に通して比べる。マスタには CN0012 の行を手元で足した形で変更後を流す（本番にはまだ無い）。
- 出すもの（replay.md）: R1 件数／R2 状態が変わった件の全件（期待: FLAG_SINGLE かつ basis に単位不明 → Error だけ）／R3 状態以外（商品・単位・価格・数量）の変化（期待 0）／R4 理由の増減（期待: condition_unknown の増加だけ）／R5 現在配信対象で配信されなくなる件（期待 0。FLAG_SINGLE は今も配信されないため）／R6 Error になる件のうち今は要確認でない件の数（本番 8件前後）。
- 停止条件（担当は数字を出して止まる）: R3・R5 が 0 でない、R2 に期待以外の変化。

## 4. 文書
- docs/handoff/v102-prod-switch/card-ER.md にこのカードを置く。design.md §17・recon.md §10 は設計者が書く。

## 5. 手順
1. `bash scripts/new-worktree.sh release/v102-condition-error --claude`（最後の claude --print のエラーは無視、worktree ができたか確認）→ その中で `./scripts/dev/executor-preflight.sh`。Bash は毎回 `cd <worktree> && …` の単独の呼び出しで（cd が worktree 外で始まるとフックがブランチを判定できず止まる）。
2. 0 の実物確認 → 実装 → テスト → 置き換え試験 → ruff・pytest・npm run check:all。
3. commit（feat:、末尾 Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>）。push・PR・本番書き込みはしない。

## 停止条件
- カードの前提と実物が違う、共有経路（resolve_condition_v2 本体など）を変えないと実装できない、金型に無い UI 部品が要る → NEEDS_DECISION。
- フックに止められたら言い換え再試行せず停止報告。最終行 DONE / BLOCKED: / NEEDS_DECISION:。
