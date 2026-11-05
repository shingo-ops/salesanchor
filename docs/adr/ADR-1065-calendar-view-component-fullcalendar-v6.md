# ADR-1065: 予定の時間割と月の升目は FullCalendar v6 を包んだ金型 CalendarView で出す

| 項目 | 内容 |
|------|------|
| ステータス | Proposed（K1〜K9 が ○ になり、agent-console の予定画面で使われたら採用に上げる） |
| 備考 | PO 2026-11-06「1」：問い「FullCalendar を包んだ部品を部品集に登録して、予定画面に使う【おすすめ】」への答え |
| 起案日 | 2026-11-06 |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-067（トークン強制）、ADR-073（部品ごとの stories）、ADR-144（金型の登録）、ADR-027（文言は t()） |
| 設計・根拠 | [design.md](../handoff/calendar-view-component/design.md)、[recon.md](../handoff/calendar-view-component/recon.md)、[card.md](../handoff/calendar-view-component/card.md) |

---

## What（何を決めたか）

1. 時間割（1〜7列）と月の升目は、部品集の金型 `CalendarView`（frontend/src/components/CalendarView.*）で出す。中身は FullCalendar。
2. FullCalendar は v6 の 6.1.22 に固定する（`^` を付けない）。5つのパッケージは同じ版にする。
3. FullCalendar の型や名前は金型の外に出さない。呼ぶ側が見るのは `CalendarView` とその型だけ。
4. 見た目は FullCalendar の `--fc-*` 変数を全部トークンで上書きして決める。変数を通らない直書きの色は、セレクタで上書きするか、使わない機能の物だと記録する。試験が変数の漏れを数える。
5. 1時間の高さは `--schedule-row-height`（48px）。見積もりは点線、重なりは赤枠（`--danger`）。
6. 送るボタン・見出しは FullCalendar の物を使わず、呼ぶ側が金型 Button で置く。ドラッグ・選択は使わない。

## Why（なぜ）

- 2026-10-30 に FullCalendar 6.1.20 と Schedule-X を実際に動かして比べ、要る形（2列・7列・月・重なり横並び・いまの線の色・日本語）が全部そろったのは FullCalendar だった（agent-console design.md §15-1）。
- v6 は legacy の札だが 2026-10-16 に 6.1.22 が出て手入れが続いている。6.1.22 には React で止まらなくなる不具合の直しが入っている（recon §4）。
- v7 は見た目の仕組み（変数の名前・テーマ）が変わり、10/30 の比較が使えない（recon §4）。
- ページごとに作り込むと、時間割が2か所（Sales Anchor の予定ページと agent-console）に分かれる。金型1か所にする。

## v7 に上げる条件

- v6 の新しい版が12か月出ない、または v6 で直らない不具合・危険が見つかったら、v7 で同じ見本（stories 7つ）を作り直して比べる。変えるのは金型の中だけ。

## 受け入れるリスク

- v6 は実行時に `<style>` を差し込む。CSP で inline style を止める変更をするときは、この金型が崩れないかを先に確かめる（recon §8）。
- agent-console は同じ版の依存を自分で持つ必要がある。版がずれると見た目がずれる。agent-console の予定画面の設計で 6.1.22 に固定する。
- 地名つきの時刻は使わない。動かしている機械の時刻で出す。
