# 設計: 実機スマホを再起動したあと、番号を聞かずにつなぎ直す

- 状態: PO 承認 2026-11-02「1」（AI の選択肢「1. スイッチを入れるのだけ PO にお願いし、番号は道具が Mac の仕組みから読んで自動でつなぐ。『つなぎ直す命令は使わない』の決まりを変える」に対して）
- 元の設計: docs/handoff/mac-jobs-watch/design-phone.md（§3-1 の「見るだけ」を、この文書の範囲だけ変える）
- 調べた事実: docs/handoff/mac-jobs-watch/recon-reconnect.md
- 対象 ADR: ADR-1009（見張りの知らせ先。変えない）

## 1. 目的と合格条件

PO にとって変わること: スマホを再起動したあと、PO の操作は「ワイヤレスデバッグのスイッチを入れる」1 回だけになる。画面の番号を AI に伝えなくてよい。

| # | 基準 | 検証方法 | 合格ライン |
|---|---|---|---|
| R1 | adb の一覧にスマホが無く、Mac の仕組み（dns-sd）にはスマホが見えるとき、`scripts/dev/phone-serial.sh` がつなぎ直して名前を出す | 試験（偽の adb・偽の dns-sd）と、本物の Mac で 1 回 | 終了 0・`IP:番号` を 1 行。本物では PO から番号を聞かない |
| R2 | 別の Android の合図（name= が違う）にはつながない | 試験 | 偽の adb に connect が届かない |
| R3 | dns-sd でも見えないとき、今まで通り終了 1 | 試験 | 終了 1・connect を呼ばない |
| R4 | 切る・止める命令を増やさない | 差分の検索 | `kill-server` `disconnect` `tcpip` `usb` `reconnect` が台本に 0 件。増えた命令は `adb connect` だけ |
| R5 | 1 回の呼び出しにかかる時間に上限がある | 試験（偽の dns-sd が止まらない場合） | 15 秒以内に終わる |
| R6 | 既存の試験を壊さない | `bash scripts/tests/test-mac-jobs-watch.sh` | `FAIL=0`。PASS は 210 より増える |

## 2. 対象と対象外

- 対象: `scripts/dev/phone-serial.sh`、`scripts/tests/test-mac-jobs-watch.sh`、この設計と調べた事実、`docs/specs/mac-jobs-watch/kgi.md`（P4 の結果と R1〜R6）、作業の札
- 対象外: `scripts/mac-jobs-watch.sh`（呼び方は変えない。見張りが 30 分ごとに道具を呼ぶので、つなぎ直しも 30 分ごとに起きる）、見張りの間隔、plist、通知の文面、adb の待ち受け役の止め直し

## 3. 変更の中身（scripts/dev/phone-serial.sh）

今の 15〜16 行目（一覧から探す → 無ければ終了 1）の「無ければ」の所に、次の手順を足す。一覧で見つかったときの動きは変えない。

1. `PHONE_RECONNECT` が `0` なら、今まで通り終了 1（つなぎ直しを止めるスイッチ。既定は 1）
2. `PHONE_DNSSD`（既定 `dns-sd`）が無ければ終了 1
3. `"$PHONE_DNSSD" -B _adb-tls-connect._tcp local.` を最大 3 秒だけ動かし、出てきた実例名（行の最後の欄）を集める
4. 実例名ごとに `"$PHONE_DNSSD" -L <実例名> _adb-tls-connect._tcp local.` を最大 3 秒動かす。出力に `name=${PHONE_NAME}`（既定 `SC-51G`）がある実例だけを使う。`can be reached at <ホスト>:<番号>` から ホストと番号を取る（ホストの最後の `.` は外す）
5. `"$PHONE_DNSSD" -G v4 <ホスト>` を最大 3 秒動かし、最初の IPv4 の値を取る
6. `"$adb_cmd" connect <IP>:<番号>` を 1 回だけ呼ぶ（出力は捨てる）
7. もう一度 15 行目と同じ探し方をし、見つかれば今までと同じ選び方で 1 行出して終了 0。見つからなければ終了 1

