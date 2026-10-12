# design: 要確認の一覧を、配信テストのスプレッドシートの「要確認」タブに出力する（段1：出力だけ）

- 状態: 設計案（Opus 作成・自己審査済み。独立した第二者レビューではない）
- PO の依頼（原文 2026-10-12）:
  - 「要確認だがもう少し使いやすくしたい、スプレッドシートが使い慣れているので動悸することは出来る？スプレッドシートに要確認を一覧で出力、人が修正したらアプリ側に戻すような仕組みはできる？」
  - 「このシートは配信テストを確認するためのシートなのでこのシートの"要確認"シートに出力できる？」
  - 離席時の一任「このセッションだけで最後まで完結させる」「PRマージ、デプロイまで完走させてくれ」
- 現在地: [recon.md](recon.md)（docs/handoff/review-sheet-export/recon.md）
- 対象ADR: ADR-154、ADR-1007、ADR-027、ADR-135・ADR-136

## 1. 目的（利用者に見える変化）
- 配信テストのスプレッドシートの「要確認」タブに、アプリの要確認の一覧（画面の「要確認」と同じ件）が出る。
- 配信のたびに書き直される。
- シートで直した内容をアプリに戻す仕組みは、段2で作る（この段では作らない）。

## 2. 対象と対象外
- 対象：配信先のうち「要確認タブ名」を設定した配信先だけ。今回の設定は「配信テスト」の1行だけ。
- 対象外：
  - ほかの配信先（山崎涼太郎・無料トライアルシート）
  - 「在庫集計」タブの中身
  - 配信の判定
  - 画面
  - シートからアプリへの書き戻し

## 3. 置き場（SSOT）
- **どの配信先に出すか**：配信先の設定の表 `public.tcg_distribution_targets` に、列 `review_sheet_name TEXT`（NULL 可）を1つ足す。NULL なら出さない。設定は配信先の設定と同じ表にまとめる。
- **何を出すか**：画面の要確認一覧と同じ関数 `fetch_analysis_results(status_tab="NEEDS_REVIEW")`（`backend/app/services/tcg_analysis_review_svc.py:149-336`）だけを使う。条件を別に書かない。
- **理由の日本語**：
  - 正本は `frontend/src/locales/ja.json` の reviewReason。
  - backend からは ja.json が読めない（recon §5）。そのため、backend/app/data/review_reason_labels_ja.json に、reviewReason の写しを置く。
  - 写しが正本と1文字でも違えば、試験 backend/tests/test_review_reason_labels_ja_sync.py が失敗する。写しは手で直さない。作り直しの道具を同じ PR に入れる。
- シートは表示の窓で、データの正本はアプリの DB のまま。シートから読む処理は、この段には無い。

## 4. 変更
### PR①（migration だけ。GO が要る）
- `migrations/20261012_210000_add_tcg_distribution_targets_review_sheet_name.sql`：
  ```sql
  ALTER TABLE public.tcg_distribution_targets ADD COLUMN IF NOT EXISTS review_sheet_name TEXT;
  COMMENT ON COLUMN ...;
  ```
  あわせて `scripts/run_all_migrations.sh` に登録する。
- 1回だけのデータ変更 SQL（`docs/handoff/review-sheet-export/data/`、ADR-1007）：
  - `docs/handoff/review-sheet-export/data/rs_precheck.sql`（配信テストの行が1行・spreadsheet_id 一致・review_sheet_name が NULL）
  - `docs/handoff/review-sheet-export/data/rs_dryrun.sql`（UPDATE … WHERE id=<配信テストの id> AND spreadsheet_id='1unwFM3MZikSmQjZ744uxhvzG2ENhuhcDsvse1dfSrm4'、1行だけ・ROLLBACK）
  - `docs/handoff/review-sheet-export/data/rs_commit.sql`
  - `docs/handoff/review-sheet-export/data/rs_verify.sql`
  - `docs/handoff/review-sheet-export/data/rs_rollback.sql`（NULL に戻す）
  - README の記録欄
### データ変更（PR① の本番反映の後、PR② のマージの前）
- rs_* を本番で実行して記録する。

