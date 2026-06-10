# design — ADR-126 追補: 担当者名任意化・フォールバック

**仕事名**: adr-126-contact-optional  
**日付**: 2026-06-11  
**対象ADR**: ADR-126（追補）  
**担当**: architect

---

## 設計方針

Contact Name を任意化し、空欄の場合は `companies.billing_display_name` をフォールバックとして `contacts.display_name` に保存する。

ZIP/メールの「出口補完（DBは空）」と異なり、担当者名は登録時に確定させる。理由: 担当者は「この取引の窓口は誰か」という関係の記録であり、空のままにすると後工程（連絡時の宛先）が機能しない。

---

## 変更箇所と設計根拠

| 変更箇所 | 変更内容 | 根拠 |
|---------|---------|------|
| `RegisterRequest.validate_contact_required` | 削除 | 担当者名必須→任意（ADR-126 追補 §0） |
| `RegisterRequest.normalize_contact_name` | 新規追加（空文字→None） | フォールバック判定を `None` で統一 |
| `SELECT id, billing_display_name FROM companies` | `billing_display_name` 追加取得 | フォールバック値の取得 |
| `contact_display_name` 変数 | `contact_name.strip() or billing_display_name_fallback` | フォールバックロジック本体 |
| `RegisterPage.tsx` 必須バリデーション | 2チェック削除 | フロント制約をバックエンドと同期 |
| `contactHint` i18n | 「空欄で結構です（ご自身が窓口として登録されます）」 | ADR-126 追補で確定した注記文 |

---

## 受け入れ条件と検証方法

| 基準 | 検証方法 |
|------|---------|
| contact_name 空欄で送信 → 422 にならない | pytest `test_all_contact_fields_empty_accepted` |
| contact_name="" → None に正規化 | pytest `test_empty_name_accepted` |
| contact_name なし + email/tel なし → 受理 | pytest `test_all_contact_fields_empty_accepted` |
| contact_name 空欄送信 → contacts.display_name = billing_display_name | E2E または本番カナリー確認 |
| contactName 必須バリデーションなし → `*` マーク非表示 | 目視確認（RegisterPage フォーム） |
| contactHint が「空欄で結構です…」に変更 | 目視確認（en/ja） |
| migration なし（deploy.yml 変更なし） | CI `models.py に新 Column → deploy.yml` チェック通過 |

---

## 外部・過去事例の参照と我々への応用

- **ADR-126 §5「偽データをDBに入れない」との非対称性**: ZIP/メールは「出口補完（DBは空）」だが、担当者名は「窓口の実体確定」のため登録時にDBへ保存する設計とした（ADR-126 追補 Section 0 に根拠記載）。参照: `docs/handoff/adr-126-contact-optional/recon.md`
- **社内過去事例（SA-18 Phase2）**: 確実性はゲートで担保するアプローチを踏襲。バリデーション緩和は受け入れ条件＋Evaluator で担保。
- **Pydantic field_validator パターン**: `Optional[str]` フィールドの空文字列 → None 正規化は既存の `validate_email` / `validate_tel` と同パターン。`contact_name` も同様に実装し一貫性を維持。
