# 設計 — fedex-etd-step1-guide

**対象ADR**: ADR-137  
**recon**: docs/handoff/fedex-etd-step1-guide/recon.md  
**日付**: 2026-06-22  
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

- 事例: FedEx Developer Portal 公式 UI（2026-06-22 実機操作）→ 6サブステップ + 7スクリーンショットで手順を網羅
- ADR-129（Label Validation ウィザード）での段階的ガイドUI設計パターンを踏襲

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 連携ガイドタブ → ステップ1 に 1-1〜1-6 が表示される | 目視確認（FedExページ > 連携ガイドタブ > ステップ1） |
| 各サブステップに対応するスクリーンショットが表示される | 目視確認（7枚すべて） |
| テストキー / 本番キーの区別注記が最下部に表示される | 目視確認（`fedexEtdGuideStep1SandboxNote` キー） |
| ja.json / en.json にキーが同数追加されている | CI「Frontend lint & custom checks」PASS |
| migration / deploy.yml / 本番スクリプトが含まれない | `git diff --name-only origin/develop...HEAD` — frontend/ のみ確認済み |

---

## 技術 How・KPI

- 変更範囲: FE ガイド文言 + 画像 + locale + CSS のみ
- 新規 i18n キー: 8キー（ja + en）
- 画像: `frontend/public/images/fedex-setup/` 7枚（ADR-137 E4 対応）

---

## 弊害・トレードオフ

- スクリーンショット7枚（合計約1.4 MB）を `public/` に追加 → ビルドサイズ微増（許容範囲）
- ⑦（概要・キー）はマスク済み画像を使用。未マスクファイルはコミットしない

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | FedexEtdSetupGuide.tsx portal ステップ拡張 | Generator |
| 2 | CSS クラス追加 | Generator |
| 3 | i18n キー追加（ja/en） | Generator |
| 4 | スクリーンショット7枚配置 | Generator |

---

## 継続

- 完了後: スクリーンショットのマスク状態を本番で目視確認
- 次フェーズ: ETD ステップ2（apis）の詳細化は CTS 確認後（ADR-137 E1b 待ち）
