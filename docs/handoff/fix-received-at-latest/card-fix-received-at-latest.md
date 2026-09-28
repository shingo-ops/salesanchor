# CARD-FIX-RECEIVED-AT-LATEST: 受信時刻の修正（実装カード）

- 設計: `docs/handoff/fix-received-at-latest/design.md`（§9 APPROVE）
- 調査: `docs/handoff/fix-received-at-latest/recon.md`
- 作業場所: worktree release-fix-received-at-latest（origin/main `638cc6f91` 起点）
- 実装の条件: PO の明示的な実装承認を受けてから着手する。承認前は着手しない

## 触るファイル（これ以外は触らない）
1. `backend/app/services/tcg_line_import_svc.py`（:289 と :309 の2か所だけ）
2. `backend/tests/test_tcg_line_import.py`（`test_build_timestamp_ascending_order` だけ）
3. migrations/20260929_120000_fix_source_messages_received_at.sql（新規作成）
4. `.claude-pipeline/active-work.d/` の、このブランチの台帳
- 削除するファイル: なし
- 触らないもの: `backend/app/services/tcg_analyzer_svc.py`、配信・ダッシュボードのコード、frontend、ADR ファイル

## 手順
0. `./scripts/dev/executor-preflight.sh || exit 1`
1. `backend/app/services/tcg_line_import_svc.py`
   - :289 `"received_at": str,            # 最初の timestamp "YYYY-MM-DD HH:MM:00"` を
     `"received_at": str,            # 採用した最新メッセージの timestamp（line_posted_at と同値）` に変更
   - :309 `received_at = sorted_msgs[0]["timestamp"]` を `received_at = latest_msg["timestamp"]` に変更
   - 行番号がずれていたら、変更前の文字列で特定する。見つからなければ止まって報告する
2. `backend/tests/test_tcg_line_import.py` の `test_build_timestamp_ascending_order`
   - docstring を「received_at と line_posted_at は最新（最後）のタイムスタンプ、raw_text は最新のメッセージ本文（SQR-05）。」に変更
   - `assert entries[0]["received_at"] == "2026-08-01 10:00:00"` を次の2行に置き換える
     - `assert entries[0]["received_at"] == "2026-08-01 10:05:00"`
     - `assert entries[0]["received_at"] == entries[0]["line_posted_at"]`
3. マイグレーションを、design.md §5 の SQL のとおり一字一句作る
4. 検証（生の出力をすべて報告する）
   - `cd backend && pytest -q tests/test_tcg_line_import.py`
   - ruff／mypy（`.github/workflows/test.yml` の lint ジョブと同じコマンド）
   - migration guard などのローカルの検査があれば実行する（`scripts/` と `.github/workflows/` から特定して実行し、コマンドを報告する）
   - ローカルに PostgreSQL があれば、マイグレーションを2回流して、2回目の更新が0行であることを確認する。環境がなければ「未実施」と報告する（推測で済ませない）
5. コミット（recon.md、design.md、このカードも含める）→ push → `gh pr create --base main --draft`
   - PR 本文: `### 標準ワークフロー確認`（対象ADR: ADR-158／recon と設計のパス／触るファイル・削除するファイル）と、`migrations/` を含む危険 PR であることを明記する。GO記録の欄は空欄で置く（GO の原文を創作しない）
   - `scripts/dev/validate-pr-body.sh` が通ること
6. 停止する。マージ・un-draft・本番の操作はしない。CI の完了も待たない。PR の URL を報告して終わる

## 止まる条件
- 変更前の文字列が見つからない／テストが意図しない理由で失敗する／検査で赤になる → 生の出力を報告して止まる
- 触るファイル以外の変更が必要になった → 止まって報告する

## GO の前に PO へ提示すること（設計担当が行う）
- 対象: PR 番号、変更の3行要約、試算した入れ替わり件数（design.md §7）
- 直前のバックアップ: `source_messages(id, received_at)` と `analysis_results(id, is_current)` の退避。取り方は PO と合意する
- GO は PO の「GO #PR番号」でのみ有効
