# WhatsApp — 電話のタブ

> この文書は何か（専門用語なしの1行）: WhatsAppの「電話」タブを撮って、部品の大きさを数字にした記録。通話は一切していない。

親: [../README.md](../README.md) / 手順書: [../../../../handoff/app-visual-language/phone-capture-runbook.md](../../../../handoff/app-visual-language/phone-capture-runbook.md)

- 記録日: 2026-10-10 / 記録者: スマホ（Android）の Termux で動く Claude Code
- 端末: 画面 1080x2340px・密度480dpi（3倍）。**px ÷ 3 = dp**
- 元データ（写真・構造データ）は**リポジトリに入れていない**（手順書 §0-1）。この文書の数値はすべて下記コマンドの出力から機械集計した。
- 人の名前・メッセージ本文・電話番号・メールアドレス・アカウント名は**一切含めていない**（手順書 §0-2）。部品表には文字情報を出力しない設計にしている。

## 取得に使ったコマンド

```bash
# 前面のアプリを確認（これが目的のアプリでなければ撮らずに中止する）
adb shell dumpsys window | grep -m1 "mCurrentFocus="
# 写真
adb exec-out screencap -p > <名前>.png
# 部品の構造（位置・大きさ・押せるか）
adb shell uiautomator dump /sdcard/d.xml && adb pull /sdcard/d.xml
# 画面サイズと密度
adb shell wm size ; adb shell wm density
```

数値の出し方: 部品の位置・大きさは構造データの `bounds` から、色は写真の画素の最頻値から集計した（集計スクリプトは `png.py` / `analyze.py` 相当の処理＝目で見た推定値は使っていない）。

## 1. 全体

| 項目 | 値 |
|---|---|
| 部品の総数 | 58 |
| 押せる部品の数 | 6 |
| 押せる部品のうち44dp(132px)未満 | **1** |

## 2. 部品ごとの位置と大きさ

