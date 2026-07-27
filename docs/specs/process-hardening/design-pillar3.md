# 柱3-a/b design — テストスキーマ複製の検出

> この文書は何か（専門用語なしの1行）:
> テスト用ファイルが本番テーブル定義を新しくコピーしたら機械が気づいて止める、その作り方を決めた設計。

親: docs/specs/process-hardening/kgi.md（柱3節）
recon: docs/handoff/pillar3-test-schema-dup/recon.md
対象ADR: ADR-121

## 1. あるべき姿（親から）
テストが本番テーブル定義を各自コピーする状態を止め、コピーはこれ以上増やさない。既存31ファイルは段階的に減らす。本便は「増やさない検出（柱3-a/b）」を設計する。

## 2. 対象KGI（本便が満たすもの）
- 柱3-a: テストの独自CREATE TABLEの新規増加を機械が検出して止める。
- 柱3-b: 検出パターンが変種（IF NOT EXISTS有無・引用符違い・スキーマ接頭辞）を取りこぼさない。
- 柱3-e: 欠落版・充足版のペアテストで実測（柱3-a/bの検証方法）。
（柱3-c 一覧固定・柱3-d 同伴警告は別便）

## 3. recon根拠（file:line・実測）
- 独自複製ファイル: 31（conftest.py除く）。docs/handoff/pillar3-test-schema-dup/recon.md §2。
- 本物の複製は execute(text(...)) の複数行文字列内: backend/tests/test_channel_type_control.py:52-53、backend/tests/test_adr119_backfill_source_guard.py:66-67（プレースホルダ版も execute(text(f...)) 内の本物）。
- 罠（複製でない）は execute の外: backend/tests/test_tenant_service.py:17,25,40,41（sql=／assert内）、backend/tests/test_inventory_parser_real_samples.py:60（docstring）。test_tenant_service.py は execute=0。
- 既存の最重要関所 scripts/check-process-artifacts.js には既存ファイルの追加行を見る処理が無い（recon §6）。

## 4. design（技術How）
### 4-1 置き場（独立スクリプト＋専用CI）
- 新規 scripts/check-test-schema-dup.js（最重要関所 scripts/check-process-artifacts.js には足さない）。手本 scripts/check-dangling-routes.js。
- 専用CIジョブ .github/workflows/test-schema-dup-gate.yml（手本 .github/workflows/dangling-route-gate.yml）。本体テストも同ジョブで実行。
- 注: スクリプト新規・CIジョブ追加は危険変更。実装便でPO自筆GO必須。本便は設計のみ。

### 4-2 検出アルゴリズム（集合差分・dangling-routes方式）
- BASE_SHA と HEAD_SHA で、変更された backend/tests 配下の各ファイルの「本物のCREATE TABLE数」を全文走査で数える。
- 本物の定義: execute(text(...)) の複数行文字列内に現れる CREATE TABLE。sql=文字列・assert・docstring・コメント内は除外。
- 判定: あるテストファイルで HEAD の本物数 > BASE の本物数（conftest.py=集約先は対象外）なら赤。減少・不変は緑。
- 全文走査のためファイル文脈（execute ブロックの内外）が使え、追加行だけを見る方式の文脈不足を避ける。

### 4-3 変種対応（柱3-b）
検出対象の書式（recon §3実測）: CREATE TABLE ／ CREATE TABLE IF NOT EXISTS ／ スキーマ接頭辞 {schema}.name・public.name ／ 大小文字。除外: execute外の文字列・assert・docstring。正確な照合規則は実装便でペアテスト（柱3-e）により確定する。

## 5. 弊害・トレードオフ
- execute ブロックの内外判定を要し、単純な行一致より実装が複雑。ただし罠は2ファイル5行と限定的（recon §4）で複雑さは抑えられる。
- 全文走査は変更ファイルのみ対象のため負荷は限定的。
- public.tenants AS（別テーブル空コピー・backend/tests/test_webhook_instagram.py:208）は通常の定義複製と別用途。対象に含めるかは実装便で判定（本設計では保留）。

## 6. 外部・過去事例
- scripts/check-dangling-routes.js（同リポジトリ）: BASE/HEADの集合差分で新規・削除を検出し、専用CIジョブ＋専用テストを同workflowで走らせる方式。柱3の独立スクリプト＋CIの直接の手本。
- ペアテスト手本: scripts/tests/test-migration-registration-exists.js、scripts/tests/test-dangling-routes.js（planted violation方式）。

## 7. 受入基準
| 基準 | 検証方法 |
|---|---|
| 新規複製を仕込んだPRで赤になる | ペアテストの充足版=本物CREATE TABLE追加で exit 1 |
| 罠（sql=／assert／docstring）で誤検出しない | ペアテストで罠を仕込み exit 0 |
| 変種（IF NOT EXISTS・スキーマ接頭辞）を取りこぼさない | 各変種を仕込むテストで全て検出 |
| 既存の緑PRが赤化しない | 過去マージ済みPRのファイル集合で空振り=緑 |

## 8. 維持の仕組み
- 守り手: .github/workflows/process-artifacts-gate.yml
- 対象: 本設計docが無断で書き換わること
- 補足: 柱3-a/b の実装本体（check-test-schema-dup.js）の守り手は実装便で新設する専用CIジョブ。本便は設計のみのため、設計docの改変防止を既存関所が担う。

## 9. 接触面分析（6面）
- 人: 実装役がテストにCREATE TABLEを足すとき赤で気づく。
- エージェント: 本設計docと recon が案内書。実装便のカードが従う。
- 機械: 新規CIジョブは実装便。本便は既存 process-artifacts gate のみ。
- データ: 非接触（テストのスキーマ定義の話。本番DB tenant_004 非接触）。
- 本番: 非接触（CIのみ）。
- 外部: 非接触。
