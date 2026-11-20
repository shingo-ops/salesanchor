# 実装カード 便1 直し1（予定の色・Google の名札の色の欄の名前）

- 設計: docs/handoff/event-color/design.md §4-4（名札の表）・recon.md §5（名札の各件は id と `backgroundColor`）・ADR-1081
- 枝: release/event-color-label-field-fix（origin/main d4bea69c1 起点）
- 実装役: クラウドの Sonnet。Opus がカードを書いた。PO の実装承認: 2026-11-20「1」（直す作業に進む）。

## 1. なぜ（本番の事実・2026-11-20 Opus 実測）

- PO がアプリで予定「テスト」を黄色にした。本番 DB の color_key は `banana`。Google 側の予定には名札も colorId も無い（Google の画面は青のまま）。
- PO が Google で予定「豊田自動車　期間工面接」を黄色にした。Google 側は colorId "5"。本番 DB の color_key は空（02:43:16 UTC に取り込みで更新済み）。
- 原因: `backend/app/services/google_calendar.py:408` が名札の色を `label.get("color")` で読む。Google の公開の API 説明（discovery revision 20261115）の `EventLabel` の欄は `id`・`name`・`backgroundColor` だけで、`color` は無い。だから名札の表は毎回 {} になり、送る側は `eventLabelId=""`、取り込む側は NULL になった。
- 試験の偽物（`backend/tests/test_calendar_service.py:2333`・`:2390`）も `"color"` で書いていたので通ってしまった。設計書に欄の名前を書き入れ忘れたのが Opus の漏れ。

## 2. 触るファイル（この 2 つだけ）

1. `backend/app/services/google_calendar.py`
   - `:408` 前: `        color = label.get("color")`
   - `:408` 後: `        color = label.get("backgroundColor")`
   - ほかの行は変えない。
2. `backend/tests/test_calendar_service.py`
   - `:2333` の `_LABELS` の 2 件の `"color"` を `"backgroundColor"` に変える（値はそのまま）。
   - `:2390` の `{"id": "L-red", "color": "#d50000"}` の `"color"` を `"backgroundColor"` に変える。
   - `TestGoogleToolEventLabel` の最後に試験を 2 本足す:
     - `test_label_without_background_color_is_ignored`: 名札が `[{"id": "L-x", "color": "#d50000"}]`（欄の名前が違う）のとき、`get_event_label_colors` が `{}` を返す。
     - `test_vendored_discovery_event_label_uses_background_color`: 入っている `googleapiclient` の同梱の API 説明 `googleapiclient/discovery_cache/documents/calendar.v3.json` を開き、`schemas.EventLabel.properties` に `backgroundColor` があり `color` が無いこと。ファイルの場所は `pathlib.Path(googleapiclient.__file__).parent / "discovery_cache" / "documents" / "calendar.v3.json"`。ファイルが無い・`EventLabel` が無いときは skip せずに落とす（Google の形が変わったら気づくため）。

## 3. 触らない

- `backend/app/services/calendar_service.py`・`google_webhook.py`・`event_colors.py`・画面のファイル・migrations・docs。

## 4. 確かめ（生の出力をファイルに残し、最後に結果の行を書く）

- `cd backend && python -m pytest tests/test_calendar_service.py -q` が全部通る（新しい 2 本を含む）。
- `cd backend && python -m pytest tests/test_event_colors_tokens.py tests/test_google_webhook*.py -q` が通る（無いファイルは外してよい）。
- `cd backend && python -c "import googleapiclient;print(googleapiclient.__version__)"` の出力を書く。
- `git diff origin/main --stat` が上の 2 ファイル＋このカードだけ。

## 5. 止まる条件

- 確かめが 1 つでも落ちたら、直さずに `NEEDS_DECISION:` で出力を添えて止まる。
- 2 ファイル以外を変えたくなったら止まる。
- commit は 1 つ。文: `fix(calendar): 名札の色を backgroundColor で読む（ADR-1081・K3/K4）`。push は `git push origin release/event-color-label-field-fix`（force は使わない）。
