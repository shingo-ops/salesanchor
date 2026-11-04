# design: 予定の画面の表示崩れ 3 件の直し（2026-11-04）

recon: `docs/handoff/schedule-labels-week-layout/recon.md`（以下 R§1〜R§4）
状態: 設計案作成済み・設計審査済み（§8）。PO 依頼は不具合の直し（原文は recon 冒頭）。

## 1. 目的（PO の言葉で）

予定の画面を開いたとき、予定の中身（題名と種類）が読めて、週の 7 日が 1 段に並ぶ。

## 2. 成功条件（PO が画面で ○× を付けられる形）

| # | 基準 | 検証方法 |
|---|---|---|
| K1 | 週表示の予定の箱に、Google や自分で入れた予定の題名が出る | 反映後に PO の画面（今回と同じ 11/1〜11/7 の週）で見る。題名の文字が箱の 1 行目にあれば ○ |
| K2 | 種類の札が「商談・打合せ」など日本語で出る。`schedule.calendarLabels` の文字が画面のどこにも出ない | 同じ画面で見る。英語設定では「Meetings」など |
| K3 | 横幅 1024px 以上の画面で、週の見出しの曜日と日付が日〜土の 7 列 1 段に並び、下の時間の列もそろう | 同じ画面で見る。土曜が 2 段目に落ちなければ ○ |
| K4 | 種類の言葉が設定の表から消えたら、機械が止める | 新しい試験。言葉を 1 つ消すと落ち、戻すと通る（実装報告に生出力） |
| K5 | 日表示（1 日だけ）は今まで通り 1 列で横幅いっぱい | 反映後に「日」に切り替えて見る |

## 3. 対象と対象外

- 対象: R§1 種類の言葉 7 個、R§2 題名が縮んで消える、R§3 週の 7 列が折れる、K4 の機械の見張り
- 対象外:
  - 色の直書きのトークン化（R§4・既知の残件。別テーマ）
  - 1023px 以下・767px 以下の狭い画面の並び（`schedule.css:1270-1272`・`:1288-1290`）の見直し。今の並びをそのまま保つ
  - 予定の箱の中の並び順・札の大きさ・時刻の出し方の変更
  - 裏側・DB・Google の取り込み

## 4. 変更前後（触るのは 4 ファイル＋書類）

### 4-1. `frontend/src/locales/ja.json`（`schedule` の中、`"settingsPermissionRequired"` の行の後ろ）

変更前（3247-3249 行目付近）:
```json
    "owner": "担当者",
    "settingsPermissionRequired": "この画面はマネージャーのみ利用できます"
  },
```
変更後:
```json
    "owner": "担当者",
    "settingsPermissionRequired": "この画面はマネージャーのみ利用できます",
    "calendarLabels": {
      "personal": "個人（担当者）",
      "meeting": "商談・打合せ",
      "procurement": "仕入・入荷",
      "shipping": "発送予定 / 集荷",
      "billing": "請求・入金期限",
      "release": "新商品の発売日",
      "holiday": "日本の祝日"
    }
  },
```
値は消える前（7bcc80e62）と 1 文字も変えない（R§1 の表）。

### 4-2. `frontend/src/locales/en.json`（`schedule` の中、`"owner": "Owner"` の行の後ろ）

変更前（3247-3249 行目付近）:
```json
    "settingsPermissionRequired": "This page is available to managers only.",
    "owner": "Owner"
  },
```
変更後:
```json
    "settingsPermissionRequired": "This page is available to managers only.",
    "owner": "Owner",
    "calendarLabels": {
      "personal": "Personal",
      "meeting": "Meetings",
      "procurement": "Purchasing / Inbound",
      "shipping": "Shipping / Pickup",
      "billing": "Billing / Payments",
      "release": "New Releases",
      "holiday": "Japan Holidays"
    }
  },
```

### 4-3. `frontend/src/pages/schedule.css`

(a) 題名を縮ませない（553-561 行目）。`width: 100%;` の次に 1 行足す:
```css
.schedule-event__title {
  ...（既存のまま）
  width: 100%;
  flex-shrink: 0;
}
```
1 時間の箱（48px）では題名 15px と種類の札 24px が入り、時刻は箱の外に切れる。時刻は 1.5 時間以上の箱と、押したときの吹き出しで見える。題名を優先する（予定の中身が分かることが PO の依頼の中心）。

(b) 週の列を 1 段に固定する（476-480 行目）。
変更前:
```css
.schedule-grid__days {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(var(--schedule-day-min-w), 1fr));
  min-width: 0;
}
```
変更後:
```css
.schedule-grid__days {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(0, 1fr);
  min-width: 0;
}
```
渡された日の数だけ等しい幅の列が 1 段に並ぶ（週は 7 列・日表示は 1 列）。画面の部品（TSX）は変えない。

