from __future__ import annotations

"""
認証関連Pydanticスキーマ。

元の app.auth.schemas から移動。後方互換性のため、旧パスからもインポート可能。
"""

from pydantic import BaseModel, Field, field_validator

from app.schemas.base import validate_email_loose


class UserRegister(BaseModel):
    """ユーザー登録リクエスト

    email は EmailStr ではなく簡易バリデーション（validate_email_loose）を使う。
    .local 等のRFC予約TLDも識別子として許容するため。実在性チェックは
    上流のFirebase Auth側で担保される。パスワードは受け取らない
    （初回設定メールのリンクから本人が決める。ADR-1013 便4a）。
    """
    email: str = Field(min_length=3, max_length=255)
    username: str = Field(min_length=1, max_length=255)
    full_name: str | None = None
    tenant_code: str = Field(min_length=1, max_length=50)

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return validate_email_loose(v)


class PasswordChange(BaseModel):
    """パスワード変更リクエスト（ログイン中）。新パスワードの決まりは password_policy で見る。"""
    current_password: str = Field(min_length=1, max_length=1024)
    new_password: str = Field(min_length=1, max_length=1024)


class UserLogin(BaseModel):
    """ログインリクエスト"""
    email: str = Field(min_length=3, max_length=255)
    password: str

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return validate_email_loose(v)


class TokenResponse(BaseModel):
    """ログイン成功時のレスポンス"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """JWTトークンの中身（デコード後）"""
    user_id: int
    email: str
    tenant_id: int
    tenant_code: str


class UserResponse(BaseModel):
    """ユーザー情報レスポンス"""
    id: int
    email: str
    username: str
    full_name: str | None
    tenant_id: int
    is_active: bool

    model_config = {"from_attributes": True}
