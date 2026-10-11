# 実装カード AGE: 配信の「48時間以内だけ」を1か所の定義にし、設定が無い時は配信を止める（便AGE）

設計者: Opus（2026-10-11）。PO の言葉（2026-10-11）:
- 「システム解析後に最終的に集計したリストに残るのはLINEでの投稿日時が48時間以内の商品、それ以外は集計リストから外してログにする」
- 「解析したリストは全てログになってDBに残る認識で48時間以内の投稿のデータのみ印が付き配信される」→ 設計者が「理解・合意」と回答。
- 「確立したなら進める…PRマージ、デプロイまで完走させてくれ」
根拠の調査: /tmp/CC報告ファイル/is-current-48h/（summary.txt ほか）。

## 0. 事実（調査済み・着手前に実物で再確認し、ずれたら NEEDS_DECISION）
- 配信本体 backend/app/services/tcg_distribution_svc.py fetch_output_rows の 48時間の絞り :220-224、プレビュー件数 fetch_preview_data :322-326 に同じ文が複製。除外内訳（:346-380 付近、WHERE ar.is_current = TRUE）は48時間で絞っていない＝プレビューの内訳だけ48時間より前の行も数える。
- 48 の値は public.tcg_distribution_settings.max_age_hours（本番 48）。読む所は :306（プレビュー）と :762（配信実行）で `int(settings.get("max_age_hours", "0"))`。キーが無いと 0 → `if max_age_hours:` が偽 → 絞りが外れ、全期間の行が配信される。
- 配信先シートは配信のたびに clear → append_rows（:519-522）。
- is_current（tcg_analyzer_svc.py _merge_supplier_products）は「同じ仕入元×商品×状態の最新行」の印で経過時間を見ない（ADR-158）。本便では変えない（時間で変わる条件は読み取り時に当てるのが正しく、印を毎回付け直す仕組みは作らない）。

## 1. 変更（tcg_distribution_svc.py の中だけ。ほかの画面・表は変えない）
1-1. 48時間の条件を1つの関数にする（例 `_age_window(max_age_hours) -> tuple[str, dict]`、SQL 断片 `AND sm.line_posted_at >= NOW() - make_interval(hours => :max_age_hours)` と bind）。fetch_output_rows・fetch_preview_data の件数・除外内訳の3か所はすべてこれを使う（重複を消す）。line_posted_at IS NOT NULL の常時条件は今のまま。
1-2. 除外内訳にも 48時間の条件を当てる（内訳の数が「48時間以内の現行行」の内訳になる）。除外内訳の表示文言（frontend の i18n、tcgDistribution.preview 等）が「全期間」を前提にした書き方なら報告する（直すかは設計者が決める）。
1-3. 設定の読み方を1か所に（例 `_max_age_hours(settings) -> int | None`）。値が無い・整数でない・負の時は None。
  - 配信実行（:762 付近）: None なら配信しない（ほかの早期 return と同じ形で errors に「max_age_hours 未設定のため配信しない」を入れ、logger.error）。
  - プレビュー: None なら件数・内訳を出さずに同じエラーを返す（応答の形はプレビュー API の既存のエラーの返し方に合わせる。既存に無ければ設計者に報告）。
  - 値が 0 の扱い: frontend の DistributionSettingsDrawer.tsx（:47, :59 付近）と i18n の説明で 0 が「無制限」と説明されているかを確認する。説明されていれば 0 は今のまま（無制限）とし、説明が無ければ 0 も None と同じ（配信しない）にする。どちらにしたかと根拠を報告。
1-4. 値 48 をコードに書かない（設定の表が唯一の値）。

## 2. テスト
- 3か所が同じ条件を使うこと（48時間より前の行が配信・件数・内訳のどれにも入らない）PG テスト。
- 設定が無い時に配信しない・プレビューがエラー（PG または単体）。
- 0 の扱い（1-3 の判断どおり）。
- 既存の配信テストが通ること。

## 3. 本番前の確認（読み取り・repo 外 /tmp/CC報告ファイル/is-current-48h/）
- 本番の今のデータで、変更前と変更後の fetch_output_rows の行数・行の集合が同じこと（48時間の条件は同じなので差0の期待）。可能なら本番 DB を読み取り専用で使う手元の実行で、無理なら SQL を組み立てて比較。
- 除外内訳の変更前・変更後の数。

## 4. 手順
1. `bash scripts/new-worktree.sh release/distribution-age-window --claude` → `./scripts/dev/executor-preflight.sh`。Bash は単独の `cd <worktree> && …`。
2. 実装 → テスト → 本番前の確認 → ruff・pytest。
3. commit（feat: または fix:、末尾 Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>）。push・PR はしない。
4. このカードを docs/handoff/distribution-age-window/card-AGE.md に置く。

## 停止条件
- 前提と実物が違う、tcg_distribution_svc.py 以外を変えないとできない、プレビューのエラーの返し方が決められない → NEEDS_DECISION。フックに止められたら言い換えず止まる。最終行 DONE / BLOCKED: / NEEDS_DECISION:。
