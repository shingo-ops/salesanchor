# review-opus: pr-ownership-rest (PR #4663)

審査日: 2026-10-22 / 審査役: Opus（Reviewer）/ 対象 HEAD: 3cb313af6
生出力: /tmp/CC報告ファイル/pr-ownership-rest-review/（diff.txt, checks.txt, gate.log, body.md）

## 結論
APPROVE（コード）。マージ条件: ① process-artifacts gate の「### GO記録」充足（scripts/ を含む危険PR・ADR-136）② pending の CI 2件の完了。

## 1. 判定の意味（不変か）
| 観点 | 事実 | 判定 |
|---|---|---|
| owner の求め方 | scripts/validate-pr-ownership.sh:140-141 で origin URL から `owner/repo`、:144 で `${REPO_SLUG%%/*}` = `shingo-ops`。同一リポジトリのブランチなら正しい | OK |
| state=closed＋merged_at | :143-145。独立実行: `head=shingo-ops:release/loading-mold-pages-2` → `[{"merged_at":"2026-10-22T11:06:15Z","number":4658}]`、本ブランチ → `0` | OK |
| 変更前との同値性 | 変更前 origin/main:scripts/validate-pr-ownership.sh:138 は「merged のPRが1件でもあれば止める」。変更後 :151 も「merged 件数≠0なら止める」 | 同値 |
| per_page=100 | 同一ブランチ名の closed PR が100件を超える運用はない（ブランチはトピックごと） | 十分 |
| `--method GET -f` | `gh api --help`: "To send the parameters as a GET query string instead, use --method GET" | OK |
| origin URL 解析 | https / https(.gitなし) / git@ / ssh:// / トークン付き https の5形式すべて `shingo-ops/salesanchor` を得た | OK |
| 全体実行 | 本ブランチで `bash scripts/validate-pr-ownership.sh` → 「✅ オーナーシップチェック通過」rc=0 | OK |

## 2. 失敗時の挙動（fail-closed）
- 【事実】変更前も失敗時は止まっていた。`set -e`（:14）下で `X="$(失敗するコマンド 2>/dev/null)"` は rc=1 で終了（`bash -c 'set -e; X="$(false 2>/dev/null)"; echo reached'` → rc=1, reached 出力なし）。recon.md の「無言で止まった」と一致。
- 【事実】したがって本PRは「通す→止める」の変更ではなく、「無言で止める→理由を出して止める」の変更（:146）。
- 影響: Mac のネット断では push 自体が不可能なので追加影響なし。gh 未ログイン時は従来どおり止まり、今後は理由が表示される。gh 未導入時は従来どおりチェック4をスキップ（:138）。妥当。

## 3. 呼び出し元
- 実行経路は frontend/.husky/pre-push:23-25 のみ（core.hooksPath=frontend/.husky、ルート .husky/ は存在しない）。
- 手動実行の案内: ~/.claude/agents/generator.md:70、scripts/codex-generator.sh:96。
- 終了コード・引数の契約は不変（0=通過 / 1=中断）。他への影響なし。

## 4. 検証記録 a〜d（/tmp/CC報告ファイル/pr-ownership-rest/）
- a.txt: マージ済みブランチで中断文言＋rc=1。独立再実行で #4658 merged を確認、主張どおり。
- b.txt: PASS rc=0。主張どおり。
- c.txt: 「マージ済みPRの確認(REST)に失敗しました: error connecting to invalid.example」rc=1。主張どおり。
- d.txt: bash -n rc=0。
- 注: a〜c は block.sh（チェック4部分の抜き出し）での実行。全体実行は本審査で本ブランチの rc=0 のみ確認。

## 5. recon.md / design.md
- recon.md:7 の「:138（変更前）」は origin/main と一致。gh 呼び出し1か所も origin/main の grep で一致。既存ADR（ADR-074）記載あり。
- design.md: ADR参照・`|基準|検証方法|` 表・外部事例・維持の仕組み・戻し方あり。揃っている。
- PR本文「削除するファイル: scripts/validate-pr-ownership.sh」は scripts/check-process-artifacts.js:898 の定義（1行でも変更した行があるファイル）どおりで正しい。「変更規模 小（1ファイル）」はコード1ファイルの意味と読める（軽微）。

## 6. CI（gh pr checks 4663, 審査時点）
pass 34 / skipping 10 / pending 2（deprecated 列の新規参照チェック、pytest-run-internal）/ fail 1。
fail = process-artifacts gate: 「❌ PR本文に「### GO記録」セクションがありません」（gate.log）。コード不備ではなく GO 手続き待ち。

## 残リスク（非ブロック）
- 【未確認】クラウド実行時の origin URL 形式は記録がない（cloud-trial-20261022 に get-url の出力なし）。仮に `http://…@127.0.0.1:<port>/git/<owner>/<repo>` のようなプロキシ形式なら、:140 の sed では `git/shingo-ops/salesanchor` となり、REST は Not Found（本審査で `repos/git/shingo-ops/salesanchor/pulls` → Not Found を確認）→ 理由つきで中断する。安全側だが KGI（クラウドで push が通る）は未達になる。次回クラウド試行で `git remote get-url origin`（資格情報はマスク）を記録すること。中断した場合は「末尾2区切りを owner/repo とする」解析へ直す。
- head の owner が実在しない値の場合、REST は 0 件を返す（`head=git:release/loading-mold-pages-2` → 0）＝通過側に倒れる。fork から push する運用はないため現状影響なし。
- 【未確認】クラウドで gh の REST 呼び出し自体が通るか（run-summary.txt:6 では gh auth status が「GH_TOKEN invalid」）。次回クラウド試行で確認する事項。失敗時は理由つきで中断するため現状より悪化はしない。
