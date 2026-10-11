# AY-2d 変更後の実画面判定

方法: vite build→preview（Chromium headless shell 1217、DPR2）。API は page.route で /api/v1/public/register を同一 JSON でモック（{"valid":true,"company_name":"Sample Trading Co.","lead_id":1,"token_type":"register"}）。Firebase 初期化用に VITE_FIREBASE_* はダミー値でビルド（before/after 同一）。/register は「別の配送先を登録」を選択した状態（全入力欄を表示）で採取。

## 判定表

| 画面 | 幅 | DOM入力数 | scrollWidth/clientWidth before→after | 入力欄どうしの重なり before→after | ラベル文字との重なり before→after | 横はみ出し入力 after | tel 行が1行 after |
|---|---|---|---|---|---|---|---|
| register | 1280 | 27 | 1280/1280 → 1280/1280 | 2 → 0 | 0 → 0 | 0 | true,true |
| address | 1280 | 12 | 1280/1280 → 1280/1280 | 1 → 0 | 0 → 0 | 0 | true |
| change-billing | 1280 | 12 | 1280/1280 → 1280/1280 | 1 → 0 | 0 → 0 | 0 | true |
| register | 375 | 27 | 375/375 → 375/375 | 2 → 0 | 0 → 0 | 0 | true,true |
| address | 375 | 12 | 375/375 → 375/375 | 1 → 0 | 0 → 0 | 0 | true |
| change-billing | 375 | 12 | 375/375 → 375/375 | 1 → 0 | 0 → 0 | 0 | true |

## computed style の差（幅|プロパティ|before → after: 件数。DOM入力欄のべ件数）

| 幅 | プロパティ | before → after | 件数 |
|---|---|---|---|
| 1280 | border-top-color | rgb(118, 118, 118) → rgb(226, 232, 240) | 51 |
| 1280 | border-top-left-radius | 0px → 6px | 51 |
| 1280 | border-top-style | inset → solid | 51 |
| 1280 | border-top-width | 2px → 1px | 51 |
| 1280 | color | rgb(0, 0, 0) → rgb(26, 32, 44) | 51 |
| 1280 | font-family | Arial → -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif | 51 |
| 1280 | font-size | 13.3333px → 14.4px | 51 |
| 1280 | height | 19px → 39.6094px | 47 |
| 1280 | height | 25.5938px → 39.6094px | 4 |
| 1280 | line-height | normal → 21.6px | 51 |
| 1280 | padding-bottom | 0px → 8px | 51 |
| 1280 | padding-left | 0px → 12px | 51 |
| 1280 | padding-right | 0px → 12px | 51 |
| 1280 | padding-top | 0px → 8px | 51 |
| 1280 | width | 149px → 140px | 4 |
| 1280 | width | 149px → 600px | 43 |
| 375 | border-top-color | rgb(118, 118, 118) → rgb(226, 232, 240) | 51 |
| 375 | border-top-left-radius | 0px → 6px | 51 |
| 375 | border-top-style | inset → solid | 51 |
| 375 | border-top-width | 2px → 1px | 51 |
| 375 | color | rgb(0, 0, 0) → rgb(26, 32, 44) | 51 |
| 375 | font-family | Arial → -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif | 51 |
| 375 | font-size | 13.3333px → 14.4px | 51 |
| 375 | height | 19px → 44px | 47 |
| 375 | height | 25.5938px → 44px | 4 |
| 375 | line-height | normal → 21.6px | 51 |
| 375 | padding-bottom | 0px → 8px | 51 |
| 375 | padding-left | 0px → 12px | 51 |
| 375 | padding-right | 0px → 12px | 51 |
| 375 | padding-top | 0px → 8px | 51 |
| 375 | width | 149px → 140px | 4 |
| 375 | width | 149px → 375px | 43 |

差のあったプロパティ: border-top-color, border-top-left-radius, border-top-style, border-top-width, color, font-family, font-size, height, line-height, padding-bottom, padding-left, padding-right, padding-top, width

判定(はみ出し0・重なり0・tel1行): PASS

