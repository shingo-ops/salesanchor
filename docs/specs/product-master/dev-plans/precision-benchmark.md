# 開発計画書 — 解析精度の物差し（退行検知・サーバー内完結）

配置先: docs/specs/product-master/dev-plans/precision-benchmark.md
親仕様: docs/specs/product-master/README.md
区分: 既存の延長・修正（STANDARD-WORKFLOW §1.8）。新しい設計仕様書は作らない。
対象ADR: ADR-154（照合ロジックは GAS 実行順序を100%再現。本計画は照合ロジックを1行も変えない）
起草日: 2026-09-06
起草者: 設計パートナー（PO: しんご）

この文書は何か（専門用語なしの1行）:
商品マスタやキーワードを変えたとき「どの行の判定が変わったか」を機械が数え、悪化があれば本番への切替を止める仕組みを、データをサーバーから出さずに作る計画。

---

## 0. 一言で

いまは、マスタを1件足すたびに1,626行の判定がどこか変わるが、どの行が変わったかを見る手段が無い。
本計画は「変える前に、壊していないことを機械に証明させる」柵を作る。精度そのものは上げない。下げさせない。

---

## 1. 現在地（実測のみ・出所つき）

| 事実 | 値 | 出所（実測日・SHA） |
|---|---|---|
| 商品行（extraction_items） | 1,626行 | recon 2026-09-04・0d329d40 |
| 解決 / 複数候補 / 未解決 | 1,294 / 46 / 286行（184種） | 同上 |
| 商品マスタ / 検索語 / 除外語 / 正規化ルール | 268 / 593 / 128 / 136 | 同上 |
| キーワード品質の問題 | 空キーワード 1商品・3文字以下 23行・複数商品ヒット 1語→3商品 | recon §5・同上 |
| 照合の純関数（DBを受け取らない） | 15個（normalize_en, token_and_match, match_one_kw, match_keyword, filter_product_codes_by_unit_kubun, match_pid_name_first, resolve_unit, resolve_unit_v2, resolve_condition, resolve_condition_v2, app_kubun_matches, _parse_numeric, apply_field_normalization, build_note_ja, resolve_status_v2） | CARD-BENCH-RECON-01 06a/06b・f5a65310 |
| DBを受け取る関数 | 8個（load_* 7個 + analyze_extraction_job） | 同上 06b/07b |
| 照合の入口の引数 | match_pid_name_first(raw_name, product_codes, search_kw: dict, exclude_kw: dict) | 同上 08b |
| 既存DBロール | jarvis（Superuser）/ qa_tenant006_rw / salesanchor_app の3つ | 同上 10a |
| 既存スキーマ | public, tenant_001, 003, 004, 005, 006（bench 系は無い） | 同上 10b |
| 切替スクリプト | scripts/blue-green-cutover.sh 164行。Step 3（health 確認）と Step 4（nginx 切替）の間に、green が起動済み・未接客の区間がある。set -e と trap ERR あり | 同上 07b/07c |
| TCG_SCHEMA | cutover の docker run に --env TCG_SCHEMA="${TCG_SCHEMA:-tenant_004}" が既にある | 同上 07b |
| CI ランナー | ubuntu-latest が大半。external-state-snapshot.yml は [self-hosted, salesanchor-vps]。全件は未確認（head -40 で切れ） | 同上 08 |
| サーバー内の定期実行 | systemd タイマー16本すべてOS標準。アプリ側の定期実行は0本 | 同上 11 |
| テストの空白 | DBをモックしているため SQL 文字列と実行順序は検査されない。本日の障害3件はテスト緑で本番発覚 | handoff 2026-09-05 recon §3 |
| migration の置き場・採番 | migrations/（root直下）・247本・YYYYMMDD_HHMMSS_説明_テナント識別子.sql・直近 20260905_150000・採番規則の文書は無し | CARD-BENCH-RECON-02・b877b14a |

未確認（本計画の土台には不要。第2段階以降で要る）:
- tcg_analyzer_svc.py 1012〜1132行（session.commit と E3a/E3b/E4 の呼び出し）
- runs-on の全件

---

## 2. KGI（○×で判定できるもののみ）