(c) 狭い画面の並びを今のまま保つ。1270-1272 行目と 1288-1290 行目の `.schedule-grid__days { … }` の中に、それぞれ `grid-auto-flow: row;` を 1 行足す（既存の `grid-template-columns` の行は残す）。(b) で入れた「横に並べる」が狭い画面に効かないようにするため。

`--schedule-day-min-w`（15 行目）は 1271 行目で使い続けるので残す。

### 4-4. `frontend/src/features/schedule/calendars.config.test.ts`（新規）

`CALENDARS` の全部の `labelKey` について、`ja.json` と `en.json` の両方に空でない文字があることを確かめる。書き方は `frontend/src/pages/schedule/schedule-utils.test.ts:1-3` にならい JSON を import する。キーは `.` で区切ってたどる。種類ごとに 1 件ずつ（7 種類 × 2 言語）落ちたものが分かる形にする（`it.each` など）。

## 5. 代替案と選んだ理由

- 週の列: TSX から日の数を CSS 変数で渡し `repeat(var(--n), minmax(0,1fr))` にする案 → TSX と CSS の 2 か所に手が入り、`style` の直書きが増える。CSS だけで済む `grid-auto-flow: column` を選ぶ
- 週の列: `--schedule-day-min-w` を小さくするだけの案 → 横幅が足りない画面で再び折れる。根本の直しにならない
- 題名: 箱の高さを増やす案 → 時間の目盛りと合わなくなる。題名だけ縮ませない案を選ぶ
- 見張り: `check-i18n-missing-keys.js` を `labelKey:` まで見るよう広げる案 → 全画面に効き、他の画面の書き方を巻き込む。今回は予定の種類の表に絞った試験にとどめる

## 6. リスクと対処

- 週の列が狭い画面幅（1024px 付近）で 1 列 90px 程度になる → 見出しは曜日 1 字と日付の丸（46px）なので収まる。予定の題名は省略記号「…」で切れる（既存の `text-overflow: ellipsis`）
- 1 時間の箱で時刻が見えなくなる → §4-3(a) の通り、吹き出しで見える。PO が時刻も必要と言えば次の便で箱の並びを直す
- 戻し方: この PR の revert（DB・裏側の変更なし）

## 7. 外部事例

不要。理由: 既に動いていた言葉の復元と、CSS の並びの不具合の直しで、新しい仕組みを入れないため。

## 8. 設計審査（同一 AI による自己審査・独立した第二者レビューではない）

- 既存仕様・ADR との整合: ADR-027（キーを ja/en 同時に足す）、ADR-067・ADR-144（色の直値・生の部品を足さない。CSS は既存トークンのみ、新しい色なし）に沿う
- 根拠: 3 件とも file:line・git の記録・実測（題名 0px → 15px）で裏付け済み
- 受入条件の検証可能性: K1〜K3・K5 は PO の画面、K4 は試験の生出力で ○× が付く
- 実装範囲: 4 ファイル、変更前後を全部書いた
- 判定: **APPROVE**。未解決事項なし

## 9. 維持する仕組み

- K4 の試験が CI（frontend の unit）で毎回走る。種類の言葉が再び消えると PR が赤くなる

## 10. 実装カード（クラウドの Sonnet 向け）

1. `release/schedule-labels-week-layout` を取得し、`./scripts/dev/executor-preflight.sh` を通す
2. 先に §4-4 の試験だけ足し、`cd frontend && npx vitest run --config vitest.unit.config.ts --project unit src/features/schedule/calendars.config.test.ts` が **14 件落ちる**ことを生出力で残す
3. §4-1・§4-2 を足し、同じ試験が **14 件通る**ことを生出力で残す
4. §4-3(a)(b)(c) を足す
5. `cd frontend && npm run check:all` と `npx vitest run --config vitest.unit.config.ts --project unit src/pages/schedule src/features/schedule` を流し、生出力を残す
6. ja.json の `meeting` を 1 つ消すと試験が落ち、戻すと通ることを確かめて生出力を残す（戻し忘れ禁止）
7. 実装報告 `docs/handoff/schedule-labels-week-layout/impl-report-1.md` に 2〜6 の生出力を書く
8. 触らない: 上記 4 ファイルと実装報告以外。特に `calendars.config.ts`・`SchedulePageImpl.tsx`・色の値
9. 想定分岐: 2 で落ちる件数が 14 でない／4-3 で stylelint などの点検が落ちる／ja.json の行番号が設計とずれる → 直さずに `BLOCKED:` で止まり、生出力を添えて報告する
10. commit して push。PR は作らない（Opus が作る）
