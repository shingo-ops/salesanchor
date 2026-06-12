# design.md — smoke [7] ヘルスチェック偽陽性修正

**対応ADR**: ADR-115（デプロイ安全策）  
**対応recon**: `docs/handoff/smoke-health-retry/recon.md`

## 外部・過去事例の参照と我々への応用

- 該当なし：blue-green cutover 後の一時的接続断は既知パターン（ADR-115 で認識済み）。
  リトライ上限3回・間隔5秒は "本物の障害は複数回連続で失敗する" という一般原則に基づく。
  外部事例の新規参照は不要と判断。

## ゴール

blue-green cutover 直後の一時的な `RemoteDisconnected` を吸収し、
本物の障害検知能力を損なわずに偽陽性 FAIL を解消する。

## 修正方針

`scripts/smoke_test_post_deploy.sh:97-99` の1回実行を、最大3回・5秒間隔のリトライに置き換える。

- リトライ3回: 一時的な接続断（1〜2回失敗）は吸収、本物のダウン（3回全失敗）は検知
- 間隔5秒: blue-green 後の安定待ちとして十分、テスト全体の遅延は最大+10秒
- FAIL メッセージに `after 3 attempts` を追記して偽陽性と本物の違いを明示

## 受け入れ条件

| 基準 | 検証方法 |
|------|---------|
| 次回 develop→main デプロイで smoke [7] が緑で終わる | deploy workflow の conclusion=success 確認 |
| 本物のダウン時は引き続き FAIL になる | 3回全失敗時の `exit 1` パスがコードに存在すること（コードレビュー） |
| 偽陽性リトライ時はログに `attempt N/3 failed` が出る | deploy ログで確認可能 |
