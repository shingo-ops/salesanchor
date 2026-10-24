# K11 意味の対応表（段3c-2 入口の入れ替え）

> この文書は何か：入口（AGENTS.md・CLAUDE.md）を短い案文に入れ替えるとき、一字一句の一致では見つからない行が、入れ替え後のどこに同じ意味で在るかを1行ずつ示す表です（KGI-11）。設計: design.md §23・§24。

- 起点: d298ab129（段3c-1 #4708 のマージ後の origin/main）。CLAUDE.md 88行・AGENTS.md 110行、空行以外 128行。
- 「入口」は入れ替え後の AGENTS.md（= draft/AGENTS.entry.md、53行）と CLAUDE.md（= draft/CLAUDE.entry.md、9行）。行番号は入れ替え後のもの。
- 「目次」は入れ替え後の docs/INDEX.md。行番号は変わりやすいので、指す先（リンク）で示す。
- 一字一句の一致（入口に 27行・docs に 51行）はこの表に載せない。一致の確かめ方は design.md §24。
- 「削除」は移り先を作らないと判断した行。理由を書く。

| 起点の行 | 起点の中身（要約） | 入れ替え後の在りか | 備考 |
|---|---|---|---|
| CLAUDE.md:3 | チーム共通の真実のみ・個人設定と初期セットアップの場所 | CLAUDE.md:9（個人設定は `~/.claude/CLAUDE.md`、初期セットアップは `docs/onboarding/claude-code.md`）・AGENTS.md:3 | 「チーム共通の真実のみ」は AGENTS.md:3「全 AI 共通の入口。決まりの本文はここが正本」が言い直す |
| CLAUDE.md:10 | 役割分担は codex-operations.md | 目次（codex-operations.md の行。「役割分担を確かめるとき」） | |
| CLAUDE.md:11 | 事業 Sales Anchor (salesanchor) | AGENTS.md:8 | 「(salesanchor)」の補足だけ落ちる |
| CLAUDE.md:15 | 仕様書 docx 他3冊 | 目次（業務の仕様書の行） | G3（段3c-1 で追加済み） |
| CLAUDE.md:16 | 設計判断は ADR・メモリを根拠にしない・ADR 変更後は一覧を作り直す | AGENTS.md:12・目次（ADR の一覧の行。`node scripts/generate-adr-index.js`） | 必須チェック「ADR index is up to date」は CI が強制 |
| CLAUDE.md:23 | 無制限鍵の見出し（PO 決定 2026-09-30 の注記つき） | AGENTS.md:26 | PO 決定の経緯は git の履歴 |
| CLAUDE.md:24 | reader 鍵の道・読み取り調査は恒常許可・変更は作業ごとに GO | AGENTS.md:26 | 本文は同じ。字下げと太字だけ違う |
| CLAUDE.md:25 | 鍵の値を表示しない・人間の無制限鍵を変えない | AGENTS.md:27 | 字下げだけ違う |
| CLAUDE.md:38 | 見出し「ブランチ運用ルール」 | AGENTS.md:30「ブランチと作業場所」 | この見出しを指していた2件は段3c-1 で直した |
| CLAUDE.md:40 | origin/main から release/* を作る・develop 起点は廃止・develop は残置 | AGENTS.md:34・:35・docs/specs/branch-operations/README.md §3-3 | |
| CLAUDE.md:41 | 作業前に必ず new-worktree.sh --claude・詳細は PARALLEL_TERMINAL_GUIDE | AGENTS.md:34・CLAUDE.md:7・目次（並行ターミナルの使い方の行） | G6（この便で目次に1行足す） |
| CLAUDE.md:42 | .claude/agents 変更前は git pull | CLAUDE.md:8 | |
| CLAUDE.md:43 | develop/main への直接コミット禁止 | AGENTS.md:32 | |
| CLAUDE.md:59 | 見出し「標準開発フロー（正本: docs/STANDARD-WORKFLOW.md）」 | AGENTS.md:42 | |
| CLAUDE.md:61 | 作業前に STANDARD-WORKFLOW を読む・3フェーズ・B 区分は KGI の PO 承認不要 | AGENTS.md:42・docs/STANDARD-WORKFLOW.md:23・:79 | |
| CLAUDE.md:65 | 見出し「実行役 preflight」 | AGENTS.md:39「作業の型」 | |
| CLAUDE.md:67 | 実行役は preflight を必ず実行 | AGENTS.md:41 | 「(CC/Codex)」が「実行役は」に |
| CLAUDE.md:77 | 見出し「データ手動 DB INSERT の原則禁止（ADR-025）」 | AGENTS.md:21（本文に ADR-025 の詳細リンクあり） | G5（本文は一字一句 AGENTS.md:21 に在る） |
| CLAUDE.md:83 | 見出し「ADRと実装の優先順位（最上位原則）」 | AGENTS.md:13 | |
| CLAUDE.md:84 | ADR と実装が食い違えば ADR を優先 | AGENTS.md:13 | |
| CLAUDE.md:88 | 作業前/commit前/PR前は executor-checklist | AGENTS.md:43 | |
| AGENTS.md:3 | Codex 向け・CLAUDE.md に対応するファイル | AGENTS.md:3 | 入れ替え後は全 AI 共通の正本 |
| AGENTS.md:10 | 役割分担・Codex の運用・開発コマンド | 目次（codex-operations.md・dev-commands.md の行） | |
| AGENTS.md:14 | 見出し「Generator Executor 切り替え（ADR-082）」 | 削除 | 廃止済みの節。経緯は ADR-082 と git の履歴 |
| AGENTS.md:16 | 上の節は #2715 で廃止済み | 削除 | 同上 |
| AGENTS.md:22 | 設計判断は ADR・チャット履歴を根拠にしない | AGENTS.md:12 | |
| AGENTS.md:23 | KPI 正本は kpi.md | 目次（KPI の正本の行） | G4（段3c-1 で追加済み） |
| AGENTS.md:27 | 見出し「実行役 preflight」 | AGENTS.md:39 | |
| AGENTS.md:29 | 実行役は preflight を必ず実行 | AGENTS.md:41 | |
| AGENTS.md:33 | 見出し「ブランチ運用ルール」 | AGENTS.md:30 | |
| AGENTS.md:35 | origin/main から release/* を作る | AGENTS.md:34・docs/specs/branch-operations/README.md §3-3 | |
| AGENTS.md:36 | develop/main への直接コミット禁止 | AGENTS.md:32 | |
| AGENTS.md:37 | release/* → main は PR 経由 | AGENTS.md:32 | |
| AGENTS.md:51 | 不可逆操作の一覧（1行目） | AGENTS.md:17 | AGENTS.md:17 は CLAUDE.md 版の一覧（Required Status Check を含む上位集合） |
| AGENTS.md:52 | 同（2行目） | AGENTS.md:17 | 同上 |
| AGENTS.md:53 | 同（3行目） | AGENTS.md:17 | 同上 |
| AGENTS.md:59 | i18n（1文目） | AGENTS.md:49 | CLAUDE.md:73 と同じ中身（1行にまとまっている） |
| AGENTS.md:60 | i18n（2文目） | AGENTS.md:49 | 同上 |
| AGENTS.md:64 | 見出し「サブディレクトリ別ルール」 | AGENTS.md:45 | |
| AGENTS.md:66 | 表の見出し行 | AGENTS.md:45・目次（frontend・backend の行） | |
| AGENTS.md:67 | 表の区切り行 | 同上 | |
| AGENTS.md:68 | frontend/ → frontend/AGENTS.md | AGENTS.md:45・目次（frontend の行） | |
| AGENTS.md:69 | backend/ → backend/AGENTS.md | AGENTS.md:45・目次（backend の行） | |
| AGENTS.md:73 | 見出し「ADR 一覧」 | AGENTS.md:12・目次（ADR の一覧の行） | |
| AGENTS.md:75 | ADR 一覧は docs/adr/README.md（自動生成） | AGENTS.md:12 | |
| AGENTS.md:79 | 見出し「このファイルの自動更新ルール」 | 削除 | AGENTS.md が正本1か所になり、CLAUDE.md の決定を AGENTS.md へ写す決まりは不要。ユーザー側 ~/.claude/CLAUDE.md の同じ決まりは段6 |
| AGENTS.md:81 | メモリ保存時に AGENTS.md も更新（1行目） | 削除 | 同上 |
| AGENTS.md:82 | 同（2行目） | 削除 | 同上 |
| AGENTS.md:84 | 更新トリガー例 | 削除 | 同上 |
| AGENTS.md:88 | 見出し「実装役の常設ルール（カード運用）」 | docs/ai-agents/executor-preamble.md:1（目次の「実装役への指示の定型文」の行） | 節の本文 :90-110 は一字一句 docs に在る |

合計 50 行（CLAUDE.md 21・AGENTS.md 29）。
