# 仕様書（あるべき姿）- ブランチ運用: develop 廃止後の開発環境

**日付**: 2026-07-01
**担当**: Planner (Claude)
**PO承認**: GO（2026-07-01 / しんご）

**GO記録**: 2026-07-01 / PO: しんご / develop 廃止後のブランチ運用仕様書を正本化する GO を確認

---

## 1. 目的

develop ブランチを廃止する。目的は「develop を消すこと」ではなく、develop を廃止しても開発できる環境がこれまでと変わらないこと。「開発環境」は次の3層すべてを含む。

- 動線: 機能開発の入口から PR 提出、本番反映まで詰まらず流れる
- 守り: 関所（CI検問）とブランチの鍵（ruleset）が、これまでと同じ厳しさで効く
- 作法: 危険操作の承認、worktree の作法、台帳(active-work)管理などの開発ルールが、これまでと同じように働く

## 2. 背景

#2701 の集約により develop の内容は main に完全反映済み（origin/main..origin/develop = 0）。develop に「main に無い中身」はゼロ。二段構えを維持する意味が薄く、二重管理と恒常的な back-merge のコストが残るため、develop を畳み main 一本に集約する。

## 3. あるべき姿

### 3-1. 動線

- 新規開発は release/ から枝を出し main へ PR を作る一本道で回る
- PR の既定の行き先は main（develop を指す既定は残さない）

### 3-2. 守り（最重要）

develop がこれまで手前で引き受けていたリスク管理を、廃止後は main の関所がすべて引き継ぐ。素通りを一つも作らない。現在 develop の鍵にのみ必須で main の鍵に無い次の守りを main へ移す。

- UI ガバナンス検問
- dangling-route 検問
- worktree 整合性チェック（main 宛でも動くようにする）

main の鍵（消せない・巻き戻し禁止・レビュー必須・process-artifacts gate 必須）は廃止作業で一切弱めない。「develop にあって main に無い守り」が廃止完了時点でゼロ。

### 3-3. 作法

worktree の唯一の正規入口は `scripts/new-worktree.sh` であり、`origin/main` 起点で作る。台帳への登録は `scripts/new-worktree.sh` が自動で行い、手作業やミラーは不要。（例外: Discord の件のセッションの作業場所は、agent-console が `~/worktrees/discord-cases/` に作る本店から切り離した写しで、台帳もその写しの中に agent-console が同じ書式で登録する。`--no-verify` は使わない。ADR-1039 Exceptions）危険操作の承認手順（確認→退避→試し→自筆GO→実行→検算）、台帳更新が、main 一本の動線でこれまでどおり機能する。develop 前提の自動化のうち、リスクを止める「守り」は main へ移し、単なる develop 運用の付随機能（AI自動ライン等）は廃止する。

### 3-4. 撤去そのもの

develop ブランチが存在しない。撤去は全工程の最後。撤去前はいつでも安全に中止できる。撤去時は控え（SHA）を取り、問題時は復元できる。

## 4. KGI（PO が画面・出力で ○× を一義に判定できる成功条件）

| # | KGI | ○判定の方法 |
|---|-----|------------|
| 1 | 新規開発の入口〜PR提出まで詰まらず進める | しんごが実際に開発入口を一度通しエラーで止まらなければ ○ |
| 2 | 変更が CI を通り本番に届き本番アプリが正常動作 | 変更が main 反映され app.salesanchor.jp が正常表示 → ○ |
| 3 | develop が存在しない | `git ls-remote origin develop` が空 → ○ |
| 4 | develop 由来の自動化エラーが残っていない | 廃止後の main CI に develop 原因の失敗が無い → ○ |
| 5 | 各危険工程にしんご自筆 GO 記録がある | PR 本文に自筆 GO 記録あり → ○ |
| 6 | main の守り（関所・鍵・作法）が撤去前後で弱まっていない | 撤去前後で main の検問一覧・鍵設定を見比べ減っていない → ○ |
| 7 | develop が引き受けていたリスク管理が廃止後は main 側ですべて効いている | 「develop にあって main に無い守り」の全項目が廃止後 main で効いている → ○（一つでも素通りなら ×） |

最重要は KGI7。

## 5. 対象範囲・触らない範囲

