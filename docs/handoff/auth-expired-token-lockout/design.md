# 期限切れの札で接続元が止まる件 — 設計（design）

- 現在地: [docs/handoff/auth-expired-token-lockout/recon.md](recon.md)
- 決定記録: docs/adr/ADR-1083-expired-token-not-counted-as-bruteforce.md
- PO の決定: 2026-11-20 「1」（期限が切れただけの札は失敗として数えない。偽の札で何度も試す相手は今までどおり止める）

## 1. 目的

しばらく開いていなかったスマホでアプリを開いても、ログインが「試行回数が多すぎます」で止まらないようにする。乗っ取りの総当たりを止める力は落とさない。

## 2. 成功の条件（PO が ○× で見られる形）

| 番号 | 基準 | 検証方法 |
|---|---|---|
| K1 | 本物で期限だけ切れた札を同じ接続元から 11 回送っても、回数止めの数は 0 のまま（429 にならない） | CI の試験 `test_expired_self_token_is_not_counted_as_failure`（record_auth_failure の呼ばれた回数が 0） |
| K2 | 期限切れでも、他の鍵で署名した札は今までどおり 1 回ずつ数える | CI の試験 `test_expired_token_with_wrong_signature_is_counted`（呼ばれた回数が 1） |
| K3 | 期限切れの札への返事は今までと同じ 401・同じ文言（画面の札の取り直しが今までどおり動く） | CI の試験で status 401・detail が `_INVALID_TOKEN_DETAIL` と一致 |
| K4 | 今ある試験がすべて通る | CI の必須チェックが全部緑 |
| K5 | 本番に入った後、期限切れの札の 401 が 10 回以上続いた接続元が 429 にならない | 本番の記録を reader 鍵で読む（§8 の問い合わせ）。対象が出るまで最長 14 日見る |
| K6 | PO の Android で、2 日ほど開かなかった後に開いても止まらない | PO の目視（止まった／止まらない） |
| K7 | 回数止めが既に効いている接続元には、期限切れの札でも今までどおり 429 | CI の試験 `test_locked_ip_still_gets_429_for_expired_token` |

- K5 の判定: 14 日のうちに対象（10 回以上 401 の接続元）が 1 つ以上出て、どれも 429 が 0 件なら ○。1 つでも 429 があれば ×。14 日で対象が 0 なら K5 は「対象なし」とし、K6 で判定する。

## 3. 対象と対象外

- 対象: backend/app/auth/dependencies.py の `_authenticate_self_token` の札の読み解きの例外の扱いだけ。
- 対象: backend/tests/test_self_auth.py への試験 4 本の追加。
- 対象外: 回数止めの数（10 回・15 分）・`check_auth_rate_limit`・`record_auth_failure` の本体（backend/app/cache.py）。
- 対象外: ログインの口（backend/app/routers/auth.py）・口座の止め（ADR-1013 の 10 回）。
- 対象外: 画面（frontend）。開いた瞬間に古い札で 11 回頼む動きは、この直しで害が無くなる。画面の直しは別の話として残す（§10）。
- 対象外: DB・migration・nginx・deploy の設定。

## 4. 変更前 → 変更後

backend/app/auth/dependencies.py:9（import）

変更前:
```python
from jose import JWTError
```
変更後:
```python
from jose import ExpiredSignatureError, JWTError
```

backend/app/auth/dependencies.py:59-64（`_authenticate_self_token` の頭。:58 は秘密が無いときの raise で、触らない）

変更前:
```python
    try:
        claims = self_tokens.decode_access_token(token)
        user_id = int(claims["sub"])
        issued_at = datetime.fromtimestamp(claims["iat"], timezone.utc)
    except (JWTError, ValueError, KeyError, TypeError, OverflowError, OSError):
        raise await _reject_self_token(client_ip)
```
変更後:
```python
    try:
        claims = self_tokens.decode_access_token(token)
        user_id = int(claims["sub"])
        issued_at = datetime.fromtimestamp(claims["iat"], timezone.utc)
    except ExpiredSignatureError:
        # 署名は自社の鍵で合っていて、期限だけが切れた札（python-jose は署名の確認の後に期限を見る）。
        # 総当たりではないので回数止めに数えない（ADR-1083）。返事は他の失敗と同じ 401。
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_TOKEN_DETAIL)
    except (JWTError, ValueError, KeyError, TypeError, OverflowError, OSError):
        raise await _reject_self_token(client_ip)
```

