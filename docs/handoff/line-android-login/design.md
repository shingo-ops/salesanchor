# Android LINEインポート専用の端末APIキー

親: docs/specs/product-master/README.md
現状: docs/handoff/line-android-login/recon.md
対象ADR: ADR-072（schema明示）、ADR-154（既存解析の維持）。

## 合意した最終範囲

ユーザーは初回だけ端末を認可し通常はログインなしで送る方式に合意。その後、より手間の少ない方式を求め、フロントエンドは後回し・インポート先行を明示した。従って本PRは送信専用APIキー、管理者側の初回許可、Termux送信に限定。画面変更は含めない。

## 動作と境界

端末が256bit乱数を生成しsali1_接頭辞を付け、ハッシュだけをPOST /tcg/line-devices/startへ登録。短い端末コードを返し10分間待機する。端末は5秒間隔で自身のキーをBearerに付けstatusを確認。公開登録はDBトランザクションロックでsocket peerあたり10件/時、全体30件/時に制限し、Redis不通時にも解除されない。プロキシ配下でpeerが共通なら保守的な共有上限となる。
初回認可は既存VPSのSSH運用経路を使う、main限定・shingo-cc/shingo-ops限定の手動ジョブ。メールと端末コードを構造化JSONで渡し、DB上で対象のactive super-admin・active tenantを確認して許可する。任意SQL/コマンド入力は受け付けない。キー・パスワード・Firebaseトークンは渡さない。Web用のapprove/list/revoke APIは既存require_super_adminで保護するが画面は後続。
端末コードは1回だけ使用可。許可済み端末は1所有者20件まで。キーはLINE Android取り込みと自身の認可状態確認だけに使用でき、既存PC/API/Firebase認証へ混ぜない。既存のAndroid検証・共通取込を呼び、認可したユーザーをuploaded_byに記録する。
所有ユーザーとテナントの有効性、super-admin権限、TCG_SCHEMA、固定scopeを毎回DBで検証。90日無利用で失効し成功した送信で90日延長。管理者ジョブまたは所有者APIから取消し可能。取消しは以後の要求に適用し、処理開始済み要求の巻き戻しは行わない。キー自体の定期ローテーションはなく、有効性と取消しをDBで管理する。

## データと移行

public.line_import_devicesだけをadditiveに新設。キー・端末コードのハッシュ、所有者、固定scope/TCG_SCHEMA、時刻、取消しを保存。平文キーは端末のdevice.json（600）に原子的に保存。SHA256の元となる256bit乱数は辞書攻撃できるパスワードとは異なる。PCの認証・原本・解析ロジックは変更しない。
既存/新規テナントいずれも共通public表を使用するためテナント別DDL不要。run_all_migrations.shに登録し通常deploy.ymlの既存経路で実行。バックアップは通常デプロイ工程で取得。新しい外部secretsは不要。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 未認可・失効・取消し・権限喪失・別schemaを拒否 | test_line_import_devices.py、実PostgreSQL test_line_import_devices_pg.py |
| キーで許可APIやPC APIを呼べない | API認可テスト、既存get_current_userを維持 |
| 同時承認でも端末コードは単回使用 | PostgreSQL並行テスト |
| DDLが冪等で必要列が存在、最小権限DMLで動作 | 一時DBでSQLを2回適用しinformation_schemaを検証 |
| 端末キーがログ・登録本文に出ない、失敗でも旧キー保持 | test_device_session.py |
| 通信失敗・重複・確認待ちを維持 | test_android_import.py |
| 実ファイルのAPI受付 | 本番反映後に端末登録・原本送信。未実施 |

## 外部・過去事例の参照と我々への応用

2026-09-12にFirebase公開設定GETで403/API_KEY_HTTP_REFERRER_BLOCKEDを実測。資格情報の正否とは無関係にCLI直接ログインが使えないため、その試作を撤去。制限解除・Referer偽装・ブラウザー資格情報の吸い出しをしない。
RFC 8628 https://www.rfc-editor.org/rfc/rfc8628.html の端末コード分離・期限・明示承認を参照。本実装は用途限定の独自APIキー登録でありOAuth準拠とは呼ばない。スマートフォン上の通常アプリのOAuthを置き換えるものではない。

## 維持の仕組み

- 守り手: backend/tests/test_line_import_devices.py
- 守り手: backend/tests/test_line_import_devices_pg.py
- 守り手: tools/termux-line-import/test_device_session.py
- 人手で守る: 管理者による初回許可・取消し、実機送信確認。本番反映はPR番号付きGO後。
