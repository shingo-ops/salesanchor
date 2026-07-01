# Phase 3 設計 — ブランチ運用：develop 廃止後の開発環境

**対象ADR**: ADR-056（Human-in-the-Loop Minimization／develop への自動化）
**仕様書**: ../../specs/branch-operations/README.md
**recon**: ./recon.md
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

基本方針: 「行き先を全て main へ付替 → devの守りを main へ移設 → 撤去 → 後片付け」。撤去は最後、撤去前は中止可能。

第1便（動線付替）:
- 削除: auto-back-merge.yml, auto-release-pr.yml, claude-pipeline.yml（ADR-056廃止＝R）
- 書換: gh-pr-create-safe.sh:56/66, pr-base-check.yml:27, executor-preflight.sh:74, new-worktree.sh:73, backfill-active-work-done.sh:72, reaper-worktree.sh:214/229, validate-pr-ownership.sh:36, validate-worktree-start.sh:47 の develop→main
- 除外: deploy.yml（危険ファイル・後片付けへ）、検問の branches:[main,develop] 欄（後片付けへ）
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
第4便（後片付け）: 検問の develop 欄整理、deploy.yml stamp の目印を main へ、記録

## 弊害・トレードオフ

- リスク1: ADR-056（AI自動化）を廃止する → 対策: しんごの「全手動GO」方針に合致。将来必要なら練習場を作り直せる。R確定（仕様書§3-3）
- リスク2: 撤去後 deploy.yml stamp が毎回失敗ログを出す（continue-on-error で握り潰される）→ 対策: 第4便で stamp の目印を main へ修正。実害ゼロだが恒常赤stepを消す
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
