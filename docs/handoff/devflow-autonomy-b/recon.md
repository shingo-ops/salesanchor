# 方針案 vs 今のルール・仕組み（recon）

基準: origin/main = 84eda6a4bda49c6293423cccb9b8b034fbb045ae（`git fetch origin main` 後に `git show origin/main:<path>` で読んだ）
調査日: 2026-10-14 / 読み取りのみ（編集・commit・本番接続なし。gh api は GET のみ）
生データ: 作業時にリポジトリ外へ保存した生出力（check-process-artifacts.js の行番号付き写し、Ruleset・Branch Protection の GET 結果、workflow 一覧）。リポジトリには含めない
略記: file:line の file は origin/main 上のパス。`~/.claude/...` は本店 Mac のローカル実体（リポジトリ外）。

## 要点（先に）
- 【事実】KGI の PO 承認は文書の規則だけで、機械は見ていない（check-process-artifacts.js に KGI 承認を確かめる処理なし。kgi.md は正本扱いの宣言照合のみ :106）。一方、recon／design／対象ADR の実在は機械が見る（:645-695）。
- 【事実】画面・API の不具合修正（frontend/src、backend/app/routers 等）は、免除不可で recon/design/対象ADR が必須（:967 `allowExempt: !hasUserImpacting`）かつ GO 記録が必須（:937-947）。ただし GO は ADR-1003 で Opus に委譲済みなので、B の流れを成立させるのに PO の GO は要らない。
- 【事実】ADR-1003 の委譲は、方針案の A より広い（migrations・deploy.yml・scripts も Opus の GO で通せる。PO 本人必須は DROP を含む migration、workflow-lint.yml など7項目だけ）。方針案 A の 1・2 は「今より厳しくする」案になる。
- 【事実】Opus の `gh pr merge` を止めているのは ~/.claude/settings.json の autoMode.soft_deny（ADR-1003 と食い違う）。
- 【事実】main の Ruleset は承認レビュー0件・merge 方式は merge のみ・bypass なし。必須チェック15件が緑なら、書き込み権限を持つ人（shingo-ops は admin）が UI からマージできる設定。スマホアプリでできるかは【未確認】。

---

## 1. 1件ごとの PO 承認を求めている規則

