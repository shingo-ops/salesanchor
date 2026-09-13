本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

CARD-LINE-25TH-MASTER-01

状態: 改訂発行済み。設計§17改訂6は同一AI自己審査APPROVE。POはセット/プロモ両側への複合除外を説明した質問に「進める」と回答。本便の実装・試験・PR更新まで再開する。
このカードは、25th通常商品・セット・プロモを取り違えず、曖昧な名前を人の確認へ回すための実装指示書です。
親: `docs/specs/product-master/README.md`
設計: `docs/handoff/tcg-product-master-growth/design-keyword.md` §17改訂6（旧改訂4/5の停止やPM0072不変を置換）。
根拠: `docs/handoff/tcg-product-master-growth/recon.md` の25th全解析9行の最終診断。
対象ADR: ADR-113 / ADR-154。mode: handoff。
読んだ節: `docs/ai-agents/design-partner.md` §5.5、`docs/handoff/design-partner-card-ops/guards/00-common.md`、`guards/11-lint.md`。
自己照合: 1○ 記号保護、2○ ready PR、3○ 親への全文報告、4○ 25th商品分離1目的、5○ 既存originブランチ起点、6○ 正式本文例、7○ 局所対照と実PG受入の区別。
人手照合: 既存PR #3475 HEAD13c58171/所有3ファイル/作業台の実在を確認。POの番号付きGOや本番操作許可ではない。

受領確認
最初に「CARD-LINE-25TH-MASTER-01 改訂6受領」と返す。設計と本カードの範囲外なら実行せず親へ返す。

担当・所有範囲
既存実装担当1名。所有は次の3ファイルだけ。
- `migrations/20260913_120000_tcg_25th_product_disambiguation.sql`
- `scripts/run_all_migrations.sh`（既存登録1行を保持）
- `backend/tests/test_tcg_work_matching_integration.py`
他者も同じコードベースで作業している。変更を戻さず保持する。設計/台帳は親が担当する。
本番接続/本番DB変更/マージ/再解析/配信/Gemini呼出/CI設定/secrets変更/追加エージェント/ガード解除は禁止。
過去のSSH読取やGO #3470を本便へ流用しない。

手順0 preflight
  cd /Users/tanizawashingo/salesanchor && ./scripts/dev/executor-preflight.sh

手順1 既存作業台
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-25th-product-disambiguation && git status --short --branch
起点はorigin/release/line-25th-product-disambiguation。新しい作業台を作らない。本店の未保存変更を取り込まない。
親が本店active-work.dの本ブランチ行を再開へ更新する。担当は設計台帳を書き換えない。

手順2 ブランチ照合
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-25th-product-disambiguation && git rev-list --left-right --count HEAD...origin/main
最新mainの通常取り込みは許可。runnerは両便の登録を保持し、意味変更/所有外の競合は停止する。

手順3 修正
すべての編集/保存コマンドを専用作業台へのcdで始める。編集とgit保存は別cmdにする。
設計§17改訂6どおり新セットとPM0072へ複合除外「スペシャルセット プロモパック」を各1語追加。
PM0072の同一性と既存検索4/除外1語を最初の書込前に検査する。既存ID/語/位置は保持し追加1語だけ。
新商品1/検索3/除外12が最初の予定差分。既存の原子性・ロック・採番・空箱保護は維持する。
新セットの既存候補照合は最終6除外に一致する場合だけ再利用する。未適用の旧草案を本番適用済みとして救済しない。
PM0073、商品判定/単位フィルタの製品コード、CIは変更しない。

手順4 実PG試験
設計§17改訂6の6項目を全て検証。名前だけの27例と、単位を含む全解析の期待を区別する。
元9行のプロモ+BOX、曖昧セット+プロモ+BOXを削除せず未特定/要確認の期待へ設計どおり修正する。
正常プロモ+PackはPM0072、曖昧名はBOX/Pack/未知単位全て未特定/要確認/配信0。
内部理由MULTIへの固定はしない。未特定という受入は維持する。
サプライ6+否定12+空箱3欄と同梱備考2例、旧v4拒否/訂正保持/新版参照成功を維持する。
PM0072同一性/辞書異常を失敗時変更0の試験へ追加。初回1/3/12、2回目0、対象外/他tenant不変を確認する。
既存CIの使い捨てPostgreSQLを使い、DB削除・独自の基礎表重複定義・SQLite代用をしない。必須試験のskipは不可。
Dockerなしローカルではpytestを実行せず、ready PR更新後のCIで実測する。未実施/skipは成功に数えない。
原文をGit/CIへ入れない。親が保存67件を実登録語で局所再照合するため最終HEADを報告する。

手順5 静的検査
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-25th-product-disambiguation/backend && make lint-ci

手順6 差分検査
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-25th-product-disambiguation && git diff --check

手順7 台帳構造検査
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-25th-product-disambiguation && bash scripts/check-task-state.sh

手順8 保存・既存PR更新
所有3ファイルだけを確認してコミットする。
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-25th-product-disambiguation && git log -1 --format=%H
保存確認後に通常pushし、既存ready PR #3475の本文を最終差分・検証に更新する。新PRを作らない。
本文は実改行の一時ファイルに保存して--body-fileで渡す。検査はgh pr checksとGitHub APIで確認する。
良い本文例:
### 標準ワークフロー確認
- recon: docs/handoff/tcg-product-master-growth/recon.md
- 設計: docs/handoff/tcg-product-master-growth/design-keyword.md
- 対象ADR: ADR-113, ADR-154
- 設計仕様書: docs/specs/product-master/README.md
- 触るファイル: migrations/20260913_120000_tcg_25th_product_disambiguation.sql, scripts/run_all_migrations.sh, backend/tests/test_tcg_work_matching_integration.py
- 削除するファイル: （なし）
上はorigin/mainに対して追加だけの場合の例。実差分に既存行変更があれば該当パスを正式欄へ記載する。
禁止形: 未実施を成功と書く、過去GOの流用、期待を実結果に合わせて弱める、所有外差分の同梱。
所有内の実装/試験不具合は修正・再検証。設計の変更が必要なら親へ返す。

完了報告・停止
冒頭「本報告はカード CARD-LINE-25TH-MASTER-01 改訂6の実行結果である」。
親へPR URL/HEAD/3ファイル/試験の成功失敗skip/未実施を報告し、生出力全文を非公開ファイルに保存してパスを返す。
停止時は手順番号/最後のコマンド/理由/エラー全文を返す。期待不一致は対象名と実値を出す。
技術合格後も番号付きGO未受領のゲートは保持し、実装・試験・PR更新までで停止する。
END OF CARD
