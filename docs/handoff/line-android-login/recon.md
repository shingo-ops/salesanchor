# 端末インポートの現状と検証

親: docs/specs/product-master/README.md
設計: docs/handoff/line-android-login/design.md

- backend/app/routers/tcg_line_import.py:673: PR #3443のAndroid入口。本番反映成功、未認証401を確認。PC関数のAST不変を確認済み。
- backend/app/auth/dependencies.py:453: 既存require_super_admin。新しい端末キーはこの共通認証へ追加しない。
- backend/app/tcg_config.py:1: 固定TCG_SCHEMA。端末認可も同じschemaに束縛する。
- backend/app/services/line_import_devices.py:1: 用途限定のキー管理。
- .github/workflows/verify-meta-subscriptions.yml:25: 既存VPS管理経路。新しいジョブは端末許可/取消しのみ。
- migrations/20260912_160000_line_import_devices.sql:1: public表のadditive DDL。全テナント共用。

Firebase直接ログインは公開設定GETで403/API_KEY_HTTP_REFERRER_BLOCKEDを確認したため撤去。ユーザーは初回端末認可に合意し、さらにフロントエンド後回し・インポート先行を指示した。画面の試作変更は差分から取り除いた。

## 現在地

端末クライアント23単体テスト成功。API境界テストとPostgreSQLのDDL冪等・ライフサイクル・並行認可・失効・登録制限テストを追加。Dockerのない端末ではpytestを走らせずCIで実施する。実PostgreSQL検証はまだ未実施として扱う。
backend make lint-ci結果とCIは更新後に記録する。端末には前便の停止するFirebase試作がまだ入っており、本番反映後にdevice_session版へ更新する。原本・未送信2件は保持、専用端末キーは未登録。実送信は未完了。
