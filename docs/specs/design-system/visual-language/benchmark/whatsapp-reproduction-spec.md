# WhatsApp — 再現用の構造仕様

> この文書は何か（専門用語なしの1行）: WhatsApp の画面を「そっくり同じに作る」ために必要な、部品の入れ子と余白の数字。

親: [README.md](README.md) / 手順書: [../../../../handoff/app-visual-language/phone-capture-runbook.md](../../../../handoff/app-visual-language/phone-capture-runbook.md)

- 記録日: 2026-10-11 / 端末: 1080x2340px・密度480dpi（3倍）。**数字はすべて dp**（px ÷ 3）
- 取得元: `adb shell uiautomator dump` の `bounds` から、**親と子の座標の差**として余白を計算した。目で見た推定値は使っていない。
- 読み方: 行頭の字下げが入れ子の深さ。`<T>`=押せる / `<L>`=長押しできる / `<F>`=フォーカスできる。
- 文字情報（名前・本文）は出力していない。幅が部品ごとに違うのは中の文字数によるもので、**可変幅**として扱う。

## 1. 会話一覧の1行

```
contact_row_container [LinearLayout] 360x76dp  親からの余白: 左0 上124 右0 下447.3 <TLF>
  row_addon_start [FrameLayout] 72x68dp  親からの余白: 左0 上4 右288 下4 
    contact_selector [FrameLayout] 72x68dp  親からの余白: 左0 上0 右0 下0 <TLF>
      contact_photo [ImageView] 52x52dp  親からの余白: 左10 上8 右10 下8 <TLF>
  row_content [LinearLayout] 272x46dp  親からの余白: 左72 上15 右16 下15 
    conversations_row_header [LinearLayout] 272x21.7dp  親からの余白: 左0 上0 右0 下24.3 
      (FrameLayout) [FrameLayout] 244.3x21.7dp  親からの余白: 左0 上0 右27.7 下0 
        conversations_row_contact_name [TextView] 135x21.7dp  親からの余白: 左0 上0 右109.3 下0 
      conversations_row_date [TextView] 23.7x16.3dp  親からの余白: 左248.3 上2.7 右0 下2.7 
    bottom_row [LinearLayout] 272x22.3dp  親からの余白: 左0 上23.7 右0 下0 
      (LinearLayout) [LinearLayout] 272x22.3dp  親からの余白: 左0 上0 右0 下0 
        (FrameLayout) [FrameLayout] 272x22.3dp  親からの余白: 左0 上0 右0 下0 
          single_msg_tv [TextView] 50x22.3dp  親からの余白: 左0 上0 右222 下0
```

### 再現のための要点

| 決まり | 値 |
|---|---|
| 行の高さ | **76dp 固定**（隙間ゼロで連続。区切り線なし） |
| 行全体が押せる | `contact_row_container` が押せる＋長押しできる |
| **顔写真が別の当たり判定** | 行の中の `contact_selector`（72x68dp）が**独立して押せる**。行をタップ＝会話を開く、顔写真をタップ＝プロフィール写真。**当たり判定が入れ子になっている** |
| 顔写真の列 | 幅72dp。中の画像は52dp（左右10dp・上下8dpの余白） |
| 本文の塊 | 左72dp・右16dp・上下15dp の余白。高さ46dp |
| 1行目（名前の行） | 高さ21.7dp |
| 2行目（プレビューの行） | 高さ22.3dp。1行目との間は 46 − 21.7 − 22.3 = **約2dp** |
| 日付 | 名前の行の右端に置く。高さ16.3dp（上下2.7dpの余白）＝**名前より小さい文字** |
| 未読バッジ | 20x20dp。本文の塊の**右端ぴったり**（左252dp = 272 − 20） |
| 印（既読・音声など） | 16x16dp。プレビュー文の左に置き、文字の開始位置が21dp ずれる |
| 最下行 | 画面下で切れている（67.3dp）＝一覧に下方向の余白を持たせていない |

## 2. 会話画面の上部バー

