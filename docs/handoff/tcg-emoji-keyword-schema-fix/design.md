# design: tcg-emoji-keyword-schema-fix

## 参照
- recon: docs/handoff/tcg-emoji-keyword-schema-fix/recon.md

## 対象ADR
既存機能のバグ修正のため新規ADRなし。関連: ADR-072（テナントスキーマ分離）

## 変更概要

### 1. キーワードスキーマ修正
`backend/app/services/tcg_work_reference.py`:49 の text(""") を text(f""") に変更し、
キーワードサブクエリの public を {schema} に置き換える。

| 基準 | 検証方法 |
|------|---------|
| tenant_004.product_search_keywords が参照される | 本番ログで SQL が `tenant_004.product_search_keywords` を参照することを確認 |
| Gemini に渡るキーワード数が増加 | デバッグログで reference["products"] の search_keywords 配列長を確認 |

### 2. 絵文字除去
`backend/app/services/gemini_extraction_svc.py` に strip_emoji() を追加。
format_prompt_input() 内で呼び出し、LINEメッセージの絵文字を除去してから Gemini に渡す。

| 基準 | 検証方法 |
|------|---------|
| 絵文字を含むメッセージが正常に処理される | テスト6件パス確認 |
| INVALID_RESPONSE 件数の減少 | 本番デプロイ後に tcg_line_extraction_attempts の result カラムを集計 |

## 外部・過去事例の参照と我々への応用
- SQLAlchemy text(f"...") + schema 文字列埋め込み: 既存コード (tcg_work_reference.py の public.products 参照部分) と同一パターン。schemaは内部定数なのでインジェクションリスクなし。
- 絵文字除去: Unicodeコードポイント範囲（U+1F300〜U+1FAF8等）の正規表現でフィルタ。外部ライブラリ不要で既存 requirements.txt を変更しない。
- 過去事例: PR #3495（略称追加）で tenant_004 スキーマへの直接INSERT/UPDATE を実施済み。今回はクエリ側の参照先を揃える修正。

## 維持の仕組み
- load_work_reference() のシグネチャ schema: str は既存のまま。呼び出し元は変更不要。
- テスト (backend/tests/test_tcg_gemini_extraction.py) に strip_emoji 単体テスト6件を追加。将来の誤退行を防ぐ。
- スキーマ名は呼び出し元 (backend/app/tasks/tcg_extraction.py 等) から渡されるため、新テナント追加時も自動対応。

### 守り手:
内部バッチ処理のみ。ユーザー向けUIへの影響なし。

## 守り手
なし（内部バッチ処理のみ・ユーザー向けUIへの影響なし）
