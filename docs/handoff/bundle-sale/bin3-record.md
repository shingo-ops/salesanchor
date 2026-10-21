---
mode: handoff
adr: ADR-1027
status: 便3 再解析 93 job 済（2026-10-17、実行者 PO）・K1 PO 目視 ○（2026-10-18、PO チャット「y」）・K2 の値段は本文と未照合
---

# bin3-record — まとめ売り 便3（再解析と照合）の記録

親: [design.md](./design.md)（便3）／[ADR-1027](../../adr/ADR-1027-bundle-sale-reading.md)／前の便: [bin2-record.md](./bin2-record.md)

生出力は /tmp/CC報告ファイル/bundle-sale/bin3/ に保存（下記に各パス）。仕入元の LINE 本文は載せない（ID・数値・商品名のみ）。

## 1. 対象

93 job。設計の 92 job から 1 増えた。増えた 1 件は job 0d163f4c で、2026-10-17 12:53Z の解析で入った新規投稿であり、他の 92 job と同じ決め方（まとめ売りの候補になる投稿）で拾った（Opus の判断）。一覧: /tmp/CC報告ファイル/bundle-sale/bin3/jobs_now.txt（旧 92 件: jobs92_old.txt）

## 2. 事前確認

- 換算済み 13 行（÷N されていた行）に人の直しがあるか: 0 件。見た場所は `apply_value_overrides` が元にする `public.item_corrections`（`backend/app/services/v102_human_decisions_svc.py:524`）。
- 再解析前の値 867 行を保存: /tmp/CC報告ファイル/bundle-sale/bin3/before.tsv。取り直し（before2.tsv）と完全一致（run/before-vs-before2.diff）。

## 3. 実行

- 実行者: PO。`!` で run-bin3.sh を実行。Gemini は呼ばない（`reanalyze_v102_job` を 1 job ずつ）。
- 結果: out-apply.txt に job の行が 93 行（すべて `ok`）、末尾 `DONE ok=93 ng=0`。時刻は 16:16:49Z〜16:30:57Z（2026-10-17）。出典: PO の端末に出た start / done の表示を保存したもの（/tmp/CC報告ファイル/bundle-sale/bin3/run/po-terminal.txt）。out-apply.txt にはこの 2 値は無い。各行の全文はここに載せない（run/out-apply.txt）。
- 止まる仕組み: 実行中のデプロイがあれば中止／jobs.txt が 93 行でなければ中止／末尾が `DONE ok=93 ng=0` でなければ NG で終了（`set -euo pipefail`）。

### run-bin3.sh（全文）

```bash
#!/bin/bash
# 便3(まとめ売り再解析93job): jobs.txt の job を作業用コンテナで解析し直す（書き込みあり・PO が ! で実行）。Gemini は呼ばない。
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
REMOTE=/tmp/bin3_reanalyze
KEY=~/.ssh/manual-only/id_ed25519
HOST=ubuntu@49.212.137.46
RUN="cd /home/ubuntu/salesanchor && docker compose run --rm --no-deps -T -v $REMOTE:/m -w /app -e PYTHONPATH=/app celery-worker python -u /m/apply.py"

# (a) 実行中のデプロイが無いこと
BUSY="$(cd /Users/tanizawashingo/salesanchor && gh run list --workflow deploy.yml --limit 5 --json status --jq '.[]|select(.status=="in_progress" or .status=="queued" or .status=="waiting")|.status')"
if [ -n "$BUSY" ]; then
  echo "中止: デプロイが実行中です。終わってからやり直してください。"; exit 1
fi
[ "$(grep -c . jobs.txt)" = "93" ] || { echo "中止: jobs.txt が93行ではありません"; exit 1; }

# (b) 送る
ssh -i "$KEY" "$HOST" "mkdir -p $REMOTE && chmod 777 $REMOTE"
scp -q -i "$KEY" jobs.txt apply.py "$HOST:$REMOTE/"

# (c) 実行（終了コードは (d) で見る）
echo "start $(date -u +%H:%M:%SZ)"
set +e
ssh -i "$KEY" "$HOST" "$RUN" > out-apply.txt 2>&1
RC=$?
set -e
echo "done  $(date -u +%H:%M:%SZ)  ssh_rc=$RC"

# (e) 後片付け（成否に関わらず）
ssh -i "$KEY" "$HOST" "rm -f $REMOTE/*.py $REMOTE/*.txt; rmdir $REMOTE; ls -d $REMOTE 2>&1 | head -1" || true

# (d) 末尾判定
if [ "$(tail -n 1 out-apply.txt)" != "DONE ok=93 ng=0" ]; then
  echo "NG: 末尾が 'DONE ok=93 ng=0' ではありません（out-apply.txt を確認）"; tail -n 3 out-apply.txt; exit 1
fi
echo "OK: DONE ok=93 ng=0"
```

