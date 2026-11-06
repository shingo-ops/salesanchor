# card: 便2 追加1 本物の Redis を使う締め出しの試験に、自社の札を持たせる

状態: カード発行（Opus、2026-11-05）。親カード: [card-2.md](./card-2.md)。設計: [design.md](./design.md) §5-2（一時記憶を使うのは自社の札だけ）。
担当: クラウドの Sonnet。触ってよいのは `backend/tests/test_real_redis_lockout.py` の 1 ファイルだけ。PR は作らない（Opus が PR #5145 に載せる）。
基準: 枝 `release/firebase-removal-bin2` の `87d75572a6ae7367e5c52d2ddd99e143f5e02508`。

## 読んだ節（docs/handoff/design-partner-card-ops/guards/）
- guards/00-common.md: 全コマンドを作業場所の cd から始める・出力に上限（tail）・sleep しない・プレースホルダを残さない。○
- guards/03-file.md・guards/05-pr.md: 触るファイルは 1 つだけと書いた。PR は Opus が作る（Sonnet は push まで）。○
- guards/10-executor.md: 散文で組み立てを頼まない（§1 に変更前と変更後の文を書いた）。○

## なぜ
PR #5145 の CI（run 41961019067・job pytest-run-internal）で 1 件だけ赤になった。
`FAILED tests/test_real_redis_lockout.py::TestRealRedisLockout::test_s1_cached_user_bypasses_ip_lock - AssertionError: 巻き添え発生 (S1): IP ロック中にキャッシュ済みトークンが 429 で遮断された。`
原因: 便2 で、一時記憶（Redis）を使うのは発行元が自社（iss=salesanchor）の札だけになった（`backend/app/auth/dependencies.py:184`）。この試験の `CACHED_TOKEN` は JWT の形をしていない文字列で、発行元が無い。このため一時記憶を見ずに回数の確認へ進み、429 になった。親カード §2-14 (9) で `test_security_hardening.py` に入れた直しと同じ種類。この試験は本物の Redis が無いと飛ばされるため、手元の実行では見えなかった。
S3 は今は通っているが、一時記憶を通らず自社以外の札として 401 で返っているだけで、確かめたいこと（一時記憶ありで通る）を確かめていない。同じ直しで S3 も本来の道を通る。

## 0. 実装前点検（外れたら実装せず BLOCKED: で止まる）
- P1 `git diff --quiet 87d75572a6ae7367e5c52d2ddd99e143f5e02508 HEAD -- backend scripts .github frontend` が終了 0（基準の後はこのカードの追加だけ）。
- P2 `sed -n '72p' backend/tests/test_real_redis_lockout.py` が `CACHED_TOKEN = "cached-valid-token-abc123"`。
- P3 `sed -n '25,27p' backend/tests/test_real_redis_lockout.py` が `import hashlib`・`import json`・`import os` の 3 行（24 行目は空行。Opus が 6c9a95038 で実測）。

## 1. 変更の中身（`backend/tests/test_real_redis_lockout.py` だけ）
(a) 25 行目 `import hashlib` の直前に 1 行足す（24 行目の空行はそのまま残す）。
変更前:
```python
import hashlib
import json
```
変更後:
```python
import base64
import hashlib
import json
```

(b) 72 行目（(a) の後は 73 行目）を置き換える。
変更前:
```python
CACHED_TOKEN = "cached-valid-token-abc123"
```
変更後:
```python
_JWT_HEADER = b'{"alg":"HS256","typ":"JWT"}'


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _unsigned_jwt(claims: dict) -> str:
    """署名なしの JWT の形の札（振り分けは iss だけを見るため、署名は要らない）。"""
    return f"{_b64(_JWT_HEADER)}.{_b64(json.dumps(claims).encode())}.sig"


# 一時記憶を使うのは自社の札（iss=salesanchor）だけ（docs/handoff/firebase-removal/design.md §5-2）
CACHED_TOKEN = _unsigned_jwt({"iss": "salesanchor", "email": "shingo@example.com", "sub": "1"})
```

