# rule-enforcement recon（決まりを機械の検査に変える：現状調査）

- 調査の起点: origin/main df81bce7d（作業場所 release/rule-enforcement-design）
- 種別: 読み取り専用の調査（フェーズ2）。製品コード・CI・設定・Ruleset は変更していない
- 生出力の置き場: /tmp/CC報告ファイル/an-gov/rule-enforcement/（各節に個別のファイル名を書く）
- 前回調査（起点）: /tmp/CC報告ファイル/an-gov/pre-guard-recon.md、/tmp/CC報告ファイル/an-gov/rule-enforcement-matrix.md、/tmp/CC報告ファイル/an-gov/ruleset-15777895.json
- ラベル: 【事実】は根拠（file:line か保存した出力）付き。【未確認】は今回確かめていないこと。推測は書かない

## 0. 要点

【事実】
- 4 章の表に挙げた決まりは 85 件（A=AGENTS.md 21、C=CLAUDE.md 2、E=executor-checklist 11、S=STANDARD-WORKFLOW 13、B=branch-operations 6、F=frontend 16、K=backend 16）。同じ段落や同じ仕組みで守られる命令文は 1 件にまとめて数えた
- 判定の内訳: 止める 27／一部止める 11（止める側は計 38）／警告のみ 0／無し 23／未確認 24。「警告のみ」で終わる決まりは表に無いが、決まりの一部が警告止まりの箇所はある（F04 は node_modules が無いと警告して飛ばす、K16 の mypy、S06 の初期期間）
- GitHub 側（ruleset と CI）だけが、手元CC・クラウドCC・Codex・人の手のすべてに効く
- 手元の ~/.claude の hook は手元の Claude Code にだけ効く。リポジトリ内 `.claude/settings.json` の hook はクラウドだけで効く（前回調査 pre-guard-recon.md）
- 素通りできる人: 現在の ruleset にバイパス権者がいるかは見えない（2 章）。だから「いる／いない」とは言えない

## 1. 準備（作業場所と事前確認）

【事実】
- 作業場所: `/Users/tanizawashingo/worktrees/release-doc-agenda-nav-maintain-m4/release-rule-enforcement-design`（ブランチ release/rule-enforcement-design、起点 origin/main df81bce7d）
- 配置が m4 の作業場所の下になっている（new-worktree.sh の出力どおり。変更していない）
- `./scripts/dev/executor-preflight.sh` は PREFLIGHT OK。警告は 2 つ（本店チェックアウトが 4856 コミット遅れ、本店に未コミット 31 件）。出力: /tmp/CC報告ファイル/an-gov/rule-enforcement/preflight.txt
- new-worktree.sh は最後の Claude 自動起動で「Input must be provided」と出たが、作業場所は作られている

## 2. Ruleset とバイパス

【事実】
- 持ち主は個人アカウント（c3-owner.txt = User）。組織の ruleset は 404（c2-org-rulesets.txt）。リポジトリの ruleset は 2 つ: 16619490「Protect develop branch」と 15777895「main branch protection」（c1-rulesets-parents.json）
- 今回の実行者 shingo-cc は write 権限のみで admin ではない（c5-perm.txt: admin false / push true）。shingo-ops は admin（c4-collab.txt）
- 両 ruleset の JSON に `bypass_actors` の項目が無い（c6-ruleset-15777895.json、d-ruleset-16619490.json）。同じ JSON に `current_user_can_bypass: "never"` がある（これは実行者 shingo-cc についての値）
- main ruleset 15777895（対象 ~DEFAULT_BRANCH）のルール（このほか ruleset 全体に require_extra_approval_for_unattributed_changes: true。必須チェック 16 件のうち 6 件は integration_id 15368＝GitHub Actions 付きで登録）:
  - deletion
  - non_fast_forward
  - pull_request（承認数 0、コードオーナー審査なし、スレッド解決不要、マージ方法は merge のみ）
  - required_status_checks（strict true、16 件）
- develop ruleset 16619490（対象 refs/heads/develop）のルールは 2 つだけ: deletion と required_status_checks（strict false、13 件）。pull_request も non_fast_forward も無い。ADR-136 `docs/adr/ADR-136-cc-bot-github-identity.md:79` にも「develop: pull_request rule 存在せず」とある
- ADR-135 `docs/adr/ADR-135-release-stowaway-prevention.md:65` に「main の bypass_actors（admin=shingo-ops）は維持（バイパスはログに残る）」とある。これは ADR 本文の記述で、現在の設定の観測ではない

