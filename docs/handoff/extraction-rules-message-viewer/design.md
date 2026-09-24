# design: extraction-rules-message-viewer

## 参照 ADR
- ADR-027: UI i18n 強制 (`docs/adr/ADR-027-ui-internationalization.md`)
- ADR-144: UIガバナンス (`docs/CC_UI_GOVERNANCE.md`)

## 修正1: フロントエンド型定義修正

**あるべき姿**: フロントエンドの型定義はバックエンドの `SupplierExtractionRulesResponse` と一致する

| 基準 | 検証方法 |
|------|---------|
| `SupplierExtractionDetail` が `latest_raw_text` フィールドを持つ | TypeScript コンパイルが通る |
| `detailToForm(data)` が正しく動作する | フォームに既存値が表示される |

**変更前後**:
- `source_text: string | null` → 削除
- `rules: ExtractionRules` ネスト → 削除
- フラット `extraction_*` + `latest_raw_text` フィールドを追加
- `detailToForm(data.rules)` → `detailToForm(data)`

## 修正2: source-messages エンドポイント追加

**あるべき姿**: `GET /api/v1/super-admin/suppliers/{id}/source-messages` が存在し、仕入元の全メッセージをページ送り用に返す

| 基準 | 検証方法 |
|------|---------|
| レスポンスが `{ messages: [...], total: N }` 形式 | API 呼び出しで確認 |
| `is_active = true` のメッセージのみ返す | SQL WHERE 条件 |
| `created_at DESC` で降順 | 最新が先頭 |

## 修正3: メッセージページ送りUI

**あるべき姿**: 仕入元選択時に全メッセージを取得し、左ペインでページ送りできる

| 基準 | 検証方法 |
|------|---------|
| 前後ナビゲーションボタンが表示される | UI 目視確認 |
| 先頭で前ボタン disabled、末尾で次ボタン disabled | 動作確認 |
| メッセージ日時が表示される | UI 目視確認 |
| メッセージがない場合「メッセージなし」表示 | noMessages i18n キー |

## 影響範囲

- `SupplierExtractionRulesPage`: 単独ページ + AnalysisRulesPage からの embedded 使用
- embedded prop の動作は変更なし
- 既存の extraction-rules GET/PATCH エンドポイントは無変更

## 外部事例
- ページ送りナビゲーション: 既存の `AnalysisDashboardPanel.tsx` での `DashboardIcons.arrowRight` 使用パターンを踏襲

## 戻し方
- フロントエンド: 型定義・JSX を元の `source_text`/`rules` ネスト構造に戻す
- バックエンド: `source-messages` エンドポイントと `SupplierSourceMessage*` スキーマを削除

## 測り方
- 仕入元選択 → source-messages API が呼ばれ複数メッセージが返る
- ナビゲーションボタンで前後のメッセージに切り替えられる
- ルール設定フォームに既存値が正しく入っている（型修正の検証）
