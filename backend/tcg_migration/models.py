"""
TCG Analysis System — SQLAlchemy Models (v1.1)

テーブル命名ルール:
  - 既存 public schema と衝突するもの: tcg_ プレフィックス
      suppliers → tcg_suppliers   (衝突: migrations/056_add_suppliers_type_and_promote_public.sql)
      products  → tcg_products    (衝突: migrations/062_create_inventory_movements_and_budget.sql)
  - 衝突なし: プレフィックスなし

変更履歴:
  v1.1 (MIG-04 Phase 2): ExtractionJob.prompt_version 追加, ImportJob 追加
"""

import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# 仕入元
# ---------------------------------------------------------------------------

class TcgSupplier(Base):
    """1 社 = 1 行の仕入元マスタ。経路は supplier_channels で管理。"""
    __tablename__ = "tcg_suppliers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(20), nullable=False, unique=True)   # SP0001〜
    name = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    channels = relationship("SupplierChannel", back_populates="supplier")


class SupplierChannel(Base):
    """送信経路（LINE / Discord 等）。1 社が複数経路を持てる。"""
    __tablename__ = "supplier_channels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("tcg_suppliers.id", ondelete="CASCADE"),
                         nullable=False)
    channel = Column(String(50), nullable=False)   # 'line' | 'discord' | ...
    external_id = Column(Text, nullable=True)       # 経路側の識別子
    is_active = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("channel", "external_id", name="uq_supplier_channels_channel_external"),
    )

    supplier = relationship("TcgSupplier", back_populates="channels")
    source_messages = relationship("SourceMessage", back_populates="supplier_channel")


# ---------------------------------------------------------------------------
# 原文メッセージ
# ---------------------------------------------------------------------------

class SourceMessage(Base):
    """1 通のメッセージ = 1 行。supersede 方式で履歴を保持。"""
    __tablename__ = "source_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_channel_id = Column(UUID(as_uuid=True),
                                  ForeignKey("supplier_channels.id", ondelete="SET NULL"),
                                  nullable=True)
    raw_text = Column(Text, nullable=False)
    raw_sha256 = Column(String(64), nullable=False)
    received_at = Column(DateTime(timezone=True), nullable=True)
    superseded_by = Column(UUID(as_uuid=True), ForeignKey("source_messages.id"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    supplier_channel = relationship("SupplierChannel", back_populates="source_messages")
    extraction_jobs = relationship("ExtractionJob", back_populates="source_message")


# ---------------------------------------------------------------------------
# 抽出ジョブ
# ---------------------------------------------------------------------------

class ExtractionJob(Base):
    """1 原文に対する1回の Gemini 抽出実行。"""
    __tablename__ = "extraction_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_message_id = Column(UUID(as_uuid=True),
                                ForeignKey("source_messages.id", ondelete="CASCADE"),
                                nullable=False)
    status = Column(String(30), nullable=False, default="pending")
    # 'pending' | 'running' | 'done' | 'error' | 'empty'
    extracted_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    prompt_version = Column(String(50), nullable=True)   # MIG-04 Phase 2 追加
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    source_message = relationship("SourceMessage", back_populates="extraction_jobs")
    extraction_items = relationship("ExtractionItem", back_populates="extraction_job")


# ---------------------------------------------------------------------------
# 抽出アイテム（行単位）
# ---------------------------------------------------------------------------

class ExtractionItem(Base):
    """Gemini が抽出した 1 行 = 1 件。ID は不変。"""
    __tablename__ = "extraction_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    extraction_job_id = Column(UUID(as_uuid=True),
                                ForeignKey("extraction_jobs.id", ondelete="CASCADE"),
                                nullable=False)
    # 原文位置
    line_start = Column(Integer, nullable=True)
    line_end = Column(Integer, nullable=True)
    # Gemini 出力
    raw_product_name = Column(Text, nullable=True)
    raw_quantity = Column(Text, nullable=True)
    raw_price = Column(Text, nullable=True)
    raw_unit = Column(Text, nullable=True)
    raw_state = Column(Text, nullable=True)
    raw_memo = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    extraction_job = relationship("ExtractionJob", back_populates="extraction_items")
    analysis_result = relationship("AnalysisResult", back_populates="extraction_item",
                                   uselist=False)
    unparsed_lines = relationship("UnparsedLine", back_populates="extraction_item")


# ---------------------------------------------------------------------------
# 未解析行
# ---------------------------------------------------------------------------

