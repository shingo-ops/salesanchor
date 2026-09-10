# Phase 3 設計 — ブランチ運用：develop 廃止後の開発環境

> この文書は何か: develop廃止を、どういう順番でどう実現するかを描いた設計図。

**対象ADR**: ADR-056（Human-in-the-Loop Minimization／develop への自動化）
**仕様書**: ../../specs/branch-operations/README.md
**recon**: ./recon.md（docs/handoff/branch-operations/recon.md）
**日付**: 2026-07-01
**担当**: Planner（Claude）

---

## 外部・過去事例の参照と我々への応用

- 事例1: Git Flow から Trunk-Based Development への移行（業界一般）→ 我々への応用: 長命の develop を廃し main 一本に集約する流れは業界的に確立。要点は「開発動線の既定 base の切替」と「develop 前提の自動化の除去」を撤去前に完了させること。本設計もこの順（付替→撤去）を踏襲。
- 事例2: 過去 #2701（develop→main 完全集約）→ 我々への応用: develop の中身は main に完全反映済み（recon §1・main..develop=0）。back-merge 不要という判断の根拠。捨てる部屋は掃除しない原則を適用。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| PR既定 base が main（develop でない） | scripts/gh-pr-create-safe.sh:56 が --base main に変更されている（grep 目視＋実PR作成で確認） |
| 削除対象3ファイルが存在しない | git ls-tree origin/main -- .github/workflows/{auto-back-merge,auto-release-pr,claude-pipeline}.yml が空 |
| 書換8ファイルに develop 記述が残っていない | 各 file の該当行（recon §2）が main に変更済み（grep 確認） |
| 第1便PRが main にマージ・CI緑・自筆GO | PR本文に自筆GO記録＋CI success |
| 第1便完了時に develop がまだ存在 | git ls-remote origin develop が非空（撤去前の中止可能性を担保） |
| UI governance が main の鍵に必須追加 | gh api repos/.../rules/branches/main に ui-governance-gate が含まれる |
| dangling-route が main の鍵に必須追加 | 同上に dangling-route gate が含まれる |
| worktree 整合性が main 宛で発火 | worktree-integrity-check.yml の on: に main が含まれる |
| 「develop にあって main に無い守り」がゼロ | 撤去前の鍵・検問突合で develop 専属の守りが残っていない |
| develop が存在しない（撤去完了） | git ls-remote origin develop が空 |
| 撤去後 main CI に develop 由来の失敗なし | 撤去直後の main CI が success（failure/cancelled=0） |
| 本番アプリ正常 | app.salesanchor.jp が正常表示 |

## 技術 How・KPI

## 維持の仕組み

- 守り手: 人手で守る（PO が第1.5便の実地確認を行い、main/develop の両方で gate が効くことを目視で確認するため）
- この設計は `docs/handoff/branch-operations/recon.md` の実物確認と対で維持する。
- 守りの移設は `main` と `develop` の両方で必須チェックを一致させ、片側だけ弱くなる状態を作らない。
- 第1.5便で移設した守りは、PO の実地確認後に第2便以降の撤去に進む。

基本方針: 「行き先を全て main へ付替 → devの守りを main へ移設 → 撤去 → 後片付け」。撤去は最後、撤去前は中止可能。

第1便（動線付替）:
- 削除: auto-back-merge.yml, auto-release-pr.yml, claude-pipeline.yml（ADR-056廃止＝R）
- 書換: gh-pr-create-safe.sh:56/66, pr-base-check.yml:27, executor-preflight.sh:74, new-worktree.sh:73, backfill-active-work-done.sh:72, reaper-worktree.sh:214/229, validate-pr-ownership.sh:36, validate-worktree-start.sh:47 の develop→main
- 除外: `.github/workflows/deploy.yml`（危険ファイル・後片付けへ）、検問の branches:[main,develop] 欄（後片付けへ）
- KPI: 上表の第1便該当基準が全て○

第1.5便（守りの移設）:
- main の鍵に UI governance gate・dangling-route gate を必須追加
- worktree-integrity-check.yml を main 宛でも発火するよう変更
- KPI: 「develop にあって main に無い守り」がゼロ

関門（撤去前・しんご実地確認）:
- 新動線(release/→main)で開発を一度通し、動線が詰まらない＋守りが効くことをしんごが○判定
- ここが撤去可否の分岐。×なら撤去せず修正へ戻る

第2便（鍵外し）: develop の deletion ルールを外す
第3便（撤去・唯一の危険操作）: develop の SHA を控え→自筆GO→削除→検算（確認→退避→試し→GO→実行→検算）
第4便（後片付け）: 検問の develop 欄整理、`.github/workflows/deploy.yml` stamp の目印を main へ、記録

