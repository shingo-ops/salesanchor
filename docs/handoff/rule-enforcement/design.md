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
1. コメントの扱い: .sql は引用符の中の行コメント・ブロックコメントの始まりをコメントと見なさない切り方でコメントを除いてから当てる。閉じの無いブロックコメントはコメントとして扱わない。.sql 以外は、素の文とコメントを除いた文の両方に当て、どちらかで当たれば検出する。
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
1. .sql の読み方を PostgreSQL の字句の決まりに合わせる（引用符・E 付き文字列・二重引用符の名前・ドル引用・入れ子のコメント）。ドル引用の中身は実行される文として読み直す。閉じが無い引用・コメントは、R6b と同じく止める側に倒す。
2. 当てる文の種類を足す（持ち主ごとの一括削除、外部表の削除とその列の削除、空白を含む引用符つきの名前での列削除の略記、実行計画の測定・準備文を経由した大量削除）。
3. 中身の無い条件: WHERE の条件が、かっこの外で定数・真偽値・演算子だけのときは WHERE が無いのと同じに扱う。列や関数を 1 つでも参照すれば対象外。条件の全体を包むかっこは外して判断する。
4. .sql 以外: シェルのヒアドキュメントの中身と、改行の記号から始まる文字列の中身にも当てる（素の文と、コメントを除いた文の両方。R6b と同じ）。
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
5. .sql 以外:
   - シェルのヒアドキュメントの終わり語に、バックスラッシュで始まる形も認める。
   - ヒアドキュメントの中の psql 命令の行（バックスラッシュで始まる行）は、文の区切りとして扱う（その次の行を文の始まりとして当てる）。
   - Python の文字列は、`\n` `\r` `\t` を実際の改行・空白に置き換えてから当てる（置き換えた文に対しても、素の文とコメントを除いた文の両方。R6b と同じ）。
6. 長い入力:
   - 入れ子のドル引用・入れ子のかっこ・閉じの無いブロックコメントの処理を、呼び出しの入れ子（再帰）ではなく繰り返しにする。
   - 2 乗で伸びる処理（同じ位置からの読み直し）を、1 回の読みで済む形にする。
   - 1 回の読みで済ませられない形（閉じかっこの無い削除文が多数並ぶ形）のために、読み進める量に上限（入力の長さ×60＋200 万字）を付け、使い切ったら「検出」に倒す（止める側。2026-10-28 実装中に補足）。この上限は削除文の読みに使う。ALTER TABLE の操作の読みは 1 回の読みで済む形にし、ALTER TABLE が多数並ぶ普通の変更で上限に届かないようにする（審査 should 2 を受けて 2026-10-28 補足）。
   - 繰り返しに変えるとき、閉じの無いブロックコメントの後ろの扱いは R6c と同じにする（1 字進めて読み続け、その後ろの行コメントの除去と引用の読みを続ける）。（審査 should 1 を受けて 2026-10-28 補足）
   - ALTER TABLE の操作の読みは、ファイル全体を 1 回だけ字句の決まりで読んでから行う。この 1 回の読みで、各位置が「文字列・二重引用符の名前・ドル引用・コメントの外か」と「かっこの深さ」を求める（standard_conforming_strings が off のときの読み方も同じく 1 回）。ALTER TABLE の始まりと読みを止める位置は、この外側かつ深さ 0 の位置だけで決める。ドル引用の中身は、これまでどおり別の文として読み直し、その中の ALTER TABLE はその中で同じ読み方をする。閉じの無い引用・コメントの扱いは R6c と同じにする（4 回目の審査 nit を受けて 2026-10-28 改め）。ALTER TABLE の字を含む引用符の中身も、Python の文字列などのために別の範囲として読む（入れ子は 3 段まで）。この読み直しは、外側で ALTER TABLE を読んでいる途中かどうかに関係なく必ず行う（注釈の中の ALTER TABLE の字で読みが「途中」になり、後ろの文字列の中の本物を飛ばして R6c より弱くなる形を防ぐ。4 回目の審査 must 1 を受けて 2026-10-28 補足）。standard_conforming_strings が off の読み方では、読み直す引用符の中身の中で、バックスラッシュとその次の 1 字を逃がしとして読み飛ばす（外側の文字列の中で逃がされた引用符を、文字列の開きと読まないため。これが無いと、閉じない引用が多数並ぶ普通の形で探し直しの上限に届き、誤って検出する。2026-10-28 実装中に補足）。閉じの無い引用符やドル引用の開きは 1 字として読み進め、そのための探し直しの合計に上限（長さ×40＋100 万字）を付け、使い切ったら検出に倒す（止める側。3 回目の審査のあと実装中に補足）。（2 回目・3 回目の審査 must 1 と 3 回目の should 1 を受けて 2026-10-28 改め。引用符だけを見て止める位置を決めると、かっこの中のドル引用の字で読みが早く止まり R6c より弱くなる。各当たりから読み直すと 2 乗で遅くなる）
7. R6c より弱くしないことを、形ごとの直しではなく作りで保証する（5 回の審査で、作り直すたびに R6c より弱くなる形が別の筋で見つかったため。5 回目の審査を受けて 2026-10-28 追加）。
   - origin/main（R6c）の見分けの関数を、中身を変えずに「下限の見分け」として残す。最終の判定は「新しい見分けで当たる、または下限の見分けで当たる」とする。
   - 下限の見分けには、繰り返しの回数の上限を数える仕掛けだけを足す。上限に届いたら検出に倒す（止める側）。上限の大きさは、1 回の判定全体で共有する「入力の長さ×100＋6000 万回」とする（回数の上限であり、時間の上限ではない。K3 の 443 件では 0 件。実測は同じ文を N 回並べた形で数えた（行数ではない）。ALTER TABLE だけを並べた形の多くは 700〜1000 回のあいだで、注釈や UPDATE と組み合わさる形は 400〜700 回のあいだで、.sql で ; の無い ALTER TABLE だけの形は 1000〜2000 回のあいだで上限に届き、届いたら検出に倒れる（止める側）。400 回までは、測ったすべての形で届かない。上限に届く大きさの変更は検出に倒れることがあり、止める側の誤りとして受け入れる。2026-10-28 実測で決定）。深い入れ子で例外が出たときも検出に倒す（R6c でも例外で止まっていた）。
   - そのため、R6c にあった誤検知 1 件（ALTER TABLE の既定値のドル引用の中のカンマ）は残る（誤検知は 3 件のまま）。対象外の欄に書いた R6c より弱くなる 1 形も、下限の見分けで検出に戻る。
   - あわせて、ブロックコメントの読みで、開きが積まれていないときの `*/` は閉じとして扱わず 1 字だけ進める（PostgreSQL では、`*` のすぐあとの `/*` もコメントの開き。5 回目の審査 must 2）。
   - standard_conforming_strings が off の読み方でバックスラッシュとその次の 1 字を読み飛ばす範囲は、読み直す範囲の全体とする（実装に合わせて文を改める。普通の読み方も必ず一緒に流すため、見逃しは増えない。5 回目の審査 nit）。

### 対象外
- main でも同じ FP 3 件（ドル引用タグの大小文字違いの見本、シェルのヒアドキュメントの中のコメント行、ALTER TABLE の既定値のドル引用の中のカンマ）。どれも止める側で、過去 443 件では 0 件。3 件目は、変更後 6 の読み方で操作を割らなくなり、誤検知でなくなった（2026-10-28 実装結果）。
- Python の文字列の `\n` を改行として読む（変更後 5）ため、`--` 注釈の終わる位置が R6c と変わる。そのため、削除文の直前に意味の無い語が残る形 1 つは、R6c では検出・R6d では非検出になる。この形は PostgreSQL が構文の誤りとして実行しない文（実行して確かめてはいない）で、過去 443 件では 0 件。改行として読むほうが実際に流れる文に近いため、こちらを採る（4 回目の審査 should 1 を受けて 2026-10-28 補足）。変更後 7 の下限の見分けにより、この形も最終の判定では検出になる（2026-10-28 追記）。ヒアドキュメントの中のバックスラッシュで始まる行を文の区切りとして読む形（変更後 5）も同じ扱い。
- ADR-1003 の説明文、試験を GitHub で毎回動かすこと、実行時に組み立てる SQL（R6c と同じ）。

### 受入条件
- K1 試験が全件合格。1〜5 の各形を ○ と × の両方で、本物の git の差分で試す。既存の試験（269 件）はすべて合格のまま。
- K2 mine.js の全 82 件（今は OK 64・MISS 15・FP 3）で、FP は main と同じ 3 件以下・MISS 0 件。mine2.js の 2 件がどちらも期待どおり。R6c（origin/main）で検出していた見本のうち、期待が「検出」のもので非検出になるもの 0（後退 0）。期待が「非検出」の見本が非検出になるのは誤検知が直ったもので、後退に数えない。
- K3 今の origin/main で migration と見なされる全ファイルに R6c と新判定を当て、新しく true になるファイル 0 件。1 件でも出たら止めて報告。
- K4 速さ: K3 の実ファイルは最終の判定が 1 件 1 秒以内。わざと長くした形（perf の各形、最大約 213 万字）と depth.js の 1 万段は、1 件 30 秒以内・例外なし（R6c も同じ種類の形で 20 秒前後かかる。CI の検査なので、本番の動きには関わらない）。ALTER TABLE を 400 回まで並べた普通の形は、上限に届いて検出に倒れるもの 0 件。（下限の見分けを足したため、2026-10-28 に「各 1 秒以内」から改め。R6c より弱くしないことを速さより優先する）
- K6 R6c より弱くならないこと: 審査の probe（/tmp/CC報告ファイル/rev4830〜rev4830e の全て）と差分ファズ（fuzz・fuzzalt・fuzzat）で、R6c で検出・新判定で非検出が 0 件。
- K5 process-artifacts gate を含む必須の検査が緑。

### リスクと対処
- 「残りが無いか」の判断が広すぎて普通の DELETE を止める恐れ → 列・関数・引数が 1 つでも残れば対象外。mine.js の × 側の見本（列 IS NULL・列 = true・$1・ANY($1)・引用符つきの列・行の比較・型変換と now()・current_setting など）と K3 で確かめる。
- OR の枝の扱いで、定数の偽の枝と列の枝をつないだ形も止める → 止める側の誤り。K3 で過去の実例 0 件を確かめる。1 件でも出たら止めて報告。
- 処理を繰り返しに書き換えるため判定が変わる恐れ → K1 の既存 269 件と K2 の後退 0 で確かめる。

