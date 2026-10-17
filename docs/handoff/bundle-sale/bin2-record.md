---
mode: handoff
adr: ADR-1027
status: 便2 本番投入済（2026-10-17、実行者 PO）
---

# bin2-record — まとめ売り 便2（本番データ投入）の記録

親: [design.md](./design.md) 5-6（便2）／[ADR-1027](../../adr/ADR-1027-bundle-sale-reading.md)

## 1. 目的

design.md 5-6 の便2。記録した SQL を本番で DRY-RUN → COMMIT → verify し、次の2つを入れる。
- 単位の呼び名 6 行（line_units の name_ja / name_en）
- 理由コード 1 行（review_reason_codes に bundle_unverified）

## 2. 事前読み取り（実行前）

reader の道（AI 用の本番 DB 読み取り専用、ADR-1024）で読んだ。生出力: /tmp/CC報告ファイル/bundle-sale/bin2/step1a.txt／step1a2.txt／step1b.txt／step1c.txt

- line_units 対象 6 行（id 9, 10, 11, 12, 13, 16）は name_ja・name_en とも NULL（step1a2.txt: 6 行すべて `True|True`）。
- review_reason_codes は 38 件、うち bundle_unverified は 0 件（step1b.txt: `38|0`）。
- review_reason_codes の列は code・source・fix_stage・created_at（すべて NULL 可、既定値なし）（step1c.txt）。

## 3. 実行

- 実行者: PO。`!` で台本 run-bin2.sh を実行（2026-10-17）。終端は `ALL_DONE`。
- 手順: dry_run 2 本（units_display_dry_run.sql、bu_dryrun.sql。必ず ROLLBACK）→ commit 2 本（units_display_commit.sql、bu_commit.sql）→ verify 2 本（units_display_verify.sql、bu_verify.sql）。
- 止まる仕組み: 台本は各 SQL の出力に必ず含まれる印（例 `DRYRUN_OK`、`CHECK_OK 6`、`ROWS_OK 39`）を `grep -x` で確認し、欠けたらその場で exit する。`set -euo pipefail` で ssh 失敗時も止まる。dry_run の印が揃わなければ commit には進まない。

### 実行した台本（run-bin2.sh 全文）

```bash
#!/bin/bash
# まとめ売り便2（ADR-1027）: 本番に 単位の呼び名6行 と 理由コード1行 を入れる。PO が ! で実行する。
# 順序: 試し2本（必ず ROLLBACK）→ 両方の印が揃ったときだけ本番2本 → 確認2本。印が欠けたらそこで止まる。
# 出力: /tmp/CC報告ファイル/bundle-sale/bin2/run-*.txt（チャットに貼らない）
set -euo pipefail
W=/Users/tanizawashingo/worktrees/salesanchor/release-bundle-sale-bin2
D=/tmp/CC報告ファイル/bundle-sale/bin2
K=~/.ssh/manual-only/id_ed25519
H=ubuntu@49.212.137.46
RUN="cd /home/ubuntu/salesanchor && docker compose exec -T postgres psql -U jarvis -d jarvis_db -X -q -t -A -v ON_ERROR_STOP=1"
UD=$W/docs/handoff/bundle-sale/data
BD=$W/docs/handoff/v102-prod-switch/data/review_reason_codes

run() { # $1=SQLファイル $2=出力名 $3...=出力に必ず含まれる印
  local f=$1 o=$D/run-$2.txt; shift 2
  ssh -i $K -o BatchMode=yes $H "$RUN" < "$f" > "$o" 2>&1 || { echo "NG: $o"; cat "$o"; exit 1; }
  for m in "$@"; do grep -qx "$m" "$o" || { echo "NG: $o に「$m」が無い"; cat "$o"; exit 1; }; done
  echo "OK: $o"
}

run "$UD/units_display_dry_run.sql" 1-units-dryrun "UPDATED|6" "CHECK_OK 6" "DRYRUN_OK"
run "$BD/bu_dryrun.sql"             2-bu-dryrun    "INSERTED|1" "CHECK_OK 1" "ROWS_OK 39" "DRYRUN_OK"
run "$UD/units_display_commit.sql"  3-units-commit "UPDATED|6" "CHECK_OK 6" "COMMIT_DONE"
run "$BD/bu_commit.sql"             4-bu-commit    "INSERTED|1" "CHECK_OK 1" "ROWS_OK 39" "COMMIT_DONE"
run "$UD/units_display_verify.sql"  5-units-verify "VERIFY_DONE"
run "$BD/bu_verify.sql"             6-bu-verify    "bundle_unverified|system|analysis" "ROWS|39" "VERIFY_DONE"
echo "ALL_DONE"
```

## 4. 結果（出力行そのまま）

### run-1-units-dryrun.txt
```
UPDATED|6
CHECK_OK 6
DRYRUN_OK
```

### run-2-bu-dryrun.txt
```
INSERTED|1
CHECK_OK 1
ROWS_OK 39
DRYRUN_OK
```

### run-3-units-commit.txt
```
UPDATED|6
CHECK_OK 6
COMMIT_DONE
```

### run-4-bu-commit.txt
```
INSERTED|1
CHECK_OK 1
ROWS_OK 39
COMMIT_DONE
```

### run-5-units-verify.txt
```
9|Case|カートン|Case
10|Box|BOX|Box
11|Pack|パック|Pack
12|Piece|枚|Piece
13|Set|セット|Set
14|本|NULL|NULL
15|点|NULL|NULL
16|個|個|Item
17|Booklet|NULL|NULL
18|MasterCarton|NULL|NULL
VERIFY_DONE
```

### run-6-bu-verify.txt
```
bundle_unverified|system|analysis
ROWS|39
VERIFY_DONE
```

読み方（verify）: id 9 Case=カートン/Case、10 Box=BOX/Box、11 Pack=パック/Pack、12 Piece=枚/Piece、13 Set=セット/Set、16 個=個/Item が入った。14・15・17・18 は NULL のまま（対象外）。bundle_unverified は source=system・fix_stage=analysis で入り、review_reason_codes は 39 件（事前 38 + 1）。

## 5. 戻し方

- 単位の呼び名: [units_display_rollback.sql](./data/units_display_rollback.sql)
- 理由コード: [bu_rollback.sql](../v102-prod-switch/data/review_reason_codes/bu_rollback.sql)（この PR で追加）

どちらも本番での実行は PO の承認後。

## 6. 次

便3（design.md 5-6。便2 の後）。