時間の上限: dns-sd は自分では終わらないので、背景で起動し、決まった秒数のあと止める（macOS に `timeout` 命令が無いため）。止めるのは自分が起動した dns-sd だけ。3〜5 の合計は最大 3+3+3 秒（name= が一致した最初の 1 件で打ち切る）。

先頭の説明の行（「見るだけ。つながりを切る・入れ直す命令は使わない」）は、「切る命令は使わない。一覧に無く、Mac の仕組みで見えるときだけ `adb connect` を 1 回呼ぶ（design-reconnect.md）」に書き換える。設定の行に `PHONE_RECONNECT`・`PHONE_NAME`・`PHONE_DNSSD` を足す。

## 4. 試験（scripts/tests/test-mac-jobs-watch.sh）

- 既存の試験のうち adb の一覧が空になるもの（P㊱ など見張りが 1 時間で知らせる試験）が、本物の dns-sd で本物のスマホを見つけないように、試験の共通の準備で `PHONE_DNSSD` を偽物（何も出さない）にする
- 足す試験: R1（偽の dns-sd が SC-51G の合図を出す → 偽の adb の connect のあと一覧に出る → 終了 0・IP:番号）、R2（name=Pixel だけ → connect 0 回・終了 1）、R3（何も出さない → 終了 1）、R5（偽の dns-sd が止まらない → 15 秒以内に終了）、`PHONE_RECONNECT=0` で connect 0 回

## 5. 代替案

- adb の待ち受け役を止めて起こし直し、adb 自身の合図探しを直す: 直るかが分からず、ほかの作業のつながりが切れる。採らない
- 見張りの台本の側でつなぎ直す: AI の道具が呼んだときにはつながらない。採らない
- 再起動のあともスイッチが入ったままにする: Android の設定で変えられる方法をまだ確かめていない。今回は扱わない

## 外部・過去事例の参照と我々への応用

- 出典: Android 公式「Android Debug Bridge」（developer.android.com/tools/adb、2026-11-02 参照）。「常に許可」の印を付けたネットワークでは、つながったときに無線のデバッグを許す、とある。印は付いていた（スマホの記録に家の Wi-Fi が 2 件）が、再起動でスイッチは切れた（PO の目視）。適用限界: 公式は再起動後のスイッチの扱いを書いていない
- 数値の事例は使わない（この変更の正しさは試験と本物の 1 回で確かめる）

## 6. 危険と対処・戻し方・維持

- 危険: 同じ家の別の Android につなぐ → name= の一致でしか connect しない（R2）
- 危険: 呼び出しが長くなる → 上限 15 秒（R5）。見張りは 30 分ごとなので影響は無い
- 戻し方: `PHONE_RECONNECT=0` で今まで通り。または本 PR を戻す
- 測り方: 本物の Mac で、スマホを一覧から外した状態（再起動のあとスイッチを入れた直後）に道具を 1 回呼ぶ

## 維持の仕組み

- 守り手: 試験 `scripts/tests/test-mac-jobs-watch.sh`（R1〜R5 を足す）。CI の既存の台本の試験で毎回動く

## 7. 設計審査（同じ AI による自己審査。独立した第二者審査ではない）

- 判定: APPROVE
- 根拠: 調べた事実（docs/handoff/mac-jobs-watch/recon-reconnect.md）の 3 つの観測（dns-sd -B で見える・-L で `Android.local.:33815` と `name=SC-51G`・-G v4 で `192.168.10.106`）と、`adb connect 192.168.10.106:33815` で `connected` になった観測がそろっている。変える場所は 1 ファイルの「無ければ」の枝だけで、見つかったときの動きは変わらない
- 未解決: 再起動のあともスイッチが入ったままにできるか（扱わない）
