# Phase 2c 設計 — ADR-127 登録リンクボタン色修正

**対象ADR**: ADR-127  
**recon**: docs/handoff/adr-127-phase2c/recon.md  
**日付**: 2026-06-11  
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 該当なし：1行の CSS クラス変更のみ。外部事例参照が必要な設計判断なし。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 未登録企業の登録リンクボタンがアクセントカラーで表示される | 手動 Test A: 未登録企業ページでボタン色目視確認 |
| 登録済み企業の登録リンクボタンがグレー disabled で表示される | 手動 Test A: 登録済み企業ページでボタン色目視確認 |

---

## 技術 How・KPI

- KPI: ボタン色が ADR-127 §4 要件を満たす（未登録=accent・登録済み=grey disabled）
- 技術選択: `btn-sm` に `btn-primary` クラスを追加（理由: `btn-primary:disabled` ルールがグレー表示を担うため）

---

## 弊害・トレードオフ

- なし（既存 CSS ルールを活用するのみ。スタイル副作用なし）

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | CompanyDetailPage.tsx の className 変更（1行） | Generator |

---

## 継続

- 完了後: Test A（ブラウザ目視）でしんごさんが確認
- 次フェーズ: ADR-127 Phase 3（change_billing / add_address フォーム）
