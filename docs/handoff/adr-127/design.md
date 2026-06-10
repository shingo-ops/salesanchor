# design — ADR-127: 登録後の変更・追加を専用フォーム化

**仕事名**: adr-127-registration-post-forms
**日付**: 2026-06-11
**対象ADR**: ADR-127
**担当**: architect

参照: `docs/handoff/adr-127/recon.md`

## 設計方針

ADR-097/126 の拡張として、登録後の変更・追加を専用フォームに分離し、新規登録の二重発行を防止する。本 PR はドキュメント（ADR本文）のみ。実装はGenerator に委ねる。

## 変更箇所と設計根拠

| 変更箇所 | 変更内容 | 根拠 |
|---------|---------|------|
| `docs/adr/ADR-127-registration-post-forms.md` | 新規起案 | 登録後変更・追加経路の欠如をカナリーで確認 |
| `docs/adr/README.md` | インデックス再生成 | CLAUDE.md 規定: ADR 追加後必須 |

## 受け入れ条件と検証方法

| 基準 | 検証方法 |
|------|---------|
| ADR-127 が docs/adr/ に存在する | ファイル存在確認 |
| ADR インデックスが最新 | CI「ADR index is up to date」チェック通過 |

## 外部・過去事例の参照と我々への応用

- ADR-097「上書きせず追加（住所帳）」の思想を請求先変更にも拡張（案B: 降格＋INSERT）。
- ADR-101 スナップショットにより billing 行変更後も既存請求書が不変であることを確認済み（`backend/app/routers/invoices.py:53-82`）。
- #1918 のエラーコード方式を新フォームにも踏襲する方針を ADR に明記。
