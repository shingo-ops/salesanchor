# design — rule-create-drawer

## 概要

tcg_status_master にルールを新規作成するための Drawer UI と、
単一ルールのパターンマッチをテストするバックエンドエンドポイントを実装。

## 変更内容

### バックエンド

`backend/app/routers/super_admin_status_master.py` に `/super-admin/status-master/preview` POST エンドポイントを追加。

- 照合ロジックは `backend/app/services/tcg_analyzer_svc.py` の `_match_status_pattern`（line 1077）と同一（SSOT 遵守）
- DB アクセスなし（純粋なロジック演算）
- require_super_admin 認証必須

### フロントエンド

新規ファイル: `frontend/src/pages/super-admin/components/RuleCreateDrawer.tsx`

- 金型のみ使用: Drawer / TextField / Select / Button / Badge / Card
- フォームフィールド: status_id, canonical, match_type, effect, search_pattern, exclude_pattern, priority, note
- パターンテストセクション: Card(container) 内に TextField + Button + Badge 結果
- 作成時は enabled: false で POST `/super-admin/status-master`
- 全文字列 t("key") 経由

変更ファイル: `frontend/src/pages/super-admin/components/RuleManagementPanel.tsx`

- RuleCreateDrawer import 追加
- createDrawerOpen state 追加
- ContentToolbar right に「新規作成」HeaderButton 追加
- RuleCreateDrawer コンポーネントを末尾にレンダリング

## KGI/KPI

| 基準 | 検証方法 |
|------|----------|
| 「新規作成」ボタンが RuleManagementPanel の ContentToolbar に表示される | 画面目視 |
| ボタンクリックで Drawer が右からスライドイン | 画面目視 |
| フォーム送信後ルール一覧が更新される | 一覧のルール数増加で確認 |
| 「判定」ボタン押下でバックエンド呼び出しが発生し Badge が表示される | Network タブ + 画面目視 |
| LITERAL/REGEX/DEFAULT の判定結果が `backend/app/services/tcg_analyzer_svc.py` と一致 | 単体テスト + 目視 |
| ja/en 両ロケールで同一キー数（82件） | python3 一致確認済み |

## 外部・過去事例の参照と我々への応用

`backend/app/services/tcg_analyzer_svc.py` の `_match_status_pattern`（line 1077）が既存の照合ロジックの正本。
Preview エンドポイントはこの関数と同一の分岐（DEFAULT→True / LITERAL→lower in lower / REGEX→re.search）を使用。
フロントエンド側でロジックを再実装していないため、将来の照合仕様変更は同ファイル1箇所の修正で反映される。

既存ドロワー実装（`frontend/src/features/supplier-master/SupplierDetailDrawer.tsx`）のフォームスペーシングパターン（`var(--space-4)` gap）を踏襲。

## 維持の仕組み

守り手: RuleManagementPanel + super_admin_status_master.py の担当者（ADR-144 / ADR-027 遵守者）

- Preview エンドポイントは `require_super_admin` 認証で保護。DB アクセスなし（ロジックのみ）
- 作成されたルールは `enabled: false` のため本番解析に影響なし
- ルール有効化には既存のテストゲート（rule_test_runs）が必要（PATCH エンドポイント側の制約）
- i18n キーは CI で ja/en 一致チェックが行われる

## 参照

- recon.md（本ディレクトリ）
- ADR-027: docs/adr/ADR-027-ui-internationalization.md
- ADR-144: docs/CC_UI_GOVERNANCE.md
