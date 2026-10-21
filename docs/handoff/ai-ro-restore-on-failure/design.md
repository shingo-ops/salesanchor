<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — ai-ro-restore-on-failure

**対象ADR**: ADR-1024（改訂を追記）、ADR-1037（関連）  
**recon**: docs/handoff/ai-ro-restore-on-failure/recon.md  
**日付**: 2026-10-21  
**担当**: Planner（Opus）

---

## 1. 目的と成功条件（KGI）

入れ替え（デプロイ）の移行ステップが途中で失敗したとき、AI 用の読み取りビュー（ai_ro）を外したままにせず、その場で作り直す。今は、次の入れ替えが成功するまで AI が DB を読めない（recon F1・F2。10/21 は約13分読めなかった）。

PO 承認: テーマは PO「1」（2026-10-21）。成功条件の案は次の3つ。PO の返答は「確立したなら進める」（2026-10-21）。

- K1 失敗した入れ替えでもビューが作り直される（ログに作成結果の行が出て、reader の道で本数が成功回と同じ）
- K2 作り直しで在庫表を1秒より長く待たせない
- K3 作り直しが失敗しても、入れ替えの成否（終了コード）は変わらない

## 2. 対象と対象外

- 対象: `scripts/run_all_migrations.sh` の `_ai_ro_create_on_exit`（:126-144）、その上のコメント（:121-124）、作成の時間上限の変数1行（:125 の次）。新しい試験 `tests/sandbox/ai-ro-restore-on-failure.sh`。ADR-1024 の改訂欄。
- 対象外:
  - 作成 SQL（`migrations/20261017_130100_create_ai_ro_views.sql`）は変えない。拒否リストの正本もそのまま（SSOT を増やさない）。
  - 作成に lock_timeout や流し直しを足すこと（§5 の理由で足さない）。待ちの上限は statement_timeout で付ける（§3）。
  - 移行ステップが10分で打ち切られた場合や、信号で止まった場合（recon 不明点5）。
    - 設計審査が macOS の bash 3.2 で測ると、SIGTERM・SIGHUP でも EXIT trap は rc=0 として動き、今の作りでも作成に進んだ。
    - 本番の bash 5 での動きは未確認。ssh-action が打ち切ったとき、遠隔の台本に信号が届くかも未確認。
    - 今回は変えない。試験 T8 で、ubuntu の bash 5 での動きを記録だけ残す（合否にしない）。
  - deploy.yml・compose・readonly_query.py は触らない。

## 3. 変更前後

変更前（:129-132）:

```bash
  if [ "${rc}" -ne 0 ]; then
    echo ">>> [final] skip ai_ro views (script failed rc=${rc}; views stay dropped)"
    exit "${rc}"
  fi
```

変更後（:125 の次に1行足し、関数全体を次の形にする。終了コードは「元の rc」をそのまま返す）:

```bash
AI_RO_CREATE_SQL="migrations/20261017_130100_create_ai_ro_views.sql"
AI_RO_CREATE_TIMEOUT="${AI_RO_CREATE_TIMEOUT:-30s}"
_ai_ro_create_on_exit() {
  local rc=$?
  trap - EXIT
  if [ "${rc}" -ne 0 ]; then
    echo ">>> [final] script failed rc=${rc}; recreating ai_ro views anyway"
  fi
  echo ">>> [final] psql < ${AI_RO_CREATE_SQL}"
  if [ ! -f "${REPO_DIR}/${AI_RO_CREATE_SQL}" ]; then
    echo "⚠️ ${AI_RO_CREATE_SQL} が見つかりません（ai_ro は外れたまま＝AI は読めない）"
    exit "${rc}"
  fi
  # ビューは AI が読むための補助。作成に失敗しても入れ替えの成否は変えず、「読めない」側に倒す
  # 1文ごとの上限。打ち切り（57014）は作成 SQL の WHEN others に捕まらず、全体が戻って下の警告に入る
  # VERBOSITY=terse: エラーは重さ・本文・位置だけにし、CONTEXT（SQL 文）を公開ログに出さない
  if ! docker exec -e PGOPTIONS="-c statement_timeout=${AI_RO_CREATE_TIMEOUT}" -i "${POSTGRES}" ${PSQL} -v VERBOSITY=terse < "${REPO_DIR}/${AI_RO_CREATE_SQL}"; then
    echo "⚠️ ai_ro views の作成に失敗（ai_ro は外れたまま＝AI は読めない）"
    exit "${rc}"
  fi
  exit "${rc}"
}
```