### 戻し方
merge commit の revert。

ADR-1003 の説明: 2026-10-28 に ADR-1003 末尾へ実装の現状を追記した（決定は変えていない）。

### 審査（Opus 自己審査・2026-10-28）
APPROVE。根拠: 目的が見本の件数で判定でき、K2/K3 で後退と誤検知の増加、K4 で速さを数で見る。仕様の根拠は公式文書で確認済み。事業判断が要る点は無い（PO 決定「3」の範囲内の見分けの強化）。未解決: なし。

## R2a 今ある検査が止めている部分を違反の見本で試す（設計・2026-10-29）

### 前提（origin/main c350824c4 の事実）
- 台帳 docs/specs/rule-enforcement/rules.yml の 205 項目は review 88・exempt 117・gate 0。review のうち 48 項目は reason が「gate候補」で始まる（検査が一部だけ止めている決まり）。§5 R2 は「gate の各項目に見本を置く」としていたため、このままでは見本を置く対象が 0 件になる。
- 見本を置ける検査 12 本（§5 R2）は、どれも node_modules・外部の Python の部品・docker・DB なしで動く。GitHub API を使うのは scripts/check-process-artifacts.js だけで、MOCK_PR_BODY（:1733）・MOCK_PR_AUTHOR（:1711）・MOCK_ORIGIN_MAIN_FILES（:1145）を渡せば API なしで動く。
- 既存の試験のうち、CI で動いていないものがある: scripts/tests/test-process-artifacts.js、scripts/test_lint_tenant_schema.py、scripts/tests/test-migration-column-churn.js、scripts/tests/test-migration-duplicate-registration.js（.github/workflows に呼ぶ行が無い）。
- .github/workflows/rule-registry.yml は main 向け PR で動く。権限は contents: read だけ、checkout は既定（fetch-depth 1）、setup-node は無い。必須チェックではない。
- 2026-10-29 PO「1」: 完全に止まる決まりが 0 件のため、今の検査が止めている部分だけを違反の見本で試す進め方を選んだ。
- 調べの生出力: 手元の /tmp/CC報告ファイル/r2-recon/ と /tmp/CC報告ファイル/r2-recon2/。

### 目的
今ある必須チェックが「止める」と言っている違反を、わざと作った見本で本当に止めることを毎回の PR で確かめる。検査がこっそり弱くなったら、その PR で気づける。止まった割合（違反の見本のうち失敗になった数）を数で出す。

### 変更後
1. 見本は「決まり」ではなく「検査」ごとに置く。1 つの見本は、1 つの必須チェックが呼ぶスクリプトに、1 つの入力を食べさせたときの期待（失敗 か 成功）を持つ。見本が一部を止めている決まりの id を書けるようにする（台帳の review の項目でよい）。台帳の kind は変えない。完全に止まる決まり（gate）の数は 0 のまま。
2. 置き場は scripts/tests/rule-fixtures/<検査の短い名前>/<見本の名前>/。中身:
   - case.json: `check`（必須チェックの名前。docs/specs/rule-enforcement/required-checks.txt にあること）、`rules`（id の一覧。rules.yml に実在すること。空でもよい）、`expect`（`fail` か `pass`）、`expect_output`（fail のとき必須。失敗の出力に必ず含まれる文字列。別の理由で落ちたものを「止まった」と数えないため）、`argv`（実行する命令。`{BASE}` `{HEAD}` を差し込める）、`env`（渡す環境変数）、`env_files`（環境変数の名前と、見本のフォルダの中のファイルの組。中身をその変数に入れる。PR 本文を渡すため。任意）、`delete`（消すファイルの一覧。任意）。
   - files/: HEAD の側で上書きまたは足すファイル。base_files/（任意）: BASE の側で先に足しておくファイル（例: 消される側の API の道を、本物のファイルを写さずに用意するため）。どちらも名前の末尾に `.fixture` を付けて置き、試すときに外す（見本のファイルがリポジトリの中で本物の migration・文書・画面のファイルとして他の検査に当たらないため）。
3. 試し役 scripts/tests/run_rule_fixtures.py（新規・Python の標準ライブラリだけ）:
   - 見本ごとに、今の HEAD から使い捨ての git の写しを作る。base_files/ があれば置いて 1 コミット作り、それを BASE とする（無ければ写しの HEAD が BASE）。そのうえで files/ を置き delete を消して 1 コミット作り、それを HEAD とする。写しの中で argv を実行し、終了コードと出力を見る。終わったら写しを必ず片付ける。コミットの名前は環境変数で渡し、全体の git の設定は変えない。
   - 判定: expect が fail なら「終了コードが 0 以外、かつ expect_output が出力にある」で合格。pass なら「終了コードが 0」で合格。
   - 最後に「違反の見本 N 件中 N 件で止まった・正しい見本 M 件中 M 件で通った・見本が一部を止めている決まり K 件」を表示する。1 件でも期待と違えば exit 1。
   - case.json の形（必須の欄・check が required-checks.txt にある・rules が rules.yml にある）が崩れていても exit 1。
4. 最初の見本（R2a）は、パスに関係なく毎回走る必須チェック 4 本に置く。各検査に違反の見本を 1 つ以上・正しい見本を 1 つ以上:
   - process-artifacts gate（scripts/check-process-artifacts.js）: 例として、コードの変更で PR 本文に「触るファイル」の宣言が無い、migrations/ を足して GO 記録が無い。正しい見本は、違反の見本の 1 つと同じ変更で足りない欄を足したもの。
   - UI governance gate（scripts/check-ui-governance.js）: 既存の試験が失敗を期待している形の 1 つを、本物のファイルの差分で作る。
   - dangling-route gate（scripts/check-dangling-routes.js）: 画面から呼ばれている API の道を消す。正しい見本は、どこからも呼ばれていない道を消す、またはどこも消さない。
   - doc index reachability（scripts/ci/check_doc_index.py --root . --strict）: 目次から届かない新しい文書を足す。正しい見本は、目次から既にリンクで届くフォルダ（docs/ai-agents/lessons.d/）に新しい文書を足したもの（実装時に変更。どちらも「目次から届くかどうか」だけを分ける見本で、意図は同じ）。
   - 見本は、止まると分かっている形だけにする。すり抜ける形は公開のリポジトリに置かない。
5. .github/workflows/rule-registry.yml に setup-node（他のゲートと同じ版）と、試し役を流す手順を 1 つ足す。手順は失敗で止まる（continue-on-error を付けない）。ジョブは必須チェックではないので、マージは止めない（§3-5 の段階導入。必須への格上げは PO の登録で、R2a の外）。timeout-minutes は実測を見て決め、10 分を超えない。

### 対象外（後の作業）
- R2b: 残りの 8 本（generate-adr-index.js --check、frontend/scripts/check-claude-size.js、lint_tenant_schema.py、check-doc-heading-duplicates.sh、check-migration-value-writes.py、check-migration-column-churn.js、check-migration-duplicate-registration.sh、check-lessons-section.sh）の見本。check-lessons-section.sh は自分では失敗を返さず、失敗の判定は lessons-guard.yml の中にあるため、見本ではなく evidence（実際に止まった PR）で代える。
- R2c: CI で動いていない既存の試験 4 本を CI で動かす。
- 経路ごとの試し（§5 R2 の最後の項目。手元の Claude・クラウドの Claude・PO 名義・Codex から違反の PR を出す）。Codex を使っているかは R0 で確定していない（recon §12 に記載なし）。
- 台帳の kind・check_rule_registry.py の変更、gate への格上げ、必須チェックへの登録。

### 受入条件
- K1 試し役が CI（rule registry のジョブ）と手元の両方で exit 0。表示が「違反の見本 N 件中 N 件で止まった」「正しい見本 M 件中 M 件で通った」で、N は 4 以上・M は 4 以上。4 本の検査のそれぞれに違反と正しい見本が 1 つ以上ある。
- K2 弱めたら気づく: 手元の使い捨ての写しで、4 本の検査それぞれを「常に成功で終わる」ように書き換えると、試し役が exit 1 になり、その検査の違反の見本の名前を表示する（書き換えはコミットしない）。expect_output を実際に出ない文字列にした見本も exit 1 になる。
- K3 見本のファイルが他の検査に当たらない: この PR で必須チェック 16 件が全部 pass（見本を足したことで新しく落ちるものが無い）。
- K4 片付け: 試し役の実行後に、使い捨ての写し（git worktree list に出るもの・一時フォルダ）が残らない。見本の途中で失敗したときも残らない。
- K5 速さ: rule registry のジョブ全体の所要時間を CI の記録で測り、PR 本文に書く。

### リスクと対処
- 見本が別の理由で落ちて「止まった」と数えてしまう → expect_output を必須にし、K2 で出ない文字列の見本が落ちることを確かめる。
- 見本のファイルが本物の migration や文書として他の検査に当たる → `.fixture` を付けて置く（K3）。
- 使い捨ての写しが残る → 片付けを必ず通る形にする（K4）。
- 検査の側の正しい変更で見本が合わなくなる → 失敗の表示に見本の名前と期待を出す。直し方は見本を今の検査に合わせて直すこと（検査を弱めた結果なら、それが気づくべき変化）。

### 戻し方
merge commit の revert。

### 審査（Opus 自己審査・2026-10-29）
APPROVE。根拠: 目的が見本の件数（止まった割合）と K2 の弱めた試しで判定できる。入力の渡し方は 4 本とも実物で確かめた（r2-recon2）。PO の選択（2026-10-29「1」）の範囲で、台帳の kind と必須チェックの登録は変えない。未解決: なし（UI governance gate の違反の形は既存の試験から実装時に選び、報告で示す）。

## R2b 残りの検査に違反の見本を足す（設計・2026-10-29）

