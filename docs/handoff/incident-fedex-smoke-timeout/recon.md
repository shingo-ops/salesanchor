# recon — FedEx smoke タイムアウト障害（2026-09-02）

> この文書は何か（専門用語なしの1行）:
> 2026年9月2日にデプロイが失敗した件について、何が起きていたのかを実物のコードとログで確かめた記録。

**仕事名**: incident-fedex-smoke-timeout
**日付**: 2026-09-02
**対象ADR**: ADR-125（FedEx Rates Stage1）
**担当**: architect
**親**: 該当なし。docs/specs/README.md（索引）に本領域の設計仕様書は存在しない（2026-09-02 実測・grep で該当0件）。
**測定SHA**: 1f0cae7fb632533a24e580acdaea6f884ee6bc67

---

## 事象

2026-09-02T03:28:57Z 開始のデプロイ run 33587198390（headSha 93de37e5bb05e8cd77537b5e21bc2f5df504db4b・PR #3206 のマージ）が failure で終了した。失敗ステップは step 18「FedEx Rates live smoke (ADR-124 D2)」。

ログ実測（run 33587198390 / job 100113715023）:
- 03:31:50Z 呼び出し開始
- 03:31:59Z ERROR: live_error returned — FedEx API not healthy: FedEx 見積もり取得失敗: Rates API タイムアウト（FedEx サーバーが応答しません）
- 03:32:00Z Process exited with status 1

同ログに Discord 通知の応答として次が記録されている。
{"message": "Unknown Webhook", "code": 10015}

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `.github/workflows/deploy.yml:487` | FedEx smoke ステップの条件は `if: ${{ success() }}`。migration の有無に関係なく全デプロイで実行される |
| `.github/workflows/deploy.yml:498` | `FEDEX_SMOKE_ENABLED` が `true` でなければ exit 0 でスキップする |
| `.github/workflows/deploy.yml:504` | `bash scripts/smoke/external-fedex.sh --live` を呼ぶ |
| `.github/workflows/deploy.yml:516` | smoke の exit が非0のとき exit 1 でステップを失敗させる |
| `.github/workflows/deploy.yml:523` | `ROLLBACK_DISCORD_WEBHOOK` に `secrets.DISCORD_WEBHOOK_OWNER_PING` を渡す |
| `.github/workflows/deploy.yml:536` | 同じ secret を Finalize の自動ロールバック通知にも使う |
| `.github/workflows/deploy.yml:44` | paths-filter の `nginx` フィルタ対象は `nginx/**` と `docker-compose.yml` の2つ |
| `.github/workflows/deploy.yml:361` | Recreate nginx の条件は `success() && steps.changes.outputs.nginx == 'true'` |
| `.github/workflows/deploy.yml:671` | Verify deployment は `if: success()` |
| `.github/workflows/deploy.yml:767` | Stamp main deploy date は `if: success()` |
| `.github/workflows/deploy.yml:907` | Emergency block /design/ は `if: failure()`。htpasswd を削除して nginx を force-recreate する |
| `scripts/smoke/external-fedex.sh:140` | --live は FedEx を直接叩かず、本番 backend の /api/v1/shipping/calculate を curl する。`--max-time` の指定がない |
| `scripts/smoke/external-fedex.sh:175` | live_error の文字列をそのまま ERROR として出力する |
| `scripts/smoke/external-fedex.sh:180` | exit 1 で終了する |
| `backend/app/services/fedex_rates.py:103` | `_TIMEOUT = httpx.Timeout(connect=3.0, read=7.0, write=5.0, pool=5.0)`。環境別・テナント別の分岐はない |
| `backend/app/services/fedex_rates.py:351` | Rates API への `httpx.post` |
| `backend/app/services/fedex_rates.py:359` | 上記 post に `timeout=_TIMEOUT` を渡す |
| `backend/app/services/fedex_rates.py:361` | `httpx.TimeoutException` を捕捉する |
| `backend/app/services/fedex_rates.py:362` | `FedExAPIError("Rates API タイムアウト（FedEx サーバーが応答しません）")` を raise する |
| `backend/app/routers/shipping.py:339` | `_try_fedex_live` の try。`fedex_rates.get_rates` を1回呼ぶ |
| `backend/app/routers/shipping.py:356` | `FedExAPIError` を捕捉する |
| `backend/app/routers/shipping.py:358` | live_error を返して終了する。再試行しない |
| `backend/app/routers/shipping.py:417` | calculate が `_try_fedex_live` を1回だけ呼ぶ |
| `.github/workflows/monthly-secret-expiry.yml:22` | 失効監視の WATCH_LIST に `DISCORD_WEBHOOK_OWNER_PING` が含まれる |

---

## 確定した事実

