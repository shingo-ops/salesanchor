# recon-draft: 部署制の前提となる「全体の地図と関所」（KGI K1〜K4）

- 基準: `git rev-parse origin/main` = `2ac19f708aae252098631da5274bd1b28162f9e0`（`git fetch origin` 実行後に取得）
- 調査は読み取りのみ。すべて origin/main 基準（`git show origin/main:<path>` / `git grep ... origin/main` / `git ls-tree`）。ローカルファイルは未使用。
- 注記: 本タスクは recon-draft.md 以外の書き込みを禁じられていたが、調査の中間ファイル（`sh.sh`・集計tsv等）をスクラッチパッド（同ディレクトリ）に作った。リポジトリ内には何も書いていない。
- 注記: この Mac の `grep` は ugrep 7.8.4（GNU grep ではない）。hex 件数の再現（R4）は CI（ubuntu の GNU grep）と差が出うる。

---

## R0 既存ADR・仕様の検索

### R0-1 ADR一覧（本テーマに効くもの）

| ADR | 題名 | 状態 | 本テーマに効く決定（1行） | 根拠 |
|---|---|---|---|---|
| ADR-027 | UI の i18n 対応（日本語/英語） | Accepted | 全UI文字列を多言語化。CLAUDE.md は `t("key")` 経由・ja/en 同一キー必須を強制規約にしている | `docs/adr/ADR-027-ui-internationalization.md:5`（状態）, `:11-19`（What）, `CLAUDE.md`「i18n 強制（ADR-027）」節 |
| ADR-067 | デザイントークン強制 | Accepted | CSS変数を唯一の真実(SSOT)とし、逸脱を CI と ESLint で機械ブロック | `docs/adr/ADR-067-design-token-enforcement.md:3`（状態）, `:21`（決定） |
| ADR-072 | tenant schema 修飾の戦略統一 | Proposed (v2) | schema prefix と reset_tenant_context のハイブリッド。CI linter で両パターンを検証（必須チェック「ADR-072 tenant schema lint」の根拠） | `docs/adr/ADR-072-tenant-schema-prefix-enforcement.md:4`（状態）, `:79`, `:101` |
| ADR-114 | worktree ライフサイクルの完全自動化 | Proposed（改訂） | 本テーマ（地図・関所）に直接効く決定は無し。「真実は1つ（active-work のステータス）」という SSOT 原則の適用例のみ | `docs/adr/ADR-114-worktree-auto-cleanup.md:5`, `:23` |
| ADR-135 | リリース相乗り防止（develop=出荷可能） | Accepted | process-artifacts gate を main 必須に登録した、と記載。**実機の ruleset とは食い違う（R1参照）** | `docs/adr/ADR-135-release-stowaway-prevention.md:3`, `:48-51` |
| ADR-136（2本が同番号） | (a) CC ボット GitHub Identity 分離 / (b) 取引額集計 SSOT v_company_stats | (a) Accepted / (b) Completed | (a) PR作者チェックを process-artifacts gate に追加、GO は PO 単独（承認フロー v2）。(b) 取引額の正本を v_company_stats に一本化 | `docs/adr/ADR-136-cc-bot-github-identity.md:5,:20`, `docs/adr/ADR-136-company-stats-ssot.md:3,:13` |
| ADR-144 | UI共通部品の遵守ガバナンス | Accepted | pages/ の生 select/input/自作タブの新規追加を CI で赤にする（既存は赤化しない＝ラチェット）。例外は `ui-allow: 理由 (#番号)` | `docs/adr/ADR-144-ui-component-governance.md:3`, `:29-48` |
| ADR-1003 | GO 発行を Opus へ常時委譲 | Accepted | process-artifacts gate の `AUTHORIZED_GO_ISSUERS` に委譲名義を追加。DROP 系 migration 等は PO 本人の GO が必須 | `docs/adr/ADR-1003-go-delegation-to-opus.md:5,:14-17` |
| ADR-121 | SOP process-artifacts gate | 採択（提案日 2026-06-09） | process-artifacts gate の正本 ADR（FEATURE-INDEX が指す） | `docs/adr/ADR-121-sop-process-artifacts-gate.md:4`, `docs/adr/FEATURE-INDEX.md:40` |
| ADR-155 | 商品マスタ SSOT（CSV＋アプリ）。migration-guard チェック7/8 のコメントが参照 | Accepted | 共用マスタテーブルへの INSERT/UPDATE/SELECT を migration で禁止 | `docs/adr/ADR-155-product-master-ssot-csv-app.md:5`, `.github/workflows/migration-guard.yml:394-407` |

- 【事実】ADR番号 ADR-136 が2ファイル存在する（`docs/adr/ADR-136-cc-bot-github-identity.md` と `docs/adr/ADR-136-company-stats-ssot.md`）。番号の重複は、ADR 参照を機械で解決する場合（process-artifacts gate の `adrFileMatchesReference`）に曖昧さの原因になりうる。【未確認】gate が重複でどう動くか。
- 【事実】ADR-072 と ADR-114 の状態は Proposed のまま。ADR-072 は必須チェックとして実際に稼働している（R1）。
- 【事実】FEATURE-INDEX のキーワード検索（SSOT/token/governance/金型/i18n/E2E/Playwright/OpenAPI/型生成/ruleset/required/必須チェック/process-artifacts）で該当した行は `docs/adr/FEATURE-INDEX.md:14,35,36,37,40` のみ。**OpenAPI・型生成・E2E・Playwright・配線台帳に関する ADR は FEATURE-INDEX に無い**（`git grep -il -E 'OpenAPI|型生成' origin/main -- docs/adr` も ADR 本文はヒットせず、ヒットしたのは FEATURE-INDEX.md / README.md の別語のみ）。

### R0-2 docs/specs の状態とKGI

| 文書 | 状態行 | KGI（要約） | 根拠 |
|---|---|---|---|
| `docs/specs/db-ssot/` | あるべき姿 PO承認。KGI PO承認 2026-07-09。子5本は「design済/計画済」（実装は STEP1〜3 の計画） | K1 重複コピー箇所数=0 / K2 正本の所在が設計書に明記=全数 / K3 正本以外は背番号参照=全数 / K4 分類値は台帳から選ぶ=全数 / K5 持ち主(リード)に必ず辿れる=全数。KPI 達成◯/5 | `docs/specs/db-ssot/README.md:6-7,:18-22`, `docs/specs/db-ssot/kgi.md:1,:8-14` |
| `docs/specs/design-system/` | 状態: あるべき姿・KGI・理想設計 PO承認済（2026-07-04）。関所実装は「後続予定（未作成）」と明記 | ①共通部品の定義が各1ヵ所 ②色・文字・余白・角丸の生値がページ側に0 ③1ヵ所変更が全ページに波及 ④カタログに全部品 ⑤ベタ書き再発を止める関所が在る ⑥索引・親子リンク。KPI 現在値は「測定前 0/6」の記載 | `docs/specs/design-system/README.md:9,:24-25`, `docs/specs/design-system/kgi.md:1,:11-16,:18` |
| `docs/specs/design-tokens-ssot/` | ステータス: あるべき姿・KGI 承認済み（PO・2026-07-09） | ①未索引の種別0 ②未記載パーツ0 ③追加前に重複を機械確認できる ④重複ゼロ ⑤索引が正本にPR反映（open台帳方式・全5項目） | `docs/specs/design-tokens-ssot/README.md:7`, `docs/specs/design-tokens-ssot/kgi.md:8-16` |
| `docs/specs/component-standard.md` | 確定日 2026-06-07（状態行は無し、design-system の子と明記） | ボタン角丸6px・カード角丸8px 等の確定値（KGIは持たない） | `docs/specs/component-standard.md:4,:6,:14-24` |
| `docs/specs/process-hardening/` | ステータス: あるべき姿確定（PO自筆 2026-07-19）。KGI は 2026-07-20 PO承認 | ②-a〜c（未対応ミス警告・ペアテスト完備・欠落版が赤で止まる実測）＋柱1〜3。効果は「未確立（弱）」と自己申告 | `docs/specs/process-hardening/README.md:7,:9`, `docs/specs/process-hardening/kgi.md:9-13,:17-21` |

### R0-3 本テーマと範囲が重なる箇所

- 【事実】K1〜K4（地図と関所）は既存の3系統と重なる。
  - db-ssot: 「正本の所在を設計書に明記（K2）」「背番号参照（K3）」は DB 側の正本台帳。本テーマの「全体の地図（画面→API→テーブル）」と同じ種類の台帳を別軸で要求している。
  - design-system / design-tokens-ssot: 「関所（機械チェック）」「索引（台帳）」を要求。design-system は KGI⑤ の関所を「後続予定（未作成）」と明記（`docs/specs/design-system/README.md:24-25`）が、実際には ADR-144 の `UI governance gate` が main 必須になっている（R1）。文書側と実機が食い違っている可能性があるが、README 側の更新有無は【未確認】。
  - process-hardening: 「関所の自動再採点」等、関所そのものの信頼性を扱う。
- 【事実】`docs/specs/design-system/kgi.md:25` は hex 本物件数を 36 件としている（recon cbaee61）。R4 の再現（index.css を除いて 56 件）と一致しない。理由は【未確認】。
- 【事実】`docs/specs/design-tokens-ssot/README.md:15` は design-system（便0.5）を「本テーマが優先する」と位置づけ、両者の優先順位が文書上で定義されている。

### R0 使用コマンド
```
git fetch origin; git rev-parse origin/main
git show origin/main:docs/adr/FEATURE-INDEX.md | grep -niE '...キーワード...'
git ls-tree -r --name-only origin/main -- docs/adr | grep -E 'ADR-(027|067|072|114|135|136|144|1003)'
git show origin/main:<各ADR/specs> | awk 'NR>=s&&NR<=e'   （scratchpad の sh.sh で行番号付与）
git grep -il -E 'db-ssot|design token|デザイントークン|UI governance|金型|process-artifacts|OpenAPI|型生成' origin/main -- docs/adr
git ls-tree -r --name-only origin/main -- docs/specs/{db-ssot,design-system,design-tokens-ssot,component-standard.md,process-hardening}
```

---

## R1 必須チェック（K1）

### R1-1 main の必須チェック13本（`gh api repos/shingo-ops/salesanchor/rulesets/15777895` の出力そのまま）

ruleset 名 `main branch protection` / enforcement `active` / 対象 `~DEFAULT_BRANCH` / strict=true / PR経由・merge のみ許可・承認数0・コードオーナーレビュー無効・deletion と non_fast_forward を禁止。

```
pytest (SQLite + PostgreSQL RLS)
テナントスキーマ整合性チェック
マイグレーションSQL 実行テスト（実DB）
models.py に新 Column → deploy.yml にマイグレーション追記必須
ADR-072 tenant schema lint (strict mode)
Lint & Dark Mode Check (ADR-067)
gitleaks（シークレット漏洩検出）
CLAUDE.md line count check
ADR index is up to date
UI governance gate                 (integration_id 15368 = GitHub Actions)
dangling-route gate                (integration_id 15368)
warn-direct-lesson-edit
guard-authoring/evaluation         (integration_id 15368)
```

