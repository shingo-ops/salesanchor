# worktree guardrail close recon

親参照: [docs/specs/branch-operations/README.md](/Users/tanizawashingo/salesanchor/docs/specs/branch-operations/README.md) §3-3

この文書は何か（専門用語なしの1行）:
抜け道を塞ぐ前に、どこを塞ぐと人が詰まるかを実物で確認するための調査メモ。

## 結論

- 本当の砦はサーバ側（GitHub gate / Ruleset）で、ローカル抜け道封じは補助として切り分けられる: **YES**
- 抜け道を塞いでも締め出しを起こさない条件: **new-worktree.sh が正規入口として動き、active-work 自動登録が崩れず、release/* / hotfix/* の main 向け例外と break-glass 非常口を残すこと**
- 緊急の非常口が塞がれず生き残るか: **YES**

## ADR 検索結果

- `docs/adr/ADR-074-worktree-agent-enforcement.md`
- `docs/adr/ADR-086-parallel-development-standardization.md`
- `docs/adr/ADR-114-worktree-auto-cleanup.md`
- `docs/adr/ADR-135-release-stowaway-prevention.md`
- `docs/adr/ADR-136-cc-bot-github-identity.md`

## Q1. 抜け道の実体とローカルフック

- `git commit --no-verify` は `pre-commit` と `commit-msg` を bypass する。Git 公式仕様のため、`frontend/.husky/pre-commit` のようなローカル commit フックは `--no-verify` で回避できる。`git push --no-verify` は `pre-push` を bypass する。  
  参考: `frontend/.husky/pre-commit:1-31`, `frontend/.husky/pre-push:1-35`, Git 公式 `--no-verify` 仕様
- `frontend/.husky/pre-commit:16-28` は worktree 外の commit を止め、例外は `active-work.md` のみ変更のときだけ。
- `frontend/.husky/pre-push:21-34` は rebase 進行中の push を止め、`scripts/validate-pr-ownership.sh` と active-work 形式検証を呼ぶ。
- `scripts/validate-pr-ownership.sh:45-66` は worktree 外からの push を止める。
- `scripts/validate-pr-ownership.sh:69-91` は `active-work.md` に `| branch |` がない push を止める。
- `scripts/validate-pr-ownership.sh:100-126` は feature ブランチの `develop` 乖離を止めるが、`release/*` と `hotfix/*` は例外にしている。
- `scripts/validate-pr-ownership.sh:135-146` は既に merge 済みの PR への追加 push を止める。
- 正しい入口は `scripts/new-worktree.sh` で、`scripts/new-worktree.sh:69-90` が worktree 作成の正規経路、`scripts/new-worktree.sh:118-155` が active-work への自動登録と重複ガード。

## Q2. 文字だけか、GitHub 承認 identity まで見るか

- `scripts/check-process-artifacts.js` は PR の GitHub review identity を見ていない。見ているのは PR 作者 login と PR 本文文字列、そして diff のファイル区分。
- PR 作者チェックは `scripts/check-process-artifacts.js:567-589`。ここで見ているのは `gh api` で取る `.user.login` だけで、review/approve の identity ではない。
- GO 記録検証は `scripts/check-process-artifacts.js:184-259`。`GO発行者` と `GO原文` を PR 本文からパースし、`AUTHORIZED_GO_ISSUERS = ['shingo-ops', 'Shingo']` と `GO #<PR番号>` 形式・番号一致を確認している。
- 実際の判定は `scripts/check-process-artifacts.js:691-727` で、危険変更なら GO 記録の文字列が揃っているか、ユーザー影響変更や外部 API 変更なら GO 記録があるかを確認する。GitHub の Approve / Review state を読む分岐はない。
- したがって gate は **案a ではなく案b寄り** だが、ここでの「b」は **実際の GitHub Approve identity ではなく、PR 本文に転記された PO の GO 文字列と author login** を突き合わせる構造を指す。GitHub Review の本人性確認そのものはしていない。

## Q3. main / develop へのマージは PO Approve なしでも成立するか

- `docs/BRANCH_PROTECTION_SETUP.md:230-243` にある通り、危険変更は `process-artifacts gate`、通常 PR は CI 緑で通る構造になっている。
- `docs/BRANCH_PROTECTION_SETUP.md:298-314` で `process-artifacts gate` は develop Ruleset の required status checks に入っている。
- `docs/BRANCH_PROTECTION_SETUP.md:48-51` で main 側にも `process-artifacts gate` を required status check として追加済みと書かれている。
- `docs/BRANCH_PROTECTION_SETUP.md:130-141` と `docs/adr/ADR-136-cc-bot-github-identity.md:91-108` に break-glass があるため、PO GitHub Approve がなくても本番障害復旧時は 0-Approve マージ経路が残る。
- ただし通常の危険変更は `scripts/check-process-artifacts.js:692-727` により PR 本文の GO 記録が無いと通らない。よって **「PO アカウントの GitHub Approve だけでなくても成立する」が、無条件ではない**。GitHub を開かず完全完結できるかは、危険変更であれば **PO が GO を PR 本文に転記する運用が前提**。

## Q4. bot / agent では偽造しにくい要素

- GitHub Review そのものの本人性はこの gate では見ていない。
- ただし `scripts/check-process-artifacts.js:234-257` の `GO発行者` は `shingo-ops` / `Shingo` 以外を落とすので、bot / agent のログイン名を入れても通らない。
- `scripts/check-process-artifacts.js:243-252` の `GO原文: GO #<PR番号>` は PR 番号まで完全一致が必要なので、別 PR への流用も通らない。
- `CLAUDE.md:55-58` と `docs/BRANCH_PROTECTION_SETUP.md:136-139` は、緊急時の break-glass でも Shingo 即時報告と事後 Approve を要求する。
- つまり、bot / agent が単独で作れない偽造不能要素は **PR 本文中の PO 名義 GO 記録** と **緊急時の人間報告・事後 Approve**。GitHub Review identity 自体は gate の検証対象外。

## Q5. `permit-danger.sh`・ADR-136・§6 の連動

- この checkout では `permit-danger.sh` は見つからなかった。代わりに、危険変更の管制は `scripts/check-process-artifacts.js:691-727` と `docs/adr/ADR-136-cc-bot-github-identity.md:30,46,63-69,102-108` にある。
- `docs/STANDARD-WORKFLOW.md:85-96` は、危ない変更は自己判断で通さず、人間承認または緊急特例で開くと定義している。
- `docs/STANDARD-WORKFLOW.md:69-74` は、不明を残したまま実行しないことを明文化している。
- `docs/PARALLEL_TERMINAL_GUIDE.md:21-33` と `docs/adr/ADR-086-parallel-development-standardization.md:45-58` は、worktree 正規入口と active-work 自動登録を正本化している。
- 申告ルールの置き場としては、`docs/STANDARD-WORKFLOW.md:69-74` の不明点プロトコルが最も自然で、ここに「フック/門番で止まったらこじ開けず PO に申告」を寄せるのが重複が少ない。`CLAUDE.md:55` の break-glass とも矛盾しない。
- 機械が強制しているのは主に **文字** であり、GitHub の approval identity ではない。例外として、break-glass の実運用だけは人間の報告と事後 Approve が必要。

## 参考ファイル

- [docs/PARALLEL_TERMINAL_GUIDE.md](/Users/tanizawashingo/salesanchor/docs/PARALLEL_TERMINAL_GUIDE.md)
- [docs/STANDARD-WORKFLOW.md](/Users/tanizawashingo/salesanchor/docs/STANDARD-WORKFLOW.md)
- [docs/BRANCH_PROTECTION_SETUP.md](/Users/tanizawashingo/salesanchor/docs/BRANCH_PROTECTION_SETUP.md)
- [docs/adr/ADR-086-parallel-development-standardization.md](/Users/tanizawashingo/salesanchor/docs/adr/ADR-086-parallel-development-standardization.md)
- [docs/adr/ADR-135-release-stowaway-prevention.md](/Users/tanizawashingo/salesanchor/docs/adr/ADR-135-release-stowaway-prevention.md)
- [docs/adr/ADR-136-cc-bot-github-identity.md](/Users/tanizawashingo/salesanchor/docs/adr/ADR-136-cc-bot-github-identity.md)
- [scripts/new-worktree.sh](/Users/tanizawashingo/salesanchor/scripts/new-worktree.sh)
- [scripts/validate-pr-ownership.sh](/Users/tanizawashingo/salesanchor/scripts/validate-pr-ownership.sh)
- [scripts/check-process-artifacts.js](/Users/tanizawashingo/salesanchor/scripts/check-process-artifacts.js)
