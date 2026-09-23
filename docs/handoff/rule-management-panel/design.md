# ルール管理パネル — design

recon: [docs/handoff/rule-management-panel/recon.md](./recon.md)

## 概要
解析管理ページに「ルール管理」グループを追加し、tcg_status_master のルール運用ビューを提供する。
既存の StatusMasterPanel（マスタ管理グループ）はデータCRUD用として維持。

## 対象ADR: ADR-027, ADR-067, ADR-144

## 変更前後

| 項目 | 変更前 | 変更後 |
|------|--------|--------|
| サイドメニュー | 解析状況 + マスタ管理 の2グループ | 解析状況 + ルール管理 + マスタ管理 の3グループ |
| ルール管理UI | なし（PR #3623で削除済み） | RuleManagementPanel（ルール運用ビュー） |
| バックエンド | 変更なし | 変更なし（既存API利用） |
| DB | 変更なし | 変更なし（tcg_status_master SSOT） |

## 新規ファイル
- `frontend/src/pages/super-admin/components/RuleManagementPanel.tsx` — ルール管理パネル

## 変更ファイル
- `frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx` — キー追加 + ルール管理グループ追加
- `frontend/src/pages/super-admin/AnalysisRulesPage.tsx` — パネル描画追加
- `frontend/src/locales/ja.json` — i18nキー追加
- `frontend/src/locales/en.json` — i18nキー追加

## RuleManagementPanel 仕様
- GET /super-admin/status-master から取得
- DataTable 7列: 表示名, 検索パターン, 除外パターン, 照合方法(Badge), 効果(Badge), 優先度, 有効(Badge)
- 検索バー（表示名・パターンでフィルタ）
- 行クリックで enabled トグル（PATCH /super-admin/status-master/:id）
- ページネーション（50件/ページ）

## タブ分離（追加仕様）
- 金型 Tabs コンポーネント（variant="underline"）で3タブ表示
- 完売ルール: `effect === "EXCLUDE"`（完売・売切等の除外ルール）
- 日付ルール: `effect === "OUTPUT" && match_type !== "DEFAULT"`（日付・予約パターンルール）
- デフォルト: `match_type === "DEFAULT"`（デフォルトステータス）
- タブに件数バッジ表示
- クライアントサイドフィルタ（全9件のため十分）

## 受入条件

| 基準 | 検証方法 |
|------|----------|
| サイドメニューに「ルール管理」グループ表示 | 画面確認 |
| ルール管理パネルに全ルールが表示 | 画面確認（9件のシードデータ） |
| Badge で照合方法・効果・有効状態が色分け | 画面確認 |
| 行クリックで有効/無効トグル | 画面操作確認 |
| 検索でルールをフィルタ可能 | 画面操作確認 |
| ハードコード日本語なし | grep -rn '[ぁ-ん]' RuleManagementPanel.tsx で0件（コメント除く） |
| 既存パネル（マスタ管理）に影響なし | StatusMasterPanel が従来通り動作 |

## 外部・過去事例の参照と我々への応用
既存パターン（StatusMasterPanel）の再構築。新たな外部ライブラリや独自実装は導入しない。
DataTable / Badge / ContentToolbar は既にプロジェクト標準として採用済み（ADR-144）。

## 維持の仕組み
守り手: `frontend/src/pages/super-admin/components/RuleManagementPanel.tsx:37`（ADR-027 i18n）・`frontend/src/pages/super-admin/components/RuleManagementPanel.tsx:90`（ADR-144 金型）

- ADR-027 準拠を CI grep チェック（`grep -n '[ぁ-ん]' RuleManagementPanel.tsx` が UI 文字列で 0 件）で担保
- ADR-144 準拠は PR レビュー時に金型外コンポーネント使用の有無を確認
- tcg_status_master 側スキーマ変更時は RuleEntry 型定義の更新が必要（`frontend/src/pages/super-admin/components/RuleManagementPanel.tsx:20-33`）

## 守り手
- `frontend/src/pages/super-admin/components/RuleManagementPanel.tsx:37` — 全UI文字列 t() 経由（ADR-027）
- `frontend/src/pages/super-admin/components/RuleManagementPanel.tsx:90-117` — Badge variant はデザイントークン準拠（ADR-067）
- `frontend/src/pages/super-admin/components/RuleManagementPanel.tsx:52` — 既存API利用でバックエンド変更なし
