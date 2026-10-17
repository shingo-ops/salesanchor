# recon: 試し実行の除外27行を実測で確かめる（件3）

> 出発点: docs/handoff/found-untouched-20261017/handoff.md:15-17（#4481 件3）／docs/handoff/migration-dryrun-enforce/design.md:59
> 基準: origin/main 0677f423e。生出力: /tmp/CC報告ファイル/kenn3/

## 既存 ADR
- `git grep -il "dryrun\|dry-run\|試し実行" docs/adr/`（7-adr.txt）
- docs/adr/ADR-1005*.md:19（全件ドライランは登録290件のうち162件を対象外にしていた）、:27（段階0「対象外の理由を明らかにし、戻せるものは戻す」）
- docs/adr/ADR-1007-migration-structure-only-run-once.md:88（決定5 検査の強化）

## 事実
1. scripts/migration-guard/dryrun-exclusions.tsv は全33行、コメント :1-6、データ :7-33 の27行（1-tsv.txt）。:3「足すときは実測の ERROR を reason に書く」、:5-6「直すか通ることが分かったら同じPRで行を消す」。
2. 27行のうち実測の ERROR を書いた行は0。:7-21 の15行は「Python migration 依存のため除外（既存コメントの引き継ぎ）」、そのうち3行と :22-33 の12行は「…が無いため落ちると見込まれる（静的解析の見込み。未実行）」。
3. 除外が効くのは .github/workflows/migration-test.yml:1813 の step（`python3 scripts/migration-dryrun-report.py run --db jarvis_report --rounds 2 --psql psql`）だけ。job `migration-full-dryrun`（:1095-1827）は paths-filter（:44-47）に scripts/migration-guard/** を含むので、tsv だけの変更でも起動する。集約 job migration-test（:1829〜）が必須チェック。
4. scripts/migration-dryrun-report.py run は1本落ちても続行し、ファイルごとの結果を GITHUB_STEP_SUMMARY に出す（:55-92）。失敗が1本でもあれば終了コード1（:95-108）。
5. #4466 の実測は Draft PR 上の CI で、tsv を変えて1変更ずつ run を回し失敗本数を数えた（docs/handoff/migration-dryrun-baseline/design.md:26-36）。「見込み」の5行は実際には通った（同 design.md:11、Sprint1 python が public.products を作るため）。
6. ローカル: `docker info` 失敗（4-docker.txt）。ローカルでの再現手段は記録なし → 実測は CI 上で行う。
7. 危険度: scripts/check-process-artifacts.js:117 `^scripts/` に該当（GO 要）。deploy.yml は tsv を読まない（grep 0件）。#4466 は同種の変更で本番に何も入らないと記録。

## 未確認
- 27行それぞれが今の CI で通るか落ちるか（本便で実測する）。
