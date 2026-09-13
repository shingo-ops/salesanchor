本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

CARD-LINE-25TH-MASTER-01

状態: 発行済み・実装PR #3475提出済み。全解析で単位絞込みと期待が衝突し設計§17改訂5はREVISE。匿名9行診断完了（HEAD13c58171）。設計補正のPO判断待ちで、期待変更/辞書追加変更/マージは停止。
この文書は、25th通常商品とスペシャルセットを辞書で分けるための実装指示書です。
親: `docs/specs/product-master/README.md`
設計: `docs/handoff/tcg-product-master-growth/design-keyword.md` §17改訂4（変更表と受入の詳細は改訂3、移行安全契約は改訂2を継承）。
根拠: 同ディレクトリrecon「訂正と追加実測: スペシャルセットはSIG実データにも存在」。
対象ADR: ADR-113 / ADR-154。mode: handoff。
読んだ節: `docs/ai-agents/design-partner.md` §5.5、`docs/handoff/design-partner-card-ops/guards/00-common.md`、`guards/11-lint.md`。
自己照合: 1○ 記号保護、2○ ready PR、3○ 宛先全文報告、4○ 25th商品分離1目的、5○ origin/main起点と公式机作り、6○ PR例、7○ 実測27例と移行受入を区別。
発行前の人手照合: 空箱保護は本番反映済み。最新マスタ照合と自己審査は完了。本便の明示委任を受領し発行。書式検査の成功を発行承認に代用しない。

受領確認
最初に「CARD-LINE-25TH-MASTER-01 受領」と返す。未発行状態なら実行せず、その旨を設計パートナーへ返す。

担当・範囲
実装担当1名が所有する。新規migration `migrations/20260913_120000_tcg_25th_product_disambiguation.sql`、runner `scripts/run_all_migrations.sh` の登録1行、`backend/tests/test_tcg_work_matching_integration.py` の関連試験だけを変更する。
他者も同じリポジトリで作業している。既存変更を戻さず、並行差分を保持する。設計/recon/台帳は設計担当所有で本カードから変更しない。
本番DB操作・本番接続・マージ・再解析・シート配信・Gemini呼出・CI設定・secrets変更・追加サブエージェント起動・ガード解除を禁止する。

開始条件
設計PR #3464 / HEAD67312ce0の§17改訂4と、本カードに記録した本便の明示委任を確認する。本カードが未発行の場合は手順0より前に停止する。
既存の人間用SSH読取1回の許可は消費済み。本カードでSSH権限を再付与しない。

手順0
  cd /Users/tanizawashingo/salesanchor && ./scripts/dev/executor-preflight.sh

手順1
  cd /Users/tanizawashingo/salesanchor && bash scripts/new-worktree.sh release/line-25th-product-disambiguation

手順2
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-25th-product-disambiguation && git status --short

手順3
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-25th-product-disambiguation && git rev-list --left-right --count HEAD...origin/main

手順4（実装）
編集/保存コマンドも必ず専用作業台へのcdを先頭に置く。編集とgit保存は別cmdにする。
親補正: pythonから開始すると本店mainを対象と検知され実行前に拒否されたため、所有範囲を変えず作業場所を明示する。
設計§17改訂3の登録表と改訂2の属性・単一トランザクション・ロック・同一性確認・採番・再実行差分0を実装する。
新セットの属性・固定27例は設計§17改訂4に従う。設計と本カードの範囲に限定する。空箱の除外語を商品辞書へ加えない。
対象が存在しない/同一性不一致/同名別形態/部分的表欠落/既存語重複等の異常では書込み前に失敗させる。想定外の対象を実装担当が選ばない。
全TCG表なしは変更0。runnerに当該migrationを1行登録し、既存登録順と内容を保持する。既存解析/単位/状態/配信コードは変更しない。