【未確認】
- 現在の main ruleset の bypass_actors の中身（admin でないと見えない。shingo-ops の権限で `gh api` を引けば確認できる）
- develop への直 push を GitHub が拒否するか（ルール上は pull_request が無いので止める型ではない。拒否の有無は push を試していない）
- 素通りできる人が実際にいるか。ADR-135:65 の記述が正なら shingo-ops（admin）が該当する可能性があるが、設定の観測はまだ

## 3. 必須チェック 16 件の動く条件

出典の列は `.github/workflows/` 配下。「自動で緑」は、条件に合わないとき集約ジョブが skip を成功として扱うこと。

| # | 必須チェックの名前 | ワークフロー | 動く条件（根拠） | 条件外のとき |
|---|---|---|---|---|
| 1 | pytest (SQLite + PostgreSQL RLS) | test.yml | main と develop 向け PR（:4-7）。中身は backend/**、migrations/**、scripts/**、pyproject.toml、docker-compose*.yml、test.yml 自身の変更時（:43-50） | 集約ジョブが成功（:251-269、if: always()） |
| 2 | テナントスキーマ整合性チェック | schema-check.yml | backend/app/models.py、migrations/、scripts/migrate_*、scripts/db/、scripts/setup_tenant.py、自身の変更時（:40） | 集約ジョブが成功（:222-238） |
| 3 | マイグレーションSQL 実行テスト（実DB） | migration-test.yml | migrations/**、scripts/migrate_*.py、check-migration-registration-exists.sh、run_all_migrations.sh、scripts/migration-guard/**、migration-dryrun-report.py、自身の変更時（:41-48） | 集約ジョブが成功（:1844-1866） |
| 4 | models.py に新 Column → deploy.yml にマイグレーション追記必須 | migration-guard.yml | 全 PR で起動（:3-5）。各ステップは差分に応じて動く | ステップごとに「なし」で緑 |
| 5 | ADR-072 tenant schema lint (strict mode) | lint-tenant-schema.yml | backend/app/routers/、scripts/lint_tenant_schema.py、自身の変更時（:53） | 成功 |
| 6 | Lint & Dark Mode Check (ADR-067) | e2e.yml | frontend/** と e2e.yml の変更時（:52-56）。中身は `npm run check:all`（:81-82） | skip を成功扱い（:124-143） |
| 7 | gitleaks（シークレット漏洩検出） | secret-scan.yml | 全 PR、条件なし（:8） | - |
| 8 | CLAUDE.md line count check | check-claude-size.yml | AGENTS.md、CLAUDE.md、＊＊/CLAUDE.md、＊＊/AGENTS.md、docs/INDEX.md の変更時（:23） | skip で緑 |
| 9 | ADR index is up to date | adr-index-check.yml | docs/adr/ADR-*.md、docs/adr/README.md、scripts/generate-adr-index.js の変更時（:19-22） | 緑（:33-35） |
| 10 | UI governance gate | ui-governance-gate.yml | main と develop 向け PR は常に | - |
| 11 | dangling-route gate | dangling-route-gate.yml | main と develop 向け PR は常に | - |
| 12 | warn-direct-lesson-edit | lessons-guard.yml | 全 PR。§6 に追記があり lessons-cleanup ラベルが無いときだけ失敗（:24-29） | 緑 |
| 13 | guard-authoring/evaluation | guard-authoring-gate.yml | pull_request_target のジョブがコミットステータスを出す（:16-18,43-66）。main 向けの全 open PR に出る | 管理対象パスの変更が無ければ outside-scope で ok（scripts/check-guard-evaluations.js:91） |
| 14 | process-artifacts gate | process-artifacts-gate.yml | main と develop 向け PR（opened／synchronize／reopened／edited）は常に（:8-11）。docs だけの変更は一部の照合を自動スキップ（前回調査） | - |
| 15 | API contract is up to date | api-contract-check.yml | main 向け PR は常に（:3-5）。frontend/api-contract/ の差分があれば失敗（:50-55） | - |
| 16 | doc index reachability | doc-index-reachability.yml | main 向け PR、main への push、定期実行（:6-11）。`--strict` | - |

【事実】3 つのワークフローの冒頭に「必須ではない」と書いてあるが、3 つとも main ruleset の必須チェックに入っている（ui-governance-gate.yml:6、dangling-route-gate.yml:5、process-artifacts-gate.yml:5）。ADR-144 も :103 で非必須と書き、:139 で必須登録済みと書いていて食い違う（`docs/adr/ADR-144-ui-component-governance.md`）。
【事実】develop の必須チェック 13 件は、上の表から #12、#13、#15、#16 を除き「Playwright E2E (chromium)」を足したもの（d-ruleset-16619490.json）。

## 4. 決まりの一覧と強制の有無

判定の意味: 止める＝違反すると失敗や拒否になる／一部止める＝一部の条件でだけ止める（備考に範囲）／警告のみ＝通すが表示する／無し＝強制する仕組みを検索して見つからなかった／未確認＝今回仕組みを特定していない。
「誰に効くか」: 手元CC＝手元の Claude Code、クラウドCC＝クラウドの Claude、全員＝GitHub 側（ruleset と CI）。
見つからなかったと書いた箇所の検索範囲は、前回調査（pre-guard-recon.md）の hook 一覧と今回の `.github/workflows/`、`scripts/`、`frontend/package.json`、`frontend/.husky/`。範囲外は 未確認 のままにしてある。

| ID | 決まり | 決まりの出典 | 強制する仕組み（根拠） | 判定 | 誰に効くか |
|---|---|---|---|---|---|
| A01 | ADR を優先・メモリを根拠にしない | AGENTS.md:12-13 | 見つからなかった | 無し | - |
| A02 | 不可逆操作は PO 確認 | AGENTS.md:15-21 | ~/.claude の agent-danger-hook.sh、クラウドは guard_pre_tool.py K1（pre-guard-recon.md） | 止める | 手元CC・クラウドCC。Codex と人の手は対象外 |
| A03 | 暗号化済シークレットの手動投入・destructive 常時厳禁 | AGENTS.md:21 | 今回は仕組みを特定していない | 未確認 | - |
| A04 | VPS は制限付き鍵のみ | AGENTS.md:23-28 | VPS 側 ForceCommand（VPS 側の設定は今回見ていない） | 未確認 | - |
| A05 | 無制限鍵で変更作業をするときは作業ごとに PO の GO | AGENTS.md:26 | 見つからなかった | 無し | - |
| A06 | 鍵・パスワード・トークンの値を表示しない | AGENTS.md:27 | 見つからなかった | 無し | - |
| A07 | main への直コミット・直 push 禁止、release/* → main は PR 経由 | AGENTS.md:30 | ruleset 15777895 の pull_request ルール、worktree-only-guard、frontend/.husky/pre-commit:3-26 | 止める | 全員（GitHub 側）。バイパスは 未確認 |
| A08 | develop への直コミット禁止 | AGENTS.md:30 | ruleset 16619490 は deletion と必須チェックのみ。直 push が拒否されるかは試していない | 未確認 | - |
| A09 | PR は shingo-cc 名義（コード変更 PR） | AGENTS.md:31 | scripts/check-process-artifacts.js:808-820（前回調査） | 止める | 全員（CI。docs-only PR は対象外） |
| A10 | PR 作成前に gh auth status で名義確認 | AGENTS.md:31 | 見つからなかった | 無し | - |
| A11 | 作業前に new-worktree.sh で作業場所を作る | AGENTS.md:32 | worktree-only-guard.sh／worktree-access-guard.sh（手元）、frontend/.husky/pre-commit:3-26（commit 時のみ） | 止める | 手元CC、Husky が入った環境 |
| A12 | main / develop を消さない | AGENTS.md:33 | 両 ruleset の deletion ルール | 止める | 全員 |
| A13 | migrations/・deploy.yml・本番 scripts/ を含む PR は GO まで main にマージしない | AGENTS.md:34 | scripts/check-process-artifacts.js:111-125,345-379 → 必須チェック process-artifacts gate | 止める | 全員（CI） |
| A14 | 作業開始前に executor-preflight.sh を実行 | AGENTS.md:39 | スクリプトはあるが実行したかを確かめる仕組みは見つからなかった | 無し | - |
| A15 | STANDARD-WORKFLOW の 3 フェーズに従う | AGENTS.md:40 | check-process-artifacts.js の recon／設計の実在検査（L407-505） | 一部止める | 全員（CI。docs 単独 PR は自動スキップ） |
| A16 | 仕入元の原文を書き写さない | AGENTS.md:41 | scripts/agent-hooks/confidential-quote-guard/（ADR-1045） | 止める | 手元CC のみ |
| A17 | push は git -C <絶対パス> push -u を単独で、PR 本文はファイルで渡す | AGENTS.md:41 | 同上の見張り | 止める | 手元CC のみ |
| A18 | executor-checklist.md を読む | AGENTS.md:42 | 見つからなかった | 無し | - |
| A19 | 手順を答える前に docs/INDEX.md を辿る | AGENTS.md:43 | 見つからなかった | 無し | - |
| A20 | frontend/ backend/ を触る前に各 AGENTS.md を開く | AGENTS.md:44 | 見つからなかった | 無し | - |
| A21 | Legacy（jarvis-claude.uk）を独断で削除しない | AGENTS.md:11 | 今回は仕組みを特定していない | 未確認 | - |
| C01 | 作業場所を作るときは --claude を付ける | CLAUDE.md:7 | 見つからなかった | 無し | - |
| C02 | .claude/agents 変更前に git pull | CLAUDE.md:8 | 見つからなかった | 無し | - |
| E01 | 1 便 1 目的・指示外をしない | docs/ai-agents/executor-checklist.md:7-18 | 見つからなかった | 無し | - |
| E02 | 触る／削除するファイルを宣言し実測と照合 | 同:7-18 | scripts/dev/validate-pr-body.sh 検査5-6、scripts/check-process-artifacts.js:847-915 | 一部止める | 手元CC（hook）、全員（CI。PR 番号 2600 以上・docs 単独は自動スキップ） |
| E03 | 報告の全文・消化○× の自己チェック | 同:7-18 | 見つからなかった | 無し | - |
| E04 | track-record の相乗り記帳 | 同:7-18 | 見つからなかった | 無し | - |
| E05 | gh pr create/edit は Write で本文ファイル → 別コマンドで渡す | 同:7-18 | pr-body-guard.sh（前回調査）、confidential-quote-guard | 止める | 手元CC のみ |
| E06 | サブエージェント報告の末尾に DONE／BLOCKED ラベル | 同:7-18 | require-status-label.sh（前回調査） | 止める | サブエージェントの手元CC |
| E07 | recon は読み取り専用・file:line・SHA 併記 | 同:20-23 | check-process-artifacts.js:407-500,681 は file:line が 1 件も無いと失敗。読み取り専用と SHA 併記は検査なし | 一部止める | 全員（CI。docs 単独 PR は自動スキップ） |
| E08 | 設計は最終形の全文・節番号の重複なし | 同:25-30 | scripts/check-doc-heading-duplicates.sh（対象は STANDARD-WORKFLOW.md と design-partner.md の 2 つ）、.github/workflows/process-artifacts-gate.yml:46-47 | 一部止める | 全員（CI） |
| E09 | 正本・統治ファイルは危険ファイル扱い＋PO の GO | 同:25-30 | check-process-artifacts.js:111-125（STANDARD-WORKFLOW.md 等は GO 要求。AGENTS.md・CLAUDE.md は宣言照合まで） | 一部止める | 全員（CI） |
| E10 | 迷ったら止まる・フックに止められたら言い換えない | 同:32-44 | 見つからなかった | 無し | - |
| E11 | 若い番号の PR に譲る | 同:46-52 | 見つからなかった | 無し | - |
| S01 | Phase1 KGI・PO 承認 | docs/STANDARD-WORKFLOW.md:18-28 | check-process-artifacts.js の宣言読み取りのみ（前回調査、一部未精読） | 一部止める | 全員（CI） |
| S02 | Phase2 recon の実在 | 同:18-28 | validate-pr-body.sh 検査3、check-process-artifacts.js:407-500,673-681 | 止める | 手元CC、全員（CI） |
| S03 | Phase3 設計の実在・設計→recon→ADR の相互参照 | 同:18-28 | validate-pr-body.sh 検査4、check-process-artifacts.js:499,505 | 止める | 手元CC、全員（CI） |
| S04 | §1.5 設計仕様書の先読み・リンク | 同:30-39 | 見つからなかった | 無し | - |
| S05 | §1.6 親子リンク・素人向け 1 行 | 同:43-53 | 同:53 に「文章規約であり関所による機械強制ではない」と明記 | 無し | - |
| S06 | §1.7 維持の仕組み欄 | 同:55-63 | check-process-artifacts.js:88（MAINTENANCE_GRACE_PR=2600。初期は警告、以降は停止） | 一部止める | 全員（CI） |
| S07 | §1.8 3 段階振り分け | 同:65-77 | 見つからなかった | 無し | - |
| S08 | 新しい手順書は INDEX か specs/README に「いつ読むか」付き 1 行 | 同:77 | .github/workflows/doc-index-reachability.yml:30（check_doc_index.py --strict）。必須チェック | 止める | 全員 |
| S09 | PR 本文に「標準ワークフロー確認」 | 同:79-104 | validate-pr-body.sh 検査1、guard_pre_tool.py:16,632 | 止める | 手元CC・クラウドCC。CI 側は process-artifacts |
| S10 | 危険変更（migrations・deploy.yml・scripts）の GO | 同:136-149 | check-process-artifacts.js:111-125,345-379 | 止める | 全員（CI） |
| S11 | 完了の定義(4)：人の動作確認・evidence 記録 | 同:88-104 | 見つからなかった | 無し | - |
| S12 | 未知点プロトコル | 同:120-124 | 今回は仕組みを特定していない | 未確認 | - |
| S13 | 免除・関所の運用 | 同:136-173 | 今回は仕組みを特定していない | 未確認 | - |
| B01 | PR は Draft から | docs/specs/branch-operations/README.md:82-95 | 今回は仕組みを特定していない | 未確認 | - |
| B02 | break-glass の手順 | 同:82-95 | 今回は仕組みを特定していない | 未確認 | - |
| B03 | マージはマージコミットのみ | 同:82-95 | ruleset 15777895 の allowed_merge_methods が merge のみ | 止める | 全員 |
| B04 | マージ前に reviewer（opus）の APPROVE | 同:82-95、ADR-1029 | ~/.claude の review-gate、クラウド guard が gh pr merge を止める。ruleset の承認数は 0 | 止める | 手元CC・クラウドCC。人の手の gh と GitHub 画面には効かない |
| B05 | release PR の記載一覧 | 同:82-95 | 今回は仕組みを特定していない | 未確認 | - |
| B06 | develop は第 3 便まで残置・新規作業で使わない | 同:97-103 | 見つからなかった（develop の ruleset は直 push を止める型ではない） | 無し | - |
| F01 | 画面タイトルは PageLayout 経由・raw h2 禁止 | frontend/AGENTS.md:5-19 | frontend/eslint.config.js:140-149、check:page-layout（frontend/package.json:24） | 止める | 全員（CI の Lint & Dark Mode Check。frontend 変更時のみ） |
| F02 | subtitleKey で渡す・インラインスタイル禁止 | 同:19 | 今回は仕組みを特定していない | 未確認 | - |
| F03 | 右上ボタンは headerAction・position: fixed 禁止 | 同:19 | check:css-fixed-position（frontend/package.json:32、:46 の check:all に含まれる） | 止める | 全員（CI。frontend 変更時のみ） |
| F04 | 全 UI 文字列は t()・日本語ハードコード禁止（コミット時） | 同:21-31 | frontend/package.json:56（lint-staged の eslint --max-warnings=0）。node_modules が無いと飛ばして警告だけ（frontend/.husky/pre-commit:45-49） | 止める | Husky と node_modules が揃った環境のみ |
| F05 | 同（CI 側） | 同:25 | eslint.config.js:31 は 'warn'、CI の lint は eslint src（package.json:15）で --max-warnings なし。CI で warn が失敗扱いになるかは見ていない | 未確認 | - |
| F06 | ja.json と en.json は同一キー | 同:23 | frontend/scripts/check-i18n-missing-keys.js:101-113 は閲覧ページ辞書の ja/en 一致のみ。本体辞書はコードで使うキーが両言語にあるかのみ（:117-134）。使われないキーの片側欠けは検査なし | 一部止める | 全員（CI の Lint & Dark Mode Check） |
| F07 | UI 部品は金型を使う・生 select 等と色直値禁止・ui-allow は理由と番号 | 同:34-36 | .github/workflows/ui-governance-gate.yml、scripts/check-ui-governance.js:25,122。必須チェック | 止める | 全員 |
| F08 | 色トークンは :root と :root.force-dark の両方 | 同:38-42 | check:dark-parity（frontend/.husky/pre-commit:52-55、check:all） | 止める | Husky 環境、全員（CI。frontend 変更時のみ） |
| F09 | 非色トークンは tokens.css の :root のみ | 同:41 | check:new-tokens は frontend-check.yml:53 にあるが必須チェックではない | 未確認 | - |
| F10 | CSS 詳細度（stylelint no-descending-specificity） | 同:46-53 | check:stylelint（check:all に含まれる）。「grep で確認する」こと自体は検査なし | 一部止める | 全員（CI。frontend 変更時のみ） |
| F11 | lucide-react から直接 import しない | 同:55-58 | frontend/eslint.config.js:118-127 | 止める | 全員（CI の Lint。frontend 変更時のみ）、Husky 環境 |
| F12 | iconSizes.ts は生成物・直接編集しない | 同:60-62 | predev／prebuild で再生成（package.json:51-52）。--check を CI が走らせている形跡は e2e.yml・frontend-check.yml に見つからなかった | 未確認 | - |
| F13 | アイコンに aria-hidden="true" | 同:64 | 今回は仕組みを特定していない | 未確認 | - |
| F14 | UI 変更は同一 PR で tests-e2e の spec を更新 | 同:67-77 | e2e が spec を走らせるが「同一 PR で更新したか」の検査は見つからなかった | 未確認 | - |
| F15 | InboxKartePanel 変更時は karte-visual-gate.spec.ts を同一 PR で更新 | 同:75 | 今回は仕組みを特定していない | 未確認 | - |
| F16 | 新規ページは nav キーを ja/en に追加 | 同:19 | check:nav-sync（check:all に含まれる）。検査内容は読んでいない | 未確認 | - |
| K01 | write endpoint は db.commit() 直後に reset_tenant_context() | backend/AGENTS.md:10 | scripts/lint_tenant_schema.py:6-9,77 → 必須チェック ADR-072 tenant schema lint | 止める | 全員（CI。backend/app/routers/ 変更時のみ） |
| K02 | 新規テナント作成時の 4 ステップ（暫定） | 同:12-22 | 見つからなかった（同:22 に自己消滅の注記あり） | 無し | - |
| K03 | レビュー用テナントのパスワードはホスト側に保存 | 同:8 | 見つからなかった | 無し | - |
| K04 | 移行・バッチ実行時は tenant_code を明示 | 同:9 | 見つからなかった | 無し | - |
| K05 | migration は追加専用（DROP COLUMN／TABLE は ADR 承認） | 同:24-28 | .github/workflows/migration-guard.yml:343-389。型変更・リネームを検出するかは読んでいない | 一部止める | 全員（CI。必須チェック #4） |
| K06 | migration のファイル名はタイムスタンプ形式 | 同:33 | migration-guard.yml:95-111 | 止める | 全員（CI） |
| K07 | migration は deploy.yml に登録 | 同:34-35 | migration-guard.yml:119 | 止める | 全員（CI） |
| K08 | 適用経路を PR 本文に明記 | 同:36 | 今回は仕組みを特定していない | 未確認 | - |
| K09 | 実機 PostgreSQL で information_schema を確認 | 同:37 | 今回は仕組みを特定していない | 未確認 | - |
| K10 | migration-test のセットアップに最小定義を足す | 同:38 | 今回は仕組みを特定していない | 未確認 | - |
| K11 | {schema} プレースホルダ禁止 | 同:39 | migration-guard.yml:171-189 | 止める | 全員（CI） |
| K12 | 新テーブルは全カラムに COMMENT ON COLUMN | 同:66 | .github/workflows と scripts/check-*.js を検索して見つからなかった。ほかの場所は見ていない | 未確認 | - |
| K13 | Pydantic Field に description | 同:67 | 今回は仕組みを特定していない | 未確認 | - |
| K14 | 取引先は companies 系を使う（customers 廃止） | 同:68 | 今回は仕組みを特定していない | 未確認 | - |
| K15 | 受信翻訳は enqueue_inbound_translation() 経由 | 同:69 | 今回は仕組みを特定していない | 未確認 | - |
| K16 | make lint（ruff／bandit／mypy） | 同:70 | .github/workflows/test.yml:84（ruff は止める）、:56（bandit は止める）、:58（mypy は警告のみ）。backend 等の変更時のみ（:43-50） | 一部止める | 全員（CI） |

集計（rows.txt を grep して数えた。出力は /tmp/CC報告ファイル/an-gov/rule-enforcement/rows.txt）: 合計 85＝止める 27、一部止める 11、警告のみ 0、無し 23、未確認 24。

## 5. i18n の検査はどの必須チェックが走らせるか

【事実】
- ja/en キー検査と日本語リテラル禁止は、どちらも必須チェック「Lint & Dark Mode Check (ADR-067)」（e2e.yml:125）が `npm run check:all`（e2e.yml:82、frontend/package.json:46）で走らせる。中身に `npm run lint`（eslint src、:15）と `check:i18n-missing-keys`（:28）が入っている
- 動く条件は frontend/** か e2e.yml の変更時のみ。それ以外は skip で成功扱い（e2e.yml:52-56,124-143）
- ESLint の `local/no-japanese-literal` は 'warn'（frontend/eslint.config.js:31）。デザインシステム・locales・storybook 等と design-preview では off（:244,:252）
- check-i18n-missing-keys.js:101-113 が比べるのは閲覧ページ辞書 viewer の ja と en だけ。本体辞書 ja.json と en.json の全キー同士の一致は比べていない（スクリプト全体の grep と該当部の読みによる）

【未確認】CI の eslint が warn で失敗するか（--max-warnings の指定が CI 側の記述に見つからなかった）。

## 6. Husky

【事実】
- `frontend/package.json:47` の prepare が `cd .. && husky frontend/.husky`。作業場所で `git config --get core.hooksPath` を引くと `frontend/.husky` が返った
- frontend/.husky/pre-commit:
  - :3-26 作業場所の外のコミットを止める（GITHUB_ACTIONS 設定時は飛ばす）
  - :45-49 lint-staged は node_modules の実行ファイルがあるときだけ動く。無ければ警告して飛ばす（警告のみ）
  - :52-55 dark-parity 検査
  - :58 check-claude-size.js を無条件で実行し、失敗で止める
  - :60-75 ruff は `--exit-zero`（警告のみ）。ruff 未導入のときだけ exit 1
  - :79-83 router 変更時に ADR-072 tenant lint
- frontend/.husky/pre-push: :10-19 rebase 中の push を止める、:23-26 validate-pr-ownership.sh、:30-34 active-work の書式検査
- 出力: fh-segments.txt

## 7. 手元で CI 相当を走らせる入口

【事実】
- `cd frontend && npm run check:all`（frontend/package.json:46、frontend/AGENTS.md:42）。CI の必須チェック #6 と同じ中身
- `cd backend && make check`（backend/Makefile:8。lint-ci と test）
- `scripts/dev/validate-pr-body.sh:288-319` は PR 作成前に check-process-artifacts.js を `LOCAL_PRECHECK=1` で呼ぶ（設計: docs/handoff/local-gate-ci-parity/design.md）
- scripts/dev/desk-check.sh は始業確認（本店でないか、起点の鮮度）のみで、CI 相当ではない（:1-38）
- 個別: scripts/check-process-artifacts.js、scripts/check-ui-governance.js、scripts/check-dangling-routes.js、scripts/generate-adr-index.js、scripts/lint_tenant_schema.py、scripts/check-doc-heading-duplicates.sh、scripts/ci/check_doc_index.py
- ルートに Makefile と package.json は無い。必須チェック 16 件を 1 コマンドで全部走らせる入口は見つからなかった

【未確認】docs/handoff/local-gate-ci-parity/design.md の中身（ファイルの存在のみ確認）。

## 8. ADR の記述（引用）

パスは `docs/adr/` 配下。

- ADR-113-two-mode-dev-flow.md:116-123: モード強制の表。Agent front-matter は soft、SA-19 CI は hard backstop
- ADR-135-release-stowaway-prevention.md:15-16 develop に必須承認なし・process-artifacts は当時 main で必須でなかった／:39 DANGEROUS_PATTERNS に scripts/ を追加／:50 process-artifacts gate を必須チェックに登録／:65 main の bypass_actors（admin=shingo-ops）は維持
- ADR-136-cc-bot-github-identity.md:57-82 承認ベースの統制は回避可能で Ruleset に承認数なし／:79 develop に pull_request rule 無し／:104-110 Ruleset で承認 1 を要求する案は 2026-06-13 に却下し、チャット GO とゲートスクリプトの検証を採用
- ADR-144-ui-component-governance.md:103 非必須と記載／:139 必須チェックとして登録済み（食い違い）
- ADR-1003-go-delegation-to-opus.md:38-45 PO 本人の GO が要る例外。Ruleset 変更・大量 DELETE・secrets・外部 GUI・force push は check-process-artifacts.js が機械検証できない対象で、手順で担保
- ADR-1015-autonomy-b-class-no-po-approval.md:61 権限・hook・CI・Ruleset は対象外
- ADR-1029-review-gate-hook.md:25 マージ前の reviewer APPROVE は文書だけで強制されていなかった／:36 Branch Protection と Ruleset は変更しない
- ADR-1033-conversation-consent-ticket.md:20 除外一覧（main/develop への push、force push、Ruleset 等）／:24 同意票は「GO #PR番号」の代わりにならない
- ADR-1040-doc-agenda-nav-entry-index.md:51-59 強制の仕組みの表（check-claude-size、doc-index-reachability は必須で 2026-10-27 登録、agent-hooks-test は必須でない、週次点検、process-artifacts）／:34 CI は警告で始め、0 件が 5 回連続で失敗に引き上げ
- ADR-1045-confidential-quote-guard.md:9 関連 ADR／:39 展開や git／gh の子コマンドの止め方
- 検索: ADR 全件の語句検索で 66 ファイルが該当（a-adr-hits.txt）。引用行の原文は a-adr-key-lines.txt。docs/adr/FEATURE-INDEX.md:5,:25 は recon 前に ADR を grep するよう求めている

## 9. 文書同士の食い違い

【事実】
- docs/adr/FEATURE-INDEX.md:47 は ADR-1040 を「Proposed」とするが、ADR-1040 本文（:5）は Accepted
- docs/adr/FEATURE-INDEX.md:41 は ADR-135 の Ruleset B/C を「PO GO 待ち」とするが、ADR-135:50 は実施済み
- ui-governance-gate.yml:6、dangling-route-gate.yml:5、process-artifacts-gate.yml:5 の冒頭は非必須と書くが、3 つとも main ruleset の必須チェック
- ADR-144:103 と :139 が互いに食い違う
- docs/specs/branch-operations/README.md は develop を残置・新規作業禁止とするが、develop ブランチは存在し（d-develop-branch.txt）、専用の ruleset がある

## 10. 未確認の一覧

1. 現在の main ruleset の bypass_actors と、素通りできる人の有無（shingo-cc は admin でないため見えない）
2. develop への直 push を GitHub が拒否するか（試していない）
3. CI の eslint が warn（`local/no-japanese-literal`）で失敗するか
4. 本体辞書 ja.json と en.json の全キー一致を検査する仕組みの有無（今回の読みでは見つからなかった）
5. 4 章で「未確認」とした決まり（A03、A04、A08、A21、S12、S13、B01、B02、B05、F02、F05、F09、F12-F16、K08-K10、K12-K15）の強制の有無
6. Codex に効く強制の有無（Codex 用の hook 設定は今回見ていない）
7. VPS 側 ForceCommand の設定内容

## 11. 生出力の置き場

/tmp/CC報告ファイル/an-gov/rule-enforcement/ 配下:
- preflight.txt
- c1-rulesets-parents.json、c2-org-rulesets.txt、c3-owner.txt、c4-collab.txt、c5-perm.txt、c6-ruleset-15777895.json
- d-ruleset-16619490.json、d-develop-branch.txt
- a-adr-key-lines.txt、a-adr-hits.txt
- e-i18n-grep.txt
- g-jobnames.txt、g-triggers.txt、g-segments.txt、g-evalctx.txt
- fh-segments.txt、h-segments.txt、h2-segments.txt、rows.txt（4 章の行の抜き出し）