| # | 規則（要旨） | 場所 | 機械で強制? |
|---|---|---|---|
| 1 | 全タスク3フェーズ。①KGI設定は定量・PO承認 | CLAUDE.md:70-72 / docs/STANDARD-WORKFLOW.md:23（「PO承認が必須ゲート」）, :79（KGI：定量・PO承認済み） | 文書のみ（KGI承認を見る処理は :645-695 に無い） |
| 2 | 1.5 設計仕様書（あるべき姿）の確認・作成（Planner＋PO） | docs/STANDARD-WORKFLOW.md:24, :34-39 | 文書のみ。:63「中身の適切性は人」 |
| 3 | 不明が残ったら PO に相談、不明を残したまま実行しない | docs/STANDARD-WORKFLOW.md:115-119 | 文書のみ |
| 4 | 危ない変更の特例は「認可された人間の承認」でのみ。main マージ＝本番投入可（ADR-135）。GO 記録の軽量ルール | docs/STANDARD-WORKFLOW.md:135-142 | GO記録は機械（check-process-artifacts.js:346-387） |
| 5 | 完了の定義: 危険変更は GO 記録／ユーザー影響変更は本番に出す前に Shingo の GO 記録／人が実際に動作確認 | docs/STANDARD-WORKFLOW.md:83-93 | GO記録は機械。「人の動作確認」は文書のみ |
| 6 | 不可逆操作は必ず PO 確認（permit-danger.sh） | CLAUDE.md:36-40 付近 | 一部のみ機械（§2 のローカルフック） |
| 7 | 無制限鍵の変更作業は作業ごとに PO の GO | CLAUDE.md:29-30 | ローカルフック＋文書 |
| 8 | リリース相当の大きな変更は Draft。PO が確認し GO を出すまで un-draft／マージ禁止 | CLAUDE.md:53 | 文書のみ |
| 9 | main にマージ＝本番投入可。migrations/・deploy.yml・本番 scripts は PO GO まで待機 | CLAUDE.md:56、docs/adr/ADR-135-release-stowaway-prevention.md:23-60 | gate が機械（DANGEROUS_PATTERNS） |
| 10 | 危険PR の GO 手順（ADR-136）。GO 権限は PO。ADR-1003 により例外を除き Opus へ常時委譲 | CLAUDE.md:57 / docs/adr/ADR-136-cc-bot-github-identity.md:49-69 | 機械（AUTHORIZED_GO_ISSUERS :43-45） |
| 11 | ADR-1003: 委譲 GO の条件（必須CI緑・Reviewer APPROVE・PO へ3行報告）と PO 本人必須の7例外 | docs/adr/ADR-1003-go-delegation-to-opus.md:25-45 | 例外のうち2つだけ機械（check-process-artifacts.js:49-86）。残り5つは人手（ADR-1003:45） |
| 12 | 危険操作（正本・関所・migrations・deploy.yml・本番scripts）は PO 自筆 GO 必須、設計パートナー/実装役は代筆しない | docs/ai-agents/design-partner.md:115-116 | 文書のみ。ただし :215 で「実装役が転記してよい」とあり、:116 と緊張関係 |
| 13 | 正本・統治ファイル（STANDARD-WORKFLOW／CLAUDE.md／AGENTS.md／design-partner.md 等）に触れる便は危険ファイル変更PR扱い、PO GO 必須 | docs/ai-agents/executor-checklist.md:28-29 | STANDARD-WORKFLOW.md だけ gate が危険扱い（:121）。他は正本宣言照合まで（:104-109） |
| 14 | 各正本ファイルの変更は PR＋PO 承認のみ | docs/STANDARD-WORKFLOW.md:4,:165 / docs/ai-agents/design-partner.md:355 / docs/ai-agents/executor-preamble.md:11 | 文書のみ（※PO 承認の機械確認なし） |
| 15 | ゲートの除去・弱体化は不可逆扱い＝PO 確認 | docs/STANDARD-WORKFLOW.md:166 | 文書のみ |
| 16 | 設計パートナー: KGI は PO 承認ゲート、recon 後に PO 承認を取る場合あり、最終承認は PO | docs/ai-agents/design-partner.md:72,:106-108,:157 | 文書のみ |
| 17 | 設計担当が PO に相談してよい場合は3つだけ（設計意図とずれ／事業判断／auto-mode classifier が止めた） | docs/ai-agents/design-partner.md:421-424 | 文書のみ |
| 18 | 実装者は迷ったら全停止して設計担当へ。Opus が設計の範囲内で完走させる | docs/ai-agents/design-partner.md:420、docs/ai-agents/executor-checklist.md:31-43 | 文書のみ |
| 19 | 承認待ちを含む作業は独立カードに分離 | docs/ai-agents/design-partner.md:308 | 文書のみ |
| 20 | AGENTS.md（Codex 側）: 通常経路は ChatGPT設計→CC実装→ChatGPT最終ゲート→GO（Opus 委譲）→main。PO Approval の行あり | AGENTS.md:26, :59, :146-, :188 | 文書のみ |
| 21 | ADR-1012（Proposed）: 段階ごとに実装カードと PO の実装承認を取る | docs/adr/ADR-1012-ai-ops-247.md:6 | 文書のみ（Proposed） |
| 22 | PR 作者は shingo-cc（コード変更PR） | CLAUDE.md:51、docs/adr/ADR-136-cc-bot-github-identity.md:20 | 機械（check-process-artifacts.js:38,:805-810）。取得失敗は fail-open（:801） |

FEATURE-INDEX.md に「承認」「GO」「自律」「委任」で当たったのは、ADR-135（:38）・ADR-1012（:45）のみ（実行: `git show origin/main:docs/adr/FEATURE-INDEX.md | grep -n ...`）。docs/adr/README.md で当たった ADR-1003（:184）・ADR-1009（:190）・ADR-1011（:192）は §4 で扱う。docs/specs/README.md は「KGI 承認済」の状態欄が並ぶのみで、規則はない（:11-12 ほか）。

【事実】docs/ai-agents/design-partner.md:127 付近ではなく docs/STANDARD-WORKFLOW.md:127 で、ADR-012／ADR-113 の「Generator が How を自律設計」は SOP が上書きすると明記している。ADR-113 自体（docs/adr/ADR-113-two-mode-dev-flow.md:48-58 terminal モード）は How を Generator が自律設計と書いている（食い違いが残っている）。

