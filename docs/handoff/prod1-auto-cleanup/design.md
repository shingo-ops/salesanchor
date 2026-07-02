# prod1 Docker 自動クリーンアップ 設計書（F2）

## 概要

prod1 VPS の Docker 資源を週次で自動回収するスクリプト (`scripts/f2-cleanup.sh`) を導入する。

## 受け入れ基準（KGI-F2）

| # | 条件 | 出力での見方 | 判定 |
|---|------|-------------|------|
| a | 捨て駒がガードで残り→0h で消える | RUN1 で `KEEP ... f2-dummy-stopped`、RUN2 で `REMOVED ... f2-dummy-stopped` | ○/× |
| b | 現役・本番が無傷 | BEFORE/AFTER で `running=11` 不変（postgres/redis 含む） | ○/× |
| c | 消えたのはキャッシュ＋停止コンテナのみ | `volumes=171` `images=36` が BEFORE/AFTER で不変 | ○/× |

## 対象・非対象

### 対象（削除する）

| 種別 | 条件 |
|------|------|
| 停止コンテナ（exited） | `FinishedAt` 基準で AGE_HOURS（既定 168h = 7日）より古いもの |
| Build キャッシュ | `docker buildx prune --filter "until=${AGE_HOURS}h" --force` で古いキャッシュ |

### 非対象（一切触れない）

- **volume**（`astro-webapp_postgres_data`・`astro-webapp_redis_data` 含む全171個）
- **image**（全36個）
- **稼働中コンテナ**（11個）
- crontab 既存 2 行（backup.sh / backup_to_s3.sh）

## 年齢測定の基準

- **コンテナ**: `FinishedAt`（作成日でなく停止日）で計測
  - 理由: CI が短命コンテナを大量生成するケースで作成日基準だと現役コンテナを誤削除するリスクがある
- **Build キャッシュ**: `--filter "until=${AGE_HOURS}h"`（Docker 内部の最終使用時刻基準）

## 実行スケジュール

| 項目 | 値 |
|------|-----|
| 頻度 | 週1回 |
| 実行時刻 | 日曜 04:00 JST |
| 実行ユーザー | ubuntu |
| ログ | `/tmp/f2-cleanup.log`（コンテナ再起動で消えるが週次で十分） |
| 引数 | `168 both`（既定値のため省略可） |

crontab 追加行（Phase 3 以降・PO GO後）:
```cron
0 4 * * 0  TZ=Asia/Tokyo bash /home/ubuntu/salesanchor/scripts/f2-cleanup.sh 168 both >> /tmp/f2-cleanup.log 2>&1
```

## ROLLBACK

crontab の該当1行を削除するだけで即停止する。  
本番DB (`astro-webapp_postgres_data`) / 本番コード / volume / image に一切触れないため、スクリプト実行済みでも本番への影響はない。

## ADR 参照

| ADR | 関連内容 |
|-----|---------|
| ADR-079 | 鍵制約（制限付き鍵 `salesanchor-claude` / 無制限鍵 `manual-only`） |
| ADR-114 | 掃除自動化の先例（既存 cleanup 運用パターン） |
| ADR-135 | develop にマージ = 本番投入可の宣言（本 PR は main base のリリース PR） |

## 外部事例

- Docker 公式: `docker buildx prune --filter "until=<duration>"` はフィルタ値として `until` を受け付ける（`--filter` フラグ自体は `docker buildx prune --help` で確認済み）
- GitHub Actions self-hosted runner 運用では週次 `docker system prune` が一般的だが、volume・image を誤削除するリスクがあるため、本設計では対象を停止コンテナ＋build キャッシュのみに限定

## recon / ADR 相互参照

- recon 出典: `docs/handoff/prod1-auto-cleanup/recon.md`（2026-06-29 14:32 JST FRESH-RUN）
- 停止コンテナ: recon §② = 0個（クリーン）
- 保持必須 volume: recon §③ `astro-webapp_postgres_data`・`astro-webapp_redis_data`
- build キャッシュ: recon §⑤ = 2.287GB・最古2ヶ月前

## 検証方法

```
| 基準 | 検証方法 |
|------|---------|
| BEFORE/AFTER で running=11 不変 | snap 関数の出力を目視確認 |
| volumes=171 不変 | snap 関数の出力を目視確認 |
| images=36 不変 | snap 関数の出力を目視確認 |
| 捨て駒 KEEP → REMOVED | RUN1/RUN2 のログ行を目視確認 |
```
