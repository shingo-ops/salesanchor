# design: 決まりを機械の検査に変える（誰がやっても違反が本番に出ない）

- 親: [docs/specs/rule-enforcement/README.md](../../specs/rule-enforcement/README.md)

> この文書は何か: 決まりを台帳で仕分け、main の必須チェック・違反の見本・提出前の検査で守るための実現の設計。

- 状態: 設計案作成済み／設計審査1回目 REVISE・2回目 REVISE・3回目 REVISE・4回目 REVISE・5回目 APPROVE（指摘は反映済み §15）／PO 計画承認 済み（D1、2026-10-27 原文「1」）／main 反映 #4815（2026-10-27）／R0 完了（recon §12）／R0.5 以降は未着手
- 対象: 決まりの文書（kgi.md「範囲の確認」1 の範囲）、main の必須チェック、本番の鍵を使う GitHub の自動作業、本番の VPS と PO の Mac にある自前の実行機、提出前の検査の入口、週次点検
- KGI（PO 承認済み 2026-10-27「1」）: `docs/specs/rule-enforcement/kgi.md`
- 現在地: `docs/handoff/rule-enforcement/recon.md`（起点 origin/main df81bce7d）
- 対象 ADR: `docs/adr/ADR-136-cc-bot-github-identity.md`（Ruleset の承認数を使わず「記録＋検査スクリプト」で統制。本設計も踏襲）、`docs/adr/ADR-135-release-stowaway-prevention.md`（必須チェック登録・bypass_actors）、`docs/adr/ADR-1029-review-gate-hook.md`（マージ前審査。R3 で一部置き換える §5 R3）、`docs/adr/ADR-1040-doc-agenda-nav-entry-index.md`（段階導入）、`docs/adr/ADR-1003-go-delegation-to-opus.md`（Ruleset 変更は PO 本人）
- 先例: `docs/handoff/local-gate-ci-parity/design.md:10-11`（手元の関所は CI と同じスクリプトを「写さずに呼ぶ」。発端は `docs/handoff/local-gate-ci-parity/recon.md:4`）

## 1. 目的（PO から見える変化）

- 決まりに反した変更は、作ったのが誰（手元の Claude・クラウドの Claude・Codex・人の手）でも main に入らず、本番に出ない
- 本番の鍵は main の中身でしか使えない（main 以外の道で本番に触れない）
- 同じ検査が提出の前にも走るので、提出してから落ちて作り直す回数が減る
- 決まりを足したのに守らせ方を決め忘れる、ということが起きない

## 2. 現在地の要約（recon より）

- 本番への自動反映は main への push だけ（`.github/workflows/deploy.yml:3-6`、environment の承認者なし）。main の ruleset 15777895 の必須チェック 16 件が、全員に効く唯一の関所（recon §2, §3）
- ただし本番の鍵（secrets.VPS_HOST）を使う手動起動のワークフローが 6 本ある: `.github/workflows/line-import-operations.yml:4`、`.github/workflows/line-import-device.yml:4`、`.github/workflows/rotate-qa-firebase.yml:7`、`.github/workflows/setup-pgw.yml:7`、`.github/workflows/setup-pushgateway-once.yml:7`、`.github/workflows/verify-meta-subscriptions.yml:18`（設計審査1回目の指摘 M4）。手動起動では選んだブランチの最後のコミットが GITHUB_SHA になる（https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows 2026-10-27 閲覧）ので、main 以外のブランチの中身が鍵付きで動く前提で塞ぐ（R5）。ただし穴は手動起動だけでなく、リポジトリに置いた鍵を使う全ワークフローにある（§5 R5、設計審査2回目 must-3）
- 決まり 85 件のうち 止める 27・一部止める 11・無し 23・未確認 24（recon §4）。この数え方は人の判断を含むので、R1 で機械の数え方に置き換える
- 手元の hook は手元の Claude だけ、リポジトリの hook はクラウドの Claude だけに効く。Codex と人の手には ruleset と CI 以外は効かない（recon §0）
- マージ前の審査（ADR-1029）は hook だけで強制され、ruleset の承認数は 0。人の手のマージと GitHub 画面からのマージには効かない（recon §4 B04）。直近 30 件のマージ済み PR で `VERDICT: APPROVE on <sha> PR #n` のコメントがあったのは 3 件（#4811・#4804・#4802）、台帳の自動 DONE 化 PR 11 件は 0 件（審査1回目の実測。基準値）
- 素通りできる立場（bypass_actors）と素通りの記録（rule suites の bypass）は shingo-cc では見えない（recon §2、2026-10-27 実測 `gh api repos/shingo-ops/salesanchor/rulesets/rule-suites?rule_suite_result=bypass` → 404）
- ruleset 全体に `require_extra_approval_for_unattributed_changes: true`、必須チェック 16 件のうち 6 件は integration_id 15368（GitHub Actions）付きで登録（recon §2）

## 3. 方針

1. **最後の関所を一本にする**: 守りの本体は main の必須チェックだけ。本番の鍵も main の中身でしか使えないようにする。ほかの道具の hook は「先に知らせる」補助
2. **記録を検査で確かめる型（ADR-136 の型）**: 人の承認数を ruleset に足すのではなく、PR に残った記録を必須チェックが確かめる。GO 記録（`scripts/check-process-artifacts.js:330-385`）と同じ型。違い: GO 記録の検査は PR 側のスクリプトが `pull_request` で動く（`.github/workflows/process-artifacts-gate.yml:8-11,44`）。R3 は main 側のコードが動き、書いた名義でも絞る
3. **決まり台帳を正本にする**: 決まり 1 件 = 台帳 1 行。決まりの文書の中で決まりの語に合う行は、全部どれかの台帳項目か「決まりではない（理由）」に振り分ける（漏れを機械で数える）
4. **写さずに呼ぶ**: 提出前の検査は、必須チェックが呼ぶのと同じスクリプトを呼ぶ
5. **段階導入**: 新しい検査は警告で始め、連続 5 回の PR で誤検知 0 件なら失敗に上げる（ADR-1040:34 と同じ）
6. **変更は一度に 1 つ・1 便 1 目的**（docs/ai-agents/executor-checklist.md:7-18）

## 4. 便の分け方

| 便 | 内容 | KGI | 触る範囲 | GO 記録（Opus に委任・ADR-1003） | PO 本人の操作 |
|---|---|---|---|---|---|
| R0 | 調べの仕上げ（コード変更なし） | G1 G3 | recon.md の追記だけ | 不要 | 読み取りの台本を `!` で 1 回 |
| R0.5 | 文書の食い違い 5 件の直し | — | docs/adr/FEATURE-INDEX.md、docs/adr/ADR-144-ui-component-governance.md、ゲート 3 本の冒頭コメント | 要（必須チェックのワークフローを含む） | なし |
| R1 | 決まり台帳と台帳の検査（警告で開始）＋ ADR 起案 | G1 G5 | docs/specs/rule-enforcement/、scripts/ci/、.github/workflows/ 1 本、docs/adr/ 1 本 | 要（scripts/） | 格上げ時に必須チェック登録 |
| R2 | 違反の見本の試験（軽い検査） | G2 | scripts/tests/rule-fixtures/、台帳検査から実行 | 要（scripts/） | なし |
| R3 | マージ前審査の記録を必須チェックで確かめる | G2 G3 | .github/workflows/ 1 本、scripts/ci/ 1 本、docs/adr/ 1 本 | 要 | 必須チェック登録（integration_id 15368 付き）。登録は §5 R3 の格上げの前提 5 つがそろってから |
| R4 | 提出前に同じ検査を走らせる一本の入口 | G4 | scripts/dev/、frontend/.husky/pre-push | 要（scripts/） | なし |
| R5 | 本番の鍵を main だけにする・素通りの見張り | G3 | 本番の鍵を使う全ワークフロー（deploy.yml を含む）、PIPELINE_PAT を使うワークフロー、週次点検 | 要 | GitHub の設定（environment と鍵の移動）。§9 D2・D3 |
| R6〜 | 台帳で gate に仕分けた「無し」の決まりを 1 件ずつ検査にする | G1 G2 | 決まりごと | 決まりごと | 決まりごと |

