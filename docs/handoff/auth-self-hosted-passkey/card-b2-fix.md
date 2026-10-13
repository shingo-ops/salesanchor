# 実装カード 便2 追補 — 便2 審査の LOW 3 件を直す（backend のみ・既定は Firebase のまま）

> この文書は何か：ADR-1013 便2（#4231）のセキュリティ審査で出た軽い指摘 3 件を、便4（切替）より前に直す指示書です。本番は既定の `AUTH_PROVIDER=firebase` なので、利用者から見た動きは何も変わりません。

- 設計: docs/handoff/auth-self-hosted-passkey/design.md §3・§4
- 元の指示書: docs/handoff/auth-self-hosted-passkey/card-b2.md
- PO の実装承認: 2026-10-14 チャット「y」（便3 カード作成と LOW 3 件の修正を進める問いへの回答）
- 危険便: いいえ（コードのみ。migrations・deploy・compose・secrets に触れない）
- 担当: 実装 Sonnet／コード審査 Fable（セキュリティ観点込み）／マージ Opus

## 1. 範囲

入れる: 下の 3 件だけ。入れない: それ以外のリファクタ・文言変更・新機能。

## 2. 前提の事実（2026-10-14・origin/main d3e832701 基準）

| # | 事実 | 出典 |
|---|---|---|
| F1 | Cookie を付けるときは `httponly=True`・`secure=self_tokens.cookie_secure()`・`samesite="strict"`・`path=REFRESH_COOKIE_PATH` | `backend/app/routers/auth.py:198-208` |
| F2 | Cookie を消すときは `response.delete_cookie(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)` だけで、secure・httponly・samesite を渡していない（消すための Set-Cookie の属性が付けたときと食い違う） | `backend/app/routers/auth.py:211-212` |
| F3 | `datetime.fromtimestamp(claims["iat"], timezone.utc)` が try の外にある。iat が範囲外の大きな整数・数値の文字列・範囲外の負の値のとき OverflowError・TypeError・ValueError が出て、401 ではなく 500 になる。iat が無い・数値に直せない文字列のときは、python-jose が先に弾くため（`require_iat: True`・`backend/app/auth/self_tokens.py:131`）修正前から 401（2026-10-14 Fable 審査で訂正。実測は審査の報告による） | `backend/app/auth/dependencies.py:105` |
| F4 | テストが `http.post(..., cookies={"sa_refresh": cookie})` の「リクエストごとの cookies 指定」を使っている（httpx 0.28 で非推奨） | `backend/tests/test_self_auth.py:203`・`:306` |
| F5 | 依存の版: starlette==1.3.1・httpx==0.28.1 | `backend/requirements.txt:2`・`:15` |

## 3. 触るファイル（これ以外は触らない）

- `backend/app/routers/auth.py`
- `backend/app/auth/dependencies.py`
- `backend/tests/test_self_auth.py`
- `docs/handoff/auth-self-hosted-passkey/card-b2-fix.md`（このカード）

## 4. 作り方

### 4.1 routers/auth.py（F2）

変更前:

```python
def _clear_refresh_cookie(response: Response | JSONResponse) -> None:
    response.delete_cookie(self_tokens.REFRESH_COOKIE_NAME, path=self_tokens.REFRESH_COOKIE_PATH)
```

変更後:

```python
def _clear_refresh_cookie(response: Response | JSONResponse) -> None:
    response.delete_cookie(
        self_tokens.REFRESH_COOKIE_NAME,
        path=self_tokens.REFRESH_COOKIE_PATH,
        secure=self_tokens.cookie_secure(),
        httponly=True,
        samesite="strict",
    )
```

着手前に、starlette 1.3.1 の `Response.delete_cookie` が `secure`・`httponly`・`samesite` を受け取ることを、その版を入れた環境の `inspect.signature` で確かめ、出力を報告に貼る。受け取らない場合は実装せず `BLOCKED:` で止まる。

### 4.2 dependencies.py（F3）

変更前（:96-107 の該当部分）:

