# design — 安全装置 #8: 再解析完了チェック

## 対象ADR
ADR-154（TCG PARITY-02 配信機能）

## 参照
- recon: docs/handoff/dist-deploy-guard/recon.md
- 根拠インシデント: DEPLOY_LOG.md §「インシデント記録: 再解析完了前に配信を実行（2026-09-04）」

## 変更内容

`run_distribution()` の先頭（設定ロードより前）に以下のガードを追加:

```python
pending_rows = (await db.execute(
    text("SELECT id, started_at FROM tenant_004.analysis_runs"
         " WHERE completed_at IS NULL ORDER BY started_at LIMIT 10")
)).mappings().all()
if pending_rows:
    details = [{"run_id": str(r["id"]), "started_at": r["started_at"].isoformat()} ...]
    return {"errors": [{"error": f"安全装置 #8: 再解析未完了 ... {details}"}], ...}
```

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| pending runs が 0 件のとき配信ロジックへ進む | `test_run_distribution_proceeds_when_no_pending_runs` PASS |
| pending runs が 1 件以上のとき配信中止・run_id/started_at をエラーに含む | `test_run_distribution_blocks_when_pending_analysis_runs` PASS |
| 中止メッセージに「安全装置 #8」の文字列を含む | 同上 |

## 外部・過去事例の参照と我々への応用

- 本日（2026-09-04）の実インシデント: 6ジョブ再解析が 00:59 UTC 開始・completed_at=NULL のまま、02:39 UTC 完了前に配信スクリプトが実行された
- 手順書への記載「配信前に pending = 0 を確認すること」は、手動確認依存のため防止力が低い
- コードガードとすることで手順書・人間の確認を不要にする

## 維持の仕組み

守り手: `test_run_distribution_blocks_when_pending_analysis_runs` が analysis_runs テーブルへのアクセスをモックし、ガードの動作を常時確認する。ガードロジックを削除・変更した場合はテストが失敗する。