順番の理由: 台帳（R1）が無いと「全部」を数えられず、見本（R2）が無いと「止まる」の証拠が出ない。R3 は人の手のマージ、R5 は main 以外の道という大きい穴をふさぐ。R4 は手戻り削減で守りの本体ではないので後。R5 は R0 の結果と D2 の判断を待つので R3 の後。

## 5. 各便の中身

### R0 調べの仕上げ

- 担当（Sonnet）が確定する:
  - recon §10 の未確認 1〜7、§4 の未確認 24 件（仕組みのファイル:行で。確定できないものは「無し」として守りが無い側に倒す）
  - `.codex/config.toml` の中身（Codex に効く仕組み）
  - 鍵（secrets と vars）を参照する全ワークフローの一覧と、鍵ごとの起動の種類（`grep -l 'secrets\.' .github/workflows/` を全部読む）。そこから「本番の鍵の名前の一覧」の案を作る（本番のサーバー・DB・外部サービスに届く鍵）
  - PIPELINE_PAT を使う全ワークフローと、その鍵でしている操作
  - main 以外を選んだ手動起動がどの版のワークフローで動くかの、GitHub の説明書の出典（Context7 か公式の説明書。実際に起動して試すことはしない）
  - 既定のブランチの版で動く起動（pull_request_target・issue_comment・workflow_run・schedule）の GITHUB_REF が environment のブランチ制限をどう通るか（説明書の出典）と、その起動の種類で本番の鍵を使い PR の head を checkout するワークフローの全部
  - 自前の実行機（self-hosted runner）の一覧: ラベル・置き場所（本番の VPS・PO の Mac）・そこから届く範囲・使っているワークフローと起動の種類（既知: `[self-hosted, salesanchor-vps]` を qa-smoke・monitoring-config-drift・rotate-qa-firebase・external-state-snapshot、`[self-hosted, macOS]` を hook-permission-check・reaper-schedule。origin/main 77b40a1ae の `runs-on:`: external-state-snapshot.yml:50、monitoring-config-drift.yml:21、rotate-qa-firebase.yml:12、qa-smoke.yml:58、hook-permission-check.yml:30、reaper-schedule.yml:28。設計審査4回目・5回目の実測）。実行機を使えるワークフローやブランチを絞れるか（個人名義のリポジトリで runner groups が使えるか）の説明書の出典
  - 状態を付けた順番で、同じ名前の commit status が後から付けたもので上書きされるかの説明書の出典
- PO 本人が `!` で読み取りの台本を 1 回実行する（GET のみ。Opus が台本の全文を事前に示す）:
  - main ruleset 15777895 と develop ruleset 16619490（shingo-ops 名義。bypass_actors を見る）
  - rule suites の bypass（直近 1 か月）
  - リポジトリの secrets と variables の名前の一覧（値は出ない API）
  - 既定のワークフロー権限（`actions/permissions/workflow`。shingo-cc では 403）
  - 自前の実行機の一覧と、フォークからの PR のワークフローの実行に承認が要る設定（`actions/runners`・`actions/permissions`）
  - PIPELINE_PAT の持ち主と権限の範囲（鍵の設定画面で見える範囲。値は見ない）
  - 出力は `/tmp/CC報告ファイル/an-gov/rule-enforcement/` に保存
- 成果: recon.md に §12 を追記

### R0.5 文書の食い違いの直し

- recon §9 の 5 件を直すだけの便。`.github/workflows/process-artifacts-gate.yml` を含むので GO 記録が要る（`scripts/check-process-artifacts.js:122`）

### R1 決まり台帳と台帳の検査

- 決まりの文書の一覧: `docs/specs/rule-enforcement/rule-docs.txt`（kgi.md「範囲の確認」1 で PO が確かめた一覧をそのまま書く。glob 可）
- 台帳: docs/specs/rule-enforcement/rules.yml
  ```yaml
  rules:
    - id: A07
      source: AGENTS.md
      anchor: "`develop` / `main` への直接コミット禁止"   # 出典の文書にこの文字列が残っていること
      kind: gate            # gate＝機械で止める / review＝審査役が見る / exempt＝止めない
      check: "process-artifacts gate"   # gate のとき: 必須チェックの名前
      when: ci             # gate のとき: before_submit（提出前にも分かる）/ ci（CI でだけ分かる）
      fixture: scripts/tests/rule-fixtures/A07/   # gate のとき: 違反の見本（R2）。置けない検査は evidence
      evidence: ""          # 見本を置けない gate のとき: 実際に止まった PR 番号
      reason: ""            # review / exempt のとき必須
  not_rules:              # 決まりの語に合うが決まりではない行
    - source: docs/STANDARD-WORKFLOW.md
      anchor: "…"
      reason: "例文の中の語"
  ```
- 決まりの語: `禁止|必ず|必須|厳禁|してはならない|しない|すること|MUST|NEVER` を含む行（語の一覧は台帳の先頭に置き、台帳と一緒に変える）
- 検査: scripts/ci/check_rule_registry.py（新規）。確かめること:
  1. **突き合わせ（G1）**: rule-docs.txt の全文書で決まりの語を含む行を全部挙げ、各行が `rules` のどれかの anchor を含むか、`not_rules` に登録されているかを確かめる。どちらでもない行は「未仕分け」として件数と場所を出して失敗。これで 85 件という数を人の数え方に頼らない
  2. 全項目の anchor が source に今も実在する（文言が消えた・変わったら気づく）
  3. `kind` が 3 種のどれか。gate は check・when と、fixture か evidence のどちらか。review と exempt は reason が空でない
  4. gate の check が `docs/specs/rule-enforcement/required-checks.txt`（ruleset の必須チェックの名前と integration_id の写し）にある
  5. **G5**: 1 の突き合わせは PR の版で毎回走るので、決まりの文書に決まりの行を足して台帳を変えなければ「未仕分け」で落ちる。免除行は設けない（審査1回目 S3: 自由記述の理由は抜け道になるため）。決まりの語を含まない行の変更（誤字直し）は突き合わせに影響しないので台帳は要らない
  6. 決まりの語の一覧・rule-docs.txt・rules.yml・not_rules の変更は、GO 記録の要る対象にする（`scripts/check-process-artifacts.js:115-128` の一覧に docs/specs/rule-enforcement/ の rules.yml・rule-docs.txt・required-checks.txt・prod-secrets.txt の 4 つだけを足す。README などの誤字直しには GO 記録を要らないようにする）。語を消して G5 を外す道を、記録なしでは通さない
- 限界（隠さない）: 一覧に無い言い方（「不可」「いけない」「のみ」「避ける」「don't」など）で書いた決まりは突き合わせを素通りする。R1 の初回で決まりの文書の全文から言い方を集めて語の一覧を作り、以後は審査役の確認項目に「語の一覧に無い言い方の決まりが足されていないか」を入れる
- 1 行に決まりが 2 つ以上ある・1 つの決まりが複数行にまたがるときは、台帳の項目に `anchors:`（一覧）を持たせる。1 行は 1 項目にしか属せないとし、重なりは検査で失敗にする
- ワークフロー: .github/workflows/rule-registry.yml（新規・paths なし・main 向け PR の opened／synchronize／reopened／edited）。最初は `continue-on-error`（警告）。連続 5 回の PR で誤検知 0 件なら失敗に上げ、PO が必須チェックに登録（integration_id 15368 付き）
- `required-checks.txt` と実際の ruleset の差は、同意と権限の週次点検（`docs/handoff/permission-delegation/routine.json` と `scripts/dev/consent-audit.py`）に 1 項目足して毎週比べる（ruleset は shingo-cc で読める recon §2）
- ADR を R1 で起案する（台帳を正本にすること、関所を一本にすること、R3 で ADR-1029:31,36 を置き換える予定を書く）

### R2 違反の見本の試験