| 部品（アプリ内部の名札） | 左上(x,y)px | 大きさpx | 大きさdp | 押せる | 備考 |
|---|---|---|---|---|---|
| `(名札なし) FrameLayout` | 0,0 | 1080x2340 | 360x780 |  |  |
| `(名札なし) LinearLayout` | 0,0 | 1080x2295 | 360x765 |  |  |
| `(名札なし) FrameLayout` | 0,0 | 1080x2295 | 360x765 |  |  |
| `action_bar_root` | 0,0 | 1080x2295 | 360x765 |  |  |
| `root_view` | 0,0 | 1080x2295 | 360x765 |  |  |
| `window_size_calculator_view` | 0,0 | 1080x2295 | 360x765 |  |  |
| `main_container` | 0,0 | 1080x2295 | 360x765 |  |  |
| `(名札なし) LinearLayout` | 0,111 | 1080x2184 | 360x728 |  |  |
| `conversation_list_view_host` | 0,111 | 1080x2184 | 360x728 |  |  |
| `(名札なし) FrameLayout` | 0,111 | 1080x1942 | 360x647 |  |  |
| `pager_holder` | 0,111 | 1080x1942 | 360x647 |  |  |
| `pager` | 0,111 | 1080x1942 | 360x647 |  |  |
| `(名札なし) LinearLayout` | 0,111 | 1080x1942 | 360x647 |  |  |
| `calls_recyclerView` | 0,111 | 1080x1942 | 360x647 |  |  |
| `(名札なし) LinearLayout` | 0,628 | 1080x1076 | 360x359 |  |  |
| `text_layout` | 0,772 | 1080x788 | 360x263 |  |  |
| `(名札なし) ViewGroup` | 0,772 | 1080x788 | 360x263 |  |  |
| `header` | 72,772 | 936x788 | 312x263 |  |  |
| `header_image_view_inflated` | 285,772 | 510x474 | 170x158 |  |  |
| `headline` | 166,1318 | 748x85 | 249x28 |  |  |
| `description` | 72,1451 | 936x109 | 312x36 |  |  |
| `header` | 0,111 | 1080x168 | 360x56 |  |  |
| `toolbar_container` | 0,111 | 1080x168 | 360x56 |  |  |
| `toolbar` | 0,111 | 1080x168 | 360x56 |  |  |
| `(名札なし) TextView` | 48,151 | 126x88 | 42x29 |  |  |
| `(名札なし) LinearLayoutCompat` | 816,111 | 264x168 | 88x56 |  |  |
| `menuitem_search` | 816,123 | 144x144 | 48x48 | ○ |  |
| `menuitem_overflow` | 960,123 | 120x144 | 40x48 | ○ | **44dp未満** |
| `fabText` | 601,1837 | 431x168 | 144x56 | ○ |  |
| `bottom_nav_container` | 0,2053 | 1080x242 | 360x81 |  |  |
| `bottom_nav_divider` | 0,2053 | 1080x2 | 360x1 |  |  |
| `nav_phoenix_rounded_background_container` | 0,2055 | 1080x240 | 360x80 |  |  |
| `bottom_nav` | 0,2055 | 1080x240 | 360x80 |  |  |
| `(名札なし) ViewGroup` | 0,2055 | 1080x240 | 360x80 |  |  |
| `(名札なし) FrameLayout` | 0,2055 | 270x240 | 90x80 | ○ |  |
| `navigation_bar_item_icon_container` | 39,2091 | 192x96 | 64x32 |  |  |
| `navigation_bar_item_icon_view` | 87,2091 | 96x96 | 32x32 |  |  |
| `navigation_bar_item_labels_group` | 54,2202 | 161x93 | 54x31 |  |  |
| `navigation_bar_item_small_label_view` | 54,2202 | 161x57 | 54x19 |  |  |
| `(名札なし) FrameLayout` | 270,2055 | 270x240 | 90x80 | ○ |  |
| `navigation_bar_item_icon_container` | 309,2091 | 192x96 | 64x32 |  |  |
| `navigation_bar_item_icon_view` | 357,2091 | 96x96 | 32x32 |  |  |
| `navigation_bar_item_labels_group` | 284,2202 | 242x93 | 81x31 |  |  |
| `navigation_bar_item_small_label_view` | 284,2202 | 242x57 | 81x19 |  |  |
| `(名札なし) FrameLayout` | 540,2055 | 270x240 | 90x80 | ○ |  |
| `navigation_bar_item_icon_container` | 579,2091 | 192x96 | 64x32 |  |  |
| `navigation_bar_item_icon_view` | 627,2091 | 96x96 | 32x32 |  |  |
| `navigation_bar_item_labels_group` | 554,2202 | 242x93 | 81x31 |  |  |
| `navigation_bar_item_small_label_view` | 554,2202 | 242x57 | 81x19 |  |  |
| `(名札なし) FrameLayout` | 810,2055 | 270x240 | 90x80 |  |  |
| `navigation_bar_item_icon_container` | 849,2091 | 192x96 | 64x32 |  |  |
| `navigation_bar_item_active_indicator_view` | 849,2091 | 192x96 | 64x32 |  |  |
| `navigation_bar_item_icon_view` | 897,2091 | 96x96 | 32x32 |  |  |
| `navigation_bar_item_labels_group` | 904,2202 | 81x93 | 27x31 |  |  |
| `navigation_bar_item_large_label_view` | 904,2202 | 81x57 | 27x19 |  |  |
| `(名札なし) View` | 0,0 | 1080x111 | 360x37 |  |  |

## 3. 色（写真の画素の最頻色。括弧内は標本数）

| 領域 | 範囲 | 最頻色 上位2 |
|---|---|---|
| 上部バー | y=111〜279 | `#0a1014`(19647) / `#f7f8fa`(358) |
| 本文エリア | y=300〜2050 | `#0a1014`(185918) / `#21c063`(7249) |
| 下部ナビ | y=2055〜2295 | `#0a1014`(25401) / `#103529`(1695) |

## 4. この画面の構成

電話（通話履歴）のタブ。`selected="true"` が「電話」の表記に付き、本体は `calls_recyclerView`。

**注意**: この画面では通話履歴の項目を一切タップしていない（手順書 §0-5 で通話は禁止）。撮影のみ。

