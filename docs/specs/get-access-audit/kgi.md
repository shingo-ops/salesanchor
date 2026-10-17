# KGI — get-access-audit

PO 承認: 2026-10-17 の一任（ideal-state.md）に基づき Opus が確定。PO 個別の y は未取得。

| ID | 基準（○×で判定） | 検証方法 | 結果 |
|---|---|---|---|
| K1 | 一覧の全件取得・ファイル出力の GET が成功したら、data_access_events に event_type=data_export の行が 1 行残る（利用者・パス・接続元つき） | CI の T1・T2 が緑（変更前は赤）。本番で行が現れるかは反映後の利用待ちで観測 | ○（CI: 変更前 35 failed→変更後 37 passed、PR #4411 の pytest 合格）。本番の data_export 行は 2026-10-17 01:41 JST 時点で未発生（利用待ち） |
| K2 | 1 人が 10 分に 500 回を超えて閲覧したら、bulk_read_alert の行がちょうど 1 行と警告ログが残る。500 回以下では 0 行 | CI の T3・T4 が緑（変更前は赤） | ○（同上） |
| K3 | 本番で閲覧の回数を実際に数えている | 本番 Redis の `bulk_read:` キーを、アプリ自身の Redis 接続で読む（パスワードは画面に出さない） | ○（2026-10-17 00:05Z、無制限鍵の使用は PO 許可。確認アクセス 1 回で、その email のキーが count=1・TTL 659、他に利用者のキー 1 件: /tmp/CC報告ファイル/s6-get-audit/k3/probe.txt）。当初は「ログの失敗 0 件」で ○ にしていたが、直接の証拠ではなかったため差し替えた。このとき 401 の閲覧も数えていることが分かり、追補1（docs/handoff/s6-get-access-audit/design-fix1.md、PR #4421）で直した。下の F1〜F3 を参照 |
| K4 | 反映後もエラーが増えず、普段の使い方で誤検知が出ない | backend の Traceback・ERROR、nginx の 5xx が反映前の基準から増えない。観測時間内の bulk_read_alert が 0 行 | ○（反映 2026-10-16 16:24Z 後 17 分・nginx 248 行: Traceback・ERROR 0、5xx 0、大量閲覧の警告 0、bulk_read_alert 0。反映前も 0） |

生出力: /tmp/CC報告ファイル/s6-get-audit/k/（before.txt・after1.txt・after2.txt）、merge/（checks・deploy）。

補足（2026-10-17）: 10/15 07:45Z 以降、data_access_events の user_email がすべて NULL だったのは、その間の書込がスクリプト・curl・監視通知など機械からの呼び出しだけだったため。ブラウザからの書込には email が入っている（/tmp/CC報告ファイル/s6-get-audit/email-null/prod-null.txt）。

## 追補1（401・403 の閲覧を数えない、PR #4421）

PO 承認: 2026-10-17 チャットで「y」。2026-10-17 01:10Z にマージし、deploy が成功した（run 38989711935）。

| ID | 基準（○×で判定） | 検証方法 | 結果 |
|---|---|---|---|
| F1 | 401・403 になった閲覧は回数に数えられない | CI の T6。本番では、架空の email を入れた署名なしのトークンで GET を送り、その email の `bulk_read:` キーを数える | ○（CI: 変更前 2 failed→変更後 39 passed。本番: 01:15Z と 01:40Z の 2 回、それぞれ 401 を 3 回送り、キーは 0 件。01:40Z は別 PR の反映で backend が入れ替わった後で、入れ替わり後のコンテナにも修正の行があることを確かめた: fix1-prod/probe.txt・probe2.txt） |
| F2 | ログイン済みの閲覧は今までどおり数えられる | CI の T4。本番では、反映後にブラウザからの 200 の GET が来たら、すぐ `bulk_read:*` を読む | ○（01:38Z にブラウザからの GET 2 件のあと、利用者のキーが 1 件・count=1: fix1-prod/f2-gets.txt・f2-redis.txt） |
| F3 | 反映後にエラーが増えない | backend の Traceback・ERROR、nginx の 5xx、閲覧回数の失敗ログ | ○（01:16Z と 01:40Z の 2 回測り、すべて 0 件: fix1-prod/f3-1.txt・f3-2.txt） |

生出力: /tmp/CC報告ファイル/s6-get-audit/fix1/（試験）、fix1-prod/（本番）。

付記: マージの前に、#4421 の CI が閲覧ページの試験 2 本で落ちた。この 2 本は固定日時で作ったトークンを使っていて、2026-10-16 22:00Z に期限が切れていた。S6 とは無関係なので、別の PR #4425 で直してから通した。
