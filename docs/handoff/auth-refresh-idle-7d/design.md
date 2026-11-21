# design: 7 日使わなければログインし直し（ADR-1084）

- 調査: docs/handoff/auth-refresh-idle-7d/recon.md
- ADR: docs/adr/ADR-1084-refresh-idle-7-days.md
- PO 決定: 2026-11-21「2」（7 日使わなければログインし直し）

## 1. 目的

スマホや札を盗まれたとき、使える期間を最長 30 日から「最後に使ってから 7 日」に縮める。ふだん使う人の手間は増やさない。

## 2. 受入条件

| # | 基準 | 検証方法 |
|---|---|---|
| K1 | 最後の取り替えから 7 日を超えた引換券で更新すると 401 | 試験 `test_refresh_rejected_after_idle_7_days`（CI） |
| K2 | 7 日以内（6 日 23 時間）なら更新できる | 試験 `test_refresh_allowed_within_idle_7_days`（CI） |
| K3 | 7 日切れの券を出しても、その組の他の券は失効しない（使い回し扱いにしない） | K1 の試験で `revoked_at IS NULL` の行が残ることを確かめる |
| K4 | 30 日の絶対期限・取り替え・使い回し検知の既存試験がそのまま通る | backend/tests/test_self_auth.py 全件（CI） |
| K5 | 本番反映後、7 日以上前に作られた券での更新成功が 0 件 | reader 鍵で §8 の 1 文を、反映の 1 時間後と 7 日後に流す |
| K6 | 本番反映後 7 日間、ふだん使う口座（1・3）の新しいログインのうち「その直前の券がまだ生きていて 7 日未満」のものが 0 件（＝7 日の決まりで切られていないのにログインし直させられた件が無い） | §8 の 2 文目で、新しいログインごとに直前の券からの間隔と、その券が失効済みか（ログアウト等）を出す。0 件でない行は、別の機械からのログインか本人に確かめる |

## 3. 対象と対象外

- 変更: backend/app/auth/self_tokens.py（定数 1 つ・UPDATE の条件 1 つ）・backend/tests/test_self_auth.py（試験 2 本）。
- 変更しない: 30 日の絶対期限・入館証 15 分・機械の覚え 180 日・画面・DB の形（created_at はある）・回数止め。

## 4. 変更前後

backend/app/auth/self_tokens.py

変更前（:24-25）:
```python
ACCESS_TOKEN_TTL_SECONDS = 900
REFRESH_ABSOLUTE_TTL = timedelta(days=30)
```
変更後:
```python
ACCESS_TOKEN_TTL_SECONDS = 900
REFRESH_ABSOLUTE_TTL = timedelta(days=30)
# 最後の取り替えから、これだけ使われなければ更新を断る（ADR-1084）
REFRESH_IDLE_TTL = timedelta(days=7)
```

変更前（:208-215）:
```python
    result = await db.execute(
        text(
            "UPDATE public.auth_refresh_tokens SET revoked_at = :now, last_used_at = :now "
            "WHERE token_hash = :h AND revoked_at IS NULL AND expires_at > :now "
            "RETURNING user_id, family_id, family_created_at, created_at, trusted_device_id"
        ),
        {"now": now, "h": token_hash},
    )
```
変更後:
```python
    result = await db.execute(
        text(
            "UPDATE public.auth_refresh_tokens SET revoked_at = :now, last_used_at = :now "
            "WHERE token_hash = :h AND revoked_at IS NULL AND expires_at > :now "
            "AND created_at > :idle_cutoff "
            "RETURNING user_id, family_id, family_created_at, created_at, trusted_device_id"
        ),
        {"now": now, "h": token_hash, "idle_cutoff": now - REFRESH_IDLE_TTL},
    )
```

- 券は取り替えのたびに新しく作られる（created_at が今になる）ので、created_at が「最後に使った時刻」と同じ意味になる。
- 7 日切れの券は取り出せず、:217-232 に進む。失効していない券なので組は触らずに None を返す（使い回し扱いにしない＝K3）。呼び出し側は今と同じ 401。

