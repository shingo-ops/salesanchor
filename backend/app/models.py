from sqlalchemy import JSON, BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    tenant_name = Column(String(255), nullable=False, unique=True)
    tenant_code = Column(String(50), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True, index=True)
    settings = Column(JSON, default=dict)

    # リレーション
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    username = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    full_name = Column(String(255))
    # spec.md v1.1 F2 (Sprint 2): マーケットプレイス中央 admin フラグ。
    # テナント admin (role='admin') とは独立、Jarvis 運用 admin のみ true。
    # 詳細: migrations/064_add_users_is_super_admin.sql
    is_super_admin = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True, index=True)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # リレーション
    tenant = relationship("Tenant", back_populates="users")


class StaffJoinInvite(Base):
    """スタッフ自己登録の招待（ADR-1068）。表の定義は migrations/20261107_120000_create_staff_join_invites.sql。

    招待の状態と、一人の人へつなぐ番号だけを持つ。名前・メールは置かない。鍵と登録番号は sha256 だけ。
    FORCE RLS（会社別）。読み書きの前に set_tenant_context で会社を決める。
    """
    __tablename__ = "staff_join_invites"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    role_id = Column(Integer, nullable=False)  # 会社ごとのスキーマの roles.id（外部キーなし）
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(LargeBinary, nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, nullable=False, default="open")  # open / submitted / linked / revoked
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    staff_id = Column(Integer, nullable=True)
    reg_code_hash = Column(LargeBinary, nullable=True, unique=True)
    reg_code_expires_at = Column(DateTime(timezone=True), nullable=True)
    discord_channel_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    linked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
