# 設計 追補1 — S6 ログインに失敗した閲覧（401・403）を数えない

**日付**: 2026-10-17　**元の設計**: [docs/handoff/s6-get-access-audit/design.md](design.md)　**現在地**: [docs/handoff/s6-get-access-audit/recon.md](recon.md) ＋ 本書 §1　**ADR**: ADR-1003（GO 委任）　**PO 承認**: 2026-10-17「y」（本書 §2 の直し方）

## 1. 見つかった食い違い（本番で確かめた事実）

- 元の設計の審査（review-opus.md 指摘 3）では「認証の無い GET は数えない」としていた。
- しかし実装（PR #4411）の `_record_read_access` は、応答の状態を見ずに `_count_read_and_check(user_email)` を呼ぶ（backend/app/middleware/audit.py:304）。email は署名を確かめずに読む（:67-78）。
- 2026-10-17 00:05Z の確認: 架空の email を入れた署名なしのトークンで GET /api/v1/companies を 1 回送った。応答は 401 だった。それでも本番 Redis に `bulk_read:010a3bf501f51381:2986992` が count=1・TTL 659 でできた（/tmp/CC報告ファイル/s6-get-audit/k3/probe.txt）。
- 影響: 他人の email を書いた偽のアクセスを 501 回送ると、その人の名前で bulk_read_alert を 1 行出させられる。遮断はしないため、影響は誤った警告 1 行だけ。

## 2. 直し方

`_record_read_access` の中で、回数を数えるのを `status_code not in _AUTH_FAILURE_CODES`（401・403、既存の定数 :38）のときだけにする。

```python
            if status_code not in _AUTH_FAILURE_CODES and await _count_read_and_check(user_email):
```

data_export の記録は今のまま（`status_code < 400` で、すでに 401・403 を除いている）。

触らない: ほかの関数、書込の検知（`_check_and_record_bulk_export` も署名検証なしで数えるが、書込は 401 でも data_write を記録する既存の仕様で、S6 の範囲外）、migrations、frontend。

## 3. 試験（backend/tests/test_get_access_audit.py に足す）

- T6: Redis の incr が 501 を返す状態で、401 を返す GET を送る → incr が呼ばれず、INSERT は 0 回。403 も同じ。
- T4（既存）: 200 の GET では従来どおり bulk_read_alert が 1 行入る（緑のまま）。

変更前のコードで T6 が赤になることを先に確かめる。

## 4. 受入条件

| 基準 | 検証方法 |
|---|---|
| F1: 401・403 になった閲覧は回数に数えられない | T6 が CI で緑（変更前は赤）。反映後、本番で同じ確認アクセス（架空の email・署名なし）を 1 回送り、401 が返ること、その email の `bulk_read:` キーが 0 件であることを確かめる |
| F2: ログイン済みの閲覧は今までどおり数えられる | T4 が緑。反映後、本番 Redis の `bulk_read:*` のキーが、利用者の閲覧があれば 1 件以上ある |
| F3: 反映後にエラーが増えない | backend の Traceback・ERROR と nginx の 5xx が 0 件のまま |

## 5. 戻し方

PR を Revert して再デプロイする。DB と設定は変えない。

## 6. 審査（Opus 自己審査・同一 AI）

APPROVE。変えるのは条件の 1 行だけで、使う定数は既存のもの。元の設計の意図（ログイン済みだけ数える）に実装を合わせる変更で、新しい判断は無い。
