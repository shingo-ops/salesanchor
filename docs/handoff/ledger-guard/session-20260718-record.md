# セッション記録 — ledger-guard 便3完結＋掃き出し＋stash仕分け（2026-07-18〜19）

> この文書は何か（専門用語なしの1行）:
> 台帳の混線を構造ごと無くした日の、全成果・残作業・教訓の固定記録。

- 親: ../../specs/ledger-guard/README.md ／ 設計: ../../specs/ledger-guard/design-phase2.md
- recon: ./recon.md ／ 関連ADR: ADR-114

## 1. 本日の成果（全てGitHubメタデータで実測済み）

| PR | 内容 | mergeCommit | mergedAt |
|---|---|---|---|
| #2939 | 便3-1: 机作りの登録先を1ブランチ1ファイルへ切替（.gitkeep常設＋new-worktree.sh置換） | 038fd78d | 2026-07-18T10:26:27Z |
| #2953 | 便3-2: 本体台帳の凍結アーカイブ化＋pre-commit台帳例外の撤去 | 84c05654 | 2026-07-18T12:49:07Z |
| #2957 | 掃き出し便: 未コミット退避61行を凍結アーカイブへ逐語保全 | 9d5490df | 2026-07-18T14:37:02Z |

- G3実測PASS: 机作り直後の本店追跡ファイル変更0件（2回再現）
- G5実測PASS: 2机連続作成で相互のファイル接触0（機械判定）
- 実運用実証: 単票の自動生成・ledger-update.shによる分割側DONE記帳を生ログ確認
- 判定: 台帳（active-work.md）の混線は構造的に封鎖完了

## 2. 付随成果

- 本店をmain最新へ復旧（退避3点セット取得後・他セッションの記入は1行も失わず）
- docs/handoff/ledger-guard/recon.md 新設（関所要求書類の正規化）
- design-phase2.md に「## 維持の仕組み」欄を追加

## 3. stash仕分けの結果

- 出発点: 120件 → 現在: 81件（39件をPO承認の上drop）
  - 第1弾34件: 台帳ファイルのみのstash（照合つき降順drop・検算PASS）
  - 第2弾5件: 追加行が全行mainに存在する完全白のみ（行単位機械照合）
- 全120件の退避パッチ: ~/salesanchor-evacuation/stash-archive-20260719-002136/（復元可能）
- 残81件の扱いルール: コード含む灰色。各テーマの持ち主が再開時に退避パッチを見て
  要否判断。dropは全件PO承認制。一括削除は禁止。

## 4. 退避物の所在（本日分）

- ~/salesanchor-evacuation/20260718-202133/（本店復旧時の3点セット・台帳68行パッチ）
- ~/salesanchor-evacuation/20260718-232431/（追加退避: dp-sec6-gate-lessons DONE行）
- ~/salesanchor-evacuation/20260718-dp-lessons/（dp教訓6行パッチ→PR #2952でmain反映済みと確認）
- ~/salesanchor-evacuation/stash-archive-20260719-002136/（stash全120件）

## 5. 残宿題（次回以降・優先順）

1. PR本文テンプレの逐語正本化: 本日関所に6回落ちた真因。#2953の最終合格本文を
   正本テンプレとして固定（関所のrecon引用は.md拡張子のみ認識、の対応含む）
2. 【2026-07-20更新】マージキューは shingo-ops が個人アカウント(type=User)のため導入不可と実測確定。代替: gh-pr-merge-safe.sh に MERGE_RETRY（not up to date時の追従→再採点→再マージ・最大2回・コンフリクトと他事由は即停止）を実装（衝突源③の実用対策）
3. design-partner.md §6 教訓追記便（下記§6を逐語で反映）
4. ledger-guard設計書のステータス更新（G3〜G6実測結果の記帳・G4/G6の扱い確定）
5. 正本文書の1便1ファイル化設計（台帳と同型・衝突可能性の実用ゼロ化）
6. 本店鮮度の機械検知（SessionStartフック等・G2の延長）

## 6. 未記帳の教訓（§6追記便への持ち込み・逐語）

- 関所のbase比較はPR作成時のBASE_SHAを使うため、mainが先行すると他セッションの
  変更を「宣言外」と誤検出する。main追従（merge origin/main）でbaseを進めて解消する。
- grep -c は「マッチ行数」を数える。個数の検収は grep -o | wc -l を使う
  （1行複数マッチの数え漏れで誤STOPが起きる）。
- 関所のrecon引用認識は拡張子 .md/.js/.ts/.tsx/.py/.yml/.yaml/.json のみ。
  .sh は対象外のため、シェルスクリプト主体のテーマでは .md 側の根拠引用を必ず併記する。
- 「nothing to commit」は checkout元と現状が同一の証拠として読む
  （除去のつもりの checkout が空振り＝その変更は既に別経路でmainに在る）。
- stashのdropは降順（大きい番号から）で行い、drop直前に中身とメッセージを再照合する。
- 灰色（一部未反映）のstashは一致率9割でも削らない。全行一致の完全白のみ機械判断で
  drop可、それ以外は持ち主判断。
