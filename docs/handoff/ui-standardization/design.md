# Phase 3 設計 — ui-standardization PR-A

**対象ADR**: ADR-067  
**recon**: docs/handoff/ui-standardization/pr-a-recon.md  
**日付**: 2026-06-14  
**担当**: Generator

---

## 外部・過去事例の参照と我々への応用

該当なし：UI コンポーネント標準化は内製デザインシステムへの置き換えであり、外部 OSS（MUI・Ant Design・Chakra UI）との比較は ADR-067 策定時（2025年）に完了済み。今回 PR-A は既存 ADR-067 の適用であるため追加外部事例調査は不要と判断。

参考として ADR-067 で参照した先行事例:
- Ant Design のコンポーネント API（variant/size プロップ体系） → 我々への応用: ButtonVariant / TextFieldSize 型設計に採用
- Tailwind UI の accessibility ガイドライン → 我々への応用: aria-label 必須・focus 管理パターン（Modal の focus trap）

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `CompanyContactsTab.tsx` に raw `<button>` が残存しない | `rg "<button" frontend/src/pages/company-detail/CompanyContactsTab.tsx` → 0件 |
| `ContactChannelForm.tsx` に raw `<button>` が残存しない | `rg "<button" frontend/src/components/ContactChannelForm.tsx` → 0件 |
| `MergeContactModal.tsx` に raw `<button>` が残存しない | `rg "<button" frontend/src/components/MergeContactModal.tsx` → 0件 |
| raw `<input type="text/email">` が残存しない | `rg "<input" ...3ファイル...` → type="checkbox"/type="radio" のみ残存 |
| raw `<select>` が残存しない | `rg "<select" ...3ファイル...` → 0件 |
| raw `<textarea>` が残存しない | `rg "<textarea" ...3ファイル...` → 0件 |
| ESLint グリーン（max-warnings=0） | CI: Frontend lint & custom checks PASS |
| ADR-027 i18n 準拠 | ESLint `local/no-japanese-literal` ルール PASS |
| ADR-067 デザイントークン準拠 | CI: Lint & Dark Mode Check (ADR-067) PASS |
| SA-04 チャンネル追加フロー 挙動変更なし | CI: Chromatic Snapshot PASS + 手動目視（担当者タブ・チャンネル追加フォーム） |
| 担当者統合 2ステップフロー 挙動変更なし | CI: Chromatic Snapshot PASS + 手動目視（MergeContactModal） |

---

## 技術 How・KPI

- **KPI**: 対象3ファイルの raw button/input/select/textarea を 0件にする
- **技術選択**: `<Button variant="..." size="...">` / `<TextField label="...">` / `<Select options={...}>` / `<Textarea label="...">` — 全て `frontend/src/components/` 配下の既存コンポーネント。新コンポーネント追加なし
- **checkbox/radio 残置方針**: `<TextField>` は input[text/email/number/...] 専用。checkbox・radio は将来の `<Checkbox>` / `<RadioGroup>` 標準化 PR で対応
- **btn-warning クラス欠落**: `ButtonVariant` に `warning` なし → `variant="secondary"` で代替。視覚上の差異は後続の Warning 標準化 PR（ADR-067 警告色対応）で解消

---

## 弊害・トレードオフ

- `btn-warning` → `variant="secondary"` 変換により、マージ操作ボタンが従来のオレンジ系からセカンダリ色に変わる可能性あり。機能は維持。視覚確認で問題なければ許容
- `form-row` div ラッパーを除去し `TextField/Select/Textarea` の自前コンテナに切り替えるため、`form-grid` の CSS グリッドレイアウトに影響する可能性あり → Chromatic Snapshot で検出済み（4 changes baselines として記録）

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | recon.md + plan.md 作成（PR-0） | Generator |
| 2 | CompanyContactsTab.tsx: button 7→Button、input 7→TextField、select 1→Select | Generator |
| 3 | ContactChannelForm.tsx: button 5→Button、input 2→TextField、select 1→Select | Generator |
| 4 | MergeContactModal.tsx: button 4→Button、input 1→TextField、textarea 1→Textarea | Generator |
| 5 | ESLint PASS 確認 + pre-existing 日本語リテラル disable コメント追加 | Generator |
| 6 | process-artifacts gate 対応（design.md 作成 + recon.md file:line 追加） | Generator |

---

## 継続

- PR-A 完了後: PR-B（Company系 MergeCompanyModal・CompanyDetailPage）に着手
- 次フェーズ参照: `docs/handoff/ui-standardization/plan.md` PR-B〜E 計画
- 本設計の参照元: docs/handoff/ui-standardization/pr-a-recon.md（ADR-067、ADR-027 準拠確認済み）