### 前提（origin/main 16ec7021b の事実。調べの生出力は手元の /tmp/CC報告ファイル/r2b-recon/）
- 2026-10-29 PO「1」で、R2a と同じ形の見本を残りの検査にも足す作業を選んだ。
- R2a の「対象外」に挙げた 8 本のうち 7 本は、試し役 scripts/tests/run_rule_fixtures.py を変えずに、使い捨ての写しで違反の見本が exit 1、正しい見本が exit 0 になることを確かめた（run_all.txt の最終行「違反の見本 13 件中 13 件で止まった・正しい見本 14 件中 14 件で通った」。この数は調べの写しで作った見本の数で、lessons の見本を含む。実装の数は R2a の 10 件を含めて違反 12・正しい 13）。7 本とも標準の道具だけで動き、node_modules・外部の Python の部品・docker・DB・ネットワークは要らない。
- 7 本と、それを呼ぶ必須チェック（docs/specs/rule-enforcement/required-checks.txt の名前）:
  - scripts/generate-adr-index.js --check → ADR index is up to date（adr-index-check.yml:31）
  - frontend/scripts/check-claude-size.js → CLAUDE.md line count check（check-claude-size.yml:38-40）。R2a の節で scripts/check-claude-size.js と書いたのは場所の誤り。
  - scripts/lint_tenant_schema.py --mode strict backend/app/routers/ → ADR-072 tenant schema lint (strict mode)（lint-tenant-schema.yml:69）
  - scripts/check-doc-heading-duplicates.sh（引数なし）→ process-artifacts gate（process-artifacts-gate.yml:47）
  - scripts/check-migration-value-writes.py → models.py に新 Column → deploy.yml にマイグレーション追記必須（migration-guard.yml:407・:424・:437）
  - scripts/check-migration-column-churn.js → 同じ（migration-guard.yml:552）
  - scripts/check-migration-duplicate-registration.sh → 同じ（migration-guard.yml:556）
- scripts/check-lessons-section.sh は自分では常に exit 0 で、数を出すだけ。落とす判定（数が 0 でなく、例外の印が無いとき失敗）は lessons-guard.yml:24-29 の中にある。

### 目的
R2a と同じく、今ある必須チェックが「止める」と言っている違反を、わざと作った見本で毎回の PR で確かめる。試せる検査を 4 本から 11 本にする。

### 変更後
1. scripts/tests/rule-fixtures/ に、上の 7 本それぞれについて違反の見本 1 つ以上・正しい見本 1 つ以上を足す。形は R2a と同じ（case.json・files/・base_files/・`.fixture`）。試し役は変えない。
2. 見本の入れ方は、CI での呼び方にできるだけ合わせる:
   - generate-adr-index.js: 違反は ADR の文書を 1 つ足して目次を直さない。正しい見本は変更なし。
   - check-claude-size.js: argv は `node frontend/scripts/check-claude-size.js`。違反は AGENTS.md を上限を超える行数に差し替える。正しい見本は変更なし。
   - lint_tenant_schema.py: argv は CI と同じ `--mode strict backend/app/routers/`。違反は commit の直後に reset が無い道を 1 つ足す。正しい見本は同じ道で reset を足したもの。
   - check-doc-heading-duplicates.sh: argv は CI と同じ引数なし。違反は既定で読む文書の 1 つ（docs/ai-agents/design-partner.md）を、写しの中で、節の番号が重なる小さな文書に差し替える。正しい見本は変更なし。
   - check-migration-value-writes.py: 違反は守る表に値を書く migration を足し、`diff {BASE} {HEAD} --check 7`。正しい見本は構造だけを変える migration で同じ範囲を全部の確認で流すものと、`repo` を変更なしで流すもの。
   - check-migration-column-churn.js: 本物の登録表は大きいため、検査が持つ差し替えの環境変数（MIGRATIONS_SCRIPT_OVERRIDE・ALLOWLIST_OVERRIDE）で小さな登録表と空の例外表を渡す。違反は同じ列を足して消す。正しい見本は足すだけ。
   - check-migration-duplicate-registration.sh: `--migrations-script` で小さな登録表を渡す。違反は同じ行を 2 回登録。正しい見本は重なりなし。
3. rules 欄: rules.yml の reason にその検査の名前が出てくる id で、見本の違反が当たるものだけ（調べでは generate-adr-index.js が L362、lint_tenant_schema.py が K01。ほかは空）。実装時に rules.yml の reason を読んで確かめる。
4. docs/handoff/rule-enforcement/design.md の R2a 節の check-claude-size.js の場所を直す（frontend/scripts/）。
5. rule-registry.yml は変えない（timeout 10 分の中に収まることを K5 で測る。収まらなければ止まって報告する）。

### 対象外
- check-lessons-section.sh: 見本は置かない。試し役は終了コードで判定するが、この検査は常に exit 0 で、落とす判定はワークフローの中にある。見本で試すには判定を argv に書き写す必要があり、写しがワークフローとずれても気づけないため。R2a の設計どおり、実際に止まった PR の記録（evidence）で代える。evidence の調べは後の作業。
- 差し替えの環境変数・引数を使う 2 本（column-churn・duplicate-registration）は、本物の登録表と本物の例外表そのものは試さない（検査の判定の部分だけを試す）。
- check-migration-value-writes.py は、違反の見本を check 7 だけに置く。check 8 と repo（全件走査）の失敗の道には違反の見本を置かない（正しい見本だけ）。正しい見本の `--check all` は CI に無い呼び方（CI は 7 と 8 を別々に流す）。
- check-claude-size.js は、CI では frontend を作業場所にして流すが、見本は根から流す。検査は根の場所をスクリプト自身の場所から求める（check-claude-size.js:18）ため、結果は変わらない。
- R2c（CI で動いていない既存の試験を CI で動かす）、R4、台帳の kind・必須チェックの登録は変えない。

### 受入条件
- K1 試し役が CI（rule registry のジョブ）と手元の両方で exit 0。11 本の検査それぞれに違反と正しい見本が 1 つ以上あり、違反の見本は全部止まり、正しい見本は全部通る。
- K2 弱めたら気づく: 使い捨ての写しで、今回の 7 本それぞれを「常に成功で終わる」ように書き換えると、試し役が exit 1 になり、その検査の違反の見本の名前を出す（書き換えはコミットしない）。
- K3 この PR で必須チェック 16 件が全部 pass（見本を足したことで新しく落ちるものが無い）。
- K4 実行後に使い捨ての写しと一時フォルダが残らない。
- K5 rule registry のジョブ全体の所要時間を CI の記録で測り、PR 本文に書く。10 分の上限の半分（5 分）を超えたら、マージせず止まって報告する。

### リスクと対処
- Linux と macOS の道具の違い（awk・sed・grep）で、手元では通り CI で落ちる → K1 を CI で確かめる。落ちたら見本ではなく原因を調べて報告する。
- 見本のファイルが本物の migration・ADR・文書として他の検査に当たる → `.fixture` を付けて置く（K3）。
- 見本の数が増えて遅くなる → K5 で測る。

### 戻し方
merge commit の revert。

### 審査（Opus 自己審査・2026-10-29）
APPROVE。根拠: 7 本とも試し役を変えずに違反と正しい見本の結果を写しで確かめた（r2b-recon/run_all.txt）。lessons は判定がワークフローの中にあり、R2a で決めた evidence の扱いを変えない。差し替えを使う 2 本・value-writes・claude-size は CI の呼び方との差を対象外に明記した（doc-heading は CI と同じ引数なし）。未解決: なし。
- 実装後の審査（Opus 審査役・39f944f5a）: must 0。should は必須チェック 2 件（GO 原文の未記入・ブランチの起点の遅れ）で、手続きで解く。nit 5 件のうち 4 件（調べの数・value-writes と claude-size の差の明記・自己審査の文）をこの節で直した。expect_output をより狭くする nit は、今の見本の組み合わせで別の理由と取り違えないため直さない。

## R2c CI で動いていない既存の試験 4 本を毎回の PR で動かす（設計・2026-10-30）

### 前提（origin/main 5195ecc1d の事実。調べの生出力は手元の /tmp/CC報告ファイル/r2c-recon/）
- 2026-10-29 PO「1」で、毎回は動いていない既存の試験 4 本を毎回動かす作業を選んだ。
- 4 本は .github/workflows のどこからも呼ばれていない（79 ファイルを名前で探して 0 件。1-grep.txt）。backend の pytest は testpaths が tests のため scripts/ の試験を拾わない（backend/pyproject.toml:54）。
- 4 本は今の main で全部通る（2-*.txt）:
  - scripts/tests/test-process-artifacts.js: `node` で exit 0、326 PASS / 0 FAIL。手元の Mac で 4 分 15 秒。検査を子プロセスで何百回も起動するため遅い。実行中に docs/handoff/_test_tmp/ を作る。
  - scripts/tests/test-migration-column-churn.js: exit 0、13 passed、2.5 秒。
  - scripts/tests/test-migration-duplicate-registration.js: exit 0、3 passed、0.5 秒。
  - scripts/test_lint_tenant_schema.py: `python3 -m pytest -q` で 11 passed、約 1 秒。`python3 -I` で直接流すと試験の関数が 1 つも呼ばれず、何も確かめないまま exit 0 になる（2-lint-tenant.txt が空）。
- 要るもの: js の 3 本は node の標準部品と git だけ。py の 1 本は pytest だけ。docker・DB・ネットワークは要らない。
- 4 本が試す検査と、それを呼ぶ必須チェック: check-process-artifacts.js → process-artifacts gate、lint_tenant_schema.py → ADR-072 tenant schema lint (strict mode)、check-migration-column-churn.js と check-migration-duplicate-registration.sh → migration-guard.yml の中の手順（552・556 行）。
- rule-registry.yml の rule registry ジョブは必須チェックではなく、timeout 10 分、setup-node 22 あり、setup-python と pytest の導入は無い。pytest の入れ方の手本は hook-test.yml:37-44（setup-python 3.12 → setup-uv → `uv pip install --system pytest`）。

### 目的
R2a・R2b の見本は「検査が違反を止めるか」を 1 件ずつ試す。既存の 4 本は同じ検査を細かい場合分けで試している（合わせて 353 件）。これが毎回動いていないため、検査の細かい部分が壊れても気づけない。4 本を毎回の PR で動かし、壊れたらその PR で気づけるようにする。

### 変更後
1. .github/workflows/rule-registry.yml に、rule registry と並んで走る別のジョブ `existing-rule-tests`（名前「existing rule tests」）を足す。毎回の PR で動く（on は今のまま。paths の絞り込みはしない）。
2. ジョブの手順: checkout@v5 → setup-node@v5（'22'）→ setup-python@v5（'3.12'）→ setup-uv@v4 → `uv pip install --system pytest` → 4 本を 1 手順ずつ流す（js は `node <path>`、py は `python3 -m pytest -q scripts/test_lint_tenant_schema.py`）。どの手順も continue-on-error にしない。
3. timeout-minutes は 15。test-process-artifacts.js が遅いため、rule registry の 10 分とは分ける。
4. py の 1 本は必ず pytest で流す（`python3 -I` では何も試さずに通るため）。pytest は試験が 1 件も集まらないと exit 5 で落ちるので、試験の関数の名前が変わって空振りすることも防げる。
5. 必須チェックには登録しない（登録は Branch Protection の変更で、PO 本人の判断が要るため）。
6. docs/handoff/rule-enforcement/design.md の R2b 節の末尾行にある数え誤り「nit 4 件のうち 3 件」を「nit 5 件のうち 4 件」に直す（R2b の審査で次の変更で直すとした分）。

