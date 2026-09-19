# recon — 安全装置 #8: 再解析完了チェック

## 背景
2026-09-04: analysis_runs の completed_at IS NULL が残った状態で配信スクリプトを実行した。
手順書への記載だけでは防げないことが実証されたため、コードで強制する。

## 対象ADR
ADR-154（TCG PARITY-02 配信機能）

## 変更対象ファイル（file:line）

### 配信サービス
- `backend/app/services/tcg_distribution_svc.py:600` — `run_distribution()` 関数の先頭にガードを追加
- `backend/app/services/tcg_distribution_svc.py:13` — 安全装置一覧に #8 を追記

### テスト
- `backend/tests/test_tcg_distribution.py:1` — モジュール docstring に #8 テストを追記
- `backend/tests/test_tcg_distribution.py:187` — 安全装置 #8 テスト2件を追加

### ドキュメント
- `DEPLOY_LOG.md:101` — インシデント記録・unit_ng 残存・マスタ育成引き継ぎを追記

## 触らないファイル
- 配信先マスタ（tcg_distribution_targets）: 変更なし
- migration ファイル: 変更なし
- API ルーター: 変更なし
