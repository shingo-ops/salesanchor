# ADR-1055 段C 直し2: 場所の表を開く命令の名前を直す（実装カード v1）

- 状態: 設計案作成済み・Opus 自己審査 APPROVE（同一AIの審査で、独立した第二者の審査ではない）・PO 実装承認済み（2026-11-04 PO「1」＝直しを始める）
- 担当: 実装はクラウドの Sonnet。マージ前に手元の審査役（reviewer・opus）の審査を受ける。GO・マージは PO の委任に基づき Claude Opus（backend の1行と試験だけ・secrets は触らない）
- 前の直し: `stageC-geoip-mount-card.md`（本体に場所の表をつないだ・本番反映済み）。その後も場所が空のままだったので調べ直した

## 1. 目的（PO に見える変化）
- 知らない機械からのログインの知らせ（メール・許可画面・機械の一覧）の「場所の目安」に、市や国の名前が出る（例「Phoenix, アメリカ合衆国」）
- 表を実際に開いて引く道を試験で通す。同じ種類の間違い（部品にない名前で開く）を、次からは試験が赤で止める

## 2. 観測した事実（2026-11-04・根拠つき）
- 前の直しの後も、新しい許可依頼の場所が空: reader 鍵の道 `SELECT id, status, created_at, ..., location FROM ai_ro.public__auth_login_requests WHERE created_at > '2026-11-04 04:20:05+00'` → 1件（04:34:31 UTC）・location 空（AUDIT ts=2026-11-04T05:00:22Z）。接続元は公開の IPv4（同じ表・`family=4`・私用の帯ではない・AUDIT ts=2026-11-04T05:00:56Z）
- 本番の backend の中で試した結果（PO の `!` 読み取り `geo-lookup-check.sh`・15:09 JST・生出力 `/tmp/CC報告ファイル/stagec/geo/lookup-check.txt`）:
  - `astro-webapp_geoip -> /geoip rw=false`（前の直しどおりつながっている）
  - `maxminddb 3.2.0`・`has Mode: False MODE_MMAP: 2`
  - 1回目（14:36）: `AttributeError: module 'maxminddb' has no attribute 'Mode'`
  - `maxminddb.open_database("/geoip/dbip-city-lite.mmdb", maxminddb.MODE_MMAP)` は開けた: `metadata: DBIP-City-Lite`・`city -> {'en': 'Phoenix'}`・`country -> {..., 'ja': 'アメリカ合衆国', ...}`
  - 今のコードの `geo.lookup("4.249.21.1")` と `geo.lookup("8.8.8.8")` はどちらも `None`、そのたびに `geoip: ファイルを開けない（場所は不明として扱う）`
- 手元で同じ版を入れて確かめた（Python 3.12 venv・`pip install maxminddb==3.2.0`）: `dir(maxminddb)` の MODE は `MODE_AUTO, MODE_FD, MODE_FILE, MODE_MEMORY, MODE_MMAP, MODE_MMAP_EXT`・`maxminddb.MODE_MMAP == 2`。Context7 にこの部品の資料は無かった（`resolve-library-id "maxminddb python"` で該当なし）ので、実物の部品で確かめた
- 間違っている行: `backend/app/auth/geo.py:53` `new_reader = maxminddb.open_database(path, maxminddb.Mode.MMAP)`。例外は `:54-56` で握られて None になる（認証は止まらない）
- 部品の版: `backend/requirements.txt:54` `maxminddb==3.2.0`
- 部品を使っている所はこの1か所だけ（`git grep -n -E 'maxminddb|Mode\.' origin/main -- backend/`）
- 今までの試験が見逃した理由: `backend/tests/test_new_device_approval.py:1068-1075` `test_geo_lookup_returns_none_without_database` は表が無いときしか試していない。表を開く道を通る試験が無かった（前の設計での入れ忘れ）

## 3. 変更（2ファイル）
### 3-1. `backend/app/auth/geo.py:53`（1行）
変更前:
```
            new_reader = maxminddb.open_database(path, maxminddb.Mode.MMAP)
```
変更後:
```
            new_reader = maxminddb.open_database(path, maxminddb.MODE_MMAP)
```
- 実装前に実物の `:53` が上の「変更前」と同じ文字か読む。違えば止める

