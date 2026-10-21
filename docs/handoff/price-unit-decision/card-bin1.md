# 実装カード: 値段で単位を決める 便1（物差しの時点を投稿日時にする）

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・03-file.md・04-worktree.md・05-pr.md・10-executor.md

受領確認: 着手前に「カード受領・worktree release/price-unit-bin1」と 1 行返してから始める。

PO 実装承認: 2026-10-21「1」（買取価格と自社の値段で先に作り、他社は取り込むお店を決めてから後で足す。最初の分＝便1・便2 を作る）。設計: docs/handoff/price-unit-decision/design.md（PR #4585、審査 APPROVE 264befe05、Fable APPROVE）。決定: docs/adr/ADR-1036-price-decides-unit.md。

## 作業場所
- 既に作ってある worktree `/Users/tanizawashingo/worktrees/salesanchor/release-price-unit-bin1`（ブランチ release/price-unit-bin1、origin/main 起点）の中だけで作業する。本店（~/salesanchor）で checkout・編集しない。
- 開始時に `./scripts/dev/executor-preflight.sh || exit 1`。
- このカード自身（card-bin1.md）は Opus がこのブランチに置く。消さない。

## やること（design.md「コードの変え方 → 便1」をそのまま）
1. `backend/app/services/line_analysis_v102_svc.py`
   - `_POSTED_AT_SQL`／`load_posted_date`（:1458-1468 付近）の隣に、同じ SQL で日時のまま返す `load_posted_at(session, extraction_job_id)` を足す。
   - `_buyback_units`（:962 付近）: 対象がある（:966 の判定が真）ときだけ、SAVEPOINT（:969 `session.begin_nested()`）の**中で** `load_posted_at` を 1 回呼ぶ。失敗したら今の except に入り「この投稿では決めない」。`posted_at` が None なら何もしない（今の values のまま）。`apply_buyback_units` に `posted_at` を渡す。
2. `backend/app/services/v102_buyback_unit_svc.py`
   - `apply_buyback_units(..., posted_at)`（:194）と `load_medians(session, product_ids, max_age_days, posted_at)`（:155）に `posted_at` を**必須**引数（既定値なし）で足す。
   - `_MEDIAN_SQL`（:54-65）: LATERAL の中に `AND l.fetched_at <= :posted_at AND l.fetched_at >= :posted_at - make_interval(days => :days)` を足し、`AND sp.last_seen_at >= now() - make_interval(days => :days)` を消す。他は変えない。
3. 既存テストの直し（この 2 本の、design.md に書いた箇所だけ）
   - `backend/tests/test_v102_value_overrides.py:204-209` の `fake_apply` の引数。
   - `backend/tests/test_v102_buyback_unit.py`: :185-188（SQL の確認を、上の 2. で足す 2 つの条件の文字列の確認に替える）、:161-168（値の dict に posted_at）、:71-72 `_apply`・:158・:173（posted_at を渡す）、:203-212 `_WriteSession`／`_Session.execute`（`_POSTED_AT_SQL` に投稿日時を返す。:238・:249 が今どおり通る）。
4. 足すテスト（`backend/tests/test_v102_buyback_unit.py`）
   - 投稿日時より後の値・31 日前の値を物差しに使わない（SQL に渡る値と条件で確かめる）。
   - `posted_at` が None なら values が変わらない。
   - `load_posted_at` が例外なら、この投稿では決めない（values が変わらず、保存全体は続く）。
5. 記録 SQL（ADR-1007）を作る: `docs/handoff/price-unit-decision/data/bin1/` に precheck.sql・dryrun.sql・commit.sql・rollback.sql・verify.sql。形は前例 `docs/handoff/v102-buyback-unit/data/` をそのまま写す。
   - 中身: `tcg_distribution_settings` の `unit_buyback_max_age_days` を 7 → 30、`note` を「買取価格による単位・状態の判定: 行の投稿日時より前の、この日数以内の買取の値だけを使う」。
   - precheck は「今 7 で、行が 1 行だけ」を確かめ、違えば止まる形。dryrun は ROLLBACK で終わる。rollback は 7 と元の note に戻す（元の note は前例の commit.sql から写す）。
   - 本番では流さない（PO が後で `!` で流す）。

## 触らない範囲
- 上記以外の製品コード・既存テスト・frontend・migrations・deploy.yml・本番 scripts。
- 対象 `is_candidate`・帯・状態・basis・`decide_code`・`_write_results` の順序（便2 以降）。
- 本番 DB・設定値（記録 SQL を作るだけ）。

## 想定分岐（迷ったら停止し、Opus へ NEEDS_DECISION: で返す）
- 行番号が design.md とずれている → 名前で探して直す。中身が設計と違う（例: SAVEPOINT の外でしか呼べない形、`_MEDIAN_SQL` の LATERAL の形が違う）なら止める。
- 上の 2 本以外の既存テストが落ちる → 直さずに止める。
- 前例 `docs/handoff/v102-buyback-unit/data/` が無い・形が読めない → 止める。
- `tcg_distribution_settings` の列名が前例と違う → 止める。

## 完了の条件
- ローカルで `backend/tests/test_v102_buyback_unit.py`・`backend/tests/test_v102_value_overrides.py`・`backend/tests/test_gemini_raw_copy_v102_unit_state_set.py` と、`line_analysis_v102` を含むテストが通る（生出力をファイルへ）。
- `gh auth status` で shingo-cc を確認し、worktree 内から `gh pr create --base main`。migration を含まないので Draft にしない。本文はテンプレ起点で「### 標準ワークフロー確認」（recon/design は docs/handoff/price-unit-decision/、対象 ADR-1036、触るファイルを 1 行カンマ区切り、削除するファイル なし、PO 承認 2026-10-21「1」）。社外秘の原文・投稿番号は入れない。
- 報告は DONE / BLOCKED: / NEEDS_DECISION: で、PR URL・HEAD・テスト生出力のパス。

END OF CARD