### PR②（コードだけ）
1. `backend/app/services/tcg_analysis_review_svc.py`：一覧の SELECT に `sm.line_posted_at`、応答の件に `posted_at` を足す（足すだけ。並びと件数は変えない）。API の型の生成も更新する。
2. 新規 backend/app/services/tcg_review_sheet_svc.py：
   - `build_review_rows(items, labels) -> list[list[str]]`（純粋関数）。列（見出しは定数 `REVIEW_SHEET_HEADERS`）は次のとおり。
     1. 投稿日時（JST の "YYYY-MM-DD HH:MM"）
     2. 仕入先（provider）
     3. 行（gemini.span の "Lx-y"）
     4. 原文（その件の行の文字。raw_text の span の範囲の行を改行でつなぐ）
     5. 価格（gemini.price の写し）
     6. 数量（gemini.quantity の写し）
     7. 商品（system.product_title。無ければ空）
     8. 状態（system.condition）
     9. 単位（system.unit）
     10. 要確認の理由（review_reason_details の code を labels で日本語にし、「、」でつなぐ。labels に無い code はそのまま出す）
     11. 間の行（gap_suspect.gap_lines を "L14、L15"）
     12. 候補（gap_suspect.candidates の name を「、」でつなぐ）
     13. 件の番号（extraction_item_id。段2の書き戻しの目印）
   - `write_review_sheet_sync(gc, creds, target, rows)`：`_write_to_target_sync` と同じ安全装置 #1〜#5 を当て、タブは target["review_sheet_name"] にする。タブが無ければ止める（作らない）。clear してから見出しとデータを append_rows（RAW）する。既存の関数を引数でタブ名を受け取れる形に分けて使い回し、同じ安全装置を二重に書かない。
3. `backend/app/services/tcg_distribution_svc.py` の `run_distribution`：
   - 配信先の書き込みが ok だった後、`review_sheet_name` がある配信先にだけ、要確認のタブを書く。
   - 要確認の書き込みが失敗しても、配信の結果（ok）は変えない。失敗はログに出し、既存の失敗の通知に「要確認タブ」として載せる。
   - 一覧の取得は1回の配信で1回だけ（limit は DIST_ROW_LIMIT）。
   - 配信先の読み込み（:566-568）に列を足す。
4. backend/app/data/review_reason_labels_ja.json、その作り直しの道具 backend/app/tools/sync_review_reason_labels.py、試験 backend/tests/test_review_reason_labels_ja_sync.py。
5. 試験：
   - build_review_rows（全列・候補なし・理由の日本語化・知らない code）
   - 書き込み（タブが無いと止まる・行数の上限・タブ名の一致）
   - run_distribution（review_sheet_name が NULL の配信先には書かない・要確認の失敗で配信の結果が変わらない）

## 5. 受入条件と検証方法

| 基準 | 検証方法 |
|---|---|
| 1. 本番の表に列があり、配信テストだけが「要確認」、ほかの2行は NULL | 本番の読み取り SQL |
| 2. 次の配信の後、配信テストの「要確認」タブの行数 = その時点の要確認の件数＋見出し1行 | シートの読み取り（行数）と、fetch_analysis_results の total |
| 3. 「在庫集計」タブの配信の行数・ok は、今までどおり（3つの配信先とも） | tcg_distribution_targets の last_result・count |
| 4. ほかの2つの配信先の「要確認」タブには書かれない | 書き込みのログ・2つのシートのタブの読み取り |
| 5. 理由の写しが ja.json と一致 | 試験（CI） |
| 6. CI 全緑 | gh pr checks |

## 6. 危険と対処
- お客様のシートに社内の情報（原文・理由）が出る：review_sheet_name が NULL の配信先には書かない。NULL が既定。データの変更は、配信テストの id と spreadsheet_id の両方が一致する1行だけ。
- 配信が止まる：要確認の書き込みは、配信の書き込みの後に別に行い、失敗しても配信の結果は変えない。
- 原文が社外秘：配信テストのシートの見られる人は、Drive の権限で owner・reader・writer の3件（recon §3）。見られる人の範囲は PO の管理。
- 戻し方：rs_rollback.sql（NULL に戻すと書かれない）、または PR② の revert。

## 7. 維持の仕組み
- 守り手: backend/tests/test_review_reason_labels_ja_sync.py（理由の日本語の写し）、backend/tests/test_tcg_review_sheet_svc.py（列と安全装置）。

## 8. 外部・過去事例の参照と我々への応用
- 社内の前例：
  - 配信（`backend/app/services/tcg_distribution_svc.py`）の安全装置 #1〜#5 と、clear してから書く方式を、そのまま使う。
  - 写しを試験で正本とそろえる型は、`backend/tests/test_review_reason_codes_consistency.py`（seed と ja.json）の前例。
- 外部事例：該当なし（既存の書き込みの仕組みに、タブを1つ足すだけで、新しい技術の選択を含まないため）。

## 9. 審査（Opus 自己審査）
- 判定: APPROVE。
- 根拠：
  - 要確認の定義は画面と同じ関数だけ。
  - 出す先は設定の表の1列だけ。
  - 理由の日本語は、ja.json を正本とし、写しは試験で縛る。
  - 配信の結果を変えない。
- 未解決：シートからアプリへの書き戻し（段2）。誰が直したかの記録の方法は、段2の設計で PO に確認する。
