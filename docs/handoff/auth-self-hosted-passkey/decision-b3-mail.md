# 便3 判断メモ — メール送信の設定（SMTP）を1か所で共有するか

> 状態: **設計案（草案）・PO の判断待ち**。PO の承認ではありません。
> 作成: 2026-10-14 Claude Opus（設計）／調査 Sonnet／審査 Fable（§9）
> 関連: ADR-1013、design.md §6 便3（`docs/handoff/auth-self-hosted-passkey/design.md:156`）、ADR-075（本番の秘密は GitHub Secrets のみ）
> 調査の生出力: /tmp/CC報告ファイル/auth-b3/（各ファイルの先頭に実行コマンドと時刻）

## 1. 決めること

便3 では、パスワード再設定と招待のメールを送るために、SMTP の設定を backend に渡します。設定の持ち方を、次の3案から選びます。

- **y1（共有・すべて有効）**: `SMTP_HOST`・`SMTP_PORT`・`SMTP_USER`・`SMTP_PASSWORD`・`MAIL_FROM` を1組だけ持つ。今は設定が無いため送られていない既存の3つの送信（発注書メール API・LP 問い合わせ通知・データ削除の完了通知）も、同じ設定で実際に送られるようになる
- **y2（共有・便3 では再設定メールだけ）**: 設定は1組。ただし既存の3つの送信は、別のスイッチで止めたままにする
- **n（分離）**: ログイン用に、さくらで別のアドレスを作り、別の名前（例: `AUTH_SMTP_*`）で別のパスワードを持つ。既存の3つの送信は送らないまま

## 2. 今の状態（事実・2026-10-14 06:20〜06:58 JST・origin/main 313590428）

| # | 事実 | 根拠 |
|---|---|---|
| F1 | SMTP の設定を読むのは backend の3ファイルだけで、3か所がそれぞれ設定の有無を判定している（判定が重複している）。他に smtplib や `SMTP_` を読む箇所は、backend/app・backend/scripts・scripts に無い | `backend/app/services/email_sender.py:40-46`・`:58-62`、`backend/app/services/po_mailer.py:33-40`・`:76-90`、`backend/app/routers/contact.py:41-47`・`:58-62`。recon-mail-wiring.md、Fable 審査 L4 |
| F2 | 設定が無いとき、3機能とも送らずにログだけ残す（例外にはならない）。判定は `all([...])` で、値が空でも「未設定」になる | `po_mailer.py:79-84`・`email_sender.py:51-56`・`contact.py:51-56` |
| F3 | `docker-compose.yml` と `.github/workflows/deploy.yml` に `SMTP_*`・`MAIL_FROM`・`CONTACT_NOTIFY_EMAIL` は1行も無い | `git grep` 0 件 |
| F4 | 本番の backend は `scripts/blue-green-cutover.sh:92` の `docker run --env-file .env` で起動しており、.env のキー57個がすべてコンテナに入っている。celery-worker は compose の `environment:` で起動しており、32個だけが入っている | /tmp/CC報告ファイル/auth-b3/backend-run-mode.txt・prod-env-names.txt |
| F5 | 本番の .env（2ファイル）、backend（66個）、celery-worker（32個）のどれにも、`SMTP_`・`MAIL_`・`EMAIL_`・`AUTH_` で始まる名前は無い | prod-env-names.txt（名前の数だけ数えた。値は読んでいない） |
| F6 | 監査記録で、発注書メールの「送信」「スキップ」「失敗」は5テナントすべて0件（監査記録そのものは tenant_001 に19行・tenant_004 に7行・tenant_006 に206行ある） | /tmp/CC報告ファイル/auth-b3/po-mail-count.txt |
| F7 | 発注書メールの API（`purchase_orders.py:384`・`:494`）を呼ぶ画面・GAS・スクリプトは、リポジトリ内に無い。旧システム（jarvis-claude.uk）からの呼び出しは **未確認** | /tmp/CC報告ファイル/auth-b3/po-ui-callers.txt |
| F8 | 問い合わせ通知の宛先は環境変数 `CONTACT_NOTIFY_EMAIL`。無ければ固定値 `support@salesanchor.jp`。過去の受信件数は、backend コンテナが 2026-10-14 朝に入れ替わり（06:41 と 06:52 JST の起動を観測）、ログが残っていないため **未確認**。support@ で受信できるかも **未確認** | `backend/app/routers/contact.py:27`・contact-log.txt |
| F9 | salesanchor.jp の MX は `salesanchor.sakura.ne.jp`、SPF は `v=spf1 a:salesanchor.sakura.ne.jp mx ~all`。`_dmarc` は無い（NXDOMAIN）。DKIM はセレクタ `default`・`rs` で調べて無い（さくらのセレクタは鍵を作ったときに決まるので、これ以外は調べていない） | /tmp/CC報告ファイル/auth-b3/dns-now.txt（8.8.8.8 に問い合わせ） |
| F10 | backend コンテナから `salesanchor.sakura.ne.jp:587` に接続できる。STARTTLS が使え、暗号化した後に認証方式（PLAIN・LOGIN 等）が示される。ログインと送信は試していない | /tmp/CC報告ファイル/auth-b3/smtp-starttls.txt・smtp-reach.txt |
| F11 | さくら公式: 送信サーバー名には初期ドメイン（○○.sakura.ne.jp）を入れる。STARTTLS は初期ドメインのみ。DKIM は 2024-01-31 から対応で、SMTP 認証で送ったときに署名される。送信上限は「15分毎に100通程度」（アドレスごとか契約全体かは公式に記載なし）。国外IPアドレスフィルターは SMTP 認証の送信も拒否する | sakura-mail-official.md・sakura-mail-official-2.md |
| F12 | 3つの実装はいずれも `smtp.starttls()` を必ず呼ぶ | `email_sender.py:71`・`contact.py:83`・`po_mailer.py:108` |
| F13 | 削除完了通知は celery-worker で動く。Celery のタスクは、実際には送らなかったときも `"sent"` を返す | `backend/app/tasks/email_tasks.py:46-48`、呼び出し元 `data_deletion.py:234-235` |
| F14 | 発注書メールは Reply-To を付けないので、仕入先が返信すると `MAIL_FROM` 宛てになる | `po_mailer.py:93-98` |
| F15 | メール設定の一元化を決めた ADR は無い。ADR-075 は「本番の秘密は GitHub Secrets のみ」 | recon-mail-wiring.md §5 |