| # | 合格条件 | 測り方 |
|---|---|---|
| K1 | bench_004 スキーマと bench_ro ロールが存在し、bench_ro は tenant_004 に SELECT のみ、bench_004 に SELECT・INSERT のみ持つ | \dn と \dp の生出力。INSERT を tenant_004 に試みて permission denied が返る |
| K2 | 写し取りの実行で、bench_004 の商品行数 = tenant_004 の extraction_items 行数（同一トランザクション内で両方 count） | 両 count を並べた生出力 |
| K3 | 変更なしの同一SHAで検査を2回走らせ、差分行数 = 0 | 検査の出力に changed=0 が2回 |
| K4 | 検索語を1件だけ意図的に変えた枝で検査を走らせ、差分行数 ≥ 1 かつ変わった行の商品コードが列挙される | 検査の出力（防音室ではなく green コンテナ内で実施） |
| K5 | 検査中の DB 接続はすべて bench_ro。tenant_004 への書き込みが 0 回 | pg_stat_statements または監査ログの生出力（取得方法は第1段階で実測して決める） |
| K6 | cutover Step 3 と Step 4 の間で検査が走り、差分行数 ≥ 1 のとき exit 1 で切替が止まり、旧 backend が接客を継続する | 意図的に差分を作った枝で cutover を1回実行し、Step 4 に進まないことを出力で確認 |
| K7 | リポジトリに商品名・仕入元名・原文が1件も入らない | PR 差分に対する grep（tenant_004 の商品名を1件も含まない） |
| K8 | 実行時間を実測して記録する（見積り値は書かない） | 検査の出力に経過秒数 |

---

## 3. 構成（何を・どこに）

### 3-1. データの置き場（サーバー内で完結）

| 置くもの | 置き場 | 外に出るもの |
|---|---|---|
| 商品行の写し（id, raw_product_name, raw_quantity, raw_price, raw_unit, raw_state。raw_memo は判定に渡らないため写さない） | bench_004.snapshot_items | 無し |
| マスタの写し（商品・検索語・除外語・単位・状態・正規化ルール・注記・ステータス） | bench_004.snapshot_master_*（表ごと） | 無し |
| 判定結果の基準 | bench_004.baseline_results | 無し |
| 検査ごとの成績 | bench_004.bench_runs（run_id, sha, snapshot_id, changed_count, improved_count, regressed_count, elapsed_sec） | 無し |
| 変わった行の一覧 | bench_004.bench_diffs（run_id, item_id, before, after） | 無し |
| GitHub | 検査のコードのみ。スキーマ名・接続名は持つが値は持たない | コードのみ |
| 設計パートナー・実行役 | 件数・合否・列名・行番号まで。行の中身は求めない | 件数のみ |

### 3-2. ロール（最小権限）

- bench_ro: tenant_004 の対象表に SELECT のみ。bench_004 に SELECT・INSERT のみ（UPDATE・DELETE・DDL 無し）。
- 既存の qa_tenant006_rw（用途別・限定権限）と同じ流儀で1つ足す。jarvis（Superuser）は検査に使わない。

### 3-3. 検査の中身

1. bench_004 の写しをメモリに読む（bench_ro）
2. 現行コードの純関数を呼ぶ: apply_field_normalization → resolve_unit_v2 → filter_product_codes_by_unit_kubun → match_pid_name_first → resolve_condition_v2 → resolve_status_v2（analyze_extraction_job 内の呼び順のまま。順序を変えない）
3. 結果を baseline_results と突き合わせ、行ごとに 同一 / 改善（未解決→解決）/ 悪化（解決→未解決・解決先が変わる）に分ける
4. bench_runs と bench_diffs に INSERT
5. 悪化 ≥ 1 なら終了コード 1

「悪化」の定義は初版では上記2つに固定する。定義の変更は本計画書の改版として PO の○を要する。

### 3-4. 関所の位置

scripts/blue-green-cutover.sh の Step 3（health 確認成功）直後・Step 4（nginx 切替）直前に、green コンテナ内で検査を実行する。
- 悪化があれば exit 1 → 既存の trap ERR が green を片付け、旧 backend が接客を継続する
- 検査自体の失敗（接続不可など）も exit 1 で止める（安全側）
- 環境変数 BG_SKIP_BENCH=1 で一時的に飛ばせるようにするか否かは、PO 判断（初版では設けない案を推奨。抜け道は使われる）

