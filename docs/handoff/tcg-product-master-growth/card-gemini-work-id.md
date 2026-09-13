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
