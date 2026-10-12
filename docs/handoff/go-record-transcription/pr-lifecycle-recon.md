# PR作成とマージ審査の現状調査（2026-09-28）

この文書は何か: 提出前の承認要求と、マージ前の検査の不足を実物から確かめた記録。
親: [GO記録の手順](README.md)。設計: [限定修正設計](pr-lifecycle-design.md)。
対象ADR: ADR-113、ADR-121、ADR-135、ADR-136。
調査基準: origin/main 4bad43a4dca6368ffa7370792a3c912e90bba521。
担当: Sol調査、Astra原典読み取り/設計。製品の現状と設計案を区別する。

| 根拠 | 観測事実 |
|---|---|
| scripts/gh-pr-create-safe.sh:26-42 | PR作成前にfull checkerを呼ぶが本文・SHA・PR番号を渡さない |
| scripts/dev/validate-pr-body.sh:283-324 | 準備段階でもGO節と番号を要求。実番号一致は確認できない |
| scripts/gh-pr-merge-safe.sh:39-83 | .pr-numberと台帳の所有権確認 |
| scripts/gh-pr-merge-safe.sh:92-164 | マージ直前GO検査なし。自動main追従後も再送する |
| scripts/check-process-artifacts.js:257-333 | GO四欄/発行者/番号の判定正本 |
| scripts/check-process-artifacts.js:663-675 | BASE_SHA/HEAD_SHAがないと失敗 |
| scripts/check-process-artifacts.js:705-742 | 実PRからauthor/bodyを取得、MOCK等の試験入力も存在 |
| scripts/check-process-artifacts.js:830-866 | 危険/ユーザー影響にGO必須。緊急はfollowup起票の副作用あり |
| scripts/tests/test-process-artifacts.js:248-340 | GOの既存単体条件と正常/否定テスト |
| scripts/tests/test-merge-safe-guard.sh:21-99 | 一時git/mock gh、鍵欠落/空と旧自動追従の検査 |
| .github/workflows/process-artifacts-gate.yml:8-44 | 実PRイベントからSHA/番号/repoを渡しfull gate実行 |
| docs/handoff/go-record-transcription/README.md:69-77 | 正規順序はPR作成→番号確定→PO GO→転記→マージ前確認 |

実拒否: LINEガイドの正式create-safe操作はPreToolUseでCanonical PR body validation failed（ユーザー影響変更のGO記録欠落）となった。
ラッパー本体は起動しなかったため、SHA不足はコード読取の事実であり、この操作の実エラーとは区別する。
ローカルCodex adapter.py:639-661はworktree内のvalidatorを無引数で呼ぶ。個人hook/trust設定は今回変更不要。

環境変数調査: BASE_SHA/HEAD_SHA/PR_NUMBER/REPO/HEAD_REF/BASE_REFが本番入力。MOCK_EXTERNAL_API_CHANGE、MOCK_BASE_REF、MOCK_HEAD_REF、MOCK_ADDED_FILES、MOCK_ORIGIN_MAIN_FILES、MOCK_PR_AUTHOR、MOCK_PR_BODY、CHANGED_FILESが試験上書き。
MAINTENANCE_ENFORCEとrequire先のGITHUB_OUTPUTも境界で確認する。資格値は出力していない。
副作用: createFollowupIssueは緊急モードでgh issue createを行い、未マージでも先行マージした文面となる。検証専用モードが必要。
CIの既存2テスト接続: .github/workflowsで名前検索0件。自動実行済みとはしない。

環境: preflight OK。main本店272behind/台帳外未保存18件は保護。関連過去4枝はDONE/PR MERGED、登録worktreeなし。重複進行を確認せず。
作業机上限100のため、自分のguide机だけを整理。87c4ad83aのlocal/remote一致・cleanを確認、ignoredは生成物のみ。ブランチ削除0。
固有UUID退避: /private/tmp/line-guide-parked-20260928/worktree-id.json。実画面証跡は /tmp/reports/card-line-guide-01 に保持。
公式reaperは削除候補0、その後new-worktree.shでrelease/pr-lifecycle-gatesをorigin/main起点に作成。
他者の未保存/未マージの作業場所削除0。UUID: 722c1db5-c61c-4a07-8f67-656f808a4300。

仕様確認: Context7 /websites/cli_github_manualとローカルgh helpで、--match-head-commit、checksのpending exit8、PR JSON各fieldを照合。
出典: https://cli.github.com/manual/gh_pr_merge 、https://cli.github.com/manual/gh_pr_checks 。

未確認: 新実装/回帰試験/本番のmerge結果。Rulesetのrequired status実設定は未調査なので既存workflowが必須登録済みとは断定しない。
未解決の実装前提はなし。上の未確認項目は実装後の試験/承認ゲートで扱う。

## GitHub実設定の追加確認

Sol read-only取得: 2026-09-28T06:28:31Z。実設定変更0。
GET /repos/shingo-ops/salesanchor/rulesets/15777895 と GET /repos/shingo-ops/salesanchor/rules/branches/main は成功。
active ruleset main branch protectionがmainへ適用、PR必須、merge方式だけ許可、required approving reviews=0、current_user_can_bypass=never。
required status checksは13件、strict=true。process-artifacts gateはこの13件に含まれない。
13件: pytest (SQLite + PostgreSQL RLS)、テナントスキーマ整合性チェック、マイグレーションSQL 実行テスト（実DB）、models.py に新 Column → deploy.yml にマイグレーション追記必須、ADR-072 tenant schema lint (strict mode)、Lint & Dark Mode Check (ADR-067)、gitleaks（シークレット漏洩検出）、CLAUDE.md line count check、ADR index is up to date、UI governance gate、dangling-route gate、warn-direct-lesson-edit、guard-authoring/evaluation。
後者3種のうちUI/dangling-route/guard-authoringはintegration_id=15368。
classic /branches/main/protection は404で、未設定か可視性不足かはこの応答だけでは区別しない。
結論: merge helperのfull checkerはGO直前検査を担うが、GitHub UIや素のCLI経路までサーバ側でGOを強制済みとは言えない。Ruleset変更は本便対象外。
