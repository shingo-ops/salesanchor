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

## 外部事例
該当なし（既存の仕入元マスタパターンの横展開のため）

## 守り手
- migration-guard CI チェック
- ADR-155 SSOT ポリシー
- reset_tenant_context（ADR-072）