| # | 必須チェック名 | workflow:job（ファイル:行） | 何を検査しているか（1行） |
|---|---|---|---|
| 1 | pytest (SQLite + PostgreSQL RLS) | `.github/workflows/test.yml:251`（集約ジョブ。`pytest-run` と `lint-backend` の結果を `:258-267` で集約、backend 未変更なら skipped を成功扱い） | backend 全 pytest（`:241` `pytest -q`）＋ ruff（`:86`）＋ bandit（`:90`）。mypy は `:111` で `|| true`（落ちても通る） |
| 2 | テナントスキーマ整合性チェック | `.github/workflows/schema-check.yml:223`（集約）／実体 `:48` | `scripts/check_schema_catchup_sync.py`（`:93`）、`setup_tenant.py`（`:197`）、`sync_tenant_schema.py --dry-run`（`:217`） |
| 3 | マイグレーションSQL 実行テスト（実DB） | `.github/workflows/migration-test.yml:1688`（集約。`:1687` コメントで必須名と一致させる旨） | migration SQL を実DBで実行。登録存在チェック（`:64`, `:83`）含む |
| 4 | models.py に新 Column → deploy.yml にマイグレーション追記必須 | `.github/workflows/migration-guard.yml:9`（job `check` 1本に チェック1〜9 が同居） | 新Column→deploy.yml追記、新 migration の登録、`{schema}` リテラル禁止、FK参照先、timestamp重複、DROP は ADR 承認、共用マスタへのデータ操作/参照禁止（ADR-155）、`supplier_channels.supplier_id` 破壊的変更禁止（SSOT ガード `:588-652`） |
| 5 | ADR-072 tenant schema lint (strict mode) | `.github/workflows/lint-tenant-schema.yml:38` | `python3 scripts/lint_tenant_schema.py --mode strict backend/app/routers/`（`:69`） |
| 6 | Lint & Dark Mode Check (ADR-067) | `.github/workflows/e2e.yml:85`（集約 `lint`）／実体 `:56-79` `lint-run` が `npm run check:all` | frontend 変更時のみ `check:all`（約24本のスクリプトと eslint を並列実行）。未変更なら skipped で成功 |
| 7 | gitleaks（シークレット漏洩検出） | `.github/workflows/secret-scan.yml:16` | `gitleaks/gitleaks-action@v2`（`:24`）、設定 `.gitleaks.toml` |
| 8 | CLAUDE.md line count check | `.github/workflows/check-claude-size.yml:12` | `node scripts/check-claude-size.js`（`:40`）。CLAUDE.md 行数上限 |
| 9 | ADR index is up to date | `.github/workflows/adr-index-check.yml:9` | `node scripts/generate-adr-index.js --check`（`:31`）。ADR 未変更ならスキップ（`:35`） |
| 10 | UI governance gate | `.github/workflows/ui-governance-gate.yml:17` | `scripts/check-ui-governance.js`（`:39`）＋ そのテスト（`:33`）。pages/ の生UI部品の新規増加を赤（R4） |
| 11 | dangling-route gate | `.github/workflows/dangling-route-gate.yml:13` | PR で削除された backend ルートが frontend から参照されていれば赤（`scripts/check-dangling-routes.js:5-11`）。ワークフロー先頭コメント `:5` は「必須ではない」と書いたままだが、ruleset では必須（コメントと実機が不一致） |
| 12 | warn-direct-lesson-edit | `.github/workflows/lessons-guard.yml:10` | `scripts/check-lessons-section.sh`（`:20`）。`docs/ai-agents/design-partner.md` の §6 教訓への直書き追加を検知しブロック |
| 13 | guard-authoring/evaluation | 結果 context は `.github/workflows/guard-authoring-gate.yml` の job `evaluate`（`:43-45`）が `scripts/run-guard-evaluation.js`（`:66`）で対象SHAへ publish。unit job は `:30-41` | 関所（ガード）の新設・変更に対し、変更blob・読書blob・評価・検証記録を照合（`docs/handoff/design-partner-card-ops/guard-authoring-design.md:29`）。導入記録 `docs/ai-agents/evidence-registry.md:2118` |

- 【事実】main の必須13本は、**画面・API・DBの配線を検査するものは `dangling-route gate`（削除ルートの参照切れ）のみ**。frontend↔backend の型一致・画面一覧・API一覧を検査するチェックは必須13本に無い。
- 【事実】本テーマの K1（必須チェック）に関わる、pr 経由ではない経路: ruleset の `bypass_actors`（admin=shingo-ops）は ADR-135 で維持と明記（`docs/adr/ADR-135-release-stowaway-prevention.md:65`）。ruleset JSON 本体では今回の取得項目に bypass を含めていない【未確認】。

### R1-2 process-artifacts gate

- 【事実】workflow: `.github/workflows/process-artifacts-gate.yml:19`（job 名 `process-artifacts gate`）。先頭コメントに「※ 必須ではない（non-mandatory）」「develop→main リリースPRのみスクリプト内でスキップ」（`:5-6`）。トリガーは `pull_request` の `opened, synchronize, reopened, edited`、対象ブランチ `main, develop`（`:9-11`）。実行は `node scripts/check-process-artifacts.js`（`:44`）と `bash scripts/check-doc-heading-duplicates.sh`（`:47`）。
- 【事実】**ruleset 比較**（`gh api` の実出力）:
  - main（15777895）の必須13本に `process-artifacts gate` は**無い**。
  - develop（16619490 `Protect develop branch`）の必須13本に `process-artifacts gate` は**ある**。develop の13本は `pytest…`, `テナントスキーマ整合性チェック`, `マイグレーションSQL 実行テスト（実DB）`, `models.py に新 Column…`, `ADR-072…`, `Lint & Dark Mode Check (ADR-067)`, **`Playwright E2E (chromium)`**, `gitleaks…`, `CLAUDE.md line count check`, `ADR index is up to date`, **`process-artifacts gate`**, `dangling-route gate`, `UI governance gate`。
  - develop には `warn-direct-lesson-edit` と `guard-authoring/evaluation` が無く、main には `Playwright E2E (chromium)` と `process-artifacts gate` が無い。