### 3-2. 試験を1つ足す（`backend/tests/test_new_device_approval.py` の `test_geo_lookup_returns_none_without_database` の直後）
- 名前: `test_geo_lookup_opens_database_and_formats_place`
- `tmp_path` に中身が何でもよいファイルを1つ作り、`GEOIP_DB_PATH` をそのパスにする（`os.stat` を通すため）
- `geo._reader`・`geo._reader_path`・`geo._reader_mtime` を `monkeypatch.setattr` で None にする（前の試験の残りを消す・試験の後は自動で戻る）
- `maxminddb.open_database` を `monkeypatch.setattr` で偽物に差し替える。偽物は受け取った mode を記録し、`get(ip)` で次を返す読み手を返す:
  `{"city": {"names": {"en": "Phoenix"}}, "country": {"names": {"en": "United States", "ja": "アメリカ合衆国"}}}`
- 確かめること:
  - `geo.lookup("4.249.21.1") == "Phoenix, アメリカ合衆国"`
  - 記録した mode が `maxminddb.MODE_MMAP`
- `maxminddb.Mode` などの部品の名前を、試験の側で足したり差し替えたりしない（それをすると今回の間違いが試験で隠れる）
- 3-1 を外した状態でこの試験が落ちること（今のコードは `AttributeError` を握って None を返す）を生出力で示す。戻してから commit

### 触らない
- `geo.py` の他の行・`devices.py`・`routers/`・frontend・compose・`scripts/`・deploy.yml・DB・secrets・`requirements.txt`（部品の版は変えない）
- 過去の許可依頼の場所は埋め直さない

## 4. 選んだ理由と退けた案
- 採用: 部品が持つ名前 `MODE_MMAP` に1行で直す。動きは開き方を含めて元の意図どおり（MMAP）で、戻しは revert だけ
- 退けた案1: mode を渡さず既定（`MODE_AUTO`）にする → 開き方が環境で変わり、意図した MMAP と違う場合がある
- 退けた案2: 部品の版を変える → 影響が広く、今回の原因（名前の誤り）に対して大きすぎる
- 退けた案3: 本物の小さな表ファイルを試験用に作る → 表を書く部品が依存に無く、新しい依存が増える。偽の読み手で「開く命令の名前」と「並べ方」は確かめられる。本物の表で引けることは §6 G-d で本番で確かめる

## 5. 守りへの影響
- 場所は表示と記録だけで、許可の判定には使わない（`backend/app/auth/geo.py:4`）。ログインを止める仕組みは変わらない
- 表が読めないときに None を返す作り（`:54-56`・`:78-80`）はそのまま

## 6. 受入条件
| 基準 | 検証方法 |
|---|---|
| G-a 変更は2ファイル（と本カード・実装報告） | PR の diff が `geo.py` の1行・試験1つの追加・文書のみ |
| G-b 試験が間違いを見つける | Sonnet が 3-1 を一時的に外した状態で新しい試験が落ちることを生出力で示す（戻してから commit） |
| G-c CI が緑 | PR の必須の確かめがすべて緑 |
| G-d 本番の backend で場所が引ける | 反映後、PO の `!` で `geo-lookup-check.sh` → `geo.lookup: 'Phoenix, アメリカ合衆国'` の形（None でない）・「ファイルを開けない」が出ない |
| G-e 新しい依頼に場所が入る | 反映後の次の許可依頼（K7 の再実行でも可）で reader 鍵の道の `count(location)` が反映後に作られた依頼の数と同じ。メールの「場所の目安」が「不明」でない |

## 7. 戻し方
この PR を revert する PR を main に入れる。場所が「不明」に戻るだけで、認証は止まらない。

## 8. 止まる条件
- 実物の `geo.py:53` が §3-1 の「変更前」と違う → 止めて報告
- 試験の環境に `maxminddb` が入っていない・`MODE_MMAP` が無い → 止めて報告
- CI が赤 → 直さず報告
- 3-1・3-2 以外を変えたくなった → 止めて報告

## 9. 外部事例
不要。部品の名前の誤りを直すだけで、外部の仕組みの選び方を含まない。

## 10. 維持の仕組み
- 新しい試験が、表を開く命令を部品にない名前に変えたとき（部品の版上げで名前が変わったときを含む）に CI を赤にする
