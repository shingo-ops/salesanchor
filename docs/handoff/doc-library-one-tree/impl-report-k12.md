本報告はカード card-impl-k12 の実行結果である

作業開始時 HEAD（push 済み枝の先頭）: a565524dfc1679716e6e355247f2ff238793a2c9（a565524df で始まる、一致）

## §0 生出力
```
$ wc -l
    9 CLAUDE.md
   46 AGENTS.md
   44 docs/INDEX.md
   99 total
$ diff AGENTS
26c26
< - **無制限鍵（`~/.ssh/manual-only/id_ed25519`）**: 本番 DB の読み取りは reader 鍵の道（`docs/handoff/ai-readonly-db-path/usage.md`）を使い、manual-only は使わない。DB 以外の読み取りだけの調査（ログ/設定表示・`ss`/`ps`/`systemctl status`・接続確認）は恒常許可。変更を伴う作業（ファイル作成・コンテナ起動停止・設定変更・再起動・DB 書き込み）は作業ごとに PO の GO が必要（設計担当が GO 原文を依頼文と PR に転記）。ただし、PO が合意した設計の作業手順に書かれ審査役が APPROVE した行は、Opus 本人が実行前に控えを取って実行してよい（ADR-1003 追記 2026-11-02。条件・除外・記録の形は同 ADR。担当（サブエージェント・クラウド）は含まない）
---
> - **無制限鍵（`~/.ssh/manual-only/id_ed25519`）**: 本番 DB の読み取りは reader 鍵の道（`docs/handoff/ai-readonly-db-path/usage.md`）。DB 以外の読み取りだけの調査は恒常許可。変更を伴う作業は作業ごとに PO の GO が必要（例外・条件・記録の形は ADR-1003 と下の詳細）
43c43
< - push・PR/issue の本文・コメントに仕入元の投稿の原文を「」『』で書き写さない。送る前の見張り（`scripts/agent-hooks/confidential-quote-guard/`、ADR-1045）が原文と照らして止める。止められたら語句を消し、形の説明に書き換える。push は `git -C <worktree の絶対パス> push -u origin <ブランチ>` を単独で、本文は Write で作ったファイルを `--body-file <絶対パス>` で渡す（これ以外の形は止まる。commit は heredoc か `-F <絶対パス>` で書ける。見張りの登録は PO が `!` で実行）
---
> - push・PR/issue の本文・コメントに仕入元の投稿の原文を「」『』で書き写さない（見張り ADR-1045 が止める。止められたときの直し方と push・本文の渡し方は `docs/ai-agents/executor-checklist.md`）
45c45
< - 手順や作業方法を答える・計画する前に、必ず目次 `docs/INDEX.md` を開き、章→末端の順にたどって該当する手順書を読む（記憶や推測だけで答えない）
---
> - 手順や作業方法を答える・計画する前に、必ず目次 `docs/INDEX.md` を開き、合う行の手順書を読む（記憶や推測だけで答えない）
$ ls
ls: cannot access 'docs/ai-agents/entry-rule-add.md': No such file or directory
$ grep -c
docs/handoff/rehearsal-env/design-b-ssh-isolation.md:0
docs/ai-agents/executor-checklist.md:0
$ grep -n
21:## §1 調査便（recon）のとき
```

