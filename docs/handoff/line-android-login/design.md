# Termux内のメール・パスワードログイン

親: docs/specs/product-master/README.md
現状: docs/handoff/line-android-login/recon.md
対象ADR: ADR-154。Android履歴を既存解析へ渡すPR #3443の端末側認証を補完し、サーバー認証や解析は変更しない。

## 動作

line-import loginをTermux本体で実行。TTYでメールアドレスと非表示パスワードを入力し、Firebase signInWithPasswordへHTTPS送信。パスワードは永続保存しない。TOTP要求時は6桁コードを端末内で入力しmfaSignIn:finalizeへ渡す。SMS等の未対応方式は停止する。
既存のSales Anchor pending読み取りAPIで認証と管理者権限を確認する。APIの一覧本文は読み取り・保存しない。loginはトーク送信もenableも行わない。
IDトークンとrefresh tokenはsession.jsonへ600で原子的に保存。送信時に期限残り120秒以下ならSecure Token APIで更新。失敗時は旧セッションと原本・キューを保持する。セッションがない場合のみ従来token.txtと互換。リダイレクトは拒否、認証先はコードで固定。共有パスワード、ブラウザーの認証ストア、サービスアカウントは使わない。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| パスワード・メール・MFAコードをセッションに保存しない | test_firebase_session.py |
| 期限前キャッシュ再利用と期限直前更新 | 同テスト |
| 認証失敗時はセッションと原本・キューを保持 | 同テスト |
| 非TTYと非表示不可の場合に入力拒否 | 同テスト |
| 既存送信の成功・失敗・重複処理を維持 | test_android_import.py |
| 実アカウントで認証し専用APIへ送信 | 端末で人手検証。未実施 |

## 外部・過去事例の参照と我々への応用

Firebase公式REST仕様: https://firebase.google.com/docs/reference/rest/auth （メール・パスワード認証、更新トークン交換）。Identity Platform MFA仕様: https://docs.cloud.google.com/identity-platform/docs/reference/rest/v2/accounts.mfaSignIn/finalize （TOTP検証）。2026-09-12確認。外部の導入成功件数は未調査で成功実績を主張しない。ローカル30テスト成功は本番認証成功を意味しない。

## 制約

SMS MFA・reCAPTCHAには未対応。Web APIキーにHTTPリファラー制限等がある場合はCLI認証が拒否されうる。制限やMFAを解除して回避しない。APIキーは端末のfirebase.jsonで設定済みだが、他端末には管理者が設定する必要がある。更新トークンは機密情報であり端末のプライベート領域に保持する。

## 維持の仕組み

- 守り手: tools/termux-line-import/test_firebase_session.py
- 守り手: tools/termux-line-import/test_android_import.py
- 人手で守る: 端末内のログイン入力、MFA、Sales Anchor権限、実送信確認。

## 実機で判明した接続制限（2026-09-12）

ユーザーの対話ログインはFirebase段階で失敗。資格情報を使わないGET /v1/projectsによる公開設定確認でHTTP 403 / API_KEY_HTTP_REFERRER_BLOCKEDを確認した。パスワードの正否は未判定。既存Web APIキーを使ったTermux直接ログインは現構成では利用できない。
制限を解除したりRefererを偽装したりしない。CLIはパスワード入力前に公開設定の接続可否を確認し、制限を区別して停止する。生のエラー応答・キー・資格情報は表示しない。修正後33テスト成功。
次案: 初回だけ既存Webログインで端末を認可し、以後はTermuxで送信する。当初のフロントエンド不要の合意から端末認可画面が増えるため、ユーザーへ方式変更を確認中。未実装。