backend/tests/test_self_auth.py の :268 の後（`test_refresh_rejected_after_absolute_30_days` の次）に 2 本足す:

```python
async def test_refresh_rejected_after_idle_7_days(http, db_session, password_hash):
    await _insert_user(db_session, hash_value=password_hash)
    cookie = await _login_cookie(http)
    old = datetime.now(timezone.utc) - self_tokens.REFRESH_IDLE_TTL - timedelta(minutes=1)
    await db_session.execute(text("UPDATE auth_refresh_tokens SET created_at = :t"), {"t": old})
    await db_session.commit()

    assert (await _refresh(http, cookie)).status_code == 401
    live = await _row(db_session, "SELECT count(*) AS n FROM auth_refresh_tokens WHERE revoked_at IS NULL")
    assert live.n == 1  # 使い回し扱いにしない


async def test_refresh_allowed_within_idle_7_days(http, db_session, password_hash):
    await _insert_user(db_session, hash_value=password_hash)
    cookie = await _login_cookie(http)
    recent = datetime.now(timezone.utc) - self_tokens.REFRESH_IDLE_TTL + timedelta(hours=1)
    await db_session.execute(text("UPDATE auth_refresh_tokens SET created_at = :t"), {"t": recent})
    await db_session.commit()

    assert (await _refresh(http, cookie)).status_code == 200
```

## 5. 影響範囲（呼び出し元の全走査）

- `rotate_refresh_token` の呼び出し元: backend/app/routers/auth.py:526 の更新の口だけ（`git grep -n rotate_refresh_token -- backend/app` で 2 件＝定義と呼び出し 1 か所）。
- auth_refresh_tokens を読む他の場所: backend/app/auth/dependencies.py:709（入館証の sid から組を引く。失効だけを見る。入館証は 15 分で切れるので 7 日の判定は要らない）・backend/app/auth/devices.py:308・:328・:357（失効と機械の結び付け。期限は見ない）。どちらも変えない。
- 画面: 更新が 401 になれば今と同じくログイン画面に戻る（frontend/src/lib/auth/selfAuth.ts:199）。

## 6. 代替案

| 案 | 採らない理由 |
|---|---|
| 分・時間単位で画面を自動ログアウト | 入館証は既に 15 分で切れる。何度もログインさせると確かめずに承認する「認証疲れ」で逆に危ない（Microsoft Entra 公式） |
| last_used_at 列を見る | 取り替えで新しい券ができるので、今の券の last_used_at は常に空。created_at で同じ意味になる |
| 期限を設定表に持つ | 30 日・15 分と同じくコードの定数にそろえる。変えるときは ADR と試験を一緒に変える |

## 7. 外部・過去事例の参照と我々への応用

| 誰が | 何を | 数値 | 適用限界 |
|---|---|---|---|
| NIST SP 800-63B-4（2025） | 本人確認レベル 2 の推奨 | 放置 1 時間・全体 24 時間（SHOULD） | 米政府系。民間の義務ではない |
| Auth0 文書 | 引換券の設定例 | 使わない日数 14 日・全体 365 日。使い回し検知と併用 | 設定例。効果の測定値ではない |
| Recorded Future（2025） | 盗まれたログイン情報 | 使える札付き 2 億 7600 万件（31%）・36.4% が 24 時間以内に出回る | 札が盗まれる規模の根拠 |
| NordStellar（2025-04・二次情報） | 盗まれた札の有効率 | 約 940 億件のうち有効 20.55% | 寿命が短いほど盗まれても使えない根拠 |
| Microsoft Entra 文書 | 再ログインの頻度 | 既定 90 日の移動窓・頻繁な再認証は認証疲れを招くと警告 | 件数の数値は無い |

自社で導入前後を測って公表した事例は見つかっていない。効果は §2 の K5・K6 で自社の数で測る。

## 8. 本番での測り方