ほかの行（`UNCACHED_TOKEN`・S1〜S3 の本体・`_request_with_ip`）は変えない。

## 2. 手順
手順1 枝を取る
    cd ~ && git clone https://github.com/shingo-ops/salesanchor.git sa && cd sa && git checkout release/firebase-removal-bin2 && git log --oneline -1 | tail -1

手順2 P1〜P3 を流し、結果をそのまま報告に貼る
    cd ~/sa && git diff --quiet 87d75572a6ae7367e5c52d2ddd99e143f5e02508 HEAD -- backend scripts .github frontend; echo "P1 exit=$?"
    cd ~/sa && sed -n '72p' backend/tests/test_real_redis_lockout.py | tail -1
    cd ~/sa && sed -n '25,27p' backend/tests/test_real_redis_lockout.py | tail -3

手順3 部品を入れる（Python 3.12 の venv `/tmp/v312`。py312-guard の決まり）
    cd ~/sa && python3.12 -m venv /tmp/v312 && /tmp/v312/bin/python --version | tail -1
    cd ~/sa/backend && /tmp/v312/bin/python -m pip install -q -r requirements.txt -r requirements-dev.txt 2>&1 | tail -3

手順4 §1 の変更をする

手順5 札の形を確かめる（iss が salesanchor と読めること）
    cd ~/sa/backend && ENVIRONMENT=test /tmp/v312/bin/python -c "from tests.test_real_redis_lockout import CACHED_TOKEN; from app.auth.self_tokens import peek_issuer; print(peek_issuer(CACHED_TOKEN))" 2>&1 | tail -3
期待: `salesanchor`

手順6 本物の Redis で 3 つの試験を流す（Redis が入れられる場合だけ）
    cd ~/sa && (command -v redis-server || (sudo apt-get install -y -q redis-server >/dev/null 2>&1 && command -v redis-server)) | tail -1
    cd ~/sa && redis-server --port 6399 --requirepass testpass123 --daemonize yes | tail -1
    cd ~/sa/backend && REDIS_URL=redis://:testpass123@localhost:6399/0 ENVIRONMENT=test /tmp/v312/bin/python -m pytest -q -p no:cacheprovider --no-cov tests/test_real_redis_lockout.py 2>&1 | tail -15
期待: `3 passed`。redis-server が入れられないときは、手順6 を飛ばしたと報告に書いて先へ進む（CI で確かめる）。

手順7 ruff
    cd ~/sa/backend && /tmp/v312/bin/python -m ruff check tests/test_real_redis_lockout.py 2>&1 | tail -10

手順8 変わったファイルを確かめる（`backend/tests/test_real_redis_lockout.py` の 1 つだけであること）
    cd ~/sa && git status --short | tail -5 && git diff --stat | tail -3

手順9 記録して送る
    cd ~/sa && git add backend/tests/test_real_redis_lockout.py && git commit -q -m "test(auth): give the real-redis lockout test a self-issued token (firebase-removal bin2)" && git log --oneline -1 | tail -1
    cd ~/sa && git push origin release/firebase-removal-bin2 2>&1 | tail -3

## 3. 想定される分かれ道
- P1〜P3 のどれかが外れた → 実装せず `BLOCKED: P番号 と見えたもの`。
- 手順5 が `salesanchor` でない → `BLOCKED: 札の形` と出力。
- 手順6 で 3 passed にならない → 最後の 30 行を報告して `BLOCKED: 締め出しの試験`。
- 手順8 で他のファイルが変わっている → 戻してから進む。戻せなければ `BLOCKED: 余計な変更`。

## 受領確認（最初の報告の 1 行目に書く）
RECEIVED firebase-removal-bin2-fix1 HEAD=（git rev-parse HEAD の 40 桁）

## 4. 報告の形
- 1 行目: 受領確認。
- 分かれ道に当たって停止したときは、どの分かれ道かと見えたものを書き、最後の行を `BLOCKED: 理由` にする。
- 手順2・5・6・7・8・9 の出力をそのまま貼る。
- 秘密の値は貼らない。
- 最後の行: `DONE` か `BLOCKED: 理由`。

END OF CARD
