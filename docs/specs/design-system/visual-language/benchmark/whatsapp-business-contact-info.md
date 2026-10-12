# WhatsApp — 連絡先情報（ビジネスアカウント）

> この文書は何か（専門用語なしの1行）: 相手がビジネスアカウントの連絡先情報画面を撮って、営業時間などの部品の大きさを数字にした記録。

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
| 部品の総数 | 79 |
| 押せる部品の数 | 10 |
| 押せる部品のうち44dp(132px)未満 | **2** |

## 2. 部品ごとの位置と大きさ

| 部品（アプリ内部の名札） | 左上(x,y)px | 大きさpx | 大きさdp | 押せる | 備考 |
|---|---|---|---|---|---|
| `(名札なし) FrameLayout` | 0,0 | 1080x2340 | 360x780 |  |  |
| `(名札なし) LinearLayout` | 0,0 | 1080x2295 | 360x765 |  |  |
| `(名札なし) FrameLayout` | 0,111 | 1080x2184 | 360x728 |  |  |
| `action_bar_root` | 0,111 | 1080x2184 | 360x728 |  |  |
| `(名札なし) LinearLayout` | 0,111 | 1080x2184 | 360x728 |  |  |
| `content` | 0,111 | 1080x2184 | 360x728 |  |  |
| `(名札なし) ListView` | 0,111 | 1080x2184 | 360x728 |  |  |
| `header_placeholder` | 0,111 | 1080x607 | 360x202 |  |  |
| `business_details_card` | 0,718 | 1080x1465 | 360x488 |  |  |
| `(名札なし) LinearLayout` | 0,718 | 1080x497 | 360x166 |  |  |
| `business_title` | 344,718 | 392x97 | 131x32 |  |  |
| `business_subtitle` | 275,815 | 530x73 | 177x24 |  |  |
| `business_details_actions` | 36,888 | 1008x313 | 336x104 |  |  |
| `action_call` | 276,936 | 264x217 | 88x72 | ○ |  |
| `action_tile_icon` | 312,936 | 192x144 | 64x48 |  |  |
| `action_tile_label` | 276,1104 | 264x49 | 88x16 |  |  |
| `action_forward` | 540,936 | 264x217 | 88x72 | ○ |  |
| `action_tile_icon` | 576,936 | 192x144 | 64x48 |  |  |
| `action_tile_label` | 540,1104 | 264x49 | 88x16 |  |  |
| `(名札なし) View` | 0,1201 | 1080x2 | 360x1 |  |  |
| `business_profile_card` | 0,1215 | 1080x474 | 360x158 |  |  |
| `(名札なし) LinearLayout` | 0,1227 | 1080x450 | 360x150 |  |  |
| `business_hours` | 0,1227 | 1080x150 | 360x50 | ○ |  |
| `business_hours_icon` | 36,1227 | 150x150 | 50x50 |  |  |
| `business_hours_content_view` | 186,1227 | 750x131 | 250x44 |  |  |
| `business_hours_grid` | 186,1227 | 750x131 | 250x44 |  |  |
| `business_hours_day_layout_0` | 186,1227 | 750x131 | 250x44 |  |  |
| `business_hours_day_layout_title` | 222,1266 | 321x68 | 107x23 |  |  |
| `business_hours_day_layout_description` | 543,1266 | 393x68 | 131x23 |  |  |
| `business_hours_chevron_icon` | 936,1227 | 144x111 | 48x37 |  |  |
| `business_categories` | 0,1377 | 1080x150 | 360x50 |  |  |
| `field_icon` | 36,1377 | 150x150 | 50x50 |  |  |
| `business_field_layout` | 186,1377 | 894x146 | 298x49 |  |  |
| `field_textview` | 222,1377 | 480x107 | 160x36 |  |  |
| `business_profile_field_bottom_container` | 186,1484 | 894x39 | 298x13 |  |  |
| `business_location` | 0,1527 | 1080x150 | 360x50 | ○ |  |
| `field_icon` | 36,1527 | 150x150 | 50x50 |  |  |
| `business_field_layout` | 186,1527 | 894x146 | 298x49 |  |  |
| `field_textview` | 222,1527 | 96x107 | 32x36 |  |  |
| `business_profile_field_bottom_container` | 186,1634 | 894x39 | 298x13 |  |  |
| `add_business_to_contact` | 0,1689 | 1080x192 | 360x64 | ○ |  |
| `(名札なし) LinearLayout` | 0,1701 | 1080x168 | 360x56 |  |  |
| `list_item_with_left_icon` | 0,1701 | 1080x168 | 360x56 |  |  |
| `list_item_icon` | 72,1749 | 72x72 | 24x24 |  |  |
| `list_item_text_container` | 216,1751 | 816x68 | 272x23 |  |  |
| `list_item_title` | 216,1751 | 288x68 | 96x23 |  |  |
| `business_details_business_account` | 0,1881 | 1080x302 | 360x101 | ○ |  |
| `(名札なし) LinearLayout` | 0,1893 | 1080x278 | 360x93 |  |  |
| `list_item_with_left_icon` | 0,1893 | 1080x278 | 360x93 |  |  |
| `list_item_icon` | 72,1996 | 72x72 | 24x24 |  |  |
| `list_item_text_container` | 216,1941 | 816x182 | 272x61 |  |  |
| `list_item_title` | 216,1941 | 432x68 | 144x23 |  |  |
| `list_item_description` | 216,2009 | 762x114 | 254x38 |  |  |
| `actions_card` | 0,2183 | 1080x112 | 360x37 |  |  |
| `(名札なし) LinearLayout` | 0,2195 | 1080x100 | 360x33 |  |  |
| `notifications_and_sounds_layout` | 0,2195 | 1080x100 | 360x33 | ○ | **44dp未満** |
| `list_item_with_left_icon` | 0,2195 | 1080x100 | 360x33 |  |  |
| `list_item_icon` | 72,2243 | 72x52 | 24x17 |  |  |
| `list_item_text_container` | 216,2245 | 816x50 | 272x17 |  |  |
| `list_item_title` | 216,2245 | 96x50 | 32x17 |  |  |
| `header` | 0,111 | 1080x607 | 360x202 |  |  |
| `picture` | 0,111 | 1080x487 | 360x162 |  |  |
| `photo_overlay` | 0,111 | 1080x487 | 360x162 |  |  |
| `toolbar` | 0,111 | 1080x168 | 360x56 |  |  |
| `wds_toolbar_nav_button` | 0,111 | 144x168 | 48x56 | ○ |  |
| `(名札なし) FrameLayout` | 912,171 | 48x48 | 16x16 |  |  |
| `(名札なし) LinearLayoutCompat` | 960,111 | 120x168 | 40x56 |  |  |
| `menuitem_overflow` | 960,123 | 120x144 | 40x48 | ○ | **44dp未満** |
| `subject_layout` | 0,334 | 1080x384 | 360x128 |  |  |
| `collapsing_profile_photo_view` | 0,334 | 1080x384 | 360x128 |  |  |
| `profile_photo_container` | 348,334 | 384x384 | 128x128 |  |  |
| `wds_profile_picture` | 348,334 | 384x384 | 128x128 | ○ |  |
| `(名札なし) LinearLayout` | 0,508 | 1080x36 | 360x12 |  |  |
| `(名札なし) View` | 0,0 | 1080x111 | 360x37 |  |  |
| `(名札なし) View` | 0,2295 | 1080x45 | 360x15 |  |  |

