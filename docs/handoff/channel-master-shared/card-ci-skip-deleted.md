# 実装カード CI-1: 消した移行の台本を、自動確認が動かそうとしないようにする

> この文書は何か（専門用語なしの1行）:
> 移行の自動確認が「PR で消した台本」まで動かそうとして赤になる穴を、1行の直しでふさぐ作業の指示書。

- 親: design.md §7（`scripts/migrate_20260621_030000_backfill_lead_channel_type.py` をファイルごと消す・design.md:167／card-pr-b.md:90）。この削除を含む PR-B #5230 が、この穴で赤になっている
- PO 承認: 2026-11-07「1」（選択肢「自動確認の仕組みを1行直す」）
- 基準: origin/main 198c583c0（2026-11-07 取得）。行番号はこの版で Opus が読んで確かめた
- ブランチ: `release/migration-test-skip-deleted`（作成済み）
- 起票: Draft・`--base main`・`shingo-cc` 名義。危険パス（migrations/・deploy.yml・本番 scripts/）は含まない
- 読んだ決まり: docs/handoff/design-partner-card-ops/guards/00-common.md・04-worktree.md・05-pr.md・10-executor.md
- 受領確認: 着手の前に、§0 の1202行目の文が手元と同じかを1行で返してから始める
- 停止: 迷ったら止まり、`BLOCKED:` か `NEEDS_DECISION:` で理由を返す

## 0. 観測した事実（Opus 確認済み）

- `.github/workflows/migration-test.yml:1202` は `git diff --name-only "$BASE" "$HEAD"` で変わったファイルを取り、`:1209` で `^scripts/migrate_` を選ぶ。消したファイルも一覧に入る
- PR-B の CI 記録: 消した台本を `python` で動かそうとして `[Errno 2] No such file or directory`（`/tmp/CC報告ファイル/prb/mig-log-4.txt:22`）
- `git log origin/main --diff-filter=D -- 'scripts/migrate_*.py'` は0件。台本を消した前例は無い
- 手元で試した結果（git 2.39.3）:
  - PR-B の差分に `--diff-filter=d` を付けると、`scripts/migrate_*` は0件（消した1件が外れる）
  - 台本を足した過去の commit 7d04dc265 に付けても、5件がそのまま残る
- git の説明書（`git help diff`）: 大文字の種類は小文字にすると「除く」になる。例 `--diff-filter=ad` は追加と削除を除く。Context7 は月の上限で使えなかったため、説明書で代わりに確かめた
- 同じ `ALL_CHANGED` を使う生 SQL の選び出し（`:1227-1229`）は、消した SQL をもともと `grep -L` で落としている。この直しで結果は変わらない

## 1. やること（この順）

1. `./scripts/dev/executor-preflight.sh || exit 1`
2. `.github/workflows/migration-test.yml:1202` を次の通りに直す（この1行だけ）

   変更前:
   ```
             if ! ALL_CHANGED=$(git diff --name-only "$BASE" "$HEAD"); then
   ```
   変更後:
   ```
             if ! ALL_CHANGED=$(git diff --name-only --diff-filter=d "$BASE" "$HEAD"); then
   ```
3. 直した行のすぐ上に、コメントを1行足す: `# --diff-filter=d: PR で消したファイルは一覧から外す（消した台本を動かそうとして落ちるのを防ぐ）`
4. commit・push・Draft PR 起票。PR 本文に `### 標準ワークフロー確認` 欄を書く

## 2. 触らない

- `.github/workflows/migration-test.yml` のほかの行
- ほかのすべてのファイル（このカードを除く）

## 3. 受け入れ条件

| 基準 | 検証方法 |
|---|---|
| 差分が 1202 行目の直しとコメント1行だけ | `git diff origin/main --stat` が migration-test.yml 1ファイル・+2 −1 と、このカード1ファイル |
| この PR の CI が緑 | この PR の `gh pr checks` に fail が無い |
| 合流後、PR-B #5230 の「マイグレーションSQL 実行（内部）」が緑 | PR-B に本線を取り込んで CI を回し、`gh pr checks 5230` で確かめる（Opus） |

## 4. 想定分岐

- 1202 行目の文が上と違う → 止まって BLOCKED: で返す（本線が動いた）
- CI で別の確認が赤 → 直さずに、その確認名と記録の該当行を返す

## 5. 戻し方

この PR を revert すると、元の1行に戻る。

## 6. 維持の仕組み

前例の無い穴だったため、直しの理由を 1202 行目の上のコメントに残す。同じ確認の中で台本を選ぶ所はこの1か所だけ（`:1209`）。

END OF CARD
