# 実装カード 便D1: v102 のシステム段に人の判断を反映し、直したら配信まで回す（backend）

- 設計: [design.md](./design.md) §13（特に 13-3・13-4・13-7 の D-K1〜K6）。recon は design.md §13 冒頭と docs/handoff/v102-prod-switch/recon.md
- 発行: 2026-10-09 Claude Opus。PO: 2026-10-09「便C・便D を進める」、規則「要確認を直して回す際も投稿日時が古ければ解析して記録だけ残す、投稿日時が最新の商品であれば配信リストに加える」、同日「PRマージ、デプロイまで完走」
- 作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-v102-prod-switch-cd（ブランチ release/v102-prod-switch-cd、起点 f0d710185）。Bash は毎回 `cd <worktree> && ...`

## 0. 着手前（読むだけ。file:line で報告。前提違いは NEEDS_DECISION）
1. preflight。`git fetch origin` し、起点以降に main で line_analysis_v102_svc.py・gemini_raw_copy_v101.py・gemini_raw_copy_v102_product_first.py・tcg_analyzer_svc.py・item_corrections_svc.py・tcg_condition_review_svc.py が変わっていれば、`git merge origin/main`（rebase 禁止）してから始める。
2. product_id の判断の human_value の型: item_corrections_svc.py:59-73 の int(human_value) と、ProductMasterDrawer.tsx:420-447 が送る値（product_uuid か整数 id か）。両者が食い違う（UUID 文字列を int にしようとする）なら止まる。
3. 商品を固定する口: resolve_product_first（gemini_raw_copy_v102_product_first.py:470-506）・_product_first_fields（gemini_raw_copy_v101.py:795-807）・_extract_one（:810）・_extract_v102 の build（:1126-1153）・extract_v101_items 呼び出し（line_analysis_v102_svc.py:229-254）の引数の流れ。前後の作品で決める処理（gemini_raw_copy_v102_context_work.py:142-146 の chosen_product_id）が、固定した件を上書きしないか。
4. 状態の判断の読み方: condition_review の human_value の JSON（tcg_condition_review_svc.py:276-278）から decision と condition_id、conditions.is_active。
5. Redis の使い方の既存例（git grep "redis" backend/app で SET NX の例）と、Celery タスクの countdown の既存例。

## 1. 変更内容
### 1-1. 判断の読み込み（新規 `backend/app/services/v102_human_decisions_svc.py`、判断の読み方の唯一の置き場所）
- `load_v102_decisions(session, item_ids) -> dict[item_id, Decisions]`。Decisions = {product_id: int|None, condition_id: int|None, ack_codes: frozenset[str]}。
- 件ごとに item_corrections を corrected_at・id の降順で読み、「最後の書き写しの直し」（field_name が v102_lines・v102_price・v102_quantity・v102_item_added の行の corrected_at の最大。無ければ無し）より**後**の行だけを有効とする（同時刻は無効側）。
- product_id: 有効な最新の field_name='product_id' の human_value（0-2 で確かめた型で整数 id に）。空・不正は無視（logger.warning）。
- condition: 有効な最新の field_name='condition_review' で decision が confirm/correct、condition_id の状態が is_active のとき、その id。
- ack: 有効な最新の field_name='review_ack' の JSON の codes（v=1 のみ。不正は無視・warning）。
- 定数（field_name の文字列、REVIEW_ACK、TRANSCRIPTION_FIELDS 等）はこのファイルだけで定義。

### 1-2. 試作版に「商品の固定」を渡す
- resolve_product_first に任意の引数 `fixed_product_id: int | None = None` を足す。指定時は照合の結果に関わらず、その商品で status='matched'・product_id=fixed・work_id を products から（chosen_product_id の差し替え :483-485 と同じ作り方）。商品が products に無ければ固定しない（warning）。
- その値を run_v102_pipeline → extract_v101_items → _extract_v102 の build → _extract_one → _product_first_fields → resolve_product_first へ、件の位置（gemini_index の並びの順）ごとの dict `fixed_products: dict[int, int] | None = None` で渡す。前後の作品で決める処理（context_work）は固定した件を変えない。
- **固定が無いとき（None・空 dict）の結果は今と1文字も変わらない**（D-K2）。prompt_ab の呼び出しは変えない。

