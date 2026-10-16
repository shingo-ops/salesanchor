# 実装カード: v6→v102 やり直しの道具

- 設計: docs/handoff/reextract-v6-with-v102/design.md（r5 APPROVE、review-opus.md「## r5 審査」）
- 実装の承認: PO の「y」（2026-10-16。v6 の投稿を Gemini でやり直す）＋離席一任（2026-10-15）。本カードの範囲に限る。
- ブランチ・作業場所: release/reextract-v6-with-v102（/Users/tanizawashingo/worktrees/salesanchor/release-reextract-v6-with-v102）

## 作るもの（新規ファイルのみ）
1. backend/app/tools/reextract_v6_with_v102.py
   - design §3 の D1〜D5 を、そのとおりに作る。
   - 審査の「実装カードに書くべき注意点」（review-opus.md の r2 の節）の 1〜6 を守る。
2. backend/tests/test_reextract_v6_with_v102_pg.py
   - design §7 の試験を全部入れる。
   - DB は既存の PG 試験の作法（例: backend/tests/test_line_analysis_v102_pg.py）に合わせる。試験DBは試験後に消す。
   - Gemini は prohibit_live_gemini の fixture を import して効かせる。Gemini と解析の中身は mock にする。
3. scripts/ops/reextract-v6-loop.sh（ホストで動かす繰り返し。design D6、r3 の m6）
   - 名前を付けて置くだけ。本番では Opus が使う。
   - コンテナ名は `reextract-v6-YYYYMMDD-N`。

## 触らない範囲
- 既存のファイルはすべて変えない。backend/app 以下の既存モジュール・migrations・workflow・docker-compose を含む。
- 既存の関数は、import して呼ぶだけにする。
  - run_v102_extraction, run_v102_analysis, _load_resolved_pairs, _merge_supplier_products, load_extraction_context, _apply_pre_extraction_filter, _publish_review_changed, get_engine
  - 名前と引数は実物で確かめる。

## 実物点検（作る前に。結果は報告に file:line で書く）
- 上の関数の、実際のシグネチャと置き場所。
- Gemini client を作る関数（gemini_extraction_svc.py:248-276 付近の _get_genai_client 等）。
  - 道具の中だけで包み、HttpOptions(timeout=300000) を付けられるか。
  - 手元の google-genai の版を書く。
- llm_usage_events の列（source_ref, occurred_at, cost_usd）。
- Dockerfile の appuser の uid。

## 想定分岐（当たったら止めて BLOCKED: で報告する）
- 既存ファイルを変えないと作れない。
- 関数のシグネチャが設計と違い、意味が変わる。
- HttpOptions の timeout を、道具の中だけでは付けられない。
  - この場合は、signal.alarm だけで作れるかを書いて止まる。

## 検証（実行して生出力を /tmp/CC報告ファイル/v6-to-v102/impl/ に保存）
- `cd backend && python -m pytest tests/test_reextract_v6_with_v102_pg.py -q`（PG が無ければ、そのことを書く）
- ruff・型チェック等、リポジトリの既存の lint を新規ファイルにかける。
- `python -m app.tools.reextract_v6_with_v102 --help`

## コミット
- docs/handoff/reextract-v6-with-v102/ の recon.md・design.md・review-opus.md・card.md も git add する。
- コミットメッセージの末尾は `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。
- push はしない（Opus がする）。