- gate の各項目に「違反の見本」と「合格の見本」を 1 つずつ置き、その項目の check が呼ぶスクリプトに食べさせて、違反→失敗・合格→成功を確かめる。台帳検査（R1）が見本の試験も実行する。CI の中で動くので作った人に関係なく同じ結果になる
- 見本を置けるのは、スクリプトがあって数秒で動く検査だけ（審査1回目 確認5 の一覧: check-process-artifacts.js、check-ui-governance.js、check-dangling-routes.js、generate-adr-index.js --check、check-claude-size.js、lint_tenant_schema.py、check_doc_index.py、check-doc-heading-duplicates.sh、check-lessons-section.sh、check-migration-value-writes.py、check-migration-column-churn.js、check-migration-duplicate-registration.sh）
- 次の検査は見本を置かず `evidence: PR #<番号>`（実際に止まった PR）で代える: ワークフローに直書きの検査（`.github/workflows/migration-guard.yml:95-111,113-,171-189,343-389`、`.github/workflows/lessons-guard.yml:24-29`、`.github/workflows/api-contract-check.yml:50-55`）、外部の部品（secret-scan）、実 DB や node_modules が要る検査（pytest・schema-check・migration-test・`npm run check:all`）。止まった実例が無い項目は、R2 の中で試しの PR を作って止まることを確かめ、その番号を書く
- 経路ごとの試し（G2）: 違反を 1 つ入れた試しの PR を、①手元の Claude ②クラウドの Claude ③PO 名義の台本（人の手の代わり）④Codex（R0 で使っていると確かめられた場合。使っていなければ「未使用」と記録）から出し、全部 BLOCKED を確かめて閉じる

### R3 マージ前審査の記録を必須チェックで確かめる

- 今: マージ前の審査役 APPROVE は hook だけで強制（ADR-1029）。人の手・GitHub 画面のマージには効かない
- 変更: 必須チェック「review verdict」を足す。PR のコメントに `VERDICT: APPROVE on <PR の HEAD の SHA 40 桁> PR #<番号>` があるかを確かめ、HEAD のコミットに状態を付ける
- 安全の条件（リポジトリは PUBLIC でフォーク可。審査1回目 S1）:
  - 起動は `pull_request_target`（opened／synchronize／reopened）と `issue_comment`（created・edited）
  - PR の head を checkout しない。main 側のスクリプトだけを動かす
  - コメント本文や PR の題名を `${{ }}` で `run:` に埋め込まない（環境変数で渡す）
  - 権限は `statuses: write` と `pull-requests: read` だけ
  - 書いた名義の login が shingo-cc か shingo-ops のコメントだけを数える
  - issue_comment の経路では `github.event.issue.pull_request` があることを確かめ、PR を API で引いて head の SHA を得る。実行中に head が変わったら書かない（`scripts/run-guard-evaluation.js:37-39` の型）
  - 手本の `scripts/run-guard-evaluation.js` は pull_request_target 専用（:46）なので流用せず、新しいスクリプト scripts/ci/check_review_verdict.py を作る
- 必須チェックへの登録は integration_id 15368 付き（審査1回目 M6。外の鍵から同じ名前の状態を付けても数えられない）
- 対象外にする PR: 台帳の自動 DONE 化（`.github/workflows/ledger-auto-done-main.yml:138,151` が PIPELINE_PAT で作り `gh pr merge --auto` でマージ。作者は shingo-ops）。判定は新しく書かず、正本の `scripts/ci/is-ledger-done-pr.sh`（4 条件は :7-11、判定は :69-73）を呼ぶ。呼ぶ側の一覧に review-verdict を足す。一つでも外れれば対象。PIPELINE_PAT を使えば同じ形の PR を作れるが、それができるのはブランチに push できる人＝ VERDICT の行を自分で書ける人と同じ範囲なので、R3 にとって新しい穴にはならない（限界の 1 つ目と同じ）。PIPELINE_PAT は G3 の側（R5・D3）で扱い、R3 の格上げは D3 に依存しない
- 作業の流れの変化（手間は増える）: 今は VERDICT のコメントを書くのは 30 件中 3 件（§2）。R3 の後は、マージ前に審査役の最後の行（`VERDICT: APPROVE on <sha40> PR #<番号>`）を、Opus が「確認済み」コメントにそのまま書く。書かなければマージできない
- 限界（隠さない）:
  - 書き込み権限のある名義なら、その 1 行を書ける。検査は「審査の記録が無いまま入る」ことを止めるが、偽の記録は止めない
  - 後から必ず見つける仕組み（偽装の道に関係なく効く）: 週次点検で「先週 main に入った全 PR（台帳 PR は `scripts/ci/is-ledger-done-pr.sh` で除く）に、その PR の最後の HEAD の SHA に合う VERDICT コメントがあるか」と「その VERDICT に review-gate の記録（`~/.claude/review-gate/records/`、ADR-1029:17）か、審査の全文のコメント（クラウドの審査役は全文を PR のコメントに残す）があるか」を数え、0 件でなければ知らせる
  - 状態の偽装（PR 側のワークフローが「review verdict」を合格にする）: 必須チェックは integration_id 15368（GitHub Actions）で登録するので、同じリポジトリの PR で動くワークフローが付けた状態とは区別できない。必須チェックの名前は commit status とジョブ名（check run）のどちらでも満たせる（https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches 2026-10-27 閲覧）。道は 2 つ:
    - (a) GITHUB_TOKEN で statuses API を呼ぶ: 書き込み権限が要る。pull_request で動き `permissions:` を書いていないワークフローが 28〜41 本ある（ファイルの先頭に無いもの 41 本、どのジョブにも無いもの約 30 本。設計審査3回目・4回目の実測）。既定の権限が書き込みなら、その手順を書き換えるだけで付けられる。既定の権限は shingo-cc で読めない（`gh api repos/shingo-ops/salesanchor/actions/permissions/workflow` → 403）。R0 で PO が読み、書き込みなら「既定を読み取りに変える」ことを R3 の格上げの前提にする（PO の操作。§9 D4）。補助として、review-verdict（main 側のコード）が PR の差分のワークフローを YAML として読み、`statuses: write`・`checks: write`・`write-all` を新しく与えたら失敗にする（文字列の一致は `value-write-allowlist` のような名前にも当たるので使わない）。これだけでは閉じない: PR に含まれない別のブランチに push で動くワークフローを置けば、PR の HEAD の SHA に状態を付けられ、差分には出ない。同じ名前の状態は後から付けたものが効く可能性がある（【未確認】R0 で説明書の出典を取る）。書き込みのできる名義なら状態を付けられることは、素通りの道として D2 で PO に見せる。より強い代わりの案は §8
    - (b) ジョブの名前を「review verdict」にしただけのジョブ: 書き込み権限が要らない。同じ名前が複数あると「ambiguous」になると説明書にあるが、合格と数えられるか止まるかは【未確認】。R3 の中で試しの PR で確かめ、合格と数えられるなら review-verdict が PR の差分のワークフローに同じジョブ名があれば失敗にする
    - どちらの道でも、上の週次点検（全 PR に合う VERDICT があるか）が後から見つける
- 先例: 既存の必須チェック `guard-authoring/evaluation` は pull_request_target の GITHUB_TOKEN で付けた状態を integration_id 15368 で登録して動いている（recon §2、ruleset 15777895 の読み取り結果）。R3 の作りはこれと同じ
- ADR: R3 の前に ADR を出し、ADR-1029:31（画面からのマージ・自動マージは対象外）と :36（Ruleset は変えない）を置き換える。緊急時（ADR-136 の break-glass）は審査なしのマージができなくなるので、§9 D2 の素通りの扱いと合わせて決める
- R3 を必須チェックに上げる前提（全部そろってから PO が登録する）: ①D4（既定の権限が書き込みなら読み取りに変えた） ②(b) の試しの結果と、それに応じた検査 ③ADR の置き換えがマージ済み ④D2（緊急時の扱い）が決まった ⑤連続 5 回の PR で誤検知 0 件

### R4 提出前に同じ検査を走らせる一本の入口

