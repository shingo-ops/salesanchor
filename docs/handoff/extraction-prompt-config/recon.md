# Recon: 抽出プロンプトDB管理化

## 調査済みファイルと参照行

- "backend/app/services/gemini_extraction_svc.py:103-133" — WORK_ID_PROMPT_TEXT定数（矛盾箇所: L106, L127）
- "backend/app/services/gemini_extraction_svc.py:301-393" — "call_gemini_extraction()" 関数（DB配線追加対象）
- "backend/app/services/tcg_analyzer_svc.py:1273-1284" — "_resolve_pid()" 関数（"-" ガード追加対象）
- "backend/app/routers/super_admin_suppliers.py:598-667" — supplier_prompts APIパターン（踏襲元）
- "migrations/087_create_supplier_prompts.sql" — supplier_prompts migrationパターン（踏襲元）
- "scripts/run_all_migrations.sh:826" — migration登録末尾
- "frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:69-165" — プロンプト編集UIパターン（踏襲元）
- "frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx" — サイドバーキー定義
- "frontend/src/pages/super-admin/AnalysisRulesPage.tsx:163-183" — パネル切り替え

## 既存ADR

- ADR-027: i18n強制（全UIテキストはt("key")経由）
- ADR-072: write endpointのdb.commit()直後にreset_tenant_context()必須
  - 本実装: publicテーブルのみアクセス、テナントコンテキスト不要。super_admin_suppliers.pyの既存パターンに合わせてreset_tenant_context()は不使用（確認済み）
- ADR-144: UIガバナンス遵守（デザインシステムコンポーネント使用）

## DB接続パターン確認

- "backend/app/services/tcg_product_master_svc.py:543-560" — 同期DB接続パターン（"_SYNC_DB_URL = os.getenv("DATABASE_URL", "").replace(...)"）
- gemini_extraction_svc.pyはCeleryタスク内の同期関数のため、同パターンを採用

## バグ調査

- "tcg_analyzer_svc.py:1273-1284": "_resolve_pid" が "None" と """" のみガード → "-" が通過して validate_product_id に渡される
- "gemini_extraction_svc.py:106": 「商品IDは参照products内のidをそのまま選ぶ」← 「コード」と「id」が混在
- "gemini_extraction_svc.py:127": 「商品コードはRESOLVED_PRODUCT_CODE列に返す」← 実際はIDを返すべき
- "public.products WHERE id=61": product_code='-' が設定されており _resolve_pid の legacy変換でも解決不可