## git diff --stat origin/main（報告 commit 前）
```
 .../release-notification-channel-datetime.md       |   5 -
 AGENTS.md                                          |   6 +-
 CLAUDE.md                                          |   1 +
 backend/app/auth/dependencies.py                   |  20 +-
 backend/app/auth/geo.py                            |   2 +-
 backend/app/auth/permission_catalog.py             |  20 -
 backend/app/metrics.py                             |  39 --
 backend/app/routers/contacts.py                    |   2 +-
 backend/app/routers/discord_channel_invite.py      |   2 +-
 backend/app/routers/discord_role_resync.py         |   2 +-
 backend/app/routers/duplicates.py                  |   2 +-
 backend/app/routers/notifications.py               |  15 +-
 backend/tests/test_new_device_approval.py          |  32 --
 backend/tests/test_notification_event_routing.py   |  21 -
 backend/tests/test_permission_catalog.py           | 138 -----
 backend/tests/test_self_auth.py                    |  94 +---
 backend/tests/test_smoke_auth_least_privilege.py   |  10 -
 docs/INDEX.md                                      |  70 +--
 docs/ai-agents/entry-rule-add.md                   |  16 +
 docs/ai-agents/executor-checklist.md               |   1 +
 .../stageC-geoip-open-mode-card.md                 |  85 ---
 .../stageC-geoip-open-mode-impl-report.md          |  44 --
 docs/handoff/auth-self-hosted-passkey/design.md    |   2 +-
 docs/handoff/block-firebase-token/card.md          | 229 --------
 docs/handoff/block-firebase-token/design.md        |  98 ----
 docs/handoff/block-firebase-token/recon.md         |  40 --
 docs/handoff/build-on-github/adr-draft.md          |  59 ---
 docs/handoff/build-on-github/design.md             | 579 ---------------------
 .../build-on-github/external-cases-dockerd.md      |  72 ---
 docs/handoff/build-on-github/kgi.md                |  29 --
 docs/handoff/build-on-github/recon.md              |  63 ---
 docs/handoff/build-on-github/review-opus.md        |  14 -
 .../discord-buttons-permission/card-impl-1.md      |  47 --
 .../discord-buttons-permission/deploy-record-1.md  |  21 -
 docs/handoff/discord-buttons-permission/design.md  | 118 -----
 .../discord-buttons-permission/impl-report-1.md    | 230 --------
 docs/handoff/discord-buttons-permission/recon.md   |  95 ----
 .../card-channel-datetime.md                       |  59 ---
 .../discord-outside-ticket-notify/design.md        |  27 -
 .../impl-report-channel-datetime.md                |  43 --
 docs/handoff/doc-agenda-nav/baseline.md            |   8 +
 docs/handoff/doc-library-one-tree/card-impl-k12.md |  88 ++++
 docs/handoff/doc-library-one-tree/design.md        |   4 +-
 .../doc-library-one-tree/drafts/AGENTS-C.md        |  46 ++
 .../doc-library-one-tree/drafts/INDEX-C3.md        |  30 ++
 .../doc-library-one-tree/drafts/entry-rule-add.md  |  16 +
 .../external-cases-20261104.md                     | 106 ++++
 .../external-cases-b-20261104.md                   |  86 +++
 .../handoff/doc-library-one-tree/k12-fix-design.md | 161 ++++++
 .../card-impl-3.md                                 | 162 ------
 .../design.md                                      |  73 +--
 .../impl-report-3.md                               |  96 ----
 .../impl-report-4.md                               |  74 ---
 .../rehearsal-env/design-b-ssh-isolation.md        |   4 +
 docs/runbooks/alerts.md                            |  18 -
 docs/specs/doc-agenda-nav/kgi.md                   |   6 +-
 docs/specs/rule-enforcement/rules.yml              |  12 +-
 .../inbox/InboxKartePanel.discordButtons.test.tsx  |  89 ----
 frontend/src/pages/inbox/InboxKartePanel.tsx       |  26 +-
 monitoring/prometheus/alert_rules.yml              |  24 -
 monitoring/prometheus/tests/alert_rules_test.yml   |  56 +-
 61 files changed, 637 insertions(+), 3000 deletions(-)
```

## §5 t1 (check_doc_index --strict)
```
SUMMARY unreached=0 deep=0 blank_when=0 no_when_column=0 broken_link=0 dup_words=0 safety_missing=0 agents_import_missing=0 warnings=0
MAX_DEPTH_TERMINAL 3
rc=0
```

## §5 t2 (check-claude-size)
```
⚠️  tools/claude-channels/intake/CLAUDE.md: LIMITS 未登録 — check-claude-size.js の LIMITS 配列に追加してください（ADR-076・ADR-1040）
✅ CLAUDE.md サイズチェック PASSED
rc=0
```

## §5 t3 (移した行の一致数)
```
1
1
```

## §5 SAME 検査と MISSING 検査
```
SAME
(MISSING 0 行)
```

