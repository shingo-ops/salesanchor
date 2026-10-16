# KGI — 接続元 IP の決め方（client-ip）

> この文書は何か：「接続元 IP を偽れない」を、○×で判定できる目標に置き換えたものです。

親: [README.md](README.md)　／　あるべき姿: [ideal-state.md](ideal-state.md)

**状態: PO 承認済み（2026-10-16、PO「y」）**。区分 B（backend のみ。`migrations/`・`deploy.yml`・本番 `scripts/` を含まない）。

## 背景（2026-10-16 の事実。根拠は [../../handoff/s5-client-ip/recon.md](../../handoff/s5-client-ip/recon.md)）

backend は接続元 IP を決める同じ関数を 4 か所に写して持ち、どれも X-Forwarded-For（利用者が自由に書ける値）の先頭を信用している。X-Forwarded-For に毎回違う値を付ければ、ログインとパスワード再設定の失敗回数制限（10 回で 15 分ロック）をすり抜けて総当たりでき、監査記録の IP も偽の値になる。本番の入口は nginx だけで、nginx はすべての backend 向け経路で X-Real-IP を本当の接続元で上書きしている。

## KGI

| ID | 目標（○×で判定） | 判定方法 | 現在値（2026-10-16） |
|---|---|---|---|
| K1 | 接続元 IP を決める関数が backend に 1 つだけ（写し 0）で、X-Forwarded-For を読む箇所が 0 | `git grep -niE "headers\.get\(\s*[\"']x-forwarded-for" backend/app` が 0 件、`git grep -nE "def (_?get_client_ip\|_get_client_ip_from_request\|_client_ip)\(" backend/app` が 1 件 | 読む箇所 4・関数 5（4 写し＋viewer.py の 1） |
| K2 | X-Forwarded-For に偽の値を付けてログインに失敗し続けると、偽の値を毎回変えても回数制限で止まる | CI の試験が緑（偽の値を毎回変えて 10 回失敗→11 回目が 429） | 試験なし（今のコードでは止まらない） |
| K3 | 本番で偽の X-Forwarded-For を付けた要求 1 件の、監査記録に残る IP が本当の接続元（偽の値ではない） | 本番 DB `public.auth_events` の client_ip を、同じ要求の nginx 記録の接続元と照合 | 反映前に同じ手順で測る（偽の値が残ることを確認） |
| K4 | 反映後、401・429 が反映前より増えない | 反映前後の nginx 記録の 401・429 件数（1 時間あたり） | 基準: 2026-10-16 04:58Z〜08:11Z の nginx 記録 3591 行で 401 が 41・429 が 0 |

（表の中の `\|` は表の区切りと区別するための書き方。実際に打つときは `|` にする。）

## 運用方針

- 対象は backend の接続元 IP の決め方だけ。nginx の設定・WAF（前段の防御サービス）・端末登録（line_import_devices.py）の IP の扱いは変えない（[design.md](../../handoff/s5-client-ip/design.md) の対象外）。
- 新しい場所で接続元 IP が要るときは、この 1 つの関数を使う（写しを作らない）。
