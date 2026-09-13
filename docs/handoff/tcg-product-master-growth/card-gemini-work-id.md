---
mode: handoff
---
# CARD-LINE-GEMINI-WORK-ID-01

この文書は何か: 商品マスタから作品だけを判断し、ほかの情報を原文のまま保つ変更の実装指示。
親: [商品マスタ](../../specs/product-master/README.md)。設計: [design-keyword.md §16.10](./design-keyword.md)。根拠: [recon.md](./recon.md)。ADR-154/ADR-113。
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
読んだ節: docs/handoff/design-partner-card-ops/guards/04-worktree.md、11-lint.md。
受領確認: 対象CARD-LINE-GEMINI-WORK-ID-01。実装承認は2026-09-12のPO後続指示。マージには現行ゲートを満たすPO原文が別途必要。

照合結果: 1記号○、2ready PR○、3報告宛先○、4作品IDと必須配信除外の1目的○、5専用起点○、6書式○、7合格条件○。正式機械検査はcard-lintを実行して記録する。
作業場所はnew-worktree.shで作成済みのrelease/line-gemini-work-id-design、起点origin/main 66b41766。新たなエージェントを起動しない。

許可ファイル: backend/app/services/gemini_extraction_svc.py、backend/app/services/tcg_work_reference.py、backend/app/tasks/tcg_extraction.py、backend/app/services/tcg_analyzer_svc.py、backend/app/services/tcg_distribution_svc.py、migrations/20260912_020000_tcg_resolved_work_id.sql、scripts/run_all_migrations.sh、backend/tests/test_tcg_work_id.py、backend/tests/test_tcg_gemini_extraction.py、backend/tests/test_tcg_work_matching_integration.py、既存design-keyword.md/recon.md、docs/adr/ADR-154-tcg-parity02-gas-python-migration.md、docs/adr/README.md（生成）、docs/specs/product-master/README.md、tasks/todo.md、docs/ai-agents/evidence-registry.md、本カード。
テスト追加が既存契約に必要な場合も上記3テストへ集約。製品実装は設計§16.10に忠実。schema追加前にGeminiを呼ばない。新規テナントの無関係な表を作らない。
禁止: テスト中のGemini実呼出し、顧客データの公開、deploy.yml/CI/secrets変更、スプレッドシートの試験書込み、旧抽出値の推測補完、ゲート回避、GO原文の代筆。

手順1 設計どおり実装と静的検査
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-gemini-work-id-design/backend && make lint-ci
期待する出力: ruff/bandit成功。mypyは既存の警告扱いを明示。ローカルDocker不在ではpytestを実行しない。
手順2 文書検査
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-gemini-work-id-design && bash scripts/check-task-state.sh
期待する出力: 終了0と構造検査成功。対象ファイルはgit diff --name-onlyで全件確認、想定外変更0。
手順3 カード検査
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-gemini-work-id-design && bash scripts/card-lint.sh docs/handoff/tcg-product-master-growth/card-gemini-work-id.md
期待する出力: 違反0。正式PRはgh-pr-create-safe.shでready、--draft禁止。PR本文の良い例は「- 設計: docs/handoff/tcg-product-master-growth/design-keyword.md」、禁止形は架空URL/未作成文書。

CIで模擬Geminiと隔離PostgreSQLによる正常/不正ID/型番作品限定/旧版/配信要確認除外/未migration/参照変更の試験を行う。実行件数と成否を生出力から記録。未実行を成功扱いにしない。
停止時は手順番号・最後のコマンド・理由を完了報告へ記す。本報告はカードCARD-LINE-GEMINI-WORK-ID-01の実行結果である、と冒頭に記す。完了報告の本文に検証の生出力を全文含める（POへの説明は要点を併記可）。
END OF CARD


