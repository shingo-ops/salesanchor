"""
検証用フィーチャーフラグデモエンドポイント。

テナント単位フィーチャーフラグ (tenant_features) の動作検証に使用する。
require_feature("inventory_v2") で保護されたエンドポイントを提供し、
フラグが無効なテナントからのアクセスは 403 で拒否される。
"""

from fastapi import APIRouter, Depends

from app.auth.dependencies import require_feature

router = APIRouter()


@router.get(
    "/feature-demo/ping",
    dependencies=[Depends(require_feature("inventory_v2"))],
)
async def feature_demo_ping():
    """フィーチャーフラグ検証用エンドポイント。

    inventory_v2 が有効なテナントのみ 200 を返す。
    無効なテナントには require_feature が 403 を返す。
    """
    return {
        "status": "ok",
        "message": "feature inventory_v2 is enabled for your tenant",
    }