### 対象外
- 4 本の試験と検査の中身は変えない。
- 必須チェックへの登録（Branch Protection の変更）。
- check-lessons-section.sh を実際に止まった記録で確かめる作業、提出前の一本の入口（R4）、語の一覧の作り直し（R1c）。
- test-process-artifacts.js を速くすること（K3 で測り、上限を超えたときだけ別に考える）。

### 受入条件
- K1 この PR で、existing rule tests ジョブが success。4 本それぞれの手順が success で、最後の行（326 PASS・13 passed・3 passed・11 passed）が出ている。
- K2 弱めたら気づく: 使い捨ての写しで 4 本が試す検査をそれぞれ 1 か所ずつ弱めて（違反を見逃す形に書き換えて）流すと、その試験が exit 0 以外になる。4 本それぞれ 1 回。書き換えはコミットしない。
- K3 ジョブ全体の所要時間を CI の記録で測り、PR 本文に書く。15 分の上限の半分（7 分 30 秒）を超えたらマージせず止まって報告する。
- K4 この PR で必須チェック 16 件が全部 pass。
- K5 実行後に使い捨ての写しと一時フォルダが手元に残らない。

### リスクと対処
- checkout の既定は履歴 1 件だけ。test-process-artifacts.js などが履歴を要ると CI で落ちる → K1 で確かめる。落ちたら、そのジョブだけ fetch-depth: 0 にする（ほかは変えない）。理由を報告に書く。
- Linux と macOS の道具の違いで、手元では通り CI で落ちる → K1 で確かめる。落ちたら試験を直さず、原因を調べて報告する。
- 毎回の PR で数分の実行が増える → K3 で測る。

### 戻し方
merge commit の revert。

### 審査（Opus 自己審査・2026-10-30）
APPROVE。根拠: 4 本とも今の main で通ることを写しで確かめた（r2c-recon/2-*.txt）。py の 1 本が直接の実行では空振りする点は、pytest で流し、試験 0 件で落ちる性質で防ぐ。workflow-lint.yml と Branch Protection には触れないため、ADR-1003 の本人 GO の例外に当たらない。未解決: CI での所要時間と、履歴 1 件の checkout で動くか（K1・K3 で確かめる）。

### 追記（CI の 1 回目の結果・2026-10-30）
- 事実: 7f8d24c8 の existing rule tests は、工程の成果物の検査の試験で 324 PASS / 2 FAIL（run 41001128041）。落ちたのは LOCAL_PRECHECK の 2 件で、どちらも「LOCAL_PRECHECK は CI では使えません」で止まった。他の 3 本の手順は前の手順の失敗で動いていない。
- 原因: 検査は `LOCAL_PRECHECK` と `GITHUB_ACTIONS === 'true'` の併用を止める（scripts/check-process-artifacts.js:1642）。試験は手元での事前検査を真似るため LOCAL_PRECHECK=1 を渡すが、CI の実行環境の GITHUB_ACTIONS=true をそのまま子に引き継ぐ。手元では GITHUB_ACTIONS が無いので通る。
- 対処: その手順だけ `env -u GITHUB_ACTIONS node scripts/tests/test-process-artifacts.js` で流し、手元と同じ条件にする。試験と検査の中身は変えない。CI での併用を止める決まりは、試験が自分で GITHUB_ACTIONS=true を渡す 1 件（test-process-artifacts.js:2039）で引き続き試される。
- 他の 3 本の手順も、この修正後の CI で初めて結果が出る。そこで落ちたら同じように原因を調べて止まる。

## R2d tenant schema 検査の「違反なら失敗で終わる」部分を試す（設計・2026-10-30）

### 前提（origin/main ba3e9207d の事実。調べの生出力は手元の /tmp/CC報告ファイル/lint-strict-recon/）
- 2026-10-30 PO「２」で、R2c で見つかった足りない所をふさぐ作業を選んだ。
- R2c の K2 で、scripts/lint_tenant_schema.py の strict の `return 1` を `return 0` に弱めても、scripts/test_lint_tenant_schema.py は 11 passed のまま通った。試験は `lint_file()` だけを呼び、`main()` と終了コードを試していない（試験 13〜18 行は lint_file だけを import）。
- 必須チェック「ADR-072 tenant schema lint (strict mode)」は `python3 scripts/lint_tenant_schema.py --mode strict backend/app/routers/` を呼ぶ（lint-tenant-schema.yml:66-69）。止まるかどうかは、この命令の終了コードだけで決まる。
- `main(argv)`（lint_tenant_schema.py:306）は引数のパスだけを走査し、git やネットワークに依存しない（325-333 行）。違反があれば strict で 1、warning で 0、違反がなければ 0 を返す（356-367 行）。最後は `sys.exit(main())`（370-371 行）。旗は `--mode strict` で、`--strict` は無い。
- 一時の違反ファイル・正しいファイルで実測：命令として流すと strict＋違反は rc=1（stderr に `mode=strict: failing CI`）、strict＋正しいは rc=0、warning＋違反は rc=0（d_*.txt）。

### 目的
CI と同じ「命令として流したときの終了コード」を試験で確かめ、strict の失敗の返し方が壊れたら R2c で足した毎回の試験で気づけるようにする。

### 変更後
1. scripts/test_lint_tenant_schema.py に試験を 3 件足す。検査の本体を、CI と同じく別のプロセスの命令として流す（`subprocess.run([sys.executable, <scripts の絶対パス>/lint_tenant_schema.py, "--mode", ..., <一時ファイル>], capture_output=True, text=True)`）。
   - strict＋違反ファイル → returncode が 1、stderr に `mode=strict: failing CI` を含む。
   - strict＋正しいファイル → returncode が 0。
   - warning＋違反ファイル → returncode が 0（strict と warning の取り違えに気づくため）。
2. 違反ファイル・正しいファイルは既存の `_write_tmp` で作る。パスは必ず明示する（既定の `backend/app/routers` は実行場所で変わるため使わない）。
3. 既存の 11 件と検査の本体は変えない。ワークフローも変えない（R2c の existing rule tests が毎回 pytest で流す）。

### 選んだ理由
`main()` を直接呼ぶ形より、命令として流す形を選ぶ。CI が見るのは `sys.exit(main())` を通った終了コードで、そこまで含めて試せるため。実測で、絶対パスで呼べば実行場所に依存しなかった。

### 対象外
- 検査の本体・既存の試験・ワークフローの変更。
- 試験だけを変える PR では、必須チェック「ADR-072 tenant schema lint」は変更の絞り込みにより検査を飛ばして pass になる。この PR の試験の確かめは existing rule tests で行う。

### 受入条件
- K1 手元と CI の existing rule tests で `python3 -m pytest -q scripts/test_lint_tenant_schema.py` が 14 passed。
- K2 弱めたら気づく：使い捨ての写しで、strict の `return 1` を `return 0` に弱めると、足した試験が落ちて pytest が exit 0 以外になる。strict と warning の判定を入れ替える弱め方でも 1 回試す。書き換えはコミットしない。
- K3 この PR で必須チェック 16 件が pass、existing rule tests が success。
- K4 一時ファイル・使い捨ての写しが残らない（足した試験が作る一時ファイルも、試験の中で消す）。

### リスクと対処
- 足した試験が一時ファイルを残す → 試験の中で消す（K4）。
- CI の Python の版と手元の違い → K1 で CI でも確かめる。

### 戻し方
merge commit の revert。

### 審査（Opus 自己審査・2026-10-30）
APPROVE。根拠：足りない所は R2c の K2 で実測済み（11 passed のまま通った）。命令として流す形は調べで rc=1/0/0 を実測済み。検査・ワークフロー・必須チェックの登録に触れないため、ADR-1003 の本人 GO の例外に当たらない。未解決：なし（CI での結果は K1・K3 で確かめる）。

## R1c-1 決まりの語の一覧を広げる（第1段：言い方のはっきりした語）

### なぜ
台帳の語の一覧（rules.yml:12）は 9 語だけで、一覧に無い言い方で書いた決まりは突き合わせを素通りする（§5 R1 の限界、ADR-1047 条文の取りこぼし）。2026-10-30 PO「2,1」で、語の一覧の作り直しを先に進めると決めた。

### 調べた事実（origin/main 162cb754、生出力 /tmp/CC報告ファイル/r1c-words/）
- check_rule_registry.py と同じ読み方（44 本・5786 行・全行）で再現し、今の語の一覧で 412 行に当たることを確かめた
- 一覧に当たらない 5374 行で、言い方ごとの行数（重なりあり）：「〜ない」で終わる動詞の否定 227（うち記録の文書 evidence-registry.md 133・lessons.d 21）、のみ 142（記録 89）、だけ 70（記録 33）、べき 33（大半が「あるべき姿」）、不可 32（「不可逆」を含む）、が必要 24、不要 19、ないこと 9、止める 8、避け 7、してよい 7、限る 6、ならない 5（うち「進んではならない」など、「して」でない形が design-partner.md:32 の 1 行。新しい語でも当たらない残りは evidence-registry.md:1271・:1493 の記録の行で「緑にならない」等の形）、認めない 4、要る 4、必要がある 3。英語は only 62 のほかは 0〜7
- 下の第1段の語で新しく当たった行は 117 行（529 − 412。「不可逆」だけの行を除いた和集合。check_rule_registry.py の実測）。足した項目は 116 件（rules 205→254 で 49、not_rules 49→116 で 67）。差 1 は STANDARD-WORKFLOW.md:83 が既存の S03 の anchor にすでに当たるため（新しい項目が要らない）

### 何を変えるか（第1段）
- rules.yml:12 の words を次にする：
  `禁止|必ず|必須|厳禁|[てで]はならない|しない|すること|ないこと|不可(?!逆)|認めない|限る|不要|が必要|必要がある|してよい|要る|止める|避け|MUST|NEVER`
  - 「してはならない」は「「てはならない」「ではならない」」に広げる（「進んではならない」を拾うため。今の 2 行は引き続き当たる）
  - 「不可」は「不可逆」を除く