コメント（:121-124）は次に置き換える:

```bash
# ADR-1024: ai_ro ビューの作成（秘密列を除く）。スクリプトの成否にかかわらず、常に最後に流す。
# 将来の migration が末尾に追記されても、作成は常に最後になる。
# 途中で失敗した場合も作り直す（拒否リストは流した時点の列名で決まり、途中の状態にも同じ判定が当たる。ADR-1024 改訂）。
# 作成の成否は終了コードを変えない（元の rc を返す）。待ちの上限は AI_RO_CREATE_TIMEOUT（1文ごと）。
# （TOTAL は ^run_ 行を数えるため、ここでは run_sql を使わず直接流す）
```

- rc≠0 のとき: 作成を飛ばさずに流してから、元の rc で終わる。
- rc=0 のとき: 「作成→成否にかかわらず exit 0」は今と同じ。違うのは、作成が鍵を待ち続けても30秒で打ち切って警告に入ること（今は上限が無く、10分の打ち切りまで待ちうる）。
- 30秒の根拠: 成功回の作成は約0.7秒（recon F3）。上限は1文ごとにかかる。DO ブロック1つ（511本）に30秒あれば、40倍の余裕がある。
- statement_timeout を選んだ理由:
  - PostgreSQL 16 公式文書（plpgsql-control-structures、2026-10-21 確認）には「The special condition name OTHERS matches every error type except QUERY_CANCELED and ASSERT_FAILURE.」とある。
  - statement_timeout の打ち切りは query_canceled（57014。errcodes-appendix、同日確認）になる。1本ずつの例外処理（create SQL :68）には飲まれず、作成全体が戻る。
  - lock_timeout の失敗は lock_not_available（55P03）になり、WHEN others に捕まる。捕まると、そのビューだけ欠けたまま作成は成功扱いになる。
- VERBOSITY=terse を足した理由（コード審査 M1、2026-10-21）:
  - 打ち切りの回（T7）だけ、ログに `CONTEXT:  SQL statement "CREATE VIEW ai_ro.… AS SELECT <列> FROM …"` が出た（sandbox run 39598850269）。表名と、拒否リストを通った列名が公開ログに出る。
  - PostgreSQL 16 公式文書（libpq-control、2026-10-21 確認）には「In TERSE mode, returned messages include severity, primary text, and position only」とある。app-psql の SHOW_CONTEXT の項には「This setting has no effect when VERBOSITY is set to terse or sqlstate.」とある。
  - 成功回の作成結果の行（`RAISE NOTICE 'ai_ro views created: …'`、create SQL :74）は本文（primary text）なので、今のまま出る。K-本番1 の数え方は変わらない。

## 4. 影響範囲（呼び出し元の全走査）

- `_ai_ro_create_on_exit` を使うのは :145 の `trap` だけ（recon :28）。
- `scripts/run_all_migrations.sh` を呼ぶのは `.github/workflows/deploy.yml:577`（`bash scripts/run_all_migrations.sh`）だけ。終了コードで成否を決める。終了コードは変わらないので、deploy.yml の分岐は今と同じに動く。
- ai_ro を読むのは `backend/app/ops/readonly_query.py` だけ（recon :37）。読む側は変えない。
- ログの文面「skip ai_ro views」「views stay dropped」を機械で数える仕組みは無い。`git grep -n -e "skip ai_ro" -e "views stay dropped" origin/main`（2026-10-21）のヒットは台本の :130 と、過去の設計書2つ（`docs/handoff/migration-deadlock-retry/design.md:8` の判定方法、`docs/handoff/shime-review-exclude/design.md:506` の記録）だけ。前者は「失敗したら × 」の目印にこの文面を使っている。変更後は失敗回の目印が「script failed rc=」になる。過去の記録なので書き換えず、ADR-1024 改訂欄に文面が変わったことを書く。
- 作成の psql は `-v ON_ERROR_STOP=1`（:25）。作成 SQL の途中で失敗すれば 0 以外を返し、警告の分岐に入る。
- 作成 SQL の既存試験 `backend/tests/ops/test_ai_ro_views.py:29` は、作成 SQL を直接流す。台本を通らないので影響は無い。
- 利用者向けの使い方 `docs/handoff/ai-readonly-db-path/usage.md:38-40`（§4 デプロイ中の 42P01）に、「移行が失敗した回も、最後に作り直される」を1文足す。