### 規則ごとに、変えるのに直す文書
- KGI の PO 承認ゲート → docs/STANDARD-WORKFLOW.md:23,:79、docs/ai-agents/design-partner.md:72,:106、CLAUDE.md:70-72（要約）、AGENTS.md の同記述。STANDARD-WORKFLOW.md は gate が自己保護している危険パス（check-process-artifacts.js:121）なので、変更 PR 自体に GO 記録が要る。
- 不明点は PO に相談 → docs/STANDARD-WORKFLOW.md:115-119。
- 危険 GO の範囲 → docs/adr/ADR-1003-go-delegation-to-opus.md（新 ADR で追補が筋）＋ docs/handoff/go-record-transcription/opus-delegation.md ＋ check-process-artifacts.js（コード）。
- 正本変更は PR＋PO 承認 → 各正本末尾（STANDARD-WORKFLOW.md:165 ほか）。
- 索引: ADR を足す／変えるなら `node scripts/generate-adr-index.js` を実行して docs/adr/README.md を再生成（CLAUDE.md の規則）。

---

## 2. 機械が強制しているもの

### 2-A. CI（main の必須チェック）
【事実】`gh api repos/shingo-ops/salesanchor/rulesets/15777895`（GET）の rules。保存先: リポジトリ外の作業フォルダ。
- deletion、non_fast_forward
- pull_request: required_approving_review_count=0、require_code_owner_review=false、require_last_push_approval=false、allowed_merge_methods=["merge"]
- required_status_checks（strict）15件: pytest(SQLite+PostgreSQL RLS)／テナントスキーマ整合性チェック／マイグレーションSQL実行テスト／models.py に新 Column→deploy.yml 追記必須／ADR-072 tenant schema lint／Lint & Dark Mode Check (ADR-067)／gitleaks／CLAUDE.md line count check／ADR index is up to date／UI governance gate／dangling-route gate／warn-direct-lesson-edit／guard-authoring/evaluation／process-artifacts gate／API contract is up to date
- bypass_actors=null、current_user_can_bypass（shingo-cc）=never