- scripts/dev/check-before-submit.sh（新規）: 変更ファイルから、必須チェックと同じ条件（recon §3 の「動く条件」）で該当する検査スクリプトを選んで呼ぶ。呼ぶのは CI と同じスクリプト（写さない）。台帳の `when: before_submit` の項目が対象。どれを呼んだか・飛ばしたか（「CI で確かめる」）を全部表示する
- 呼び出し元:
  - 手元の Claude: `scripts/dev/validate-pr-body.sh` の最後の成功表示（:321）の前で呼ぶ（:322 は `exit 0`）。影響範囲: `scripts/gh-pr-create-safe.sh:132`、`scripts/tests/test-pr-lifecycle.py:156`（スクリプトを写して試験する）
  - 人の手と Codex: `frontend/.husky/pre-push` から呼ぶ（`--no-verify` で外せるが、外しても最後の関所で止まる）
  - クラウドの Claude: `.claude/settings.json:79` の hook は 10 秒で打ち切り・失敗で止める設定なので、重い検査を直接呼ばない。hook は `gh pr create` と `mcp__github__` の PR 作成の前に「scripts/dev/check-before-submit.sh を先に流したか」を確かめるだけにする（実際の入口は `.claude/settings.json:79` から呼ばれる `scripts/agent-hooks/cloud/dispatch.sh`。流した印は作業場所の `.git/` の中の `check-before-submit.ok`（`.git/` の中なのでコミットされず .gitignore も要らない）。中身は流した時点の HEAD の SHA で、PR を作る時点の HEAD と違えば止める）
- 実行環境が足りない検査は「手元では飛ばした・CI で確かめる」と表示して通す（黙って通さない）

### R5 本番の鍵を main だけにする・素通りの見張り

- 穴の形: リポジトリに置いた鍵は、どのブランチの、どの起動の種類（push・pull_request・手動起動）のワークフローにも渡る。手動起動 6 本だけの話ではない（例: `.github/workflows/external-state-snapshot.yml` の手動起動、`.github/workflows/qa-smoke.yml` の pull_request、`.github/workflows/test-phase2-rehearsal.yml` の feature ブランチへの push。設計審査2回目の実測）。environment の鍵はその environment を参照するジョブにだけ渡り、ブランチの制限は実行の GITHUB_REF で照合される（https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment 2026-10-27 閲覧）。いま environment は `github-pages` の 1 つだけ
- 手順:
  1. R0 で「本番の鍵の名前の一覧」を確定し、PO が承認する（`docs/specs/rule-enforcement/prod-secrets.txt`。名前だけで値は書かない）
  2. その一覧の鍵を environment「production」（main だけ）に移す。設定は PO 本人の操作。参照する全ワークフロー（deploy.yml を含む）に `environment: production` を足す。deploy.yml は GO 記録の要る対象（`scripts/check-process-artifacts.js:119`）
  3. 1 本ずつ移し、移した直後に main から 1 回動かして確かめる
- main 以外で正当に鍵を使う作業: R0 の一覧に鍵ごとに「main 以外の起動（pull_request・feature ブランチへの push など）で使っているか」を付ける（例: `qa-smoke.yml:42,64`、`test-phase2-rehearsal.yml:15,38`）。当たった鍵は、①起動の種類を変える ②本番の鍵の一覧から外す（PO 承認）③作業をやめる、のどれにするかを §9 D5 で PO が決める。鍵をリポジトリに戻す戻し方は G3 を × にするので、戻したら週次点検で知らせる
- 既定のブランチの版で動く起動（pull_request_target・issue_comment・workflow_run・schedule）は GITHUB_REF が既定のブランチになり、「main だけ」の制限を通る（【未確認】説明書で R0 に確かめる）。中身は main のワークフローなので「main の中身でしか使えない」は保たれるが、PR の head を checkout して鍵付きで動かすものがあれば穴になる。R0 で「この起動の種類で本番の鍵を使い、PR の head を checkout するもの」を全部挙げる
- 自前の実行機（self-hosted runner）: 本番の VPS 上の実行機 `[self-hosted, salesanchor-vps]` は qa-smoke（pull_request で動く。冒頭のコメントに本番 DB・本番 API・本番 Firebase に直接届くためとある）ほか 3 本が使い、PO の Mac 上の実行機 `[self-hosted, macOS]` は hook-permission-check・reaper-schedule が push と pull_request で使う。どのブランチのワークフローでも `runs-on:` にそのラベルを書けば、鍵が無くても本番のホストや PO の Mac で任意の手順を動かせるので、鍵を environment に移しても塞がらない（monitoring-config-drift.yml:4 は鍵を使わないと書いている）。リポジトリは公開でフォークできるので、書き込み権限の無い外の人がフォークから出した PR でも、pull_request で実行機を使うワークフロー（qa-smoke・hook-permission-check）が動けば届く（【推測】フォークからの PR の実行に承認が要る設定かどうかで変わる。設定は R0 の PO の台本で読む）。扱い（実行機を使えるワークフローやブランチを絞る・pull_request で使わない・実行機をやめて鍵付きの GitHub の実行機に替える）は R0 の結果を見て §9 D6 で決める。実行機を絞る runner groups は説明書で組織の設定として書かれている（https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/managing-access-to-self-hosted-runners-using-groups 2026-10-27 閲覧）。個人名義のリポジトリで使えるかは【未確認】（R0）
- PIPELINE_PAT（shingo-ops 名義・admin の鍵。持ち主は `scripts/ci/is-ledger-done-pr.sh:21`）: 8 本のワークフローが `secrets.PIPELINE_PAT` を参照し（active-work-auto-done・active-work-auto-review・auto-merge-guard・deploy・external-state-snapshot・ledger-auto-done-main・ledger-done-update-branch・monthly-secret-expiry）、pull_request で起動するものもある。どのブランチのワークフローからでも shingo-ops 名義で admin の操作ができるので、G3 の穴になる。main 限定の environment に単純に移すと、pull_request の closed で動く ledger-auto-done-main（GITHUB_REF は refs/pull/N/merge）が止まる。扱い（権限を絞った別の鍵・別の名義・起動の種類を変える）は R0 で使い方を全部確かめてから §9 D3 で決める。別の鍵にするなら deploy.yml の PIPELINE_PAT の 3 か所（起点 df81bce7d で :64、:916-917、:1042。origin/main 77b40a1ae では :922-923、:1048 にずれている。R5 の着手時に数え直す）も書き換える
- 素通りの立場は R0 の結果と §9 D2 で決める
- 週次点検に足す: 先週、決まりを素通りした取り込みが 0 件か（rule suites の bypass。admin 名義でしか読めないので、shingo-ops 名義の読み取り専用の鍵を用意できるかを R0 で確かめる。用意できなければ PO の月 1 回の `!` 実行で代える）／ruleset と required-checks.txt の差／VERDICT の突き合わせ

### R6〜 「無し」の決まりを検査にする

- R1 の台帳で gate に仕分けた「無し」の決まりを、影響の大きい順に 1 便 1 件で検査にする。順番と件数は R1 の台帳ができてから PO に見せて決める

## 6. 決まりの仕分けの基準（R1 で全件に当てる）

| 区分 | 条件 | 例 |
|---|---|---|
| gate（機械で止める） | 変更の中身（ファイル・差分・PR 本文・コメント）だけで○×が決まる | 日本語のハードコード、migration のファイル名、doc の目次登録 |
| review（審査役が見る） | 判断が要るが PR の中で確かめられる | 1 便 1 目的、設計が最終形の全文か |
| exempt（止めない） | PR に痕跡が残らない行い、または本番に出ない | 「迷ったら止まる」、作業前に preflight を叩く、develop の扱い |

exempt の決まりで手元の hook が守っているもの（例: 不可逆操作の確認 A02）は、hook を残したまま exempt（理由: PR の外の操作）と書く。

## 7. 影響範囲

