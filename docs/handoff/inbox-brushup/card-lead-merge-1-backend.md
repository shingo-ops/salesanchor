# 実装カード 1/2: リードの統合をサーバーで直す（13表・空欄埋め・下見・知らせ）

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

- 設計: `docs/specs/transaction-flow/lead-merge/design.md` §5-1・§5-5(1)・§8 A1
- 決定: `docs/adr/ADR-1049-lead-merge-all-tables-and-fill-blanks.md`
- 現状: `docs/handoff/inbox-brushup/lead-merge-recon.md`
- 実装の承認: PO 2026-10-28「決めた内容を記録に残してクローンの大きさを測り、作る」
- 2/2（画面）は本カードの PR がマージされてから出す。

## 0. カード発行前の照合（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲む | ○ |
| 2 | PR は ready で作る（`--draft` を付けない） | ○（手順 9） |
| 3 | 報告の宛先: 完了報告の本文に生出力を全文含める | ○（§報告） |
| 4 | 1便1目的（サーバーだけ。画面は 2/2） | ○ |
| 5 | 既存ブランチへの追記ではない（新しい作業場所） | ○（手順 1） |
| 6 | PR 欄の書式を実例で示す | ○（手順 8） |
| 7 | 合格を出力まで縛る（試験の件数・削除の無い差分） | ○（手順 6・7） |
| 8 | 件数の判定には名前を出す手順を対で置く | ○（手順 6 で落ちた試験名を出す） |
| 9 | 出力量に上限の無いコマンドを使わない | ○ |
| 10 | 停止時の3点・終端合図・報告冒頭の宣言 | ○（§報告） |
| 11 | 期待値は実測から。行番号を停止条件にしない | ○ |
| 12 | 停止は不可逆なものだけ。数の食い違いは記録して続行 | ○ |
| 13 | 定型の4点（sleep 禁止・Write/Edit・validate-pr-body.sh・止められたら原文） | ○（§守ること） |

## 守ること

- sleep で待たない。CI の終わりを待たない（PR の URL を報告して終える）。
- ファイルの作成と編集は Write / Edit ツールで行う。ヒアドキュメントで書かない。
- PR を作る前に `bash scripts/dev/validate-pr-body.sh < <本文ファイルの絶対パス>`（本文は標準入力で渡す）で exit 0 を確かめる。
- フックや自動判定に止められたら、言い換えて再試行しない。止まった手順・最後のコマンド・理由の原文を報告して終える。
- 禁止: マージ、`migrations/` の変更、`frontend/` の変更、本番への接続、`/review` の実行、ほかのブランチの操作、GO 記録への書き込み。
- 仕入元の投稿の原文を PR 本文・コミットに書き写さない。

## 手順

1. `./scripts/dev/executor-preflight.sh || exit 1` を実行する。続けて `bash scripts/new-worktree.sh release/lead-merge-backend` で作業場所を作り、以後その中で作業する。`git log -1 --oneline` と `git status --short` を記録する。
2. 着手時の確かめ（記録のみで続行）: lead-merge-recon.md §2 の13表について、結び付きの決まり（FK・ON DELETE・UNIQUE）を `backend/app/services/tenant.py` と `migrations/` で開き、ファイル:行を記録する。lead-merge-recon.md §2 の表と違う表が1つでもあれば、その表名と出典を記録して**ここで停止**する（設計の前提が変わるため）。
3. `backend/app/routers/leads.py` の統合（`POST /leads/{master_id}/merge`）を design.md §5-1 の1〜9のとおり直す。
   - 13表の一覧は1か所の定数にする（表名・列名・一意の決まりの種類）。
   - 空欄の判定: NULL・空文字（前後の空白を除いて空）・空の配列。status と prospect_rank は対象外。
   - loser の条件は今のまま `status != "lead"` で 400。
   - `await db.commit()` の直後に `await reset_tenant_context(db, tenant_id)` があることを確かめ、無ければ足す（ADR-072。`backend/tenant/CLAUDE.md`）。
   - `publish_leads_update` は `leads.py` の作成・更新・削除と同じ形（関数の中で import、except で `logging.warning`）で、commit と `invalidate_dashboard_cache` の後に呼ぶ。文言は「リード統合継続」。
4. 下見 `POST /leads/{master_id}/merge/preview` を足す。権限 `require_permission("leads.delete")`、体は `LeadMergeRequest`、返す型 `LeadMergePreview`（各表の付け替え件数・一意の決まりで消す件数・埋まる項目の一覧[項目名・今の値・入る値]）。書き込みをしない。統合と同じ計画の関数を使う。
5. `backend/tests/test_lead_merge_pg.py` を新しく作る。形は既存の `backend/tests/test_leads_assignment_opened_at_pg.py` に合わせる。中身は design.md §5-5(1) の全項目（13表・K1・K3・K4 2件・K5・一意の4表・下見2件・異常系3件・漏れの見張り1件）。漏れの見張りは、テナントの schema で `lead_id` 列を持つ表（`information_schema.columns`）と public.registration_tokens を数え、定数の13と比べる。
6. 試験を動かす（記録のみで続行）: `backend/tests/test_lead_merge_pg.py` と、既存の統合・リードの試験（`grep -l "merge" backend/tests/*.py` で出たもの）。結果の全文と、失敗があればその試験名を記録する。
7. 差分の確かめ（記録のみで続行）: `git diff origin/main --stat` と `git diff origin/main --name-only`。`leads.py` で消えた行の数（`git diff origin/main --numstat -- backend/app/routers/leads.py`）。
8. PR 本文を `.github/PULL_REQUEST_TEMPLATE.md` から Write で作る。「### 標準ワークフロー確認」の書き方:
   - 良い例: `触るファイル: backend/app/routers/leads.py, backend/app/schemas/lead.py, backend/tests/test_lead_merge_pg.py`
   - 禁止形: 行頭に `-` を付けた箇条書き、同じ行に注記を付ける
   - `削除するファイル: なし`（消すファイルが無いとき）
   - `対象ADR: docs/adr/ADR-1049-lead-merge-all-tables-and-fill-blanks.md`、`recon: docs/handoff/inbox-brushup/lead-merge-recon.md`、`設計: docs/specs/transaction-flow/lead-merge/design.md`（平打ち）
   - 触るファイルは手順 7 の `--name-only` の全部（上の良い例は形の例。実際の一覧に合わせる）
9. `scripts/dev/validate-pr-body.sh` を exit 0 まで確かめる → `git -C <作業場所の絶対パス> push -u origin release/lead-merge-backend` を単独で実行 → `gh auth status` で `shingo-cc` を確かめる → `gh pr create --base main --head release/lead-merge-backend --title "fix: リードの統合で13表を付け替え空欄を埋める（ADR-1049）" --body-file <絶対パス>`（ready。`--draft` を付けない）。

停止するのは: 手順 2 で表が違ったとき、push・PR 作成が拒否されたとき、フックに止められたとき。それ以外の数の食い違いは記録して最後まで進む。

## 報告

- 冒頭に「本報告はカード 1/2（リードの統合 サーバー）の実行結果である」。
- 完了報告の本文に、手順 1〜9 で実行した全コマンドの生出力を全文含める（`.claude/agents/generator.md`「カード実行時の応答様式」）。
- 停止したときは「停止した手順番号／最後に実行したコマンド／停止した理由」。
- 最後の行に `END-OF-CARD-1` と書く。