### apply.py（全文）

```python
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
```

## 4. 照合（K1〜K6）

判定の基準は kgi.md。check/summary.md は check6 の調べの前の中間の判定（K2 ×・K6 保留）で、check6 で規則による外れと分かったため、この記録で判定し直した。

取得: run/fetch-after.sh → check/after.tsv（861 行・93 job）。before.tsv は 867 行。照合の全体: /tmp/CC報告ファイル/bundle-sale/bin3/check/summary.md（生出力は同フォルダ）。

| # | 基準 | 観測値 | 判定 |
|---|---|---|---|
| K1 | 4周年40パックセット行が 3 画面で「商品名 40パックセット／Pack／24,000円／15」 | DB: item 8d9eea15 は bundle_size=40・unit=Pack・数量 15・値段 24000・needs_review=False。配信式で商品名=「4周年!四皇トレジャーゲット キャンペーンパック 40パックセット」。画面は 3 画面（在庫表・閲覧ページ・GAS在庫一覧）で PO が目視 | ○（根拠: PO チャット回答 y（2026-10-18）。DB 側も一致: 「…キャンペーンパック 40パックセット」・24000・15） |
| K2 | 決まる行が bundle_size=本文の数・値段=本文のまとめ値段・単位=中身の単位 | replay の decided は 145 行。after で bundle_size が入った行は 144 行。145 行すべてで bundle_size と単位が replay と一致（144 行は現行行、1 行 ddf2bfa8 は bundle_size=100 で入ったが 5 の規則で現行から外れた）。decided 以外で bundle_size が付いた行 0。値段は replay に本文値が無く、本文との直接照合はしていない（13 行は K5 で一致、ほかは before と同じ値） | まとめの数・単位 ○（145/145）／値段は本文と未照合 |
| K3 | 誤り 3 種（154c8ea1・dbe5702e・64255758）にまとめの数が付かない | 3 item とも bundle_size 空、replay 判定 none。注記: 3 件とも 93 job の外の行で、今回は再解析していない（最新計算 10/16〜10/17 10:44） | ○（再解析で確かめた形ではない） |
| K4 | 決まらない 5 種に要確認の印、配信に出ない | 5 種とも needs_review=True・review_reasons に bundle_unverified（5/5）。配信条件（check/k4_dist_cond.tsv）では pid_resolved=False が 4 件（3a81d9cf・75100be0・7a3a3150・a98fe6ba）、exclusion=excluded が 2 件（6943d3a1・a98fe6ba）で、a98fe6ba は両方。5 件とも少なくとも一方で外れる。配信 SQL を実際に流した出力は未取得 | ○ |
| K5 | ÷N されていた 13 行が本文どおりに戻る | 13/13 行が V102:bulk:set:100(1000) の price_basis から変化。例 cd0d1216: 380円/1300 → 38000円/13。13 行すべて bundle_size 入り・decided | ○ |
| K6 | まとめ売りでない行の単位・値段・数量が変わらない | まとめでない 717 行で unit・値段・数量の変化 0。現行から外れた非対象 5 行も単位・値段・数量は before と同じ（before.tsv・check6/six.tsv） | ○ |