```python
    try:
        claims = self_tokens.decode_access_token(token)
        user_id = int(claims["sub"])
    except (JWTError, ValueError, KeyError, TypeError):
        raise await _reject_self_token(client_ip)
    ...
    changed_at = self_tokens._as_utc(row.password_changed_at)
    issued_at = datetime.fromtimestamp(claims["iat"], timezone.utc)
```

変更後:

```python
    try:
        claims = self_tokens.decode_access_token(token)
        user_id = int(claims["sub"])
        issued_at = datetime.fromtimestamp(claims["iat"], timezone.utc)
    except (JWTError, ValueError, KeyError, TypeError, OverflowError, OSError):
        raise await _reject_self_token(client_ip)
    ...
    changed_at = self_tokens._as_utc(row.password_changed_at)
```

（`issued_at` を使う比較 `if changed_at is not None and issued_at < changed_at:` はそのまま。DB 照会の順番は変えない。）

### 4.3 test_self_auth.py（F4 と F2・F3 のテスト）

- `:203`・`:306` の `cookies={"sa_refresh": cookie}` をやめ、送る直前に `http.cookies.set("sa_refresh", cookie, domain="app.salesanchor.jp", path=<REFRESH_COOKIE_PATH の値>)` で設定してから送る形にする。前のテストの Cookie が残らないよう、関数の最初で `http.cookies.clear()` を呼ぶ。path は `self_tokens.REFRESH_COOKIE_PATH` を参照し、文字列を直書きしない。httpx 0.28.1 の `Cookies.set` の引数は、その版の `inspect.signature` で確かめて報告に貼る。
- テストを 2 件足す:
  1. logout（または Cookie を消す経路）の応答の `set-cookie` ヘッダに `httponly`・`samesite=strict`・`max-age=0` が含まれること。`AUTH_COOKIE_SECURE` が真の設定のときは `secure` も含まれること（既存テストの設定の切り替え方に合わせる）
  2. 正しい秘密鍵で署名したが `iat` が無いトークン、`iat` が文字列のトークンの 2 通りで、保護された API が 401 を返すこと（500 にならないこと）。トークンの作り方は既存テストの作り方に合わせる
- 既存のテストは消さない・弱めない。

## 5. 確かめ方（担当が実行し、生の最終行を報告に貼る）

1. 修正前の main で、4.3 の追加テスト 2 件が失敗することを先に確かめる（TDD の順）。失敗の最終行を貼る
2. 修正後: `cd backend && python -m pytest -q tests/test_self_auth.py` が全件成功
3. `cd backend && python -m pytest -q tests -k "auth"` の最終行（PostgreSQL 実機必須の error は件数とテスト名を書く）
4. `git diff origin/main...HEAD --name-only` が §3 の 4 ファイルだけ

## 6. 分岐ごとの対処

| 状況 | 対処 |
|---|---|
| starlette 1.3.1 の delete_cookie が secure 等を受け取らない | 実装しない。`BLOCKED:` と signature の出力を返す |
| 追加テストが修正前でも通る（失敗しない） | テストが的外れ。実装に進まず `NEEDS_DECISION:` で返す |
| §3 以外のファイルを触る必要が出た | 止まって `NEEDS_DECISION:` |
| フックに止められた | 言い換えて再試行しない。`BLOCKED:` で返す |

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| Cookie を消す Set-Cookie に httponly・samesite=strict（secure 設定時は secure）が付く | 追加テスト 1 |
| iat が不正な自社トークンで 500 ではなく 401 | 追加テスト 2 |
| テストが非推奨の per-request cookies を使わない | `git grep -n "cookies=" backend/tests/test_self_auth.py` が 0 件 |
| 既存の挙動が変わらない | test_self_auth.py 全件成功・CI 全件成功 |
| 本番の挙動が変わらない | 既定 firebase のまま。反映後に login（正しい形の本文）が 404・logout（トークンなし）が 401 |

## 8. PR

- ブランチ: release/auth-stage2-low-fixes（origin/main 起点）
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に recon・設計・このカード・ADR-1013・触るファイル 4 件を書く
- 危険パスを含まないため GO 記録は不要。マージは Opus が CI・Fable 審査を確かめてから行う
