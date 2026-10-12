# WhatsApp — 会話一覧（受信箱）

> この文書は何か（専門用語なしの1行）: WhatsAppの会話一覧を撮って、行の高さや押せる場所の大きさを数字にした記録。

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
| 部品の総数 | 161 |
| 押せる部品の数 | 29 |
| 押せる部品のうち44dp(132px)未満 | **2** |

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
| `conversations_coordinator_layout` | 0,111 | 1080x1942 | 360x647 |  |  |
| `conversation_container` | 0,111 | 1080x1942 | 360x647 |  |  |
| `(名札なし) RecyclerView` | 0,111 | 1080x1942 | 360x647 |  |  |
| `(名札なし) FrameLayout` | 0,279 | 1080x180 | 360x60 |  |  |
| `my_search_bar` | 0,291 | 1080x144 | 360x48 |  |  |
| `search_bar_inner_layout` | 36,291 | 1008x144 | 336x48 | ○ |  |
| `search_icon` | 48,303 | 120x120 | 40x40 |  |  |
| `search_text` | 168,330 | 876x65 | 292x22 |  |  |
| `(名札なし) FrameLayout` | 0,459 | 1080x24 | 360x8 |  |  |
| `contact_row_container` | 0,483 | 1080x228 | 360x76 | ○ |  |
| `row_addon_start` | 0,495 | 216x204 | 72x68 |  |  |
| `contact_selector` | 0,495 | 216x204 | 72x68 | ○ |  |
| `contact_photo` | 30,519 | 156x156 | 52x52 | ○ |  |
| `row_content` | 216,528 | 816x138 | 272x46 |  |  |
| `conversations_row_header` | 216,528 | 816x65 | 272x22 |  |  |
| `(名札なし) FrameLayout` | 216,528 | 610x65 | 203x22 |  |  |
| `conversations_row_contact_name` | 216,528 | 356x65 | 119x22 |  |  |
| `conversations_row_date` | 838,536 | 194x49 | 65x16 |  |  |
| `bottom_row` | 216,599 | 816x67 | 272x22 |  |  |
| `(名札なし) LinearLayout` | 216,599 | 744x67 | 248x22 |  |  |
| `(名札なし) FrameLayout` | 216,599 | 744x67 | 248x22 |  |  |
| `single_msg_tv` | 216,599 | 744x67 | 248x22 |  |  |
| `conversations_row_message_count` | 972,602 | 60x60 | 20x20 |  |  |
| `contact_row_container` | 0,711 | 1080x228 | 360x76 | ○ |  |
| `row_addon_start` | 0,723 | 216x204 | 72x68 |  |  |
| `contact_selector` | 0,723 | 216x204 | 72x68 | ○ |  |
| `contact_photo` | 30,747 | 156x156 | 52x52 | ○ |  |
| `row_content` | 216,756 | 816x138 | 272x46 |  |  |
| `conversations_row_header` | 216,756 | 816x65 | 272x22 |  |  |
| `(名札なし) FrameLayout` | 216,756 | 610x65 | 203x22 |  |  |
| `conversations_row_contact_name` | 216,756 | 354x65 | 118x22 |  |  |
| `conversations_row_date` | 838,764 | 194x49 | 65x16 |  |  |
| `bottom_row` | 216,827 | 816x67 | 272x22 |  |  |
| `(名札なし) LinearLayout` | 216,827 | 744x67 | 248x22 |  |  |
| `message_type_indicator` | 219,836 | 48x48 | 16x16 |  |  |
| `(名札なし) FrameLayout` | 279,827 | 681x67 | 227x22 |  |  |
| `single_msg_tv` | 279,827 | 681x67 | 227x22 |  |  |
| `conversations_row_message_count` | 972,830 | 60x60 | 20x20 |  |  |
| `contact_row_container` | 0,939 | 1080x228 | 360x76 | ○ |  |
| `row_addon_start` | 0,951 | 216x204 | 72x68 |  |  |
| `contact_selector` | 0,951 | 216x204 | 72x68 | ○ |  |
| `contact_photo` | 30,975 | 156x156 | 52x52 | ○ |  |
| `row_content` | 216,984 | 816x138 | 272x46 |  |  |
| `conversations_row_header` | 216,984 | 816x65 | 272x22 |  |  |
| `(名札なし) FrameLayout` | 216,984 | 610x65 | 203x22 |  |  |
| `conversations_row_contact_name` | 216,984 | 213x65 | 71x22 |  |  |
| `conversations_row_date` | 838,992 | 194x49 | 65x16 |  |  |
| `bottom_row` | 216,1055 | 816x67 | 272x22 |  |  |
| `(名札なし) LinearLayout` | 216,1055 | 744x67 | 248x22 |  |  |
| `(名札なし) FrameLayout` | 216,1055 | 744x67 | 248x22 |  |  |
| `single_msg_tv` | 216,1055 | 739x67 | 246x22 |  |  |
| `conversations_row_message_count` | 972,1058 | 60x60 | 20x20 |  |  |
| `contact_row_container` | 0,1167 | 1080x228 | 360x76 | ○ |  |
| `row_addon_start` | 0,1179 | 216x204 | 72x68 |  |  |
| `contact_selector` | 0,1179 | 216x204 | 72x68 | ○ |  |
| `contact_photo` | 30,1203 | 156x156 | 52x52 | ○ |  |
| `row_content` | 216,1212 | 816x138 | 272x46 |  |  |
| `conversations_row_header` | 216,1212 | 816x65 | 272x22 |  |  |
| `(名札なし) FrameLayout` | 216,1212 | 610x65 | 203x22 |  |  |
| `conversations_row_contact_name` | 216,1212 | 208x65 | 69x22 |  |  |
| `conversations_row_date` | 838,1220 | 194x49 | 65x16 |  |  |
| `bottom_row` | 216,1283 | 816x67 | 272x22 |  |  |
| `(名札なし) LinearLayout` | 216,1283 | 744x67 | 248x22 |  |  |
| `message_type_indicator` | 219,1292 | 48x48 | 16x16 |  |  |
| `(名札なし) FrameLayout` | 279,1283 | 681x67 | 227x22 |  |  |
| `single_msg_tv` | 279,1283 | 653x67 | 218x22 |  |  |
| `conversations_row_message_count` | 972,1286 | 60x60 | 20x20 |  |  |
| `contact_row_container` | 0,1395 | 1080x228 | 360x76 | ○ |  |
| `row_addon_start` | 0,1407 | 216x204 | 72x68 |  |  |
| `contact_selector` | 0,1407 | 216x204 | 72x68 | ○ |  |
| `contact_photo` | 30,1431 | 156x156 | 52x52 | ○ |  |
| `row_content` | 216,1440 | 816x138 | 272x46 |  |  |
| `conversations_row_header` | 216,1440 | 816x65 | 272x22 |  |  |
| `(名札なし) FrameLayout` | 216,1440 | 608x65 | 203x22 |  |  |
| `conversations_row_contact_name` | 216,1440 | 265x65 | 88x22 |  |  |
| `conversations_row_date` | 836,1448 | 196x49 | 65x16 |  |  |
| `bottom_row` | 216,1511 | 816x67 | 272x22 |  |  |
| `(名札なし) LinearLayout` | 216,1511 | 816x67 | 272x22 |  |  |
| `(名札なし) FrameLayout` | 216,1511 | 816x67 | 272x22 |  |  |
| `single_msg_tv` | 216,1511 | 623x67 | 208x22 |  |  |
| `contact_row_container` | 0,1623 | 1080x228 | 360x76 | ○ |  |
| `row_addon_start` | 0,1635 | 216x204 | 72x68 |  |  |
| `contact_selector` | 0,1635 | 216x204 | 72x68 | ○ |  |
| `contact_photo` | 30,1659 | 156x156 | 52x52 | ○ |  |
| `row_content` | 216,1668 | 816x138 | 272x46 |  |  |
| `conversations_row_header` | 216,1668 | 816x65 | 272x22 |  |  |
| `(名札なし) FrameLayout` | 216,1668 | 608x65 | 203x22 |  |  |
| `conversations_row_contact_name` | 216,1668 | 293x65 | 98x22 |  |  |
| `conversations_row_date` | 836,1676 | 196x49 | 65x16 |  |  |
| `bottom_row` | 216,1739 | 816x67 | 272x22 |  |  |
| `(名札なし) LinearLayout` | 216,1739 | 816x67 | 272x22 |  |  |
| `(名札なし) FrameLayout` | 216,1739 | 816x67 | 272x22 |  |  |
| `single_msg_tv` | 216,1739 | 623x67 | 208x22 |  |  |
| `contact_row_container` | 0,1851 | 1080x202 | 360x67 | ○ |  |
| `row_addon_start` | 0,1863 | 216x190 | 72x63 |  |  |
| `contact_selector` | 0,1863 | 216x190 | 72x63 | ○ |  |
| `contact_photo` | 30,1887 | 156x156 | 52x52 | ○ |  |
| `row_content` | 216,1896 | 816x138 | 272x46 |  |  |
| `conversations_row_header` | 216,1896 | 816x65 | 272x22 |  |  |
| `(名札なし) FrameLayout` | 216,1896 | 608x65 | 203x22 |  |  |
| `conversations_row_contact_name` | 216,1896 | 214x65 | 71x22 |  |  |
| `conversations_row_date` | 836,1904 | 196x49 | 65x16 |  |  |
| `bottom_row` | 216,1967 | 816x67 | 272x22 |  |  |
| `(名札なし) LinearLayout` | 216,1967 | 816x67 | 272x22 |  |  |
| `(名札なし) FrameLayout` | 216,1967 | 816x67 | 272x22 |  |  |
| `single_msg_tv` | 216,1967 | 623x67 | 208x22 |  |  |
| `header` | 0,111 | 1080x168 | 360x56 |  |  |
| `toolbar_container` | 0,111 | 1080x168 | 360x56 |  |  |
| `toolbar` | 0,111 | 1080x168 | 360x56 |  |  |
| `(名札なし) LinearLayout` | 48,111 | 600x168 | 200x56 |  |  |
| `toolbar_logo` | 48,171 | 600x63 | 200x21 |  |  |
| `(名札なし) LinearLayoutCompat` | 816,111 | 264x168 | 88x56 |  |  |
| `menuitem_camera` | 816,123 | 144x144 | 48x48 | ○ |  |
| `menuitem_overflow` | 960,123 | 120x144 | 40x48 | ○ | **44dp未満** |
| `extended_mini_fab` | 882,1657 | 126x120 | 42x40 | ○ | **44dp未満** |
| `(名札なし) LinearLayout` | 882,1657 | 126x120 | 42x40 |  |  |
| `extended_mini_fab_icon` | 906,1675 | 78x84 | 26x28 |  |  |
| `fab` | 864,1837 | 168x168 | 56x56 | ○ |  |
| `bottom_nav_container` | 0,2053 | 1080x242 | 360x81 |  |  |
| `bottom_nav_divider` | 0,2053 | 1080x2 | 360x1 |  |  |
| `nav_phoenix_rounded_background_container` | 0,2055 | 1080x240 | 360x80 |  |  |
| `bottom_nav` | 0,2055 | 1080x240 | 360x80 |  |  |
| `(名札なし) ViewGroup` | 0,2055 | 1080x240 | 360x80 |  |  |
| `(名札なし) FrameLayout` | 0,2055 | 270x240 | 90x80 |  |  |
| `navigation_bar_item_icon_container` | 39,2091 | 192x96 | 64x32 |  |  |
| `navigation_bar_item_active_indicator_view` | 39,2091 | 192x96 | 64x32 |  |  |
| `navigation_bar_item_icon_view` | 87,2091 | 96x96 | 32x32 |  |  |
| `navigation_bar_item_labels_group` | 54,2202 | 161x93 | 54x31 |  |  |
| `navigation_bar_item_large_label_view` | 54,2202 | 161x57 | 54x19 |  |  |
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
| `(名札なし) FrameLayout` | 810,2055 | 270x240 | 90x80 | ○ |  |
| `navigation_bar_item_icon_container` | 849,2091 | 192x96 | 64x32 |  |  |
| `navigation_bar_item_icon_view` | 897,2091 | 96x96 | 32x32 |  |  |
| `navigation_bar_item_labels_group` | 904,2202 | 81x93 | 27x31 |  |  |
| `navigation_bar_item_small_label_view` | 904,2202 | 81x57 | 27x19 |  |  |
| `(名札なし) View` | 0,0 | 1080x111 | 360x37 |  |  |