```
toolbar [ViewGroup] 360x56dp  親からの余白: 左0 上0 右0 下0 
  custom_view [RelativeLayout] 272x56dp  親からの余白: 左0 上0 右88 下0 
    back [LinearLayout] 96x48dp  親からの余白: 左0 上4 右176 下4 
      whatsapp_toolbar_home [Button] 48x48dp  親からの余白: 左0 上0 右48 下0 <TF>
      contact_photo_view [FrameLayout] 48x48dp  親からの余白: 左48 上0 右0 下0 <TF>
        conversation_contact_photo [Button] 39x39dp  親からの余白: 左2.7 上4.3 右6.3 下4.7 
        transition_start [View] 40x40dp  親からの余白: 左4 上4 右4 下4 
    conversation_contact [LinearLayout] 176x56dp  親からの余白: 左96 上0 右0 下0 <TF>
      (FrameLayout) [FrameLayout] 172x22.7dp  親からの余白: 左4 上15.7 右0 下17.7 
        conversation_contact_name [TextView] 139.3x22.7dp  親からの余白: 左0 上0 右32.7 下0 
  (LinearLayoutCompat) [LinearLayoutCompat] 88x56dp  親からの余白: 左272 上0 右0 下0 
    (ImageButton) [ImageButton] 48x48dp  親からの余白: 左0 上4 右40 下4 <TLF>
    menuitem_overflow [ImageView] 40x48dp  親からの余白: 左48 上4 右0 下4 <TLF>
```

### 再現のための要点

| 決まり | 値 |
|---|---|
| 上部バーの高さ | **56dp** |
| 左の塊 | 96dp = 戻る48dp ＋ 顔写真48dp（隣接・隙間なし） |
| 顔写真 | 当たり判定48dp の中に画像39dp。別に `transition_start` 40dp がある＝**画面遷移で写真を引き継ぐ仕掛け** |
| 相手名 | 高さ22.7dp。上から15.7dp の位置（縦中央より少し上） |
| 右の塊 | 88dp = 通話48dp ＋ その他40dp |
| 相手名の領域も押せる | `conversation_contact`（176x56dp）が押せる＝名前をタップで連絡先情報へ |

## 3. 入力欄

```
footer [FrameLayout] 360x55.7dp  親からの余白: 左0 上616.3 右0 下0 
  emoji_popup_anchor [LinearLayout] 360x55.7dp  親からの余白: 左0 上0 右0 下0 
    edit_layout [ViewGroup] 360x55.7dp  親からの余白: 左0 上0 右0 下0 
      text_entry_layout [ViewGroup] 298.7x55.7dp  親からの余白: 左0 上0 右61.3 下0 
        voice_note_stub [FrameLayout] 286.7x48.3dp  親からの余白: 左8 上3.3 右4 下4 
        input_layout [LinearLayout] 286.7x48.3dp  親からの余白: 左8 上3.3 右4 下4 <TF>
          input_layout_content [ViewGroup] 286.7x48.3dp  親からの余白: 左0 上0 右0 下0 
            emoji_picker_btn [ImageButton] 48x48dp  親からの余白: 左0 上0 右238.7 下0.3 <TF>
            entry [EditText] 142.7x32.3dp  親からの余白: 左48 上7.7 右96 下8.3 <TLF>
            input_attach_button [ImageButton] 48x48dp  親からの余白: 左190.7 上0 右48 下0.3 <TLF>
            camera_btn [ImageButton] 48x48dp  親からの余白: 左238.7 上0 右0 下0.3 <TF>
      buttons [FrameLayout] 51.3x51.3dp  親からの余白: 左302.7 上2.3 右6 下2 
        conversation_entry_action_button [RelativeLayout] 48x48dp  親からの余白: 左0 上0 右3.3 下3.3 
          send_container [FrameLayout] 48x48dp  親からの余白: 左0 上0 右0 下0 
            voice_note_btn [ImageButton] 48x48dp  親からの余白: 左0 上0 右0 下0 <F>
```

### 再現のための要点

