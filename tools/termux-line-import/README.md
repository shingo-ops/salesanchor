# TermuxからAndroidのLINE履歴を送る

現在の直接loginは本番の接続元制限（API_KEY_HTTP_REFERRER_BLOCKED）で利用できない。パスワードを再入力しない。端末認可方式の設計確認中。サーバーの履歴APIは導入済みだが、端末からの認証付き送信は未完了。

Android専用APIはPR #3443で本番反映済み。端末のloginで権限を確認してから送信を有効にする。
設計: ../../docs/handoff/line-android-import/design.md

ファイルをTermux本体の ~/line-import/lib/ に配置する。Android共有受信スクリプトからclient.py enqueueを呼ぶ。原本の保存が完了してから呼び、失敗時も原本を消さない。

```bash
python ~/line-import/lib/client.py --state-dir ~/line-import/state enqueue /path/to/talk.txt
python ~/line-import/lib/client.py --state-dir ~/line-import/state status
```

端末のFirebase公開設定（state/firebase.json: api_keyとproject_id）が必要。このGalaxyには本番Webアプリの公開設定を設定済み。他端末では管理者が同じプロジェクトのWeb APIキーを設定する。APIキーはパスワードではなくFirebaseプロジェクトを指定する公開情報。別プロジェクトや未確認の送信先に変更しない。

Termux本体の新しいセッションで:

```bash
~/bin/line-import login
```

メールアドレス・パスワードを対話入力する。パスワードと認証コードは画面に表示せず保存しない。認証アプリのMFA（TOTP）に対応。SMS・reCAPTCHA要求には未対応で停止する。認証応答をSales Anchorの既存読み取りAPIで確認した後、更新トークンを含むsession.jsonを端末内600で原子的に保存する。これは機密ファイルなので共有・Gitへの追加は禁止。Webブラウザーのセッションやチャットのパスワードは利用しない。

loginはトークを送信しない。ログイン成功後に:

```bash
~/bin/line-import enable
~/bin/line-import send
~/bin/line-import status
```

送信時に有効期限が近いトークンをFirebaseで更新する。通信失敗・失効・権限不足では送信を止め原本とキューを保持する。更新できない場合はloginを再実行する。従来のset-tokenは互換用で自動更新なし。session.jsonがある場合はloginを使う。
同じファイルは二重登録しない。共有またはsend時に再送する。常駐タイマーはない。acceptedはAPI受付、pending_reviewは既存画面で取引先確認待ち。解析完了を意味しない。確認待ちの後続状態の自動追跡は未実装。
エラー時もoriginalsとSQLiteキューは保持する。rejectedの再送は原因を解消し、状態を確認してから行う。
端末で現在導入済みの共有フックはバックアップ付き。新しいフックのAndroid共有画面からの再試験は必要。

テスト: python -m unittest discover -s . -p 'test*.py'

## 共有フックの導入

このディレクトリを端末に取得した後、Termux本体で実行する（Ubuntu内では実行しない）。既存フックのバックアップが存在する場合は上書きせず停止する。

```bash
mkdir -p ~/bin ~/line-import/lib
if [ -e ~/bin/termux-file-editor ]; then
  if [ -e ~/bin/termux-file-editor.before-android-import ]; then
    echo '既存バックアップを確認してから導入してください'; exit 1
  fi
  cp ~/bin/termux-file-editor ~/bin/termux-file-editor.before-android-import
fi
install -m 600 client.py android_parser.py firebase_session.py ~/line-import/lib/
install -m 700 termux-file-editor line-import ~/bin/
```

共有フックは標準のTermuxパッケージcom.termuxのホームを使用する。