1. FedEx Rates 呼び出しのタイムアウトは接続3.0秒・読み取り7.0秒。リトライは存在しない。`shipping.py` と `fedex_rates.py` を retry / retries / リトライ / 再試行 で grep した結果、ヒットは `fedex_rates.py:367` のコメント1件のみで、実装はない。7秒応答がなければ1回で確定的に失敗する。
2. 失敗頻度は30 run 中1件。標本は 2026-08-31T09:07Z から 2026-09-02T05:53Z までの deploy.yml の run 30件で、failure は run 33587198390 のみ。
3. 直後の run 33595722661（PR #3216）では同ステップが success。スキップではない。
4. 失敗の波及は3つ。step 20 Verify deployment と step 21 Stamp が skipped、step 22 Emergency block /design/ が実行された。
5. デプロイ失敗と docker-compose.yml のボリューム未反映に因果はない。PR #3206 の変更ファイルは4件（backend/app/discord_gateway/ticket_channel_writer.py、backend/tests/test_discord_attachment_save.py、docs/handoff/discord-attachment-save/design.md、docs/handoff/discord-attachment-save/recon.md）で docker-compose.yml を含まない。したがって step 14 のスキップは条件どおりの動作であり、smoke の失敗より前に決まっている。
6. 失敗時の Discord 通知が届いていない。ADR-124 D2 のコメント（deploy.yml:481-485）は FedEx 側障害に対する歯止めを Discord 即時通知に置いているが、その経路が機能していない。
7. `secrets.DISCORD_WEBHOOK_OWNER_PING` を実際に参照するのは4か所。deploy.yml:523、deploy.yml:536、external-state-snapshot.yml:112、external-state-snapshot.yml:128。他の多数のワークフローは環境変数名が同じでも中身に `secrets.DISCORD_WEBHOOK_SCHEDULED_REPORT` を渡している。

---

## 既存ADR検索の結果

実施コマンドと結果:
- `git grep -c -i "smoke" -- docs/adr/` → 19ファイルがヒット。主なもの: ADR-035、ADR-038、ADR-115、ADR-125、ADR-134、ADR-1000、ADR-SA-19
- `git grep -c -i -E "timeout|retry|リトライ|再試行" -- docs/adr/` → 10ファイルがヒット。主なもの: ADR-029、ADR-056、ADR-125、ADR-137
- `docs/adr/FEATURE-INDEX.md` を fedex / smoke / deploy / webhook / discord / 通知 で grep → 7行がヒット（17、18、19、37、38、43、49行目）

該当ADR: ADR-125（FedEx Rates Stage1・本件の直接の親）、ADR-115（デプロイ安全策）、ADR-134（設計図書サイト配信・/design/ 遮断の根拠）、ADR-035（外部状態検証・OWNER_PING webhook の出所）。

参照番号の食い違い（要修正・本reconの発見）:
`.github/workflows/deploy.yml:479` のコメントと step 18 の名称は「ADR-124 D2」を名乗る。しかし ADR-124 のファイルは `docs/adr/ADR-124-sop-health-reporter.md` であり、smoke でも fedex でもない。上記2つの grep でも ADR-124 は1件もヒットしない。既存の `docs/handoff/fedex-smoke-switch/design.md:3` は対象ADRを ADR-125 と記載している。deploy.yml の参照番号が誤っている可能性が高い。修正の要否は design で判断する。

---

## 過去の同型事例（社内）

同じ型（単発チェックが一時的な遅延で偽の失敗を出す）が過去に2回あり、いずれもリトライの導入で対処されている。

| 事例 | 対象 | 対処 |
|---|---|---|
| `docs/handoff/deploy-timeout-fix/design.md` | deploy.yml の Step 6 ヘルスチェック | 単発チェックを36回×5秒のリトライへ変更 |
| `docs/handoff/smoke-health-retry/design.md` | `scripts/smoke_test_post_deploy.sh` | 1回実行を3回×5秒のリトライへ変更 |

`docs/handoff/smoke-health-retry/design.md:9` に「本物の障害は複数回連続で失敗する」という原則が記されている。step 18 の FedEx smoke には、この原則がまだ適用されていない。

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 7秒以内に応答が無かった原因（FedEx側／VPSからの経路／backend負荷のいずれか） | 事後のログに残らないため、読み取りでは解消不能。新たな計測の設計が必要 | 未解消 |
| 2 | `DISCORD_WEBHOOK_OWNER_PING` が現時点でも無効か | Discord への送信が必要なため、読み取りでは解消不能 | 未解消 |
| 3 | 2026-09-02T03:31Z 時点の FedEx API の稼働状態 | 外部の公開情報では当該時刻の状態を確認できなかった（00:01Z 時点の正常観測のみ） | 未解消 |

**未解決ゼロ確認**: 未解決3件あり。いずれも読み取りでは解消できない性質のもの。design 着手の可否は PO 判断とする。

---

## 補足

- 本reconの測定は固定SHA `1f0cae7fb632533a24e580acdaea6f884ee6bc67` で行った。その後 origin/main は複数回進んだが、引用対象5ファイル（deploy.yml、fedex_rates.py、shipping.py、external-fedex.sh、docker-compose.yml）に差分がないことを `git diff --name-only` で確認済み。
- 索引 `docs/specs/README.md` に本領域の設計仕様書は存在しない。設計仕様書の要否は design で判断し、作成する場合は同便で索引に1行登録する。
- 関連テーマ `docs/specs/secrets-permission-ssot/` は鍵の台帳化と置き間違いの警報を扱うテーマで、本件の webhook 失効とは性質が異なる。同テーマは recon 未着手（README.md:16-17）。
