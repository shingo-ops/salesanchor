# design: migration が deadlock したときだけ、その1本を流し直す

- 書いた人: Claude Opus（POの委任に基づく設計）。recon は [recon.md](./recon.md)。
- PO の依頼（2026-10-20）：「他のセッションにも影響が出ているので優先的に対応して修正してくれ」「反映を止めかねない別の原因…これも修正したほうが良いのでは？」

## 目的（KGI）
- 本番 deploy が、migration の deadlock で失敗しないこと。
  - 判定方法：deploy run のログで `deadlock detected` の後に `Migrations done.` が出れば ○。`deadlock detected` の後に `skip ai_ro views (script failed` が出れば ×。

## 対象と対象外
- 対象：scripts/run_all_migrations.sh の run_sql 関数（:61-66）だけ。
- 対象外（触らない）
  - 一覧の中身と順番、run_py、ai_ro の EXIT trap（:87-106）、deploy.yml、各 migration ファイル。
  - CI（migration-test.yml）は一覧の `^run_sql` 行を自分で読んで流すため、この関数を通らない。

## 変更前後
変更前（scripts/run_all_migrations.sh:61-66）
```bash
run_sql() {
  local file="$1"
  STEP=$((STEP + 1))
  echo ">>> [${STEP}/${TOTAL}] psql < ${file}"
  docker exec -i "${POSTGRES}" ${PSQL} < "${REPO_DIR}/${file}"
}
```
変更後
```bash
# 稼働中のアプリと deadlock したときだけ、同じファイルを流し直す（全 migration は冪等で、
# CI のドライラン2周目で再実行が通ることを確かめている）。ほかのエラーは今までどおり即停止。
SQL_DEADLOCK_MAX_ATTEMPTS=3
run_sql() {
  local file="$1"
  STEP=$((STEP + 1))
  echo ">>> [${STEP}/${TOTAL}] psql < ${file}"
  local attempt=1 rc errlog
  errlog="$(mktemp)"
  while true; do
    rc=0
    docker exec -i "${POSTGRES}" ${PSQL} < "${REPO_DIR}/${file}" 2>"${errlog}" || rc=$?
    cat "${errlog}" >&2
    if [ "${rc}" -eq 0 ]; then
      rm -f "${errlog}"
      return 0
    fi
    if grep -q "deadlock detected" "${errlog}" && [ "${attempt}" -lt "${SQL_DEADLOCK_MAX_ATTEMPTS}" ]; then
      attempt=$((attempt + 1))
      echo ">>> [${STEP}/${TOTAL}] deadlock detected; retry ${attempt}/${SQL_DEADLOCK_MAX_ATTEMPTS} in 5s: ${file}"
      sleep 5
      continue
    fi
    rm -f "${errlog}"
    return "${rc}"
  done
}
```

## 代替案と選んだ理由
- 案A：毎回作って消している古い表を、一覧から外す。
  - 不採用。理由は2つある。
    - 作る側が SQL（:319・:320）と Python（:187 の 059・:189 の 067）の両方にあり、外す範囲が広い。
    - 10/19 の line_conditions 側の deadlock は防げない。
- 案B（採用）：deadlock のときだけ、その1本を流し直す。
  - 変更は1関数だけで済む。観測した 4 回すべてで、再実行すると通っていた。
  - 冪等であることは、CI の2周ドライランが毎回確かめている。
- 案C：ADR-1005 段階2（実行済みの台帳を作り、未実行のものだけを流す）。
  - 根本的な解決になるが、影響が大きい。新しいテナントのひな形との差分もある。
  - この件では止まっている deploy を早く直すことを優先し、案Cは ADR-1005 の段取りに残す。
- lock_timeout は今回は入れない。
  - 変更は一度に1つにするため。
  - 待ち時間で落ちる別の失敗を新しく作らないため。

## リスクと対処
- 途中まで流れた1本を、もう一度流すことになる。
  - 1文ずつ自動で確定するため、途中まで反映された状態から再実行する形になる。
  - 全 migration は冪等で、CI の2周目が毎回確かめている。
- 3回とも deadlock した場合は、今までどおり止まる。ai_ro も今までどおり外れたままになる。
- エラー出力（stderr）は、そのファイルを流し終えてからまとめて出る。
  - 行の順番は少し変わるが、内容は変わらない。

## 受入条件と検証方法
| 基準 | 検証方法 |
|---|---|
| A1 正常に流れるファイルは、1回で終わり rc=0 になる | 偽の docker（PATH の先頭に置く）で、成功を返す場合を試す |
| A2 1回目に deadlock、2回目に成功するなら、retry の行を1回出して rc=0 になる | 偽の docker で、1回目だけ `ERROR:  deadlock detected` を stderr に出して rc=3 を返す |
| A3 3回とも deadlock なら、3回試して rc=3 を返し、スクリプトは止まる | 偽の docker で、毎回 deadlock を返す |
| A4 deadlock 以外のエラー（例：syntax error）は再試行せず、すぐ rc=3 を返す | 偽の docker で、`ERROR:  syntax error` と rc=3 を返す |
| A5 文法に誤りが無い | `bash -n scripts/run_all_migrations.sh`、`shellcheck` があれば流す |
| K1 本番 | マージした後の deploy run で `Migrations done.` と `ai_ro views created: 510` が出る |
| K2 本番（継続） | この先の deploy で deadlock が出ても、`retry` の行の後に `Migrations done.` が出る。10/20〜11/3 の deploy run で「deadlock で失敗した数」を数え、0 なら ○ |

## 維持の仕組み
- 冪等であることは、CI のドライラン2周（migration-test.yml）が毎回確かめる。
- K2 は、2026-11-03 に deploy run の一覧から数え直す。

## 外部・過去事例の参照と我々への応用
- 他社事例は使わない。根拠は PostgreSQL 16 の公式文書「13.3.4 Deadlocks」（https://www.postgresql.org/docs/16/explicit-locking.html 、2026-10-20 に参照）で足りる。
  - 原文: "PostgreSQL automatically detects deadlock situations and resolves them by aborting one of the transactions involved"
  - 原文: "deadlocks can be handled on-the-fly by retrying transactions that abort due to deadlocks"
- このリポジトリでも、再実行すると通ることを、上の4回で観測した。
- Context7 は月の上限に達していて使えなかった。そのため公式文書を直接参照した。
