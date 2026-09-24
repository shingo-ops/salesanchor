# design: フォーマットビルダー UI

## 参照 ADR

- ADR-027: UI 文字列 i18n 強制
- ADR-144: UIガバナンス（金型コンポーネントのみ使用）

## 設計方針

`extraction_order_pattern`（既存 TEXT 列）に JSON 配列（例: `["quantity","@","price","yen"]`）を保存する。
旧値（文字列形式: `qty_at_price` 等）は JSON parse 失敗時に空配列として扱う（後方互換）。

## 基準と検証方法

| 基準 | 検証方法 |
|------|---------|
| 「要素を追加」ボタンでドロップダウンが追加される | 画面目視 |
| ドロップダウム変更でプレビューが即時更新される | 画面目視 |
| 保存後リロードでトークン配列が復元される | 画面目視 |
| 旧形式値の仕入元を開いても空ビルダーで表示される | 画面目視 |
| Gemini プロンプトに人間可読パターンが注入される | ログ確認 |

## 外部・過去事例の参照と我々への応用

- Zapier / Notion formula builder: トークンをドロップダウムで選んで式を組む UI パターン
- 本プロジェクト応用: SelectControl でトークン値を選択 → JSON 配列で保存 → Gemini プロンプト生成時に人間可読文字列に変換

## 維持の仕組み

- ESLint `local/no-japanese-literal` が日本語リテラルの直書きを検出（ADR-027）
- `check-jsx-emoji.js` が絵文字・記号リテラルを検出し `frontend/src/constants/icons.tsx` 使用を強制（ADR-144）
- `extraction_order_pattern` は JSON 配列専用に切り替わったが旧値は空配列として透過的に処理

## 守り手（触らない範囲）

- DB スキーマ（migration 不要）
- バックエンド API エンドポイント
- 他ページ・他コンポーネント