- 新しく当たった行をすべて rules か not_rules に入れる（ADR-1047 条文7〜10 と R1b の書き方に従う。1 行 1 項目。id は文書の頭文字＋各文書の次の空き番号）
  - 機械で○×が決まるが今は止める必須チェックが無い行は review で reason を「gate候補（R6）: 」で始める
  - 今回 gate は足さない（足すには止める必須チェックと見本が要る。R2 の範囲）
  - 記録の文書（evidence-registry.md・lessons.d）の行は、過去の出来事の記録なら not_rules にし reason にそう書く
- 検査の台本（check_rule_registry.py）・rule-docs.txt・required-checks.txt・ワークフローは変えない

### 第2段以降に回すもの（理由）
- 「〜ない」で終わる動詞の否定（227 行）：件数が多く、第1段と混ぜると審査で見落とす。第1段の結果を見てから、正規表現と仕分けを別の PR で行う（変更は一度に1つ）
- のみ・だけ・べき・only：見本 10 行ずつで説明文が大半（「〜のみ追加」「あるべき姿」など）。語として足すと決まりでない行が大半になる。第2段のあとに残りとして数を測って報告する
- 週次点検への「required-checks.txt と ruleset の差」（spec README:26 の R1c 後半）：PO が今回選んだのは語の一覧の作り直しなので、別の作業にする

### 受入条件
- K1：`python3 -I scripts/ci/check_rule_registry.py` の未仕分けが 0・error 0。決まりの語を含む行が 412 より増え、増えた行はすべて既存か新しい項目に当たる（差は理由を書く）
- K2：新しく足した項目すべてに reason があり、kind は review・exempt・not_rules のどれか（gate 0 のまま）。gate候補の数を報告する
- K3：語ごとの新しく当たった行の数を報告し、上の調べの数（不可逆を除く）と食い違いがあれば理由を書く
- K4：`python3 -I scripts/tests/test_check_rule_registry.py`（27 件）・run_rule_fixtures.py・`check_doc_index.py --root . --strict` が rc=0
- K5：この PR の必須チェック 16 件が pass、rule registry と existing rule tests が success
- K6：変えたファイルは rules.yml と design.md だけ

### リスクと対処
- 仕分けの誤り（決まりを not_rules にする）→ 審査役が新しい項目から見本を取って出典の行と照らす。not_rules の reason は「なぜ決まりでないか」を1文で書く
- 不可(?!逆) は「不可視」「不可能」にも当たる（今は lessons.d の不可視文字の行・kpi.md:185・evidence-registry.md:1270 で、いずれも決まりでない行として分けた）。語を絞るのは第2段で数を見て決める
- 語の一覧の変更は GO 記録の要る変更（check-process-artifacts.js）→ GO 記録を書く
- 戻し方：revert（検査は警告のまま。必須チェックではない）

### Opus 自己審査（同じ AI の審査。独立の審査は PR で別の審査役が行う）
APPROVE。根拠：語ごとの数は再現した読み方で数えた。変える場所は台帳と設計書だけ。第2段に回したものと理由を書いた。未解決：「〜ない」の正規表現は第1段のあとに決める。

## R4a 提出前の一本の入口（第1段：入口の台本と試験だけ）

### なぜ
必須チェック 16 件を手元で 1 回の命令で流す入口が無い（recon.md:199）。提出してから CI で落ち、直して出し直す手戻りがある。2026-10-30 PO「2,1」と続く「1」で、この入口を作ると決めた。KGI G4（kgi.md:18）。

### 調べた事実（origin/main a6d33ae2、生出力 /tmp/CC報告ファイル/r4-recon/・/tmp/CC報告ファイル/r4-measure/）
- 必須 16 件の命令と要るもの（r4-recon の表）。DB・redis が要る（pytest・テナントスキーマ整合性・マイグレーション実DB 2 ジョブ）、GitHub のイベントと権限が要る（guard-authoring/evaluation の評価本体）、PR 本文が要る（process-artifacts gate・migration-guard の 2 step）、npm ci と uv が要る（Lint & Dark Mode・API contract）ものは手元の入口に向かない
- 手元で流せた 15 項目は main で失敗 0。所要秒：check_doc_index 9.0・check_rule_registry 0.9・lint_tenant_schema 2.4・check-claude-size 1.4・generate-adr-index 0.5・ui-governance 0.3・dangling-routes 17.8・check-lessons-section 0.3・migration-registration-exists 0.6・migration-guard の台本群 約 30・doc-heading-duplicates 0.1・test_check_rule_registry 14.4。重いもの：test-guard-evaluations 122.7、run_rule_fixtures 全件 375.3（--only 1 種で 33.6）、gitleaks dir 135.9
- 手元は Python 3.14・Node 24、CI は Python 3.12・Node 22（guard-authoring だけ 24）
- 台帳（rules.yml）に when 列は 0 件、gate 項目も 0 件。設計 §R4（design.md:149-157）の「台帳の when: before_submit の gate 項目を選ぶ」は、今は選ぶ対象が無い
- 手元用の道はすでに 2 つある：validate-pr-body.sh:288-319 が LOCAL_PRECHECK=1 で process-artifacts を事前に流す（PR 作成時）、husky pre-commit が check-claude-size と lint_tenant_schema を流す

### 何を作るか（第1段）
- scripts/dev/check-before-submit.sh（新規、design.md:151 の名前どおり）
  - 変更ファイルの一覧は分岐点から取る。2 点で比べる検査には CI と同じく origin/main の SHA を渡す。枝が main より遅れていれば表示する（2026-10-30 審査を受けた Opus 判断）。fetch はしない（使った origin/main の SHA を表示する）。まだ commit していない変更があれば「commit してから流す」と表示して終了コード 2
  - 黙って通る道をふさぐ（2026-10-30 審査の指摘）: 必須一覧が無い・0 件、`--only` の値が無い・知らない id、流した検査が 0 件は終了コード 2。壊れた case.json・見本の選別の python が落ちたときは × で終了コード 1。一部だけ流した必須名は △（終了コードには影響しない）
  - CI と同じ台本を呼ぶ（写さない）。速い組（上の速いもの、合計約 80 秒）は変更ファイルに関係なく毎回流す。main で全部通ることを確かめてあるので、落ちたら自分の変更が原因とわかる
  - 違反の見本（run_rule_fixtures.py）は、変更ファイルが見本の case.json の argv にある台本か、その見本のフォルダの中にあるときだけ、その見本を `--only` で流す（どの見本を流すかは見本のデータから決め、台本に一覧を書き写さない）
  - 重い組（test-guard-evaluations、見本の全件）は `--full` を付けたときだけ流す。付けないときは「CI で確かめる」と名前を表示する
  - 手元で流さないもの（DB が要る 3 件・評価本体・PR 本文が要るもの・npm ci と uv が要る 2 件・gitleaks の履歴走査）は、名前と理由を「CI で確かめる」として全部表示する（黙って通さない）。process-artifacts は「PR 作成時に validate-pr-body.sh が確かめる」と表示
  - check-lessons-section の SEC6_ADDED が 0 でなければ、失敗ではなく「PR に lessons-cleanup ラベルが要る」と注意を表示（ラベルは提出後にしか付けられないため）
  - 最後に、流した検査ごとの ○×と秒、飛ばした検査と理由、手元と CI の版の違い（python3・node の版）を表示。1 つでも × なら終了コード 1、全部 ○ なら 0
- 補助の指定：`--list-fixtures`（今の変更で選ばれる見本の名前だけ表示して終わる）と `--only <検査の id,…>`（検査を絞る）は、試験を速くするための補助
- 試験（scripts/tests/ に新規。既存の試験の流れ方に合わせる）
  - main と同じ中身の写しで流すと終了コード 0 で、流した検査の名前がすべて出る
  - 違反を 1 つ入れた写し（例：tenant schema の違反の見本、doc index の切れたリンク）で流すと終了コード 1 で、落ちた検査の名前が出る
  - 見本のフォルダの台本を触ったときだけ、その見本が --only で選ばれる
  - commit していない変更があると終了コード 2
- 台帳との結び付け（when 列を読んで選ぶ）は、gate 項目が台帳に入る段（R6）で足す。今は対象が 0 件なので作らない

### 第2段以降に回すもの
- R4b：validate-pr-body.sh の成功表示の前（:321）と frontend/.husky/pre-push から呼ぶ（design.md:152-153）。入口の所要時間と誤って止める数を第1段で見てから
- R4c：クラウドの Claude の「流したか」の印（design.md:154-156）。2026-10-31 注記：R4c では印を確かめる案をやめ、クラウドでも pre-push を流す形にした（§R4c）
- gitleaks の履歴走査を手元でどう流すか（今の手元の見張りでは `gitleaks git` が止まる）

### 受入条件
- K1：main と同じ中身で流して終了コード 0。所要秒を測って表示（速い組の目安 120 秒以内）
- K2：違反を入れた写しで終了コード 1、落ちた検査の名前が出る（少なくとも 2 種類の違反で）
- K3：飛ばした検査がすべて名前と理由付きで表示される。必須 16 件の名前（required-checks.txt）が、流したか飛ばしたかのどちらかで全部出る
- K4：試験が手元で rc=0。試験は rule-registry.yml の existing-rule-tests に 1 step 足して毎回流す（2026-10-30 Opus 判断。理由: CI で流れない試験は壊れても気づけない）
- K5：必須 16 件 pass。scripts/ を触るので GO 記録を付ける
- K6：変えるのは check-before-submit.sh・試験・design.md と、rule-registry.yml の existing-rule-tests への 1 step 追加だけ（試験を毎回流すため。2026-10-30 Opus 判断。理由: CI で流れない試験は壊れても気づけない）。呼ぶ側の台本・既存の検査・他のワークフローは変えない
- 実測（事実）：K1b の所要は 124.4 秒で目安の 120 秒を超えた。同じ時間帯に他の処理が走っていて機械が混んでいたため（K1 の空いているときは 88.9 秒）

### リスクと対処
- 手元と CI の版の違いで結果が食い違う → 版を表示し、最後の判定は CI（入口は補助。ideal-state.md:15）
- 遅くて使われない → 速い組だけを既定にし、秒を表示して第2段で見直す
- 必須チェックの一覧が増えたのに入口が追従しない → K3 の試験で required-checks.txt の全件が表示されることを確かめる（名前が足りなければ試験が落ちる）
- 戻し方：revert（呼ぶ側はまだ無いので影響は入口だけ）

