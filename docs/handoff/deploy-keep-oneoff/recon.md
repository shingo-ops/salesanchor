# recon — deploy-keep-oneoff

**仕事名**: deploy-keep-oneoff  
**日付**: 2026-10-17  
**対象ADR**: ADR-092  
**担当**: Sonnet（Opus 設計のカードに基づく）

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `.github/workflows/deploy.yml:417` | frontend / celery-beat / discord-gateway の pre-cleanup。名前の部分一致のみで `docker rm -f`（変更前は :416） |
| `.github/workflows/deploy.yml:419` | celery-worker の pre-cleanup。同じく名前の部分一致のみ（変更前は :418） |
| `.github/workflows/deploy.yml:684` | ロールバック時の差し替え。同じ名前フィルタ（変更前は :682） |
| `docs/adr/ADR-092-deploy-concurrency-control.md:44` | pre-cleanup の決定。一時コンテナ（compose run）への言及なし |
| `scripts/ops/reextract-v6-loop.sh:41` | compose run で一時コンテナを作る唯一の repo 内スクリプト |

## 事実（実測）

- 本番で実測（Opus）: `compose run` の一時コンテナ名は `astro-webapp-<svc>-run-<hash>`、label `com.docker.compose.oneoff=True`。`name=astro-webapp-redis` だけだと一時コンテナも常駐 `-1` も一致し、`oneoff=False` を足すと常駐 `-1` だけが残る。
- 結論: 名前フィルタだけの rm -f は、実行中の一時コンテナ（再解析ループ等）も消す。`label=com.docker.compose.oneoff=False` を足せば一時コンテナは外れる。
- 使い捨て環境での再現（Mac / colima / docker-compose 5.5.1）で、修正前は一時コンテナも消え、修正後は残ることを確認した（生ログ: /Users/tanizawashingo/CC報告ファイル-keep/accuracy-20261014/g28-bulk-price/post/side4/p1_deploy_rm/verify/k2k3.log、リポジトリ外のため引用のみ）。

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | `compose stop -t 60 celery-worker` / `up --remove-orphans` が一時コンテナに効くか | 使い捨て環境で観測（k2k3.log の K3 節） | 解消済み（効かない。ただし本番の compose バージョンでは未確認） |
| 2 | 本番での生き残り | 本番反映後に Opus が一時コンテナを動かしながら確認（K4） | 本PRの範囲外 |

**未解決ゼロ確認**: 不明点 2 のみ本番反映後の確認事項として残る