## §5 t6 (check-before-submit, tail -80)
```
  ○ lint_tenant_schema (strict)                         0.7 秒
  ○ check-claude-size                                   0.1 秒
  ○ generate-adr-index --check                          0.2 秒
  ○ test-ui-governance                                  0.1 秒
  ○ check-ui-governance                                 0.1 秒
  ○ check-dangling-routes                               1.1 秒
  ○ test-dangling-routes                                0.2 秒
  ○ check-lessons-section                               0.0 秒
  ○ check-migration-registration-exists                 0.0 秒
  ○ test-migration-registration-exists                  0.1 秒
  ○ migration-value-writes diff --check 7               0.0 秒
  ○ migration-value-writes diff --check 8               0.1 秒
  ○ migration-value-writes repo                         0.1 秒
  ○ test_migration_value_writes                         6.3 秒
  - check-migration-column-churn                     関連パスの変更なし（CI と同じ条件で対象外）
  - check-migration-duplicate-registration           関連パスの変更なし（CI と同じ条件で対象外）
  ○ check-doc-heading-duplicates                        0.0 秒
  ○ test_check_rule_registry                            1.2 秒

-- 違反の見本（変更に関係するものだけ）--
  ○ 見本の選別（case.json）                      0.0 秒
  - 変更に関係する見本はありません（全件は --full で流せます）

-- 重い組（--full のときだけ）--
  - test-guard-evaluations (node --test)             CI で確かめる（約 120 秒。--full で流せます）
  - run_rule_fixtures（全件）                    CI で確かめる（約 375 秒。--full で流せます）

== 必須チェック（docs/specs/rule-enforcement/required-checks.txt）==
  - pytest (SQLite + PostgreSQL RLS) — CI で確かめる（DB・redis が要る）
  - テナントスキーマ整合性チェック — CI で確かめる（DB が要る）
  △ マイグレーションSQL 実行テスト（実DB） — 一部だけ手元で流した。残りは CI で確かめる（登録ファイルの存在確認だけ。実DBでの実行は CI）
  △ models.py に新 Column → deploy.yml にマイグレーション追記必須 — 一部だけ手元で流した。残りは CI で確かめる（独立した台本の step だけ。ワークフロー内に直接書かれた step は CI）
  ○ ADR-072 tenant schema lint (strict mode) — 手元で流した
  - Lint & Dark Mode Check (ADR-067) — CI で確かめる（npm ci が要り時間がかかる）
  - gitleaks（シークレット漏洩検出） — CI で確かめる（履歴の走査は手元の見張りで止まるため、この段では流さない）
  ○ CLAUDE.md line count check — 手元で流した
  ○ ADR index is up to date — 手元で流した
  ○ UI governance gate — 手元で流した
  ○ dangling-route gate — 手元で流した
  ○ warn-direct-lesson-edit — 手元で流した
  - guard-authoring/evaluation — CI で確かめる（評価本体は GitHub のイベントと権限が要る（台本の試験は --full で流せる））
  - process-artifacts gate — CI で確かめる（PR 本文が要る。PR 作成時に validate-pr-body.sh が確かめる）
  - API contract is up to date — CI で確かめる（uv と npm ci が要る）
  ○ doc index reachability — 手元で流した

== 流した検査 ==
  ○ check_doc_index --strict                            1.0 秒
  ○ check_rule_registry                                 0.2 秒
  ○ lint_tenant_schema (strict)                         0.7 秒
  ○ check-claude-size                                   0.1 秒
  ○ generate-adr-index --check                          0.2 秒
  ○ test-ui-governance                                  0.1 秒
  ○ check-ui-governance                                 0.1 秒
  ○ check-dangling-routes                               1.1 秒
  ○ test-dangling-routes                                0.2 秒
  ○ check-lessons-section                               0.0 秒
  ○ check-migration-registration-exists                 0.0 秒
  ○ test-migration-registration-exists                  0.1 秒
  ○ migration-value-writes diff --check 7               0.0 秒
  ○ migration-value-writes diff --check 8               0.1 秒
  ○ migration-value-writes repo                         0.1 秒
  ○ test_migration_value_writes                         6.3 秒
  - check-migration-column-churn                     流していない: 関連パスの変更なし（CI と同じ条件で対象外）
  - check-migration-duplicate-registration           流していない: 関連パスの変更なし（CI と同じ条件で対象外）
  ○ check-doc-heading-duplicates                        0.0 秒
  ○ test_check_rule_registry                            1.2 秒
  ○ 見本の選別（case.json）                      0.0 秒
  - test-guard-evaluations (node --test)             流していない: CI で確かめる（約 120 秒。--full で流せます）
  - run_rule_fixtures（全件）                    流していない: CI で確かめる（約 375 秒。--full で流せます）

== 版の違い（手元と CI）==
  手元: Python 3.11.18 / node v22.23.4
  CI  : Python 3.12 / node 22（guard-authoring だけ 24）
  版が違うので、最後の判定は CI です（この入口は提出前の補助）

合計 11.7 秒 / 必須 16 件を表示 / 流した検査 18 件 / 落ちた検査 0 件 / ログ /tmp/check-before-submit.V2woj8（消さずに残します）
注意: この枝は main より遅れている。main を取り込んでから流すと CI と同じ結果になる
結果: ○ 流した検査は全部通りました（終了コード 0）
流した印を書きました: /home/user/salesanchor/.git/worktrees/release-k12-index-push/check-before-submit.ok
rc=0
```