- 【事実】`docs/adr/ADR-135-release-stowaway-prevention.md:48-51` は「Ruleset 15777895 の required_status_checks に `process-artifacts gate` を登録（10件→11件）」と**実施済み**と書いているが、2026-10-02 時点の main ruleset にはその名前が無い。ADR と実機が食い違う（CLAUDE.md の最上位原則は「ADR を優先して実装を寄せる」）。いつ外れたかは【未確認】（ruleset の変更履歴は今回取得していない）。
- 【事実】スクリプトが develop→main リリースPRをスキップする（`scripts/check-process-artifacts.js:733-739`）ため、仮に main 必須にしても develop→main PR では素通りになる。現在の運用は release/* → main の PR（CLAUDE.md「ブランチ運用ルール」）で、スキップ条件は `baseRef === 'main' && headRef === 'develop'` のみ（`scripts/check-process-artifacts.js:737`）。release/* → main は検査対象。
- 検査の中身（`scripts/check-process-artifacts.js`、全999行）:
  - 分類: DOCS_PATTERNS（`:92-101`）、正本ファイル（`:104-109`: ideal-state.md / kgi.md / docs/ai-agents / CLAUDE.md / AGENTS.md）、DANGEROUS_PATTERNS（`:115-123`: migrations/, scripts/ 全般, deploy.yml, pages-layout.css, STANDARD-WORKFLOW.md, 関所自身, PRテンプレ）、REAL_CODE_PATTERNS（`:125-133`）。
  - 書類のみの変更は自動スキップ（`:765-766`）。ただし正本を含む場合は宣言照合へ進む（`:769`）。変更ファイル無しもスキップ（`:758-759`）。
  - PR作者チェック: `AUTHORIZED_AUTHORS = ['shingo-cc', 'Hikky-dev']`（`:38`）。コード変更を含む PR の作者が外れたら赤（`:800-808`）。
  - 宣言照合（`runFullCheck` `:635-`）: PR本文に「### 標準ワークフロー確認」（`:639`）、対象ADR が docs/adr/ に実在（`:649-662`）、recon パス実在＋`path:N` 引用が1件以上（`:668-679`）、引用先ファイル実在（`:459-466`）、設計doc 実在（`:686-694`）。
  - 設計doc 検査（`validateDesignDoc` `:471-`）: 「| 基準 | 検証方法 |」表で検証方法が空でない（`:477-488`）、recon.md への相互参照（`:494`）、ADR 参照（`:500`）、「外部・過去事例の参照と我々への応用」欄が空でない（`:507-515`）。
  - 「## 維持の仕組み」欄と「守り手:」にファイルパスが実在（`validateMaintenanceSection` `:525-553`）。
  - 危険変更の GO 記録（`validateGORecord` `:345-382`）: 発行者（PO＋ADR-1003 委譲名義、`:43-45`）・日時・「GO #<PR番号>」原文（番号がこのPRと一致）・バックアップ確認。DROP 系 migration と workflow-lint.yml 変更は PO 本人の GO 必須（`:361-362`）。
  - 削除照合・新規ファイルの宣言照合（`:867-910`）は PR番号 >= 2600 のみ（`MAINTENANCE_GRACE_PR = 2600` `:89`）。
- 【事実】ビルド時に process-artifacts を「通らなかった」場合の失敗は PR本文（宣言）依存のため、PR本文を編集した再採点（`edited` トリガー）が効く設計だが、再採点の取り違えは process-hardening 側で別問題として扱われている（`docs/specs/process-hardening/README.md:15`）。

### R1-3 E2E の停止

- 【事実】`.github/workflows/e2e.yml:105`: `    if: false # 一時停止 2026-06-01 — CI ボトルネック解消まで停止（再開時はこの行を削除）`（job `playwright`、`:103-104` で job 名 `Playwright E2E (chromium)`）。
- 【事実】`git log origin/main -S 'if: false' --format='%h %ci %s' -- .github/workflows/e2e.yml` の結果（全文）:
  ```
  037dde856 2026-06-01 23:06:52 +0900 chore(ci): Playwright E2E を一時停止（CIボトルネック解消まで）
  ```
- 【事実】コミット 037dde856 のメッセージ全文: 「CI の playwright ジョブが毎 PR 約 91 秒かかりボトルネックになっているため if: false で一時停止。lint ジョブは引き続き稼働。再開時は if: false の行を削除するだけでよい。」変更は e2e.yml に 1 行追加のみ。作者 shingo-ops。
- 【事実】関連 PR は #1357（base=develop, merged 2026-06-01T14:08:34Z）。本文: 「直近5回の計測で `Run Playwright E2E` ステップが毎回 91〜92秒かかっており…セットアップ込みでジョブ全体は約 2 分 10 秒」。Test plan に「playwright ジョブが skipped 表示になることを確認」。（`gh api repos/shingo-ops/salesanchor/commits/037dde856/pulls`, `gh pr view 1357 --json body`）
- 【事実】停止から 2026-10-02 まで約 4 か月、`if: false` の行は残っている（`git grep -n 'if: false' origin/main -- .github/workflows/e2e.yml` が `:105` のみ）。
- 【事実】develop ruleset は `Playwright E2E (chromium)` を必須としているが、ジョブは `if: false` で skipped になる。main ruleset にはこのチェックは含まれない。skipped が必須扱いでどう評価されるかの実機挙動は【未確認】（本調査では PR のチェック表示を見ていない）。
- 【事実】E2E テストの置き場は `frontend/package.json` の `test:e2e`（`playwright test`）。ワークフローの先頭コメントでは API は Playwright route で mock し、Firebase Auth もバイパスする設計（`.github/workflows/e2e.yml:8-11`）＝実 backend との結合は検証しない設計。

### R1-4 i18n の検査

- 【事実】`frontend/scripts/check-i18n-missing-keys.js`: literal な `t()` 参照が ja.json と en.json の両方にあるかを検証（`:5-6`）。欠落があれば `process.exit(1)`（`:76`）＝error。呼び出し元は `frontend/package.json:26`（`check:i18n-missing-keys`）→ `check:all`（`frontend/package.json:44`、i18n を含むことを確認）→ `.github/workflows/e2e.yml:79`（`npm run check:all`）→ 必須 `Lint & Dark Mode Check (ADR-067)`。つまり必須チェックの内側にあり error。
- 【事実】`frontend/scripts/eslint-rules/no-japanese-literal.cjs`: `frontend/eslint.config.js:11`（読込）, `:25`（プラグイン登録）, `:31` `'local/no-japanese-literal': 'warn'`。`:29` に「Phase 1: warn のみ（既存違反を把握してから error に昇格）」とコメント。除外は `:244`, `:252`（stories、design-system、locales、design-preview 等 `:236-241`, `:250`）。
- 【事実】CI の `npm run lint` は `eslint src`（`frontend/package.json:13`）で `--max-warnings` が付かない。したがって CI 上は warn では落ちない。`lint-staged` は `eslint --max-warnings=0`（`frontend/package.json` の lint-staged 節、`frontend/eslint.config.js:30` のコメントも同趣旨）なので、ローカルコミット時だけ warn が止める。
- 【事実】結論: ハードコード日本語の検査は「CI=warn（通る）／ローカル pre-commit=ブロック」。キー欠落の検査は「CI=error」。ADR-027 の「ハードコード日本語は絶対禁止」（CLAUDE.md）は CI では強制されていない。
- 【未確認】現在の warn の件数（`npx eslint` を実行していない。読み取り専用方針のため）。

### R1-5 hex のラチェット vs 必須 `Lint & Dark Mode Check (ADR-067)`

| 観点 | `design-token-guard.yml`（ラチェット） | 必須 `Lint & Dark Mode Check (ADR-067)` |
|---|---|---|
| 必須か | **必須ではない**（main/develop どちらの必須13本にも無い） | main・develop ともに必須 |
| workflow | `.github/workflows/design-token-guard.yml:1-20`（`frontend/src/**` 変更の PR のみ、`:5-6`） | `.github/workflows/e2e.yml:84-100`（集約）→ `:56-79`（実体 `npm run check:all`） |
| 検査 | `scripts/check-design-token-ratchet.sh`: 変更ファイルごとに BASE と HEAD の `#[0-9a-fA-F]{3,8}` 件数を比較し、増えたら赤（`:25`, `:66-70`）。対象 `frontend/src/*` の `.css .tsx .jsx .ts`、`tokens.css` は除外（`:47-60`） | `check:css-colors`（`frontend/scripts/check-css-hardcoded-colors.js:5-6,:20,:23`: CSS の hex/rgba 直書きを**絶対値で**検査、index.css・tokens.css 除外）＋ eslint の `no-restricted-syntax`（`frontend/eslint.config.js:40-48`: **インラインスタイル**への hex をerror）＋ dark-parity ほか |
| 対象言語 | css / ts / tsx / jsx（コード全般） | CSS ファイル全般＋TSX の**インラインスタイルのみ** |
| 既存違反 | 増加のみ赤（既存は赤化しない） | CSS は既存ゼロ前提の絶対検査（既存があれば赤） |
| 取りこぼし | — | TSX/TS の定数・インライン以外の hex（例: `frontend/src/features/schedule/calendars.config.ts` 21件、`frontend/src/pages/roles/RolesPage.tsx` 13件、R4参照）はこの必須チェックを通過する。`docs/adr/ADR-144-ui-component-governance.md:56-57` も「ESLint はインラインスタイルのみ対象」と明記 |

- 【事実】`design-token-guard.yml` の失敗誤検知を直した記録がある（`docs/handoff/fix-guard-hex-ratchet/recon.md:15`）。
- 【事実】`scripts/check-design-token-ratchet.sh:12-13` の `ALLOWED_EXCEPTIONS=()` は空。

### R1 補足: 必須ではない他の関所（main ruleset 13本に無いもの）
- `.github/workflows/design-token-guard.yml`（hex ラチェット）、`.github/workflows/test-schema-dup-gate.yml`（`scripts/check_test_schema_dup.py`、先頭コメント `:5` に「必須ではない」）、`.github/workflows/condition-vocab-check.yml`（job `condition vocab gate`）、`.github/workflows/process-artifacts-gate.yml`。【事実】いずれも `.github/workflows/` に存在し、main の必須13本の名前には含まれない。

### R1 使用コマンド
```
gh api repos/shingo-ops/salesanchor/rulesets/15777895 --jq ...   （13本の context 列挙）
gh api repos/shingo-ops/salesanchor/rulesets/16619490 --jq '[.rules[]|select(.type=="required_status_checks")|...context]'
gh api repos/shingo-ops/salesanchor/rulesets --jq '.[]|"\(.id) \(.name) \(.target) \(.enforcement)"'
git grep -nF '<各必須名>' origin/main -- .github/workflows
git show origin/main:.github/workflows/<file> | grep -nE ...
git grep -n 'if: false' origin/main -- .github/workflows/e2e.yml
git log origin/main -S 'if: false' --format='%h %ci %s' -- .github/workflows/e2e.yml
git show 037dde856 --stat --format=...
gh api repos/shingo-ops/salesanchor/commits/037dde856/pulls ; gh pr view 1357 --repo shingo-ops/salesanchor --json body
git grep -nE 'check-i18n-missing-keys|no-japanese-literal' origin/main -- .github frontend/package.json frontend/eslint.config.js
git show origin/main:frontend/package.json | grep -nE '"(check|lint|test)...'
git show origin/main:scripts/check-design-token-ratchet.sh
```

---

## R2 配線とDB（K2）

### R2-1 画面の一覧（`frontend/src/App.tsx`、全427行）

【事実】集計（`<Route` 要素を複数行も含めて抽出）:
- `<Route>` 要素 125 個（`git grep -c '<Route ' origin/main -- frontend/src/App.tsx` は単行形式のみで 105 → 複数行形式 20 個を足すと 125）。
- うち `path=` を持つもの 120。`path=` 無しは 5（index ルート 3 ＝ `/crm`・`/admin`・`/management-center` のハブ配下の Navigate `:197,:366,:390`、認証ラッパー 2 ＝ `<ProtectedRoute><Outlet/></ProtectedRoute>` `:165` と `<ProtectedRoute><ShellSwitch/></ProtectedRoute>`）。
- `path=` を持つ 120 のうち: リダイレクト（`<Navigate>`）5（`:183,185,186,188,190`）、`CompanyIdRedirect`（App.tsx 内定義）1、ページコンポーネントに結ばれるもの **114**（重複なしのコンポーネント数は 97。`/teams`・`/staff`・`/bots`・`/suppliers`・`/roles`・`/shifts`・`/channels`・`/data` 等は `/management-center/*` 配下と単独パスの2経路で同じコンポーネントを再利用）。
- ハブ配下の相対パス（`/crm` 配下 5、`/admin` 配下 6、`/management-center` 配下 24）は以下の表では相対パスのまま記載（`:196-204`, `:365-378`, `:389-415`）。
- ページは全て `import` 静的読込（`lazy(` は App.tsx 内に 0 件）。`frontend/src/App.tsx:11-` に import 99 行。

パス → ページコンポーネント → 定義行 → ファイル（import 元）:

| パス | コンポーネント | ルート定義 | ファイル |
|---|---|---|---|
| /login | `LoginPage` | `frontend/src/App.tsx:159` | `./pages/login/LoginPage` |
| /register | `RegisterPage` | `frontend/src/App.tsx:161` | `./pages/register/RegisterPage` |
| /register/address | `RegisterAddressPage` | `frontend/src/App.tsx:162` | `./pages/register/RegisterAddressPage` |
| /register/change-billing | `RegisterChangeBillingPage` | `frontend/src/App.tsx:163` | `./pages/register/RegisterChangeBillingPage` |
| /management-center/integrations/:carrier/setup-guide | `CarrierSetupGuidePage` | `frontend/src/App.tsx:166` | `./pages/integrations/CarrierSetupGuidePage` |
| / | `DashboardPage` | `frontend/src/App.tsx:175` | `./pages/dashboard/DashboardPage` |
| /dashboard/follow-ups | `FollowUpsPage` | `frontend/src/App.tsx:176` | `./pages/dashboard/FollowUpsPage` |
| /dashboard/leads | `FunnelLeadsPage` | `frontend/src/App.tsx:177` | `./pages/dashboard/FunnelLeadsPage` |
| /dashboard/revenue | `FunnelRevenuePage` | `frontend/src/App.tsx:178` | `./pages/dashboard/FunnelRevenuePage` |
| /dashboard/reasons | `FunnelReasonsPage` | `frontend/src/App.tsx:179` | `./pages/dashboard/FunnelReasonsPage` |
| /goals/settings | `GoalSettingPage` | `frontend/src/App.tsx:180` | `./pages/goal-setting/GoalSettingPage` |
| /leads | `Navigate` | `frontend/src/App.tsx:183` | `(redirect)` |
| /crm/leads/:id/edit | `LeadEditPage` | `frontend/src/App.tsx:184` | `./pages/leads/LeadEditPage` |
| /customers | `Navigate` | `frontend/src/App.tsx:185` | `(redirect)` |
| /companies | `Navigate` | `frontend/src/App.tsx:186` | `(redirect)` |
| /companies/:id | `CompanyIdRedirect` | `frontend/src/App.tsx:187` | `(App.tsx内定義)` |
| /contacts | `Navigate` | `frontend/src/App.tsx:188` | `(redirect)` |
| /contacts/:id/edit | `ContactEditPage` | `frontend/src/App.tsx:189` | `./pages/contacts/ContactEditPage` |
| /archive | `Navigate` | `frontend/src/App.tsx:190` | `(redirect)` |
| /lead-chat | `InboxPage` | `frontend/src/App.tsx:193` | `./pages/inbox/InboxPage` |
| /crm | `CustomerHubPage` | `frontend/src/App.tsx:196` | `./pages/crm/CustomerHubPage` |
| leads | `LeadsPage` | `frontend/src/App.tsx:199` | `./pages/leads/LeadsPage` |
| companies | `CompaniesPage` | `frontend/src/App.tsx:200` | `./pages/companies/CompaniesPage` |
| companies/:id | `CompanyDetailPage` | `frontend/src/App.tsx:202` | `./pages/company-detail/CompanyDetailPage` |
| contacts | `ContactsPage` | `frontend/src/App.tsx:203` | `./pages/contacts/ContactsPage` |
| archive | `ArchivesPage` | `frontend/src/App.tsx:204` | `./pages/archives/ArchivesPage` |
| /buyback-prices | `BuybackPricesPage` | `frontend/src/App.tsx:208` | `./pages/buyback-prices/BuybackPricesPage` |
| /inventory | `InventoryPage` | `frontend/src/App.tsx:211` | `./pages/inventory/InventoryPage` |
| /own-inventory | `OwnInventoryPage` | `frontend/src/App.tsx:213` | `./pages/inventory/OwnInventoryPage` |
| /admin/products/new | `ProductEditPage` | `frontend/src/App.tsx:215` | `./pages/products/ProductEditPage` |
| /admin/products/:id/edit | `ProductEditPage` | `frontend/src/App.tsx:216` | `./pages/products/ProductEditPage` |
| /admin/products | `ProductsPage` | `frontend/src/App.tsx:217` | `./pages/products/ProductsPage` |
| /quotes/new | `QuoteCreatePage` | `frontend/src/App.tsx:220` | `./pages/quote-create/QuoteCreatePage` |
| /quotes/:id | `QuoteDetailPage` | `frontend/src/App.tsx:221` | `./pages/quote-detail/QuoteDetailPage` |
| /quotes | `QuotesPage` | `frontend/src/App.tsx:222` | `./pages/quotes/QuotesPage` |
| /invoices/new | `InvoiceCreatePage` | `frontend/src/App.tsx:223` | `./pages/invoice-create/InvoiceCreatePage` |
| /invoices/:id | `InvoiceDetailPage` | `frontend/src/App.tsx:224` | `./pages/invoice-detail/InvoiceDetailPage` |
| /invoices | `InvoicesPage` | `frontend/src/App.tsx:225` | `./pages/invoices/InvoicesPage` |
| /reports | `StaffReportsPage` | `frontend/src/App.tsx:228` | `./pages/staff-reports/StaffReportsPage` |
| /faq | `ComingSoonPage` | `frontend/src/App.tsx:232` | `./pages/coming-soon/ComingSoonPage` |
| /orders | `OrdersPage` | `frontend/src/App.tsx:242` | `./pages/orders/OrdersPage` |
| /sales | `SalesPage` | `frontend/src/App.tsx:244` | `./pages/sales/SalesPage` |
| /commissions | `CommissionsPage` | `frontend/src/App.tsx:245` | `./pages/commissions/CommissionsPage` |
| /commission-settings | `CommissionSettingsPage` | `frontend/src/App.tsx:248` | `./pages/commission-settings/CommissionSettingsPage` |
| /staff | `StaffPage` | `frontend/src/App.tsx:251` | `./pages/staff/StaffPage` |
| /staff/:id/edit | `StaffEditPage` | `frontend/src/App.tsx:252` | `./pages/staff/StaffEditPage` |
| /bots | `BotsPage` | `frontend/src/App.tsx:253` | `./pages/bots/BotsPage` |
| /bots/:id/edit | `BotEditPage` | `frontend/src/App.tsx:254` | `./pages/bots/BotEditPage` |
| /teams | `TeamsPage` | `frontend/src/App.tsx:255` | `./pages/teams/TeamsPage` |
| /teams/:id/edit | `TeamEditPage` | `frontend/src/App.tsx:256` | `./pages/teams/TeamEditPage` |
| /roles | `RolesPage` | `frontend/src/App.tsx:257` | `./pages/roles/RolesPage` |
| /data | `ERPPage` | `frontend/src/App.tsx:258` | `./pages/erp/ERPPage` |
| /suppliers | `SuppliersPage` | `frontend/src/App.tsx:259` | `./pages/suppliers/SuppliersPage` |
| /suppliers/import | `SupplierImportTenantPage` | `frontend/src/App.tsx:260` | `./pages/suppliers/SupplierImportPage` |
| /management-center/units/import | `UnitImportTenantPage` | `frontend/src/App.tsx:261` | `./pages/units/UnitImportPage` |
| /management-center/conditions/import | `ConditionImportTenantPage` | `frontend/src/App.tsx:262` | `./pages/conditions/ConditionImportPage` |
| /management-center/status-master/import | `StatusMasterImportTenantPage` | `frontend/src/App.tsx:263` | `./pages/status-master/StatusMasterImportPage` |
| /management-center/note-master/import | `NoteMasterImportTenantPage` | `frontend/src/App.tsx:264` | `./pages/note-master/NoteMasterImportPage` |
| /management-center/product-categories/import | `ProductCategoriesImportTenantPage` | `frontend/src/App.tsx:265` | `./pages/product-categories/ProductCategoriesImportPage` |
| /suppliers/:id/edit | `SupplierEditPage` | `frontend/src/App.tsx:266` | `./pages/suppliers/SupplierEditPage` |
| /purchase-orders | `PurchaseOrdersPage` | `frontend/src/App.tsx:268` | `./pages/purchase-orders/PurchaseOrdersPage` |
| /shifts | `ShiftsPage` | `frontend/src/App.tsx:271` | `./pages/shifts/ShiftsPage` |
| /schedule | `SchedulePage` | `frontend/src/App.tsx:272` | `./pages/schedule/SchedulePage` |
| /schedule/settings | `ScheduleSettingsPage` | `frontend/src/App.tsx:273` | `./pages/schedule/ScheduleSettingsPage` |
| /channels | `ChannelsPage` | `frontend/src/App.tsx:276` | `./pages/channels/ChannelsPage` |
| /channels/oauth/callback | `OAuthCallbackPage` | `frontend/src/App.tsx:279` | `./pages/oauth-callback/OAuthCallbackPage` |
| /settings | `NotificationsPage` | `frontend/src/App.tsx:284` | `./pages/notifications/NotificationsPage` |
| /account/settings | `AccountSettingsPage` | `frontend/src/App.tsx:286` | `./pages/account-settings/AccountSettingsPage` |
| /templates | `ComingSoonPage` | `frontend/src/App.tsx:290` | `./pages/coming-soon/ComingSoonPage` |
| /super-admin/tcg-sold-out | `TcgSoldOutPage` | `frontend/src/App.tsx:299` | `./pages/super-admin/TcgSoldOutPage` |
| /super-admin/tcg-product-master | `TcgProductMasterPage` | `frontend/src/App.tsx:300` | `./pages/super-admin/TcgProductMasterPage` |
| /super-admin/tcg-product-master/import | `TcgProductImportPage` | `frontend/src/App.tsx:301` | `./pages/super-admin/TcgProductImportPage` |
| /super-admin/fx-rate | `FxRatePage` | `frontend/src/App.tsx:304` | `./pages/super-admin/FxRatePage` |
| /super-admin/tcg-parallel-report | `TcgParallelReportPage` | `frontend/src/App.tsx:309` | `./pages/super-admin/TcgParallelReportPage` |
| /super-admin/tcg-supplier-quality | `TcgSupplierQualityPage` | `frontend/src/App.tsx:314` | `./pages/super-admin/TcgSupplierQualityPage` |
| /super-admin/tcg-distribution | `TcgDistributionPage` | `frontend/src/App.tsx:319` | `./pages/super-admin/TcgDistributionPage` |
| /super-admin/tcg-line-import | `TcgLineImportPage` | `frontend/src/App.tsx:324` | `./pages/super-admin/TcgLineImportPage` |
| /super-admin/analysis-rules | `AnalysisRulesPage` | `frontend/src/App.tsx:329` | `./pages/super-admin/AnalysisRulesPage` |
| /super-admin/supplier-master | `SupplierMasterPage` | `frontend/src/App.tsx:333` | `./pages/super-admin/SupplierMasterPage` |
| /super-admin/supplier-extraction-rules | `SupplierExtractionRulesPage` | `frontend/src/App.tsx:337` | `./pages/super-admin/SupplierExtractionRulesPage` |
| /super-admin/masters/suppliers/import | `SupplierImportPage` | `frontend/src/App.tsx:341` | `./pages/super-admin/SupplierImportPage` |
| /super-admin/masters/units/import | `UnitImportPage` | `frontend/src/App.tsx:345` | `./pages/super-admin/UnitImportPage` |
| /super-admin/masters/conditions/import | `ConditionImportPage` | `frontend/src/App.tsx:349` | `./pages/super-admin/ConditionImportPage` |
| /super-admin/masters/status-master/import | `StatusMasterImportPage` | `frontend/src/App.tsx:353` | `./pages/super-admin/StatusMasterImportPage` |
| /super-admin/masters/note-master/import | `NoteMasterImportPage` | `frontend/src/App.tsx:357` | `./pages/super-admin/NoteMasterImportPage` |
| /super-admin/masters/product-categories/import | `ProductCategoriesImportPage` | `frontend/src/App.tsx:361` | `./pages/super-admin/ProductCategoriesImportPage` |
| /admin | `AdminHubPage` | `frontend/src/App.tsx:365` | `./pages/admin/AdminHubPage` |
| tenant-profile | `TenantProfilePage` | `frontend/src/App.tsx:368` | `./pages/admin/TenantProfilePage` |
| tenant-policy | `TenantPolicyPage` | `frontend/src/App.tsx:370` | `./pages/admin/TenantPolicyPage` |
| discord-config | `DiscordConfigPage` | `frontend/src/App.tsx:372` | `./pages/admin/DiscordConfigPage` |
| discord-announce | `DiscordAnnouncePage` | `frontend/src/App.tsx:374` | `./pages/admin/DiscordAnnouncePage` |
| inventory-visibility | `InventoryVisibilityPage` | `frontend/src/App.tsx:376` | `./pages/admin/InventoryVisibilityPage` |
| channel-masters | `ChannelMastersPage` | `frontend/src/App.tsx:378` | `./pages/admin/ChannelMastersPage` |
| /design-system | `DesignSystemPage` | `frontend/src/App.tsx:383` | `./pages/design-system/DesignSystemPage` |
| /design-preview | `DesignPreviewPage` | `frontend/src/App.tsx:386` | `./pages/design-preview/DesignPreviewPage` |
| /management-center | `ManagementCenterPage` | `frontend/src/App.tsx:389` | `./pages/management-center/ManagementCenterPage` |
| teams | `TeamsPage` | `frontend/src/App.tsx:391` | `./pages/teams/TeamsPage` |
| staff | `StaffPage` | `frontend/src/App.tsx:392` | `./pages/staff/StaffPage` |
| shifts | `ShiftsPage` | `frontend/src/App.tsx:393` | `./pages/shifts/ShiftsPage` |
| roles | `RolesPage` | `frontend/src/App.tsx:394` | `./pages/roles/RolesPage` |
| inventory-visibility | `InventoryVisibilityPage` | `frontend/src/App.tsx:395` | `./pages/admin/InventoryVisibilityPage` |
| commission | `CommissionSettingsPage` | `frontend/src/App.tsx:396` | `./pages/commission-settings/CommissionSettingsPage` |
| tenant-profile | `TenantProfilePage` | `frontend/src/App.tsx:397` | `./pages/admin/TenantProfilePage` |
| channels | `ChannelsPage` | `frontend/src/App.tsx:398` | `./pages/channels/ChannelsPage` |
| bots | `BotsPage` | `frontend/src/App.tsx:399` | `./pages/bots/BotsPage` |
| suppliers | `SuppliersPage` | `frontend/src/App.tsx:400` | `./pages/suppliers/SuppliersPage` |
| status-master | `StatusMasterPage` | `frontend/src/App.tsx:401` | `./pages/status-master/StatusMasterPage` |
| conditions | `ConditionsPage` | `frontend/src/App.tsx:402` | `./pages/conditions/ConditionsPage` |
| product-categories | `ProductCategoriesPage` | `frontend/src/App.tsx:403` | `./pages/product-categories/ProductCategoriesPage` |
| units | `UnitsPage` | `frontend/src/App.tsx:404` | `./pages/units/UnitsPage` |
| note-master | `NoteMasterPage` | `frontend/src/App.tsx:405` | `./pages/note-master/NoteMasterPage` |
| purchase-orders | `PurchaseOrdersPage` | `frontend/src/App.tsx:406` | `./pages/purchase-orders/PurchaseOrdersPage` |
| data | `ERPPage` | `frontend/src/App.tsx:407` | `./pages/erp/ERPPage` |
| integrations/google-drive | `GoogleDriveIntegrationPage` | `frontend/src/App.tsx:409` | `./pages/integrations/GoogleDriveIntegrationPage` |
| integrations/fedex | `CarrierIntegrationPage` | `frontend/src/App.tsx:410` | `./pages/integrations/CarrierIntegrationPage` |
| integrations/dhl | `CarrierIntegrationPage` | `frontend/src/App.tsx:411` | `./pages/integrations/CarrierIntegrationPage` |
| integrations/ups | `CarrierIntegrationPage` | `frontend/src/App.tsx:412` | `./pages/integrations/CarrierIntegrationPage` |
| integrations/paypal | `PaypalIntegrationPage` | `frontend/src/App.tsx:413` | `./pages/integrations/PaypalIntegrationPage` |
| notifications | `NotificationsPage` | `frontend/src/App.tsx:414` | `./pages/notifications/NotificationsPage` |
| reports | `StaffReportsPage` | `frontend/src/App.tsx:415` | `./pages/staff-reports/StaffReportsPage` |

（注）`/crm`・`/admin`・`/management-center` 配下の行は相対パス。`<Navigate>` は `(redirect)`。`CompanyIdRedirect` は App.tsx 内の関数コンポーネント。

### R2-2 各ページが呼ぶAPIの機械抽出方法

【事実】API 呼び出しの共通層:
- `frontend/src/lib/api.ts:29` `const API_BASE = "/api/v1";`
- `frontend/src/lib/api.ts:194-207` `export const api = { get, post, put, patch, delete, getBlob, postForm }`（`fetch` ラッパー、`:85`, `:144`, `:176` で `fetch(\`${API_BASE}${path}\`)`。Firebase IDトークンを Authorization に自動付与 `:3`、GET は 502/503/504 で自動リトライ `:6-7`）。axios は使っていない（`frontend/package.json` の dependencies に axios 無し）。
- 呼び出しの書き方（`origin/main` の `frontend/src`、テスト除外、行数ベース）: `api.get(` 231 / `api.post(` 134 / `api.patch(` 75 / `api.delete(` 64 / `api.postForm(` 31 / `api.getBlob(` 17 / `api.put(` 15。型引数付き `api.get<T>("/path")` が主流。パスはリテラルまたはテンプレート文字列（`` `/staff/${id}` ``、`` `/goals/summary?tab=${...}` ``）。
- `lib/api` を import するファイルは 206（`git grep -lE "lib/api|apiClient" origin/main -- frontend/src | wc -l`）。pages 配下の `lib/api` の直接 import 行は 132（`import { api }` 86 + `../../../lib/api` 29 + `{ api, ApiError }` 15 + `{ ApiError, api }` 2）。
- 共通層を迂回する生 `fetch(` は lib/api.ts 以外で 12 件（`git grep -nE '[^.a-zA-Z]fetch\(' ... | grep -v lib/api.ts | wc -l`）。迂回の内訳は【未確認】。
- 薄い API モジュールが別にある: `frontend/src/api/funnel.ts`（`:165,172,178,185,194,210,218` で `/analytics/*` を呼ぶ）、`frontend/src/api/closeReasons.ts:14`、`frontend/src/features/tcg-distribution/distributionApi.ts`、`frontend/src/features/tcg-import-workflow/extractionAttemptsApi.ts`・`importWorkflowApi.ts`、`frontend/src/features/tcg-sold-out/soldOutApi.ts`。

【事実】機械抽出の方式（案ではなく、必要な手順の事実整理）:
1. ページファイルの直接呼び出しは `api\.(get|post|put|patch|delete|getBlob|postForm)(<T>)?\(` の正規表現でパス文字列を抜ける。
2. ただし**ページ→子コンポーネント→API モジュール**の間接呼び出しがあるため、import グラフを辿る必要がある（下記 DashboardPage の例）。
3. パスがテンプレート文字列のとき `${...}` の部分は動的で、backend のルート定義（`/staff/{staff_id}`）との突合には正規化が要る。
4. 本調査では静的解析スクリプトの実装・実行はしていない（読み取り専用）。【未確認】全ページ網羅の精度。

試験抽出 3 ページ（ページ → エンドポイント）:

| ページ（ルート） | 直接呼び出し（ファイル:行） | 子/共有モジュール経由 |
|---|---|---|
| `DashboardPage`（`/`、`frontend/src/App.tsx:175`） | `GET /goals/summary?tab=` `frontend/src/pages/dashboard/DashboardPage.tsx:339`、`GET /analytics/forecast` `:340`、`GET /analytics/followups` `:341` | import している `FunnelSection`（`frontend/src/pages/dashboard/FunnelSection.tsx:10-` は `api/funnel` 経由で `/analytics/funnel` 等 `frontend/src/api/funnel.ts:165`）、`PriorityProspectsSection`（`GET /leads/{id}` `frontend/src/pages/dashboard/PriorityProspectsSection.tsx:151,206`、`PATCH /leads/{id}` `:249`）、`WeeklyAdvisorSection`（`GET /leads/{id}` `frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx:187`、`PATCH` `:249`）。`frontend/src/pages/dashboard/DashboardPage.tsx:39` が `FUNNEL_MODE` を `../../api/funnel` から import |
| `StaffPage`（`/staff`、`frontend/src/App.tsx:251`） | `GET /staff` `frontend/src/pages/staff/StaffPage.tsx:130`、`GET /roles` `:131`、`POST /staff` `:171`、`PATCH /staff/{id}` `:188`、`DELETE /staff/{id}` `:208` | （直接呼び出しのみ。子経由は今回未走査）【未確認】 |
| `SuppliersPage`（`/suppliers`、`frontend/src/App.tsx:259`） | `GET /suppliers?…` `frontend/src/pages/suppliers/SuppliersPage.tsx:66`、`POST /suppliers` `:84`、`PATCH /suppliers/{id}` `:96`、`DELETE /suppliers/{id}` `:104`、`GET /suppliers/export`（Blob）`:112` | （同上）【未確認】 |

- 【事実】この3例だけで見ても、ページ直下に API があるもの（Staff/Suppliers）と、子コンポーネント・共有 API モジュール経由のもの（Dashboard）が混在する。

### R2-3 backend のルーター一覧（`backend/app/main.py`）

【事実】
- `app = FastAPI(` の定義は `backend/app/main.py:186-193`。
- `app.include_router(` の呼び出し 113 件（`grep -nE '^app\.include_router\(' ` で 113、すべて main.py。main.py 以外の `include_router` は 0 件）。
- prefix の内訳: `"/api/v1"` 109 件、`"/api"` 2 件（health 等）、`"/api/v1/auth"` 1 件、`"/api/v1/admin"` 1 件。
- `backend/app/routers/` の .py は `__init__` を除き 113 ファイル（`git ls-tree` で 114 エントリ中 `__init__` 1）。include_router 113 と数は一致するが、1対1の対応は未突合【未確認】。
- 各 router ファイル自身が `APIRouter(prefix=…)` を持つのは 2 件のみ（`git grep -hE 'APIRouter\(' ... | grep -c prefix` = 2）。【推測】実際のエンドポイントのパスは各 router ファイル内の `@router.get("/xxx")` で決まるものが大半（ファイル内のデコレータは未走査のため【未確認】）。該当2件は `backend/app/routers/line_import_devices.py:14`（`/tcg/line-devices`）と `backend/app/routers/translation.py:48`（`/translation`）。

| 定義行 | router | prefix |
|---|---|---|
| `backend/app/main.py:226` | `health.router` | `/api` |
| `backend/app/main.py:228` | `auth.router` | `/api/v1/auth` |
| `backend/app/main.py:230` | `webhook.router` | `/api/v1` |
| `backend/app/main.py:232` | `meta.router` | `/api/v1` |
| `backend/app/main.py:234` | `contact.router` | `/api/v1` |
| `backend/app/main.py:236` | `registration_tokens.public_router` | `/api/v1` |
| `backend/app/main.py:240` | `public_staff_avatars.public_router` | `/api` |
| `backend/app/main.py:245` | `admin.router` | `/api/v1/admin` |
| `backend/app/main.py:252` | `discord_announcement.router` | `/api/v1` |
| `backend/app/main.py:257` | `discord_reactions.router` | `/api/v1` |
| `backend/app/main.py:262` | `discord_channel_invite.router` | `/api/v1` |
| `backend/app/main.py:267` | `discord_remove.router` | `/api/v1` |
| `backend/app/main.py:272` | `discord_role_resync.router` | `/api/v1` |
| `backend/app/main.py:277` | `discord_guild_config.router` | `/api/v1` |
| `backend/app/main.py:283` | `discord_oauth.router` | `/api/v1` |
| `backend/app/main.py:287` | `discord_auto_setup.router` | `/api/v1` |
| `backend/app/main.py:292` | `discord_ticket_config.router` | `/api/v1` |
| `backend/app/main.py:297` | `companies.router` | `/api/v1` |
| `backend/app/main.py:302` | `registration_tokens.router` | `/api/v1` |
| `backend/app/main.py:306` | `contacts.router` | `/api/v1` |
| `backend/app/main.py:310` | `countries.router` | `/api/v1` |
| `backend/app/main.py:315` | `contact_channel_links.router` | `/api/v1` |
| `backend/app/main.py:320` | `close_reasons.router` | `/api/v1` |
| `backend/app/main.py:324` | `orders.router` | `/api/v1` |
| `backend/app/main.py:329` | `own_inventory.router` | `/api/v1` |
| `backend/app/main.py:334` | `order_financials.router` | `/api/v1` |
| `backend/app/main.py:339` | `order_shipping_details.router` | `/api/v1` |
| `backend/app/main.py:344` | `order_purchase_details.router` | `/api/v1` |
| `backend/app/main.py:349` | `tenant_commission_settings.router` | `/api/v1` |
| `backend/app/main.py:353` | `order_commissions.router` | `/api/v1` |
| `backend/app/main.py:357` | `dashboard.router` | `/api/v1` |
| `backend/app/main.py:361` | `reports.router` | `/api/v1` |
| `backend/app/main.py:366` | `leads.router` | `/api/v1` |
| `backend/app/main.py:370` | `teams.router` | `/api/v1` |
| `backend/app/main.py:374` | `roles.router` | `/api/v1` |
| `backend/app/main.py:379` | `products.router` | `/api/v1` |
| `backend/app/main.py:383` | `shipping.router` | `/api/v1` |
| `backend/app/main.py:387` | `quotes.router` | `/api/v1` |
| `backend/app/main.py:391` | `invoices.router` | `/api/v1` |
| `backend/app/main.py:396` | `suppliers.router` | `/api/v1` |
| `backend/app/main.py:401` | `units.router` | `/api/v1` |
| `backend/app/main.py:406` | `payment_fee_settings.router` | `/api/v1` |
| `backend/app/main.py:411` | `status_master.router` | `/api/v1` |
| `backend/app/main.py:416` | `note_master.router` | `/api/v1` |
| `backend/app/main.py:420` | `conditions.router` | `/api/v1` |
| `backend/app/main.py:425` | `product_categories.router` | `/api/v1` |
| `backend/app/main.py:429` | `purchase_orders.router` | `/api/v1` |
| `backend/app/main.py:434` | `tenant_profile.router` | `/api/v1` |
| `backend/app/main.py:439` | `tenant_policy.router` | `/api/v1` |
| `backend/app/main.py:443` | `duplicates.router` | `/api/v1` |
| `backend/app/main.py:447` | `analytics.router` | `/api/v1` |
| `backend/app/main.py:452` | `customer_priority.router` | `/api/v1` |
| `backend/app/main.py:457` | `goals.router` | `/api/v1` |
| `backend/app/main.py:462` | `notifications.router` | `/api/v1` |
| `backend/app/main.py:466` | `staff_reports.router` | `/api/v1` |
| `backend/app/main.py:470` | `archives.router` | `/api/v1` |
| `backend/app/main.py:475` | `shifts.router` | `/api/v1` |
| `backend/app/main.py:479` | `erp.router` | `/api/v1` |
| `backend/app/main.py:484` | `integrations.public_router` | `/api/v1` |
| `backend/app/main.py:485` | `integrations.router` | `/api/v1` |
| `backend/app/main.py:490` | `staff.router` | `/api/v1` |
| `backend/app/main.py:494` | `bots.router` | `/api/v1` |
| `backend/app/main.py:499` | `meta_inbox.router` | `/api/v1` |
| `backend/app/main.py:511` | `super_admin_knowledge.router` | `/api/v1` |
| `backend/app/main.py:514` | `super_admin_aliases.router` | `/api/v1` |
| `backend/app/main.py:518` | `super_admin_conditions.router` | `/api/v1` |
| `backend/app/main.py:521` | `super_admin_tcg.router` | `/api/v1` |
| `backend/app/main.py:525` | `product_masters.router` | `/api/v1` |
| `backend/app/main.py:528` | `super_admin_dex.router` | `/api/v1` |
| `backend/app/main.py:531` | `super_admin_suppliers.router` | `/api/v1` |
| `backend/app/main.py:534` | `super_admin_units.router` | `/api/v1` |
| `backend/app/main.py:538` | `super_admin_status_master.router` | `/api/v1` |
| `backend/app/main.py:542` | `rule_test.router` | `/api/v1` |
| `backend/app/main.py:546` | `super_admin_note_master.router` | `/api/v1` |
| `backend/app/main.py:550` | `super_admin_payment_fee_settings.router` | `/api/v1` |
| `backend/app/main.py:554` | `super_admin_product_categories.router` | `/api/v1` |
| `backend/app/main.py:558` | `super_admin_product_kinds.router` | `/api/v1` |
| `backend/app/main.py:562` | `super_admin_product_lines.router` | `/api/v1` |
| `backend/app/main.py:566` | `super_admin_product_formats.router` | `/api/v1` |
| `backend/app/main.py:570` | `super_admin_quantity_units.router` | `/api/v1` |
| `backend/app/main.py:574` | `super_admin_condition_defs.router` | `/api/v1` |
| `backend/app/main.py:578` | `super_admin_weight_classes.router` | `/api/v1` |
| `backend/app/main.py:582` | `super_admin_link_templates.router` | `/api/v1` |
| `backend/app/main.py:586` | `super_admin_llm_budget.router` | `/api/v1` |
| `backend/app/main.py:590` | `tenant_admin_inventory_visibility.router` | `/api/v1` |
| `backend/app/main.py:598` | `inventory_search.router` | `/api/v1` |
| `backend/app/main.py:605` | `inventory_aggregated.router` | `/api/v1` |
| `backend/app/main.py:613` | `inventory_offers.router` | `/api/v1` |
| `backend/app/main.py:619` | `me_inventory_filters.router` | `/api/v1` |
| `backend/app/main.py:626` | `super_admin_phase_switch.router` | `/api/v1` |
| `backend/app/main.py:631` | `super_admin_tenants.router` | `/api/v1` |
| `backend/app/main.py:636` | `fx_rate_admin.router` | `/api/v1` |
| `backend/app/main.py:642` | `google_calendar.public_router` | `/api/v1` |
| `backend/app/main.py:644` | `google_calendar.router` | `/api/v1` |
| `backend/app/main.py:650` | `calendar_router.router` | `/api/v1` |
| `backend/app/main.py:656` | `translation.router` | `/api/v1` |
| `backend/app/main.py:662` | `conv_logs.router` | `/api/v1` |
| `backend/app/main.py:668` | `item_corrections.router` | `/api/v1` |
| `backend/app/main.py:673` | `tcg_analysis_review.router` | `/api/v1` |
| `backend/app/main.py:678` | `tcg_product_master.router` | `/api/v1` |
| `backend/app/main.py:683` | `tcg_product_import.router` | `/api/v1` |
| `backend/app/main.py:688` | `tcg_shadow_review.router` | `/api/v1` |
| `backend/app/main.py:693` | `tcg_shadow_accuracy.router` | `/api/v1` |
| `backend/app/main.py:698` | `tcg_supplier_quality.router` | `/api/v1` |
| `backend/app/main.py:703` | `tcg_analysis_dashboard.router` | `/api/v1` |
| `backend/app/main.py:708` | `tcg_diagnostics.router` | `/api/v1` |
| `backend/app/main.py:713` | `tcg_parallel_report.router` | `/api/v1` |
| `backend/app/main.py:718` | `tcg_distribution.router` | `/api/v1` |
| `backend/app/main.py:723` | `tcg_line_import.router` | `/api/v1` |
| `backend/app/main.py:728` | `line_import_devices.router` | `/api/v1` |
| `backend/app/main.py:731` | `buyback_prices.router` | `/api/v1` |
| `backend/app/main.py:737` | `buyback_alerts.router` | `/api/v1` |
| `backend/app/main.py:742` | `super_admin_db_schema.router` | `/api/v1` |

### R2-4 既存のSSOT系の検査

| 検査 | 場所（ファイル:行） | 何を検査するか | 必須か（main ruleset 15777895 の13本に含まれるか） |
|---|---|---|---|
| supplier_id SSOT ガード（migration-guard チェック9） | `.github/workflows/migration-guard.yml:588-652`（job `check` は `:8-9`） | migration の差分に `supplier_channels` が含まれ、かつ `DROP COLUMN supplier_id` / `ALTER COLUMN supplier_id TYPE` 等があれば赤（`:621`）。背景 PR #3539（`:652`） | **必須**（job 名「models.py に新 Column → deploy.yml にマイグレーション追記必須」が13本の4番目。チェック1〜9が同一 job `check`） |
| 共用マスタ保護（チェック7/8, ADR-155） | `.github/workflows/migration-guard.yml:394-407`, `:485-503` | 保護テーブル群への INSERT/UPDATE/DELETE（7）と SELECT（8）を migration で禁止 | 同上（必須） |
| `scripts/check_schema_catchup_sync.py` | `scripts/check_schema_catchup_sync.py:1-8`、呼び出し `.github/workflows/schema-check.yml:93` | `scripts/setup_tenant.py` と `scripts/db/sync_tenant_schema.py` の catch-up migration ファイル名リストの一致（ずれたら赤） | **必須**（schema-check.yml の集約ジョブ「テナントスキーマ整合性チェック」`:223` の内側） |
| `scripts/check-condition-vocab.js` | `scripts/check-condition-vocab.js:1-25`、呼び出し `.github/workflows/condition-vocab-check.yml:21`（job `condition vocab gate` `:13`） | 旧語彙（例 `shrink_yes`）が `frontend/src/locales/ja.json`・`en.json` に残っていないか（CODE_FILES は 2026-10-02 付で空配列、JSON のみ有効、`:9-20`） | **必須ではない**（13本に名前なし） |
| `test-schema-dup-gate.yml` | `.github/workflows/test-schema-dup-gate.yml:13-14,:34-40`（job `test-schema-dup gate`、先頭コメント `:5` が「必須ではない」） | `backend/tests/` が本番テーブル定義を独自 CREATE TABLE で複製するのを増加検知（`scripts/check_test_schema_dup.py`）＋ `docs/specs/process-hardening/pillar3-inventory.md` の整合 | **必須ではない** |
| `scripts/lint_tenant_schema.py` | `.github/workflows/lint-tenant-schema.yml:69` | `backend/app/routers/` の tenant schema 修飾（ADR-072）を strict で検査 | **必須**（13本の5番目） |

- 【事実】「画面×API×テーブルの配線」自体を台帳と突合する検査は、上記の中に無い。`dangling-route gate` だけが API ルートの削除→frontend参照を検査する（`scripts/check-dangling-routes.js:5-11`）。

### R2-5 配線台帳の代わりになりうる既存文書

- 【事実】`docs/handoff/db-structure-viewer/design.md:1-14`: 管理画面から DB 全テーブル構造・FK を見る機能。データ取得は `information_schema`（`:10-14`）＝実行時に DB から取る方式で、文書としての台帳ではない。UI は `AnalysisRulesSidebar` のパネル（`:17-19`）。
- 【事実】`docs/handoff/db-structure-graph/design.md:5-13`: LINE解析パイプラインのテーブル関連の視覚マップ（@xyflow/react、`PipelineMapPanel`）。対象は LINE 解析パイプラインのみ（`:5`）。
- 【事実】`git ls-tree -r --name-only origin/main | grep -iE 'wiring|配線|route-?map|api-?map|screen-?map|schema-?doc|er-?diagram|db-structure'` の結果は、上記 db-structure-viewer / db-structure-graph と、個別修正の handoff（`docs/handoff/discord-reaction-wiring-fix/`、`docs/handoff/fix-supplier-migration-wiring/`、`docs/handoff/fix-tcg-schema-wiring/`）、`backend/tests/test_discord_reaction_wiring.py` のみ。**画面→API→テーブルを一覧化した文書は見つからなかった**。ただしファイル名ベースの検索のみで、本文検索は未実施【未確認】。
- 【事実】`frontend/src/config/routeTitles.ts` が存在する（画面タイトルの対応表と思われるが内容は未読）【未確認】。`frontend/scripts/check-nav-title-sync.js`（`check:nav-sync`）がナビとタイトルの同期を検査する（`frontend/package.json:20`）。

### R2 使用コマンド
```
git show origin/main:frontend/src/App.tsx   （perl で <Route> を複数行含め抽出、import 行と突合）
git grep -c '<Route ' origin/main -- frontend/src/App.tsx
git show origin/main:frontend/src/lib/api.ts ; git grep -nE 'API_BASE' origin/main -- frontend/src/lib/api.ts
git grep -hE "api\.<method>(<|\()" origin/main -- frontend/src ':!*.test.*' | wc -l   （method ごと）
git grep -nE 'api\.(get|post|put|patch|delete|getBlob|postForm)' origin/main -- <3ページ>
git show origin/main:backend/app/main.py   （perl で include_router を複数行含め抽出）
git grep -hE 'APIRouter\(' origin/main -- backend/app/routers | grep -c prefix
git show origin/main:.github/workflows/migration-guard.yml | grep -nE 'チェック[0-9]|supplier'
git show origin/main:scripts/check_schema_catchup_sync.py ; git show origin/main:scripts/check-condition-vocab.js
git show origin/main:.github/workflows/{test-schema-dup-gate,condition-vocab-check}.yml
git ls-tree -r --name-only origin/main | grep -iE 'wiring|配線|route-?map|...'
```

---

## R3 フロントとバックの型（K3）

- 【事実】FastAPI の OpenAPI は出力可能な構成: `app = FastAPI(`（`backend/app/main.py:186-193`）で `openapi_url` の指定は無い（`git grep -nE 'openapi_url' origin/main -- backend/app` が0件）。`docs_url=None if is_production else "/docs"`、`redoc_url=None if is_production else "/redoc"`（`:190-191`）は Swagger UI / ReDoc のみを本番で無効化する。FastAPI の既定では `/openapi.json` は `openapi_url` 未指定なら有効のまま（FastAPI の仕様。本調査では Context7 等で公式文書の再確認はしておらず【未確認】、実機で `/openapi.json` を叩いてもいない）。
- 【事実】`backend/app/main.py:187-189` の title は "Multi-tenant CRM API"、version "1.0.0"。
- 【事実】frontend の API レスポンス型は手書き。`export interface|type` は `frontend/src` 配下の 94 ファイルに 258 宣言（`git grep -lE '^export (interface|type) ...' | wc -l` = 94、`-hE ... | wc -l` = 258、テスト・stories 除外）。トップレベルの `interface|type` 宣言は export の有無を問わず 539（同条件）。
  - 型専用ファイルの例: `frontend/src/pages/buyback-prices/buybackTypes.ts`、`frontend/src/pages/company-detail/company-detail.types.ts`、`frontend/src/pages/inbox/inbox.types.ts`、`frontend/src/pages/orders/orders.types.ts`、`frontend/src/pages/products/products.types.ts`、`frontend/src/pages/super-admin/components/shadowAccuracyTypes.ts`、`frontend/src/types/nav.ts`（`frontend/src/types/` は1ファイルのみ）。
  - 多くはページファイル内で `api.get<Staff[]>("/staff")` のように呼び出し側でインライン定義（例 `frontend/src/pages/dashboard/DashboardPage.tsx:339-341` の `GoalSummary`, `Forecast`, `FollowUps`）。
  - API モジュール側の型: `frontend/src/api/funnel.ts`（`FunnelResponse` 等 `:165-218`）。
- 【事実】型生成ツールは無い: `frontend/package.json` の dependencies（`@fullcalendar/*`, `@heroicons/react`, `@xyflow/react`, `date-fns`, `firebase`, `i18next`, `lucide-react`, `react`, `react-big-calendar`, `react-dom`, `react-i18next`, `react-router-dom`, `recharts`）にも、scripts（`build`/`test:e2e`/`lint`/`check:*`/`generate:icon-sizes` のみ）にも、openapi/swagger/orval/codegen/zod 系の語は無い（`git show origin/main:frontend/package.json | grep -inE 'openapi|swagger|orval|codegen|zod|trpc|kubb|hey-api'` が0件、`git grep -nE 'openapi|OpenAPI' origin/main -- frontend/package.json frontend/package-lock.json` も0件）。devDependencies は全件を精査していない【未確認】が、上記 grep が package.json 全体を対象にしているため 0 件は事実。
- 【事実】CI に OpenAPI を扱う job は無い（`git grep -nE 'openapi' origin/main -- .github/workflows` が0件）。
- 【事実】backend 側のスキーマ（Pydantic）の件数は今回未集計【未確認】。

### R3 使用コマンド
```
git grep -nE 'app = FastAPI\(|openapi|docs_url|redoc_url' origin/main -- backend/app/main.py
git grep -nE 'openapi_url' origin/main -- backend/app
git grep -lE '^export (interface|type) [A-Za-z_]+' origin/main -- frontend/src ':!*.test.*' ':!*.stories.*' | wc -l
git grep -hE '^export (interface|type) [A-Za-z_]+' origin/main -- frontend/src ':!*.test.*' ':!*.stories.*' | wc -l
git grep -hE '^(interface|type) [A-Za-z_]+' origin/main -- frontend/src ':!*.test.*' ':!*.stories.*' | wc -l
git show origin/main:frontend/package.json | grep -inE 'openapi|swagger|orval|codegen|zod|trpc|kubb|hey-api'
git grep -nE 'openapi' origin/main -- .github/workflows
```

---

## R4 デザイン違反（K4）

### R4-1 生 `<select>`（`git grep -nE '<select([ >]|$)' origin/main -- 'frontend/src/pages/*.tsx'`）

- 【事実】実数は **70 件**（依頼の想定 74 とは一致しない）。`git grep -nE '<select([ >/]|$)'` でも 70。全 `frontend/src` の `<select` は 79 行（pages 70 ＋ components 9。components の9は金型 `Select.tsx:53`、`CompanyContactSelector.tsx` 2、`CommissionPanel.tsx:205`、`PurchaseDetailPanel.tsx:424`、`ShippingDetailPanel.tsx:511`、`ContentToolbar.stories.tsx:16`、`InventorySearchBar.tsx:5`（コメント）、`ItemComparison.tsx:26`）。
- 【事実】CI 関所の数え方（`scripts/check-ui-governance.js:153-163` の `countSelect`: `/<select[\s>/]/g` から直前/同行の有効な `ui-allow` を除く、対象は `frontend/src/pages/**/*.tsx`、stories / `design-system/` / `design-preview/` を除外 `:88-90`）で origin/main を数えると **60 件**（=70 のうち 10 件が有効 ui-allow で除外）。同方式で input 216（※下記）、自作タブ 31。
- 全 70 件のファイル:行（ファイル別件数順）:

```
frontend/src/pages/account-settings/PreferencesSection.tsx:38
frontend/src/pages/admin/TenantPolicyPage.tsx:167
frontend/src/pages/admin/TenantPolicyPage.tsx:266
frontend/src/pages/admin/TenantPolicyPage.tsx:283
frontend/src/pages/admin/TenantProfilePage.tsx:234
frontend/src/pages/bots/BotsPage.tsx:233
frontend/src/pages/bots/BotsPage.tsx:241
frontend/src/pages/bots/BotsPage.tsx:248
frontend/src/pages/commission-settings/CommissionSettingsPage.tsx:206
frontend/src/pages/companies/CompaniesPage.tsx:506
frontend/src/pages/company-detail/CompanyBasicTab.tsx:84
frontend/src/pages/company-detail/CompanyConvLogsTab.tsx:73
frontend/src/pages/contacts/ContactsPage.tsx:273
frontend/src/pages/contacts/ContactsPage.tsx:308
frontend/src/pages/contacts/ContactsPage.tsx:341
frontend/src/pages/dashboard/DashboardPage.tsx:412
frontend/src/pages/dashboard/DashboardPage.tsx:441
frontend/src/pages/goal-setting/GoalSettingPage.tsx:711
frontend/src/pages/inbox/InboxConversationList.tsx:147
frontend/src/pages/inbox/InboxKartePanel.tsx:447
frontend/src/pages/inbox/InboxKartePanel.tsx:514
frontend/src/pages/inbox/InboxKartePanel.tsx:527
frontend/src/pages/inbox/InboxKartePanel.tsx:541
frontend/src/pages/inbox/InboxKartePanel.tsx:557
frontend/src/pages/inbox/InboxMessageThread.tsx:409
frontend/src/pages/inbox/InboxPage.tsx:92
frontend/src/pages/inbox/InboxProfileModal.tsx:161
frontend/src/pages/inbox/InboxProfileModal.tsx:200
frontend/src/pages/inbox/InboxProfileModal.tsx:215
frontend/src/pages/inbox/InboxProfileModal.tsx:226
frontend/src/pages/inbox/InboxSettingsModal.tsx:37
frontend/src/pages/inbox/ManualRecordSection.tsx:126
frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:493
frontend/src/pages/integrations/PaypalIntegrationPage.tsx:164
frontend/src/pages/inventory/InventoryPage.tsx:477
frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:308
frontend/src/pages/orders/OrdersFilterBar.tsx:40
frontend/src/pages/orders/OrdersFormModal.tsx:86
frontend/src/pages/products/ProductEditPage.tsx:231
frontend/src/pages/products/ProductEditPage.tsx:238
frontend/src/pages/products/ProductEditPage.tsx:255
frontend/src/pages/products/ProductEditPage.tsx:278
frontend/src/pages/products/ProductEditPage.tsx:285
frontend/src/pages/products/ProductEditPage.tsx:302
frontend/src/pages/products/ProductEditPage.tsx:346
frontend/src/pages/products/ProductEditPage.tsx:353
frontend/src/pages/products/ProductEditPage.tsx:360
frontend/src/pages/products/ProductsPage.tsx:220
frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:156
frontend/src/pages/purchase-orders/PurchaseOrdersPage.tsx:193
frontend/src/pages/quote-create/QuoteCreatePage.tsx:157
frontend/src/pages/schedule/SchedulePageImpl.tsx:288
frontend/src/pages/schedule/ScheduleSettingsPage.tsx:170
frontend/src/pages/schedule/ScheduleSettingsPage.tsx:225
frontend/src/pages/status-master/StatusMasterPage.tsx:260
frontend/src/pages/status-master/StatusMasterPage.tsx:274
frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:322
frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:338
frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:393
frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:409
frontend/src/pages/super-admin/components/StatusMasterPanel.tsx:311
frontend/src/pages/super-admin/components/StatusMasterPanel.tsx:325
frontend/src/pages/super-admin/DexTab.tsx:194
frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:447
frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:455
frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:472
frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:501
frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:523
frontend/src/pages/super-admin/TcgSeriesTab.tsx:190
frontend/src/pages/super-admin/TcgSeriesTab.tsx:300
```

- 【事実】ファイル別内訳の上位（関所方式 60 件）: `frontend/src/pages/products/ProductEditPage.tsx` 9、`frontend/src/pages/inbox/InboxKartePanel.tsx` 5、`frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx` 5、`frontend/src/pages/inbox/InboxProfileModal.tsx` 4、`frontend/src/pages/admin/TenantPolicyPage.tsx` 3、`frontend/src/pages/bots/BotsPage.tsx` 3 ほか（32 ファイル）。
- 【事実】70 と 60 の差 10 は、関所方式が直前/同行の有効な `ui-allow` を除外するため（`scripts/check-ui-governance.js:106-124`）。差の10件それぞれの特定は未実施【未確認】。
- 【事実】参考: 依頼の「74」に近い数字として、pages 配下の単行 `<input ... type="checkbox|radio|file|number|date|...">` が 74 行ある（`git grep -nE '<input[^>]*type="(checkbox|radio|file|number|date|hidden|password|email|range|time|datetime-local|month|color|tel|url)"' origin/main -- 'frontend/src/pages/*.tsx'`）。これが想定の出所かどうかは【未確認】。

### R4-2 金型（`frontend/src/components/` の共通部品）

| 用途 | 金型 | 場所 |
|---|---|---|
| セレクト | `Select`（ラベル付き）、`SelectControl`（コントロールのみ）。型 `SelectOption`/`SelectSize`(sm/md/lg) | `frontend/src/components/Select.tsx:15-34`（`SelectControl` `:34`、`Select` `:77`、内部で `<select>` を1箇所だけ描画 `:53`） |
| テキスト入力 | `TextField`（size sm/md/lg） | `frontend/src/components/TextField.tsx:16,:29` |
| タブ | `Tabs`（variant underline/pill、size sm/md） | `frontend/src/components/Tabs.tsx:34-48` |
| 検索入力 | `InventorySearchBar`（在庫検索用。汎用 SearchBar は未確認） | `frontend/src/components/InventorySearchBar.tsx:93` |
| その他の選択系 | `CountryCombobox`、`ChannelTypeCombobox`、`CompanyContactSelector`、`NavDropdown`、`DataTable` | `frontend/src/components/` 直下 |

- 【事実】ADR-144 が推奨代替として挙げる `OverflowTabs`（`docs/adr/ADR-144-ui-component-governance.md:38`）は `frontend/src/components` に見つからない（`git grep -nE 'OverflowTabs' origin/main -- frontend/src/components` が0件）。同様に `SearchBar` 相当の汎用部品名は ADR に書かれているが `components/` に存在しない（`export .*SearchBar` は `InventorySearchBar` のみ）。
- 【事実】`SelectControl` を使っている pages 配下のファイルは 13（`git grep -lE 'SelectControl' origin/main -- frontend/src/pages | wc -l`）。生 `<select>` を持つファイルは 32 ＝ 金型採用より未採用が多い。
- 【事実】`frontend/src/components/Select.tsx:8` に「実画面への展開は Task 2E で行う」と書かれたままで、展開は部分的。

### R4-3 生の input とタブ（`scripts/check-ui-governance.js` 基準）

検出定義:
- 生 `<input>`: `<input` の次が空白・`>`・`/`のもの（`:182-186`）。`type` が `text` / `search` / 省略のとき検出対象（`:213-218`）。複数行・`{}` を考慮してタグ末尾を探す（`:174-208`）。直前/同行の有効な `ui-allow` は除外（`:223-231`）。
- 自作タブ: `className="..."`（静的）または `` className={`...`} ``（テンプレート静的部）のトークンに `tab` を含み `table` を含まないもの（`:243-245`, `:257-275`）。
- 対象は `frontend/src/pages/**/*.tsx`、除外は stories / `design-system/` / `design-preview/`（`:88-90`）。

【事実】origin/main の実測（関所の関数 `countAll` を origin/main の同スクリプトから切り出して全 187 ファイルに適用した値。ファイル数は pages 配下 .tsx 208 のうち除外対象を除いた数）:

| 種別 | 件数 | ファイル数 | ADR-144 記載の recon 実測（2026-06-25）`docs/adr/ADR-144-ui-component-governance.md:16-18` |
|---|---|---|---|
| 生 `<select>` | 60 | 32 | 118 |
| 生 `<input text/search/省略>` | 216 | 51 | 16 |
| 自作タブ | 31 | 16 | 20 |

- 【事実】input の 216 は ADR-144 の記載値 16 と桁が違う。ADR-144 の recon は「`<input type="text"|"search">`」と書き、type 省略を数えていなかった可能性があるが、これは推測で、ADR-144 の recon の数え方は【未確認】。
- 【事実】input 上位: `frontend/src/pages/companies/CompaniesPage.tsx` 23、`frontend/src/pages/register/RegisterPage.tsx` 17、`frontend/src/pages/company-detail/CompanyBasicTab.tsx` 10、`frontend/src/pages/register/RegisterAddressPage.tsx` 9、`frontend/src/pages/admin/DiscordConfigPage.tsx` 8、`frontend/src/pages/contacts/ContactsPage.tsx` 8。
- 【事実】自作タブ上位: `frontend/src/pages/companies/CompaniesPage.tsx` 4、`frontend/src/pages/dashboard/DashboardPage.tsx` 3、`frontend/src/pages/dashboard/FunnelReasonsPage.tsx` 3、`frontend/src/pages/inbox/InboxKartePanel.tsx` 3、`frontend/src/pages/inbox/InboxProfileModal.tsx` 3。
- 【事実】`pages/` 外（`frontend/src/features/`・`frontend/src/components/`）は関所の対象外（`PAGES_DIR = 'frontend/src/pages/'` `scripts/check-ui-governance.js:36`）。`frontend/src/components/` に生 `<select>` が 5 コンポーネント（上記）あり、関所は検出しない。
- ファイル別の全件（関所方式）:

input 全ファイル別（関所方式）:
```
frontend 件数 23  frontend/src/pages/companies/CompaniesPage.tsx
frontend 件数 17  frontend/src/pages/register/RegisterPage.tsx
frontend 件数 10  frontend/src/pages/company-detail/CompanyBasicTab.tsx
frontend 件数 9  frontend/src/pages/register/RegisterAddressPage.tsx
frontend 件数 8  frontend/src/pages/admin/DiscordConfigPage.tsx
frontend 件数 8  frontend/src/pages/contacts/ContactsPage.tsx
frontend 件数 8  frontend/src/pages/register/RegisterChangeBillingPage.tsx
frontend 件数 8  frontend/src/pages/staff/StaffEditPage.tsx
frontend 件数 7  frontend/src/pages/staff/StaffPage.tsx
frontend 件数 6  frontend/src/pages/account-settings/ProfileSection.tsx
frontend 件数 6  frontend/src/pages/contacts/ContactEditPage.tsx
frontend 件数 6  frontend/src/pages/inbox/InboxProfileModal.tsx
frontend 件数 5  frontend/src/pages/admin/TenantProfilePage.tsx
frontend 件数 5  frontend/src/pages/inbox/InboxKartePanel.tsx
frontend 件数 5  frontend/src/pages/invoice-create/InvoiceCreatePage.tsx
frontend 件数 5  frontend/src/pages/products/ProductEditPage.tsx
frontend 件数 5  frontend/src/pages/quote-create/QuoteCreatePage.tsx
frontend 件数 5  frontend/src/pages/super-admin/DexTab.tsx
frontend 件数 5  frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx
frontend 件数 5  frontend/src/pages/super-admin/TcgSeriesTab.tsx
frontend 件数 4  frontend/src/pages/company-detail/CompanyDiscordTab.tsx
frontend 件数 4  frontend/src/pages/leads/LeadsPage.tsx
frontend 件数 3  frontend/src/pages/badges/BadgesPage.tsx
frontend 件数 3  frontend/src/pages/bots/BotsPage.tsx
frontend 件数 3  frontend/src/pages/companies/CompanyFormFields.tsx
frontend 件数 3  frontend/src/pages/contacts/ContactFormFields.tsx
frontend 件数 3  frontend/src/pages/integrations/FedexLabelValidationTab.tsx
frontend 件数 3  frontend/src/pages/leads/LeadEditPage.tsx
frontend 件数 3  frontend/src/pages/staff/StaffFormFields.tsx
frontend 件数 3  frontend/src/pages/suppliers/SupplierFormFields.tsx
frontend 件数 2  frontend/src/pages/admin/ChannelMastersPage.tsx
frontend 件数 2  frontend/src/pages/admin/TenantPolicyPage.tsx
frontend 件数 2  frontend/src/pages/bots/BotFormFields.tsx
frontend 件数 2  frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx
frontend 件数 2  frontend/src/pages/leads/LeadFormFields.tsx
frontend 件数 2  frontend/src/pages/notifications/NotificationsPage.tsx
frontend 件数 2  frontend/src/pages/schedule/SchedulePageImpl.tsx
frontend 件数 1  frontend/src/pages/admin/DiscordAnnouncePage.tsx
frontend 件数 1  frontend/src/pages/company-detail/CompanyChannelsTab.tsx
frontend 件数 1  frontend/src/pages/inbox/InboxConversationList.tsx
frontend 件数 1  frontend/src/pages/inbox/SalesFormMultiSelect.tsx
frontend 件数 1  frontend/src/pages/integrations/PaypalIntegrationPage.tsx
frontend 件数 1  frontend/src/pages/inventory/InventoryPage.tsx
frontend 件数 1  frontend/src/pages/orders/OrdersFilterBar.tsx
frontend 件数 1  frontend/src/pages/orders/OrdersFormModal.tsx
frontend 件数 1  frontend/src/pages/products/ProductsPage.tsx
frontend 件数 1  frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx
frontend 件数 1  frontend/src/pages/register/CountryCombobox.tsx
frontend 件数 1  frontend/src/pages/roles/RolesPage.tsx
frontend 件数 1  frontend/src/pages/staff-reports/StaffReportsPage.tsx
frontend 件数 1  frontend/src/pages/teams/TeamFormFields.tsx
```

tab 全ファイル別（関所方式）:
```
frontend 件数 4  frontend/src/pages/companies/CompaniesPage.tsx
frontend 件数 3  frontend/src/pages/dashboard/DashboardPage.tsx
frontend 件数 3  frontend/src/pages/dashboard/FunnelReasonsPage.tsx
frontend 件数 3  frontend/src/pages/inbox/InboxKartePanel.tsx
frontend 件数 3  frontend/src/pages/inbox/InboxProfileModal.tsx
frontend 件数 2  frontend/src/pages/admin/AdminHubPage.tsx
frontend 件数 2  frontend/src/pages/inbox/InboxPage.tsx
frontend 件数 2  frontend/src/pages/invoices/InvoicesPage.tsx
frontend 件数 2  frontend/src/pages/quotes/QuotesPage.tsx
frontend 件数 1  frontend/src/pages/company-detail/CompanyConvLogsTab.tsx
frontend 件数 1  frontend/src/pages/company-detail/CompanyDetailPage.tsx
frontend 件数 1  frontend/src/pages/super-admin/DexTab.tsx
frontend 件数 1  frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx
frontend 件数 1  frontend/src/pages/super-admin/LLMBudgetTab.tsx
frontend 件数 1  frontend/src/pages/super-admin/ProductMastersTab.tsx
frontend 件数 1  frontend/src/pages/super-admin/TcgSeriesTab.tsx
```

### R4-4 hex の直書き件数（design-token-guard の数え方の再現）

【事実】数え方（`scripts/check-design-token-ratchet.sh:25`）: `git show <ref>:<file> | sed -E 's/\(#[0-9]+\)//g' | grep -oE '#[0-9a-fA-F]{3,8}\b'` の行数。対象ファイルは `frontend/src/*` の `.css .tsx .jsx .ts`、`frontend/src/tokens.css` は除外（`:47-60`）。ただし本来は PR の変更ファイルの BASE→HEAD の**増加**だけを見る（`:61-70`）。ここでは同じ数え方を origin/main の全ファイルに適用して現在の総量を出した。

【事実】結果: 対象 518 ファイル中、1件以上あるのは 15 ファイル、合計 **235 件**。内訳（件数順・全件）:

```
179 frontend/src/index.css
21 frontend/src/features/schedule/calendars.config.ts
13 frontend/src/pages/roles/RolesPage.tsx
6 frontend/src/components/CompanyContactSelector.tsx
5 frontend/src/components/MergeCompanyModal.tsx
2 frontend/src/contexts/UiPrefsContext.tsx
1 frontend/src/pages/schedule/schedule-owner.ts
1 frontend/src/pages/dashboard/DashboardPage.tsx
1 frontend/src/pages/company-detail/CompanyDetailPage.tsx
1 frontend/src/pages/company-detail/CompanyBasicTab.tsx
1 frontend/src/pages/companies/CompaniesPage.tsx
1 frontend/src/components/FormField.css
1 frontend/src/components/ContactChannelForm.stories.tsx
1 frontend/src/components.css
1 frontend/src/App.tsx
```

- 【事実】`frontend/src/index.css` の 179 件は色トークンの定義側（`docs/specs/design-system/kgi.md:25` が除外対象とする「index.css/tokens.css=色トークン正本」）。これを除くと **56 件**（ts/tsx 54 件＋css 2 件）。pages 配下は 6 ファイル 18 件。
- 【事実】`docs/specs/design-system/kgi.md:25` の「36件と確定（recon cbaee61）」とは一致しない（56 vs 36）。差の理由（測定日の違い・数え方の違い・`#fff` 等の非色や ref 内 issue 番号 `#123` のような数字の誤検出の混入）は【未確認】。`sed 's/\(#[0-9]+\)//g'` は `(#3594)` のような括弧つき番号だけを除くので、括弧なしの `#123` は拾う。
- 【事実】`frontend/src/features/schedule/calendars.config.ts`（21件）と `frontend/src/pages/roles/RolesPage.tsx`（13件）が最大。どちらもインラインスタイル以外の定数（TS）で、必須の ESLint 規則（インラインスタイルのみ対象 `frontend/eslint.config.js:40-48`）を素通りする（R1-5）。
- 【未確認】CI（GNU grep）での同一性。ローカルの grep は ugrep 7.8.4 で、`\b` の扱いが GNU grep と同じかは検証していない。

### R4-5 ui-allow（29件）と番号の無い2件

- 【事実】`git grep -n 'ui-allow' origin/main -- frontend/src` は 29 行（実コメントとして `ui-allow:` を含むのも 29 行。ほかに `docs/` 配下にも言及あり）。
- 【事実】29 件の内訳: `frontend/src/pages/` 配下 26 件、`frontend/src/features/` 配下 3 件（`frontend/src/features/supplier-master/SupplierDetailDrawer.tsx:411,433`、`frontend/src/features/tcg-import-review/ReviewSection.tsx:288`）。関所の対象は pages/ のみなので、`features/` の 3 件は関所の評価には現れない。
- 【事実】関所の `isValidUiAllow`（`scripts/check-ui-governance.js:106-108` `/ui-allow:\s+\S+.*\(#\d+\)/`）で pages 配下 26 件を判定すると **有効 24・無効 2**。
- 【事実】番号の無い2件を再確認した（`git grep -n 'ui-allow:' origin/main -- frontend/src` の実出力）:
  - `frontend/src/pages/conditions/ConditionsPage.tsx:501`: `{/* ui-allow: alias table is a small inline form, not a data listing */}`（`(#番号)` 無し）
  - `frontend/src/pages/super-admin/components/UnitMasterPanel.tsx:361`: `{/* ui-allow: alias table is a small inline form, not a data listing */}`（`(#番号)` 無し）
  - 2件とも同一文言。ADR-144 の規定「理由と課題番号の両方が必須。番号なしは無効（赤のまま）」（`docs/adr/ADR-144-ui-component-governance.md:47-48`）に反する。
- 【事実】無効な ui-allow が main に存在できている。関所は PR の差分で `HEAD件数 > BASE件数` のときだけ赤にするため、既存のまま変えない限り赤にならない（`:14-16`）。この2件が実際に生UI部品（select/input/tab）を直前/同行に持つかは、関所が数える対象と1対1で突合していない【未確認】。
- 【事実】他の29件のうち 有効な番号つき 27 の番号は `#3564`, `#3306`, `#3594`, `#2624`, `#2601`, `#3558`, `#3285` など（`git grep` 出力の通り）。`#2624`（InventoryPage:462,476、InboxMessageThread:408）は「back-merge from main」を理由にしている。

### R4 使用コマンド
```
git grep -nE '<select([ >]|$)' origin/main -- 'frontend/src/pages/*.tsx'   （70件。select-all.txt に保存）
git grep -nE '<select' origin/main -- 'frontend/src/*.tsx'              （79行）
git ls-tree -r --name-only origin/main -- frontend/src/components | grep -E '\.tsx$' | grep -iE 'select|textfield|input|tabs...'
git grep -nE '^export ' origin/main -- frontend/src/components/{Select,TextField,Tabs}.tsx
node -e '（origin/main の scripts/check-ui-governance.js の countAll 等を切り出して全 pages/*.tsx に適用）'
git grep -n 'ui-allow:' origin/main -- frontend/src
git ls-tree -r --name-only origin/main -- frontend/src | grep -E '\.(css|tsx|jsx|ts)$' | grep -v '^frontend/src/tokens.css$' → 各ファイルに check-design-token-ratchet.sh:25 の sed|grep -oE を適用
```

---

## 全体の要点（各節）

- R0: 関連 ADR は 027/067/072/135/136×2/144/1003/121/155。ADR-135 は process-artifacts gate を main 必須に「実施済み」と書くが、2026-10-02 の main ruleset 13本に無い（develop には有る）。OpenAPI・型生成・E2E・配線台帳に関する ADR は FEATURE-INDEX に無い。
- R1: main 必須13本のうち配線を見るのは dangling-route gate のみ。process-artifacts gate は main 非必須・develop 必須。Playwright E2E は 2026-06-01（PR #1357）から `if: false`（理由: 約91秒/PR）。i18n 日本語直書きは CI=warn、キー欠落は CI=error。hex は必須チェックが「CSS絶対検査＋TSXインラインのみ」で、ts/tsx 定数の hex は素通り。
- R2: ルート要素125（path付き120＝ページ114＋redirect5＋CompanyIdRedirect1）、backend include_router 113。API共通層は `frontend/src/lib/api.ts`（`/api/v1`）。画面→API→テーブルの台帳は存在せず、ページ→子→APIモジュールの間接呼び出しがあるため機械抽出は import グラフ走査が要る。
- R3: OpenAPI は `/openapi.json` を無効化する設定が無い（実機未確認）。フロントの型は手書き（export 258宣言/94ファイル）。型生成ツール無し。
- R4: 生select 70（関所方式60）、input 216、自作タブ31、hex 235（index.css除き56）、ui-allow 29のうち番号無し2件を確認。依頼の 74 は select の実数と一致せず（実数70）。

DONE