### 1-3. run_v102_analysis の変更（line_analysis_v102_svc.py）
- 件を読んだ後に load_v102_decisions。固定の商品を位置の dict にして run_v102_pipeline に渡す。
- 書き込み前に件ごとに: 商品を固定した件は pid_basis='MANUAL'。状態の判断がある件は condition_id をその id（condition_canonical は conditions から）、condition_basis='MANUAL_CONDITION_REVIEW'、理由から condition_unknown・condition_multiple_candidates を外す。ack の codes にある理由を外す。外した後に理由が空なら needs_review=FALSE・review_reasons=NULL。
- is_current の付け直し: 書き込み前にこの投稿の (product_id, condition_id) の組を読み、書き込み後に _merge_supplier_products を「前の組」も含めて呼ぶ（1-4）。

### 1-4. `_merge_supplier_products`（tcg_analyzer_svc.py:1743）
- 任意の引数 `extra_pairs: Iterable[tuple[int, int]] = ()` を足し、付け直す組をこの投稿の今の組＋extra_pairs にする。無指定なら今と同じ（v6 の呼び出しは変えない）。

### 1-5. やり直し→配信のタスク（tasks/tcg_extraction.py に追加、既存の書き方に合わせる）
- `tcg.v102_reanalyze_after_correction(extraction_job_id)`: その投稿が v102（prompt_version が `v102:`）のときだけ run_v102_analysis（Gemini は呼ばない）→ commit → 配信の予約。v6 の投稿なら何もしない（info ログ）。
- 配信の予約 `schedule_distribution()`: TCG_AUTO_DISTRIBUTE=1 のときだけ。Redis キー `tcg:distribution:scheduled` を SET NX EX 90 で取れたときだけ `tcg.auto_distribute_after_analysis` を countdown=60 で積む。取れなければ積まない（既に予約済み）。Redis 不通は既存の _enqueue_auto_distribute と同じ扱い（warning）。
- 既存の自動配信（抽出の後）はこの予約を使わず今のまま（触らない）。

### 1-6. 起動する場所（保存後にタスクを積む。v102 の件だけ）
- POST /tcg/items/{id}/corrections（item_corrections.py）: 保存成功後、その件の extraction_job が v102 なら積む。condition_review の保存（同じ API の condition_review 分岐）も同じ。
- 新規 POST /tcg/items/{id}/review-ack（super_admin。body: source_message_id, codes: list[str]（1件以上・review_reason_codes にあるもの・重複除去））: item_corrections に field_name='review_ack'、human_value=`{"v":1,"codes":[...]}`、system_value=今の review_reasons。保存後に積む。v6 の件は 409（対象外）。
- 共通の「件 → 投稿 → v102 か」を1関数にする（重複させない）。

## 2. テスト（PostgreSQL は *_pg、Redis・Celery はモック）
- D-K1〜K6（design.md §13-7）。K2 は既存の test_line_analysis_v102_pg.py の K8 と同じ材料で、判断なしの結果が変わらないこと。
- 判断の有効性: 書き写しの直しより前の判断は無効、後の判断は有効、同時刻は無効。
- review-ack API: 未登録コード 422、v6 の件 409、成功時に item_corrections に1行とタスクが1回積まれる。
- 既存テスト（test_line_analysis_v102_*、test_v102_review_source、test_prompt_ab*、test_gemini_raw_copy_v10*、test_tcg_condition_review、item_corrections 関連）が通る。

## 3. 触らない
v6 の判定・再解析の振る舞い、配信の中身（fetch_output_rows・シートの書き方）、既存の自動配信の起動、prompt_ab の出力、frontend、migrations、deploy.yml、.github/workflows。

## 4. 完了
非PG pytest（--no-cov）・ruff → commit（Co-Authored-By なし）→ push → `gh pr create --draft --base main`（worktree 内から。テンプレート起点。標準ワークフロー確認：recon docs/handoff/v102-prod-switch/recon.md、設計 docs/handoff/v102-prod-switch/design.md、対象ADR ADR-154, ADR-158。触るファイル・削除するファイルは実測からパスのみ。維持の仕組み欄に守り手（テストのパス）。push と PR 作成は別コマンド）。PR 本文に「試作版ファイルに fixed_product_id／fixed_products の任意引数を追加（指定なしは結果不変）」と明記。CI を待たない。最終行 DONE / BLOCKED: / NEEDS_DECISION:。

## 5. 止まる条件
フック・権限に止められた（言い換えず文面を貼る）／0 の前提違い／カードに無いファイルを触る必要／2通り以上に分かれる／既存テストが範囲外の原因で落ちる。
