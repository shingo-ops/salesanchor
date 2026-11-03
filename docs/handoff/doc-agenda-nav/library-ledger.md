# 決まりの台帳（入口の文書の図書館化）

作成: 2026-11-02 Opus（段0）。根拠: [library-design.md](./library-design.md) §1・§4-1・§9 段0。
このリポジトリは公開されている。ここには節の名前と行番号だけを書き、決まりの本文は書かない。言い直しの対の文は、リポジトリの外の写しのフォルダ（`~/CC報告ファイル-keep/doc-library-20261102/pairs.txt`）にだけ置く。

- 所在は `ファイル:見出し:行番号`。複数あるときは `; ` で区切る。見出しに `:` を含むもの（R-129）があるので、読むときは最後の `:` で行番号を、最初の `:` でファイルを切り離す。
- 行番号は 2026-11-02 の実物（`grep -n`）。段1（2026-11-02）で区切り方を chat-layout.md（1〜10行）に分け、chat-format.md は言葉の選び方だけ（旧11〜31行 → 1〜21行）にした。この表はその後の行番号。段1b（2026-11-03）で ~/kb/AGENTS.md 15行目の括弧書き（R-91 の言い直し側）を消し、R-91 の所在を1つにした（行は残るので行番号は変わらない）。段1c（2026-11-03）で chat-format.md の3行目と7行目（R-92・R-93・R-94 の表示側）を消した。番号は付け直さないので、言葉の選び方の節の始まり（1行目）は変わらない。同じ日に「~/.claude/rules/common/coding-style.md」 の Code Quality Checklist の中の2行（code-review.md の Review Checklist と同じ文）も消した。これは最後の節の中なので、この表の行番号は変わらない。段2b（2026-11-03）で「~/.claude/rules/common/git-workflow.md」（22行）を本「~/.claude/books/git-workflow.md」へ移した（前に frontmatter 5行を足したので、見出しの行番号は元の行番号＋5。見出し行の末尾に `[R-nn]`）。「~/.claude/CLAUDE.md」 の 60行目（`@~/kb/AGENTS.md` の前）に目録の節（見出し1＋目録の行2＋空行1）を足し、その見出しを R-17 にした（目録の見出しも台帳に載せないと `L2_UNTAGGED` が 1 になるため）。
- 種別: 目録（毎回読む）／本（場面で開く）／表示（入力のたびにフックが表示）／paths（場所つきの決まり）。
- R-91〜R-94 は同じ趣旨を2か所に書いた「言い直し」の対。所在が2つある番号の数が `L2_DUP_LEDGER`。R-94 は設計の時点では見つけていなかった3件目。段1c で R-92〜R-94 の表示側を消し、所在はすべて1つになった（PO 2026-11-03「1」）。