手順5（実DB試験）
親補正: 現HEAD726475b1の追加9行試験は全行のcode/resolved/basis/reviewを失敗メッセージへ記録し、全行照合後に失敗を返す診断追記を許可。期待を通る値へ変更しない。
結果を設計担当へ返して停止。改訂5の追加登録案は未承認で実装しない。
既存GitHub CIの使い捨てPostgreSQLで初回・2回目・同一性不一致・ID競合・対象表なし・一部欠落・他テナント保持を検証する。
初回計画差分は商品1/検索3/除外10追加（否定4語案を含む）、2回目0。これは受入値であり本番実測の称ではない。DB削除やSQLite代用はしない。
匿名入力で設計§17改訂4の15商品判定対照と否定12例を再現し、サプライ6例と否定4語×3欄の12例は実解析から配信行取得まで通して出力0を確認する。
空箱3欄は商品ID保持・未確認時の配信出力0を既存保護と照合する。
商品/語追加で旧v4参照版が変わった場合の再解析拒否・既存結果/訂正不変を試験し、新版参照の匿名入力の成功と区別する。
通常/プロモ/GOLDENの既存判定保持、セット同梱プロモの備考、曖昧セット+プロモパックの要確認保持も検証する。
実原文はGit/CIへ入れない。設計担当が非公開の固定67明細で59→60・変更2を再確認するため、実装HEADと再現可能な試験手順を報告する。
Dockerがないローカルではpytestを回さず、静的検査とready PRを先行し既存CIでDB試験を実行する。skip/未実施は成功に数えない。

手順6
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-25th-product-disambiguation/backend && make lint-ci

手順7
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-25th-product-disambiguation && git diff --check

手順8
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-25th-product-disambiguation && bash scripts/check-task-state.sh

手順9（保存・提出）
診断CIの前にmainが進んだ場合は通常取り込みを行う。7dcb9ce9のrunner競合は既存Dragon Ball2行、本便25th1行、空箱の順を全て保持して解消する。
他のmain由来ファイルを独自変更せず、本便差分が所有3ファイルだけと確認して通常pushする。期待/追加登録案は変えない。
所有3ファイルの実差分を確認し、検査結果を記録してその3ファイルだけをコミットする。
コミット後に `git log -1 --format=%H` で保存を確認してpushする。公式 `scripts/gh-pr-create-safe.sh` でmain向けready PRを作成する。
PR本文は一時ファイルに実際の改行で保存し `--body-file` で渡す。必須CIは `gh pr checks` とGitHub APIで確認する。
良い記載例（正式テンプレに以下を含める。全パスは同行のカンマ区切り。削除するファイル欄は既存行を削除/変更するファイルを宣言する）:
### 標準ワークフロー確認
- recon: docs/handoff/tcg-product-master-growth/recon.md
- 設計: docs/handoff/tcg-product-master-growth/design-keyword.md
- 対象ADR: ADR-113, ADR-154
- 設計仕様書: docs/specs/product-master/README.md
- 触るファイル: migrations/20260913_120000_tcg_25th_product_disambiguation.sql, scripts/run_all_migrations.sh, backend/tests/test_tcg_work_matching_integration.py
- 削除するファイル: scripts/run_all_migrations.sh, backend/tests/test_tcg_work_matching_integration.py
実差分が上の既存行変更宣言と異なる場合は事実に合わせる。ファイルそのものの削除は許可しない。
GO記録を生成せず、番号付きGOゲートが未充足ならその状態を報告する。
禁止形: 未実施DB試験を成功と記す、登録依頼を番号付きGO原文に書き換える、対象外の差分を同梱する。
CI失敗は所有範囲内だけ調査・修正・再検証する。必要な契約変更は設計担当へ戻す。

完了報告と停止
報告冒頭「本報告はカード CARD-LINE-25TH-MASTER-01 の実行結果である」。設計パートナーへPR URL・HEAD・変更ファイル・各試験の実測/未実施を返す。
完了報告の本文に生出力を全文含める。停止時は停止した手順番号／最後のコマンド／停止理由とエラー生出力を全文返す。
本番反映・再解析・配信まで実施したと報告しない。実装・試験・PR提出の状態を区別して停止する。
END OF CARD
