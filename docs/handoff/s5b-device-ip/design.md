# 設計 — 端末登録も共通の関数で接続元 IP を決める（S5 の別便）

**日付**: 2026-10-17　**現在地**: docs/handoff/s5b-device-ip/recon.md　**仕様**: docs/specs/client-ip/README.md　**ADR**: ADR-127（回数制限）、ADR-1003（GO 委任）　**PO 承認**: 2026-10-17 チャットで「y」（「端末登録で接続元を正しく記録する修正。S5 で作った正しい接続元の取り方に直す」への回答）

## 1. 目的（利用者に見える変化）

端末登録の回数制限と記録を、本当の接続元ごとに行う。

- 今は、全員が nginx の内部の住所（172.20.0.2）として数えられている（recon §2）。
- その結果、「同じ接続元から 1 時間 10 件」の制限が「全員合わせて 10 件」として効いている。記録からも、どこから登録したかが分からない。

## 2. 変更（変更前 → 変更後）

backend/app/routers/line_import_devices.py

```python
# 変更前 :35-36
    # Use the socket peer for a conservative limit; do not trust arbitrary XFF.
    return await service.start(db, data.token_hash, data.name, request.client.host if request.client else 'unknown')
# 変更後
    # 接続元は共通の関数で決める（docs/specs/client-ip/README.md。X-Forwarded-For は読まない）
    return await service.start(db, data.token_hash, data.name, get_client_ip(request))
```

import を 1 行足す: `from app.client_ip import get_client_ip`。

触らないもの:
- service（制限の数 10 と 30、sha256 での保存）
- DB と migrations
- nginx
- 取り込みスクリプト
- ほかのルーター

既にある 1 行のハッシュは書き換えない（過去の記録として残す）。

## 3. 挙動の変わり方（PO に伝える点）

| | 変更前（本番の実態） | 変更後 |
|---|---|---|
| 同じ接続元からの上限 | 全員で 1 時間 10 件（全員が同じ接続元に見えるため） | 接続元ごとに 1 時間 10 件 |
| 全体の上限 | 30 件（10 件の制限が先に効くため、実際には効かない） | 30 件（変わらない） |
| 記録される接続元 | 全員 172.20.0.2 | 本当の接続元（のハッシュ） |

- 制限の数は変えない。もともとのコードが意図した「接続元ごとに 10 件」が、そのとおりに効くようになる。
- 1 人の攻撃者が自分で書いて偽れる値（X-Forwarded-For）は、今までどおり読まない。
- X-Real-IP は nginx が毎回上書きするので、利用者は偽れない（docs/specs/client-ip/README.md）。

## 4. 試験（backend/tests/test_line_import_devices.py に足す）

- T1: `/api/v1/tcg/line-devices/start` に `X-Real-IP: 203.0.113.7` と `X-Forwarded-For: 198.51.100.9` を付けて送る。このとき `service.start` の 4 番目の引数が `'203.0.113.7'` であること。service.start は AsyncMock で置き換え、DB は使わない。
- T2: ヘッダーが無いときは、試験用クライアントの接続元（`request.client.host`、TestClient では `'testclient'`）が渡ること。
- 変更前のコードで T1 が赤になることを先に確かめる。T2 は変更前も緑でよい（今までの動きを保つ確認）。
- 既存の test_line_import_devices_pg.py:113 は変えない（service の制限の試験）。

## 5. 受入条件

| 基準 | 検証方法 |
|---|---|
| D1: 端末登録は X-Real-IP の接続元で数え、X-Forwarded-For は使わない | T1 が CI で緑（変更前は赤）。T2・既存の試験も緑 |
| D2: 本番で、新しい登録の `created_ip_hash` が本当の接続元のハッシュになる | 反映後、Mac から `/start` を 1 回送る。このとき偽の `X-Forwarded-For: 198.51.100.9` を付け、token_hash は使い捨ての乱数にする。その行の `created_ip_hash` が、同じ要求について nginx が記録した接続元の sha256 と一致し、`sha256("172.20.0.2")` とも `sha256("198.51.100.9")` とも違うことを確かめる |
| D3: 反映後にエラーが増えない | backend の Traceback・ERROR と nginx の 5xx が 0 件のまま |

D2 の確認でできる 1 行は、承認されていない仮の登録で、権限を持たない。10 分で使えなくなり、1 日後の次の登録のときに既存の掃除処理（service :50-52）で消える。手で消すことはしない。

## 6. リスクと対処

- 取り込みスクリプトが携帯回線から登録するときは、接続元が変わることがある。登録は 1 回きりの操作で、上限は接続元ごとに 10 件なので、困らない。
- X-Real-IP が無い経路（nginx を通らない内部からの呼び出し）では、今までどおり `request.client.host` を使う。

## 外部・過去事例の参照と我々への応用

- 過去事例（社内）: S5（PR #4390、docs/handoff/s5-client-ip/）では、ログインの回数制限と監査記録を同じ共通関数に替えた。本番で、偽の X-Forwarded-For を付けても記録の接続元が nginx の接続元と一致することを確かめた（docs/specs/client-ip/kgi.md K3）。今回も同じ関数と同じ確かめ方を使う。
- 外部事例は使わない。新しい仕組みを入れるのではなく、既にある共通関数に、残っていた 1 か所を寄せるだけのため。

## 維持の仕組み

- 見張り: T1（CI の pytest で毎回走る）。
- 正本: 接続元の決め方は backend/app/client_ip.py の 1 つだけ。docs/specs/client-ip/README.md の対象に、端末登録を加える。
- 守り手: 接続元 IP を使う PR を設計する Opus（T1 が赤になった PR は、マージしない）。

## 7. 戻し方

PR を Revert して再デプロイする。DB と設定は変えない。

## 8. 審査（Opus 自己審査・同一 AI）

APPROVE。
- 変えるのは 1 行と import 1 行だけ。使う関数は本番で使われている共通関数で、データの写しを作らない。
- 挙動の変化は §3 のとおり、もとのコードの意図に合わせるもの。
- D2 の本番確認は、権限を持たない仮の 1 行を正規の API で作るだけで、既存の掃除処理で消える。
- 未解決の前提は無い。