### 列ごとの差（両方にある 861 行）

| 列 | 変わった行数 |
|---|---|
| bundle_size | 144 |
| unit_id | 89 |
| review_reasons | 17 |
| quantity_normalized | 13 |
| price_normalized | 13 |
| price_basis | 13 |
| needs_review | 9 |
| product_id | 1 |
| condition_canonical / status | 0 |

before にあって after に現行行が無い item は 6（5 に記す）。after だけの item は 0。

### A6 の差（まとめ非対象で before と after が違う行）6 行

- 5 行: review_reasons に bundle_unverified が付いただけ（単位・値段・数量は同じ）。
- 1 行 05633643（job 5f886d8c）: product_id が空 → 466068 に付いた。needs_review True→False、review_reasons「product_not_in_master,gemini_gap_suspect」→空。マスタ 466068 の updated_at は 2026-10-16 01:39:59Z。before の computed_at 2026-10-12 19:46:14Z、after 2026-10-17 16:22:32Z（マスタ更新が再計算の間にある）。

## 5. 現行から外れた 6 item の理由

生出力: /tmp/CC報告ファイル/bundle-sale/bin3/check6/（six.tsv・rivals.tsv・grep.txt・rule.txt）

規則: `backend/app/services/tcg_analyzer_svc.py` の `_merge_supplier_products`（:1951-2100、UPDATE は :2076-2081）。キーは (supplier_channel_id, product_id, condition_id)。同じ仕入元・同じ商品・同じ状態の中で、received_at が最も新しい投稿（同順は computed_at の最大、次に job_id）の行が is_current=TRUE になり、ほかの投稿の行は FALSE になる。

再解析前（根拠: before.tsv）、fea86f11・dba96a1d・c0207d4f・ddf2bfa8 の 4 行は product_id が空で、この規則の対象外だった。b6299b96・b4ebf4e9 の 2 行は product_id 440301 で現行だったが、再解析で 466088 に変わった。6 行とも、同じ仕入元の新しい投稿の行に負けた。

同じ仕入元かの確認: 勝った側の job（3b770f96・38d43356・8dcbfc9c・5f886d8c）と負けた側の job（b8f6e15a・031eebc3・38e82e4d・5f886d8c）の supplier_channel_id を reader の道で取り直した（check6/channels.sql・check6/channels.tsv）。組ごとに同じ仕入元だった: b8f6e15a と 3b770f96 は 792c36ef、031eebc3・5f886d8c・38d43356 は cac4a471、38e82e4d と 8dcbfc9c は bf8ee742。

| 外れた item | job | 商品 | 状態 | 受信 | 勝った相手の item | 相手の job | 相手の受信 |
|---|---|---|---|---|---|---|---|
| b6299b96 | b8f6e15a | 466088 | 14 | 2026-10-17 03:29Z | job 3b770f96 の 2 行（a91906e3・48580e77）が現行 | 3b770f96 | 2026-10-17 06:14Z |
| b4ebf4e9 | b8f6e15a | 466088 | 14 | 2026-10-17 03:29Z | 同上 | 3b770f96 | 2026-10-17 06:14Z |
| fea86f11 | 031eebc3 | 466068 | 12 | 2026-10-10 04:11Z | 05633643 | 5f886d8c | 2026-10-11 00:47Z |
| dba96a1d | 5f886d8c | 466063 | 14 | 2026-10-11 00:47Z | dfd1b1cb | 38d43356 | 2026-10-17 13:40Z |
| c0207d4f | 031eebc3 | 466063 | 14 | 2026-10-10 04:11Z | dfd1b1cb | 38d43356 | 2026-10-17 13:40Z |
| ddf2bfa8 | 38e82e4d | 200 | 46 | 2026-10-12 11:40Z | 7eb5c5dc | 8dcbfc9c | 2026-10-16 07:03Z |