## 弊害・トレードオフ

- リスク1: ADR-056（AI自動化）を廃止する → 対策: しんごの「全手動GO」方針に合致。将来必要なら練習場を作り直せる。R確定（仕様書§3-3）
- リスク2: 撤去後 `.github/workflows/deploy.yml` stamp が毎回失敗ログを出す（continue-on-error で握り潰される）→ 対策: 第4便で stamp の目印を main へ修正。実害ゼロだが恒常赤stepを消す
- リスク3: 撤去は不可逆 → 対策: 第3便で SHA を控え、問題時は復元。撤去前は全便で中止可能

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | 第1便: 動線付替（削除3・書換8） | Generator |
| 2 | 第1.5便: 守りの移設（鍵2・worktree検問） | Generator |
| 3 | 関門: しんご実地確認（動線＋守り） | PO |
| 4 | 第2便: develop 鍵外し | Generator（自筆GO後） |
| 5 | 第3便: develop 撤去（危険操作） | Generator（自筆GO後） |
| 6 | 第4便: 後片付け・記録 | Generator |

## 継続・申し送り

- 各便は独立PR。第3便のみ危険操作（自筆GO必須）。
- CC は本設計の How を自己流に変えない。指定外ファイルへの書き込み禁止（本セッションで逸脱2回・要警戒）。
- 撤去後、本仕様書の KGI7（守りの引き継ぎ）を最終確認し evidence-registry に記録。


## 2026-09-10: 作成時に既存worktreeを保持する指定

この節は、他の作業場所を消さずに新しい作業場所を作れるようにする変更案。
親: [ブランチ運用](../../specs/branch-operations/README.md)。根拠: [recon.md](recon.md)の同日節。
状態: 草案。設計担当が作成し同一AIで自己審査。恒久仕様へのPO承認、実装、マージは未実施。
実装持ち込み時の様式: mode: handoff（ADR-113）。既存のdevelop廃止履歴は改訂しない。

### 目的・対象と対象外

公式入口に --preserve-existing を追加し、その呼出しからの既存worktree削除を0件にする。origin/main起点・上限・担当登録・所有検証を維持する。
対象は new-worktree.sh の引数処理、回収呼出し分岐、保持時の上限案内、試験と使用手順。
回収スクリプト、定期ジョブ、削除条件、既存worktree・台帳の整理、上限引上げ、フック無効化は対象外。
PMG総合画面の製品変更とは別便。本セッションは文書のみを扱う。

### 変更前後の契約（提案）

1. 呼出し形式は `bash scripts/new-worktree.sh <branch> [--claude] [--preserve-existing]`。2つの指定は順不同、各1回まで。ブランチ欠落・未対応指定・重複指定・余分な位置引数はexit 2。引数検証をgit呼出しや回収より前に行い、不正時の副作用を0にする。
2. --preserve-existing 指定時は回収スクリプトを一切呼ばない。通常経路と上限到達時のdry-runの両方が対象。削除の実行コマンドを案内しない。ログに「今回の作成では既存作業場所を回収しない」と表示する。末尾の worktree remove / branch -d 案内も保持指定時は表示せず、通常指定時だけ従来どおり表示する。
3. 指定なしの正常な既存呼出しは従来どおり。--claude だけの場合も維持。--claude を明示しなければ別AIを起動しない。
4. 件数は既存方式・上限値を使用する。上限以上ならexit 1、新規作成・fetch・UUID発行・台帳作成なし。保持時は「上限に達したため未作成。既存作業場所の保持条件をPOと確認」と案内する。上限の変更は行わない。
5. 上限未満なら既存のfetch→origin/main起点作成→フック設定→UUID→分割台帳という処理を再利用する。既存の分岐の失敗を無視する変更を加えない。残存する既存不具合の修正は別件。
6. --preserve-existing は旧worktreeを永続保護する機能ではない。定期回収・他者の操作は制御しない。保持保証はこの呼出しが削除を起動しない範囲に限定する。
7. 現行版は新指定を無視して実削除に進む。導入済みかの試しとして旧版に新指定を渡してはならない。導入PRのマージSHAと、実行対象ファイルが当該承認版または後続の確認済み版であることを読み取りで確認してから使用する。旧版・確認不能なら停止する。

### 変更候補ファイルと正式化

