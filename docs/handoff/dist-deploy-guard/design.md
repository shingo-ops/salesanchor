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

---

## GAS 配信 Web アプリ所有権ポリシー（2026-09-04 確定）

### 確定事実（公式ドキュメント）

出典: https://developers.google.com/apps-script/guides/bound  
出典: https://developers.google.com/apps-script/guides/collaborating

| 事実 | 内容 |
|---|---|
| コンテナ所有者 = スクリプト所有者 | 誰が作成したかに関わらず、スプレッドシート所有者がスクリプトプロジェクトの所有者になる |
| アクセスリスト継承 | 編集権限者はスクリプトを実行可能、閲覧者はコードを参照可能 |
| 共有ドライブのデプロイ制約 | デプロイするアカウントが同じドメインに属している必要がある |
| clasp の制約 | バインドスクリプトを新規作成できない（clone と edit のみ） |

### 方針（PO 確定）

配信先スプレッドシートは Shingo が所有し、クライアントには渡さない。  
Web アプリは認証なし（ANYONE_ANONYMOUS）のため URL のみ提供。

- 所有権: Shingo に固定（コンテナ = Shingo 所有）
- コード非公開: クライアントはアクセスリスト外
- デプロイ制約なし: 同一ドメイン・所有者がデプロイ
- 更新方法: `tcg-client-viewer/` から clasp でコード更新 → 既存デプロイ ID に上書き（URL 不変）

### 配布手順書への追記事項

「配信先スプレッドシートは自社（Shingo）所有とする。クライアントへの共有不要。Web アプリ URL のみ提供する。」