- `except ExpiredSignatureError` は `except (JWTError, ...)` より前に置く（`ExpiredSignatureError` は `JWTError` の子なので、後ろだと先に拾われる）。
- `HTTPException`・`status`・`_INVALID_TOKEN_DETAIL` は同じファイルに既にある（dependencies.py:7・:44）。新しい定数は作らない。

## 5. 試験（backend/tests/test_self_auth.py の「9. get_current_user の自社トークン」の節に足す）

- 既存の `_current_user`（:346-355）は `record_auth_failure` を AsyncMock にしているが外から見えない。回数を見るため、同じ置き換えをして AsyncMock を返す小さな版 `_current_user_counting(db, token)` を足す（既存の関数は変えない）。
- 札の作り方は既存の `_token`（:358-362）に倣い、`exp` を過去にした版を作る（`iat` は 2 時間前、`exp` は 1 時間前）。
- 試験 1 `test_expired_self_token_is_not_counted_as_failure`: 自社の鍵で署名した期限切れの札 → 401・detail 一致・`record_auth_failure` の呼ばれた回数 0（K1・K3）。
- 試験 2 `test_expired_token_with_wrong_signature_is_counted`: kid は SECRET のもの、署名は OTHER_SECRET の期限切れの札 → 401・呼ばれた回数 1（K2）。
- 試験 3 `test_valid_self_token_bad_signature_still_counted`: 期限内で署名の違う札 → 呼ばれた回数 1（今の守りが落ちていない確かめ）。
- 試験 4 `test_locked_ip_still_gets_429_for_expired_token`: 回数止めが既に効いている（`check_auth_rate_limit` が True）とき、自社の鍵の期限切れの札でも 429（K7。dependencies.py:220-224 の止めが読み解きより前に残ることの確かめ）。`check_auth_rate_limit` を True にする置き換えは試験の中で行い、既存の `_current_user` は変えない。

## 6. 1 か所にすること（SSOT）

- 回数止めの数と期間は backend/app/cache.py:307-308 の 1 か所のまま。
- 401 の文言は dependencies.py:44 の `_INVALID_TOKEN_DETAIL` を使う。新しい文言を作らない。
- 期限切れかどうかの判断は札の部品（python-jose）の例外だけに任せる。自分で exp を比べない。

## 7. 危ないことと対処

| 危ないこと | 対処 |
|---|---|
| 偽の札が期限切れとして扱われ、数えられなくなる | 部品は署名を確かめてから期限を見る（recon §5・jwt.py:159 → :174）。kid が合わない札は読み解く前に JWTError（self_tokens.py:111-120）。試験 2 で確かめる |
| 盗んだ本物の古い札で何度も試される | 期限切れの札では中に入れない（401 のまま）。数えなくても得るものは無い |
| 部品の版が上がり、確かめる順番が変わる | 試験 2 が落ちて気づける（CI） |
| 期限切れの札を大量に送られる | 1 件ごとに署名の計算だけで終わる。DB は読まない（読み解きで止まるため）。普通の頼みの数の制限（nginx・RateLimitMiddleware）は今のまま |

## 8. 本番での測り方（K5）

reader 鍵で次を流す（1 文）。対象の接続元が出たら、その後 15 分に 429 が 0 件であることを見る。

```sql
SELECT left(md5(client_ip),8) AS ip, min(created_at) AS first_at, count(*) AS n401 FROM ai_ro.public__auth_events WHERE event_type='auth_failure' AND status_code=401 AND path NOT IN ('/api/v1/auth/refresh','/api/v1/auth/login') AND created_at > '<本番反映の時刻>' GROUP BY client_ip, date_trunc('hour',created_at) HAVING count(*) >= 10 ORDER BY 2;
```

- 記録には札が期限切れかどうかの列が無い。そのため K5 は「10 回以上 401 になった後に 429 が出ていない」で見る。期限切れだったかは §recon 3 と同じく、更新札の組の作成時刻で確かめる。
- 基準値: 反映前 30 日の 429 は 8 件（1 回・2026-11-20）。

## 9. 戻し方

