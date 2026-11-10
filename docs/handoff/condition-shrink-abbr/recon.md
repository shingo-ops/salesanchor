# recon: 状態の略語（シュリあり・シュリンク有り 等）を足す前の試し

状態: 草案（Opus 作成・2026-11-09）。根拠は origin/main d1580a38b（作業場所 release/condition-abbr-trial）と本番の読み取り専用の問い合わせ。

## 1. 目的（PO の言葉）

- 商品名の直後に「有」と〆の印が続く行の〆を、未開封の箱（シュリンク付き）だけに当てたい。そのため「有」「シュリあり」等を状態の言葉として覚えさせたい（PO 2026-11-09）。
- 語を足すと、状態の決め方以外にも「その行が状態の行か商品名の行か」の判定が変わることが分かった（下の §3）。PO は「5つ全部を足す前に、134 投稿を本番を変えずに解析し直し、前と後の結果を比べる試しを作る」を選んだ（PO 2026-11-09「2」）。

## 2. 既存 ADR・設計の検索

- `git grep -il "replay_diff\|やり直し" docs/adr/` → 該当の ADR なし。やり直しの道具は設計 `docs/handoff/v102-heading-and-unit/design-heading.md:136-147`（「試験」）で作られた。
- ADR-1007（状態マスタの値はデータの SQL で入れる）: 語を足す本番の手順は `docs/handoff/v102-rule-fixes/data/bin1/`（precheck/dryrun/commit/verify/rollback）の形。本試しでは本番の表を変えない。
- ADR-1041 What 5（見出し）: 同じ道具で前後比較した前例。

## 3. 観測事実（file:line）

### 3-1. 語の流れ（状態の語は 1 か所から読まれる）

- 状態の表の読み込み: `/Users/tanizawashingo/worktrees/salesanchor/release-condition-shrink-abbr/backend/app/services/line_analysis_v102_svc.py:222` `analyzer.load_condition_entries(session, include_scoped_groups=True)` → `:224` cond_entries → `:230-236` masters に入れ、`:235` `with_cond_terms(..., build_cond_terms(cond_entries))` で除外語の判定用の語も同じ cond_entries から作る。
- 1 行の中身: `/Users/tanizawashingo/worktrees/salesanchor/release-condition-shrink-abbr/backend/app/services/tcg_analyzer_svc.py:750-760` に `code`・`canonical`・`search_kw`・`exclude_kw`・`match_type` を持つ辞書。
- 状態の行の判定の語: `/Users/tanizawashingo/worktrees/salesanchor/release-condition-shrink-abbr/backend/app/services/gemini_raw_copy_v101.py:356-368` `_state_words(cond_entries)`（cond_entries の search_kw から作る）。
- 除外語用の語: `/Users/tanizawashingo/worktrees/salesanchor/release-condition-shrink-abbr/backend/app/services/extraction_judgement_svc.py:262-275` `build_cond_terms(cond_entries)`。
- 表を直接読むほかの場所は search_kw を読まない:
  - `/Users/tanizawashingo/worktrees/salesanchor/release-condition-shrink-abbr/backend/app/services/gemini_raw_copy_v102_product_first.py:163-168`（canonical と単位だけ）
  - `/Users/tanizawashingo/worktrees/salesanchor/release-condition-shrink-abbr/backend/app/services/v102_buyback_unit_svc.py:84-88`（code・群・単位だけ）
- → masters["cond_entries"] の search_kw を手元の記憶の中で足し、`build_cond_terms` を作り直せば、本番の表を変えずに「語を足した後」の解析を再現できる。

### 3-2. 既存のやり直しの道具

- `/Users/tanizawashingo/worktrees/salesanchor/release-condition-shrink-abbr/backend/app/tools/v102_replay_diff.py:1-10`: 保存済みの件から v102 の後処理だけをやり直す。Gemini は呼ばない（`:42-48` 呼ばれたら RuntimeError）。書き込み・commit・ロックを呼ばない（`:120` 1 投稿ごとに rollback）。
- `:100-106` `replay()` は `svc.load_v102_masters(session)` を 1 回読む。差し替えの口は見出しの設定（`--heading-setting`）だけで、状態の語を足す口は無い。
- `:141-170` 差の道具は列ごとの差の件数（summary.tsv）と、**状態が変わった件だけ**（changed.tsv）を出す。商品・単位・値段だけが変わった件、件の数が変わった投稿は一覧に出ない。
- `:62-74` 1 件の記録の列: lines・product・unit・unit_kubun・condition・condition_basis・price・quantity・status・soldout_targets・soldout_target_basis。

### 3-3. 本番で流す場所の前例

- `/Users/tanizawashingo/worktrees/salesanchor/release-condition-shrink-abbr/scripts/accuracy/llm_compare/vps_convert.sh:1-12`: PO が `!` で実行する台本。本番 worker と別の箱（`docker compose run --rm --no-deps`）、健康診断の上書き（no-health.yml）を必ず付ける。台本ファイルを `-v` で箱に入れ、`-e PYTHONPATH=/app` で本番のコードを import する（`:94`）。
- 止め: deploy が動いていない（`:29`）、本番の HEAD が origin/main と同じ（`:31-35`）、出力を上書きしない（`:37-38`）。
- → 製品コード（backend/app）を変えずに、台本ファイルを箱に入れて流せる。デプロイ不要。

### 3-4. 対象の投稿（本番の読み取り）

- 問い合わせ: `/Users/tanizawashingo/CC報告ファイル-keep/shime-auto-check/multistate/abbr/t5.sql`（2026-10-10 以降・v102 の結果がある投稿で、原文に シュリあり／シュリンク有／有〆／有り〆 を含む）。
- 結果: 134 投稿・6,513 件（`/Users/tanizawashingo/CC報告ファイル-keep/shime-auto-check/multistate/abbr/t5.txt`、id の一覧は同じ場所の posts.txt）。社外秘のため PR には載せない。
- 行の役割が変わる見込み（語を足すと状態の行になる行）: 169 行（`/Users/tanizawashingo/CC報告ファイル-keep/shime-auto-check/multistate/abbr/role.txt`。シュリンク有り系 140・シュリあり 29・有〆／有り〆 0）。これは行の判定だけを写した試算で、件の商品・値段・まとまりへの影響は未測定。

## 4. 未確認

- 1 投稿のやり直しにかかる時間（134 投稿 × 6 回の合計時間）。前例の見出しの試しの所要時間の記録は見つけていない。
- やり直しを 2 回流して完全に同じ結果になるか（時刻や並びの揺れの有無）。設計の K1 で測る。