reader 鍵で流す（1 回 1 文）。

```sql
SELECT count(*) AS n FROM ai_ro.public__auth_refresh_tokens t WHERE t.revoked_at > '<本番反映の時刻>' AND t.last_used_at = t.revoked_at AND t.created_at < t.revoked_at - interval '7 days';
```
（7 日以上前の券で取り替えに成功した数。K5 は 0）

```sql
SELECT f.user_id, f.family_created_at, p.created_at AS prev_created_at, p.revoked_at AS prev_revoked_at, f.family_created_at - p.created_at AS gap FROM (SELECT DISTINCT user_id, family_created_at FROM ai_ro.public__auth_refresh_tokens WHERE user_id IN (1,3) AND family_created_at > '<本番反映の時刻>') f LEFT JOIN LATERAL (SELECT q.created_at, q.revoked_at FROM ai_ro.public__auth_refresh_tokens q WHERE q.user_id = f.user_id AND q.created_at < f.family_created_at ORDER BY q.created_at DESC LIMIT 1) p ON true ORDER BY 2;
```
（K6: 新しいログインごとに、直前の券の作成時刻・失効時刻・間隔。`prev_revoked_at` が空か新しいログインより後で、`gap` が 7 日未満の行が 0 件なら合格）

基準値: 2026-11-21 16:12 JST に生きている券 752 本・うち 7 日以上使われていない 422 本（recon §3）。

## 9. リスクと対処

| リスク | 対処 |
|---|---|
| 毎日自動でログインする仕組みが古い券を使い回していて止まる | recon §3 で口座 87 は毎回新しい組で入ると確かめた。反映後に K5 と毎朝の画面点検の結果を見る |
| 7 日空けた人が「勝手にログアウトされた」と思う | 画面はふだんのログイン画面に戻るだけ。機械の覚え（180 日）は残るので、知らない機械の許可は要らない |
| 時計の扱いの違い | 判定は DB の 1 文の中で `now` と同じ時刻から作った cutoff と比べる |

## 10. 戻し方

この PR を戻す PR（git revert）。DB の変更が無いので、戻すのはコードだけ。

## 11. 維持の仕組み

- 守り手: .github/workflows/test.yml の必須チェック「pytest (SQLite + PostgreSQL RLS)」（K1・K2 の試験が定数から日数を作る）
- 7 日はコードの定数 `REFRESH_IDLE_TTL` の 1 か所だけ。試験は定数から日数を作るので、定数を変えても試験は落ちない（試験が守るのは「切れ目の前後で 401 と 200 が分かれること」と「使い回し扱いにしないこと」）。日数を変えるときは ADR-1084 を同じ PR で直し、合流前の審査役がその一致を見る。
- 30 日・取り替え・使い回しの決まりは既存の試験（test_self_auth.py:217・:230・:257・:270）で引き続き確かめる。

## 12. 審査

- 2026-11-21 16:20 JST クラウドの審査役（Opus・同一AIの別セッション。独立した第二者ではない）: VERDICT: REVISE。§4 のコードと試験 2 本はそのままでよい。必須の直しは文書 2 点。
  - (1) 定数の行番号が 1 つずれていた（実物は self_tokens.py:24-25。:23 は ISSUER）→ recon §2・§4 を直した。
  - (2) K6 の SQL がログイン時刻を並べるだけで、7 日切れかどうか分けられない → 直前の券からの間隔と失効の有無を出す形に直した（§2・§8）。
  - 問題なしと確かめられた点: 既存の取り替え・30 日・パスワード変更・使い回し検知が壊れない／7 日切れの券は使い回し扱いにならない（:219・:224）／試験の補助関数と import がそろっている（:3-18・conftest.py:1506-1519）／更新札を受け入れる道は rotate_refresh_token だけ（auth.py:201 はログアウト・:523 が更新の口）。
- 直しは機械的（行番号と測り方の文）で、コードの設計を変えていないので、Planner が直した形で APPROVE とする。