この PR を戻す PR を出す（git revert）。DB・設定の変更が無いので、戻すのはコードだけ。

## 10. 残すこと（この直しの外）

- 画面が開いた瞬間に古い札で 11 回頼む動き。札の取り直しを先にすれば 401 自体が減る。別の話として PO に出す。
- ログアウトしたのが人の操作か画面の自動か（23:39:26）は確かめていない。

## 11. 外部・過去事例の参照と我々への応用

- OWASP の Authentication Cheat Sheet「Account Lockout」節（https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html・2026-11-21 に curl で本文を確認）は、止める仕組みを「決まった回数のログインの失敗」で数えるとし、止める仕組みが他の利用者を締め出す手段にならないよう注意を求めている。決まった数値は示していない。
- 我々への応用: 期限が切れただけの正規の札はログインの失敗ではない。数えると正規の利用者を締め出す（今回の事故）。よって数える対象から外す。同じ節は「失敗の数は接続元でなく口座に結びつけるべき」とも書く。口座の止めは ADR-1013 で既にある。接続元の止めを口座の止めへ寄せるかは、この直しの範囲外（§10 に足さず、PO に出す材料として記録だけ残す）。
- 自社の過去の事例: ADR-127（2026-06）は、正規の利用者が回数止めの巻き添えで 429 になった事故の直し。今回も正規の利用者が止まった同じ種類の事故で、数える対象を正しくする直しにした。
- 数値の事例は使わない。この直しの効果は自社の本番の記録（K5）で測る。

## 12. 維持の仕組み

- 守り手: CI の試験 3 本（K1・K2・K7）。部品の版上げや書き換えで順番が崩れると落ちる。
- 決定は ADR-1083 に残す。回数止めを触る次の人は FEATURE-INDEX から辿らず grep で見つける（`record_auth_failure` の近くにコメントで ADR 番号を書く）。

## 13. 実装カード（クラウドの Sonnet へ渡す）

- 作業場所: `bash scripts/new-worktree.sh release/auth-expired-token-not-bruteforce --claude` で作られた場所（このブランチ）。
- 変えるファイル: §4 の 2 か所と §5 の試験 4 本だけ。他のファイルを変えたら止めて報告。
- 確かめ: `cd backend && pytest tests/test_self_auth.py -q` の生出力を残す。試験 1〜4 が通り、既存も全部通ること。
- 想定の分岐:
  - 試験 2 が「呼ばれた回数 0」で落ちる → 部品の順番が想定と違う。実装を止めて報告（設計の前提が崩れる）。
  - `_current_user` の置き換えで回数が取れない → `patch(..., new=AsyncMock())` を `as` で受ける形にする。既存の試験の形は変えない。
- 終わったら commit（日本語の要約・Co-Authored-By 行）して push。PR は作らない（Opus が作る）。

## 14. 審査の記録

- 2026-11-21 00:34〜00:36 JST、クラウドの審査役（architect・Opus 5.5・新規起動・読むだけ）が枝 `eb1de05f` を審査。結果 **APPROVE**（必須の指摘 0・推奨 4）。同一系統の AI による審査で、独立の第二者審査ではない。
- 照合: recon・design・ADR の引用行は実物とすべて一致。違い 1 件（§4 の :58-64 → :59-64）。
- python-jose 3.5.0: 取り寄せた中身で jwt.py:159 署名 → :174 `_validate_claims` → :496-497 期限の順を確認。`ExpiredSignatureError` を出すのは jwt.py:331 の 1 か所だけ。python3.12 の venv で実際に札を作り、自社の鍵の期限切れ → `ExpiredSignatureError`、別の鍵の期限切れ → `JWTError`（署名が合わない）を確認。
- 漏れ: SSE は `get_current_user` を通るので一緒に直る。ログアウトと閲覧者の道はもともと数えない。
- 推奨 4 件はすべて取り込んだ: ①§4 の行番号 ②§8 の SQL の除外を /auth/refresh と /auth/login だけにした（/auth/devices などの数える道を落とさないため）③K5 で対象が出ないときの判定を §2 に書いた ④回数止めが効いているときの 429 の試験（試験 4・K7）を足した。
- 未確認（審査役）: pytest の実行（実装の後に CI と実装役で流す）・本番の秘密の値。
