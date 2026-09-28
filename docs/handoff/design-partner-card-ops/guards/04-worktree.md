## 4. worktree・ブランチ

| 止まる形 | 回避形 | 出所 |
|---|---|---|
| `git worktree add` で直接作る → pre-commit が規約外の場所からの commit を拒否 | `bash scripts/new-worktree.sh <ブランチ名>`（`~/worktrees/salesanchor/` 配下・active-work.md に自動登録） | CARD-PMG-FIX11-09・CV-44（未検証） |
| 別セッションの worktree に触る | `worktree-access-guard.sh` が「別セッションのworktreeへのアクセスは禁止」でブロック | 実測 |
| ブランチ名が `release/*` `hotfix/*` 以外で main 向け PR | `gh-pr-create-safe.sh` が**ハードブロック**（§5） | 実測 |
| 上流が origin/main を指す → `git push` 拒否 | `git push -u origin HEAD` | CV-43・MERGE-FIX-05（未検証） |
| 既存ブランチの直接復元はcard-lint L12が拒否する | 公式new-worktree.shでorigin/main起点の新しい継続ブランチを作り、次カードで実在・HEAD・所有権を検算後、保存済みブランチを通常mergeする。元ref・退避UUID・台帳は成果がmainに含まれるまで保持 | CARD-LINE-GUIDE-04拒否、05/06実測（2026-09-28） |
| 正本に他便の先約 → 停止 | 触る前に `git grep -n "<ファイル名>" -- .claude-pipeline/` で先約確認（§6.5） | W-01・CARD-DP-RECON-03b |
| ローカル main に未解決コンフリクト → checkout 拒否 | ローカル main を起点にしない。origin/main から worktree | CARD-BENCH-RECON-02 |
| ディスク残量 → ENOSPC で worktree 作成が中途半端に失敗 | 手順0で `df -h .`。2Gi 未満なら止める | CARD-BENCH-PR-01 |
| マージ後 `cleanup-worktree.sh` が worktree とブランチを自動削除する | 削除される前提で、必要なファイルは先に退避 | 実測（gh-pr-merge-safe.sh 末尾） |

| new-worktree.sh の出力を head や tail に通す → 完了行が遅れて届き、次手順の ls が作成前に走って無いと誤判定する | 出力はパイプに通さない。判定は ls -1d と git worktree list の両方で行う | 別セッション実測・同型2回 |
| new-worktree.sh は reaper が全 worktree を走査してから作成に入る（2026-09-08 実測で64件） | 出力の見た目で成否を決めない。次手順で実在を確かめる | 実測 |
| new-worktree.sh はディレクトリが既に在ると fatal で失敗する。ブランチ作成は成功した後なので、ブランチだけが残る | 作る前に ls -1d で実在を確かめる | 別セッション報告・本セッション未検証 |
| 追加の push で git push だけを使う | PR 作成時に -u を付けても、後続の push で忘れると上流が main を指して拒否される。毎回 git push -u origin HEAD を使う | 2026-09-08 実測・同一ブランチで両方 |
| new-worktree.sh のオプション | CLAUDE.md と本ファイルで --claude の要否が食い違っている。推測でどちらかを採らない。正本は CLAUDE.md。本セッションでは --claude なしで5回成功している | 2026-09-08 別セッション報告 |
| 本店がmain以外、または作成の土台が未確認 | 本店branchがmainであることを確認し、本店HEAD・未保存差分・事前remote main SHAを記録する。本店を更新せず、公式scriptのfetch後origin/mainから作る。次カードで実作成HEADとorigin/main SHAを記録し、予定SHAとの一致を確認。不一致は停止・再査定し無断で新mainを採用しない。空き容量・作成先未存在も先に確認 | scripts/new-worktree.sh:90-106、branch-operations README §3、CARD-LINE-GUIDE-05/06（2026-09-28） |
| worktree作成と、そのworktreeの実在確認・cdを同じカードに入れる | 作成便は作成コマンドの終了と生出力の報告まで。実在確認（ディレクトリとgit登録の両方）・移動・編集は、作成成功を確認した後の別カードにする | 2026-09-10 PO引き継ぎ：同便でcdした手続き逸脱。元の実行ログは本セッション未確認 |

## 2026-09-28 継続作業の補足

- new-worktree.shは作成前にreaper --executeを呼ぶ。回収の副作用と許可範囲を作成カードで確認し、実回収対象・保護対象の出力を保存する。別作業者の未保存変更を触らないという条件は維持する。
- 今回のPO指示はAstra/Solに担当モデルを限定し、別sessionの暗黙起動を許可していない。そのため、別sessionを起動する--claudeを付けず、公式scriptの作成機能だけを使った。これは上位指示への適合であり、通常の起動規則を恒久的に解除しない。
- 今回のマージ済みworktree回収はPOの明示した削除依頼の範囲。一般的な他者worktree削除許可には拡張しない。
- 検算は事前remote SHA・実作成HEAD・次カード開始時origin/main SHAの3値を記録する。本店local HEADを更新して見かけの一致を作らない。
- 根拠と実測: [LINEガイド再開記録](../../pipeline-procedure-map/recon.md)。Astra自己審査APPROVE、別Solによる限定整合レビューは補足後APPROVE（blocking 0）。card-lint合格だけを安全性の証明にはしない。
