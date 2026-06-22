# Phase 3 設計 — codex-schedule-i18n-main

**対象ADR**: ADR-027  
**recon**: docs/handoff/codex-schedule-i18n-main/recon.md  
**日付**: 2026-06-22  
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 該当なし: 今回は既存の正本 HTML と現行コード差分の整合が目的で、外部比較よりも repo 内の一次情報を優先する。

---

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| `dashboard` / `schedule` / `common` / `nav` の literal `t()` に対して、ja/en 両 locale に欠落がない | `npm run check:i18n-dashboard-schedule` |
| Schedule Settings ページが正本どおりの2カラムで描画され、右ペインに「他のメンバー」が食い込まない | `npm run build` 後に `Schedule Settings.dc.html` とスクリーンショットを突合 |
| `discordTicketConfig.welcomeTemplateDefault` が ja/en 両 locale に存在し、初期ウェルカム文言が i18n 経由で出る | `rg -n 'welcomeTemplateDefault' frontend/src/locales/{ja,en}.json` |

---

## 技術 How・KPI

- KPI: dashboard / schedule 周辺の生キー表示を 0 件にする。
- 技術選択: `frontend/scripts/check-i18n-dashboard-schedule.js` を追加し、`frontend/package.json` の `check:all` に組み込む。

---

## 弊害・トレードオフ

- literal `t()` のみを対象にしているため、動的キーは別途レビューが必要。
- 監視対象を `dashboard.` / `schedule.` / `common.` / `nav.` に絞ることで、誤検出よりも実務上の再発防止を優先する。

---

## 計画票

| ステップ | 内容 | 担当 |
|---|---|---|
| 1 | locale キーの不足を補完する | Generator |
| 2 | i18n ガードを追加し、`check:all` に接続する | Generator |
| 3 | Schedule Settings のレイアウトと文言の正本突合を確認する | Evaluator |

---

## 継続

- 今後の i18n 追加時は `ja.json` / `en.json` の同時更新を必須化する。
- 変更後は `check:i18n-dashboard-schedule` を通してから PR 化する。