### Opus 自己審査（同じ AI の審査。独立の審査は PR で別の審査役が行う）
APPROVE。根拠：命令と所要秒は main で実測した。CI と同じ台本を呼ぶ。設計 §R4 との違い（台帳の when 列を今は読まない）は対象 0 件という事実による順番の入れ替えで、目的（提出前に同じ検査を流す）は変えない。未解決：gitleaks の手元での流し方。

## R4b 提出前の入口を push の前に自動で呼ぶ（第2段・2026-10-30 PO「1」で着手）

### 目的
- 提出前の入口（scripts/dev/check-before-submit.sh）を、人・Codex・Claude が流し忘れても push の前に自動で流す。CI で落ちてから直す手戻りを減らす
- 守りの本体は引き続き CI の必須チェック。入口は手戻りを減らす補助（ideal-state.md:15）

### 現状（事実。2026-10-30 origin/main b334e2448 で調査）
- frontend/.husky/pre-push（35 行）は rebase 中の止め・validate-pr-ownership.sh・active-work 書式の 3 つだけで、重い検査は無い
- core.hooksPath は scripts/new-worktree.sh:115 で作業場所ごとに frontend/.husky を指す。クラウドでも husky は効いた（docs/handoff/cloud-parity/recon.md:23,33）
- validate-pr-body.sh は scripts/gh-pr-create-safe.sh:132 と、手元の PR 本文の見張り（正本 docs/handoff/conversation-consent/hooks/pr-body-guard.sh:189-248。`gh pr create` と `gh pr edit` の両方の前に走る）から呼ばれる。見張りの登録（~/.claude/settings.json:282-285）に timeout の指定は無い
- validate-pr-body.sh は `git rev-parse --show-toplevel`（:9）の作業場所の HEAD とブランチで既存の事前検査をしている（:301-304）
- 入口の所要は速い組で 88.9 秒（空き）〜124.4 秒（混雑）、直し後の実測 188.8 秒（§R4a K1・K1b）
- 入口は commit していない変更があると終了コード 2（check-before-submit.sh:59-63）

### §R4 の当初案から変える点と理由
1. validate-pr-body.sh の中で入口を流すのはやめる。理由: ①validate-pr-body.sh は `gh pr edit` の前にも走るので、本文を直すたびに 90〜190 秒かかる ②見張りの中で長い処理を流すと、見張りの時間切れに当たるおそれがある。代わりに、入口が全部 ○ のときに書く「流した印」を、validate-pr-body.sh が確かめる（クラウド向けに §R4 が決めた印と同じもの。印を 1 つにそろえる）
2. 印が無いときに PR 作成を止めるのは、まだしない。この段では知らせだけを出し、件数を数える。理由: 誤って止める数をまだ測っていない（§R4a「第2段以降に回すもの」）。全セッションの PR 作成を一度に止める変更は、測ってから入れる（変更は一度に 1 つ）

### 変えること
- 入口（check-before-submit.sh）
  - 全部 ○（終了コード 0）で、かつ `--only` を付けずに流したときだけ、印を書く。置き場は `$(git rev-parse --git-dir)/check-before-submit.ok`（作業場所ごとの git の管理場所。コミットされない。作業場所では `.git` がファイルなので §R4 の「.git/ の中」をこの形に読み替える）。中身は流した時点の HEAD の 40 桁 SHA 1 行
  - 流すたびに 1 行の記録を `$(git rev-parse --git-common-dir)/check-before-submit.log` に足す（時刻 UTC・ブランチ・HEAD・終了コード・秒・呼び元（手動か pre-push か））。K8 の測定に使う
  - 審査の残り 4 件
    - (a) `--only fixture-select` だけでは「流した検査 0 件なら終了コード 2」を抜けないようにする（選別の行を流した数に数えない）
    - (b) 見本の名前が `select` のときは終了コード 2 で止める（選別の id と重なるため）
    - (c) 変えない。理由: 変更ファイルの一覧を分岐点との 3 点比較で取るのは、CI が pull_request で比べる統合後の差と同じ範囲になるため。main より遅れた枝で 2 点比較にすると、main 側の変更まで拾ってしまう
    - (d) 必須一覧の数え方を 1 つにそろえる（行頭に空白がある `#` の行も注記として数えない。:70 と :304 を同じ規則にする）
- frontend/.husky/pre-push（既存 3 つの後ろに足す）
  - push される中身が今の HEAD と同じときだけ、入口を流す。違う中身の push や削除のときは「手元の確認は飛ばした」と表示して通す
  - 印がすでに HEAD と同じなら流さずに通す（先に手で流していれば push は待たない）
  - 終了コード 1（× がある）→ push を止める。表示に「直してから push。CI でも同じ検査が落ちる」と書く
  - 終了コード 2（commit していない変更がある・origin/main が無い など、入口が使えない）→ 理由を表示して通す（判定できないものは止めない。最後は CI が止める）
  - 入口はサブシェルで git の環境変数（GIT_DIR など）を消してから呼ぶ（git は hook にこれらを渡すため。https://git-scm.com/docs/githooks 2026-10-30 閲覧）
- scripts/dev/validate-pr-body.sh
  - 成功表示（:321）の前で印を確かめる。印が無い・HEAD と違うときは「提出前の入口をまだ流していません」と知らせ、記録に 1 行足す。この段では終了コードは変えない（止めない）
- 試験（scripts/tests/test_check_before_submit.py に足す）
  - 全部 ○ で印が書かれる。× のとき・`--only` のときは書かれない
  - (a)(b)(d) の直しを確かめる
  - pre-push: × なら止まる。印が HEAD と同じなら入口を流さない。commit していない変更があっても止めない。HEAD と違う中身の push は流さない
  - validate-pr-body.sh: 印が無いと知らせが出て、終了コードは今と同じ
- 手順の文書：docs/ai-agents/executor-checklist.md §0 に「push の前に入口を流す（Claude は Bash の timeout を 600000 にする）。流さないと pre-push が流し、Bash の既定の 2 分で切れることがある」を 1 行足す

### 変えないこと
- CI のワークフロー・必須チェック・Ruleset・既存の検査の台本
- 手元の PR 本文の見張り（~/.claude/scripts/pr-body-guard.sh）とクラウドの見張り（scripts/agent-hooks/cloud/。印を確かめるのは R4c）。2026-10-31 注記：R4c では見張りで印を確かめる案をやめ、クラウドでも pre-push を流す形にした（§R4c）
- `--no-verify` の扱い（すでに決まりで禁止。外しても CI で止まる）

### 受入条件
- K1：main と同じ中身の作業場所で push の前の処理だけを流すと、入口が流れて通り、印が HEAD と同じになる。秒が記録に残る
- K2：違反を入れた写しでは push の前の処理が終了コード 1 で止まる
- K3：印が HEAD と同じなら、push の前の処理は入口を流さずに 5 秒以内で通る
- K4：commit していない変更があっても push の前の処理は止めない（理由を表示）
- K5：validate-pr-body.sh は印が無くても今と同じ終了コード。知らせの文と記録の 1 行が出る
- K6：審査の残り (a)(b)(d) が試験で確かめられ、(c) は理由を設計に残した
- K7：試験が手元と CI（rule-registry.yml の existing-rule-tests。§R4a で足した step）で rc=0。必須 16 件 pass
- K8（反映後の測定）：反映から 7 日の記録で、push の前に止めた回数・そのうち誤って止めた回数・入口の秒の中央値を数える。誤って止めた回数が 0 なら、PR 作成で止める段（R4b-2）へ進む。1 回でもあれば原因を直してから

### リスクと対処
- push が 90〜190 秒待つ → 先に手で流せば待たない（K3）。手順の文書に書く
- Claude の Bash の既定 2 分で push が切れる → push は中断されるだけで何も壊れない。手順の文書に timeout 600000 を書く
- 入口の誤りで全員の push が止まる → 終了コード 2（入口が使えない）は止めない。× の誤りが出たら revert で戻す
- 同じ Mac で複数のセッションが同時に流して遅くなる → 秒を記録し K8 で見る
- 戻し方：merge commit を revert（印と記録は git の管理場所の中のファイルなので、残っても害はない）

### 影響範囲（呼び出し元の全走査）
- frontend/.husky/pre-push：new-worktree.sh で作った全作業場所の push（人・Codex・Claude・クラウド）
- validate-pr-body.sh：gh-pr-create-safe.sh:132、手元の PR 本文の見張り、試験 scripts/tests/test-pr-lifecycle.py:156・scripts/dev/test-agent-hooks.sh:416
- check-before-submit.sh：試験 scripts/tests/test_check_before_submit.py のみ（§R4a で新設）

### Opus 自己審査（同じ AI の審査。独立の審査は PR で別の審査役が行う）
APPROVE。根拠：呼び出し元・時間切れ・所要秒は origin/main と §R4a の実測で確かめた。§R4 からの変更は、止める範囲を狭める側（知らせだけ・判定できないときは通す）で、PO が承認した目的（提出前に同じ検査を流す）は変えない。未解決：pre-push で流したときの実際の秒（K1・K8 で測る）。

## R4c クラウドの AI の変更にも提出前の入口を効かせる（第3段・2026-10-30 PO「1,2」の 2 で着手）

### 目的
- クラウドの AI が push する変更でも、提出前の入口（scripts/dev/check-before-submit.sh）が push の前に必ず流れるようにする
- クラウドで push した枝の PR を手元で作るとき、「入口を流していない」と誤って数えないようにする。R4b の K8（7 日の記録で誤って止めた回数を数える）と、その次の R4b-2（PR 作成で止める段）が正しく判断できるようにする

### 現状（事実。2026-10-30〜31 に origin/main 45b705884・29d962f9b で調査）
- クラウドの実物（一回実行 cse_01W47tdg9DdSZmuoQCyNVKVm、2026-10-30 15:05Z）
  - 入口が使う道具はすべてある：git 2.43.0・bash 5.2.21・perl 5.38.2・python3 3.11.17・node v22.22.0・GNU coreutils 9.4（mktemp・tail・cut）・grep 3.11・sed 4.9
  - 取ってきた直後のリポジトリ（/home/user/salesanchor）では core.hooksPath が未設定（`git config --get core.hooksPath` の終了コード 1）。この状態で push すると frontend/.husky/pre-push は流れない
  - scripts/new-worktree.sh で作業場所を作ると、:115 の `git -C <作業場所> config core.hooksPath frontend/.husky` が共通の設定（/home/user/salesanchor/.git/config）に書かれ、以後は pre-push が流れる
  - 作業場所で pre-push を送信前の処理として流すと、終了コード 0・8 秒。印（check-before-submit.ok）は HEAD と同じ SHA になり、記録に `… 0 7.9 pre-push` の 1 行が足された
