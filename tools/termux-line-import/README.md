# TermuxからAndroid LINE履歴をインポートする

PR #3443のAndroidパーサー・APIは本番反映済み。送信専用の端末認可APIは本PRの導入後に利用する。フロントエンドは後回しというユーザー指示に従い、初回許可は管理者の手動ジョブで実施する。

## 初回の端末登録

このディレクトリのclient.py、android_parser.py、device_session.pyをTermux本体の ~/line-import/lib に、line-import・line-import-check・termux-file-editorを ~/bin に配置する。既存ファイルは置換前にバックアップする。Python以外の追加パッケージは不要。

### 通知に必要なTermux:APIアプリ

受信・結果・詰まりの通知にはtermux-notification・termux-job-schedulerを使う。Termux本体と同じ入手元（F-Droid）からTermux:APIアプリを別途導入する。入手元が異なると署名が合わず組み合わせられない（入手元を変える場合は本体と追加アプリをすべてアンインストールしてから入れ直す）。Termux本体側でも`pkg install termux-api`を実行しておく。Termux:APIアプリが未導入の間はtermux-notificationが応答せず止まった（2026-09-17実機）。導入後に`termux-notification -t テスト -c テスト`で通知が表示されることを確認する。

```bash
~/bin/line-import connect
```

端末内で256ビットのランダムな専用キーを生成する。パスワード入力・コピー貼り付け・Firebase接続はない。サーバーへはキーのSHA256だけを登録。表示される端末コードは10分間有効。管理者がコードを許可するまで待機し、成功後にdevice.jsonを600で保存する。元のキーは新しい認可が成功するまで維持する。

管理者はmainに導入後、GitHubの既存VPS運用資格情報を使う「LINE import device (manual)」を実行する。入力はaction=approve、登録するSales Anchorユーザーのメールアドレス、端末コード。対象が有効なsuper-adminかDBで確認する。キー・パスワード・Firebaseトークンは入力しない。承認はPOの指示がある端末だけに行う。

## 送信

```bash
~/bin/line-import enable
~/bin/line-import send
~/bin/line-import status
```

成功後はLINEの履歴.txtをTermuxへ共有すると原本保存・送信が行われる。新着LINEの自動取得はしない。端末トークンはPOST /api/v1/tcg/line-devices/importと自身の認可状態確認だけに使用し、PC入口や他のAPIでは使えない。送信先は固定HTTPS。未承認、取消し、所有者の無効化・管理者権限喪失、90日間利用がない場合は拒否する。送信成功時に利用期限を90日延長する。
原本、device.json、SQLiteキューを共有・Gitに追加しない。通信失敗時も原本を保持し次回共有またはsendで再試行。同一ファイルは重複登録しない。pending_reviewは既存PC画面で取引先確認待ち、acceptedはAPI受付で解析完了とは区別する。
端末に残す原本は常に最新1件だけ（state/originalsとinboxの両方）。新しいトーク履歴を共有すると、それ以外の未完了ジョブはsuperseded扱いになり、古い原本・受信コピーは自動で削除される。LINEの履歴出力は毎回全履歴を含むため、新しいファイルが常に古いファイルの内容を包含する前提。この前提のため、古いファイルだけを後から再送することはできない（アプリ側の取り込み済みで代替する）。

## 通知と履歴

共有するたびに次の通知が届く（Termux:APIアプリ導入後）。
- 受信時：「LINE取込：受信しました（送信中）」
- 結果（成功）：「LINE取込：取り込み完了」投稿N件
- 結果（確認待ち）：「LINE取込：取り込み完了（確認待ち）」取引先確認待ちN件。PC画面で確認してください
- 結果（失敗）：「LINE取込：失敗」理由（原本は保持。次の点検で自動再送します／再認可が必要です／再送しません、のいずれか）
- 詰まり（定期点検で検知）：「LINE取込：詰まり」受信時刻から何分未完了か・止まっている段階・理由・再送回数

通知はTermux:APIアプリに依存する。アプリが消えると通知だけが出なくなるが、送信・再送自体は続く。

```bash
~/bin/line-import history 20   # 直近の経過（受信・保存・送信・点検・整理）を新しい順に表示
~/bin/line-import status       # 状態別件数に加え、最新ジョブの状態・受信時刻・経過分、詰まり判定時間を表示
```

## 定期点検（詰まり検知・自動再送）

```bash
~/bin/line-import check     # 手動で1回点検（古い履歴の削除→再送時刻を過ぎたジョブの再送→詰まり検知）
~/bin/line-import schedule  # termux-job-schedulerに15分周期の定期点検を登録（再起動後も持続）
```

`check`は他のline-importコマンドと排他制御されており、共有中の処理と重ならない場合のみ実行される（重なる場合は何もせず終了する）。

### 詰まり判定時間の設定

詰まり通知は`stall_seconds`（config.jsonの中の秒数）を設定するまで出ない。`status`に「詰まり判定時間：未設定（計測後に設定）」と表示されている間は未設定。値は実機で本番送信を数回計測し、所要時間の最大＋余裕をPOと合意してから設定する。

```bash
~/bin/line-import set-stall 1800   # 例: 30分。必ず実機計測・PO合意後に設定する
```

Androidの予定実行は最短15分で、省電力状態では遅れることがある。そのため詰まりの検知は判定時間から最大15分以上遅れることがある。

## 原本の整理

```bash
~/bin/line-import cleanup --dry-run   # 最新1件以外に消える対象を一覧表示（削除しない）
~/bin/line-import cleanup             # 一覧を確認した上で実際に削除する
```

通常運用では共有のたびに自動整理されるため、cleanupは端末の初回導入時や、旧バージョンから引き継いだ余分な原本・受信コピーを片付けるときに使う。

## 取消し

同じ管理者ジョブでaction=revoke、承認時のdevice_idと所有ユーザーのメールアドレスを指定。以後の送信を停止する。既に開始したインポートを途中で取り消す機能ではない。所有者以外の取消しは拒否する。

## 検証

```bash
python -m unittest discover -s . -p 'test*.py'
```

従来のFirebase直接login試作は接続元制限で使えないため撤去。loginはconnectの互換エイリアス。端末に残る旧Firebase公開設定は使用しない。端末の実送信は未完了で、サーバー導入・初回登録後に確認する。
