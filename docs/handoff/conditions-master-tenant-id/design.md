# Design: 状態マスタ tenant_id + CRUD

## 概要
public.conditions に tenant_id 列を追加し、仕入元マスタと同じパターンでSaaS管理者/テナント向けCRUDを実装する。

## 変更内容

### DB変更（DDLのみ）
1. public.conditions に tenant_id INTEGER 追加（ADD COLUMN IF NOT EXISTS）
2. deal_statuses.condition_id FK を public.conditions へ張り替え（冪等）
3. work_items.condition_id FK を public.conditions へ張り替え（冪等）

### バックエンド
- super_admin_conditions.py: 中央マスタCRUD（tenant_id IS NULL）
- conditions.py: テナントスコープCRUD + カタログ

### フロントエンド
- ConditionsMasterPanel: 解析管理 > マスタ管理 > 状態マスタ
- i18n: ja/en 翻訳キー追加

## 受入条件

| 基準 | 検証方法 |
|------|---------|
| tenant_id 列が追加される | migration 実行後 \d public.conditions で確認 |
| 共用マスタが管理画面に表示される | 解析管理 > マスタ管理 > 状態マスタ パネル表示 |
| CRUD操作が機能する | POST/PATCH/DELETE API + UI操作 |
| FK張り替えが冪等 | migration 2回実行でエラーなし |

## 外部・過去事例の参照と我々への応用

本PRは既存の仕入元マスタ（suppliers）の tenant_id パターンを状態マスタ（conditions）に横展開する。
- 参照元: PR #3585（supplier-dedup-upsert）で確立した tenant_id NULL/N 分離パターン
- 参照元: migrations/20260918_030000_supplier_ssot_phase2.sql（ADD COLUMN tenant_id）
- 応用: 同一DDLパターン・同一API構造・同一UIパネル構造を conditions に適用
- 外部事例: 不要（社内既存パターンの横展開のため新規調査対象なし）

## 維持の仕組み

- migration-guard CI チェック（DDL安全性）
- ADR-155 SSOT ポリシー（共用マスタは public スキーマ）
- reset_tenant_context（ADR-072、テナントコンテキスト汚染防止）
- i18n CI チェック（ADR-027、ハードコード文字列検出）
- ADR-144 UI governance（金型コンポーネント強制）
