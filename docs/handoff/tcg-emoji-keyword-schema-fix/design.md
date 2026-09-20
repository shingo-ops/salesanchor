# design: tcg-emoji-keyword-schema-fix

## 対象ADR
なし（バグ修正）

## 変更概要

### 1. キーワードスキーマ修正
`backend/app/services/tcg_work_reference.py:49` の `text("""` を `text(f"""` に変更し、
キーワードサブクエリの `public` を `{schema}` に置き換える。

| 基準 | 検証方法 |
|------|---------|
| tenant_004.product_search_keywords が参照される | 本番ログで SQL が `tenant_004.product_search_keywords` を参照することを確認 |
| Gemini に渡るキーワード数が増加 | デバッグログで reference["products"] の search_keywords 配列長を確認 |

### 2. 絵文字除去
`backend/app/services/gemini_extraction_svc.py` に `strip_emoji()` を追加。
`format_prompt_input()` 内で呼び出し、LINEメッセージの絵文字を除去してから Gemini に渡す。

| 基準 | 検証方法 |
|------|---------|
| 絵文字を含むメッセージが正常に処理される | テスト6件パス確認 |
| INVALID_RESPONSE 件数の減少 | 本番デプロイ後に tcg_line_extraction_attempts の result カラムを集計 |

## 外部事例
- SQLAlchemy f-string + `text()`: schema を f-string で埋め込む手法は既存コードでも使用されている
- 絵文字除去: `emoji` ライブラリ or 正規表現（Unicode範囲）で実装

## 守り手
なし（内部バッチ処理のみ・ユーザー向けUIへの影響なし）
