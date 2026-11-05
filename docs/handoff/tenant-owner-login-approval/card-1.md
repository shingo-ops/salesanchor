# card: 便1 スタッフ登録の重複の文言で他社在籍が分からないようにする（K7）

状態: カード発行（Opus、2026-11-06）。PO の実装承認は 2026-11-06「1」（このまま作り始める）。設計: docs/handoff/tenant-owner-login-approval/design.md 便1（設計の PR #5167 で取り込み中。このカードだけで作業できるように中身を下に全部書く）。
担当: クラウドの Sonnet。触ってよいのは下の「1. 触るファイル」だけ。本番・GitHub の secret には触らない。PR は作らない（Opus が作る）。
基準: origin/main `335389444e533120702df63fc94702fa4bc27c11`。下の行番号はすべてこの時点のもの。行がずれていたら、行番号ではなく「変更前」の文で場所を探す（同じ文が 2 か所あれば BLOCKED: で止まる）。

## 読んだ節（docs/handoff/design-partner-card-ops/guards/）
- guards/00-common.md: 全コマンドを作業場所の cd から始める・出力に上限（tail）・sleep しない・プレースホルダを残さない。○
- guards/03-file.md・guards/05-pr.md: 触るファイルを §1 で全部挙げた。消すファイルは無い。PR は Opus が作る（Sonnet は push まで）。○
- guards/10-executor.md: 散文で組み立てを頼まない（§2 に変更前と変更後の文を書いた）。○

## 受領確認（最初の報告の 1 行目に書く）
RECEIVED tenant-owner-bin1 HEAD=（git rev-parse HEAD の 40 桁）

## 0. 実装前点検（外れたら実装せず BLOCKED: で止まる）
- P1 枝 `release/tenant-owner-bin1-staff-message` を origin から取り、`docs/handoff/tenant-owner-login-approval/card-1.md` が在ること。
- P2 `git diff --quiet 335389444e533120702df63fc94702fa4bc27c11 HEAD -- backend/app/routers/staff.py backend/tests/test_staff_create_users.py` が終了 0。
- P3 `grep -n "他の会社で使われています\|スタッフはすでに登録されています" backend/app/routers/staff.py` が 87 行と 96 行の 2 件だけ。
- P4 `grep -rn "他の会社で使われています\|スタッフはすでに登録されています" backend frontend/src` が P3 の 2 件だけ（ほかの場所で同じ文を使っていない）。

## 1. 触るファイル

書き換える:
1. `backend/app/routers/staff.py`（2-1）
2. `backend/tests/test_staff_create_users.py`（2-2）

触らない: 上に挙げた以外のすべて。特に `frontend/`（画面はサーバーの文をそのまま出す。`frontend/src/pages/staff/StaffPage.tsx:170`）、`migrations/`、`docs/`。上のファイルの中でも、書いていない行は 1 文字も変えない。409 の番号・登録の判定の順番・SELECT の文は変えない。

## 2. 変更の中身

### 2-1. `backend/app/routers/staff.py`

(a) `_PLACEHOLDER_PREFIX = "TMP-"`（61 行）の次の行に、空行 1 つと次の 2 行を足す:
```
# 他社か自社かを言い分けない（ADR-1063 便1・K7）。他社在籍を文言から分からないようにする
EMAIL_UNAVAILABLE_DETAIL = "このメールアドレスは登録できません。別のメールアドレスを使ってください。"
```

(b) 85〜88 行の変更前:
```
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="このメールアドレスは他の会社で使われています",
            )
```
変更後（detail の行だけ変える）:
```
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=EMAIL_UNAVAILABLE_DETAIL,
            )
```

(c) 94〜97 行の変更前:
```
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="このメールアドレスのスタッフはすでに登録されています",
            )
```
変更後（detail の行だけ変える）:
```
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=EMAIL_UNAVAILABLE_DETAIL,
            )
```

(d) 73〜77 行の docstring の「同テナントで名簿あり → 409 /\n    別テナント → 409」は変えない（番号は同じのため）。

### 2-2. `backend/tests/test_staff_create_users.py`

(a) 自社の重複の試験 `test_existing_user_with_roster_returns_409` の変更前（95 行）:
```
    assert res.status_code == 409, res.text
    assert await _count(db_session, "users") == users_before
```
変更後（間に 2 行足す）:
```
    assert res.status_code == 409, res.text
    assert res.json()["detail"] == EMAIL_UNAVAILABLE_DETAIL
    assert "他の会社" not in res.json()["detail"]
    assert await _count(db_session, "users") == users_before
```