## 3. 色（写真の画素の最頻色。括弧内は標本数）

| 領域 | 範囲 | 最頻色 上位2 |
|---|---|---|
| ヘッダー | y=111〜519 | `#0a1014`(43358) / `#f7f8fa`(81) |
| ビジネス情報カード | y=519〜1200 | `#0a1014`(68414) / `#23282c`(4883) |
| 操作タイル帯 | y=850〜1139 | `#0a1014`(26845) / `#23282c`(4917) |
| 下部 | y=1400〜2100 | `#0a1014`(79127) / `#8d9599`(1001) |

## 4. ビジネスアカウントの連絡先情報として取れたもの

テスト用の相手が WhatsApp Business アカウントのため、この画面には**ビジネスプロフィール**の部品が含まれる。salesanchor（B2B CRM）にとって最も近いお手本にあたる。

名札から確認できたビジネス関連の部品（文字情報は出力しない）:
`business_details_card` / `business_details_business_account` / `business_categories` / `business_hours` / `business_hours_grid` / `business_hours_day_layout_0` / `business_hours_day_layout_title` / `business_hours_day_layout_description` / `business_hours_chevron_icon` / `business_field_layout` / `add_business_to_contact` / `business_details_actions`

**設計の要点**: 営業時間は「曜日ごとの行（`business_hours_day_layout_*`）＋ 開閉用の矢印（chevron）」という形で、1つのカードの中に折りたためる表として置かれている。項目ごとに別画面へ飛ばしていない。

## 5. 到達の経緯（記録）

会話の上部バーの相手名をタップしたところ、先に**プライバシーのお知らせ**（`PrivacyDisclosureContainerActivity`・「WhatsAppで連絡先を管理する方法が広がりました」＋OKボタン）が被さって表示された。OK は設定変更に当たる恐れがあるため**押さず**、「戻る」で閉じた。その裏に `ContactInfoActivity` が既に開いていた。

