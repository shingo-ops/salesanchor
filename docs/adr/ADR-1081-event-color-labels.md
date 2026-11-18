# ADR-1081: 予定ごとの色は Google カレンダーの予定のラベル 24 色＋デフォルトにし、色の値で Google と照らす

| 項目 | 内容 |
|------|------|
| ステータス | Proposed（2026-11-19 PO が目標 K1〜K7 を承認。実装の承認と本番の GO はまだ） |
| 備考 | 昇格の条件: PO の実装承認と、本番での K1〜K4 の確かめの後。PO 2026-11-19「予定ごとの色」・「1. Google と同じ24色にする【おすすめ】」・目標に「1」 |
| 起案日 | 2026-11-19 |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-1057・ADR-1059（Google との行き来）、ADR-1065・ADR-1074（予定の画面の金型と `--gcal-*`）、ADR-1075（繰り返し）、ADR-067・ADR-144（トークンと金型）、ADR-027（i18n）、ADR-1037（移行のロック待ち）。設計: `docs/handoff/event-color/design.md`・調査: `docs/handoff/event-color/recon.md` |

---

## What（何を決めたか）

1. 予定の色は Google カレンダーの「予定のラベル」と同じ 24 色と「デフォルト」から選ぶ。24 色の鍵と値の正本は `backend/app/services/event_colors.py` 1 か所。
2. 色は各社の `calendar_events.color_key`（NULL＝デフォルト＝持ち主の色）に鍵で持つ。値の決まりで 24 個に限る。
3. Google へは `eventLabelId` と `eventLabelVersion=1` で送る。名札の id は持たず、カレンダーの名札の色の値と照らして、そのたびに探す。合う名札が無ければ色なしで送り、名札は作らない。
4. Google の色は、Google で作った予定についてだけ取り込む（アプリで作った予定は取り込まない今の決まりのまま）。古い `colorId` は読まない。
5. 画面の色は `--gcal-event-<鍵>`（`index.css`）と `--event-color-<鍵>`（`tokens.css`）のトークンだけで描く。色を選ぶ部品は新しい金型 `ColorSwatchPicker`。

## Why（なぜ）

- PO の決定が「Google と同じ 24 色」。Google の今の画面の色は名札で、古い 11 色（`colorId`）とは合わない（recon.md §5）。
- 名札の id はカレンダーごとに違うかが未確認。色の値で照らせば、どのカレンダーでも同じ鍵になる（design.md §5）。
- 鍵で持てば、値の決まりで 24 個に限れて、画面はトークンを通して描ける（目標 K7）。
- 名札を付ける版の指定は、`eventLabelId` が無いと名札を外す（Google の公式文書）。だから、色を持つ本文のときだけ版を指定する（design.md §6）。

## 代わりの案

- 古い 11 色・名札の id を持つ・色の値を持つ・アプリが名札を作る・自由な色。選ばなかった理由は design.md §5。

## 影響

- 各社の `calendar_events` に欄 1 つ（移行 1 本・危険な PR）。AI 用の写しの分類表に 1 行。
- Google の呼び出しが、書き込み 1 件と取り込み 1 回につき `calendars.get` 1 回増える。
- `--gcal-*` のトークン（ADR-1074 の持ち物）に 24 個を足す。