## 3. 外部事例（要約。全文と信頼度は /tmp/CC報告ファイル/auth-b3/external-cases.md）

| 事例 | 5W2H の要点 | 数値 | この案件への当てはまり |
|---|---|---|---|
| 失敗: GitHub のメール遅延（一次情報） | 2024-04-11〜14。共有のジョブ待ち行列が詰まり、メール送信の待ち行列も止まった | 遅延は最大2時間。パスワード再設定 300〜400件、端末認証 800〜1,000件が完了できなかった。発生から公表まで約69時間 | 「認証メールが他の処理と同じ待ち行列を使う」ことの危険。SMTP の設定を共有するかどうかとは別の問題。→ 再設定メールは Celery の待ち行列を使わない（§6-3） |
| 失敗: conda-forge（CircleCI 事件・二次情報） | 2023-01。同じトークンを複数の CI で使い回していたため、入れ替えの途中の失敗が全体に広がった | 約5日間機能が止まった（件数の記載なし） | 構造は違う（複数サービスへの使い回しとボットの失敗）。言えるのは「秘密が増えると、入れ替えのときに更新する場所が増える」ことまで |
| 失敗: CircleCI 2023-01（一次情報） | 預けていた秘密がまとめて漏れた | 攻撃元の IP は8件。被害を報告した顧客は5社未満。利用者は全ての秘密の入れ替えを求められた | 1か所に集めると、そこが破られたとき全部に及ぶ。ただし今回は、どの案でも同じ GitHub Secrets と同じ .env に置くので、この差は生まれない |
| 成功（業者の主張）: Postmark | 認証メールと一斉配信を、別の IP・別の送信元に分けた | 到達率99%・迷惑メール率0.1%未満（業者の自己申告） | さくらでは IP を選べない。n で別のアドレスにしても、送るサーバーと IP は同じ |
| 成功（三次情報）: Google の2024年の送信者要件 | 2024-02 から、全送信者に SPF か DKIM を要求 | Gmail に届く未認証のメールが65%減ったと報じられた（Google の原文は未確認） | 届くかどうかを決めるのは、どの案を選ぶかではなく **DKIM・DMARC を設定するかどうか**（F9: 今は無い） |

