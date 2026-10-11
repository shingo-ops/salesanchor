# recon: v102 で円・¥を除いた探し直しで価格の行を見つけた件に記録（price_basis）を残す

調査 2026-10-11（Opus 設計・Sonnet 調査）。作業場所の起点 origin/main f98fea0d5。社外秘の原文は書かない。

## 背景
- PR #4135 で、価格の写しが原文に無いときだけ円・¥・￥を除いて探し直すようにした。その件には印が残らず、後から件単位で数えられない。
- PO 2026-10-11「記録は残したい」。条件：配信・要確認（needs_review・review_reasons）・画面の動きを変えない。

## 事実（根拠つき）
- 探し直しの分岐：`backend/app/services/gemini_raw_copy_v101.py:174`（`_priced_line` :162-181、返り値は行番号のみ）。呼び出しは `backend/app/services/gemini_raw_copy_v101.py:200`（`_price_line` :195-201）だけで、`_price_line` の呼び出しは `backend/app/services/gemini_raw_copy_v101.py:249`（`parse_v101_response`）だけ。
- 受理した件の辞書：`backend/app/services/gemini_raw_copy_v101.py:260-261`（lines・price・quantity・price_line、v102 は gemini_index も）。
- 件を作り直す `build()`：`backend/app/services/gemini_raw_copy_v101.py:1337-1343`。`_extract_one`（:933-950）は固定キーの新しい辞書を返すので、足したキーはここで落ちる。gemini_index は `build()` で明示コピーしている（同じ形で足せる）。後続の作り直し（:1112・:1137・:1162・:1187）は全部 `build()` を通る。
- 結果の列：`backend/app/services/line_analysis_v102_svc.py:571-600` `_analysis_values`（pid_basis :590、condition_basis :594）。書き込みは `backend/app/services/line_analysis_v102_svc.py:603-620` `_UPSERT_SQL`（列・VALUES・ON CONFLICT の3か所を明示列挙）だけ。
- 配信は `analysis_results.needs_review` だけを見る（`backend/app/services/tcg_distribution_svc.py:293`、`backend/app/services/tcg_distribution_svc.py:364`）。needs_review は件の review 等から作る（`backend/app/services/line_analysis_v102_svc.py:590-598`）。
- 他の箇所の analysis_results への UPDATE はすべて列を明示しており、新しい列に触れない（`backend/app/services/item_corrections_svc.py:66`、`backend/app/services/tcg_condition_review_svc.py:308` ほか）。analysis_results を `SELECT *` で API に返す箇所は無い。frontend に pid_basis・condition_basis の読み手は無い。
- 本番（2026-10-11 読み取り）：analysis_results は public と tenant_001 にある。v102 が書くのは public（`backend/app/services/tcg_analyzer_svc.py:57`）。
- migration の前例：`migrations/20261009_180000_v102_engine_columns.sql`（構造のみ・ADD COLUMN IF NOT EXISTS・COMMENT）、`migrations/20260923_120000_add_work_id_to_analysis_results.sql`。登録は `scripts/run_all_migrations.sh` 末尾（直近 :900）。deploy.yml は run_all_migrations.sh を呼ぶだけ（`.github/workflows/deploy.yml:53`）。
- SQLAlchemy の models に analysis_results は無い（`backend/app/models.py`）。

## 既存 ADR 検索
- `git grep -n -i -E "price_basis|pid_basis|condition_basis|analysis_results" -- docs/adr/` と `docs/adr/FEATURE-INDEX.md` を確認。根拠列の決まりを定める ADR は無い。
- 関係する決まり：ADR-1007（migration は構造だけ・冪等）、ADR-135（migrations/ を含む実装は PO GO まで main にマージしない）、ADR-136（危険 PR の GO 手順）、ADR-154（配信は needs_review=false に限る、`docs/adr/ADR-154-tcg-parity02-gas-python-migration.md:70`）。

## 既存の試験
- 辞書全体を比べる試験：`backend/tests/test_gemini_raw_copy_v101.py:854`・`:865`（印を常に足すと壊れる。探し直しのときだけ足せば影響なし）。
- 実 DB 試験で migration を当てる前例：`backend/tests/test_line_analysis_v102_pg.py:37-45`、`backend/tests/test_tcg_work_matching_integration.py:231-234`。
