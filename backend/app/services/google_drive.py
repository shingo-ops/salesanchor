"""Google Drive 連携サービス（サービスアカウント方式）。

API連携 > Googleドライブ の動作確認用。サービスアカウントの鍵を環境変数から
読み込み、共有ドライブ (Shared Drive) にファイルを保存する。

ベストプラクティス:
  - 鍵はコード/リポジトリには置かず、シークレット env で注入する。
    本番は base64 化した鍵 (GOOGLE_DRIVE_SA_JSON_B64) を推奨。
    サービスアカウント鍵 JSON は改行を含むため、base64 で 1 行化すると
    .env / GitHub Secret / heredoc に安全に渡せる。ローカル等では生の JSON
    文字列 (GOOGLE_DRIVE_SA_JSON) も可。
  - サービスアカウントはストレージ quota を持たないため My Drive 直書きは
    不可。必ず「共有ドライブ」へ書き込む (supportsAllDrives=True)。
    共有ドライブ側にこのサービスアカウントのメールをメンバー招待しておくこと。

変更履歴:
  2026-06-06: 初版（API連携 Googleドライブ 保存テスト）
"""

from __future__ import annotations

import base64
import binascii
import io
import json
import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

# 共有ドライブへのファイル作成に必要なスコープ
_SCOPES = ["https://www.googleapis.com/auth/drive"]

_ENV_JSON = "GOOGLE_DRIVE_SA_JSON"
_ENV_JSON_B64 = "GOOGLE_DRIVE_SA_JSON_B64"

# Drive のフォルダ/共有ドライブ URL から ID を取り出す
_FOLDER_URL_RE = re.compile(r"/folders/([a-zA-Z0-9_-]+)")
_BARE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{10,}$")


def _load_sa_info() -> Optional[dict]:
    """サービスアカウント鍵を dict で返す。未設定/不正なら None。"""
    raw_b64 = os.getenv(_ENV_JSON_B64)
    if raw_b64:
        try:
            decoded = base64.b64decode(raw_b64).decode("utf-8")
            return json.loads(decoded)
        except (binascii.Error, ValueError, UnicodeDecodeError) as e:
            logger.error("[google_drive] %s のデコードに失敗: %s", _ENV_JSON_B64, e)
            return None
    raw = os.getenv(_ENV_JSON)
    if raw:
        try:
            return json.loads(raw)
        except (ValueError, TypeError) as e:
            logger.error("[google_drive] %s が不正な JSON: %s", _ENV_JSON, e)
            return None
    return None


def is_configured() -> bool:
    """サービスアカウント鍵が利用可能か。"""
    return _load_sa_info() is not None


def get_service_account_email() -> Optional[str]:
    """招待先として表示するサービスアカウントのメール。未設定なら None。"""
    info = _load_sa_info()
    return info.get("client_email") if info else None


def extract_folder_id(url_or_id: str) -> Optional[str]:
    """共有ドライブ/フォルダの URL または ID から ID を抽出する。

    対応:
      https://drive.google.com/drive/folders/<ID>
      https://drive.google.com/drive/u/0/folders/<ID>?usp=sharing
      <ID> をそのまま渡した場合
    """
    s = (url_or_id or "").strip()
    if not s:
        return None
    m = _FOLDER_URL_RE.search(s)
    if m:
        return m.group(1)
    if _BARE_ID_RE.match(s):
        return s
    return None


def _build_service():
    """Drive v3 サービスを生成する。未設定なら RuntimeError。"""
    info = _load_sa_info()
    if not info:
        raise RuntimeError("サービスアカウント鍵が未設定です")
    # 重い google ライブラリは呼び出し時に遅延 import（起動を軽くする）
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds = service_account.Credentials.from_service_account_info(info, scopes=_SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def upload_pdf(pdf_bytes: bytes, filename: str, folder_id: str) -> dict:
    """共有ドライブのフォルダに PDF を保存し、ファイル情報を返す。

    Returns: {"id", "name", "web_view_link"}
    Raises:
        RuntimeError: 鍵が未設定
        Exception: google API 由来のエラー（呼び出し側で握る）
    """
    from googleapiclient.http import MediaIoBaseUpload

    service = _build_service()
    media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype="application/pdf", resumable=False)
    metadata = {"name": filename, "parents": [folder_id]}
    created = (
        service.files()
        .create(
            body=metadata,
            media_body=media,
            fields="id,name,webViewLink",
            supportsAllDrives=True,  # 共有ドライブへの作成に必須
        )
        .execute()
    )
    return {
        "id": created.get("id"),
        "name": created.get("name"),
        "web_view_link": created.get("webViewLink"),
    }