実装候補: scripts/new-worktree.sh、scripts/tests/test-new-worktree-preserve.sh（新規）。
手順更新候補: docs/PARALLEL_TERMINAL_GUIDE.md、docs/specs/branch-operations/README.md §3-3。
ADR-114 §4(a)に保持指定の例外を提案追記し、既定の回収・定期回収は維持する。ADR編集時は既存の索引生成を実施する。
正式記録は本design/reconへの追記、tasks/todo.md、docs/ai-agents/evidence-registry.mdを使う。新たな文書体系は作らない。
実装カードは未発行。今回の文書保存限定例外を実装役の作成許可へ流用しない。実装を承認する際、その実装担当が使用する作業場所の適法な作成手段も明示する。

### 受入条件と検証方法

試験は実利用者のworktreeを対象にしない。一時fixture内でgit・回収・claudeの呼出しを記録する隔離試験と、ローカルの試験専用Gitリポジトリによる作成確認を組み合わせる。試験のために実運用のガード設定を変えない。

| # | 基準 | 検証方法 |
|---|---|---|
| 1 | 保持指定時の回収呼出し0回 | 呼出し記録を検査、上限未満・上限到達の2ケース |
| 2 | 既存作業場所の削除0件 | fixtureの全既存パス・ブランチ・ファイルhashの前後一致 |
| 3 | 上限未満で新規作成1件 | 試験Gitでworktree数+1、HEAD=取得済origin/main |
| 4 | UUID1件・担当登録1件 | 新規worktreeのIDと分割台帳のブランチが一致 |
| 5 | 上限到達時の作成0件 | exit1、fetch・add・UUID・登録の呼出し0回 |
| 6 | 不正指定では副作用0 | 未知・重複・欠落・余分な引数でexit2、git/回収/claude全0回 |
| 7 | 指定なしの既存動作を維持 | 従来形式で回収1回、作成経路・終了コードを比較 |
| 8 | AIは明示時だけ起動 | --claude有無、2指定の順序2通りで回数照合 |
| 9 | 取得失敗後は作成なし | fetch失敗fixture、addと登録0回 |
| 10 | 作成失敗後は登録なし | add失敗fixture、UUIDと登録0回 |
| 11 | 保持時に削除を促さない | 成功・上限メッセージに実削除案内0件 |
| 12 | 既存安全チェック通過 | bash構文確認、隔離試験、作成先でvalidate-worktree-start / validate-pr-ownership |

試験の成否は実装便で記録する。本設計ターンでは上の機能試験を実施していない。

### Why・代替案・適用限界

根拠は現行作成入口の実削除呼出し1か所、上限時dry-run呼出し1か所、未対応指定の拒否0か所。これを明示分岐と先行検証で扱う。外部企業の導入事例は不要。局所的なCLI分岐の安全性は呼出し回数・既存ファイルの前後一致で検証し、外部事例から成功を推定しない。
代替A（全呼出しから自動回収を廃止）は既存運用への影響が広いため採らない。代替B（テスト用環境変数や偽ロックで回収を止める）は運用の迂回になるため採らない。代替C（毎回直接作成）は担当登録漏れを恒常化させるため恒久手順には採らない。
保持指定は削除を減らす代わりに上限到達を早め得る。上限は維持して人へ戻す。同時作成競合の原子的上限制御・夜間回収からの永続保護は解決しない。後者が必要なら別設計とする。

### 設計自己審査

APPROVE（上記の機能設計、同一AIによる自己審査）。独立した第二者レビューではない。
理由: 変更箇所、既存互換、安全側の引数失敗、旧版の誤使用防止、受入条件12項目を対応付けた。既存の親仕様とADRへの提案更新を必要物に含めた。
実装可能という無条件宣言ではない。正式仕様の承認、実装担当の作業場所、正式カードの検査は実装前ゲートとして未了。これらが揃うまで実装役へ実行指示しない。製品実装・本番・マージの承認を兼ねない。

### 維持の仕組み（本追加案）

守り手: 人手で守る。対象スクリプトの変更PRでは上記新規隔離試験と既存所有チェックの結果をReviewerが確認する。現在のCIに新試験が自動登録済みとは扱わない。担当は実装役が試験結果を提示、PO指定Reviewerが確認。
既存の削除候補判定は scripts/tests/test-reaper-safety.sh を引き続き参照。新たなCIの必須化は本便に混載せず、必要時に別設計とする。

### 文書PRの承認記録（2026-09-10）

PO（しんごさん）原文: 「GO #3390」。対象は文書PR #3390のマージ。実装・後続PR・本番操作の許可ではない。上記の未受領表記は草案作成時点の履歴。文書レビューを経た保存後も、スクリプト機能自体は未実装。