(b) 他社の試験 `test_user_in_other_tenant_returns_409_and_creates_nothing` の変更前（115 行）:
```
    assert "他の会社" in res.json()["detail"]
```
変更後:
```
    assert res.json()["detail"] == EMAIL_UNAVAILABLE_DETAIL
    assert "他の会社" not in res.json()["detail"]
```

(c) 定数の取り込み: ファイル先頭の import の並びの最後の `from` 行の次に 1 行足す:
```
from app.routers.staff import EMAIL_UNAVAILABLE_DETAIL
```
（手順3 で import の並びを表示してから足す。すでに `from app.routers.staff import ...` の行があれば、その行の名前の並びに `EMAIL_UNAVAILABLE_DETAIL` を足し、新しい行は作らない）

## 3. 手順

手順1 枝を取る
    cd ~ && git clone https://github.com/shingo-ops/salesanchor.git sa && cd sa && git checkout release/tenant-owner-bin1-staff-message && git log --oneline -1 | tail -1

手順2 実装前点検 P1〜P4 を流し、結果をそのまま報告に貼る
    cd ~/sa && git rev-parse HEAD | tail -1
    cd ~/sa && ls docs/handoff/tenant-owner-login-approval/card-1.md | tail -1
    cd ~/sa && git diff --quiet 335389444e533120702df63fc94702fa4bc27c11 HEAD -- backend/app/routers/staff.py backend/tests/test_staff_create_users.py; echo "P2 exit=$?"
    cd ~/sa && grep -n "他の会社で使われています\|スタッフはすでに登録されています" backend/app/routers/staff.py | tail -5
    cd ~/sa && grep -rn "他の会社で使われています\|スタッフはすでに登録されています" backend frontend/src | tail -5

手順3 試験ファイルの import の並びを見る
    cd ~/sa && grep -n "^import\|^from" backend/tests/test_staff_create_users.py | tail -20

手順4 §2 の変更をする（2-1 → 2-2 の順）

手順5 差分を確かめる
    cd ~/sa && git diff | tail -80

手順6 残りの文字の確かめ（期待: 1 つめは 0 行、2 つめは staff.py の 3 行＝定数 1・使う所 2）
    cd ~/sa && grep -rn "他の会社で使われています\|スタッフはすでに登録されています" backend frontend/src | tail -5
    cd ~/sa && grep -n "EMAIL_UNAVAILABLE_DETAIL" backend/app/routers/staff.py | tail -5

手順7 形の確かめ
    cd ~/sa && python3 -m py_compile backend/app/routers/staff.py backend/tests/test_staff_create_users.py && echo "compile OK" | tail -1

手順8 試験を流す（DB が要る。流せなければ流せない理由を報告して先へ進む。最後の判定は CI の pytest）
    cd ~/sa/backend && python3 -m pytest tests/test_staff_create_users.py -q 2>&1 | tail -15

手順9 記録して送る
    cd ~/sa && git add backend/app/routers/staff.py backend/tests/test_staff_create_users.py && git commit -q -m "fix(staff): do not reveal other-tenant email on staff create (ADR-1063 bin1)" && git log --oneline -1 | tail -1
    cd ~/sa && git push origin release/tenant-owner-bin1-staff-message 2>&1 | tail -3

## 4. 想定される分かれ道

BLOCKED: に入ったら、その場で作業を停止し、それまでの出力と §5 の形の報告を返して終わる（直さずに先へ進まない・別のやり方を試さない）。

- P1〜P4 のどれかが外れた → 実装せず `BLOCKED: P番号 と見えたもの`。
- 手順6 で期待と違う行が出た → 行をそのまま報告して `BLOCKED: 残り`。
- 手順7 が失敗 → 出力を報告して `BLOCKED: compile`。
- 手順8 で DB に繋がらない・依存が無いなど試験を始められない → 最後の 15 行を報告し「試験は CI で確かめる」と書いて手順9 へ進む。
- 手順8 で試験が始まり、赤がある → 赤の試験名と最後の 15 行を報告して `BLOCKED: 試験名`（直さない）。
- 変更前の文が見つからない・2 か所ある → `BLOCKED: ファイル名と行 変更前の文が一致しない`。
- push が拒まれた → 出力の最後の 3 行を報告して `BLOCKED: push`（force はしない）。

## 5. 報告の形

- 1 行目: 受領確認（`RECEIVED tenant-owner-bin1 HEAD=…`）。
- 手順2・3・5・6・7・8・9 の出力（tail の範囲）をそのまま貼る。
- §4 の分かれ道に入ったら、どれに入ったかと見えたもの。
- 秘密の値・鍵・パスワードは貼らない。
- 最後の行: `DONE` か `BLOCKED: 理由`。

END OF CARD
