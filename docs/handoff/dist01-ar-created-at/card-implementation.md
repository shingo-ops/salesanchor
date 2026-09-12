CARD-DIST01-PREVIEW-3258-01
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、03-file.md、04-worktree.md、05-pr.md、09-gh.md、10-executor.md、11-lint.md。
照合: 1○記号、2○新規PRなし、3○報告全文、4○1目的、5○既存起点、6○書式実例、7○出力で検証。
追加照合: 未確定目印なし○、対象名出力○、実在作業台○。
受領確認: 「CARD-DIST01-PREVIEW-3258-01を受領」と返す。

設計: docs/handoff/dist01-ar-created-at/design.md（2026-09-12版、mode: handoff）。
目的: previewの不存在列をcomputed_atへ直し実PG試験を追加する。
起点origin/release/fix-dist01-ar-created-at、確認時HEAD 3df471abbe7dfeba8adc6a0723ae0a272dc0f163。
既存作業台を継続。台帳同ブランチ/PR3258登録済み。新規worktree不要。
許可: backend/app/services/tcg_distribution_svc.pyの日時条件1行、backend/tests/test_tcg_distribution_pg.py新規作成。
文書はdocs/handoff/dist01-ar-created-at配下のdesign.md、recon.md、本カードの3件。既存の設計担当差分を保持する。
コード・試験は編集ツールで作成してよい。fixtureの実装詳細は設計を守る範囲で担当が決める。
ローカル実装・検証・コミットまで。push/PR作成/PR本文編集/本番マージ/本番操作/GO発行/エージェント起動は禁止。
DB migration、CI、運用scripts、secrets、配信設定、他者差分の変更も禁止。mainからreleaseへのローカル統合のみ許可。

停止時: 手順番号・最後のコマンド・理由・生出力全文を返す。範囲内の実装/試験不備は修正・再実行可。
未知の設計判断、他者差分、範囲外変更、権限拒否は設計担当へ戻す。実PG未検証・品質失敗では実装コミットに進まない。
無害な行数差は対象名と数値を記録して判定する。commitはlogで確認する。
報告冒頭: 本報告はカード CARD-DIST01-PREVIEW-3258-01 の実行結果である。
報告に全実行出力、修正前/後の試験結果、実行済/未実行の検証、HEAD、変更一覧を含める。
ログ保存先は /tmp/CC報告ファイル/dist01-3258/ 。パスを変えず作成し添付する。

手順0: preflight
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && ./scripts/dev/executor-preflight.sh
手順1: 作業台と既存変更確認
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && git status --short --branch
手順2: 参照更新
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && git fetch origin
手順3: ブランチから既存PR確認。番号3258・OPENを照合
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && gh pr view --json number,headRefName,headRefOid,state,url
手順4: 設計文書3件のみを指定
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && git add docs/handoff/dist01-ar-created-at/design.md docs/handoff/dist01-ar-created-at/recon.md docs/handoff/dist01-ar-created-at/card-implementation.md
手順5: 設計を保存。既に同内容保存済みなら重複コミットしない
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && git commit -m 'docs(dist01): finalize analysis-time preview design'
手順6: コミット実在確認
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && git log -1 --format=fuller
手順7: 最新main統合。競合は独断で解消せず報告
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && git merge --no-edit origin/main
手順8: design.mdの12ケースを新規試験へ実装。CIで接続変数欠落は失敗、ローカルskipは未検証扱い
手順9: Docker確認。利用不可ならlintのみ実施し実PG未検証を報告
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && docker info --format '{{.ServerVersion}}'
手順10: コンテナ名の空き確認。既存があれば上書きせず報告
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && docker ps -a --filter name=dist01-3258-pg --format '{{.Names}} {{.Image}} {{.Ports}}'
手順11: 空き確認後、ローカル専用DB起動
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && docker run -d --name dist01-3258-pg --publish 127.0.0.1:55432:5432 --env POSTGRES_DB=jarvis_test_db --env POSTGRES_USER=jarvis --env POSTGRES_PASSWORD=dist01-local-test postgres:16
手順12: 起動確認。起動中なら短い間隔で最大30回同じ確認。失敗は報告
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && docker exec dist01-3258-pg pg_isready -U jarvis -d jarvis_test_db
手順13: 検証環境作成
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && python3 -m venv /tmp/dist01-3258-venv
手順14: 指定依存導入
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && /tmp/dist01-3258-venv/bin/python -m pip install -r backend/requirements.txt -r backend/requirements-dev.txt
手順15: 対象条件1行をar.created_atへ一時変更し、同じ試験が不存在列で失敗することを記録
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at/backend && RLS_ADMIN_DATABASE_URL=postgresql+asyncpg://jarvis:dist01-local-test@127.0.0.1:55432/jarvis_test_db /tmp/dist01-3258-venv/bin/python -m pytest tests/test_tcg_distribution_pg.py -q --tb=short
手順16: 対象条件1行をar.computed_atへ直し、専用試験skip0と既存配信試験の成功を確認
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at/backend && RLS_ADMIN_DATABASE_URL=postgresql+asyncpg://jarvis:dist01-local-test@127.0.0.1:55432/jarvis_test_db /tmp/dist01-3258-venv/bin/python -m pytest tests/test_tcg_distribution_pg.py tests/test_tcg_distribution.py -q --tb=short
手順17: lint。mypy警告も報告
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at/backend && PATH=/tmp/dist01-3258-venv/bin:$PATH make lint-ci
手順18: 実差分確認。製品は1行と専用試験、文書3件
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && git diff origin/main --stat
手順19: 空白検査
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && git diff --check
手順20: 全検証成功後、製品と試験のみを追加
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && git add backend/app/services/tcg_distribution_svc.py backend/tests/test_tcg_distribution_pg.py
手順21: 実装ローカルコミット
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && git commit -m 'fix(dist01): use computed_at with PostgreSQL regression tests'
手順22: 最終コミット実在確認
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && git log -1 --format=fuller
手順23: 最終状態を報告し終了。pushしない
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && git status --short --branch
END OF CARD
