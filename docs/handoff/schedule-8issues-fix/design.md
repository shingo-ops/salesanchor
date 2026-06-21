# 設計 — schedule-8issues-fix

**対象ADR**: ADR-027  
**recon**: docs/handoff/schedule-8issues-fix/recon.md  
**日付**: 2026-06-21  
**担当**: Generator

---

## 外部・過去事例の参照と我々への応用

該当なし：本PRは既存コードの本番バグ修正（ハング・レイアウトズレ・重複要素）であり、外部設計事例の参照は不要と判断。各修正の根拠は recon.md の file:line 引用に基づく。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| #8: getIdToken() タイムアウト時に 10秒以内でスピナーが消える | `Promise.race` 実装確認 `api.ts:49-57` + `finally` 到達確認 `SchedulePageImpl.tsx:866-869` |
| #1: スケジュールページ左端に 24px ガター（他ページと統一） | 本番 /schedule をハードリロード → DevTools で `.schedule-page` の `padding-left` = 24px 確認 |
| #7: 右上アバターとヘッダーツールバーが重ならない | 本番 /schedule でツールバーの右端 < アバター左端を目視確認 |
| #4: カレンダーラベルが日本語で表示（個人・商談等） | 本番 /schedule サイドバーのカレンダーリストで日本語ラベル確認 |
| #6: Today/‹›/期間ラベルが左、ツール類が右 | 本番 /schedule ヘッダー目視確認 |
| #2: サイドバーが単一フラットパネル（カード入れ子なし） | 本番 /schedule サイドバー目視確認 |
| #3: 新規作成ボタンが auto 幅・アイコンとテキスト中央揃え | 本番 /schedule サイドバーの「新規作成」ボタン目視確認 |
| #5: ヘッダーのブランドアイコン（favicon img）が消え、タイトルは残る | 本番 /schedule ヘッダー目視確認 |

---

## 技術 How・KPI

- KPI: 8件の本番バグが全て解消（最悪10秒以内にスピナー消えること）
- #8: `Promise.race` パターン — `getIdToken()` の AbortController 保護圏外問題を解消
- #1/#7: 既存デザイントークン（`--page-padding-x`、`--page-header-avatar-clearance`）を再利用、新規トークン追加ゼロ
- #6: JSX ヘッダー分割（左ブロック: nav、右ブロック: tools）
- #2/#3: CSS cardスタイル削除 + `fullWidth` prop 削除でフラット化

---

## 弊害・トレードオフ

- #8 タイムアウト後のUX: エラーメッセージは表示されず空カレンダーになる（`Promise.allSettled` が reject を吸収するため `catch` に到達しない）。10秒待ちは避けられないが、ループ永久スピナーよりは改善。
- #1 top padding 追加: `--page-padding-y` (10px) も追加されるが既存ページと統一であり問題なし。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | P0: `api.ts` + `ja.json`/`en.json` 修正 | Generator |
| 2 | P1: `schedule.css` padding 追加 | Generator |
| 3 | P2: `SchedulePageImpl.tsx` + `schedule.css` 構造修正 | Generator |
| 4 | ビルド確認（tsc + vite）| Generator |
| 5 | 本番デプロイ後 /schedule ハードリロードで KPI 8点確認 | Shingo |

---

## 継続

- 完了後の監視: 本番 /schedule を Cmd+Shift+R でハードリロードし 8点 KPI を目視確認
- #4 の確認: deploy 後にカレンダーラベルが日本語表示されることを本番で確認
