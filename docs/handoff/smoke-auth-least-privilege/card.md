# 実装カード — smoke 認証の最小権限化

> この文書は何か：ADR-1017 のコード変更の指示書です（ADR-113 様式）。本番作業は含みません。

- 設計: docs/handoff/smoke-auth-least-privilege/design.md
- 対象ADR: ADR-1017・ADR-136（危険PRのGO）
- 危険便: はい（`backend/app/auth/` を含む）。GO は PO 単独（番号付き「GO #PR番号」）
- 担当: 実装 Sonnet／審査 Opus

## 1. 目的

smoke 認証が super admin を返さないようにし、非ASCII入力の 500 を 401 に直し、成立を記録する。

## 2. 触るファイル

1. `backend/app/auth/dependencies.py`
2. 新設 `backend/tests/test_smoke_auth_least_privilege.py`

## 3. 変更の要点（file:line は origin/main 基準の変更前）

| 場所 | 変更前 | 変更後 |
|---|---|---|
| import（:1-3） | logging なし | `import logging`・モジュール `logger` を追加 |
| 一致判定（:145） | `secrets.compare_digest(token, ...)` を直書き | 小関数 `_is_smoke_token` に移し、TypeError／ValueError は False |
| 解決後（:147-157） | ユーザーが居れば返す | 居なければ 401。`is_super_admin` が真なら 401。成立時に logger.info を 1 行（トークン非記録）して返す |

## 4. 触らない範囲

`.github/`・`migrations/`・`frontend/`・Firebase／自社トークン経路（:160 以降）・env 読込（:41-42）。

## 5. 想定分岐

| 場合 | 動き |
|---|---|
| env が空 | 経路は不活性（従来どおり） |
| トークン不一致／非ASCII | 通常の検証経路へ進み 401 |
| 解決先が居ない | 401 |
| 解決先が super admin | 401（ガード） |
| 解決先が一般ユーザー | 従来どおり通る＋ログ 1 行 |

## 6. 確認

`cd backend && python3 -m pytest tests/test_smoke_auth_least_privilege.py -q` が全緑。

## 7. 本番手順（GO 待ち・本カードでは実行しない）

design.md の 2-2・2-3・3 を参照。