| チェック | 何を止めるか | 根拠 |
|---|---|---|
| process-artifacts gate | PR 本文の `### 標準ワークフロー確認`（対象ADR・recon・設計・触るファイル・削除するファイル）、危険パスの GO記録、ユーザー影響変更の GO記録、PR作者、新規ファイルの main 重複、PR番号≥2600 の触る/削除ファイル宣言照合 | .github/workflows/process-artifacts-gate.yml:44 → scripts/check-process-artifacts.js:640-695, :805-810, :846-910, :916-964 |
| ADR index | ADR を変えたのに README を作り直していない | .github/workflows/adr-index-check.yml（必須） |
| gitleaks | シークレット混入 | 必須チェック名「gitleaks（シークレット漏洩検出）」 |
| migration 系 | 新 Column→deploy.yml 追記、migration の実行テスト、migration の値の書き込み | .github/workflows/migration-guard.yml、scripts/check-migration-value-writes.py:1-6 |
| ADR-072 tenant lint | テナント分離の違反（bare table、reset_tenant_context 欠落） | .github/workflows/lint-tenant-schema.yml:3-9 |
| UI governance / design-token / dangling-route / API contract | UI金型・トークン・リンク切れ・API契約 | 必須チェック名（上記） |
| workflow-lint.yml | workflow-lint.yml 自身の変更を error で止める（PO確認必須と明記） | .github/workflows/workflow-lint.yml:6-9,:37-41。ただし【事実】必須チェック15件に「CI設定整合性チェック」は入っていない |
| auto-merge-guard | 台帳DONE化PR 以外の auto-merge 予約を取り消す | .github/workflows/auto-merge-guard.yml:3,:52-60 |
| pr-base-check | main 向け PR の head が release/* か hotfix/* か | .github/workflows/pr-base-check.yml:20-29 |
| ledger-auto-done-main | main マージ後の台帳PR を自動作成・自動マージ予約（PO 操作なし） | .github/workflows/ledger-auto-done-main.yml:3-4,:151 |
| CODEOWNERS | migrations/、.github/workflows/、scripts/ 等を @shingo-ops に指定 | .github/CODEOWNERS:16-23。【事実】Ruleset の require_code_owner_review=false なので強制していない（docs/adr/ADR-135-release-stowaway-prevention.md:34-46 も同結論） |

### 2-B. ローカルのフック（~/.claude/settings.json の hooks。リポジトリ外・本店 Mac のみ）
| フック | 何を止めるか | 根拠 |
|---|---|---|
| pr-body-guard.sh | `gh pr create/edit --body` の PR 本文を検証し不正なら exit 2 | ~/.claude/scripts/pr-body-guard.sh:3-4,:68-75。内部で scripts/dev/validate-pr-body.sh と同じ検査（scripts/dev/validate-pr-body.sh:31-70）。【事実】:77-83 に `PR_BODY_VALIDATE_SKIP=1` で素通りできる口がある |
| agent-danger-hook.sh | 本番DBへの直接書き込み（psql）、permits への直接アクセス、本店での破壊的 git、danger_ops 語（DROP TABLE／rm -rf／git push --force／DELETE FROM／TRUNCATE／git push origin main 等）を exit 2 | ~/.claude/scripts/agent-danger-hook.sh:88-152, :156-189, :192-346, :351-464。danger_ops 一覧は ~/.claude/agent-tokens.json の danger_ops キー（17語。`clasp push`・`git rebase` 含む） |
| worktree-only-guard.sh／worktree-access-guard.sh | 本店・保護ブランチでの編集／commit、他セッションの作業場所への侵入 | ~/.claude/settings.json の hooks 登録（PreToolUse） |
| gh-scope-guard.sh | 【事実】docs/handoff/design-approval-ticket/（project memory）に「2行目 exit 0 で無効化中」と記録。この回では内容を未読【未確認】 | |
| .claude/hooks/require-status-label.sh ほか | 担当報告の DONE/BLOCKED: ラベル、鮮度確認 | .claude/settings.json:58-71 |
| autoMode.soft_deny（auto mode 分類器） | 【事実】`Bash(gh pr merge *)` を soft_deny（ADR-1003 の流れの外の自動承認を避ける趣旨の文）。`docker compose restart *` も soft_deny | ~/.claude/settings.json の autoMode.soft_deny（3件中 index 1,2）。ADR-1011:29-39 により AI は soft_deny を自分で変えない |

### 2-C. 「PO 承認なしで AI が PR を作る」流れを今止めるもの
1. 【事実】PR 本文 `### 標準ワークフロー確認` 不備（pr-body-guard.sh と gate の両方）。AI が recon.md／design.md を書いて PR に載せれば通る作り。
2. 【事実】frontend/src、backend/app/routers|services|auth|tasks|discord_gateway を触る変更は GO 記録が必須（check-process-artifacts.js:136-143, :937-947）。かつ免除不可（:967,:972）。GO 発行者は PO または Opus 委譲名義（:43-45）。Opus 委譲名義の GO は ADR-1003:25-29 の3条件（必須CI緑・Reviewer APPROVE・PO へ3行報告）。→ PR 作成までは PO 承認不要で進めるが、GO 記録の「GO原文: GO #<PR番号>」は PR 番号確定後でないと書けない（:373-379）。
3. 【事実】docs 以外の変更で、PR 作者が shingo-cc／Hikky-dev 以外だと fail（:805-810）。
4. 【事実】PR 作成そのものを PO 承認で止める機械は見つからなかった（承認チケットは psql 書き込みの kind のみ。docs/handoff/design-approval-ticket/design.md:93-106）。
5. 【事実】マージ段: soft_deny `gh pr merge *` が Opus のマージを止める（10/13 実測は project memory の記載。この回の再測定なし）。

### 2-D. 危険パス判定に使っている実際の一覧（file:line）
- scripts/check-process-artifacts.js:115-124 DANGEROUS_PATTERNS
  - `^migrations/`、`^scripts/`（全体）、`^ops/launchd/`、`^.github/workflows/deploy.yml$`、`^frontend/src/pages-layout.css$`、`^docs/STANDARD-WORKFLOW.md$`、`^.github/workflows/process-artifacts-gate.yml$`、`^.github/PULL_REQUEST_TEMPLATE.md$`
- :49-51 PO_ONLY_EXCEPTION_PATTERNS: `^.github/workflows/workflow-lint.yml$`
- :77 migration 追加行の `DROP (TABLE|COLUMN)`（ADR-1003 例外。diff を取れないときは fail-closed :69,:80）
- :136-143 USER_IMPACT_PATTERNS（GO 記録必須）: `frontend/src/`、`backend/app/routers|services|auth|tasks|discord_gateway/`
- :104-109 CANONICAL_DOCS_PATTERNS（書類のみでも宣言照合）: docs/specs の下の ideal-state.md、同じく kgi.md、docs/ai-agents の下の md（lessons.d 除く）、`CLAUDE.md`、`AGENTS.md`
- :92-101 DOCS_PATTERNS（書類のみは自動スキップ :765-767）
- 外部API変更は別検出（scripts/detect-external-api-change、:829-836。検出失敗は fail 側）

---

## 3. 方針案 A（止める変更9項目）× 機械検出

「検出」は「その変更が PR に入ったとき、機械が PO 本人の判断が要る状態に止められるか」ではなく、「機械が検出して何らかの GO／失敗に倒せるか」で ○／△／× を付けた。【事実】どの危険パスも GO 記録が Opus 委譲名義で通る（PO 本人必須は :49-51, :77 のみ）。

| A | 項目 | 検出 | 根拠 |
|---|---|---|---|
| 1 | migrations/ を含む変更 | ○（検出）／PO本人必須にできるのは DROP のみ | check-process-artifacts.js:116, :77。GO は委譲可（ADR-1003:35 の例外外は Opus 名義で通る） |
| 2 | deploy.yml、本番 scripts | ○（deploy.yml :119、scripts/ 全体 :117） | 「本番用」と「開発ツール」を区別しない（docs/ai-agents/design-partner.md 内の executor-checklist.md:334 付近の注記）。GO は委譲可 |
| 3 | DROP／大量DELETE／本番データ手直し | △ DROP は○（:77）。大量DELETE は×（ADR-1003:45「機械検証できない」）。本番データ手直しはローカルフックのみ（agent-danger-hook.sh:88-152, danger_ops 'DELETE FROM'／'TRUNCATE'）。CI での検出は migration の値の書き込み検査（scripts/check-migration-value-writes.py:1-6）のみ | 同左 |
| 4 | 秘密の値（secrets・鍵・token の変更） | △ コードへの混入は gitleaks（必須）。GitHub／サーバー側の secrets 変更は×（ADR-1003:45） | 同左 |
| 5 | auth/・*token*・*password*・payment*、テナントの分け方（ADR-072） | △ `backend/app/auth/` は USER_IMPACT で GO 要（:140）だが委譲可。`*token*`／`*password*`／`payment*` のファイル名判定は gate に無し（【事実】:1-1000 を grep: token は :14 の GH_TOKEN 説明のみ）。ADR-072 は lint-tenant-schema（必須）が検出 | 同左。global CLAUDE.md の security-reviewer 起動条件は文書のみ |
| 6 | 安全装置そのもの（.github/workflows/、Branch Protection・必須チェック、フック・許可設定） | △ workflow-lint.yml（PO本人必須 :50）と deploy.yml・gate yml（:119,:122）と PULL_REQUEST_TEMPLATE（:123）は○。他の .github/workflows/*.yml は real-code 扱い（:132）で GO 不要＝×。Branch Protection／Ruleset の変更は PR に現れない＝×（shingo-cc は repo 権限が write で admin なし【事実】GET collaborators）。フック・許可設定は ~/.claude（リポジトリ外）で、検出はローカルの Self-Modification 分類器（docs/adr/ADR-1011-permission-self-maintenance.md:23-27,:39） | 同左 |
| 7 | 外部画面（Cloudflare・Firebase・Meta） | × | ADR-1003:45。PR の差分に現れない |
| 8 | 新しい ADR、新機能、KGI | × ADR は docs/ 配下＝書類で自動スキップ（:92-93,:765-767）。KGI は kgi.md が正本宣言照合のみ（:106）で PO 承認の確認なし。「新機能かどうか」はパスで判定不能 | 同左 |
| 9 | Legacy（jarvis-claude.uk）削除 | × | 専用の guard なし（`git grep -l jarvis-claude origin/main -- .github scripts` は deploy.yml・scripts/nmap_scan.sh 等が当たるのみ。削除を検出する処理は未確認） |

### A に無いが機械が GO を求めている領域
- B に書かれた「画面の不具合修正・API の不具合修正」は USER_IMPACT（:136-143）で GO 記録が必須。方針案の「承認なしで PR まで」と矛盾はしないが、GO 記録（Opus 委譲名義）と recon/design/対象ADR（免除不可 :967）が機械で必須になる。
- 方針案 B の「テストの追加」は backend/tests/ が REAL_CODE（:129）で免除宣言（`- [x] 免除`）が使えるが、記録必須・governance 監査（docs/STANDARD-WORKFLOW.md:134）。「文書の更新」は書類のみなら自動スキップ（:765-767）。ただし CLAUDE.md／AGENTS.md／docs/ai-agents/ は正本扱い（:104-109）、STANDARD-WORKFLOW.md は危険扱い（:121）。

---

## 4. 既にある近い仕組み

### ADR-1011（設計承認チケット＋許可の自律保守）
- 実体は2つ。(a) 設計承認チケット（docs/handoff/design-approval-ticket/design.md。frontmatter は `status: draft（PO 承認待ち・実装未着手）` のまま :3）と、(b) ADR-1011（許可の自律保守。Accepted、docs/adr/ADR-1011-permission-self-maintenance.md:5-6）。
- 範囲: (b) は AI が週1回、~/.claude/settings.json の autoMode.allow の `SM-` で始まる文だけを足し外しできる（:15-19）。条件は PR で報告書・台帳をマージ、Reviewer APPROVE、バックアップと試験（:17-19）。範囲外は soft_deny／hard_deny／hooks／~/.claude/scripts／本番・DROP・force push・ブランチ保護・外部 GUI（:29-37）。解除: PO の「許可保守停止」（:43）。
- 期限: 期限指定なし（PO が止めるまで有効）。(a) チケット自体の期限は 72h 既定・上限7日（design.md:90）だが、kind は psql-write の1種類のみ（:93-106）、マージとデプロイは対象外（:106）。
- 状態: project memory（design_approval_ticket）では S1・S2・S4 完了、S3（PO 立会い）と Desktop 登録が残り。段3・段4（チケット本体）は未着手と記載。【未確認】この回では本番の実装状況（設計承認チケットのファイルがホームにあるかなど）を確認していない。
- 重なる所: 「設計が固まったら Opus が止まらず完走」（design.md:14）は方針案と同じ向き。
- 食い違う所: (1) チケットは権限不足で止まらないための仕組みで、「KGI 承認・実装承認をなくす」ものではない。(2) A の6「フック・許可設定」は ADR-1011:29-39 で AI が触れない範囲と一致（矛盾なし）。(3) ADR-1011 は soft_deny の `gh pr merge` を変えない（design.md:106）。

### 「自律開発の型：操作一覧を PO が一括承認」
- 実体は文書ではなく project memory（feedback_autonomy_package.md、PO 合意 2026-09-30）。リポジトリの文書では docs/handoff/design-approval-ticket/design.md（上記）がこれの実装計画に相当。docs/ai-agents/design-partner.md:195（委任文の定型）、:407-438（§10 役割と進め方）に一部が文書化されている。
- 範囲: 設計時に「操作一覧」を具体的に書いて PO が貼り返し許可する。恒常の許可を autoMode.allow に書く。フックは作業場所内だけ緩める。本番・秘密・main への操作は止めたまま。
- 期限: 期限なし（PO 合意の方針）。
- 重なる所: 設計後は Opus が完走。食い違う所: これは「設計時に PO が承認する」前提で、方針案の「1件ごとの承認をなくす」とは逆に PO 承認を1回入れる型。

### ADR-1003（GO 委任）
- Accepted、2026-09-29。委譲は常時（期限なし）。解除は PO の「委譲停止」（docs/adr/ADR-1003-go-delegation-to-opus.md:47-49）。状態「有効」は docs/handoff/go-record-transcription/opus-delegation.md:9。
- 範囲: 危険変更・ユーザー影響変更・外部API変更のマージ前 GO（:14）。条件3つ（:25-29）。PO 本人必須7例外（:31-41）。
- 重なる所: GO の PO 待ちをなくしている点は方針案と同じ向き。
- 食い違う所: (1) 方針案 A の 1・2（migrations／deploy.yml／scripts）は ADR-1003 では Opus 名義の GO で通せる。方針案はそれを PO の判断に戻す形になる。(2) ADR-1003 は条件3（PO へ3行報告）を課すが、承認ではない。(3) 方針案 A の 4・6・7（secrets／Ruleset／外部GUI）は ADR-1003 の例外と一致。(4) 方針案 A の 5（auth／payment）と 8（新機能・KGI）は ADR-1003 の例外に無い（Opus が GO を出せる範囲にある）。

---

## 5. マージの実行者

【事実】GET のみ。保存先: リポジトリ外の作業フォルダ（Ruleset の GET 結果）。
- `gh api repos/shingo-ops/salesanchor/branches/main/protection` は HTTP 404（`_bp.err`）。従来型の Branch Protection は無く、Ruleset 方式。
- Ruleset 15777895「main branch protection」enforcement=active、対象 ~DEFAULT_BRANCH。
  - 必須レビュー数 0、コードオーナーレビュー不要、最後の push 承認不要、スレッド解決不要
  - 許可される merge 方式は "merge" のみ（`gh pr merge --merge` と一致）
  - 必須ステータスチェック15件、strict=true（base が古いと緑でもマージ不可。update-branch が要る）
  - bypass_actors=null。shingo-cc の current_user_can_bypass=never
- Ruleset 16619490（develop）: deletion と required_status_checks のみ。
- repo 設定: allow_auto_merge=true、allow_merge_commit=true、allow_squash_merge=true、allow_rebase_merge=true、delete_branch_on_merge=false、private=false。
- 権限: `gh api repos/.../collaborators` → shingo-cc=write、shingo-ops=admin。
- 解釈（【事実】から導けること）: 承認レビュー0件なので、必須チェック15件が緑で base が最新なら、write 以上の権限を持つ人は Web UI の「Merge pull request」でマージできる設定。PO（shingo-ops）は admin で、bypass 設定は無いので「チェックが赤でも通せる」経路は Ruleset 上は無い。

【未確認】
- GitHub Mobile アプリで PR をマージできるか。公式ドキュメント（docs.github.com/en/get-started/using-github/github-mobile）を WebFetch したが、マージの記載は無く（"Read, review, and collaborate on issues and pull requests"、"Edit files in pull requests" のみ）、可否は確認できなかった。
- スマホブラウザで GitHub Web の「Merge pull request」を使えるか、および merge 方式が merge のみの Ruleset 下で UI にどう出るか（実測していない）。
- Opus の `gh pr merge` が soft_deny により拒否された件の再測定（project memory の 10/13 記録のみ。この回では実行していない）。

---

## 矛盾表

| 規則 | 場所 | 方針案との関係 | 直す文書 |
|---|---|---|---|
| ①KGI は PO 承認が必須ゲート | docs/STANDARD-WORKFLOW.md:23,:79 / CLAUDE.md:70-72 / docs/ai-agents/design-partner.md:72,:106 / AGENTS.md | 矛盾（B の変更も KGI→PO承認を求めている）。ただし機械は見ていない | STANDARD-WORKFLOW.md（危険パス＝GO 要）、design-partner.md、CLAUDE.md、AGENTS.md。新 ADR で線引き（A/B）を起案 |
| 実装前の PO 明示承認（「1件ごとの承認」の実体） | CLAUDE.md:70-80、STANDARD-WORKFLOW.md:24,:34-39,:115-119 | 要改定（B は AI が recon／design まで自分で残す案。記録義務は残るので両立） | STANDARD-WORKFLOW.md に「B 区分は KGI／設計承認を PO 事後確認に」等の例外節 |
| 新機能は仕様書必須（PO 作成・承認） | STANDARD-WORKFLOW.md:30-39 | 両立（方針案 A の 8「新機能は止める」と一致） | 直さない |
| 危険変更は PO の GO、ADR-1003 で Opus へ委譲 | CLAUDE.md:56-57、ADR-1003:14-45 | 要改定（方針案 A の 1・2・5 は「PO の判断を待つ」で、ADR-1003 より厳しい） | ADR-1003 追補（または新 ADR）＋ opus-delegation.md ＋ check-process-artifacts.js。方針案側を ADR-1003 に合わせる選択もある |
| ADR-1003 の PO 本人必須7例外 | ADR-1003:31-41 | 両立（方針案 A の 3・4・6・7 と一致） | 直さない |
| ユーザー影響変更は GO 記録必須 | STANDARD-WORKFLOW.md:92、check-process-artifacts.js:136-143,:937-947 | 両立（Opus 委譲の GO で通る。PO の手間は増えない） | 直さない。方針案 B の PR 本文に GO 記録が要る点だけ運用で追記 |
| 画面・API 修正は免除不可、recon/design/対象ADR 必須 | check-process-artifacts.js:967,:972 | 両立（方針案「recon/design は AI が残す」と一致） | 直さない |
| 危険操作は PO 自筆 GO、設計パートナー／実装役は代筆しない | design-partner.md:115-116 | 矛盾（design-partner.md:215 と ADR-1003 はそれを緩めている。文書内の食い違い） | design-partner.md:116 を ADR-1003 に合わせる |
| 設計担当が PO に相談してよいのは3場合だけ | design-partner.md:421-424 | 両立（方針案 C「A に当たったら止まる」と近い） | 直さない（A の定義を書き込むなら追記） |
| リリース相当の大きな変更は Draft→PO が GO まで un-draft／マージ禁止 | CLAUDE.md:53 | 要改定（B の「PO はマージを押すだけ」とは Draft の扱いが衝突しうる。「リリース相当」の定義が文書に無い【未確認】） | CLAUDE.md:53 |
| `gh pr merge *` を soft_deny | ~/.claude/settings.json autoMode.soft_deny | 矛盾（Opus がマージする前提と衝突。「PO がマージを押す」案とは両立） | 触らない（ADR-1011:29-39 で AI は変更不可。PO の `!` 操作） |
| PO がマージ（承認レビュー0・merge 方式のみ・bypass なし） | Ruleset 15777895 | 両立（write 以上なら UI でマージ可）。スマホ可否は未確認 | 直さない（変更は PO 確認必須の不可逆操作） |
| 正本変更は PR＋PO 承認のみ | STANDARD-WORKFLOW.md:4,:165 他 | 両立（ルール文書を変える段は PO 承認が要る、方針案も「PO の OK 後に ADR 起案→PR」） | 直さない |
| ADR-1012（段階ごとに PO の実装承認） | ADR-1012:6 | 矛盾（Proposed。B 区分なら承認をなくす対象になりうるが、migration を含むため A に当たる） | ADR-1012（Proposed のうちに調整） |
| ADR-113 terminal モードは How を Generator が自律設計 | ADR-113:48-58 | 両立だが STANDARD-WORKFLOW.md:127 が上書き済み（文書内の食い違い） | ADR-113（ステータス更新は別件） |
| A の 8「新しい ADR」は止める | 方針案 | 要確認（ADR 変更は docs/ 配下で gate が自動スキップ :765。機械は止めない＝運用規則のみ） | 新 ADR か CLAUDE.md に「ADR は PO 承認」と書くなら文書規則 |

---

## 【未確認】一覧
1. GitHub Mobile アプリでの PR マージ可否（公式ドキュメントに記載なし）。
2. スマホブラウザの Web UI でのマージ可否と、merge 方式のみ許可の Ruleset 下での表示。
3. Opus の `gh pr merge` が拒否される条件の再測定（10/13 の記録は project memory）。
4. gh-scope-guard.sh の現在の有効／無効（project memory に「無効化中」とあるのみ。この回は未読）。
5. 設計承認チケット 段3・段4（チケット本体）の実装状況（design.md の frontmatter は draft のまま）。
6. 「リリース相当の大きな変更」の定義（CLAUDE.md:53 に基準なし）。
7. Legacy 削除を止める機械（専用 guard は見つからなかったが、全 workflow／hook を網羅確認はしていない）。
8. 方針案 A の 5 の `*token*`／`*password*`／`payment*` を検出する CI があるか（check-process-artifacts.js には無い。他のスクリプトは網羅確認していない）。
9. PR 作成そのものを PO 承認で止めるローカルフックが他にあるか（~/.claude/scripts の全文は読んでいない。pr-body-guard.sh と agent-danger-hook.sh の主要部分のみ）。
