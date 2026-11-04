# ADR-1055 段C 直し: ログインを受け付ける本体に「場所の表」をつなぐ（実装カード v1）

- 状態: 設計案作成済み・Opus 自己審査 APPROVE（同一AIの審査で、独立した第二者の審査ではない）・PO 実装承認済み（2026-11-04 PO「1」＝直しを始める）
- 担当: 実装はクラウドの Sonnet。マージ前に手元の審査役（reviewer・opus）の審査を受ける。GO・マージは PO の委任に基づき Claude Opus（本番 `scripts/` を含む危険 PR・ADR-136。secrets は触らないので委任の例外に当たらない）

## 1. 目的（PO に見える変化）
- 知らない機械からのログインの知らせ（メール・アプリの許可画面・ログインしている機械の一覧）の「場所の目安」に、市や国の名前が出る（今は全部「不明」）
- 同じ種類のつなぎ忘れ（本番の構成にはあるのに、本番の入れ替え手順に無い置き場）を、次からは試験が赤で止める

## 2. 観測した事実（2026-11-04・根拠つき）
- 本番の許可依頼 7件すべて場所が空: reader 鍵の道で `SELECT date_trunc('day', created_at AT TIME ZONE 'Asia/Tokyo') d, count(*) n, count(location) with_loc FROM ai_ro.public__auth_login_requests GROUP BY 1` → 11-03 n=6 with_loc=0 / 11-04 n=1 with_loc=0（AUDIT ts=2026-11-04T02:37:45Z）
- 接続元の番号は外から見える IPv4: 同じ表で 社内向けの番号 0件・空 0件・IPv6 0件（AUDIT ts=2026-11-04T02:38:13Z）。番号の取り方は `backend/app/client_ip.py`（nginx が X-Real-IP を `$remote_addr` で上書き `nginx/nginx.conf:117` ほか）
- 場所は `backend/app/auth/geo.py:67-99` `lookup()` が引く。表のファイル（既定 `/geoip/dbip-city-lite.mmdb` `:18`）が無ければ None → 呼び出し側が「不明」と出す（`:78-80`）
- 本番の実物（PO の `!` 読み取り `geo-file-check.sh`・2026-11-04）:
  - `astro-webapp-celery-worker-1`: `/geoip/dbip-city-lite.mmdb` あり（126873350 バイト・Nov 2 19:00 UTC）・`astro-webapp_geoip -> /geoip` をつないでいる
  - `astro-webapp-backend-1`: `/geoip/` は空（FILE=missing）・geoip のつなぎが無い・`GEOIP_DB_PATH` は未設定（コードの既定が効くので問題ない）
- 本番の構成の正本では backend もつなぐ: `docker-compose.yml:159-160`（`# 場所の元データは celery-worker が書き、backend は読むだけ` / `- geoip:/geoip:ro`）
- しかし本番の backend は compose ではなく入れ替え手順が `docker run` で作る: `.github/workflows/deploy.yml:461` `bash scripts/blue-green-cutover.sh`（反映のたびに必ず通る）
- その `docker run` の置き場は3つだけで geoip が無い（入れ忘れ）: `scripts/blue-green-cutover.sh:94-96`
  ```
    --volume "${REPO_DIR}/firebase-credentials.json:/app/firebase-credentials.json:ro" \
    --volume "${REPO_DIR}/tcg-sheets-sa.json:${REPO_DIR}/tcg-sheets-sa.json:ro" \
    --volume "${COMPOSE_PROJECT}_attachments_data:/data/attachments" \
  ```
- 名前つきの置き場の実名は `${COMPOSE_PROJECT}_<名前>`（本番 `docker volume ls` に `astro-webapp_geoip`）。`COMPOSE_PROJECT="astro-webapp"`（`scripts/blue-green-cutover.sh:26`）
- 試験の流れ: `.github/workflows/test.yml:17-25`・`:43-50` は `scripts/**` と `docker-compose.yml` の変更で backend の pytest を動かす。yaml の読み込みは既存の試験 `backend/tests/test_compose_worker_env.py:10` と同じ形が使える

## 3. 変更（2ファイル）
### 3-1. `scripts/blue-green-cutover.sh`（1行足すだけ）
変更前（`:96`）:
```
  --volume "${COMPOSE_PROJECT}_attachments_data:/data/attachments" \
```
変更後（`:96` の次に1行）:
```
  --volume "${COMPOSE_PROJECT}_attachments_data:/data/attachments" \
  --volume "${COMPOSE_PROJECT}_geoip:/geoip:ro" \
```
- 実装前に実物の `:94-96` が §2 の3行と同じ文字か読む。違えば止める