class UnparsedLine(Base):
    """SA パーサが解析できなかった行。"""
    __tablename__ = "unparsed_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    extraction_item_id = Column(UUID(as_uuid=True),
                                 ForeignKey("extraction_items.id", ondelete="CASCADE"),
                                 nullable=False)
    line_text = Column(Text, nullable=False)
    reason = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    extraction_item = relationship("ExtractionItem", back_populates="unparsed_lines")


# ---------------------------------------------------------------------------
# 解析結果
# ---------------------------------------------------------------------------

class AnalysisResult(Base):
    """抽出アイテム 1:1 で紐付く解析結果。UPDATE 方式で更新。"""
    __tablename__ = "analysis_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    extraction_item_id = Column(UUID(as_uuid=True),
                                 ForeignKey("extraction_items.id", ondelete="CASCADE"),
                                 nullable=False, unique=True)
    # 商品解決
    product_id = Column(UUID(as_uuid=True), ForeignKey("tcg_products.id"), nullable=True)
    pid_resolved = Column(Boolean, nullable=False, default=False)
    pid_basis = Column(String(100), nullable=True)
    # 単位解決
    unit_id = Column(UUID(as_uuid=True), ForeignKey("units.id"), nullable=True)
    unit_canonical = Column(String(50), nullable=True)
    unit_resolved = Column(Boolean, nullable=False, default=False)
    # 状態解決
    condition_id = Column(UUID(as_uuid=True), ForeignKey("conditions.id"), nullable=True)
    condition_canonical = Column(String(100), nullable=True)
    condition_basis = Column(String(100), nullable=True)
    # 数量・単価
    quantity_normalized = Column(Numeric(14, 2), nullable=True)
    price_normalized = Column(Numeric(14, 2), nullable=True)
    # 注記
    note_ja = Column(Text, nullable=True)
    # ステータス
    status = Column(String(50), nullable=True)
    exclusion = Column(Text, nullable=True)
    needs_review = Column(Boolean, nullable=False, default=False)
    review_reasons = Column(Text, nullable=True)  # JSON array as text
    # エンジン情報
    engine_version = Column(String(50), nullable=False, default="compat-v1")
    computed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(),
                         onupdate=func.now())

    __table_args__ = (
        Index("ix_analysis_results_needs_review", "needs_review"),
        Index("ix_analysis_results_pid_resolved", "pid_resolved"),
        Index("ix_analysis_results_unit_resolved", "unit_resolved"),
    )

    extraction_item = relationship("ExtractionItem", back_populates="analysis_result")
    product = relationship("TcgProduct")
    unit = relationship("Unit")
    condition = relationship("Condition")


# ---------------------------------------------------------------------------
# 商品マスタ（解析コア 6 列 + メタ）
# ---------------------------------------------------------------------------

class TcgProduct(Base):
    """
    解析コア列のみ保持。
    衝突: public.products (migrations/062_create_inventory_movements_and_budget.sql)
    物流系 (入数・重量・サイズ) は products_logistics に分離。
    """
    __tablename__ = "tcg_products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(20), nullable=False, unique=True)   # PM0001〜
    japanese_title = Column(Text, nullable=False)
    release_date = Column(Date, nullable=True)
    category_class = Column(Text, nullable=False)            # カテゴリ分類。NOT NULL
    # 参照マスタ FK (UUID — 実データ投入時に解決)
    division_id = Column(UUID(as_uuid=True), nullable=True)
    work_id = Column(UUID(as_uuid=True), nullable=True)
    manufacturer_id = Column(UUID(as_uuid=True), nullable=True)
    product_category_id = Column(UUID(as_uuid=True), nullable=True)
    # その他
    required_output_value = Column(Text, nullable=True)      # REQUIRED_OUTPUT_VALUE (Series名等)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    logistics = relationship("ProductsLogistics", back_populates="product", uselist=False)
    search_keywords = relationship("ProductSearchKeyword", back_populates="product")
    exclude_keywords = relationship("ProductExcludeKeyword", back_populates="product")


class ProductsLogistics(Base):
    """解析が参照しない物流・EC 系列。今後 入数・重量・サイズ を追加予定。"""
    __tablename__ = "products_logistics"

    product_id = Column(UUID(as_uuid=True), ForeignKey("tcg_products.id", ondelete="CASCADE"),
                         primary_key=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    product = relationship("TcgProduct", back_populates="logistics")


class ProductSearchKeyword(Base):
    """Search Keywords を 1 行 1 ワードに正規化。"""
    __tablename__ = "product_search_keywords"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("tcg_products.id", ondelete="CASCADE"),
                         nullable=False)
    keyword = Column(Text, nullable=False)
    position = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("ix_product_search_keywords_product_id", "product_id"),
    )

    product = relationship("TcgProduct", back_populates="search_keywords")