勝ち負けは job 単位で決まり、item 同士の対応はない（tcg_analyzer_svc.py :2064-2072）。

- ddf2bfa8 は K2 の 145 行のうちの 1 行（bundle_size=100、数量 1、値段 24000）。相手 7eb5c5dc も bundle_size=100（数量 1、値段 24500）。
- 6 件とも ar は 1 件のみで is_current=False（check/missing6_ar.tsv）。内訳は check6/six.tsv・rivals.tsv。
- 付随（30th）: b6299b96・b4ebf4e9 は再解析で product 466088 になったが、同じ仕入元の新しい投稿 3b770f96（2026-10-17 06:14）の 466088 の行が現行。

### 残る注意（事実）

- この規則のキーに bundle_size は無い。配信の gkey（`backend/app/services/tcg_distribution_svc.py:347`）には bundle_size が入っている。
- したがって、同じ仕入元が新しい投稿で同じ商品・同じ状態を別のまとめ数やバラで出すと、古い投稿のまとめ行は現行から外れる。
- 今回の 6 件では、この形（相手が別のまとめ数・バラ）は観測していない。
- 扱いは未決。PO 判断事項として記録する。

## 6. 対象 93 job

```
031eebc3-cdcf-4b44-bcc1-df5692cb1c68
047000de-c742-4000-8370-ab68b5eca303
0734aa65-e9a4-423b-a7ea-8a5f71d462e4
089808b7-e7fa-4473-a8dc-e1335e2b4bfd
0b509282-19a2-4117-bb71-9441ddb76fc0
0b9c69f2-6658-47fa-a696-128fded49a39
0ce46a16-d22b-4df4-8bfa-d28dab3e36b1
0d163f4c-cca9-49d5-a354-935ccbbf7685
101d12e5-c25c-4700-baf7-99032d804061
1180d88a-f256-4713-84b2-7d4437548057
14e1e684-e903-4056-8989-942ccbe82ae8
17fbb3fb-a748-4a6d-b147-0fca014bc178
18b7977b-f5ea-4142-a978-0b177a49c87a
1acd5ab7-0775-44f4-afc4-6544392bb074
1be17eed-21ce-4e86-8a83-416d9476c31c
1c168d1e-854a-4bd9-bd98-33bd1eedee53
1e1c1952-9610-48a3-a0f7-8412a5366701
2705fe9f-1fc4-44ba-86db-b9ee9400de37
2e0af641-4e0f-4aee-83c2-a0b4acc5f5fb
341c284f-cffd-4869-86a1-a71b57fac310
3692888a-5e8c-4def-8556-57f58b6b1793
38e82e4d-a9fb-4ae1-b7e1-6e17cfe62902
38fc42e0-0987-41f5-b407-3d7d2c479ecc
39434c20-496d-4f6b-bd84-dd9887e7ded4
3af22170-d944-4e1d-a710-909d6c02a045
3b5f7af1-1e4b-452b-b559-fefce4b64892
3f48fa3b-51c1-4161-86dd-9ea28c0a3ac8
41048ca2-ccb1-49e4-a7c1-3398de64b1a4
4356576c-d360-4fe3-9368-47acd471a34b
44e69f81-9116-474f-9331-ef177649a569
4501a32a-1a70-490c-9ad1-af5d4586c3d5
4a302007-0708-44e7-9084-d26dd5893802
4b7343b7-5539-41ec-b42d-6871cfa95aab
4c9c54d3-c714-4644-904b-d9971382c9e0
4cc9baa3-701f-419a-b374-6ef01f552019
4cdcda6c-ec34-44b4-a41d-a38e85d90bca
4d065289-0a8d-43db-9971-db1a4a2c97f1
5b301c98-b0a3-434c-ae96-82ea3e0ad90b
5f4c66fe-94fc-44c5-a723-a108c21d2c6a
5f886d8c-d7a3-4ca9-bf86-259ecfa517f8
5fb8c785-9661-4f55-a01c-560ea8e0f0a3
5fe7822e-8f56-48fd-bde8-c220207e1b36
6059f3c1-bbcf-49f3-ac8b-0ad1e764cef4
6075873f-4e83-4d0c-ad24-14cd5eee3db2
60c06350-8ce7-47bc-a72b-84d1418e7001
6766a83f-d2ae-4517-9d54-8ec3d2a50297
6ed1fa29-32ee-4dc0-b1ac-f8ad618ec9d5
74e46e93-506a-4cee-bd40-0f5615cbfb5a
76462aa2-a58c-45ff-b8ba-4880b47dc4a7
77101fb0-2d77-48db-bdc9-83146c2fb08b
7943c193-c7fb-441f-a4b5-d15b81284821
7de3f9d1-6efc-44ce-94df-eee378dc2694
821d235a-4300-43f0-bd3b-2318cfc8316d
8579f3da-4ab7-4f81-a1d0-fb6909751253
85b9484a-026b-4b24-a088-929761f43a90
875b5f1a-f5a4-4127-a47d-b8b23d979242
88cb0e6e-274d-45eb-aa8b-e8a31f2246d1
8dcbfc9c-dc96-4e55-b341-4502feda5a62
8e1245b2-0015-4865-a544-841fb70baf10
931c7533-447b-4719-8a8c-024705d24d25
9cff5ae3-4d3f-422e-bf41-699e1912aa61
a05187fc-448d-48b8-a45d-5bca6aab9eb2
a9d60e08-c7d7-47ee-b395-94a1e3ed49dd
aed65eae-4a84-454b-a0e4-b26835ae6f3b
b8f6e15a-d2ab-48cc-928c-f18304fe6c86
c2f2998a-ba9e-4990-a6b1-56d15107caad
c3787fde-a51a-4d59-9ff5-ebf57974ea52
c5d6f58b-9871-41ef-b83c-5e49b69a7b22
cb42de20-760e-4619-a131-b245ad70c299
cd02f0b6-ed0e-483f-a5dc-e5f624bf7a86
d693392a-a89e-49c8-be24-359f57ec712d
d706850a-0819-4ca6-9c33-d88e77a70521
d7ceb732-3969-4129-bd77-d4adab9060ac
d894dfc7-e685-4da8-9970-622f7f7ae3bd
dde31f4c-d41e-4664-ba31-bde68a565052
e4c664ee-229e-48a7-a99b-b6c4466c209e
e50e771c-a76c-4851-bd25-60818cc3db62
e51bdfe6-ec07-4922-a7bc-0b590fa8a7a2
e74be62c-6e69-4745-beea-594ccfc72b5f
e79e1f60-fd42-40d9-b948-72150b8c6c2c
e811c9b8-d193-4351-9c0b-103755720c9b
e905d603-a4e0-4a78-8e19-4dcf87d7663d
ea4d7380-358b-47f6-84fa-712841137da0
eae08833-668a-457c-b3d5-b49a0b4c0c84
ed487199-1b6b-4683-8c5a-2b920776d587
eeb189f2-6f03-4471-97fe-1d026c334f24
ef0eda08-253f-4e03-a9f0-88a03091fa6f
f13a23f9-bfe4-4a67-8bcc-28ca36adcf4c
f4daa715-d2b6-4896-a165-696fa91eb459
f7227167-6c86-45a6-9f1f-d51b05bcbb89
f88c4640-5235-4071-b15b-66ac96eb5f3f
f9c0659a-a304-4a80-a7d2-4f8a556da092
fdc9bcdc-1034-4fe2-b2c0-e81ea412f6ce
```