## §2b(3) t7 (check_rule_registry, tail -80)
```
== rule registry ==
決まりの文書 46 本 / 決まりの語を含む行 540 / 未仕分け 0 / 台帳 rules 263（gate 0・review 122・exempt 141）・not_rules 118

文書ごと（語を含む行 / rules に入った / not_rules に入った / 未仕分け）:
  AGENTS.md                                                       16    16     0     0
  CLAUDE.md                                                        1     1     0     0
  frontend/AGENTS.md                                              15    13     2     0
  backend/AGENTS.md                                               16    15     1     0
  frontend/CLAUDE.md                                               0     0     0     0
  backend/CLAUDE.md                                                0     0     0     0
  docs/STANDARD-WORKFLOW.md                                       36    31     5     0
  docs/ai-agents/adr-template.md                                   0     0     0     0
  docs/ai-agents/aeon-delivery.md                                  0     0     0     0
  docs/ai-agents/aeon-operation.md                                 0     0     0     0
  docs/ai-agents/aeon-release.md                                   0     0     0     0
  docs/ai-agents/aeon-routing.md                                   1     0     1     0
  docs/ai-agents/agent-roles.md                                    4     4     0     0
  docs/ai-agents/codex-operations.md                              10     8     2     0
  docs/ai-agents/design-partner-preamble.md                        1     1     0     0
  docs/ai-agents/design-partner.md                               106    88    18     0
  docs/ai-agents/dev-commands.md                                   5     3     2     0
  docs/ai-agents/entry-rule-add.md                                 1     1     0     0
  docs/ai-agents/evidence-registry.md                            218     3   215     0
  docs/ai-agents/executor-checklist.md                            13    10     3     0
  docs/ai-agents/executor-preamble.md                             10     8     2     0
  docs/ai-agents/kpi.md                                            5     0     5     0
  docs/ai-agents/lessons.d/20260720-checkout-staged.md             0     0     0     0
  docs/ai-agents/lessons.d/20260720-required-checks-change.md      1     0     1     0
  docs/ai-agents/lessons.d/20260721-deploy-not-done.md             1     0     1     0
  docs/ai-agents/lessons.d/20260721-moving-target-freeze.md        1     0     1     0
  docs/ai-agents/lessons.d/20260721-process-hardening-recon.md     0     0     0     0
  docs/ai-agents/lessons.d/20260721-server-resource-lessons.md     1     1     0     0
  docs/ai-agents/lessons.d/20260722-design-partner-preflight.md     3     1     2     0
  docs/ai-agents/lessons.d/20260724-card-output-markers.md         0     0     0     0
  docs/ai-agents/lessons.d/20260724-guard-drill-verification.md     4     3     1     0
  docs/ai-agents/lessons.d/20260724-merge-gate-mechanics.md        4     3     1     0
  docs/ai-agents/lessons.d/20260725-card-hygiene.md                1     1     0     0
  docs/ai-agents/lessons.d/20260725-merge-waits.md                 3     3     0     0
  docs/ai-agents/lessons.d/20260727-prnum-adr-index.md             1     1     0     0
  docs/ai-agents/lessons.d/20260728-go-record-labels.md            0     0     0     0
  docs/ai-agents/lessons.d/20260728-precheck-guards.md             1     1     0     0
  docs/ai-agents/lessons.d/20260831-card-design-failures.md        3     1     2     0
  docs/ai-agents/lessons.d/20260902-data-durability.md            10     7     3     0
  docs/ai-agents/lessons.d/20260904-discord-reaction-recon.md      5     3     2     0
  docs/ai-agents/lessons.d/20260907-note-ja-merge-cleanup.md       3     3     0     0
  docs/ai-agents/lessons.d/20260916-haiku-readonly-governance.md     3     2     1     0
  docs/ai-agents/lessons.d/20261015-go-record-delegated-issuer.md     4     2     2     0
  docs/ai-agents/ops-incident-agent.md                            12    10     2     0
  docs/ai-agents/task-template.md                                  6     6     0     0
  docs/specs/branch-operations/README.md                          15    11     4     0

結果: 合格（警告 0）
rc=0
```

## git log --oneline -3（報告 commit 前）
```
e4014c40d docs: 目次を短い表にして会話の始めに読み込む（案 C3、K12）
a565524df docs: K12 実装カードに決まり台帳への登録（§2b）を足す
abc7a6239 docs: K12 19/20 on draft C3; raise the K9 limit to 7.5k (PO decision) and add the implementation card
```

最終 HEAD は報告 commit 後の git rev-parse HEAD（push 後の応答に記載。報告自身の sha は報告内に書けないため直前 commit は上の log 先頭）。

DONE
