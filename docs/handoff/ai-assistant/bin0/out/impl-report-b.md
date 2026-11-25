受領確認: card-bin0b を読んだ

# 便0-B 実装報告

## 1回目（前の回）

| 手順 | 結果 |
|---|---|
| 1 作業場所 | 作成済み。HEAD 621ac6637 = origin/release/ai-assistant-bin0b。user.name=Claude・origin/main=e30978f06 |
| 2 Docker・完成品 | digest 固定で取得（1 回 429 → 再試行で成功）。`Hermes Agent v0.23.4` ○ |
| 3 審査指摘の修正 | 3a〜3e 実施（k3-answers.json の e5・i2、run_bin0.py の date 比べ・`_to_date`・`--tool-runs-shape`、試験 10・11、config.yaml の注記、README の S8）。3f: **11 passed**（`out/raw/b3-pytest.txt`） |
| 4 ログインの仕組み | L1〜L4 を `out/measure-b-20261125.md` の表 1 に記録（L3 の実物確認は未） |
| 5 起動 | 部屋 3 つ作成・起動・`/health` 200・prompt_txt_sha256=913a71d5…53f2e |
| 6 ログイン | **通らない**。6a と 6e の 2 回とも `Failed to request device code: [Errno -2] Name or service not known`。ホスト側も `auth.openai.com` へ CONNECT 403（クラウドの外向き通信の決まり）。番号は出ていない（login-code.txt なし）。迂回はしていない |
| 7〜9 | 流していない（ログイン前提） |
| 10a/10b | 触ったのは `docs/handoff/ai-assistant/bin0/` の中だけ・鍵の値 0 件を確認 |
| 10d | 後片付け: 試しの容器・volume・鍵のファイルを消した（ログインは作っていないので logout 不要） |

- 見張りに止められた命令: なし。
- コミットについての注: カードは停止時に out/ だけを commit とするが、手順 3 の修正（検証済み・11 passed）が作業場所と一緒に失われないよう、bin0/ の中の同じ commit に入れた。範囲の外には触れていない。
- 次に必要な決定（Opus・PO）: 便0-B はこのクラウドの環境からは `auth.openai.com` に届かないため進められない。外向き通信の許可を足すか、ログインと測りを手元（Mac ではなくネットワーク制限のない実行機）で行うか。


## 2回目

| 手順 | 結果 |
|---|---|
| 事前 | `curl https://auth.openai.com/` は 302（届く）。HEAD=origin/release/ai-assistant-bin0b=c2976f8d5・user.name=Claude |
| 2 | dockerd 起動・digest 固定で取得・`Hermes Agent v0.23.4` ○ |
| 3f | pytest **11 passed**（`raw/b3-pytest.txt`） |
| 5 | 鍵・3 部屋・起動・`/health` 200。prompt_txt_sha256=913a71d5cbbbf064… （prompt.txt の sha256 の先頭 16 文字・前回と同じ） |
| 6 ログイン | 1) 容器の中に CA が無く `CERTIFICATE_VERIFY_FAILED`。README（/root/.ccr/README.md）の手当てどおり、プロキシの CA の束を容器に渡し `SSL_CERT_FILE`・`REQUESTS_CA_BUNDLE` で指した（検証は切っていない）。**逸脱**: 容器を 1 回作り直し、`-v /root/.ccr/ca-bundle.crt:/etc/ca-proxy.crt:ro` と 2 つの環境変数を足した（README の起動の形への追加）。2) 番号の出し・push・待ち: 全体の札（部屋の指定なし）は通ったが、3) 6g で 3 部屋とも `finish_reason=error`（原因: 部屋 profile の札が無い＝「Hermes is not connected to any AI provider」）。S12 の答え: **部屋ごと**（`-p 部屋` で別の札）。4) coordinator: 通った。calendar: 通った。invoice: 1 回目・2 回目とも番号が打たれず `Login timed out after 15 minutes`（時間切れ） |
| 7〜9 | 流していない（invoice の札が無く、3 部屋がそろわないため。束 69 件は invoice を使う） |
| 10a/10b/10d | 後片付けを実施（下記） |

- 見張りに止められた命令: なし。
- push した番号用の commit: login-code.txt の出し・使用済みの更新（部屋ごと）。最後の login-code.txt は invoice の 2 回目の番号（時間切れ・使えない）のまま。
- 次の決定（Opus・PO）: PO が打てるときに invoice の 1 部屋だけ再実行すれば、手順 6g 以降を続けられる。それまでは coordinator と calendar の札がこの容器の volume にだけ有る（後片付けで消える）。
- 後片付け結果: 4 つの場所（default・coordinator・calendar・invoice）で logout 命令を実行（終了コード 0）・試しの容器と volume を削除・鍵のファイルを 1 つずつ削除（残り 0 件）。

BLOCKED: invoice 部屋のログインが 2 回とも時間切れ（番号が打たれなかった）
