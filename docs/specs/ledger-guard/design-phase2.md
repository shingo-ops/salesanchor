# design 第2弾 — 台帳の書き先分割（差分設計）

> この文書は何か（専門用語なしの1行）:
> 全員が同じ1枚に書く台帳を「1ブランチ1ファイル＋束ね表示」に分割し、
> 消し合い・追いかけっこを構造ごと無くすための設計図。

- 参照: [recon.md](./recon.md)（17読者の実測・相互参照）／[ideal-state.md](./ideal-state.md) 2項
  ／[kgi.md](./kgi.md) G3〜G6／[design-phase1.md](./design-phase1.md)
- 関連ADR: ADR-114（worktree回収。DONE行は消さず残す原則を本設計も踏襲）

## 1. 新形式の仕様
- 置き場: `.claude-pipeline/active-work.d/<ブランチ名のセーフ形>.md`（1ブランチ1ファイル）
- 中身: 1行目 `branch: <正式ブランチ名>`（衝突ガード用）、続けて現行と同一の
  7列テーブル（ヘッダ＋自分の1行のみ）。列仕様は本体と同一＝検証ロジック流用。
- 衝突ガード: セーフ形変換（/→-）は `feature/a-b` と `feature/a/b` が同名衝突する。
  登録時に既存ファイルの `branch:` 行が自分と異なる場合は書かずに停止して人間へ報告。
  窓口も `branch:` 行の完全一致で照合する。
- 本体 `.claude-pipeline/active-work.md` は凍結アーカイブ（便3でヘッダ明記）。
  既存行の移住は行わない（掃き出しは対策③の別便・役割を混ぜない）。

## 2. 窓口ヘルパー（読み書きの一本化）
- `scripts/ledger-lookup.sh <branch>`: .d/ → 本体の順で1行を返す（exit 0=有/1=無）
- `scripts/ledger-update.sh <branch> --status <S> | --pr <N>`: 行の所在側を更新
- `scripts/ledger-view.sh`: 本体＋.d/全件を1枚の表に連結表示（G4の実体）
- 以後、台帳の所在を知るのはこの3本だけ。読者・書き手は窓口だけを呼ぶ。

## 3. 3便の構成と17読者の改修対応（recon.mdの実測に基づく）
### 便1: 土台（新部品のみ・全既存挙動に変更なし）
- 新設: ledger-lookup.sh / ledger-update.sh / ledger-view.sh
- check-active-work-format.sh: .d/単票の検証モード追加（列数ロジック共用）
- テスト新設: 窓口3本の単体（両所在・不在・衝突ガード）
### 便2: 読者・更新者の付け替え（書き込み先は旧のまま＝挙動不変・G6を先行実証）
- lookup経由へ: validate-pr-ownership.sh:69-84／gh-pr-merge-safe.sh:66-81／
  reaper-worktree.sh:136／check-stale-worktrees.sh
- update経由へ: cleanup-worktree.sh:52-78／register-pr.sh:62-91／
  release-worktree.sh／backfill-active-work-done.sh（走査はview併用）
- 文言・認識の更新: codex-generator.sh:81（確認手段をledger-view.shへ）／
  pre-commit:17-21（例外パターンに active-work.d/ を追加）／
  pre-push:28-31（.d/変更時もformat検証）／
  check-process-artifacts.js:743（台帳パターンに active-work.d/ を追加）
- 回帰: tests/test-reaper-safety.sh・test-manifest-generation.sh・
  test_pre_commit_hook.py を新経路で全通し
### 便3: 書き手の切替＋実測
- new-worktree.sh:121-157 の自動登録先を .d/ へ（衝突ガード込み）
- 本体active-work.mdへ凍結ヘッダ追記（「新規登録は active-work.d/ へ」）
- カード内実測（本番同条件・同一ステップ判定・不一致STOP内蔵）:
  G3=机作り直後に本店の追跡ファイル変更0件／G4=view1発で全件一覧／
  G5=2机連続作成で相互のファイル接触0／G6=読者チェック緑の再確認

## 4. 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| G3 置き書類ゼロ | 机作り直後に git status --porcelain のM行=0を実測 |
| G4 束ね表示 | ledger-view.sh 1発で本体＋.d全行が表として出力される |
| G5 並行衝突ゼロ | 2机連続作成後、互いの.dファイルと本体に差分接触0を実測 |
| G6 既存読者の互換 | 便2マージ後、push遮断・PR#整合・回収・stale判定・関所が全緑 |
| 衝突ガード | セーフ形同名・別branchの登録テストで停止＋報告を実測 |

## 5. 外部・過去事例の参照と我々への応用
Debian/Nginx/systemd が採る conf.d / sites-enabled / drop-in 方式（共有1設定を
「1項目1ファイル＋束ね読み」に分割し編集衝突を構造排除する業界標準）を台帳に応用。
一覧性は生成表示（view）で担保し、書き込み単位を所有者ごとに分ける。

## 6. 先に言う弊害
- 便2の改修範囲が広い（シェル10本超）→ 既存テスト3本＋窓口単体テストを回帰網に
- gate/フックの自己保護域（check-process-artifacts.js・pre-commit）に触れる →
  各便とも危ない変更区分の正規手順（GO転記→関所再実行→全緑→マージ）で
- .d/ファイルはDONE後も残す（ADR-114踏襲）→ 件数増は対策③の掃き出し便で整理
- セーフ形衝突はガードで停止するが自動解決はしない（レア事象・人間判断）