## 後続カード CARD-LINE-WORK-SPAN-02

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
読んだ節: guards/04-worktree.md、guards/11-lint.md。設計はdesign-keyword.md §16.12、自己審査APPROVE。PO修正着手承認「進めてくれ」。
作業場所: release/line-work-id-production-record（origin/main ee455fb1起点、既存2709f628は本番証跡の文書のみ）。
許可: gemini_extraction_svc.py、tcg_work_reference.py、tcg_analyzer_svc.py、tasks/tcg_extraction.py、tests/test_tcg_work_id.py、tests/test_tcg_work_matching_integration.py、既存design-keyword.md/recon.md、ADR154のWhyと生成索引、evidence-registry.md、tasks/todo.md、本カード。
手順1 span出力契約・p2版・p1互換・内容を含まない診断を設計どおり実装。
手順2 make lint-ci、check-task-state.sh、card-lint.sh、diff --check。Docker不在では実PGはCIで実行。Gemini実呼出しは禁止。
手順3 ready PR作成、正式カード検査違反0を先に確認。設計の再解釈・推測補正・DB/CI/secrets変更・追加本番操作は禁止。
期待: 模擬8種拒否/正常span、p1/p2実PG互換が成功。報告は本カードの実行結果として自己レビューとCI実行結果を区別する。GO3441を追加PRへ流用しない。
END OF CARD


## 実行承認待ちカード CARD-LINE-WORK-COMPARE-03

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
読んだ節: docs/handoff/design-partner-card-ops/guards/04-worktree.md、11-lint.md。照合: 1記号○/2ready PR○/3報告宛先○/4読取比較1目的○/5起点○/6書式○/7合格条件○。本カードの発行は実装開始の承認ではない。
受領確認: CARD-LINE-WORK-COMPARE-03。設計design-keyword.md §17、recon「作品IDのみ比較の設計棚卸し」。自己審査APPROVEは読取商品比較のみ。既存設計文書のPR/版を読んで、POが比較実装を明示承認した後に開始する。
手順0: executor-preflightを実行し、最新origin/main起点のrelease/line-work-id-comparisonをnew-worktree.shで準備する。既存同名の有無/台帳先約を先に調べる。机作成の完了と実在確認は分ける。既存セッションの机へ無断で入らない。エージェントは追加起動しない。
許可ファイル: backend/app/services/tcg_work_comparison_svc.py、backend/tests/test_tcg_work_comparison.py、backend/tests/test_tcg_work_comparison_pg.py、既存design-keyword.md/recon.md、tasks/todo.md/evidence-registry.md、本カード。実装差分は新サービスと新試験のみ、既存製品コードの変更/削除0。本番の判定ルールに修正が必要なら本カードを止めて設計へ戻す。
手順1: 入力固定・2列応答の厳格parser・既存純粋商品照合呼出し・非公開比較レポートを実装する。DB接続はREAD ONLY、API中transaction保持なし、入力/マスタの再読取SHA一致必須。書込み再解析関数を呼ばない。RAW欄や行番号を応答へ要求しない。欠落/余剰/重複/未知ITEM_IDやUUIDは拒否する。
API前の対照計算は、同一マスタ/RAW/処理で旧作品判断の商品結果を再現する。保存結果/旧判断対照/新判断候補を分離し、対照不一致なら原因未確定のまま実APIへ進まない。
手順2: 合成データで正常順/逆順、欠落/余剰/重複/不正UUID、未知/空WORK_ID、同名異ID、訂正発生、参照変更、RAW変更、ID集合変更を検証する。模擬モデル以外の呼出しはテスト失敗にする。
手順3: PostgreSQLで比較前後の全既存表内容一致とDBロール/transactionによるDML拒否、実analyzerとの差を検査する。商品名/型番限定/作品不明/複数候補/単位区分/Single除外を含む合成ケースで商品IDと候補集合の一致を確認する。本番analyzerを使う比較対照の書込みは隔離したCI DBだけ。全状態再解析一致とは称さない。
手順4: make lint-ci、check-task-state、card-lint、git diff --check。Docker不在では実PG試験はGitHub CIへ。期待は模擬/実PG試験が全成功、差分対象外0、既存製品変更/削除0。失敗項目はIDと理由を非公開証跡で特定する。
手順5: gh-pr-create-safe.shでready PRを作成する。--draft禁止。本文の良い例「- 設計: docs/handoff/tcg-product-master-growth/design-keyword.md」。禁止形は架空URLや未保存文書への参照。今回のGO番号は未採番。3441/3458を流用しない。
禁止: 実装テストでGemini実呼出し、本番DML/再解析/結果採用/配信、DB/CI/deploy/secrets変更、既存RAWの更新、判定不能の推測補完、承認ガード解除。後段の実Gemini比較も、CI合格・正規マージ/本番反映確認後の別手順とする。
完了報告の冒頭は「本報告はカード CARD-LINE-WORK-COMPARE-03 の実行結果である」。本文に検証の生出力を全文含め、停止時は手順番号/最後のコマンド/理由を記す。PO説明では比較設計合格・実装/CI・本番比較未実施・採用/配信未完了を分ける。
END OF CARD