触れる: PR 動線スクリプト、develop 依存の自動化ファイル、dev にのみ効く守りの main への移設、develop の鍵、develop ブランチ本体
絶対に触らない: 本番出荷処理の本体（deploy.yml のデプロイ実処理）、main の鍵、緊急遮断（ADR-134）

## 6. 段取り（詳細設計は design.md に置く）

第1便=動線付け替え → 第1.5便=守りの引き継ぎ → 関門（しんご実地確認）→ 第2便=develop 鍵外し → 第3便=develop 撤去（唯一の危険操作）→ 第4便=後片付け。撤去は最後、撤去前はいつでも中止可能。

## 7. 関連文書（この仕様書にぶら下がる子文書）

本仕様書（親・あるべき姿＋KGI）に紐づく子文書:
- recon（現在地把握）: `docs/handoff/branch-operations/recon.md`
- design（Phase3設計・第1〜4便）: `docs/handoff/branch-operations/design.md`

親子関係:
- 親: 本仕様書（KGI・あるべき姿の正本）
- 子1 recon.md: 親のKGIを満たすための現在地把握（file:line実物）
- 子2 design.md: 親のKGIとreconに基づく実現設計（各便の受入基準・KPI）

## 8. 日々の運用ルール（入口から写した決まり）

入口（CLAUDE.md・AGENTS.md）の「ブランチ運用ルール」節から、文を変えずに写しました（2026-10-23・ADR-1040 段3b）。

- 完了後 `gh pr create --base main` でPR作成 → レビュー後 `main` へマージ（merge commit・squash禁止）
- **release/* → main は PR 経由**（直push禁止・Branch Protection で強制）
  - リリース相当の大きな変更は `--draft` で起票（**必ず Draft**）→ PO が diff・相乗り PR を確認し GO を出すまで誰も un-draft/マージしない（ADR-1015 の B 区分は Draft にしない）
  - マージ前に「確認済み：〇〇」コメントを残すこと（チェックリスト形骸化防止）
  - **緊急 break-glass**（本番障害復旧のみ）: ①PRタイトルに `EMERGENCY:` 明記＋理由 ②Shingo即時報告 ③24h以内に事後Approve＋ログ記録（詳細: `docs/BRANCH_PROTECTION_SETUP.md §4`）
  - マージ方法は必ず "Create a merge commit"（squash 禁止 — back-merge が永続発生するため）
- マージ前は reviewer(opus) の `VERDICT: APPROVE on <sha> PR #<N>` 行つき報告が必須（ADR-1029 のフックで強制）
- **main にマージ＝本番投入可の宣言**（ADR-135）：`migrations/`・`deploy.yml`・本番 `scripts/` を含む実装は PO GO が出るまで release ブランチで待機し main にマージしない。main は待合室ではない。
- **危険PR（上記パス含む）のGO手順**（ADR-136）：①マージ前にチャットで「対象・変更3行サマリ・直前バックアップ確認」をPOに提示 ②POの「GO #PR番号」（番号必須・番号なし曖昧肯定は無効）を受領するまでマージ・適用しない ③受領後は PR本文に `### GO記録`（GO発行者・日時・GO原文・バックアップ確認）セクションを転記 ④GO権限はPO（Shingo）。ADR-1003により例外を除き Claude Opus 設計担当へ常時委譲（PO「委譲停止」で解除）
- **リリース PR 作成時**は `git diff main...HEAD --name-only` で全 PR・全 migration を列挙し PR 本文に記載。**1リリース1テーマ**：`migrations/` に無関係トラックの混入がないか明示確認。GO記録に相乗り全 PR を明記（#2446/#2503 教訓）。危険パスが含まれたら停止して PO 確認。

### 長命ブランチ消失防止（develop は第3便まで残置・ロールバック用・新規作業での使用禁止）

- GitHub の削除保護を使えない前提では、`main` / `develop` は「物理的に消さない」運用で固定する
- `main` / `develop` に対する `git push --delete`、GitHub UI の branch delete、`gh api` の ref delete は実行しない
- `--delete-branch` は feature head のみ許可し、長命ブランチには使わない
- `./scripts/dev/executor-preflight.sh` は `origin/main` の存在を毎回確認する（#2715 で main-only 化済み）
- もし `main` / `develop` が欠落していたら、作業は止めて PO に報告する

---

*本仕様書は develop 廃止作業の正本。recon.md / design.md は本書に紐づけて docs/handoff/ 配下に追加する。*