- 新規: docs/specs/rule-enforcement/ の rules.yml・`rule-docs.txt`・`required-checks.txt`、scripts/ci/check_rule_registry.py、scripts/ci/check_review_verdict.py、`scripts/tests/rule-fixtures/`、.github/workflows/rule-registry.yml・review-verdict.yml、scripts/dev/check-before-submit.sh、`docs/specs/rule-enforcement/prod-secrets.txt`、ADR 1〜2 本
- 変更: `scripts/dev/validate-pr-body.sh`（呼び出し）、`frontend/.husky/pre-push`（呼び出し）、`scripts/agent-hooks/cloud/dispatch.sh`（クラウドの hook。確かめるだけ）、`scripts/check-process-artifacts.js:115-128`（GO 記録の要る対象に docs/specs/rule-enforcement/ の rules.yml・rule-docs.txt・required-checks.txt・prod-secrets.txt の 4 つを足す）、`scripts/ci/is-ledger-done-pr.sh` の呼ぶ側の一覧、`docs/handoff/permission-delegation/routine.json`・`scripts/dev/consent-audit.py`（週次点検の項目）、本番の鍵を使う全ワークフロー（deploy.yml を含む。`environment:` の 1 行）、PIPELINE_PAT を使うワークフロー（D3 次第）、recon §9 の文書 5 件（R0.5）
- 呼び出し元の確認: `scripts/gh-pr-create-safe.sh:132`、`scripts/tests/test-pr-lifecycle.py:156`、`.github/workflows/ledger-auto-done-main.yml:138,151`、`.github/workflows/auto-merge-guard.yml:15-16,31`
- 触らない: 既存の必須チェック 16 件の中身、ruleset の承認数（ADR-136）、deploy.yml の手順の中身（足すのは `environment:` の 1 行。D3 で PIPELINE_PAT を別の鍵にするときだけ、その鍵の名前の差し替え 3 か所）、製品コード（backend/・frontend/src/）、`.github/workflows/workflow-lint.yml`
- 全 PR に必須チェックが 2 本増える（rule registry・review verdict）。所要時間は R1・R3 で実測する

## 8. 代替案と選ばなかった理由

| 案 | 選ばなかった理由 |
|---|---|
| ruleset の承認数を 1 にする | ADR-136:104-110 で 2026-06-13 に不採用と決定済み（2 人体制の摩擦）。本設計は決定を変えない |
| 作業前に決まりを「読んだ印」を要求する hook | 読んだかは判定できても、守ったかは判定できない。しかも手元の Claude にしか効かない（recon §0） |
| 本番に出す直前（deploy.yml）にもう一度検査 | main に入った時点で必須チェックを通っている。同じ検査の二重化になる |
| 決まりの文書から命令文を機械で抜き出し、決まりかどうかを機械に判定させる | 日本語の命令文の判定が不安定。本設計は「決まりの語に合う行を全部挙げ、人が台帳か not_rules のどちらかに振り分ける」方式で、判定は人、漏れの検出は機械に分けた（R1-1） |
| review verdict を GitHub Actions（integration_id 15368）で登録する代わりに、専用の GitHub App の名義で状態を付け、その App の integration_id で登録する | PR 側のワークフローからは偽装できなくなり最も強い。ただし App の作成・鍵の保管・PO の設定操作が増える。R3 の (a)(b) の結果と D4 の後に、まだ偽装の道が残るなら採る（R3 の中で PO に出す） |
| G5 の免除を PR 本文の 1 行で認める | 理由に何を書いても通るので抜け道になる（審査1回目 S3） |

## 9. 決めてほしいこと（PO）

- D0（決定済み 2026-10-27 PO 原文「1」＝範囲を広げる）: kgi.md「範囲の確認」の 2 点（決まりの文書の範囲・素通りの範囲を main 以外の道に広げる）
- D1（決定済み 2026-10-27 PO 原文「1」＝R0 に進む）: この計画で R0 から進めてよいか
- D2（R0 の後）: 素通りできる立場が見つかったとき、①無くす ②本番障害の復旧用に残し、使ったら知らせる、のどちらにするか。リポジトリに書き込みのできる名義（人も自動作業の鍵も）は、別のブランチの自動作業から審査の印を付けられるので、これも素通りの道として一覧に入れて見せる（§5 R3 (a)）（ADR-135:65 は「残す」と記載。R3 の後は審査なしの緊急マージにも関わる）
- D3（R0 の後）: PIPELINE_PAT（PO 名義・admin の鍵）の扱い。R0 で使い道を全部確かめ、権限を絞った別の鍵・別の名義・起動の種類を変える、の案を示して決める
- D4（R0 の後・既定のワークフロー権限が書き込みだった場合だけ）: 既定を読み取りに変えるか（PO の設定操作。書き込みが要るワークフローに `permissions:` を書き足す便が先に要る）
- D5（R0 の後）: main 以外の起動で使っている本番の鍵の扱い（§5 R5）
- D6（R0 の後）: 本番の VPS と PO の Mac にある自前の実行機の扱い。フォークからの PR の道も含む（§5 R5）

## 10. リスクと対処

| リスク | 対処 |
|---|---|
| 新しい必須チェックの誤検知で、正しい変更が止まる | 警告で始め、連続 5 回の PR で誤検知 0 件なら格上げ（§3-5）。止まったら理由と直し方を表示 |
| 突き合わせで「決まりの語」に合う行が多く、仕分けの手間が大きい | R1 の初回で件数を実測して PO に見せる。not_rules は語の位置（例文・引用）でまとめて登録できる形にする |
| 台帳の anchor が文書の言い回し変更で切れる | 失敗文に直す場所を出す |
| review verdict の偽の記録・状態の偽装 | §5 R3 の限界のとおり。週次点検で main に入った全 PR に合う VERDICT があるかを数える |
| 台帳の自動 DONE 化 PR が review verdict で止まる | §5 R3 の対象外の条件（正本 `scripts/ci/is-ledger-done-pr.sh` の 4 条件） |
| 見本が古くなり、検査を弱めても見本が通ってしまう | 見本は「違反→失敗」を確かめるので、検査を弱めると見本の試験が落ちる |
| 提出前の検査が遅くて外される | 外しても最後の関所で止まる。R4 で所要時間を測り、遅い検査は「CI で確かめる」に回す |
| ruleset の写しが実物とずれる | 週次点検で毎週比べる |
| 本番の鍵を environment に移すとき、使っている自動作業が止まる | 1 本ずつ移し、移した直後に main から 1 回動かして確かめる。戻し方は鍵をリポジトリに戻し `environment:` の行を消す |

## 11. 受入条件

| 基準 | 検証方法 |
|---|---|
| G1 未仕分け 0 件 | `python3 scripts/ci/check_rule_registry.py` が決まりの文書の決まりの語を含む全行を数え、「未仕分け 0」を表示して exit 0 |
| G1 台帳が文書と一致 | 試しに AGENTS.md の 1 決まりの文言を消した変更で、台帳検査が「anchor が見つからない」で失敗 |
| G2 見本で止まる | gate で fixture を持つ全項目で「違反の見本→失敗」「合格の見本→成功」。件数を CI のログに表示し、失敗 0 |
| G2 見本を置けない検査 | evidence の全項目に、実際に止まった PR 番号があり、その PR のチェックの結果が failure |
| G2 経路に関係なく止まる | 試しの PR（手元の Claude・クラウドの Claude・PO 名義・Codex は使っていれば）が全部 BLOCKED。PR 番号と状態を記録 |
| G2 審査の記録なしで入らない | VERDICT の無い試しの PR が「review verdict」失敗で BLOCKED。HEAD を進めると古い VERDICT では失敗に戻る。台帳の自動 DONE 化 PR は通る |
| G3 素通りの立場 | R0 で取った bypass_actors の一覧が、D2 で PO が承認した一覧と同じ。週次点検に素通り件数の行が出る |
| G3 main 以外の道 | PO が承認した `docs/specs/rule-enforcement/prod-secrets.txt` の名前が、リポジトリの secrets の名前一覧に 0 件、environment production にだけある。production のブランチ制限は main だけ（どちらも設定の読み取り結果）。main 以外から起動した試しで鍵が渡らない |
| G3 自前の実行機 | R0 で取った自前の実行機の一覧と、使っているワークフロー・起動の種類が、D6 で PO が決めた形になっている（設定の読み取りと `runs-on:` の数え上げ）。フォークからの PR の実行に承認が要る設定になっているか、pull_request で実行機を使うワークフローが 0 本。D6 で「main 以外から使えない」と決めたなら、main 以外から起動した試しで実行機に届かない |
| G3 PO 名義の鍵 | PIPELINE_PAT が D3 で決めた形になっている（鍵の置き場所と範囲の読み取り結果） |
| G4 提出前に分かる | §5 R2 の「見本を置ける検査」を check にする gate 項目は全部 `when: before_submit`（台帳検査が確かめる。空で合格にしない）。その全項目で、違反の見本を入れた変更に scripts/dev/check-before-submit.sh が失敗し、呼んだ検査の名前を表示 |
| G5 決まりを足すと仕分けが要る | AGENTS.md に決まりの語を含む行を 1 行足し台帳を変えない試しの PR が、台帳検査で失敗（格上げ後は BLOCKED） |
| 既存の動きを壊さない | 既存の必須チェック 16 件が、本テーマの PR で全部 pass |

