"""
担当者アイコン画像の検証・加工・保存（ADR-159 便A）。

- 受け付ける形式: JPEG / PNG / WebP（先頭バイトで判定。Content-Type は信用しない）
- 2MB 超は拒否
- Pillow で EXIF・ICC 等のメタデータを除去し、中央正方形に切り抜いて 256px の WebP に再エンコード
- 保存先: ATTACHMENT_ROOT/staff_avatars/<token>.webp（token = secrets.token_urlsafe(32)）

公開 URL は推測不能な token のみで認証なしに配信される（Discord が取得するため）。
"""
from __future__ import annotations

import io
import logging
import os
import re
import secrets
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

logger = logging.getLogger(__name__)

AVATAR_MAX_BYTES = 2 * 1024 * 1024
AVATAR_SIZE_PX = 256
# 展開後ピクセル数の上限（decompression bomb 対策。2MB の圧縮画像でも巨大に展開され得る）
AVATAR_MAX_PIXELS = 25_000_000
AVATAR_WEBP_QUALITY = 85
AVATAR_SUBDIR = "staff_avatars"
AVATAR_PUBLIC_PATH = "/api/public/staff-avatars"

# secrets.token_urlsafe(32) は 43 文字（base64url・パディングなし）
_TOKEN_BYTES = 32
TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")

ERR_INVALID_TYPE = "AVATAR_INVALID_TYPE"
ERR_TOO_LARGE = "AVATAR_TOO_LARGE"
ERR_SAVE_FAILED = "AVATAR_SAVE_FAILED"


class AvatarError(Exception):
    """画像の検証・保存に失敗。code はフロントが文言に変換する安定コード。"""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _root() -> Path:
    return Path(os.environ.get("ATTACHMENT_ROOT", "/data/attachments")) / AVATAR_SUBDIR


def new_token() -> str:
    return secrets.token_urlsafe(_TOKEN_BYTES)


def is_valid_token(token: str) -> bool:
    return bool(TOKEN_RE.fullmatch(token))


def detect_image_type(data: bytes) -> str | None:
    """先頭バイトから jpeg / png / webp を判定する。それ以外は None。"""
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def process_avatar(data: bytes) -> bytes:
    """検証済みの生バイト列を 256x256 の WebP（メタデータなし）に変換して返す。"""
    if len(data) > AVATAR_MAX_BYTES:
        raise AvatarError(ERR_TOO_LARGE)
    if detect_image_type(data) is None:
        raise AvatarError(ERR_INVALID_TYPE)
    try:
        Image.MAX_IMAGE_PIXELS = AVATAR_MAX_PIXELS
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()
        with Image.open(io.BytesIO(data)) as img:
            img.seek(0)  # アニメーション WebP/PNG は先頭フレームのみ使う
            oriented = ImageOps.exif_transpose(img)
            mode = "RGBA" if "A" in oriented.getbands() else "RGB"
            converted = oriented.convert(mode)
            squared = ImageOps.fit(
                converted, (AVATAR_SIZE_PX, AVATAR_SIZE_PX), method=Image.Resampling.LANCZOS,
            )
            # ピクセルだけを新しい画像へ移し、EXIF / ICC / XMP などの info を確実に落とす
            clean = Image.frombytes(mode, squared.size, squared.tobytes())
            out = io.BytesIO()
            clean.save(out, format="WEBP", quality=AVATAR_WEBP_QUALITY)
            return out.getvalue()
    except (UnidentifiedImageError, Image.DecompressionBombError, SyntaxError, OSError, ValueError):
        # 壊れた画像・偽装ファイル・展開サイズ超過は形式不正として扱う
        raise AvatarError(ERR_INVALID_TYPE) from None


def avatar_path(token: str) -> Path | None:
    """token からファイルパスを返す。token 形式が不正なら None（パストラバーサル防止）。"""
    if not is_valid_token(token):
        return None
    return _root() / f"{token}.webp"


def save_avatar(token: str, webp: bytes) -> None:
    path = avatar_path(token)
    if path is None:
        raise AvatarError(ERR_SAVE_FAILED)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(webp)
        os.replace(tmp, path)
    except OSError:
        logger.exception("[staff-avatar] 保存に失敗 path=%s", path)
        raise AvatarError(ERR_SAVE_FAILED) from None


def delete_avatar_file(token: str | None) -> None:
    """ファイルが無くてもエラーにしない（削除は冪等）。"""
    if not token:
        return
    path = avatar_path(token)
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.warning("[staff-avatar] 旧ファイル削除に失敗 path=%s", path, exc_info=True)


def build_avatar_url(token: str | None) -> str | None:
    """Discord 等の外部が取得する絶対 URL。未登録なら None。"""
    if not token:
        return None
    base = os.getenv("API_BASE_URL", "https://api.salesanchor.jp").rstrip("/")
    return f"{base}{AVATAR_PUBLIC_PATH}/{token}.webp"
