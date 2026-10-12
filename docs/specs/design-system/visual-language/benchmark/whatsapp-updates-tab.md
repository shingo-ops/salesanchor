# WhatsApp — アップデートのタブ

> この文書は何か（専門用語なしの1行）: WhatsAppの「アップデート」タブを撮って、部品の大きさを数字にした記録。

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
| 部品の総数 | 104 |
| 押せる部品の数 | 24 |
| 押せる部品のうち44dp(132px)未満 | **11** |

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
| `updates_list` | 0,111 | 1080x1942 | 360x647 |  |  |
| `(名札なし) ViewGroup` | 48,280 | 984x249 | 328x83 | ○ |  |
| `banner_icon` | 84,316 | 96x96 | 32x32 |  |  |
| `banner_description` | 228,316 | 672x177 | 224x59 |  |  |
| `dismiss_icon` | 924,316 | 72x72 | 24x24 | ○ | **44dp未満** |
| `(名札なし) ViewGroup` | 0,553 | 1080x129 | 360x43 |  |  |
| `header_textview` | 48,589 | 984x81 | 328x27 |  |  |
| `(名札なし) RelativeLayout` | 0,682 | 1080x228 | 360x76 | ○ |  |
| `container` | 0,682 | 1080x228 | 360x76 |  |  |
| `contact_selector` | 0,682 | 240x228 | 80x76 |  |  |
| `contact_photo` | 36,712 | 168x168 | 56x56 |  |  |
| `wdsProfilePicture` | 36,718 | 156x156 | 52x52 |  |  |
| `badge_click_surface` | 108,778 | 132x132 | 44x44 | ○ |  |
| `contact_mark` | 132,802 | 72x72 | 24x24 |  |  |
| `contact_text_container` | 240,730 | 840x132 | 280x44 |  |  |
| `contact_name` | 240,730 | 373x65 | 124x22 |  |  |
| `date_time` | 240,801 | 394x61 | 131x20 |  |  |
| `(名札なし) ViewGroup` | 0,910 | 1080x129 | 360x43 |  |  |
| `header_textview` | 48,946 | 984x81 | 328x27 |  |  |
| `(名札なし) LinearLayout` | 0,1039 | 1080x237 | 360x79 |  |  |
| `directory_description` | 48,1039 | 984x177 | 328x59 |  |  |
| `(名札なし) ViewGroup` | 0,1276 | 1080x138 | 360x46 |  |  |
| `header_textview` | 48,1312 | 870x57 | 290x19 |  |  |
| `addon_button` | 936,1282 | 96x120 | 32x40 | ○ | **44dp未満** |
| `newsletter_directory_row_container` | 0,1414 | 1080x228 | 360x76 | ○ |  |
| `newsletter_directory_photo_container` | 0,1414 | 240x228 | 80x76 |  |  |
| `newsletter_directory_photo` | 42,1450 | 156x156 | 52x52 | ○ |  |
| `newsletter_info_layout` | 240,1465 | 380x126 | 127x42 |  |  |
| `newsletter_name` | 240,1465 | 108x65 | 36x22 |  |  |
| `newsletter_follow_count` | 240,1530 | 380x61 | 127x20 |  |  |
| `quick_follow_button_container` | 620,1414 | 358x228 | 119x76 |  |  |
| `button_view` | 650,1462 | 298x120 | 99x40 | ○ | **44dp未満** |
| `inline_hide_button_stub` | 978,1501 | 54x54 | 18x18 | ○ | **44dp未満** |
| `newsletter_directory_row_container` | 0,1642 | 1080x228 | 360x76 | ○ |  |
| `newsletter_directory_photo_container` | 0,1642 | 240x228 | 80x76 |  |  |
| `newsletter_directory_photo` | 42,1678 | 156x156 | 52x52 | ○ |  |
| `newsletter_info_layout` | 240,1693 | 380x126 | 127x42 |  |  |
| `newsletter_name` | 240,1693 | 346x65 | 115x22 |  |  |
| `newsletter_follow_count` | 240,1758 | 380x61 | 127x20 |  |  |
| `quick_follow_button_container` | 620,1642 | 358x228 | 119x76 |  |  |
| `button_view` | 650,1690 | 298x120 | 99x40 | ○ | **44dp未満** |
| `inline_hide_button_stub` | 978,1729 | 54x54 | 18x18 | ○ | **44dp未満** |
| `newsletter_directory_row_container` | 0,1870 | 1080x183 | 360x61 | ○ |  |
| `newsletter_directory_photo_container` | 0,1887 | 240x166 | 80x55 |  |  |
| `newsletter_directory_photo` | 42,1923 | 156x130 | 52x43 | ○ | **44dp未満** |
| `newsletter_info_layout` | 240,1906 | 380x147 | 127x49 |  |  |
| `newsletter_name` | 240,1906 | 380x128 | 127x43 |  |  |
| `newsletter_follow_count` | 240,2034 | 380x19 | 127x6 |  |  |
| `quick_follow_button_container` | 620,1887 | 358x166 | 119x55 |  |  |
| `button_view` | 650,1935 | 298x118 | 99x39 | ○ | **44dp未満** |
| `inline_hide_button_stub` | 978,1974 | 54x54 | 18x18 | ○ | **44dp未満** |
| `header` | 0,111 | 1080x168 | 360x56 |  |  |
| `toolbar_container` | 0,111 | 1080x168 | 360x56 |  |  |
| `toolbar` | 0,111 | 1080x168 | 360x56 |  |  |
| `(名札なし) TextView` | 48,151 | 378x88 | 126x29 |  |  |
| `(名札なし) LinearLayoutCompat` | 816,111 | 264x168 | 88x56 |  |  |
| `menuitem_search` | 816,123 | 144x144 | 48x48 | ○ |  |
| `menuitem_overflow` | 960,123 | 120x144 | 40x48 | ○ | **44dp未満** |
| `extended_mini_fab` | 882,1657 | 126x120 | 42x40 | ○ | **44dp未満** |
| `(名札なし) LinearLayout` | 882,1657 | 126x120 | 42x40 |  |  |
| `extended_mini_fab_icon` | 918,1675 | 54x84 | 18x28 |  |  |
| `fab` | 864,1837 | 168x168 | 56x56 | ○ |  |
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
| `(名札なし) FrameLayout` | 270,2055 | 270x240 | 90x80 |  |  |
| `navigation_bar_item_icon_container` | 309,2091 | 192x96 | 64x32 |  |  |
| `navigation_bar_item_active_indicator_view` | 309,2091 | 192x96 | 64x32 |  |  |
| `navigation_bar_item_icon_view` | 357,2091 | 96x96 | 32x32 |  |  |
| `navigation_bar_item_labels_group` | 284,2202 | 242x93 | 81x31 |  |  |
| `navigation_bar_item_large_label_view` | 284,2202 | 242x57 | 81x19 |  |  |
| `(名札なし) FrameLayout` | 540,2055 | 270x240 | 90x80 | ○ |  |
| `navigation_bar_item_icon_container` | 579,2091 | 192x96 | 64x32 |  |  |
| `navigation_bar_item_icon_view` | 627,2091 | 96x96 | 32x32 |  |  |
| `navigation_bar_item_labels_group` | 554,2202 | 242x93 | 81x31 |  |  |
| `navigation_bar_item_small_label_view` | 554,2202 | 242x57 | 81x19 |  |  |
| `(名札なし) FrameLayout` | 810,2055 | 270x240 | 90x80 | ○ |  |
| `navigation_bar_item_icon_container` | 849,2091 | 192x96 | 64x32 |  |  |
| `navigation_bar_item_icon_view` | 897,2091 | 96x96 | 32x32 |  |  |
| `navigation_bar_item_labels_group` | 904,2202 | 81x93 | 27x31 |  |  |
| `navigation_bar_item_small_label_view` | 904,2202 | 81x57 | 27x19 |  |  |
| `(名札なし) View` | 0,0 | 1080x111 | 360x37 |  |  |

## 3. 色（写真の画素の最頻色。括弧内は標本数）

| 領域 | 範囲 | 最頻色 上位2 |
|---|---|---|
| 上部バー | y=111〜279 | `#0a1014`(19571) / `#f7f8fa`(369) |
| 本文エリア | y=300〜2050 | `#0a1014`(155621) / `#0a332c`(22623) |
| 下部ナビ | y=2055〜2295 | `#0a1014`(25500) / `#103529`(1556) |

## 4. この画面の構成

アップデート（ステータス／チャンネル）のタブ。`selected="true"` が「アップデート」の表記に付いていることで確認した。

一覧の行は `contact_row_container` ではなく別の作りで、チャット一覧（76dp固定）とは行の高さが異なる。部品表の各行の高さを参照のこと。