## 12. 外部・過去事例の参照と我々への応用

外部の数値事例は使わない。理由: 本設計の判断（関所を一本にする、記録を検査で確かめる）は GitHub の仕組みの事実と社内の過去の事実で決まり、外部の数値が判断を変えない。社内の事例:
- PR #2063（2026-06-12）: 承認数 0 のため承認なしでマージできた（ADR-136:84-91）→ 人の承認ではなく記録を検査で確かめる型を選んだ
- ADR-1040 の段階導入（警告→連続 5 回の PR で 0 件なら失敗）は、doc index reachability で 2026-10-27 に必須へ上げるまで誤検知なく動いた
- local-gate-ci-parity: 手元用に検査を書き写していたため CI に追いつかず PR #3861 が CI で落ちた（`docs/handoff/local-gate-ci-parity/recon.md:4`、`docs/handoff/local-gate-ci-parity/design.md:47`）→ 写さずに呼ぶ

## 13. 維持の仕組み

- 守り手: 人手で守る（理由: 守る機械＝台帳検査 .github/workflows/rule-registry.yml・.github/workflows/review-verdict.yml・週次点検の項目は R1・R3・R5 で作る。できた便から、この行をその機械の名前に書き換える）
- 決まりを足す PR で仕分けを書くのは、その PR の作者。台帳検査（R1 以後）が書き忘れを止める
- 3 段階の振り分け: 「何を守るか」は ADR（R1 で起案）に、手順は本 design と台帳に、日々の状態は週次点検の記録に残す

## 14. 設計審査

- 1回目（reviewer・model opus・2026-10-27）: REVISE。must 6・should 9・nit 3。反映は §15
- 2回目（reviewer・model opus・2026-10-27）: REVISE。M1・M2・M5 解消。新 must 5・should 5・nit 3。反映は §15 の後半
- 3回目（reviewer・model opus・2026-10-27）: REVISE。2回目の must-1〜4 解消。must-A（状態の偽装）・should 4・nit 5。反映は §15 の末尾
- 4回目（reviewer・model opus・2026-10-27）: REVISE。3回目の指摘は全部解消。must-B（自前の実行機）・should 2・nit 4。反映は §15 の 4回目の 4 行
- 5回目（reviewer・model opus・2026-10-27）: APPROVE。4回目の指摘は全部解消。should-C・should-D・nit 2 は反映済み（§15 の最後の 3 行）
- 手元の検査（担当・2026-10-27）: 見出し重複 exit 0。doc index は未追跡のため BROKEN_LINK 1 件、一時 index に足すと 0 件 exit 0。process-artifacts は本文に触るファイルと対象 ADR を書くと exit 0。file:line 参照 113 件で行ずれ 3 件 → 直した

## 15. 審査1回目の指摘と反映

| 指摘 | 反映 |
|---|---|
| M1 process-artifacts gate で落ちる | 見出しを §12 の形に。recon の /tmp のパス・裸のファイル名・glob を file:line と読まれない書き方に |
| M2 doc index で落ちる・3 ファイル構成 | docs/specs/rule-enforcement/ に README.md・ideal-state.md を作り、docs/specs/README.md に 1 行 |
| M3 台帳の自動 DONE 化が止まる・「手間は増えない」 | §5 R3 に対象外の条件と基準値 3/30、手間が増えることを明記 |
| M4 main 以外の道 | §2 に 6 本、R0 で全部確定、R5 で environment に移す。G3 の範囲は kgi.md で PO 確認待ち |
| M5 G1 が判定できない | R1-1 の突き合わせ。決まりの文書の範囲は kgi.md で PO 確認待ち |
| M6 状態の偽装 | integration_id 15368 付きで登録。残りの穴は R1-6 で止める |
| S1 安全条件 | §5 R3 の安全の条件 |
| S2 ADR-1029 の置き換え・緊急時 | §5 R3 の ADR と D2 |
| S3 免除行・起動の種類・範囲 | 免除行を廃止、edited を足す、rule-docs.txt から読む |
| S4 同梱 | R0.5 に分けた |
| S5 R4 の実行のしかた | クラウドは「流したか」だけ確かめる。影響範囲を足す。when 列 |
| S6 GO 記録 | §4 の列 |
| S7 維持の仕組み・親子リンク | §13 の形、冒頭の親リンクと 1 行、「対象」行 |
| S8 週次点検の名指し・クラウドの審査記録 | §5 R1・R3 |
| S9 重い検査の見本 | §5 R2 で evidence に回す |
| N1〜N3 | 言い方を揃え、required-checks.txt に integration_id、recon §2 に追記 |
| 2回目 must-1 台帳 PR の作者 | 正本 `scripts/ci/is-ledger-done-pr.sh` を呼ぶ（§5 R3） |
| 2回目 must-2 deploy.yml | 範囲に入れた（§4 R5・§7・README） |
| 2回目 must-3 鍵の範囲 | 本番の鍵の名前の一覧を R0 で確定・PO 承認、G3 をその一覧で判定（§5 R5・§11） |
| 2回目 must-4 PIPELINE_PAT | R0 で使い道を確定、D3 で決める（R3 の格上げとは切り離した。3回目 should-1） |
| 2回目 must-5 状態の偽装 | 名前で探す方法をやめ、review-verdict（main 側）が書き込み権限の追加を止める。既定の権限は R0 で PO が読む。先例 guard-authoring/evaluation |
| 2回目 should-1〜5 | anchors の一覧・重なり禁止／語の一覧を GO 記録対象・限界を明記／G4 を空で合格にしない／R0 の台本に 3 項目／dispatch.sh と流した印の置き場 |
| 2回目 nit | 先例の行を引用、手動起動の GITHUB_SHA を説明書どおりに、状態の欄を更新 |
| 3回目 must-A 状態の偽装 | 道を 2 つに分けて書いた（§5 R3）。(a) は既定の権限を R0 で読み D4、(b) は未確認として R3 で試す。週次点検を「全 PR に合う VERDICT」に変え、偽装の道に関係なく後から見つける |
| 3回目 should-1 R3 と D3 | R3 の格上げは D3 に依存しない。PIPELINE_PAT は G3 側で扱う |
| 3回目 should-2 main 以外の正当な使い道 | R0 で鍵ごとに印を付け D5 で決める。既定のブランチの版で動く起動の確認を R0 に |
| 3回目 should-3 deploy.yml | D3 次第で鍵の名前の差し替え 3 か所を明記 |
| 3回目 should-4 GO 記録の範囲 | 4 ファイルに絞った |
| 3回目 nit-1〜5 | 行番号・4 条件・8 本・YAML で読むを直した |
| 4回目 must-B 自前の実行機 | R0 に一覧と「絞れるか」の出典、R5 に段落、§9 D6、§11 に「G3 自前の実行機」の行 |
| 4回目 should-A (a) は差分検査で閉じない | 差分検査を「補助」とし、別ブランチの push・上書きの限界を書いた。D2 で PO に見せる。専用の GitHub App の案を §8 に |
| 4回目 should-B 格上げの前提 | R3 の節の最後に前提 5 つを並べ、§4 の R3 行にも書いた |
| 4回目 nit-1〜4 | 2回目 must-4 の行・既定のブランチの版の確認を R0 に・状態の欄・28〜41 本の数え方 |
| 5回目 should-C 実行機が範囲の文に無い | kgi.md「PO 確認待ち」2 と、design・README の「対象」に足した |
| 5回目 should-D フォークからの道 | R5 の段落・D6・§11 の「G3 自前の実行機」に足した |
| 5回目 nit-5・nit-6 | deploy.yml の行のずれを注記、実行機の file:line を R0 に |

