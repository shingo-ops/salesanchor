# v102 規則直し 便1: 状態の言葉の表に「傷あり」系を足す

親: [design.md](../../design.md) §3 便1（PO 承認 2026-10-25）。中身は `public.line_conditions` の 4 行の UPDATE だけ（コードは変えない）。値は ADR-1007 に従い data SQL で入れ、PO が `!` で流す。

## 何を変えるか

足す語: `傷あり` `傷有` `キズあり` `キズ有`（末尾に `,傷あり,傷有,キズあり,キズ有` を足す。今の値の区切りはカンマで、空白なし・末尾カンマなし）。

| code | 状態 | 変える列 |
|---|---|---|
| CN0004 | Damaged sealed box | search_kw |
| CN0002 | Damaged case | search_kw |
| CN0003 | Sealed box | exclude_kw |
| CN0001 | Case | exclude_kw |

`updated_at` も `NOW()` に更新する（前例 `docs/handoff/v102-heading-and-unit/data/` の upsert と同じ）。UPDATE の WHERE には code に加えて「変更前の md5 一致」を入れてあり、件数が 4 でなければ失敗する。

## 流す順番と印

| 順 | ファイル | 種類 | 出るべき印（全部が 1 行ずつ出ること） |
|---|---|---|---|
| 1 | precheck.sql | 読むだけ | `CAN_PROCEED\|1` / `PRECHECK_DONE`（前提と 1 つでも違えば 0 除算で失敗） |
| 2 | dryrun.sql | 入れて検査して必ず ROLLBACK | `UPDATED\|4` / `CHECK_OK 4` / `DRYRUN_OK` |
| 3 | commit.sql | 本番に反映 | `UPDATED\|4` / `CHECK_OK 4` / `COMMIT_DONE` |
| 4 | verify.sql | 読むだけ | `KW_NEW\|4` / `OTHERS_SAME\|4` / `MATCH\|4` / `VERIFY_DONE` |
| 5 | 再解析 | 7 job を `reanalyze_v102_job`（`backend/app/tasks/tcg_extraction.py:736`）で 1 つずつ | 最終行 `DONE ok=7 ng=0` |

- precheck は、4 行がそれぞれ 1 行だけあること、4 行の search_kw・exclude_kw の md5 が本番の今の値と同じこと、足す 4 語がどの列にも無いことを確かめる。
- verify の `KW_NEW|4` は足した列の md5 が期待どおり、`OTHERS_SAME|4` はほかの列（id・code・状態名・区分・有効・優先度・作成時刻・条件定義・match_type・effect・単位・note・value_group・value_rank・足さなかった側の語）が変更前のままであること、`MATCH|4` は両方。
- 再解析は Gemini を呼ばない。再解析する job の一覧は repo に置かず、`$HOME/CC報告ファイル-keep/v102-rule-fixes/bin1/jobs.txt`（7 行）を読む。

## 戻し方

1. `rollback.sql` を流す。4 行を変更前の値に戻す（WHERE は変更後の md5 一致、件数 4 でなければ失敗）。印は `REVERTED|4` / `CHECK_OK 4` / `ROLLBACK_DONE`。
2. 戻ったかは precheck.sql を流して `CAN_PROCEED|1` が出ることで確かめる（変更前の値と同じなら出る）。
3. 再解析まで進んでいた場合は、戻した後に同じ 7 job をもう一度再解析する（行の状態が元に戻る）。

## K1-1 の結果（実装前の確かめ、件数のみ）

- 4 語が当たる本番の投稿: 8 投稿。
- 当たった項目: 7 件。全件を原文で判定し、誤爆 0。
- シングル系の行に当たったもの: 0。
- 当たった項目のうち、今の在庫表に出ているもの: 2 件。
- 再解析の対象: 7 job。人の修正（item_corrections）: 0。

## 台本 run-bin1.sh（全文。PO が `!` で流す）

流すのは、この PR がマージされたあと（SQL は台本が origin/main から取り出す）。使うのは無制限鍵（manual-only）。PO が許可して流す。AI は流さない。出力は `$HOME/CC報告ファイル-keep/v102-rule-fixes/bin1/run-<時刻>/` に保存される（チャットに貼らない）。

