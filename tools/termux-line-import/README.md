# TermuxからAndroidのLINE履歴を送る

実装・検証中。サーバーのAndroid専用APIが導入されるまで送信を有効にしない。
設計: ../../docs/handoff/line-android-import/design.md

ファイルをTermux本体の ~/line-import/lib/ に配置する。Android共有受信スクリプトからclient.py enqueueを呼ぶ。原本の保存が完了してから呼び、失敗時も原本を消さない。

```bash
python ~/line-import/lib/client.py --state-dir ~/line-import/state enqueue /path/to/talk.txt
python ~/line-import/lib/client.py --state-dir ~/line-import/state status
```

API導入確認後、MFA認証済みFirebase IDトークンを端末内で設定する。チャット・GitHubへ貼らない。

```bash
python ~/line-import/lib/client.py --state-dir ~/line-import/state set-token
python ~/line-import/lib/client.py --state-dir ~/line-import/state enable
python ~/line-import/lib/client.py --state-dir ~/line-import/state send
```

set-tokenは暫定の手動設定で、自動ログイン・更新は未実装。期限切れ時に再設定が必要。通常のログイン方法はユーザーへ確認する。
同じファイルは二重登録しない。共有またはsend時に再送する。常駐タイマーはない。acceptedはAPI受付、pending_reviewは既存画面で取引先確認待ち。解析完了を意味しない。確認待ちの後続状態の自動追跡は未実装。
エラー時もoriginalsとSQLiteキューは保持する。rejectedの再送は原因を解消し、状態を確認してから行う。
端末で現在導入済みの共有フックはバックアップ付き。新しいフックのAndroid共有画面からの再試験は必要。

テスト: python -m unittest -v test_android_import.py

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
install -m 600 client.py android_parser.py ~/line-import/lib/
install -m 700 termux-file-editor line-import ~/bin/
```

共有フックは標準のTermuxパッケージcom.termuxのホームを使用する。