## R6a 本人 GO が要る PR の見分けを強くする（設計・2026-10-27）

### PO の決定
- 2026-10-27 PO「3」: 本人の許可は今のまま AI がチャットの許可を書き写す形とし、見分けの見落としだけを塞ぐ（鍵を外す案・GitHub 上で本人が承認する案は採らない）。
- このため、本人性そのもの（記録を書いたのが本当に PO か）は機械では確かめない。残る弱点として記録する。

### 目的
ADR-1003 の例外のうち、PR の差分で確かめられるもの（表や列を消す migration・大量削除・workflow-lint.yml の変更）を、書き方の違いで見落とさないようにする。

### 変更前（origin/main 0c23808 時点の事実）
- 見分けは scripts/check-process-artifacts.js の requiresPoOnlyGo（84 行）。
  - migration: migrations/ の追加行を 1 行ずつ DROP TABLE / DROP COLUMN の形に当てる。
  - workflow-lint.yml: パスの完全一致 1 本。
- 大量削除は見ていない（ADR-1003:45 も機械では見ないと明記）。
- GO発行者欄は shingo-ops / Shingo を「含む」かで判定するため、委任名義の文に PO の名前が混ざると本人扱いになる。
- 試験 scripts/tests/test-process-artifacts.js（133 件）は本物の git の差分で DROP を試す件が 0。

### 変更後
1. 対象の場所: migrations/ に加え、deploy.yml の db_migrations と同じ範囲（scripts/migrate_*.py・scripts/run_all_migrations.sh）。
2. migration の見分け: ファイルの追加行をつなげ、SQL のコメントを除き、空白と改行を 1 つにまとめてから当てる。当てる形:
   - 表や列を消す: DROP TABLE・DROP COLUMN・DROP SCHEMA・DROP DATABASE（DROP SCHEMA / DATABASE は表ごと消えるため DROP TABLE と同じ扱い）
   - 大量削除: TRUNCATE、WHERE の無い DELETE
   - WHERE のある DELETE・UPDATE は「大量」の線引きが ADR に無いため対象外（記録のみ・人の目）
3. workflow-lint.yml: パスを小文字にし、先頭の ./ を除き、.yml / .yaml の両方で .github/workflows/workflow-lint を当てる。
4. GO発行者欄: 委任名義の語（委任・Opus・代理）が入っていれば、PO の名前を含んでいても本人扱いにしない。
5. 差分が取れないときは今と同じく「本人の GO が要る」側に倒す。

### 対象外
- 本人性の機械での確認（PO 決定により採らない）
- 試験を CI で毎回動かすこと（今は CI から呼ばれていない。別の便）
- ruleset・外部 GUI・force push（PR の差分に出ない）
- ADR-1003 の文言の変更

### 影響
- 過去 180 日の migration 130 ファイルに当てた実測（R6b で測り直し）: 当たるファイルは 37。TRUNCATE の文として当たるファイルは 0（TRUNCATE の語を含む 4 ファイル（.sql 3・.py 1）は権限の取り消しや説明文だけ）、WHERE の無い DELETE も 0。この便の後は、これらの PR に PO 本人の GO の書き写しが要る（今もの DROP TABLE / COLUMN は同じ）。
- GO発行者欄の過去の書き方（「Shingo（shingo-ops）」「Shingo（PO）」など）は引き続き通る。

### 受入条件
- K1 試験が全件合格し、追加した試験が本物の git の差分で、上の 2〜4 の各形を ○（見分ける）と ×（見分けない）の両方で試している
- K2 既存の 133 件が合格のまま
- K3 この PR 自身の process-artifacts gate が緑

### 戻し方
merge commit の revert。

## R6b 本人 GO が要る変更の見分けの残り（設計・2026-10-27）

### 前提
- R6a の審査で should 3 件・nit 3 件が出た。見逃す書き方の具体例は公開しないため、種類の名前だけを書く。
- PO 決定「3」（本人性の機械確認は採らない）は変えない。

### 目的
R6a の見分けに残った見逃し 3 種類（コメントの誤認・文の始まりの狭さ・列を消す略記）をふさぎ、R6a で生じた後退を 0 にする。普通の変更を誤って止めない。

### 変更後
1. コメントの扱い: `.sql` は引用符の中の行コメント・ブロックコメントの始まりをコメントと見なさない切り方でコメントを除いてから当てる。閉じの無いブロックコメントはコメントとして扱わない。`.sql` 以外は、素の文とコメントを除いた文の両方に当て、どちらかで当たれば検出する。
   - 改訂の理由: 最初の案（素の文とコメントを除いた文の両方に当てる）は、130 ファイル中 24 件をコメントの中の語だけで新たに止め、コメントだけの記述を止めない既存の × 試験 2 件を ○ に変えたため、実測で改めた。
2. 文の始まりの範囲: 手続きのかたまりの中・前置きの句の後ろも文の始まりとして扱う。WHERE の有無は、かっこの外にある WHERE だけで判断する。
3. 列を消す略記: COLUMN を省いた列の削除も当てる。制約・既定値・NOT NULL など列以外を消す形は当てない。
4. GO発行者欄のエラー文: 本人 GO が要る PR で委任語により止めたとき、本人の発言を書き写した注記は別の欄に書くことが分かる文にする。

### 対象外
- ADR-1003 の説明文の更新（ADR の文言変更は PO 確認の要否が未確認のため別に扱う）
- 試験を GitHub で毎回動かすこと（別の便）

### 受入条件と結果
- K1 試験が全件合格（210 件）。追加の試験が 1〜3 の各形を ○ と × の両方で、本物の git の差分で試している
- K2 審査の手元の見本のうち R6a が見逃した 8 件がすべて検出になる（実測: 8 件すべて検出）
- K3 130 ファイルに R6a と新しい判定を当て、新しく当たるファイルは 0 件（どちらも 37 件で同じ）。制約・索引・既定値だけを消すファイルは当たらない
- K4 process-artifacts gate が緑

### 戻し方
merge commit の revert。

## R6c 本人 GO が要る変更の見分けの残り（設計・2026-10-28）

### 前提
- R6b（2026-10-28 本番）の 2 回の審査で、見逃し 9 種類と誤検知 2 種類が出た。見逃す書き方の具体例は公開しないため、種類の名前だけを書く。
- PO 決定「3」（本人性の機械確認は採らない）は変えない。2026-10-28 PO「1」でこの作業を選んだ。

### 目的
本人 GO が要る変更（表・列の削除、大量削除）を、審査で見つかった残りの書き方でも見分ける。R6b の判定より弱くしない。普通の変更を新たに止めない。

### 変更後
1. `.sql` の読み方を PostgreSQL の字句の決まりに合わせる（引用符・E 付き文字列・二重引用符の名前・ドル引用・入れ子のコメント）。ドル引用の中身は実行される文として読み直す。閉じが無い引用・コメントは、R6b と同じく止める側に倒す。
2. 当てる文の種類を足す（持ち主ごとの一括削除、外部表の削除とその列の削除、空白を含む引用符つきの名前での列削除の略記、実行計画の測定・準備文を経由した大量削除）。
3. 中身の無い条件: WHERE の条件が、かっこの外で定数・真偽値・演算子だけのときは WHERE が無いのと同じに扱う。列や関数を 1 つでも参照すれば対象外。条件の全体を包むかっこは外して判断する。
4. `.sql` 以外: シェルのヒアドキュメントの中身と、改行の記号から始まる文字列の中身にも当てる（素の文と、コメントを除いた文の両方。R6b と同じ）。
5. 誤検知 2 種類を直す: ALTER TABLE の操作を区切るとき引用符を見る。閉じの無い単引用符がドル引用や E 付き文字列の中にあるときは文字列の始まりと見なさない（1 で解決）。

