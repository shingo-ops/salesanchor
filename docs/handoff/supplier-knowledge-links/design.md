# design: supplier-knowledge-links

## KGI

| 基準 | 検証方法 |
|------|---------|
| フロントエンドから仕入元へblock_delimiter/skip_condition/status_keywordをリンクできる | /super-admin/supplier-extraction-rules で仕入元選択→Knowledge セクションでBadge表示・追加・削除が動作する |
| リンク済みルールがGeminiプロンプトに注入される | tcg_extraction.py 経由で抽出実行時、_build_supplier_context_note の出力に区切り記号・スキップ条件・ステータス判定が含まれる |

## 設計方針

- SSOT: knowledge_rules テーブル（既存）に新カテゴリを追加。junction テーブル（supplier_knowledge_links）で仕入元と多対多リンク
- 既存データへの影響ゼロ: WHERE NOT EXISTS で冪等seed、既存 knowledge_rules カテゴリには触れない
- バックエンド: extract_message / call_gemini_extraction / _build_supplier_context_note に knowledge_links パラメータをオプション追加（既存呼び出し元に影響なし）

## 参照ADR

- ADR-027: UI i18n 強制
- ADR-144: UIガバナンス（金型コンポーネント）
- ADR-072: write endpoint の reset_tenant_context（本実装は super_admin エンドポイントで tenant_id 無し、適用対象外）

## 弊害・リスク

- knowledge_rules の pattern_type CHECK制約: exact/substring/regex/prefix の4種のみ。seedの全パターンはこれらに準拠
- supplier_knowledge_links の UNIQUE 制約: 重複リンクは409 Conflict として返す（フロントエンドは silent 処理）

## 触らない範囲

- tenant_* スキーマのテーブル（本実装は public スキーマのみ）
- 既存の extraction_price_format 等のフィールド（別途PATCH で管理）

## 外部・過去事例の参照と我々への応用

- junction テーブルパターン（多対多・UNIQUE制約・ON DELETE CASCADE）: 既存の supplier_discord_routing / supplier_aliases と同様の構造を採用
- プロンプト注入: 既存の `_build_supplier_context_note` への optional パラメータ追加で最小変更・後方互換を維持

## 維持の仕組み

- knowledge_rules の新カテゴリ追加は seed migration で冪等管理
- supplier_knowledge_links の参照整合性は ON DELETE CASCADE で保護
- フロントエンド操作は即時APIコール（「保存」ボタン不要・独立）