## 3. 色（写真の画素の最頻色。括弧内は標本数）

| 領域 | 範囲 | 最頻色 上位2 |
|---|---|---|
| ステータスバー | y=0〜111 | `#0a1014`(12453) / `#eeeeee`(433) |
| 上部バー | y=111〜279 | `#0a1014`(18839) / `#f7f8fa`(931) |
| 検索バーの中 | y=300〜430 | `#23282c`(10747) / `#8d9599`(538) |
| 一覧の背景（行の余白） | y=690〜710 | `#0a1014`(938) |
| 下部ナビ | y=2060〜2290 | `#0a1014`(24639) / `#103529`(1401) |
| 未読バッジ | y=602〜662 | `#21c063`(281) / `#0a1014`(86) |

## 4. 文字の実際の高さ（写真の画素のインクを測った値）

| 部品 | 枠の高さpx | 文字の実高px | dp |
|---|---|---|---|
| 名前 | 65 | 36 | 12.0 |
| プレビュー文 | 67 | 44 | 14.7 |
| 日付 | 49 | 29 | 9.7 |

**この数値の限界**: インクの高さは「その行に何の文字が書かれているか」で変わる（漢字・かな・英字で字面が違う）。したがってフォントサイズそのものではなく**下限値**として扱う。フォントサイズは構造データに含まれないため、この方法では確定できない。

