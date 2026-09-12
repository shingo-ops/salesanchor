# Termuxログインの現状

親: docs/specs/product-master/README.md
設計: docs/handoff/line-android-login/design.md

- tools/termux-line-import/client.py:1: PR #3443ではIDトークン手動設定だけで自動更新なし。
- frontend/src/lib/firebase.ts:18: 既存WebアプリのFirebase公開プロジェクト設定。
- backend/app/auth/dependencies.py:150: MFAチェックを既存APIで実施。
- backend/app/routers/tcg_line_import.py:202: pending読み取りはrequire_super_admin必須。端末ログインで権限を確認するために使い、応答の一覧を読み取り・保存しない。
- PR #3443: merge fcc092fb。デプロイ34673108172成功、Android APIの未認証401確認。
- ユーザーはメールアドレスを把握し、パスワード再設定後にWebログイン成功と回答。実際のパスワードは本作業で利用しない。

## 検証

Python 3.12およびTermux本体Python 3.14.6で30テスト成功（旧16、新規認証14）。非表示入力の失敗時は入力を拒否。合成資格情報だけでテストした。実アカウントの対話ログイン・認証付き送信はユーザー操作待ち。
端末にclient.py/firebase_session.pyを導入し、旧client.pyをbackup-before-loginに保管した。Firebase公開設定のみ設定。未送信キュー2件、送信は無効のまま。

## 実機で判明した接続制限（2026-09-12）

ユーザーの対話ログインはFirebase段階で失敗。資格情報を使わないGET /v1/projectsによる公開設定確認でHTTP 403 / API_KEY_HTTP_REFERRER_BLOCKEDを確認した。パスワードの正否は未判定。既存Web APIキーを使ったTermux直接ログインは現構成では利用できない。
制限を解除したりRefererを偽装したりしない。CLIはパスワード入力前に公開設定の接続可否を確認し、制限を区別して停止する。生のエラー応答・キー・資格情報は表示しない。修正後33テスト成功。
次案: 初回だけ既存Webログインで端末を認可し、以後はTermuxで送信する。当初のフロントエンド不要の合意から端末認可画面が増えるため、ユーザーへ方式変更を確認中。未実装。
