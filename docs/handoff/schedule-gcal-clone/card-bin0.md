# カード 便0: 押した時刻で作る小窓を開く（G1）

設計: `docs/handoff/schedule-gcal-clone/design.md` §2 G1・§4 便0。原因: recon §2 B1。
成功条件の PO 承認: 2026-11-06（「1.」）。

## 枝と作業場所
- 起点 `origin/main`。枝 `release/schedule-slot-hour-fix`。`bash scripts/new-worktree.sh release/schedule-slot-hour-fix --claude` で作り、その中で作業する。

## 変えるもの（2 ファイルだけ）

### 1. `frontend/src/pages/schedule/SchedulePageImpl.tsx`（origin/main の 1574 行目）
変更前:
```tsx
                      onSelectSlot={(date, rect) => openCreate(date, rect)}
```
変更後:
```tsx
                      onSelectSlot={(date, rect) => openCreate(date, rect, date.getHours())}
```
この 1 行だけを変える。`openCreate`（:1237）・`WORKDAY_START`（:106）・月の表示の `onSelectDay`（:1550）・作るボタン（:1515）・近道 c（:1424）は触らない（月と作るボタンは今のまま 7 時で開く）。

### 2. `frontend/src/pages/schedule/SchedulePageImpl.test.tsx`
新しい `describe("SchedulePage slot click opens create at the clicked hour")` を 1 つ足す。
- 週の表示で、今日の列の `.schedule-slot` の 11 番目（10 時）を押す → 小窓の開始時刻の入力欄が `10:00`、終了が `11:00`。
- 同じく 5 番目（4 時）→ `04:00`／`05:00`、16 番目（15 時）→ `15:00`／`16:00`。
- 時刻の入力欄の探し方は、既存の試験と同じやり方（`screen` のロールか表示値）を使う。`container.querySelectorAll(".schedule-slot")` で枠を取ってよい（列は今日を含む週の列を使う）。

## 触らない範囲
- 上の 2 ファイル以外。css・トークン・文言（ja.json/en.json）・裏側は触らない。

## 確かめ
- Mac では試験を流さない。push して GitHub の CI（frontend の試験・lint・型）が緑になることで確かめる。
- 想定の分かれ道:
  - 枠の数が 24 でない・順番が違う → 試験を書き換えず BLOCKED: で止める。
  - 時刻の入力欄が `type="time"` 以外で値の形が `10:00` でない → 実物の値の形に合わせて試験を書く（中身の変更はしない）。

## commit と PR
- commit 文: `fix(schedule): open create popover at the clicked slot hour`。末尾 `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。
- PR は実装役は作らない（Opus が作る）。
