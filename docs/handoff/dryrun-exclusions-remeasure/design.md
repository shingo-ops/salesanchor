# design: 試し実行の除外27行を実測で確かめる（件3）

> 出発点: docs/handoff/found-untouched-20261017/handoff.md:15-17（#4481 件3）。recon: [recon.md](./recon.md)
> 状態: 設計案作成済み・設計審査済み（Opus 自己審査、APPROVE）。PO 2026-10-18 チャットで件3着手に「y」（マージ・デプロイまでの完走は 2026-10-17 に委任済み）。

## KGI（○×で判定）
| # | 基準 | 検証方法 |
|---|---|---|
| K1 | 27行すべてが「外した」か「実測の ERROR を reason に書いて残した」のどちらかになる。残った行の reason に「見込み」「未実行」「既存コメント」の語が無く、run 番号と ERROR の1行がある | `grep -c "見込み\|未実行\|既存コメント" scripts/migration-guard/dryrun-exclusions.tsv` が0／残った行ごとに run 番号を目で確認 |
| K2 | 最終 HEAD の CI で「マイグレーション全件ドライラン（実DB）」が 1周目・2周目とも失敗0、job success | `gh run view` の step summary |
| K3 | 除外一覧の検査が通る（試験 scripts/tests/test_migration_value_writes.py 25件 OK・必須 job 内） | CI の「models.py に新 Column …」job ログ |
| K4 | main マージ後、push で動く workflow（Deploy to VPS を含む）がすべて success | `gh run list --commit <merge sha>` |

## 実測の手順（CI 上・Draft PR）
1. 実験1: 27行をすべて消した tsv で CI を回す。run は落ちても続行し、ファイルごとの 1周目/2周目の結果が出る（recon 事実4）。
2. 実験2: 実験1で 2周目まで通ったファイルだけを消し、落ちたファイルは除外に残して CI を回す。失敗0なら確定。失敗が出たら、増えた失敗の原因を ERROR から特定し、原因になった行を除外に戻して再実行（1変更ずつ）。
3. 残した行は、その run の ERROR の1行（psql の `ERROR:` 行）と run 番号を reason に書く。
- handoff の「1本ずつ」からの変更: 27回の run の代わりに、全部外した run で各ファイルの結果を一度に取り、確定の run で外した組み合わせが失敗0であることを確かめる。外した行の根拠は確定 run の成功、残した行の根拠は実測 ERROR で、どちらも1行ごとに run で裏付けられる。

## 実測結果（2026-10-17）
- 実験1（27行すべて外す・HEAD af5365e67）: CI run 39044883118 の「マイグレーション全件ドライラン（実DB）」job success。1周目「成功 327 / 失敗 0」、2周目「成功 327 / 失敗 0」。外した27ファイルは1周目・2周目とも ✅（27×2＝54件、ERROR: の行は0）。生ログ /tmp/CC報告ファイル/kenn3/exp1/full_dryrun.log。
- 判定: 27行すべて今の土台で通る → 全部外したまま確定。残す行が無いため実験2は不要（実験1がそのまま「外した組み合わせで失敗0」の確定 run になる）。

## 変更
- scripts/migration-guard/dryrun-exclusions.tsv のデータ行（外す行は削除、残す行は reason を実測 ERROR に置換）。コメント :1-6 は触らない。
- 本 design.md・recon.md、handoff.md 件3に便のパス1行、active-work.d 台帳。

## 触らない範囲
- migrations/ の中身（落ちるファイルを直すのは別便。直す必要があれば design 追記で PO 判断へ戻す）、migration-test.yml、migration-dryrun-report.py、deploy.yml、run_all_migrations.sh。

## 代替案
- 1行ずつ27回: 1 run 約10分×27。全部外した run で同じ1行ごとの結果が取れるため不採用。
- ローカルで測る: docker が無く（recon 事実6）、CI と同じ土台（:1150-1737）の再現に別の手間と差異が出る → 不採用。

## リスクと対処
- 外したファイルが本当は他の除外ファイルに依存していた → 実験2（確定 run）で失敗0を条件にする。
- 実験中の Draft PR を誤ってマージ → Draft のまま実験し、確定後に Ready にする。

## 危険パス・GO
- scripts/ 配下（scripts/check-process-artifacts.js:117）。DB・本番・migrations/ は触らない。deploy.yml は tsv を読まない。バックアップ確認は該当なし。
- GO は POの委任に基づくClaude Opus発行（委任根拠: PO 2026-10-17 チャット「PRマージ、デプロイまで完走させてくれ」、件3着手 2026-10-18「y」）。

## 外部・過去事例の参照と我々への応用
- 過去事例: #4466（docs/handoff/migration-dryrun-baseline/design.md:26-36）。Draft PR 上で tsv を変えて CI を回し、見込みで除外していた5行が実際は通った。同じ方法を使う。外部事例は不要（同リポジトリの実測前例が直接の根拠になるため）。

## 維持の仕組み
- tsv :3 の規則（足すときは実測 ERROR）と、試験 test_dryrun_exclusions_are_valid（必須 job 内・#4483）。全件試し実行の失敗は #4476 で必須チェックを止める。
