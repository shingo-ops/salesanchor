# AY-4c-2b recon: 予定表のカレンダーのチェック欄 2 件

- 作成: 2026-10-16 Opus / 基点 origin/main 8f6d089d6（AY-4c-2a #4348 マージ後）
- 元の recon: docs/handoff/ay4c2-checkbox/recon.md 項目 8・9（予定表の 2 件はここで調査済み）

## 既存 ADR 検索

- ADR-144（UI ガバナンス）、ADR-067（デザイントークン）。AY-4c-2a の recon の検索結果を引き継ぐ。新しく当たる ADR は無い。

## 現在地（行番号は審査 r1・r2 が 2a 入りの HEAD 7e23f117c で実測。8f6d089d6 は 7e23f117c の merge commit で、frontend の差分は無い）

- frontend/src/components/CheckboxControl.tsx:12-16 props の型（`style` は Omit 済み）
- frontend/src/pages/schedule/SchedulePageImpl.tsx:522-529 マイカレンダーの自分の行（`style={{ accentColor: owner.color }}`、disabled）
- frontend/src/pages/schedule/SchedulePageImpl.tsx:553-560 他のカレンダーの行（`style={{ accentColor: owner.color }}`）
- frontend/src/pages/schedule.css:242-248 `.schedule-calendar-checkbox`（寸法・margin・flex・cursor）
- frontend/src/pages/schedule/schedule-owner.ts:43 `owner.color` は必ず文字列（既定 #1a73e8）
- docs/specs/design-system/design.md:826 「Checkbox のデータ由来 accentColor は用途が限定された dataColor 入口へ移す」
- frontend/src 内の `dataColor` は 0 件（審査 r2: /tmp/CC報告ファイル/ssot-checkbox/ay4c2b/review-r2-*.txt）
- §8 の grep の現在値（審査 r2 実測 review-r2-s8.txt）: tsx の `type="checkbox"` 5 行、css 1 行、`schedule-calendar-checkbox` 3 行、tsx の accentColor 2 行

## PO 決定

- 2026-10-16 PO「y」: カレンダーのチェック欄はカレンダーの色のまま。CheckboxControl に dataColor の口を1つ足す。