見つからなかったもの（数値なし）: 認証メールと業務メールで送信設定を共有したために届かなくなった直接の事例。13人規模で共有 SMTP と専用の送信サービスを比べた実測。

## 4. 比べた結果

| 観点 | y1（共有・すべて有効） | y2（共有・再設定メールだけ） | n（別アドレス・別パスワード） |
|---|---|---|---|
| 秘密の数 | SMTP のパスワード1つ | 1つ | 2つ（別の値なので使い回しではないが、置き場所と入れ替えの手間が2倍） |
| 届きやすさ | 同じさくらのサーバー・同じ IP。DKIM・DMARC があれば同じ条件 | 同じ | 同じ（送信元のアドレスは別になる） |
| 送信上限（15分に約100通） | 上限がアドレスごとか契約全体かは不明（F11）。既存の発注書メールは0件（F6） | 同じ | アドレスごとなら分けられる。契約全体なら同じ |
| 利用者に見える変化 | 画面からは発注書メールを送れないので変化なし（F7）。LP の問い合わせ通知が届き始める。データ削除の完了通知が本人に届き始める | 変化なし | 変化なし |
| 作るもの | 設定の判定を1か所にまとめ、4つの送信で使う | y1 に加えて、既存の3つを止めておくスイッチ（設定が1つ増える） | 判定が4か所に増えるか、2組の設定を扱う仕組みが要る |
| 追加の確認 | support@salesanchor.jp が受信できるか（F8） | 無し | さくらで2つ目のアドレスと DKIM |

**推奨: y1**。
- n にしても、送るサーバーも IP も変わらないので、届きやすさは上がりません（§3）。秘密と入れ替えの手間が2倍になるだけです。
- y2 は、止めておくスイッチが増えるうえ、「設定は入っているのに送られない」という分かりにくい状態を残します。
- y1 で利用者から見て新しく起きるのは、問い合わせ通知と削除完了通知が届き始めることだけです。発注書メールは画面から送れません（F7）。
- 「データを分散させない」という PO の方針（ADR-1013:34・design.md:174）は、ログイン情報について決めたものです。SMTP の秘密にも同じ考えを当てはめるのは、私の類推です。

## 5. y1 にした場合の便3 の範囲（カードを書くときの土台・草案）

1. **設定の判定を1か所にまとめる**: 新しく `backend/app/services/mail_config.py` を作る。`smtp_settings()` が `SMTP_*`・`MAIL_FROM` を読み、そろっていなければ None を返す。`email_sender.py`・`po_mailer.py`・`contact.py` の判定をこれに置き換える。動きは今と同じ（未設定ならログだけ）
2. **設定の渡し口**:
   - backend: `deploy.yml` が作る .env に足せば渡る（F4・blue-green は .env の全行を渡す）。.env の作り直しは、今の形（`deploy.yml:258-283` で削除し、`:291-316` で追記）に `SMTP_HOST`・`SMTP_PORT`・`SMTP_USER`・`SMTP_PASSWORD`・`MAIL_FROM`・`CONTACT_NOTIFY_EMAIL` を足す
   - celery-worker: compose の `environment:` で渡すので、`docker-compose.yml` の celery-worker に同じ名前を足す。ロールバック経路（`deploy.yml:659-662`。compose で backend を起動する）のために、backend の `environment:` にも足す
   - 値は GitHub Secrets に入れる（ADR-075）
3. **再設定・招待メール**: design.md §3 の `password-reset/request` と `register` が、1 の設定を使って送る。送信は FastAPI の BackgroundTasks で行い、Celery の待ち行列は使わない（GitHub の事例の対策）。便3 の間は `AUTH_PASSWORD_RESET_ALLOWLIST` に載ったアドレスにだけ送る（design.md のとおり）。戻すときは 1 の None 判定で止まる
4. **PO の作業（GUI）**:
   - さくらのコントロールパネルで送信用アドレスを用意し、DKIM の鍵を作る
   - DNS（ns1.dns.ne.jp）に、DKIM の TXT と `_dmarc` の TXT を足す（`p=none` から始める。さくらの案内どおり）
   - 国外IPアドレスフィルターが送信を止めないことを確かめる（本番サーバーは日本国内の IP。送信を試す時に確認する）
   - GitHub Secrets に値を登録する。`SMTP_HOST` は初期ドメイン `salesanchor.sakura.ne.jp`（STARTTLS は初期ドメインのみのため・F11・F12）、`SMTP_PORT` は 587、`MAIL_FROM` は用意したアドレス
