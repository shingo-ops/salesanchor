# KGI(○×で測る・数値化)

この文書は何か(専門用語なしの1行): このテーマの合格条件を、○×で判定できる数字にした一覧。

親: [README.md](./README.md)

正本は [design.md §1・§4](../../handoff/mac-jobs-watch/design.md)。食い違えば design.md を直してから本表を合わせる。

| # | 合格条件 | 測り方 | 合格ライン | 結果 |
|---|---|---|---|---|
| K1 | 自動試験がすべて通る | `bash scripts/tests/test-mac-jobs-watch.sh` | FAIL 0 | ○ PASS=147 FAIL=0（2026-10-15、/tmp/CC報告ファイル/ac-heavy/mac-jobs-watch/impl2/test-opus.txt） |
| K2 | 見張り役が 30 分ごと・ログイン時に動くよう登録されている | `plutil -lint`、`StartInterval`・`RunAtLoad` の値 | OK・1800・true | ○ plutil OK・run interval 1800（2026-10-15、/tmp/CC報告ファイル/ac-heavy/mac-jobs-watch/deploy/opus-print.txt） |
| K3 | Mac に設置され、設置直後に「点検結果」が Discord に届く | `launchctl print gui/$(id -u)/jp.salesanchor.mac-jobs-watch` と ~/Library/Logs/mac-jobs-watch.log | print の終了コード 0、ログに `result=boot-notice send=ok` | ○ print 終了0・runs=1・last exit code=0、2026-10-15T15:20:11 `result=boot-notice send=ok`（/tmp/CC報告ファイル/ac-heavy/mac-jobs-watch/deploy/k3-6-*.txt） |
| K4 | 異常があれば知らせ、直れば「復旧」を知らせる | 一時フォルダに試験用の入力と状態を置き（本物の状態・ログには触れない）、「停止に失敗」の行と「存在しない常駐」を入れて1回、常駐を本物だけに戻して1回、本物の通知先で動かす（手順の正本 design.md §4 K4） | 1回目 `result=alert send=ok`（2件が1通）、2回目 `result=recover send=ok` | ○ 15:20:43 `result=alert send=ok problems=unloaded:jp.salesanchor.mjw-test-absent events=colima-stopfail`、15:20:46 `result=recover send=ok`（/tmp/CC報告ファイル/ac-heavy/mac-jobs-watch/deploy/k4-mjw.log.txt） |
| K5 | 通知先の URL がログ・画面に出ない | 見張りのログ3つ（.log/.out/.err）と K4 の試験ログを、`discord.com/api/webhooks` と通知先ファイルの中身（件数だけ出す `grep -c -F -f`）で検索 | すべて 0 行 | ○ 4ファイルとも 0・0（/tmp/CC報告ファイル/ac-heavy/mac-jobs-watch/deploy/k5-counts.txt） |
| K6 | Mac を再起動した後も、3 つの見張り・お手入れが自動で再開する | 次に PO が Mac を再起動した後、Discord の「起動後の点検」通知とログ | 起動時刻が 2026-10-09 18:02 より新しい `result=boot-notice send=ok` の行があり、3 つとも「読み込み済み」 | 観測待ち（再起動は PO の操作。AI からは行わない） |

実機スマホの点検（正本は [design-phone.md §1](../../handoff/mac-jobs-watch/design-phone.md)）:

| # | 合格条件 | 測り方 | 合格ライン | 結果 |
|---|---|---|---|---|
| P1 | AI の道具が番号を決め打ちせずスマホを見つける | `bash scripts/dev/phone-serial.sh` | 終了 0・1 行・`._adb-tls-connect._tcp` で終わる | ○ 2026-11-02 本物の Mac で終了 0・`adb-RFGL61DLQCW-IwMTz9._adb-tls-connect._tcp` の 1 行 |
| P2 | 1 時間以上見えなければ 1 通、見えたら「直りました」1 通 | 試験 P㉞〜P㊸ と本物の通知先での手動試験 | FAIL 0・`result=alert send=ok problems=phone-missing`・`result=recover send=ok` | ○ 2026-11-02 試験 FAIL 0。合流後の手動試験（一時フォルダ・本物の通知先）で 0 分・30 分は送らず、60 分で `result=alert send=ok problems=phone-missing`、戻って `result=recover send=ok` |
| P3 | つながりを切る・入れ直す命令を使わない | 差分の中の kill-server・disconnect・connect・tcpip・usb・reconnect | 0 件 | ○ 2026-11-02 審査役の検索で 0 件 |
| P4 | スマホ再起動後、PO が何もしなくても戻る | 再起動 10 分後に P1 | 終了 0・1 行 | 未測定（「常に許可」の印を PO が確かめた後） |

見張りの間隔は 30 分のまま（plist は変えていない）。知らせが届くのは見えなくなってから 60〜90 分後。
| P5 | 既存の試験が今まで通り通る | `bash scripts/tests/test-mac-jobs-watch.sh` | FAIL 0 | ○ 2026-11-02 macOS で `PASS=210 FAIL=0` |

KPI: 合格した KGI の数 5/6（K6 は PO の次の再起動後に観測）。
