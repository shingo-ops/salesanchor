#!/usr/bin/env python3
"""QA Smoke Firebase パスワード更新スクリプト (ADR-038 one-shot rotation)

使い方 (backendコンテナ内):
  docker exec -i \\
    -e QA_ADMIN_PASSWORD="..." \\
    -e QA_STAFF_PASSWORD="..." \\
    -e QA_VIEWER_PASSWORD="..." \\
    astro-webapp-backend-1 \\
    python3 /tmp/qa/update_firebase_qa_passwords.py

目的: GitHub Secrets に登録済みの新パスワードを Firebase Auth ユーザーへ反映する。
      パスワード生成・bcrypt 計算はローカルで実施済み。
      このスクリプトは Firebase 側への書き込みのみ行う。
"""
from __future__ import annotations

import os
import sys

import firebase_admin
from firebase_admin import auth as fb_auth
from firebase_admin import credentials
from firebase_admin import exceptions as fb_exc

QA_EMAIL_ENV: dict[str, str] = {
    "qa-admin@salesanchor.jp":  "QA_ADMIN_PASSWORD",
    "qa-staff@salesanchor.jp":  "QA_STAFF_PASSWORD",
    "qa-viewer@salesanchor.jp": "QA_VIEWER_PASSWORD",
}


def _init_firebase() -> None:
    if firebase_admin._apps:
        return
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/app/firebase-credentials.json")
    if os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    else:
        firebase_admin.initialize_app()


def main() -> None:
    _init_firebase()

    for email, env_key in QA_EMAIL_ENV.items():
        password = os.environ.get(env_key)
        if not password:
            print(f"[FATAL] env var {env_key!r} is not set", file=sys.stderr)
            sys.exit(1)
        try:
            user = fb_auth.get_user_by_email(email)
        except fb_exc.NotFoundError:
            print(f"[FATAL] Firebase user not found: {email}", file=sys.stderr)
            sys.exit(1)
        fb_auth.update_user(user.uid, password=password)
        print(f"[OK] Firebase password updated for {email}", file=sys.stderr)

    print("[DONE] All Firebase QA user passwords updated", file=sys.stderr)


if __name__ == "__main__":
    main()
