# 段B カードの事実の生の出力（S=origin/main 22c4c221d64932bbd17ba71f292c2e89e18a5b75 で読んだ・2026-11-02 Claude Opus）

本番の数の欄は reader 鍵の 2026-11-02 の結果（users・端末の表は権限なしで読めない）。

```text
== compose AUTH_
29:          memory: 256M
52:          memory: 128M
81:      - META_OAUTH_REDIRECT_URI=${META_OAUTH_REDIRECT_URI:-}
134:      # ADR-1013 便4b: 自社ログインへの切り替え。.env に AUTH_PROVIDER=self が入る。
136:      - AUTH_PROVIDER=${AUTH_PROVIDER:-firebase}
137:      - AUTH_JWT_SECRET=${AUTH_JWT_SECRET:-}
139:      - AUTH_VIEWER_JWT_SECRET=${AUTH_VIEWER_JWT_SECRET:-}
149:      # 締切 AUTH_DEVICE_BOOTSTRAP_CUTOFF が空なら、ログイン中だった機械の自動登録（D4）をしない。
150:      - AUTH_DEVICE_APPROVAL=${AUTH_DEVICE_APPROVAL:-off}
151:      - AUTH_DEVICE_BOOTSTRAP_CUTOFF=${AUTH_DEVICE_BOOTSTRAP_CUTOFF:-}
155:      - WEBPUSH_VAPID_PRIVATE_KEY=${WEBPUSH_VAPID_PRIVATE_KEY:-}
156:      - WEBPUSH_VAPID_PUBLIC_KEY=${WEBPUSH_VAPID_PUBLIC_KEY:-}
157:      - WEBPUSH_VAPID_SUBJECT=${WEBPUSH_VAPID_SUBJECT:-}
181:          memory: 512M
202:        VITE_FIREBASE_AUTH_DOMAIN: ${VITE_FIREBASE_AUTH_DOMAIN}
205:        VITE_AUTH_PROVIDER: ${VITE_AUTH_PROVIDER:-firebase}
219:          memory: 128M
316:          memory: 768M
356:          memory: 128M
407:          memory: 256M
== deploy AUTH_/WEBPUSH
286:              -e '/^META_OAUTH_REDIRECT_URI=/d' \
316:              -e '/^AUTH_PASSWORD_RESET_ALLOWLIST=/d' \
317:              -e '/^AUTH_VIEWER_JWT_SECRET=/d' \
318:              -e '/^AUTH_PROVIDER=/d' \
319:              -e '/^AUTH_JWT_SECRET=/d' \
320:              -e '/^VITE_AUTH_PROVIDER=/d' \
327:              -e '/^WEBPUSH_VAPID_PRIVATE_KEY=/d' \
328:              -e '/^WEBPUSH_VAPID_PUBLIC_KEY=/d' \
329:              -e '/^WEBPUSH_VAPID_SUBJECT=/d' \
339:            # ADR-1019 段2: 閲覧者のトークンの鍵（viewer_tokens.py が読む）。アプリの鍵 AUTH_JWT_SECRET とは別の値
344:            META_OAUTH_REDIRECT_URI='${{ secrets.META_OAUTH_REDIRECT_URI }}'
374:            AUTH_VIEWER_JWT_SECRET='${{ secrets.AUTH_VIEWER_JWT_SECRET }}'
375:            AUTH_PROVIDER='self'
376:            AUTH_JWT_SECRET='${{ secrets.AUTH_JWT_SECRET }}'
377:            VITE_AUTH_PROVIDER='self'
384:            WEBPUSH_VAPID_PRIVATE_KEY='${{ secrets.WEBPUSH_VAPID_PRIVATE_KEY }}'
385:            WEBPUSH_VAPID_PUBLIC_KEY='${{ secrets.WEBPUSH_VAPID_PUBLIC_KEY }}'
386:            WEBPUSH_VAPID_SUBJECT='${{ secrets.WEBPUSH_VAPID_SUBJECT }}'
== cli
backend/app/cli/__init__.py
backend/app/cli/issue_trusted_device.py
== backend env read
origin/main:backend/app/auth/devices.py:57:    """AUTH_DEVICE_APPROVAL=off|enforce（既定 off。off はログインの止め方が今と同じ）。"""
origin/main:backend/app/auth/devices.py:58:    return "enforce" if os.getenv("AUTH_DEVICE_APPROVAL", "off").strip().lower() == "enforce" else "off"
origin/main:backend/app/auth/devices.py:66:    """AUTH_DEVICE_BOOTSTRAP_CUTOFF（UTC の固定値）。空・読めないときは None（D4 の登録をしない）。"""
origin/main:backend/app/auth/devices.py:67:    raw = os.getenv("AUTH_DEVICE_BOOTSTRAP_CUTOFF", "").strip()
origin/main:backend/app/auth/devices.py:73:        logger.warning("AUTH_DEVICE_BOOTSTRAP_CUTOFF を読めない（D4 の登録をしない）")
origin/main:backend/app/cli/issue_trusted_device.py:5:印の生の値を標準出力に1行だけ出す（ログには出さない）。GitHub の秘密 SMOKE_E2E_DEVICE_TOKEN へ
origin/main:backend/app/routers/auth.py:382:    AUTH_DEVICE_APPROVAL=off（既定）は今までと同じ。enforce のとき、知らない機械は 202 で止める（ADR-1055）。
origin/main:backend/tests/test_new_device_approval.py:84:    monkeypatch.delenv("AUTH_DEVICE_APPROVAL", raising=False)
origin/main:backend/tests/test_new_device_approval.py:85:    monkeypatch.delenv("AUTH_DEVICE_BOOTSTRAP_CUTOFF", raising=False)
origin/main:backend/tests/test_new_device_approval.py:91:    monkeypatch.setenv("AUTH_DEVICE_APPROVAL", "enforce")
origin/main:backend/tests/test_new_device_approval.py:581:    monkeypatch.setenv("AUTH_DEVICE_APPROVAL", "enforce")
origin/main:backend/tests/test_new_device_approval.py:582:    monkeypatch.setenv("AUTH_DEVICE_BOOTSTRAP_CUTOFF", (created + timedelta(seconds=1)).isoformat())
origin/main:backend/tests/test_new_device_approval.py:600:    monkeypatch.setenv("AUTH_DEVICE_APPROVAL", "enforce")
origin/main:backend/tests/test_new_device_approval.py:601:    monkeypatch.setenv("AUTH_DEVICE_BOOTSTRAP_CUTOFF", created.isoformat())
origin/main:backend/tests/test_new_device_approval.py:613:    monkeypatch.setenv("AUTH_DEVICE_APPROVAL", "enforce")
origin/main:backend/tests/test_new_device_approval.py:1024:    monkeypatch.setenv("AUTH_DEVICE_APPROVAL", "enforce")
origin/main:backend/tests/test_new_device_approval.py:1025:    monkeypatch.setenv("AUTH_DEVICE_BOOTSTRAP_CUTOFF", "2020-01-01T00:00:00+00:00")
origin/main:backend/tests/test_new_device_approval.py:1039:    monkeypatch.setenv("AUTH_DEVICE_APPROVAL", "enforce")
origin/main:backend/tests/test_new_device_approval.py:1040:    monkeypatch.setenv("AUTH_DEVICE_BOOTSTRAP_CUTOFF", (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat())
origin/main:backend/tests/test_new_device_approval.py:1080:    monkeypatch.setenv("AUTH_DEVICE_BOOTSTRAP_CUTOFF", "2026-11-01T12:00:00Z")
origin/main:backend/tests/test_new_device_approval.py:1082:    monkeypatch.setenv("AUTH_DEVICE_BOOTSTRAP_CUTOFF", "garbage")
origin/main:backend/tests/test_new_device_approval.py:1088:    monkeypatch.setenv("AUTH_DEVICE_APPROVAL", "ENFORCE")
origin/main:backend/tests/test_new_device_approval.py:1090:    monkeypatch.setenv("AUTH_DEVICE_APPROVAL", "whatever")
origin/main:frontend/api-contract/openapi.json:40628:        "description": "自社ログイン。失敗理由は区別せず 1 種類の文言で返す。\n\nAUTH_DEVICE_APPROVAL=off（既定）は今までと同じ。enforce のとき、知らない機械は 202 で止める（ADR-1055）。",
== login.ts
fatal: ambiguous argument 'mainests/prod-check/login.ts': unknown revision or path not in the working tree.
Use '--' to separate paths from revisions, like this:
'git <command> [<revision>...] -- [<file>...]'
== prod-ui-check env
32:        env:
100:        env:
104:          SMOKE_E2E_EMAIL: ${{ secrets.SMOKE_E2E_EMAIL }}
105:          SMOKE_E2E_PASSWORD: ${{ secrets.SMOKE_E2E_PASSWORD }}
111:        env:
150:        env:
153:          SMOKE_E2E_EMAIL: ${{ secrets.SMOKE_E2E_EMAIL }}
154:          SMOKE_E2E_PASSWORD: ${{ secrets.SMOKE_E2E_PASSWORD }}
== page-speed login
fatal: ambiguous argument 'mainests/prod-check/page-speed.spec.ts': unknown revision or path not in the working tree.
Use '--' to separate paths from revisions, like this:
'git <command> [<revision>...] -- [<file>...]'
== login.ts
/**
 * 本番の画面点検: ログイン手順（この 1 ファイルに閉じ込める）
 *
 * ログイン切替（ADR-1013）のときはこのファイルだけ差し替える。
 * 認証情報は環境変数から読み、値はログに出さない。
 */

import { expect, type Page } from "@playwright/test";

/** 点検先。今の点検の config と速さの記録がここを読む（fixtures.ts は同じ式を自前で持つ） */
export const BASE_URL = process.env.PROD_CHECK_BASE_URL || "https://app.salesanchor.jp";

// 入口（nginx）は /api/v1/auth/ を 1 つの IP から 1 分 10 件（6 秒に 1 件）・まとめて 5 件までに制限する（nginx/nginx.conf:6・:145）。
// 速さの記録（page-speed.spec.ts）が login の前に呼び、前回から 8 秒あける（6 秒に 1 件より遅くする）。今の点検は fixtures.ts の間隔を使う。
// login は 1 回で最大 3 件（refresh 401・login・refresh）を使う。超過は 5 件のまとめ枠が吸収する。
// 最初の 1 回も、このファイルを読み込んだ時刻から数える（再試行は新しい作業者で最初からやり直すため）。
const AUTH_PACE_MS = 8_000;
let lastAuthAt = Date.now();

export async function authPace(): Promise<void> {
  const wait = lastAuthAt + AUTH_PACE_MS - Date.now();
  if (wait > 0) await new Promise((resolve) => setTimeout(resolve, wait));
  lastAuthAt = Date.now();
}

// 秘密情報が未登録のときは null を返す（呼び出し側が test.skip にする）。値は出力しない。
// 今の点検は fixtures.ts の authedPage が、速さの記録は test.skip が飛ばす。
export function creds(): { email: string; password: string } | null {
  const email = process.env.SMOKE_E2E_EMAIL;
  const password = process.env.SMOKE_E2E_PASSWORD;
  if (!email || !password) return null;
  return { email, password };
}

export async function login(page: Page, email: string, password: string): Promise<void> {
  // 点検のブラウザでは顔・指紋（パスキー）を使えない扱いにし、ログイン直後の登録案内を出さない（本番に記録を残さない・ADR-1013）
  await page.addInitScript(() => {
    Object.defineProperty(globalThis, "PublicKeyCredential", { value: undefined, configurable: true });
  });
  // 点検のブラウザでは「予備の合言葉を作りませんか」の小窓を出さない（残りがある扱いにする・本番に記録を残さない・ADR-1055）
  await page.context().route("**/api/v1/auth/recovery-codes/status", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ remaining: 10 }) }),
  );
  await page.goto("/login");
  await page.getByLabel("メールアドレス").fill(email);
  await page.getByLabel("パスワード", { exact: true }).fill(password);
  await page.getByRole("button", { name: "ログイン", exact: true }).click();
  await page.waitForURL(
    (url) => url.pathname === "/" || url.pathname === "/dashboard",
    { timeout: 30_000 },
  );
}

// 右上のアバター（ユーザーメニューを開く）→「サインアウト」→ 確認ダイアログの「サインアウト」
export async function signOut(page: Page): Promise<void> {
  await page.getByRole("button", { name: "ユーザーメニューを開く" }).click();
  await page.getByRole("button", { name: "サインアウト" }).first().click();
  await expect(page.getByText("サインアウトしますか？")).toBeVisible();
  // 確認ダイアログは DOM の後ろ側にあるので最後のボタンを押す
  await page.getByRole("button", { name: "サインアウト" }).last().click();
  await page.waitForURL((url) => url.pathname === "/login", { timeout: 30_000 });
}
== page-speed login
12:import { BASE_URL, authPace, creds, login } from "./login";
480:    await login(page, c.email, c.password);
== fixtures login
11:import { creds, login } from "./login";
21:// （refresh 401・login・refresh）。6 秒 × 3 = 18 秒 + 余裕で、test の始まり同士を 20 秒空ける。
35:      const context = await browser.newContext({ baseURL: BASE_URL });
39:      await login(page, c.email, c.password);
== who uses SMOKE_E2E_PASSWORD / auth/login in workflows+tests
origin/main:.github/workflows/prod-ui-check.yml
origin/main:scripts/security_check.sh
origin/main:scripts/tests/nginx-case-api-guard.sh
origin/main:tests/prod-check/login.ts
origin/main:tests/prod-check/page-speed.spec.ts
origin/main:tests/prod-check/playwright.config.ts
origin/main:tests/prod-check/prod-ui.spec.ts
== cli body
"""点検専用の人などに、いつもの機械の印を1つ発行する（ADR-1055 D12）。

使い方: python -m app.cli.issue_trusted_device --user-id <id> --label prod-ui-check

印の生の値を標準出力に1行だけ出す（ログには出さない）。GitHub の秘密 SMOKE_E2E_DEVICE_TOKEN へ
画面に出さずに直接流す（値は記録しない）。DB には sha256 だけを置く（created_via='cli'）。
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import secrets
import sys

from sqlalchemy import text

from app.database import AsyncSessionLocal


async def issue(user_id: int, label: str) -> str:
    raw = secrets.token_urlsafe(32)
    async with AsyncSessionLocal() as db:
        exists = (
            await db.execute(text("SELECT 1 FROM public.users WHERE id = :id AND is_active"), {"id": user_id})
        ).first()
        if exists is None:
            raise SystemExit("user not found or inactive")
        await db.execute(
            text(
                "INSERT INTO public.user_trusted_devices (user_id, token_hash, label, created_via, created_at, last_used_at) "
                "VALUES (:uid, :h, :label, 'cli', now(), now())"
            ),
            {"uid": user_id, "h": hashlib.sha256(raw.encode()).digest(), "label": label[:100]},
        )
        await db.commit()
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="いつもの機械の印を1つ発行する")
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--label", default="cli", help="機械の呼び名")
    args = parser.parse_args(argv)
    raw = asyncio.run(issue(args.user_id, args.label))
    sys.stdout.write(raw + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
== auth/login hits
origin/main:scripts/security_check.sh:191:    STATUS=$(curl -so /dev/null -w "%{http_code}" -X POST "$TARGET_URL/api/v1/auth/login" -H "Content-Type: application/json" -d '{"email":"test@test.com","password":"test"}' 2>/
origin/main:scripts/tests/nginx-case-api-guard.sh:110:    / /api/v1/auth/login /api/v1/ops/case/pending "/api/v1/ops/case/${UUID_LOWER}/ticket" \
origin/main:tests/prod-check/playwright.config.ts:11: *   SMOKE_E2E_EMAIL / SMOKE_E2E_PASSWORD  点検用の人の認証情報（CI の secrets）
origin/main:tests/prod-check/prod-ui.spec.ts:116:      (r) => r.request().method() === "POST" && new URL(r.url()).pathname === "/api/v1/auth/login",
== other password logins (python/js clients)
origin/main:backend/tests/test_viewer_isolation.py
origin/main:scripts/security_check.sh
origin/main:tests/prod-check/page-speed.spec.ts
origin/main:tests/prod-check/prod-ui.spec.ts
== security_check caller
== users
db error: InsufficientPrivilege pgcode=42501

== live families
db error: InsufficientPrivilege pgcode=42501

== trusted devices
db error: InsufficientPrivilege pgcode=42501

== passkeys
db error: UndefinedTable pgcode=42P01

```