class ProductExcludeKeyword(Base):
    """Exclude Keywords を 1 行 1 ワードに正規化。"""
    __tablename__ = "product_exclude_keywords"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("tcg_products.id", ondelete="CASCADE"),
                         nullable=False)
    keyword = Column(Text, nullable=False)
    position = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("ix_product_exclude_keywords_product_id", "product_id"),
    )

    product = relationship("TcgProduct", back_populates="exclude_keywords")


# ---------------------------------------------------------------------------
# 単位マスタ
# ---------------------------------------------------------------------------

class Unit(Base):
    __tablename__ = "units"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(20), nullable=False, unique=True)   # e.g. UN0001
    canonical = Column(Text, nullable=False)
    kubun = Column(String(50), nullable=True)                # 箱系 / パック系 / 枚系 etc.
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    aliases = relationship("UnitAlias", back_populates="unit")


class UnitAlias(Base):
    __tablename__ = "unit_aliases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unit_id = Column(UUID(as_uuid=True), ForeignKey("units.id", ondelete="CASCADE"),
                      nullable=False)
    alias_text = Column(Text, nullable=False)
    lang = Column(String(10), nullable=False, default="ja")

    __table_args__ = (
        UniqueConstraint("alias_text", "lang", name="uq_unit_aliases_text_lang"),
        Index("ix_unit_aliases_unit_id", "unit_id"),
    )

    unit = relationship("Unit", back_populates="aliases")


# ---------------------------------------------------------------------------
# 状態マスタ
# ---------------------------------------------------------------------------

class Condition(Base):
    __tablename__ = "conditions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(20), nullable=False, unique=True)   # CN0001〜
    canonical = Column(Text, nullable=False)
    app_kubun = Column(String(50), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    aliases = relationship("ConditionAlias", back_populates="condition")


class ConditionAlias(Base):
    __tablename__ = "condition_aliases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    condition_id = Column(UUID(as_uuid=True), ForeignKey("conditions.id", ondelete="CASCADE"),
                           nullable=False)
    alias_text = Column(Text, nullable=False)
    lang = Column(String(10), nullable=False, default="ja")

    __table_args__ = (
        UniqueConstraint("alias_text", "lang", name="uq_condition_aliases_text_lang"),
        Index("ix_condition_aliases_condition_id", "condition_id"),
    )

    condition = relationship("Condition", back_populates="aliases")


# ---------------------------------------------------------------------------
# 注記
# ---------------------------------------------------------------------------

class ItemNote(Base):
    __tablename__ = "item_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    extraction_item_id = Column(UUID(as_uuid=True),
                                 ForeignKey("extraction_items.id", ondelete="CASCADE"),
                                 nullable=False)
    note_text = Column(Text, nullable=False)
    note_type = Column(String(50), nullable=True)    # 'ja' | 'en' | 'raw_fallback'
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_item_notes_extraction_item_id", "extraction_item_id"),
    )


# ---------------------------------------------------------------------------
# 監査ログ
# ---------------------------------------------------------------------------

class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    table_name = Column(String(100), nullable=False)
    record_id = Column(UUID(as_uuid=True), nullable=True)
    action = Column(String(20), nullable=False)       # 'INSERT' | 'UPDATE' | 'DELETE'
    changed_by = Column(String(100), nullable=True)
    changed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    old_values = Column(Text, nullable=True)          # JSON
    new_values = Column(Text, nullable=True)          # JSON

    __table_args__ = (
        Index("ix_audit_log_table_record", "table_name", "record_id"),
        Index("ix_audit_log_changed_at", "changed_at"),
    )


# ---------------------------------------------------------------------------
# インポートジョブ (MIG-04 Phase 2 新規)
# ---------------------------------------------------------------------------

class ImportJob(Base):
    """LINE エクスポートファイルのアップロード取り込み履歴。冪等化キー: raw_sha256。"""
    __tablename__ = "import_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(Text, nullable=False)
    raw_sha256 = Column(String(64), nullable=False, unique=True)
    message_count = Column(Integer, nullable=False, default=0)
    provider_count = Column(Integer, nullable=False, default=0)
    unresolved_count = Column(Integer, nullable=False, default=0)
    uploaded_by = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="ok")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