- クラウドの実物（一回実行 cse_01W47tdf5Z62r4bG1uaJCwWY、2026-10-30 15:17Z）：new-worktree.sh で作った作業場所（/root/worktrees/salesanchor/release-r4c-cloud-design-doc）から実際に `git push` すると、所有権の検査が通り（「オーナーシップチェック通過」）、入口が流れて rc=0・12 秒。印は作業場所の git ディレクトリに HEAD と同じ SHA で書かれた
- frontend/.husky/pre-push は、入口より前に scripts/validate-pr-ownership.sh を呼ぶ。この検査は、作業場所（`${AGENT_WORKTREE_BASE}`＝`${HOME}/worktrees` か `<本体>/.claude/worktrees` の下）の外からの push（:51-67）と、active-work に登録の無い枝（:84-94）を exit 1 で止める
- frontend/.husky/pre-commit:2-25 は、同じ作業場所の判定で、作業場所の外からの commit を「commit を中断しました: worktree 外での作業は禁止されています」と出して exit 1 で止める（GITHUB_ACTIONS のときは飛ばす）
- frontend/package.json:47 の prepare（`cd .. && husky frontend/.husky`）は、npm install / npm ci のときに core.hooksPath を frontend/.husky/_ に書き換える（new-worktree.sh:112-114 の注記にも同じ説明がある）
- クラウドの決まり（scripts/agent-hooks/cloud/rules.md:9-10）は「調べる・作る・push する」まで。コードを含む枝は push までで、PR は手元で shingo-cc 名義で作る。作業場所を new-worktree.sh で作る決まりは rules.md に無い（AGENTS.md「ブランチと作業場所」には「作業前に必ず（例外なし）」とある）
- 今あるクラウドの実行の登録は一回実行の 5 件で、定期のものは無い。push するものはすべて new-worktree.sh で作業場所を作ってから push している（2026-10-31 に RemoteTrigger の一覧で確かめた）。ただし dispatch.sh は CLAUDE_CODE_REMOTE のクラウドの会話すべてで動くため、登録の無い会話（Web から始めた会話・リモートで分けた担当など）も対象になる。これらの数は数えていない
- 作業場所の外で止めたときの知らせが示す枝名は `feature/morimoto/<トピック名>`（frontend/.husky/pre-commit:21 の固定の文面、scripts/validate-pr-ownership.sh:62-63 の `${AGENT_BRANCH_PREFIX}`＝.claude/agent-config.sh:39）。AGENTS.md の作業場所の枝名は `release/<topic>` で、手元で PR を作る道（gh-pr-create-safe.sh:110）は release/* と hotfix/* だけを通す
- クラウドの見張り（scripts/agent-hooks/cloud/guard_pre_tool.py:623-634 check_pr_create）は、コードを含む枝の PR 作成をすでに止めている。クラウドで作れる PR は文書だけ
- クラウドの SessionStart は scripts/agent-hooks/cloud/dispatch.sh:53-55 が `python3 session_start.py rules.md` を流すだけで、標準入力は渡さない。dispatch.sh:2 で `CLAUDE_CODE_REMOTE` のときだけ動く
- 手元で PR を作る道は 2 つ
  - scripts/gh-pr-create-safe.sh：今の作業場所のブランチの PR だけを作る（:105-109。:123-130 で手元の HEAD と origin の HEAD の一致を確かめる）。印の照合は正しい
  - 手元の PR 本文の見張り（正本 docs/handoff/conversation-consent/hooks/pr-body-guard.sh）：`gh pr create --head <枝>` の枝の作業場所が手元にちょうど 1 つあるときだけ、そこを検証の場所にする（:104-173）。無ければ命令を流した作業場所のまま validate-pr-body.sh を呼ぶ（:245）。命令文に `cd` があるときは枝を求めない（:106）
- validate-pr-body.sh:322-329 は、検証の場所の HEAD と印を比べ、違えば知らせを出して記録に `nostamp` の 1 行を足す。クラウドで push した枝は手元に作業場所が無いため、PR を作るたびに「命令を流した作業場所のブランチと HEAD」で `nostamp` が記録される。これは別の枝の記録で、K8 の数を水増しし、R4b-2 で止める段に進むと毎回誤って止める元になる
- CI で流れる試験は .github/workflows/rule-registry.yml:64-76 の分だけで、validate-pr-body.sh の `nostamp` を試すのは scripts/tests/test_check_before_submit.py（:361-403）。scripts/dev/test-agent-hooks.sh・scripts/tests/test-pr-lifecycle.py・scripts/agent-hooks/cloud/test.sh は CI では流れない
- test_check_before_submit.py を流す job「existing rule tests」（rule-registry.yml:42-43・:76）は、必須チェックの一覧（docs/specs/rule-enforcement/required-checks.txt の 16 件）に入っていない。落ちてもマージは機械では止まらない

### §R4 の当初案から変える点と理由
1. クラウドの見張りで PR 作成の前に印を確かめる案（§R4 の「クラウドの Claude」、§R4b の「変えないこと」の注記）はやめる。代わりに、クラウドでも pre-push が必ず流れるようにする。理由：①クラウドで作れる PR は文書だけで、コードの PR は手元で作る（rules.md:10・guard_pre_tool.py:623-634）。見張りで確かめても、肝心のコードの変更には効かない ②pre-push は push のたびに流れ、クラウドでも 8〜12 秒で終わった（上の実物）③クラウドの記録はその実行が終わると消えるため、見張りで数えても K8 に使えない
2. R4b の K8 の 7 日は、この段の 便1 を手元に入れた時刻から数え直す。理由：それより前の `nostamp` の行は、クラウドの枝の分と本当に流し忘れた分を後から分けられない（記録の行は命令を流した作業場所のブランチ名で書かれる）。PO の決定は「11/6 以降に判断」なので、数え始めが遅れても決定の範囲に収まる

### 変えること
- 便1（手元で PR を作るときの照らし合わせ）
  - docs/handoff/conversation-consent/hooks/pr-body-guard.sh：`gh pr create --head` または `gh pr edit` の対象の枝（:107 からの HEAD_BRANCH）が分かったときは、validate-pr-body.sh に環境変数 `CBS_PR_HEAD_REF=<枝>` を渡す
  - scripts/dev/validate-pr-body.sh：`CBS_PR_HEAD_REF` があり、検証の場所のブランチと違うときは、印を比べない。知らせは「この枝の入口は push した側（クラウドなど）の pre-push が流した。手元の印は無い」に変え、記録に `otherhead` の 1 行を足す。行の 6 列は既存とそろえる：時刻・`<枝>`・`refs/remotes/origin/<枝>` の SHA（取れなければ `-`）・`otherhead`・`0`・`validate-pr-body`。終了コードは今と同じ（止めない）。SHA の列は記録の参考で、pr-body-guard.sh が fetch しないため古い値や `-` になりうる。K6 の数えには使わない
  - scripts/gh-pr-create-safe.sh:132：`env -u PR_BODY_VALIDATE_SKIP` に `-u CBS_PR_HEAD_REF` を足す（手元の shell に残った値で照合を飛ばさないため。この道は今の作業場所の枝だけなので値は要らない）
  - 試験（CI で流れる scripts/tests/test_check_before_submit.py の :361-403 の並びに足す）：①`CBS_PR_HEAD_REF` が今のブランチと違うと `otherhead` の 6 列の行が記録され `nostamp` は記録されない ②同じか無いときは今と同じ動き。scripts/dev/test-agent-hooks.sh（手元だけ）には pr-body-guard.sh が `--head` の枝を `CBS_PR_HEAD_REF` で渡すことを足す
  - 手元の見張りの入れ替え：正本を ~/.claude/scripts/pr-body-guard.sh へ写すのは PO の `!` で行う（見張りの登録は PO が行う決まり。AGENTS.md「作業の型」）。写す台本は scratchpad に用意する
  - 限界：命令文に `cd` がある形（`cd X && gh pr create --head <枝>`）では枝を求めないため、今と同じく `nostamp` が残る（pr-body-guard.sh:106）。K6 ではこの形の行を数えから外せないので、PR 作成は `--head` 単独の形で行う決まり（いまの運用）を続ける
- 便2（クラウドで pre-push を必ず流す）
  - scripts/agent-hooks/cloud/rules.md：「作業を始めたら、ファイルを変える前に `bash scripts/new-worktree.sh release/<topic>` で作業場所を作り、そこで変更・commit・push する（AGENTS.md「ブランチと作業場所」と同じ）。push の前に pre-push が提出前の入口を流す。× なら直してから push。`--no-verify` は使わない。止められたときの知らせは `feature/morimoto/<トピック名>` の枝名を示すが、枝名は `release/<topic>` を使う（手元で PR を作る道が release/* と hotfix/* だけを通すため）」を足す
  - scripts/agent-hooks/cloud/session_start.py：決まり（rules.md）を渡す前に、プロセスの今の場所で `git rev-parse --show-toplevel` を流し、取れたらその場所に `git config core.hooksPath frontend/.husky` を書く（new-worktree.sh:115 と同じ値）。取れない・失敗したときは書かずに決まりだけ渡し、知らせに 1 行足す（止めない）。dispatch.sh は変えない
  - これで止める範囲が広がる点（はっきり書く）：作業場所を作らずにリポジトリ直下で作業すると、①commit の時点で pre-commit:2-25 が「worktree 外での作業は禁止」と出して exit 1 で止める ②commit を含まない枝を直下から push しても、入口より前に所有権の検査が同じ文面と new-worktree.sh の手順を出して exit 1 で止める。今は hooksPath が未設定のため、直下の commit も push も検査なしで通っている。止まるのは AGENTS.md で「例外なし」と決まっている作業場所の決まりに反する commit と push だけで、登録済みの一回実行 5 件はどれも作業場所で commit・push しているので止まらない（上の実物）。登録の無い会話は数えていないが、rules.md の追記はすべてのクラウドの会話に渡る。止められたら、変更を作業場所へ移し（`bash scripts/new-worktree.sh release/<topic>` で作業場所を作り、直下の未 commit の変更をそこで作り直す）、作業場所で commit・push すればよい。知らせの枝名（feature/morimoto/）ではなく rules.md の release/<topic> に従う
  - クラウドの AI が会話の途中で npm install / npm ci を流すと、prepare が core.hooksPath を frontend/.husky/_ に書き換える。この形でも pre-push が提出前の入口を流すことを K4③ で確かめる（pre-commit が流れるかは K4③ では判定しない）（確かめるまでは未確認として扱う）
  - .git/hooks に置かれた hook は core.hooksPath を設定すると使われなくなる。クラウドの .git/hooks に sample 以外の hook があるかを K3 で記録する。あれば止めずに PO に報告し、扱いを決める
- 便1・便2 の実装 PR はどちらも scripts/ に触るため、ADR-135 の承認と GO の記録が要る。ADR-1003 の例外 7 種には当たらないので、Claude Opus への委任 GO で記録する
  - 試験：scripts/agent-hooks/cloud/test.sh の K5（:332-340）に、一時 repo を今の場所にして SessionStart を流すと、その一時 repo の core.hooksPath が frontend/.husky になり、決まりの JSON も出る、を足す。test.sh:284-290 の run() は cwd を指定せず流した場所のリポジトリを使うため、run() に cwd を渡せるようにし、SessionStart を流すケース（今ある :333 を含む）はすべて一時 repo を今の場所にして流す。手元で流すときも書き込み先は一時 repo だけ（手元の本体の .git/config は書かない）ことを、流す前後の本体の値の比較で確かめる。この試験は CI では流れない（手元とクラウドで流す）

### 変えないこと
- クラウドの見張り guard_pre_tool.py（PR 作成の判定）・dispatch.sh・.claude/settings.json
- check-before-submit.sh・frontend/.husky/pre-push・frontend/.husky/pre-commit・validate-pr-ownership.sh・.claude/agent-config.sh（止めたときの知らせの枝名 feature/morimoto/ も変えない。手元の人の作業にも出る文面のため。クラウドには rules.md で release/<topic> を示す）
- CI のワークフロー・必須チェック・Ruleset
- 別件として記録だけするもの：
  - guard_pre_tool.py:400 が整形前の命令文で `psql` を探すため、読むだけの grep の検索の形にある `\|psql` でも止まる（2026-10-30 の一回実行で実際に止まった）。R4c とは別の便で直す（変更は一度に 1 つ）
  - validate-pr-body.sh:301-304 の事前検査（process-artifacts）は、命令を流した作業場所の差分と枝で動く。クラウドの枝の PR では別の枝の差分を見る。前からある挙動で、R4c では変えない

### 受入条件
- K1（便1）：手元で、作業場所の無い枝を `CBS_PR_HEAD_REF` に入れて validate-pr-body.sh を流すと、記録に `otherhead` と枝名の 6 列の 1 行が足され、`nostamp` は足されない。終了コードは今と同じ
- K2（便1）：`CBS_PR_HEAD_REF` が無いか今の作業場所の枝と同じなら、印が無ければ今と同じ `nostamp`、HEAD と同じなら記録なし
- K3（便2）：クラウドの一回実行で、取ってきた直後のリポジトリ直下（new-worktree.sh を流さない）で core.hooksPath が frontend/.husky になっている。あわせて、直下の .git/hooks の中で名前が `.sample` で終わらないファイルの一覧を記録する（0 件なら ○。1 件以上なら止めずに PO に報告）
- K4（便2）：クラウドの一回実行で
  - ①new-worktree.sh で作った作業場所から文書だけを変えた試しの枝を実際に `git push` すると、push の表示に提出前の入口の結果が出て rc=0、印が HEAD と同じになる
  - ②リポジトリ直下で、origin/main から新しい commit を含まない試しの枝を作って `git push` すると、所有権の検査の「worktree 外での作業は禁止」で rc≠0 になり、枝は origin に作られない（`git ls-remote` で確かめる）。直下で試しの文書を 1 行変えて `git commit` すると、pre-commit の「commit を中断しました」で rc≠0 になり、commit は作られない（確かめた後に変更を戻す）
  - ③①の作業場所で `npm ci --prefix frontend` を流したあと、core.hooksPath の値を記録し、試しの文書をもう 1 行変えて commit・`git push` すると、提出前の入口の結果が出て rc=0、印が新しい HEAD と同じになる
  - ①③の試しの枝は確かめた後に消す（main・develop ではない release/ の試しの枝だけ）
- K5：
  - CI の必須 16 件（required-checks.txt）が pass
  - 必須ではない job「existing rule tests」（足した試験 test_check_before_submit.py を流す）が pass。必須ではないため、マージの前に結果を目で確かめて GO の記録に書く
  - CI で流れない試験（test-agent-hooks.sh・cloud/test.sh）は手元で rc=0、cloud/test.sh はクラウドの一回実行でも rc=0。手元の本体の core.hooksPath は試験の前後で同じ
- K6（反映後・R4b の K8 の材料）：便1 を手元に入れた時刻から 7 日の記録で、`nostamp` と `otherhead` を分けて数え、表にして PO に示す。R4b の K8 の判断は `nostamp` だけで行う。K6 自体は数えて示せば ○

### リスクと対処
- 便1 の見張りの入れ替えは PO の `!` が要る → 入れるまで K6 の数え始めを遅らせる。台本 1 行で済む形にする
- 便2 で、作業場所を作らずに直下で commit・push する実行が止まる → rules.md に手順（release/<topic>）を書く。pre-commit と所有権の検査の知らせも new-worktree.sh で作業場所を作る手順を出すが、枝名は feature/morimoto/ を示すため、rules.md に「知らせの枝名ではなく release/<topic> を使う」と書く。止まっても commit が作られない・枝が origin に作られないだけで、release/<topic> の作業場所を作って作り直せば戻る
- クラウドの AI が知らせのとおり feature/morimoto/ の枝で push する → 手元で PR を作る道（gh-pr-create-safe.sh:110）で止まり、本番には出ない。release/<topic> の枝で作り直す
- npm install / npm ci で core.hooksPath が frontend/.husky/_ に変わる → K4③ で、その形でも入口が流れることを確かめる。流れなければ便2 を本番に入れる前に止めて設計を見直す
- クラウドの pre-push が × で push を止め、クラウドの AI が `--no-verify` で外す → rules.md に禁止を書く。外しても CI の必須チェックで止まる
- クラウドの環境が変わり、入口の道具が欠ける → 入口は終了コード 2（使えない）で止めずに通し、CI が止める（R4b の決まりのまま）
- 戻し方：merge commit を revert。便1 の見張りは、前の正本を ~/.claude/scripts/ へ写し直す。便2 で書いた core.hooksPath は、その一回実行の箱の中だけの設定で、実行が終われば消える

### 影響範囲（呼び出し元の全走査）
- pr-body-guard.sh：手元の Claude の `gh pr create`・`gh pr edit`（~/.claude/settings.json の登録）。試験 scripts/dev/test-agent-hooks.sh
- validate-pr-body.sh：gh-pr-create-safe.sh:132（`CBS_PR_HEAD_REF` を外して渡すので今と同じ動き）、pr-body-guard.sh、試験 scripts/tests/test_check_before_submit.py:33・:361-403、test-pr-lifecycle.py:156・test-agent-hooks.sh:416
- session_start.py：dispatch.sh の SessionStart（クラウドだけ）。試験 scripts/agent-hooks/cloud/test.sh の K5（:332-340）
- frontend/.husky/pre-push → scripts/validate-pr-ownership.sh：便2 でクラウドの直下の push でも流れるようになる（止める範囲が広がる点として上に記載）
- frontend/.husky/pre-commit：便2 でクラウドの直下の commit でも流れるようになる（同上）
- frontend/package.json:47 の prepare：便2 の設定を上書きしうる（K4③ で確かめる）
- 記録ファイル check-before-submit.log を読む台本：origin/main を探した範囲では試験だけ

### 審査
- 1 回目（reviewer・opus、2026-10-31）：REVISE。採否に関わる指摘 2 件（①便2 の直下の hooksPath 設定で、直下からの push が所有権の検査で止まるのに「止める範囲は広げない」と書いていた ②足す試験が CI で流れず K5 が何も確かめない）と軽い指摘 5 件（session_start の場所の求め方・§R4b の古い注記・`CBS_PR_HEAD_REF` の受け継ぎ・`cd` 形の限界・記録行の列）。すべてこの版に入れた
- 2 回目（reviewer・opus、2026-10-31）：REVISE。行番号はすべて origin/main と一致。採否に関わる指摘 2 件（①直下では push より先に pre-commit が commit を止めるのに書いていない ②test_check_before_submit.py を流す job は必須 16 件に入っておらず K5 の書き方が事実と違う）と、K4② の手順が pre-commit に当たる点、任意の提案 5 件（.git/hooks の記録・npm install 後の確かめ・GO の記録・:771 の注記・5 件の言い方）。すべてこの版に入れた
- 3 回目（reviewer・opus、2026-10-31）：REVISE。行番号はすべて origin/main と一致し、2 回目の指摘にはすべて応えていた。採否に関わる指摘 1 件（止めたときの知らせが示す枝名は feature/morimoto/ で、rules.md の release/<topic> と「同じ手順」ではない。知らせのとおりに作った枝は手元の PR の道で止まる）と、任意の指摘 4 件（止めない範囲を登録済みの一回実行に限って書く・test.sh の run() に cwd を渡す・K4③ と pre-commit の書き方をそろえる・記録の SHA は古いことがある）。すべてこの版に入れた
- Opus 自己審査（同じ AI の審査）：APPROVE。根拠：pre-commit:2-25・:21、validate-pr-ownership.sh:62-63、agent-config.sh:39、test.sh:284-290、required-checks.txt、rule-registry.yml:42-43・:76、package.json:47 を origin/main で読んで確かめた。直下で止まるのは AGENTS.md の「例外なし」の決まりに反する commit と push だけで、今ある実行は 5 件とも作業場所で commit・push している（RemoteTrigger の一覧）。止める範囲の広がりを隠さずに書き、戻し方を書いた。未解決：session_start が動くときのプロセスの今の場所がリポジトリの中か（K3）、npm ci のあとも入口が流れるか（K4③）、.git/hooks に独自の hook があるか（K3）。どれも便2 の受入で確かめ、満たさなければ便2 を本番に入れない