| R-nn | 節の名前 | 所在 | 種別 | 移した段 |
|---|---|---|---|---|
| R-01 | 認証情報 | ~/.claude/CLAUDE.md:認証情報:3 | 目録 | 未 |
| R-02 | Context7 | ~/.claude/CLAUDE.md:Context7:9 | 目録 | 未 |
| R-03 | 報告の型 | ~/.claude/CLAUDE.md:報告の型:12 | 目録 | 未 |
| R-04 | 記憶で答えない | ~/.claude/CLAUDE.md:記憶で答えない:36 | 目録 | 未 |
| R-05 | 出力を省略しない（生出力はファイルへ） | ~/.claude/CLAUDE.md:出力を省略しない（生出力はファイルへ）:40 | 目録 | 未 |
| R-06 | 「実行した」と「反映された」は別物 | ~/.claude/CLAUDE.md:「実行した」と「反映された」は別物:45 | 目録 | 未 |
| R-07 | 変更は一度に1つ | ~/.claude/CLAUDE.md:変更は一度に1つ:48 | 目録 | 未 |
| R-08 | 提案の型 | ~/.claude/CLAUDE.md:提案の型:51 | 目録 | 未 |
| R-09 | 迷ったら止まる | ~/.claude/CLAUDE.md:迷ったら止まる:54 | 目録 | 未 |
| R-10 | GAS / clasp | ~/.claude/CLAUDE.md:GAS / clasp:57 | 目録 | 未 |
| R-11 | 優先順位 | ~/kb/AGENTS.md:優先順位:3 | 目録 | 未 |
| R-12 | 絶対ルール | ~/kb/AGENTS.md:絶対ルール:9 | 目録 | 未 |
| R-13 | フォルダ索引 | ~/kb/AGENTS.md:フォルダ索引:19 | 目録 | 未 |
| R-14 | 検査 | ~/kb/AGENTS.md:検査:29 | 目録 | 未 |
| R-15 | PO への返事の区切り方（1〜10行・見出しは # の1つだけ） | ~/kb/00-rules/chat-layout.md:PO への返事の区切り方:5 | 目録 | 段1 |
| R-16 | 言葉の選び方 | ~/kb/00-rules/chat-format.md:言葉の選び方:1 | 表示 | 段1 |
| R-17 | 本の目録（場面で開く。開く前に目録の行を読む） | ~/.claude/CLAUDE.md:本の目録（場面で開く。開く前に目録の行を読む）:60 | 目録 | 段2b |
| R-21 | Commit Message Format | ~/.claude/books/git-workflow.md:Commit Message Format:8 | 本 | 段2b |
| R-22 | Pull Request Workflow | ~/.claude/books/git-workflow.md:Pull Request Workflow:17 | 本 | 段2b |
| R-31 | 担当（サブエージェント） | ~/.claude/rules/common/agents.md:担当（サブエージェント）:3 | 目録 | 未 |
| R-32 | Parallel Task Execution | ~/.claude/rules/common/agents.md:Parallel Task Execution:11 | 目録 | 未 |
| R-33 | Scope Termination（スコープ終了ルール） | ~/.claude/rules/common/agents.md:Scope Termination（スコープ終了ルール）:15 | 目録 | 未 |
| R-41 | Claude Code だけの決まり | CLAUDE.md:Claude Code だけの決まり:5 | 目録 | 未 |
| R-42 | プロジェクト前提 | AGENTS.md:プロジェクト前提:5 | 目録 | 未 |
| R-43 | 不可逆操作は必ず PO 確認 | AGENTS.md:不可逆操作は必ず PO 確認:15 | 目録 | 未 |
| R-44 | VPS 直作業禁止（技術的にも制限付き鍵のみ） | AGENTS.md:VPS 直作業禁止（技術的にも制限付き鍵のみ）:23 | 目録 | 未 |
| R-45 | ブランチと作業場所 | AGENTS.md:ブランチと作業場所:30 | 目録 | 未 |
| R-46 | 作業の型 | AGENTS.md:作業の型:39 | 目録 | 未 |
| R-101 | Purpose | ~/.claude/rules/common/code-review.md:Purpose:14 | paths | 未 |
| R-102 | When to Review | ~/.claude/rules/common/code-review.md:When to Review:18 | paths | 未 |
| R-103 | Review Checklist | ~/.claude/rules/common/code-review.md:Review Checklist:36 | paths | 未 |
| R-104 | Security Review Triggers | ~/.claude/rules/common/code-review.md:Security Review Triggers:50 | paths | 未 |
| R-105 | Review Severity Levels | ~/.claude/rules/common/code-review.md:Review Severity Levels:62 | paths | 未 |
| R-106 | Agent Usage | ~/.claude/rules/common/code-review.md:Agent Usage:71 | paths | 未 |
| R-107 | Review Workflow | ~/.claude/rules/common/code-review.md:Review Workflow:80 | paths | 未 |
| R-108 | Approval Criteria | ~/.claude/rules/common/code-review.md:Approval Criteria:91 | paths | 未 |
| R-109 | Integration with Other Rules | ~/.claude/rules/common/code-review.md:Integration with Other Rules:97 | paths | 未 |
| R-110 | Immutability (CRITICAL) | ~/.claude/rules/common/coding-style.md:Immutability (CRITICAL):14 | paths | 未 |
| R-111 | Core Principles | ~/.claude/rules/common/coding-style.md:Core Principles:26 | paths | 未 |
| R-112 | KISS (Keep It Simple) | ~/.claude/rules/common/coding-style.md:KISS (Keep It Simple):28 | paths | 未 |
| R-113 | DRY (Don't Repeat Yourself) | ~/.claude/rules/common/coding-style.md:DRY (Don't Repeat Yourself):34 | paths | 未 |
| R-114 | YAGNI (You Aren't Gonna Need It) | ~/.claude/rules/common/coding-style.md:YAGNI (You Aren't Gonna Need It):40 | paths | 未 |
| R-115 | File Organization | ~/.claude/rules/common/coding-style.md:File Organization:46 | paths | 未 |
| R-116 | Error Handling | ~/.claude/rules/common/coding-style.md:Error Handling:54 | paths | 未 |
| R-117 | Input Validation | ~/.claude/rules/common/coding-style.md:Input Validation:62 | paths | 未 |
| R-118 | Naming Conventions | ~/.claude/rules/common/coding-style.md:Naming Conventions:70 | paths | 未 |
| R-119 | Code Smells to Avoid | ~/.claude/rules/common/coding-style.md:Code Smells to Avoid:78 | paths | 未 |
| R-120 | Deep Nesting | ~/.claude/rules/common/coding-style.md:Deep Nesting:80 | paths | 未 |
| R-121 | Magic Numbers | ~/.claude/rules/common/coding-style.md:Magic Numbers:84 | paths | 未 |
| R-122 | Long Functions | ~/.claude/rules/common/coding-style.md:Long Functions:88 | paths | 未 |
| R-123 | Code Quality Checklist | ~/.claude/rules/common/coding-style.md:Code Quality Checklist:92 | paths | 未 |
| R-124 | Feature Implementation Workflow | ~/.claude/rules/common/development-workflow.md:Feature Implementation Workflow:18 | paths | 未 |
| R-125 | Skeleton Projects | ~/.claude/rules/common/patterns.md:Skeleton Projects:14 | paths | 未 |
| R-126 | Design Patterns | ~/.claude/rules/common/patterns.md:Design Patterns:26 | paths | 未 |
| R-127 | Repository Pattern | ~/.claude/rules/common/patterns.md:Repository Pattern:28 | paths | 未 |
| R-128 | API Response Format | ~/.claude/rules/common/patterns.md:API Response Format:36 | paths | 未 |
| R-129 | Minimum Test Coverage: 80% | ~/.claude/rules/common/testing.md:Minimum Test Coverage: 80%:14 | paths | 未 |
| R-130 | Test-Driven Development | ~/.claude/rules/common/testing.md:Test-Driven Development:21 | paths | 未 |
| R-131 | Troubleshooting Test Failures | ~/.claude/rules/common/testing.md:Troubleshooting Test Failures:31 | paths | 未 |
| R-132 | Test Structure (AAA Pattern) | ~/.claude/rules/common/testing.md:Test Structure (AAA Pattern):37 | paths | 未 |
| R-133 | Test Naming | ~/.claude/rules/common/testing.md:Test Naming:55 | paths | 未 |
| R-134 | GAS / clasp | ~/.claude/rules/gas-clasp.md:GAS / clasp:7 | paths | 未 |
| R-135 | Standards | ~/.claude/rules/python/coding-style.md:Standards:10 | paths | 未 |
| R-136 | Immutability | ~/.claude/rules/python/coding-style.md:Immutability:15 | paths | 未 |
| R-137 | Formatting | ~/.claude/rules/python/coding-style.md:Formatting:34 | paths | 未 |
| R-138 | Reference | ~/.claude/rules/python/coding-style.md:Reference:40 | paths | 未 |
| R-139 | PostToolUse Hooks | ~/.claude/rules/python/hooks.md:PostToolUse Hooks:10 | paths | 未 |
| R-140 | Warnings | ~/.claude/rules/python/hooks.md:Warnings:17 | paths | 未 |
| R-141 | Protocol (Duck Typing) | ~/.claude/rules/python/patterns.md:Protocol (Duck Typing):10 | paths | 未 |
| R-142 | Dataclasses as DTOs | ~/.claude/rules/python/patterns.md:Dataclasses as DTOs:20 | paths | 未 |
| R-143 | Context Managers & Generators | ~/.claude/rules/python/patterns.md:Context Managers & Generators:32 | paths | 未 |
| R-144 | Reference | ~/.claude/rules/python/patterns.md:Reference:37 | paths | 未 |
| R-145 | Secret Management | ~/.claude/rules/python/security.md:Secret Management:10 | paths | 未 |
| R-146 | Security Scanning | ~/.claude/rules/python/security.md:Security Scanning:21 | paths | 未 |
| R-147 | Reference | ~/.claude/rules/python/security.md:Reference:28 | paths | 未 |
| R-148 | Framework | ~/.claude/rules/python/testing.md:Framework:10 | paths | 未 |
| R-149 | Coverage | ~/.claude/rules/python/testing.md:Coverage:14 | paths | 未 |
| R-150 | Test Organization | ~/.claude/rules/python/testing.md:Test Organization:20 | paths | 未 |
| R-151 | Reference | ~/.claude/rules/python/testing.md:Reference:36 | paths | 未 |
| R-91 | 言い直し(a) 区切り方の要点 | ~/kb/00-rules/chat-layout.md:PO への返事の区切り方:5 | 目録 | 段1b |
| R-92 | 言い直し(b1) 専門用語と普通の言葉 | ~/.claude/CLAUDE.md:報告の型:20 | 目録 | 段1c |
| R-93 | 言い直し(b2) 具体の名前・作業の呼び名 | ~/.claude/CLAUDE.md:報告の型:25 | 目録 | 段1c |
| R-94 | 言い直し(c) 何のためかを2回問い直す | ~/kb/AGENTS.md:絶対ルール:16 | 目録 | 段1c |