## 5. 代替案と選択理由

| 案 | 内容 | 判断 |
|---|---|---|
| A（採用） | 失敗時も作成を流し、元の rc で終わる | 変更が1か所。成功時の動きは今と同じ |
| B | 作成に lock_timeout=1s と流し直しを足す | 不採用。lock_timeout の失敗（55P03）は、1本ずつの EXCEPTION（create SQL :62-71）に飲まれる。鍵を持たれた表のビューだけが欠けたまま、作成は成功扱いになる。欠けた表の名前は NOTICE（:74）に出るが、終了コードでは分からない |
| B'（採用。A に足す） | 作成に statement_timeout=30s を渡す | 採用。打ち切り（57014）は WHEN others に捕まらず、全体が戻る。結果は「全部ある」か「警告」の2つだけになる。ACCESS EXCLUSIVE の持ち主がいても、10分待ち続けない（設計審査 M1） |
| C | 失敗時は deploy.yml の別ステップで作る | 不採用。作成の場所が2か所に分かれ、配線の正本が増える |
| D | 今のまま（次の成功で戻る） | 不採用。F1 で8回とも外れたまま、10/21 は約13分 |

## 6. リスクと対処

- R1 途中まで進んだ状態の DB にビューを作る → 拒否リスト（create SQL :23）は、流した時点のカタログにある列名で決まる（:29-41）。
  - 途中まで進んだ状態の列名にも、同じ判定が当たる。新しい表に秘密列があっても、名前で外れる。
  - 設計審査が数えると、run_sql 334本のうち321本は BEGIN が無い。途中の状態（改名の途中の列名など）が残りうる。
  - 秘密系の列の `RENAME COLUMN` は、登録済みの BEGIN の無い移行に0件だった。今は害が無い。
  - 試験 T1 で、秘密列がビューに出ないことを確かめる。
- R2 ai_reader ロールが無い DB（新しい環境で、ロール作成 :1037 より前に失敗）→ 作成全体がロールバックされ0本。今と同じ結果で、警告を出して元の rc で終わる。試験 T3。
- R3 DB が落ちていて失敗した → 作成も失敗し、警告を出して元の rc で終わる。待ち時間は psql の接続失敗だけ。
- R4 作成が ACCESS EXCLUSIVE を持つ接続に当たって待つ → 失敗した移行の psql は終わっていて、その鍵は既に外れている。
  - 10/21 に products の鍵を持っていた相手の、鍵の種類は未確認（ADR-1037:41）。
  - ほかの接続が ACCESS EXCLUSIVE を持つ場合は、後から来た在庫表の読み取りも同じ鍵を待つ。作成のせいで増える待ちは無い（recon 不明点2）。
  - 作成は30秒で打ち切られ、全体が戻る。そのあと警告を出して、元の rc で終わる。試験 T7 で確かめる。
- R5 trap 登録（:145）より前の失敗 → ビューはまだ外していないか、外す SQL が1本で失敗して残っている。今と同じ。

戻し方: この PR を revert する（動きが変わるのは scripts/run_all_migrations.sh だけ。ほかは試験と文書。DB の形は変えない）。

## 外部・過去事例の参照と我々への応用

