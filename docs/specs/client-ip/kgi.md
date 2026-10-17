# KGI — 接続元 IP の決め方（client-ip）

> この文書は何か：「接続元 IP を偽れない」を、○×で判定できる目標に置き換えたものです。

親: [README.md](README.md)　／　あるべき姿: [ideal-state.md](ideal-state.md)

**状態: PO 承認済み（2026-10-16、PO「y」）**。区分 B（backend のみ。`migrations/`・`deploy.yml`・本番 `scripts/` を含まない）。

## 背景（2026-10-16 の事実。根拠は [../../handoff/s5-client-ip/recon.md](../../handoff/s5-client-ip/recon.md)）

backend は接続元 IP を決める同じ関数を 4 か所に写して持ち、どれも X-Forwarded-For（利用者が自由に書ける値）の先頭を信用している。X-Forwarded-For に毎回違う値を付ければ、ログインとパスワード再設定の失敗回数制限（10 回で 15 分ロック）をすり抜けて総当たりでき、監査記録の IP も偽の値になる。本番の入口は nginx だけで、nginx はすべての backend 向け経路で X-Real-IP を本当の接続元で上書きしている。

## KGI

| ID | 目標（○×で判定） | 判定方法 | 現在値（2026-10-16 反映後） | 判定 |
|---|---|---|---|---|
| K1 | 接続元 IP を決める関数が backend に 1 つだけ（写し 0）で、X-Forwarded-For を読む箇所が 0 | `git grep -niE "headers\.get\(\s*[\"']x-forwarded-for" backend/app` が 0 件、`git grep -nE "def (_?get_client_ip\|_get_client_ip_from_request\|_client_ip)\(" backend/app` が 1 件 | main（52199cdf8）で読む箇所 0・関数 1（backend/app/client_ip.py:12）。反映前は読む箇所 4・関数 5 | ○ |
| K2 | X-Forwarded-For に偽の値を付けてログインに失敗し続けると、偽の値を毎回変えても回数制限で止まる | CI の試験が緑（偽の値を毎回変えて 10 回失敗→11 回目が 429） | backend/tests/test_client_ip.py の T5 が CI 緑（PR #4390）。変更前のコードでは 11 回目が 401（`assert 401 == 429` で赤） | ○ |
| K3 | 本番で偽の X-Forwarded-For を付けた要求 1 件の、監査記録に残る IP が本当の接続元（偽の値ではない） | 本番 DB `public.auth_events` の client_ip を、同じ要求の nginx 記録の接続元と照合 | 反映後 2026-10-16 19:17 JST: client_ip=49.128.148.145、nginx の接続元 49.128.148.145 と一致。反映前 18:24 JST は 203.0.113.77（偽の値） | ○ |
| K4 | 反映後、401・429 が反映前より増えない | 反映前後の nginx 記録の 401・429 件数（1 時間あたり） | 反映後 10:15Z〜11:19Z（約 1.07 時間・1068 行）: 401 が 7（約 6.5/時。うち 6 は /design/、1 は K3 の測定要求）・429 が 0・5xx 0。基準 04:58Z〜08:11Z（約 3.2 時間・3591 行）: 401 が 41（約 12.8/時）・429 が 0 | ○ |

（表の中の `\|` は表の区切りと区別するための書き方。実際に打つときは `|` にする。）

## 運用方針

- 対象は backend の接続元 IP の決め方だけ。nginx の設定・WAF（前段の防御サービス）は変えない。端末登録（line_import_devices.py）は追補 S5b で同じ関数に寄せた。
- 新しい場所で接続元 IP が要るときは、この 1 つの関数を使う（写しを作らない）。

## 追補 S5b — 端末登録の接続元（2026-10-17、PO「y」）

端末登録 `POST /api/v1/tcg/line-devices/start` は `request.client.host`（本番では nginx の内部の住所 172.20.0.2）で回数制限と記録をしていたため、全員が同じ 1 つの接続元として数えられていた（[recon](../../handoff/s5b-device-ip/recon.md)）。PR #4437 で `get_client_ip` に寄せた（[設計](../../handoff/s5b-device-ip/design.md)）。

| ID | 目標（○×で判定） | 判定方法 | 現在値（2026-10-17 反映後） | 判定 |
|---|---|---|---|---|
| D1 | 端末登録は X-Real-IP の接続元を使い、X-Forwarded-For を使わない | CI の試験 T1・T2 が緑 | backend/tests/test_line_import_devices.py の 2 本を含む pytest-run-internal が最終 HEAD 5be1251e9 で pass。変更前の赤は未観測（試験だけの状態の CI は試験側の誤りで別の理由で落ち、その後の積み直しは自動判定に止められたため） | ○ |
| D2 | 本番で新しい登録の created_ip_hash が本当の接続元のハッシュになる | 偽の X-Forwarded-For と X-Real-IP を付けた /start 1 件の created_ip_hash を、nginx 記録の接続元の sha256 と照合 | 2026-10-17 04:38:02Z: nginx の接続元 49.128.148.145 の sha256（先頭 dc3d8b7acbc4）と一致。172.20.0.2（5b69f20f75ab）・198.51.100.9・198.51.100.10 のいずれとも不一致。この行は承認されていない仮の登録で、10 分で失効し、既存の掃除処理で消える | ○ |
| D3 | 反映後にエラーが増えない | backend の Traceback・ERROR、nginx の 5xx 件数 | 反映前 03:30Z: 0・0。反映後 04:39Z: 0・0。取り込みスクリプトの /import は反映後も 200 | ○ |
