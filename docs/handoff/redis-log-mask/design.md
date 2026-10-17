# design: Redis の接続ログでパスワードを伏せる（2026-10-17。PO「y」）

- 参照: docs/handoff/redis-log-mask/recon.md、ADR-075（秘密は GitHub Secrets だけに置く）・S3 の考え方（秘密を外へ出さない）
- 目的: ログにパスワードを出さない。ホスト・ポート・DB 番号は残す（障害の調べに使う）
- 変更: backend/app/cache.py に `_mask_url` を足し、:29 で使う。分けられない値は `<redacted>`
- 触らない: Redis のパスワード自体（変えない）、他の logger
- 戻し方: PR を Revert
- 外部事例: 不要（1行のログの伏せ字。urllib.parse の標準の分け方を使う）

## 受入
| 基準 | 検証方法 |
|---|---|
| パスワード入り URL がログで `***` になる | backend/tests/test_cache_mask_url.py |
| init_redis 成功ログにパスワードが無い | 同上（caplog） |
| 本番の gateway のログで、反映後の起動の行が `redis://:***@` | docker compose logs discord-gateway を grep（パスワード入りの行が新しく増えない） |

## 外部・過去事例の参照と我々への応用
- 過去事例: S3（#4399、例外の中身を応答に出さない）。秘密や内部の値を外へ出さない同じ考え方を、ログに当てはめる。
- 外部事例: 使わない（数字で効果を示す事例は不要。1行のログの伏せ字で、効果は本番ログの grep で直接確かめる）。

## 維持の仕組み
- 守り手: backend/tests/test_cache_mask_url.py（CI の pytest で毎回走り、ログにパスワードが出ると落ちる）
