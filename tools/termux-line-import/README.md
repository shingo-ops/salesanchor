# TermuxからAndroid LINE履歴をインポートする

PR #3443のAndroidパーサー・APIは本番反映済み。送信専用の端末認可APIは本PRの導入後に利用する。フロントエンドは後回しというユーザー指示に従い、初回許可は管理者の手動ジョブで実施する。

## 初回の端末登録

このディレクトリのclient.py、android_parser.py、device_session.pyをTermux本体の ~/line-import/lib に、line-importとtermux-file-editorを ~/bin に配置する。既存ファイルは置換前にバックアップする。Python以外の追加パッケージは不要。

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

## 取消し

同じ管理者ジョブでaction=revoke、承認時のdevice_idと所有ユーザーのメールアドレスを指定。以後の送信を停止する。既に開始したインポートを途中で取り消す機能ではない。所有者以外の取消しは拒否する。

## 検証

```bash
python -m unittest discover -s . -p 'test*.py'
```

従来のFirebase直接login試作は接続元制限で使えないため撤去。loginはconnectの互換エイリアス。端末に残る旧Firebase公開設定は使用しない。端末の実送信は未完了で、サーバー導入・初回登録後に確認する。
