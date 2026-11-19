# 作業票 6b: RLS を飛び越せる役の許可一覧を固定する（ADR-1063 便6 の後）

## なぜ
便6 の毎日点検の初回（2026-11-19 09:05 JST、本番 celery-worker の記録）は黄。
理由は許可一覧 BYPASSRLS_ROLES が空のため（判定は backend/app/tasks/tenant_isolation_daily_check.py の judge、空なら黄）。
初回の観測で RLS を飛び越せる役は 2 件: ai_unmask_owner, jarvis。PO は 2026-11-19 に 2 件とも登録する案に「1」。

## 触るファイル（これ以外は触らない）
1. backend/app/ops/tenant_rls_allowlist.py の `BYPASSRLS_ROLES: dict[str, str] = {}` の 1 行だけ。
2. .claude-pipeline/active-work.d/release-tenant-rls-pin-bypass-roles.md（登録）
3. docs/handoff/tenant-owner-login-approval/card-6b.md（この作業票）

## 変更後（そのまま書く）
```python
# 2026-11-19 09:05 JST の本番の毎日点検（ADR-1063 便6）の初回で見えた 2 件。PO 2026-11-19「1」で固定。
BYPASSRLS_ROLES: dict[str, str] = {
    "jarvis": (
        "移行（migration）を流す役。superuser（ADR-1018 Context）。"
        "アプリと Celery は salesanchor_app で接続しており、この役では接続しない。"
    ),
    "ai_unmask_owner": (
        "値を返す DB 関数 ops_case.unmask_fetch の持ち主。NOLOGIN。"
        "関数の中で許可した行が RLS で 0 件にならないよう BYPASSRLS を付ける（ADR-1024 の BYPASSRLS の例外・ADR-1052）。"
    ),
}
```
モジュール冒頭の説明文の「（便6 で初回の観測を PO に報告してから固定する）」は「（2026-11-19 に初回の観測で固定）」に直してよい（同じファイル内のみ）。

## 触らない
judge・SQL・試験・CI の設定。試験は ROLES / TABLES を試験の中で定義しており、この一覧の中身に依らない（backend/tests/test_tenant_isolation_daily_check.py:20-21、a8 は judge を同じ一覧で呼び比べるだけ）。

## 確かめ方
- V1: `cd backend && ruff check app/ops/tenant_rls_allowlist.py && ruff format --check app/ops/tenant_rls_allowlist.py` が 0。
- V2: `python -c "from app.ops.tenant_rls_allowlist import BYPASSRLS_ROLES as r; assert set(r)=={'jarvis','ai_unmask_owner'} and all(v.strip() for v in r.values())"`（backend で実行）が成功。
- V3: judge に初回の本番の事実（bypass_roles=['ai_unmask_owner','jarvis']、tables=許可一覧の 11 件、current_super/bypass=False）を渡すと ("green", [], [])。
- V4: `pytest backend/tests/test_tenant_isolation_daily_check.py -q` が失敗 0（実 PostgreSQL の試験は skip 可・CI で確かめる）。
- V5: `git diff origin/main --name-only` が上の 3 件だけ。

## 想定分岐
- V3 が緑にならない → 止めて BLOCKED: と生出力を返す。一覧や judge を推測で直さない。
- 本番で役が増えた・減った → 翌朝の点検が赤/参考で知らせる。この票の範囲外。

## 受入（PO が見る形）
| 基準 | 検証方法 |
|---|---|
| 翌朝 09:05 の管理者用 Discord の点検が「緑」 | 本番 celery-worker の記録の color が green |
| 一覧に無い係が増えたら赤 | 試験 a4（既存）が通る |

## 戻し方
この PR を revert すると一覧は空に戻り、点検は黄に戻る。DB・本番データは変えない。