```bash
#!/bin/bash
# v102 規則直し 便1: line_conditions 4行に「傷あり」系4語を足し、7 job を再解析する。PO が ! で実行する。
# 順序: precheck → dryrun（必ず ROLLBACK）→ commit → verify → 再解析。印が欠けたらそこで止まる。Gemini は呼ばない。
set -euo pipefail
REPO=/Users/tanizawashingo/salesanchor
KEEP=$HOME/CC報告ファイル-keep/v102-rule-fixes/bin1
JOBS=$KEEP/jobs.txt
OUT=$KEEP/run-$(date -u +%Y%m%dT%H%M%SZ)
K=$HOME/.ssh/manual-only/id_ed25519
H=ubuntu@49.212.137.46
REMOTE=/tmp/bin1_reanalyze
RUN="cd /home/ubuntu/salesanchor && docker compose exec -T postgres psql -U jarvis -d jarvis_db -X -q -t -A -v ON_ERROR_STOP=1"
RUNPY="cd /home/ubuntu/salesanchor && docker compose run --rm --no-deps -T -v $REMOTE:/m -w /app -e PYTHONPATH=/app celery-worker python -u /m/apply.py"

# (a) 事前: jobs.txt が7行・実行中のデプロイが無い
[ "$(grep -c . "$JOBS")" = "7" ] || { echo "中止: jobs.txt が7行ではありません"; exit 1; }
BUSY="$(cd /Users/tanizawashingo/salesanchor && gh run list --workflow deploy.yml --limit 5 --json status --jq '.[]|select(.status=="in_progress" or .status=="queued" or .status=="waiting")|.status')"
if [ -n "$BUSY" ]; then echo "中止: デプロイが実行中です。終わってからやり直してください。"; exit 1; fi
mkdir -p "$OUT"

# SQL は作業場所ではなく origin/main から取る（マージ後に作業場所が片付けられても流せる）。流すのはマージのあと。
git -C "$REPO" fetch -q origin
for n in precheck dryrun commit verify rollback; do
  git -C "$REPO" show "origin/main:docs/handoff/v102-rule-fixes/data/bin1/$n.sql" > "$OUT/$n.sql"
done
[ -s "$OUT/precheck.sql" ] || { echo "中止: precheck.sql が空です（マージ前、または取得失敗）"; exit 1; }
SQL=$OUT

run() { # $1=SQLファイル $2=出力名 $3...=出力に必ず含まれる印（1行まるごと一致）
  local f=$1 o=$OUT/run-$2.txt; shift 2
  ssh -i "$K" -o BatchMode=yes "$H" "$RUN" < "$f" > "$o" 2>&1 || { echo "NG: $o"; cat "$o"; exit 1; }
  for m in "$@"; do grep -qx "$m" "$o" || { echo "NG: $o に「$m」が無い"; cat "$o"; exit 1; }; done
  echo "OK: $o"
}

# (b) SQL 4本
run "$SQL/precheck.sql" 1-precheck "CAN_PROCEED|1" "PRECHECK_DONE"
run "$SQL/dryrun.sql"   2-dryrun   "UPDATED|4" "CHECK_OK 4" "DRYRUN_OK"
run "$SQL/commit.sql"   3-commit   "UPDATED|4" "CHECK_OK 4" "COMMIT_DONE"
run "$SQL/verify.sql"   4-verify   "KW_NEW|4" "OTHERS_SAME|4" "MATCH|4" "VERIFY_DONE"

# (c) 再解析（job を1つずつ）
cat > "$OUT/apply.py" <<'PY'
# 書き込みあり（PO が実行）: jobs.txt の job を reanalyze_v102_job で1つずつ再解析する（Gemini は呼ばない）
import sys, time
from app.tasks.tcg_extraction import reanalyze_v102_job as r

JOBS = [l.strip() for l in open("/m/jobs.txt") if l.strip()]
print("jobs", len(JOBS), flush=True)
ok = ng = 0
for j in JOBS:
    t = time.time()
    try:
        res = r(j)
        good = isinstance(res, dict) and res.get("status") == "reanalyzed"  # skipped（v102以外）は ng 扱い
        print(j, "ok" if good else "ng", res, round(time.time() - t, 1), flush=True)
    except Exception as e:  # noqa: BLE001
        good = False
        print(j, "ng", "EXC", repr(e), round(time.time() - t, 1), flush=True)
    if good:
        ok += 1
    else:
        ng += 1
print(f"DONE ok={ok} ng={ng}", flush=True)
sys.exit(1 if ng else 0)
PY
ssh -i "$K" -o BatchMode=yes "$H" "mkdir -p $REMOTE && chmod 777 $REMOTE"
scp -q -i "$K" "$JOBS" "$OUT/apply.py" "$H:$REMOTE/"
echo "start $(date -u +%H:%M:%SZ)"
set +e
ssh -i "$K" -o BatchMode=yes "$H" "$RUNPY" > "$OUT/out-apply.txt" 2>&1
RC=$?
set -e
echo "done  $(date -u +%H:%M:%SZ)  ssh_rc=$RC"

# (d) 後片付け（成否に関わらず）
ssh -i "$K" -o BatchMode=yes "$H" "rm -f $REMOTE/*.py $REMOTE/*.txt; rmdir $REMOTE; ls -d $REMOTE 2>&1 | head -1" || true

# (e) 末尾判定
if [ "$(tail -n 1 "$OUT/out-apply.txt")" != "DONE ok=7 ng=0" ]; then
  echo "NG: 末尾が 'DONE ok=7 ng=0' ではありません（$OUT/out-apply.txt を確認）"; tail -n 3 "$OUT/out-apply.txt"; exit 1
fi
echo "OK: DONE ok=7 ng=0"
echo "ALL_DONE"
```

再解析の成否判定の根拠: `reanalyze_v102_job` は、v102 以外の job では `"status": "skipped"`（`backend/app/tasks/tcg_extraction.py:745`）、成功時は `"status": "reanalyzed"`（同 :759-761）を返す（origin/main で確認）。解析が失敗すれば例外になり、apply.py は ng として数える。

参考にした前例: `docs/handoff/bundle-sale/bin2-record.md:33-61`（SQL を流す部分）、`docs/handoff/bundle-sale/bin3-record.md:28-`（再解析の部分）。

## 流す直前の写し（前後比較の基準）

流す直前に、7 job の全項目の今の状態・単位・商品・is_current を reader 鍵で読み、社外秘フォルダに写す（再解析の前後比較の基準）。写すのは台本の外で、Opus の担当が行う。

## 流した後に確かめること（K1-3）

reader 鍵で本番を読み、再解析の前後の表を社外秘フォルダに保存して、状態が変わった行が全部原文で正しいことを確かめる（design.md §4 K1-3）。