## 実装承認待ち CARD-LINE-WORK-CLIENT-04

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
読んだ節: docs/handoff/design-partner-card-ops/guards/04-worktree.md、11-lint.md。受領確認: CARD-LINE-WORK-CLIENT-04。設計design-keyword.md §17.12、reconのClient寿命不具合節。自己審査APPROVE、PO実装承認待ち。
手順0: POが修正実装を承認した場合のみ、executor-preflight後に最新origin/main起点の専用release/line-work-client-lifetimeを公式new-worktreeで準備する。先約確認必須。新エージェント自動起動禁止。
許可ファイル: backend/app/services/tcg_work_comparison_svc.py、backend/tests/test_tcg_work_comparison.py、既存design-keyword.md/recon.md、本カード、tasks/todo.md、docs/ai-agents/evidence-registry.md。
手順1: call_work_modelのclientをwithで保持し、応答text取得後/例外時にclose。ほかの関数やモデル設定を変えない。
手順2: 毎回新規FakeClientを生成する寿命感知試験を追加。旧実装失敗/修正後成功、正常/例外時解放、引数/text契約を確認。Gemini実通信禁止。
手順3: make lint-ci、既存Backend CI、check-task-state、card-lint、diff --check。Docker不在のローカルpytestは禁止、実PGは既存CI。合格は試験全成功と対象外差分0。
手順4: gh-pr-create-safe.shでready PR、--draft禁止。本文の良い例「- 設計: docs/handoff/tcg-product-master-growth/design-keyword.md」。正式card-lint違反0を先に確認。GO3465の転用禁止。
禁止: DB/CI/secrets/配信仕様変更、本番修正直書き、修正前後のGemini試験実呼出し、自動再試行追加、採用/全再解析/配信、未確認成功宣言。新設計へ広げる必要がある場合は停止する。
本報告はカード CARD-LINE-WORK-CLIENT-04 の実行結果である、と冒頭に記す。検証の生出力と自己確認/CIを区別し、停止時は手順番号/コマンド/理由を記録する。
END OF CARD


## 実装承認済み CARD-LINE-EXTRACTION-TIMEOUT-05

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
mode: handoff。状態: 実装承認済み・発行。読んだ節: guards/04-worktree.md、guards/11-lint.md。受領確認: CARD-LINE-EXTRACTION-TIMEOUT-05。design-keyword.md/recon.md「シンソク抽出の時間制限見直し」、ADR-154/ADR-113に従う。
手順0: POが300/330秒の限定実装と実装役への委任を承認した。受領記録2026-09-13 14:44 JST、PO原文「進める」。マージ・本番反映の承認ではない。公式作成済みrelease/shinsoku-extraction-timeout-designを使用し、preflightと現在HEAD/先約を確認する。実装担当1名へbackendの許可ファイルだけを委任。設計担当は文書を所有し、相互の変更を戻さない。
許可ファイル: backend/app/tasks/tcg_extraction.py、backend/tests/test_tcg_gemini_extraction.py（既存試験不足時のみ）、design-keyword.md、recon.md、本カード、tasks/todo.md、docs/ai-agents/evidence-registry.md。
手順1: tcg.extract_source_messageだけsoft_time_limit=300、time_limit=330にする。他の設定・処理は変更しない。
手順2: 登録task属性を確認。make lint-ciと既存Backend CIで通常抽出/例外処理の回帰0を確認。Dockerなしのローカルpytestは禁止。模擬応答のみ。
手順3: check-task-state.sh、card-lint.sh、git diff --check。期待: 違反0・対象外製品差分0・原文/解析サービス差分0。結果を設計/recon/台帳へ追記。
手順4: 正式レビュー手順でPR提出。本カードはマージ/本番反映/再抽出/配信を許可しない。番号付きGOの創作・転用は禁止。
禁止: 本番DML、実Gemini試験、マスタ修正、モデル/prompt/SDK再試行/配信変更、全taskの時間制限変更、CI/deploy/scripts/secrets変更、ガード解除。設計範囲で進められる場合のみ続行。
本報告はカード CARD-LINE-EXTRACTION-TIMEOUT-05 の実行結果である、と冒頭に記す。検証の生出力を添え、停止時は手順番号・コマンド・理由を記す。
END OF CARD