5. **反映の順番**:
   - ① コードのまとめ直しと渡し口を先に反映する。この時点では設定が空なので、何も送られない
   - ② PO が DNS と Secrets を登録する
   - ③ deploy で設定が入る
   - ④ 試験用アドレスで K5 を確認する
6. **便3 のカードで決めること**:
   - 問い合わせ通知の宛先（`CONTACT_NOTIFY_EMAIL`。support@ が受信できなければ別のアドレスを指定する）
   - 発注書メールの Reply-To（F14）

## 6. リスクと対処

| リスク | 対処 | 測り方 |
|---|---|---|
| DKIM・DMARC が無いまま送ると迷惑メールに入る（F9） | ④ の確認は DNS 登録の後に行う。K5（SPF・DKIM・DMARC がすべて pass）を満たさなければ便4 に進まない | 受信したメールのヘッダ |
| 問い合わせ通知の宛先が受信できないアドレスになっている | カードの前提確認に入れる。受信できなければ `CONTACT_NOTIFY_EMAIL` で指定する | 試験の問い合わせを1件送る |
| 他の処理が詰まって、再設定メールが止まる（GitHub 型） | 再設定メールは Celery を使わない | — |
| 送信上限に達する | 13人規模・発注書メール0件（F6）。上限の単位は不明なので、K5 の試験時に送った数を記録しておく | — |
| SMTP のパスワードが漏れる | 置き場所は GitHub Secrets と本番 .env の1組だけ。入れ替えも1か所で済む | — |

## 7. 戻し方

- GitHub Secrets から SMTP の値を消して deploy する。deploy.yml は、Secret が無いときも `KEY=`（空の値）の行を .env に書く（`deploy.yml:287-290`）。値が空なら `all([...])` が偽になり、3機能はログだけの状態に戻る（F2）。再設定メールも 1 の None 判定で止まる
- deploy は main への push で走る（`deploy.yml:3-5`）。Secrets を消しただけでは反映されないので、消した後に deploy を走らせる（手動実行の口があるかは便3 カードで確かめる）
- コードのまとめ直しは revert で戻せる

## 8. PO に聞く前に埋めた未確認（Fable 審査の後）

| 項目 | 結果 |
|---|---|
| 発注書メールの監査記録の件数 | 5テナントとも0件（生出力あり・F6） |
| 発注書メール API を呼ぶ画面 | リポジトリ内には無い（F7）。旧システムは未確認 |
| 本番 backend の起動方法 | blue-green（`docker run --env-file`）。.env の57キーがすべて入っている（F4） |
| さくらの送信上限の単位 | 公式に記載なし（未確認のまま。§6 で扱う） |
| SMTP_HOST に使う名前 | 初期ドメイン `salesanchor.sakura.ne.jp`。STARTTLS が使えることを実測した（F10・F11） |
| support@salesanchor.jp で受信できるか | 未確認。y1 でも、便3 カードの前提確認で埋める（§5-6） |

## 9. 審査（Fable）

- 1回目（2026-10-14）: **REVISE**。CRITICAL 1件・HIGH 3件・MEDIUM 6件・LOW 4件。全文は /tmp/CC報告ファイル/auth-b3/fable-review-decision.md
- 直したこと:
  - C1: 件数をテナント別の生出力で取り直した
  - H1: 「送信ボタン」という書き方をやめ、「API はあるが呼ぶ画面が無い」に改めた
  - H2: 案を3つ（y1・y2・n）に分けた
  - H3: backend の渡し方（blue-green）と、celery-worker・ロールバックの渡し方を分けて書いた
  - M1〜M6・L1〜L2: 反映した
- 2回目（2026-10-14）: **APPROVE**。残りの LOW 3件（§7 の deploy の起動条件・F8 の時刻・行番号）はこの版で反映済み。全文は /tmp/CC報告ファイル/auth-b3/fable-review-decision-2.md