| 決まり | 値 |
|---|---|
| 入力欄の帯 | 高さ **55.7dp** |
| 丸い入力枠 | 286.7 x 48.3dp。左8dp・右4dp・上3.3dp・下4dp の余白 |
| 枠の中身 | 絵文字48dp（左端）→ 文字欄142.7x32.3dp（左48dp・上7.7dp）→ 添付48dp → カメラ48dp（右端） |
| 送信ボタンは枠の外 | `buttons` 51.3dp の中に48dp のボタン。右6dp・上2.3dp。**枠と並ぶ別の丸** |
| 文字欄の高さ | 32.3dp（枠48.3dp より小さく、上下に約8dp の余白） |

## 4. メッセージの吹き出し

```
conversation_row_text [ViewGroup] 360x42.7dp  親からの余白: 左0 上431.3 右0 下142.3 <L>
  main_layout [LinearLayout] 101x32.7dp  親からの余白: 左17 上5 右242 下5 
    conversation_text_row [FrameLayout] 101x32.7dp  親からの余白: 左0 上0 右0 下0 
      message_text [TextView] 62x28.7dp  親からの余白: 左2 上2 右37 下2 
      date_wrapper [LinearLayout] 35x16.3dp  親からの余白: 左64 上14.3 右2 下2 
        date [TextView] 23x16.3dp  親からの余白: 左6 上0 右6 下0
```

### 再現のための要点

| 決まり | 値 |
|---|---|
| 行 | 全幅360dp・高さ42.7dp。**長押しの対象は行全体**（吹き出しではない） |
| 吹き出し | **中身に合わせて縮む**（この例は101dp幅）。行の左から17dp |
| 吹き出しの上下余白 | 5dp ずつ |
| 本文 | 吹き出しの内側に2dp の余白 |
| 時刻 | 吹き出しの**中の右下に同じ行で**置く（左64dp・上14.3dp）。高さ16.3dp、左右に6dp の余白 |
| 時刻の分の確保 | 本文の右に37dp 空けてから時刻を置く＝本文と時刻が重ならないよう先に場所を取る |

## 5. 形と色（写真の画素から測定）

構造データに色と形は入っていないため、写真の画素から測った。方法: 部品の枠の内側60%の**最頻色**を塗りとし、その色と一致する画素の輪郭を列ごとに追って角の丸みを求めた。

| 部品 | 大きさ | 塗りの色 | 形 |
|---|---|---|---|
| 入力欄の枠 | 287x48dp | `#20272b`（枠内の91%） | 角丸 **約8px = 約2.7dp**（完全な丸ではない） |
| 送信ボタン | 48x48dp | `#21c063` | **完全な円**（輪郭が半径=高さの半分と一致） |
| 未読バッジ | 20x20dp | `#21c063` | **完全な円** |
| 一覧の顔写真 | 枠52dp | （写真） | **直径48dpの完全な円**。52dpの枠の中央に置かれ、周囲に約2dpの余白 |

顔写真は写真なので「塗りの一致」では測れない。背景との差で輪郭を追い、半径72.5px（24.2dp）の円と仮定したときの誤差が各列1px以内で一致したため、**直径145px = 48dp の円**と確定した。

**影**: 送信ボタンの下26pxの明るさを1pxずつ測ったが、単調な勾配は現れなかった（11,12,12,12,13,13,13,13,14,14 のあと別部品に当たる）。**影は描かれていない**。

## 6. この仕様でまだ確定できないもの

| 項目 | 理由 |
|---|---|
| **フォントサイズ** | 構造データに無い。文字枠の高さ（21.7 / 22.3 / 16.3dp）と画素のインク高さ（名前36px・プレビュー44px・日付29px）から**範囲**は絞れるが、確定値ではない |
| **吹き出しの角丸** | ダークモードで吹き出しの塗りと行の背景が近く、輪郭の判定が安定しない。ライトモードで撮り直せば測れる見込み |
| **アプリが「重要でない」と印を付けた部品** | 構造データに現れない |
