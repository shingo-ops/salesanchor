# 実装カード 便2 直し1（予定ごとの色・色の値の置き場所）

- 設計: docs/handoff/event-color/design.md §4-7（2026-11-20 の直し）・ADR-1081 決定 5
- 枝: release/event-color-bin2-impl（PR #5616 の枝。新しい枝は作らない）
- 実装役: クラウドの Sonnet。Opus がカードを書いた。

## 1. なぜ

PR の確かめ `guard-hex-increase` が赤。`frontend/src/index.css` に足した `--gcal-event-*` 48 行が、色の直書きの数の見張り（`scripts/check-design-token-ratchet.sh`）に数えられた（171→219）。
見張りは `frontend/src/tokens.css` を数えない（`scripts/check-design-token-ratchet.sh:62`〜`:64`）。色の値を `tokens.css` の 1 か所に置けば、見張りを変えずに済み、置き場所も 1 つになる。

## 2. 触るファイル（この 3 つだけ）

1. `frontend/src/index.css`
   - 消す: 明るい画面の `:207`〜`:231`（説明の 1 行と `--gcal-event-*` 24 行）。
   - 消す: 暗い画面の `:448`〜`:472`（同じく説明の 1 行と 24 行）。
   - 結果: `git diff origin/main -- frontend/src/index.css` が空になること。
2. `frontend/src/tokens.css`（`:646`〜`:670`）
   - 前: `--event-color-radicchio:       var(--gcal-event-radicchio);` の形が 24 行。
   - 後: 値をそのまま書く。説明の行は次の 1 行にする。
     `/* ── 予定ごとの色（ADR-1081）。Google の予定のラベル 24 色。値の正本は backend/app/services/event_colors.py（試験で照らす）。部品と画面はこちらを使う ── */`
   - 24 行の値（並びも同じ）:
     ```
     --event-color-radicchio:       #ad1457;
     --event-color-cherry-blossom:  #d81b60;
     --event-color-flamingo:        #e67c73;
     --event-color-tomato:          #d50000;
     --event-color-tangerine:       #f4511e;
     --event-color-pumpkin:         #ef6c00;
     --event-color-mango:           #f09300;
     --event-color-banana:          #f6bf26;
     --event-color-citron:          #e4c441;
     --event-color-avocado:         #c0ca33;
     --event-color-pistachio:       #7cb342;
     --event-color-basil:           #0b8043;
     --event-color-sage:            #33b679;
     --event-color-eucalyptus:      #009688;
     --event-color-peacock:         #039be5;
     --event-color-cobalt:          #4285f4;
     --event-color-lavender:        #7986cb;
     --event-color-blueberry:       #3f51b5;
     --event-color-wisteria:        #b39ddb;
     --event-color-amethyst:        #9e69af;
     --event-color-grape:           #8e24aa;
     --event-color-cocoa:           #795548;
     --event-color-graphite:        #616161;
     --event-color-birch:           #a79b8e;
     ```
   - 暗い画面の区画（`:root.force-dark`・`:685`〜）には足さない（v1 は暗い画面も同じ値）。
3. `backend/tests/test_event_colors_tokens.py`
   - `_TOKEN_RE` を `r"--event-color-([a-z0-9-]+):\s*(#[0-9a-fA-F]+);"` に変える。
   - `test_light_tokens_match_backend_values` → `test_tokens_css_values_match_backend`: `frontend/src/tokens.css` の `:root {` の塊（`_block(text, ":root {")`）から拾い、24 個で `EVENT_COLORS` と同じ。
   - `test_dark_tokens_have_same_keys` → `test_index_css_has_no_event_colors`: `frontend/src/index.css` の全文に `--gcal-event-` も `--event-color-` も無い。
   - `test_semantic_tokens_in_tokens_css` は消す（上の 2 本で足りる）。
   - `test_frontend_key_list_matches_backend_order`・`test_locales_have_all_color_labels` はそのまま。

## 3. 触らない

- `scripts/check-design-token-ratchet.sh`（例外を足さない。足すには PO の承認が要る）。
- `frontend/src/pages/schedule/eventColors.ts`（`var(--event-color-…)` を返すのは変わらない）。ほかの画面のファイル。
- docs（Opus が直し済み）。

## 4. 確かめ（全部の生の出力をファイルに残し、最後に結果の行を書く）

- `cd frontend && npm run check:all` が rc=0。
- `cd frontend && npx vitest run src/pages/schedule src/components/ColorSwatchPicker.test.tsx` が全部通る。
- `cd backend && python -m pytest tests/test_event_colors_tokens.py -q` が 4 passed。
- `BASE_SHA=$(git merge-base origin/main HEAD) HEAD_SHA=HEAD bash scripts/check-design-token-ratchet.sh` が `PASS`。
- `git diff origin/main --stat -- frontend/src/index.css` が空。

## 5. 止まる条件

- 上の確かめが 1 つでも落ちたら、直さずに `NEEDS_DECISION:` で出力を添えて止まる。
- 3 ファイル以外を変えたくなったら止まる。
- commit は 1 つ。文: `fix(schedule): 予定の色の値を tokens.css の 1 か所へ（ADR-1081・色の数の見張り）`。push は `git push origin release/event-color-bin2-impl`（force は使わない）。
