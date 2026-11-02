# ADR-1057: Google カレンダーの接続は会社で1つとし、送るのはつないだ本人の予定だけ・Google の予定を直接扱う口は本人だけ・Google→アプリの取り込みは止める

| 項目 | 内容 |
|---|---|
| ステータス | Accepted（2026-11-03・POの委任に基づくClaude Opus発行。方針の芯は PO 決定: 予定の画面につなぐボタンを戻し本番まで進める（選択「1」）・Google に送るのは PO が入れた予定だけ（選択「1」）） |
| 起案日 | 2026-11-03 |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-1018（tenant_google_calendar_config の RLS）、ADR-1056（チャット秘書。秘書の予定も同じ作成の口を通る）、ADR-027（i18n）、ADR-067・ADR-144（金型とデザイントークン） |
| 設計 | docs/handoff/schedule-gcal-connect/design.md（現在地: docs/handoff/schedule-gcal-connect/recon.md） |

---

## What（何を決めたか）

- Google カレンダーの接続は今のまま会社で1つ（`tenant_google_calendar_config` の1行）。中身はつないだ人（`connected_by_user_id`）の Google カレンダーである。
- アプリで予定を作ったとき Google に送るのは、作った人がつないだ本人のときだけ。ほかの人の予定は送らない（`calendar_service.create_event`）。
- Google の予定を直接読む・書く口（`/google-calendar/events` の GET・POST・PATCH・DELETE）は、つないだ本人だけが使える。ほかの人（管理者を含む）と未接続は 403。
- Google→アプリの取り込みを始める同期方式（bidirectional・read_only）は、同期方式の口（`PATCH /calendar/sync-mode`）で 422 にする。write_only・none への切り替えは今どおり。
- 予定の画面のヘッダーに、オーナー・システム管理者にだけ「Googleカレンダー連携」の ghost ボタンを出す。

## Why（なぜ）

- 接続は1人分の Google カレンダーなので、会社の全員の予定（個人の予定を含む）を送ると、ほかの人の予定がつないだ人の Google に入る。PO はこれを選ばなかった。
- 直接扱う口は、ログインしている会社の人なら誰でも呼べた。画面から呼ぶ所は無くても、直接呼べばつないだ人の Google の予定を読み書きできる。管理者に絞るだけでは、つないだ人と別の管理者が読める。
- 取り込みは Google の予定を `calendar_type='shared'`（会社の予定）としてアプリに入れる。誰が始めても、つないだ人の Google の中身が会社の全員に見える。今の目的（アプリの予定を PO の Google で見る）には要らない。
- 新しい表・列は作らず、今ある `connected_by_user_id` だけで判定できる。

## 受け入れた点

- つないだ本人が作って Google に送った予定を、ほかの管理者がアプリで直す・消すと、それも Google に反映される（今の予定の画面の権限どおり）。
- 本人以外のシステム管理者が「つなぐ」を押すと、接続がその人に入れ替わる。今の会社の管理者は PO だけで、製品は PO 本人が使う前提のため受け入れる。

## 戻し方

- 実装の PR を revert する。DB の形は変えない。
- つないだ後に外すときは `DELETE /google-calendar/connect`（管理者だけ）。

## 見直す条件

- Google→アプリの取り込みが要るとき、または PO 以外の人が自分の Google をつなぎたいとき（人ごとの接続が要る）。