- 事例1: 本リポジトリ 10/21 の失敗回（run 39575250541、recon F2）。ビューを外したまま約13分 AI が読めなかった → 我々への応用: 失敗しても作り直せば、外れる時間は作成の約0.7秒（F3）だけになる。
- 事例2: PostgreSQL 16 公式文書 explicit-locking（2026-10-21 確認、recon F6）。ACCESS SHARE は ACCESS EXCLUSIVE とだけ衝突する → 我々への応用: 作成に lock_timeout を足さない根拠。
- 外部の他社事例: 該当なし。理由: 変更は自前の台本の終了処理1か所で、判断の根拠は自分の環境の実測（F1〜F5）で足りるため。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| T1 移行が rc=3 で失敗しても、ビューが作られ、終了コードは3のまま。ログに「recreating ai_ro views anyway」が出る。ログの「ai_ro views created: N」の N と、作成後の ai_ro のビュー数が同じ。秘密列（例 api_token）はビューに無い | sandbox-test.yml で `tests/sandbox/ai-ro-restore-on-failure.sh`（使い捨て postgres:16） |
| T2 移行が成功したとき、ビューが作られ終了コードは0 | 同上 |
| T3 ai_reader が無い DB で失敗したとき、終了コードは元の rc のまま、ログに固定の文字列「ai_ro views の作成に失敗」が出る | 同上 |
| T4 移行は成功し、作成だけ失敗したとき、終了コードは0 | 同上 |
| T5 ほかの接続が元の表を読み取り中（ACCESS SHARE）でも作成は待たず、作成中の読み取りは1秒以内に返る | 同上（経過ミリ秒を出す） |
| T7 別の接続が試験の表に ACCESS EXCLUSIVE を持ったまま、移行が rc=3 で失敗したとき、作成は試験用の上限（AI_RO_CREATE_TIMEOUT=3s）で打ち切られる。開始から10秒以内に終わり、終了コードは3、ログに「ai_ro views の作成に失敗」が出る。ai_ro のビューは0本（全体が戻った）。ログに `CONTEXT:` と `SQL statement` が0行（コード審査 M1） | 同上 |
| T8（記録だけ。合否にしない）ubuntu の bash 5 で、移行の途中（sleep 中）に子の bash へ SIGTERM を送ったときの終了コードと、作成が流れたか | 同上（ログに出す） |
| T6 抜き出した関数が本物の台本と同じ | 試験が `scripts/run_all_migrations.sh` から `^AI_RO_CREATE_SQL=`（:125）〜 `^trap _ai_ro_create_on_exit EXIT` を切り出して使う（写しを持たない）。範囲には時間上限の変数と trap の登録が入る。POSTGRES・PSQL・REPO_DIR と set -e は試験側で用意する |
| K-本番1 入れ替え後、ログに「skip ai_ro views」「views stay dropped」が0行。作成結果の行で failed 0 | deploy ログを `/usr/bin/grep -a` で数える |
| K-本番2 次に移行が失敗した回で、ログに「recreating ai_ro views anyway」と作成結果の行が出る。同じ回の「created N」と、reader の道で数えた本数が同じ | 次の失敗回が来たときに確かめる（来るまで未確認と記録） |

---

## 技術 How・KPI

- KPI: 移行が失敗した入れ替えで、AI が読めない時間を「次の成功まで（10/21 は約13分）」から「作成の約0.7秒」にする。
- 技術選択: 既存の EXIT trap の中で分岐を1つ外す（理由: 作成の場所を1か所に保つ。§5）。

---

## 弊害・トレードオフ

- 失敗時のログが数行増える（作成結果の NOTICE）→ 対策: 値や SQL 文は出ない（件数と表名だけ。公開リポの方針どおり）。表名は今の成功回でも出ている。作成が打ち切られた回の CONTEXT（SQL 文）は、VERBOSITY=terse で出さない（コード審査 M1、試験 T7 で確かめる）。
- 失敗時の終了が約0.7秒遅れる → 対策: 不要（deploy の打ち切りは10分）。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | 設計審査（Architect） | Opus |
| 2 | 実装カード | Opus |
| 3 | trap の変更と試験の追加、sandbox-test.yml で試験を流す | Sonnet |
| 4 | コード審査 | Opus |
| 5 | PR・委任 GO・マージ・入れ替えの確認（K-本番1） | Opus |

---

## 継続

- 完了後の監視: 入れ替えのたびに、ADR-1037 の計測（"lock conflict; retry" など）と一緒に「recreating ai_ro views anyway」と作成結果の行を数える。
- 次フェーズへの引き継ぎ: K-本番2 は次の失敗回が来るまで未確認。来たら ADR-1024 の改訂欄に結果を追記する。
- 維持する担当・仕組み: 試験 `tests/sandbox/ai-ro-restore-on-failure.sh` が本物の関数を切り出すので、関数を変えれば試験も変わる。