## 5. 行の作り（この画面の設計の要点）

| 観測事実 | 値 |
|---|---|
| 行の高さ | 228px = 76dp（7行すべて同じ） |
| 行の間隔 | 228px（隙間ゼロで連続。行間に余白を持たせていない） |
| 行と行の区切り線 | **無い**（`bounds` 上で連続し、画素でも線を検出しない） |
| 押せる範囲 | `contact_row_container` が 1080x228px = 全幅・行全体 |
| 顔写真の左余白 | 30px = 10dp |
| 本文の開始位置 | 216px = 72dp |
| 右の余白 | 48px = 16dp |

## 6. 画面のつながりとタップ数（実測）

| 操作 | タップ数 | 根拠 |
|---|---|---|
| 一覧から会話を開く | **1** | 行をタップ → `com.whatsapp.Conversation` に遷移（前面の変化で確認） |
| 会話から一覧へ戻る | **1** | 戻る（keyevent 4） |
| 別の会話に移る | **2** | 戻る1 + 行タップ1 |
| タブを切り替える | **1** | 下部ナビをタップ |

補足: `am start com.whatsapp/.Main` でアプリを開くと**常にコミュニティのタブ**が選択された状態になる（`community_fragment` の有無で確認）。チャット一覧を出すには下部ナビの「チャット」を1回押す必要がある。