### 3-2. 新しい試験 `backend/tests/test_bg_cutover_volume_parity.py`
- `docker-compose.yml` の `services.backend.volumes` を yaml で読む
- 名前つきの置き場（短い書式 `名前:行き先[:ro]` で、名前が `.` `/` `$` で始まらないもの）を全部取り出す。今は `geoip:/geoip:ro` と `attachments_data:/data/attachments` の2つ
- それぞれについて、`scripts/blue-green-cutover.sh` の中に `--volume "${COMPOSE_PROJECT}_<名前>:<行き先>[:ro]"` が、同じ行き先・同じ読み取り専用の有無で1つあることを確かめる。無ければ名前を並べて落とす
- ファイルから置き場（bind）は比べない（`TCG_SHEETS_SA_KEY_FILE` の行き先が環境で変わり、入れ替え手順は別の書き方をしているため）
- 取り出した名前つきの置き場が0個なら落とす（読み方が壊れて素通りするのを防ぐ）
- 書き方は `backend/tests/test_compose_worker_env.py` に揃える（パスは `pathlib.Path(__file__).resolve().parents[2]`）

### 触らない
- `docker-compose.yml`・`deploy.yml`・`backend/app/`・frontend・DB・secrets・`.env`・他の scripts。過去の許可依頼 7件の場所は埋め直さない（その時点の番号で引き直すことはしない）

## 4. 選んだ理由と退けた案
- 採用: 入れ替え手順に1行足す。構成の正本（compose）の意図どおりに本番を揃えるだけで、コードは変えない。戻しは revert だけ
- 退けた案1: backend に `GEOIP_DB_PATH` で別の場所を渡す → 表の置き場が2か所に分かれる（SSOT に反する）
- 退けた案2: backend の起動時に表を落とす → 取り込み係（worker）と二重になり、外への通信が増える
- 退けた案3: 試験を足さない → 同じつなぎ忘れが別の置き場でまた起きる（PO 10/31 の恒久ルール「同じ種類のミスは二度と通さない」に反する）

## 5. 守りへの影響
- 場所は表示と記録だけで、許可の判定には使わない（`backend/app/auth/geo.py:4`）。ログインを止める仕組みは変わらない
- 読み取り専用（`:ro`）でつなぐ。backend は表に書けない
- 表が読めないときも認証は止めない（`geo.py:54-56`・`:78-80`）

## 6. 受入条件
| 基準 | 検証方法 |
|---|---|
| G-a 変更は2ファイル（と本カード） | PR の diff が `scripts/blue-green-cutover.sh` の1行追加・新しい試験1ファイル・本カードのみ |
| G-b 試験が入れ忘れを見つける | Sonnet が、3-1 の1行を一時的に外した状態で新しい試験が落ち、`geoip` の名前が出ることを生出力で示す（戻してから commit） |
| G-c CI が緑 | PR の必須の確かめがすべて緑 |
| G-d 本番の backend に表が見える | 反映後、PO の `!` で `geo-file-check.sh` → `astro-webapp-backend-1` が FILE=present・`astro-webapp_geoip -> /geoip` |
| G-e 新しい依頼に場所が入る | 反映後の次の許可依頼（K7 の確かめでも可）で、reader 鍵の道の `count(location)` が反映後に作られた依頼の数と同じ。メールの「場所の目安」が「不明」でない（Gmail の本文） |

## 7. 戻し方
この PR を revert する PR を main に入れる。次の反映で backend は表なしに戻る（場所が「不明」に戻るだけ・認証は止まらない）。

## 8. 止まる条件
- 実物の `scripts/blue-green-cutover.sh:94-96` が §2 と違う → 止めて報告
- 新しい試験が今の compose で別の置き場の食い違いを見つけた → 直さず止めて報告
- CI が赤 → 直さず報告
- 3-1・3-2 以外を変えたくなった → 止めて報告

## 9. 外部事例
不要。自社の構成の正本と入れ替え手順の食い違いを直すだけで、外部の仕組みの判断を含まない。

## 10. 維持の仕組み
- 新しい試験が、compose の backend に名前つきの置き場を足して入れ替え手順に足し忘れたときに CI を赤にする（`scripts/**` と `docker-compose.yml` の変更で必ず動く）
