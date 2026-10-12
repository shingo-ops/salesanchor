# WhatsApp — 連絡先（グループ情報）の画面

> この文書は何か（専門用語なしの1行）: 会話の相手の情報画面を撮って、操作タイルや一覧行の大きさを数字にした記録。

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
| 部品の総数 | 90 |
| 押せる部品の数 | 18 |
| 押せる部品のうち44dp(132px)未満 | **5** |

## 2. 部品ごとの位置と大きさ

| 部品（アプリ内部の名札） | 左上(x,y)px | 大きさpx | 大きさdp | 押せる | 備考 |
|---|---|---|---|---|---|
| `(名札なし) FrameLayout` | 0,0 | 1080x2340 | 360x780 |  |  |
| `(名札なし) LinearLayout` | 0,0 | 1080x2295 | 360x765 |  |  |
| `(名札なし) FrameLayout` | 0,111 | 1080x2184 | 360x728 |  |  |
| `action_bar_root` | 0,111 | 1080x2184 | 360x728 |  |  |
| `search_container` | 0,111 | 1080x2184 | 360x728 |  |  |
| `(名札なし) LinearLayout` | 0,111 | 1080x2184 | 360x728 |  |  |
| `content` | 0,111 | 1080x2184 | 360x728 |  |  |
| `(名札なし) ListView` | 0,111 | 1080x2184 | 360x728 |  |  |
| `(名札なし) LinearLayout` | 0,111 | 1080x1567 | 360x522 |  |  |
| `header_placeholder` | 0,111 | 1080x408 | 360x136 |  |  |
| `group_details_card` | 0,519 | 1080x620 | 360x207 |  |  |
| `group_details_card_info_root` | 0,519 | 1080x620 | 360x207 |  |  |
| `group_title` | 276,519 | 527x145 | 176x48 | ○ |  |
| `group_details_card_subtitle` | 311,676 | 457x49 | 152x16 |  |  |
| `group_details_card_description` | 0,737 | 1080x113 | 360x38 | ○ | **44dp未満** |
| `no_description_view` | 72,749 | 936x77 | 312x26 |  |  |
| `group_details_actions` | 36,850 | 1008x289 | 336x96 |  |  |
| `action_call` | 36,886 | 264x217 | 88x72 | ○ |  |
| `action_tile_icon` | 72,886 | 192x144 | 64x48 |  |  |
| `action_tile_label` | 36,1054 | 264x49 | 88x16 |  |  |
| `action_videocall` | 300,886 | 264x217 | 88x72 | ○ |  |
| `action_tile_icon` | 336,886 | 192x144 | 64x48 |  |  |
| `action_tile_label` | 300,1054 | 264x49 | 88x16 |  |  |
| `action_add_person` | 564,886 | 264x217 | 88x72 | ○ |  |
| `action_tile_icon` | 600,886 | 192x144 | 64x48 |  |  |
| `action_tile_label` | 564,1054 | 264x49 | 88x16 |  |  |
| `action_search_chat` | 828,886 | 216x217 | 72x72 | ○ |  |
| `action_tile_icon` | 840,886 | 192x144 | 64x48 |  |  |
| `action_tile_label` | 828,1054 | 216x49 | 72x16 |  |  |
| `group_info_shortcuts_top_divider` | 0,1139 | 1080x50 | 360x17 |  |  |
| `(名札なし) View` | 0,1163 | 1080x2 | 360x1 |  |  |
| `group_info_shortcuts_bar_inflow` | 0,1189 | 1080x144 | 360x48 |  |  |
| `(名札なし) LinearLayout` | 0,1189 | 1080x144 | 360x48 |  |  |
| `(名札なし) LinearLayout` | 305,1189 | 235x144 | 78x48 |  |  |
| `(名札なし) TextView` | 341,1232 | 163x57 | 54x19 |  |  |
| `(名札なし) LinearLayout` | 540,1189 | 235x144 | 78x48 | ○ |  |
| `(名札なし) TextView` | 617,1232 | 81x57 | 27x19 |  |  |
| `participants_card` | 0,1333 | 1080x141 | 360x47 |  |  |
| `(名札なし) LinearLayout` | 0,1333 | 1080x141 | 360x47 |  |  |
| `participants_title` | 48,1333 | 924x141 | 308x47 |  |  |
| `participants_search` | 972,1333 | 108x141 | 36x47 | ○ | **44dp未満** |
| `add_participant_layout` | 0,1474 | 1080x204 | 360x68 |  |  |
| `add_participant_button` | 0,1474 | 1080x204 | 360x68 | ○ |  |
| `add_participant_icon` | 48,1516 | 120x120 | 40x40 |  |  |
| `add_participant_text` | 216,1542 | 336x68 | 112x23 |  |  |
| `group_chat_info_layout_root` | 0,1678 | 1080x204 | 360x68 | ○ |  |
| `group_chat_info_layout` | 0,1678 | 1080x204 | 360x68 |  |  |
| `private_ai_badge_container` | 0,1720 | 216x120 | 72x40 |  |  |
| `wdsProfilePicture` | 42,1720 | 132x120 | 44x40 | ○ | **44dp未満** |
| `(名札なし) LinearLayout` | 216,1717 | 822x125 | 274x42 |  |  |
| `(名札なし) LinearLayout` | 216,1717 | 822x68 | 274x23 |  |  |
| `(名札なし) LinearLayout` | 216,1717 | 533x68 | 178x23 |  |  |
| `name` | 216,1717 | 96x68 | 32x23 |  |  |
| `owner_view` | 773,1717 | 265x68 | 88x23 |  |  |
| `participant_label_view_text` | 216,1785 | 365x57 | 122x19 |  |  |
| `group_chat_info_layout_root` | 0,1882 | 1080x204 | 360x68 | ○ |  |
| `group_chat_info_layout` | 0,1882 | 1080x204 | 360x68 |  |  |
| `private_ai_badge_container` | 0,1924 | 216x120 | 72x40 |  |  |
| `wdsProfilePicture` | 42,1924 | 132x120 | 44x40 | ○ | **44dp未満** |
| `(名札なし) LinearLayout` | 216,1950 | 822x68 | 274x23 |  |  |
| `name` | 216,1950 | 143x68 | 48x23 |  |  |
| `(名札なし) LinearLayout` | 0,2086 | 1080x164 | 360x55 | ○ |  |
| `text` | 216,2134 | 816x68 | 272x23 |  |  |
| `(名札なし) LinearLayout` | 0,2250 | 1080x45 | 360x15 |  |  |
| `actions_card` | 0,2250 | 1080x45 | 360x15 |  |  |
| `(名札なし) FrameLayout` | 0,2250 | 1080x45 | 360x15 |  |  |
| `(名札なし) View` | 0,2274 | 1080x2 | 360x1 |  |  |
| `header` | 0,111 | 1080x408 | 360x136 |  |  |
| `picture` | 0,111 | 1080x288 | 360x96 |  |  |
| `photo_overlay` | 0,111 | 1080x288 | 360x96 |  |  |
| `toolbar` | 0,111 | 1080x168 | 360x56 |  |  |
| `wds_toolbar_nav_button` | 0,111 | 144x168 | 48x56 | ○ |  |
| `(名札なし) FrameLayout` | 768,171 | 48x48 | 16x16 |  |  |
| `(名札なし) LinearLayoutCompat` | 816,111 | 264x168 | 88x56 |  |  |
| `(名札なし) Button` | 816,123 | 144x144 | 48x48 | ○ |  |
| `menuitem_overflow` | 960,123 | 120x144 | 40x48 | ○ | **44dp未満** |
| `subject_layout` | 0,135 | 1080x384 | 360x128 |  |  |
| `collapsing_profile_photo_view` | 0,135 | 1080x384 | 360x128 |  |  |
| `profile_photo_container` | 348,135 | 384x384 | 128x128 |  |  |
| `wds_profile_picture` | 348,135 | 384x384 | 128x128 | ○ |  |
| `(名札なし) LinearLayout` | 0,309 | 1080x36 | 360x12 |  |  |
| `(名札なし) FrameLayout` | 936,351 | 144x168 | 48x56 |  |  |
| `(名札なし) View` | 0,0 | 1080x111 | 360x37 |  |  |
| `(名札なし) View` | 0,2295 | 1080x45 | 360x15 |  |  |

## 3. 色（写真の画素の最頻色。括弧内は標本数）

| 領域 | 範囲 | 最頻色 上位2 |
|---|---|---|
| ヘッダー | y=111〜519 | `#0a1014`(37189) / `#321622`(9702) |
| 情報カード | y=519〜1139 | `#0a1014`(61487) / `#23282c`(9720) |
| 操作タイル帯 | y=850〜1139 | `#0a1014`(21738) / `#23282c`(9724) |
| 参加者リスト | y=1333〜2100 | `#0a1014`(84165) / `#103529`(1735) |

