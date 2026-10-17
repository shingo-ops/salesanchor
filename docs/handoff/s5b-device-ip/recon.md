# 現在地 — 端末登録の接続元 IP（S5 の別便）

**日付**: 2026-10-17　**基準**: origin/main e455886b5　**生出力**: /tmp/CC報告ファイル/device-ip/recon/（Sonnet が調べ、Opus がコードと本番の値を直接確かめた）

## 1. コード（事実）

- backend/app/routers/line_import_devices.py:33-36 `POST /tcg/line-devices/start` は、接続元を `request.client.host if request.client else 'unknown'` で決めて `service.start` に渡す（:35 のコメントは「XFF を信用しない」）。
- backend/app/services/line_import_devices.py:39-62 `start` はこの値を sha256 にする（`digest(peer)`、:20）。値の使い道は 2 つある。
  - :43-49 の回数制限。直近 1 時間で「全体 30 件以上」または「同じ `created_ip_hash` が 10 件以上」なら 429 `device_registration_limited` を返す。
  - :55-60 の保存先 `public.line_import_devices.created_ip_hash`。
- 列の定義は migrations/20260912_160000_line_import_devices.sql の `created_ip_hash VARCHAR(64) NOT NULL`。生の IP は保存しない。
- backend/app で接続元 IP を直接読むのは、この :36 だけ（client_ip.py を除く。recon/direct.txt）。ほかはすべて共通関数 backend/app/client_ip.py `get_client_ip` を使う（dependencies.py・audit.py・rate_limit.py・session_guard.py・auth.py・viewer.py。recon/users.txt）。
- `get_client_ip` の決め方: X-Real-IP を IP として検証して使い、無ければ `request.client.host`、それも無ければ "unknown"。X-Forwarded-For は読まない（client_ip.py:12-21）。

## 2. 本番（事実）

- nginx は、backend 向けの 23 の経路すべてで `proxy_set_header X-Real-IP $remote_addr;` を設定している（recon/nginx.txt）。
- backend から見た `request.client.host` は nginx の内部の住所 172.20.0.2。
- `public.line_import_devices` は 1 行で、2026-09-12 06:00:10Z の登録。その `created_ip_hash` の先頭 12 桁 `5b69f20f75ab` は、`sha256("172.20.0.2")` の先頭 12 桁と一致した（recon/prod-db.txt と、Opus の手元での再計算）。
- 上の 2 点から、本番では誰が登録しても同じ「1 人」として数えられている。
  - 「同じ接続元から 10 件」の制限は、実際には「全員合わせて 1 時間 10 件」として効いている。
  - 記録からは、どこから登録したかが分からない。
- nginx の記録に残る接続元は、利用者の公開の住所（例: 2026-10-17 01:15Z の確認アクセスは 49.128.148.145。/tmp/CC報告ファイル/s6-get-audit/fix1-prod/nginx-get.txt）で、nginx の前に別の中継は見えていない。

## 3. 呼び出し元

- Mac・Termux の取り込みスクリプトだけ。tools/termux-line-import/device_session.py:13 と client.py:22 が呼ぶ。
- frontend からは呼ばない（openapi.json に定義があるだけ。recon/callers.txt）。

## 4. 試験

- backend/tests/test_line_import_devices_pg.py:113-120 は、`svc.start` を直接呼んで、10 回の後に 429 になることを確かめている。
- ルーターがどの値を接続元として渡すかを確かめる試験は無い（recon/tests.txt）。

## 5. 決まりごと

- docs/specs/client-ip/README.md:13 は、この箇所を「挙動が変わるため別便」として対象外にしている。docs/handoff/s5-client-ip/design.md:66 も同じ。
- docs/adr と docs/adr/FEATURE-INDEX.md に、端末登録や接続元 IP を扱う ADR は無い（recon/adr.txt）。
- 関係する ADR は、client-ip 仕様が挙げる ADR-127（回数制限）と、GO 委任の ADR-1003。