### 試験の × に置く普通の変更の例
- 入れ子のブロックコメントの中だけに書いた表削除
- ロールバック手順を行コメントで書いただけの変更（ドル引用や E 付き文字列の直後を含む）
- 実行計画だけ（SELECT を測る）・WHERE に列を使う DELETE・制約や既定値だけを消す ALTER TABLE
- シェルのヒアドキュメントの中の WHERE に列を使う DELETE

### 対象外
- ADR-1003 の説明文の更新（PO 確認の要否が未確認）
- 試験を GitHub で毎回動かすこと（別の作業）
- 文字列を実行時に組み立てる SQL（中身が差分に現れないもの）

### 受入条件
- K1 試験が全件合格。1〜5 の各形を ○ と × の両方で、本物の git の差分で試す。既存の試験はすべて合格のまま
- K2 審査の手元の見本で、対象の 9 種類がすべて検出、誤検知 2 種類がすべて非検出。R6b で検出していた見本で非検出になるもの 0
- K3 origin/main で migration と見なされる全 443 ファイルに R6b と新判定を当て、新しく当たるファイル 0 件
- K4 process-artifacts gate を含む必須の検査が緑

### 戻し方
merge commit の revert。

## R6d 本人 GO が要る変更の見分けの残り（わざと崩した書き方・長い入力）（設計・2026-10-28）

### 前提
- R6c（#4829、本番 2026-10-28 01:36）の審査（APPROVE on 7daa0d5、must 0）で should 3 つが残った。具体の書き方は公開しない（手元: /tmp/CC報告ファイル/rev4829/probe/mine.js・mine-out.txt・mine2.js・depth.js・perf-*.txt）。
- 見本 mine.js の結果: 見逃し（MISS）15 件、誤検知（FP）3 件。FP 3 件は main でも同じ（R6c で増えたものではない）。
- 2026-10-28 PO「1」でこの作業を選んだ。PO 決定「3」（本人性の機械確認は採らない）は変えない。
- 仕様の出典（Context7 は月の上限で使えなかったため、PostgreSQL 16 公式文書を直接確認、2026-10-28）:
  - sql-syntax-lexical: ドル引用のタグは大文字小文字を区別する。standard_conforming_strings が off のときは普通の文字列でもバックスラッシュが逃がし記号になる。数の指数は digits e [+-] digits。
  - sql-createrule: `DO [ ALSO | INSTEAD ] { NOTHING | command | ( command ; ... ) }`、command は SELECT/INSERT/UPDATE/DELETE/NOTIFY。

### 目的
mine.js の MISS 15 件と mine2.js の MISS 1 件をすべて検出にする。ドル引用タグを公式の決まりどおり大小文字を区別して読む。長い入力で止まらないようにする。R6c より弱くしない。普通の変更を新たに止めない。

### 変更後
1. 中身の無い条件の見分けを「数え上げ」から「残りが無いか」に変える。
   - WHERE の条件から、文字列（普通・E 付き・U& 付き・ドル引用）、数（指数表記を含む）、`::型名` の型変換、真偽値・NULL、演算子と語（AND OR NOT IS IN BETWEEN LIKE ILIKE SIMILAR TO DISTINCT FROM ANY ALL SOME CAST AS）、かっこ・カンマを取り除く。何も残らなければ、WHERE が無いのと同じに扱う。
   - かっこの外の OR でつながった枝のうち 1 つでも上の意味で中身が無ければ、条件全体を中身が無いと扱う（止める側。例: 定数の真の枝と列の枝を OR でつないだ形）。
   - 列名・引用符つきの名前・関数・`$1` などの引数・`%s` などの差し込み記号が 1 つでも残れば対象外（今まで通り）。
2. 当てる文の種類を足す: 準備文の型の指定にかっこが入れ子になる形、ルール定義の DO ALSO / DO INSTEAD / DO の後ろ（かっこで複数の文を並べる形を含む）。
3. ドル引用のタグを、大文字小文字を区別して閉じを探す（公式の決まりどおり）。タグの大小文字違いの見本が止まるのはこの読み方のせいではなく、ドル引用の中の文も当てる作り（関数本体の中の削除を見つけるために必要）のせい。止める側の誤りとして残す（2026-10-28 実装中に判明し改めた）。
4. ファイルの中で standard_conforming_strings を off にしているときは、普通の文字列でもバックスラッシュを逃がし記号として読む読み方でも当て、どちらかで当たれば検出する（止める側）。
5. `.sql` 以外:
   - シェルのヒアドキュメントの終わり語に、バックスラッシュで始まる形も認める。
   - ヒアドキュメントの中の psql 命令の行（バックスラッシュで始まる行）は、文の区切りとして扱う（その次の行を文の始まりとして当てる）。
   - Python の文字列は、`\n` `\r` `\t` を実際の改行・空白に置き換えてから当てる（置き換えた文に対しても、素の文とコメントを除いた文の両方。R6b と同じ）。
6. 長い入力:
   - 入れ子のドル引用・入れ子のかっこ・閉じの無いブロックコメントの処理を、呼び出しの入れ子（再帰）ではなく繰り返しにする。
   - 2 乗で伸びる処理（同じ位置からの読み直し）を、1 回の読みで済む形にする。
   - 1 回の読みで済ませられない形（閉じかっこの無い削除文が多数並ぶ形）のために、読み進める量に上限（入力の長さ×60＋200 万字）を付け、使い切ったら「検出」に倒す（止める側。2026-10-28 実装中に補足）。この上限は削除文の読みだけに使う。ALTER TABLE の操作の読みは上限の対象にせず、1 回の読みで済む形にする（審査 should 2 を受けて 2026-10-28 補足）。
   - 繰り返しに変えるとき、閉じの無いブロックコメントの後ろの扱いは R6c と同じにする（1 字進めて読み続け、その後ろの行コメントの除去と引用の読みを続ける）。（審査 should 1 を受けて 2026-10-28 補足）

### 対象外
- main でも同じ FP 3 件（ドル引用タグの大小文字違いの見本、シェルのヒアドキュメントの中のコメント行、ALTER TABLE の既定値のドル引用の中のカンマ）。どちらも止める側で、過去 443 件では 0 件。
- ADR-1003 の説明文、試験を GitHub で毎回動かすこと、実行時に組み立てる SQL（R6c と同じ）。

### 受入条件
- K1 試験が全件合格。1〜5 の各形を ○ と × の両方で、本物の git の差分で試す。既存の試験（269 件）はすべて合格のまま。
- K2 mine.js の全 82 件（今は OK 64・MISS 15・FP 3）で、FP は main と同じ 3 件以下・MISS 0 件。mine2.js の 2 件がどちらも期待どおり。R6c（origin/main）で検出していた見本で非検出になるもの 0（後退 0）。
- K3 今の origin/main で migration と見なされる全ファイルに R6c と新判定を当て、新しく true になるファイル 0 件。1 件でも出たら止めて報告。
- K4 速さ: perf の各形（最大 20 万字）と depth.js の 1 万段で、新判定が 1 件 1 秒以内・例外なし。
- K5 process-artifacts gate を含む必須の検査が緑。

### リスクと対処
- 「残りが無いか」の判断が広すぎて普通の DELETE を止める恐れ → 列・関数・引数が 1 つでも残れば対象外。mine.js の × 側の見本（列 IS NULL・列 = true・$1・ANY($1)・引用符つきの列・行の比較・型変換と now()・current_setting など）と K3 で確かめる。
- OR の枝の扱いで、定数の偽の枝と列の枝をつないだ形も止める → 止める側の誤り。K3 で過去の実例 0 件を確かめる。1 件でも出たら止めて報告。
- 処理を繰り返しに書き換えるため判定が変わる恐れ → K1 の既存 269 件と K2 の後退 0 で確かめる。

### 戻し方
merge commit の revert。

### 審査（Opus 自己審査・2026-10-28）
APPROVE。根拠: 目的が見本の件数で判定でき、K2/K3 で後退と誤検知の増加、K4 で速さを数で見る。仕様の根拠は公式文書で確認済み。事業判断が要る点は無い（PO 決定「3」の範囲内の見分けの強化）。未解決: なし。
