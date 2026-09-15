---
mode: handoff
---
CARD-PMG-ATTEMPT-RECORD-FIX-01
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
読んだ節: guards/00-common.md、既存カード02の公開境界、ADR-113、backend/AGENTS.md。
照合: 専用作業台・既存SSOT・正式チェック・設計草案と製品変更の区別。
受領確認: カード名と作業場所をrootへ返す。
担当: 既存error_visibility_recon。rootは設計/台帳、担当は製品/試験を所有。
POは検証後の本番反映まで明示依頼済み。新番号のGO原文を創作しない。
他者も作業中。変更を戻さず、他branchの製品や未保存文書を編集しない。
根拠: 本作業台design.md末尾の限定是正案/確定追補、reports/pr3494-evidence-20260914。
限定設計は同一AI自己審査APPROVE。期待値の出所/比較契約/保存境界を変えない。
本カードは実装・隔離検証まで。後段commit/push/PR/マージ/本番はroot検収後のカード。
手順0
  cd /Users/tanizawashingo/salesanchor && ./scripts/dev/executor-preflight.sh
期待する出力: 成功。
先約・実在を確認し、公式scripts/new-worktree.shでrelease/attempt-record-integrity-fixをorigin/main起点に作成。
--claudeは使わない。追加エージェント起動は禁止。失敗時はrootへ根拠を返す。
作成手順の補足: 公式reaperの既定安全検査でclean・全commit保存済み・mainマージ済みと判定した作業台の通常回収は、公式new-worktreeに含まれる準備として許可。製品や未保存変更の編集/削除は引続き禁止。手動削除、強制回収、保護解除はしない。
今回rootがrelease/csv-ssot-migration-fixのclean、HEAD85bcd325とPR3500の同HEAD/mainマージを直接確認。先約IN_PROGRESSは古い記録のためマージ事実と分離。公式ツールが直前に未保存ありと判定したものを回収しない。
許可製品: backend/app/services/tcg_extraction_record_svc.py、migrations/20260914_010000_tcg_extraction_attempts.sql。
許可試験: backend/tests/test_tcg_extraction_record_pg.py、必要なら同系新規test_tcg_extraction_record_integrity_pg.py。
設計参照は旧作業台から読取り。rootの文書はコピー/編集しない。新台帳の担当欄は実在に基づく記入のみ許可。
手順1
保存案を製品へ忠実に組込む。prepare_items/completeの両超過経路で測定値を保持し、既存failの所有確認後に同じ試行行へ保存。
元の成功/失敗契約、既存固定コード、上限、本文NULL、所有権/終了済み保護を維持。新表/新列/履歴補完なし。
構造検証は正規DDLからの期待値と照合。対象本番表から期待値を学習しない。全比較項目はdesign追補準拠。
実装の期待値を正規DDLで生成した隔離基準表と照合する試験も追加。余剰/不足は停止。既存列型/NULL/索引検査維持。
既存migrationの検証を強化し、runner/CI/deployは編集しない。本番DDLは実行しない。
手順2
実PGで候補の正常7/不正8/未知等価式1を正式migrationへ適用し、正常/冪等/複数schema/rollbackと既存行不変を検証。
実taskで上限境界/超過サイズ保持/本文NULL/新明細0/自動解析0を確認。旧試行/並行/終了行/DB記録失敗と既存試験を回帰。
通常make lint-ci、差分チェックを実施。Dockerなしのpytestは禁止。Dockerの有無を先に確認。
必要なら専用Docker試験環境を新設し、他者のDB/volumeを使わない。環境依存を推測せずrootへ報告。
実Gemini/本番/Sheets/API外部呼出し0。合成入力のみ。失敗は成功扱いせず修理対象を本カード内に限定。
手順3
作業場所、HEAD/base、差分ファイル、全検証コマンド/結果、残件をrootへ返す。
期待する出力: 実差分と実検証。未知の設計変更が必要なら提案根拠を返し製品操作を停止。
commit/push/PR/マージ/本番変更/承認チェック迂回は禁止。完了報告後は編集を停止する。
END OF CARD