---

## 4. 段階（1段階1PR。各段階の KGI を満たしてから次へ）

| 段階 | 内容 | 触るファイル | GO | KGI |
|---|---|---|---|---|
| 1 | bench_004 スキーマ・表・bench_ro ロールを migration で作成 | migrations/（新規1本・root直下） | 要（本番DBサーバーへの DDL） | K1 |
| 2 | 写し取りスクリプト（tenant_004 → bench_004。bench_ro で実行） | backend/scripts/bench_snapshot.py（新規） | 不要（読み取り＋bench_004 への INSERT のみ） | K2, K7 |
| 3 | 検査スクリプト（純関数を呼び、baseline と比較、bench_runs に記録） | backend/scripts/bench_check.py（新規）・backend/tests/（スクリプト自体の単体テスト） | 不要 | K3, K4, K5, K8 |
| 4 | cutover への挿入 | scripts/blue-green-cutover.sh | 要（本日2回本番を止めた場所） | K6 |
| 5 | 「解析精度管理」画面に bench_runs / bench_diffs を表示 | frontend/src・backend/app/routers/ | 要 | 画面で K3/K4 の結果が見える |

段階4は、docker run と docker-compose の設定分離（handoff 2026-09-05 recon §2-1）の整理と同じPRにしない。単独で入れる。

---

## 5. 触らないもの（名指し）

- tcg_analyzer_svc.py の判定ロジック（ADR-154。純関数を「呼ぶ」だけ。書き換えない）
- tenant_004 への一切の書き込み（bench_ro に権限を与えない）
- analysis_results（読み取りも本計画では行わない。baseline は検査が自分で計算する）
- PR #3306 / #3309 の領域（取り込みの2段階化・確認画面）
- import_jobs（LINE取り込み専用。流用しない）

---

## 6. 弊害・限界（正直に）

1. 基準は「正解」ではなく「今の答え」。今の誤判定も固定される。誤りを直すと悪化として赤になる → 人が「正しい変化」と認めて基準を更新する運用が要る。更新は migration と同じ扱いで PO の○を要する。
2. 関所が切替の直前＝マージの後。悪化が見つかるとマージ済みコードを戻す作業が要る。ただし旧 backend が接客を続けるため本番は無傷。
3. 写しは古くなる。仕入元が新しい書き方を始めると写しに無い。取り直しの頻度は運用で決める（初版では手動。定期化は第2段階の後に判断）。
4. Gemini の読み取りは測れない。本計画は「抽出された後の商品行」から先しか見ない。層2（少数原文での抽出の記録）は別計画。
5. 商品名に判別情報が無い行は、どう育てても解決しない。判定に渡るのは raw_product_name のみ（analyze_extraction_job 実測）。本計画の対象外。
6. 純関数15個のうち、resolve_unit / resolve_condition（v1）が現行で呼ばれているかは未確認。呼ばれていなければ検査対象から外す（第3段階で実測して決める）。

---

## 7. 維持の仕組み

- 守り手（自動）: 段階4の関所。悪化があれば切替が止まる。
- 守り手（手動）: 基準更新は PO の○のみ。更新履歴は bench_runs に残る。
- 検査コード自体の退行: backend/tests/ の単体テスト（写しの形が変わったとき赤になる）。
- 記録: 段階ごとの実測値を本文書 §1 の表に追記する（見積り値は書かない）。

---

## 8. 次の一手

段階1の設計（bench_004 の表定義・bench_ro の GRANT 文）を design として起こし、PO の○の後に migration カードを発行する。
設計に入る前に1点だけ実測が要る: migration の採番規則と直近の番号（推測で番号を振らない）。

---

## 実測の出所

- docs/handoff/tcg-product-master-growth/recon.md（2026-09-04・0d329d40）
- docs/handoff/tcg-2026-09-05-summary/recon.md（2026-09-05・ffd50d98）
- CARD-SHIME-RECON-01 / CARD-BENCH-RECON-01 の生出力ファイル（2026-09-05〜06・f5a65310）
- 書き込みは一切行っていない
