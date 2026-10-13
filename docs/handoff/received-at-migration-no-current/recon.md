# recon: デプロイのたびに is_current が古い決め方に戻る件

調査者: Opus（2026-10-13）。本番は読み取りだけ。基準は origin/main 480bd986f。

## 1. 既存 ADR の検索
- `git grep -i is_current docs/adr/` → docs/adr/ADR-158-product-level-supersession.md（is_current の定義。:26「新メッセージにも存在する product_id の旧行を FALSE」）
- ADR-155（マイグレーションは構造変更のみ。値の書き込みは neutralize する）: /Users/tanizawashingo/worktrees/salesanchor/release-received-at-migration-no-current/scripts/check-migration-value-writes.py:1-14
- 前の便: docs/handoff/v102-same-post-rows/design.md（#4169。is_current を投稿単位で決める）

## 2. 観測した事実
- デプロイは毎回、全マイグレーションを先頭から流し直す。唯一の実行経路は /Users/tanizawashingo/worktrees/salesanchor/release-received-at-migration-no-current/scripts/run_all_migrations.sh（/Users/tanizawashingo/worktrees/salesanchor/release-received-at-migration-no-current/.github/workflows/deploy.yml:53 のコメント）。
  - 対象のファイルは /Users/tanizawashingo/worktrees/salesanchor/release-received-at-migration-no-current/scripts/run_all_migrations.sh:846 で毎回流れる。
- /Users/tanizawashingo/worktrees/salesanchor/release-received-at-migration-no-current/migrations/20260929_120000_fix_source_messages_received_at.sql の中身は2つ。
  - :6-9 `source_messages.received_at` を `line_posted_at` にそろえる UPDATE
  - :11-30 analysis_results.is_current を、組（supplier_channel_id, product_id, condition_id）ごとに `ROW_NUMBER() = 1` の1行だけ TRUE にして、全表を決め直す UPDATE
- :11-30 は #4169 より前の決め方（組ごとに1行）。今の正本は /Users/tanizawashingo/worktrees/salesanchor/release-received-at-migration-no-current/backend/app/services/tcg_analyzer_svc.py:1744 `_merge_supplier_products`（:1855 top_job。同じ投稿の組の行をすべて TRUE）。
  - 同じ投稿の行は ORDER BY（received_at DESC, computed_at DESC）が同順位なので、:11-30 は、どの1行を選ぶかが決まらない。
- 本番で起きたこと（/tmp/CC報告ファイル/same-post-rows/deploy/）
  - 2026-10-12 19:38Z：#4169 をデプロイ。直近48時間の143投稿を解析し直した後、「同じ投稿の同じ組で、TRUE が一部の行だけ」の組は 33 → 0 になった。
  - 19:47Z：#4183 のデプロイが始まった。マイグレーションの流し直しの間に、20組の行が FALSE に戻った。戻った行の updated_at は、すべて 2026-10-12 19:51:51.248299+00 の1回の更新。
  - 失敗した21投稿をやり直した後も、20組が残った（t5_after2.out）。
- received_at の UPDATE（:6-9）が今変える行：`line_posted_at IS NOT NULL AND received_at IS DISTINCT FROM line_posted_at` は 0 行（2026-10-13 読み取り、ra.out）。
- neutralize の前例：#4017（例 migrations/075_create_goals.sql）。値の書き込みを外し、`-- NEUTRALIZED (ADR-…, 日付): 理由` のコメントを残す。

## 3. 未確認
- 過去の「解析し直すたびに表示が入れ替わる」現象のうち、何件がこのファイルによるものか（数えていない）。
