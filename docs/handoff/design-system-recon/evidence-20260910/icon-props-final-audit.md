# Icon / Spinner props 最終読み取り照合

基準: main `23413b10f29228ffce7c7bf0813649b1910cf6bb`。2026-09-10の本照合で `git rev-parse HEAD`、`git status --short -- frontend/src`（出力なし）を実行。製品変更なし。以下の案は設計担当案であり、PO自筆決定や実装済み記録ではない。

## 観測事実

パスは frontend/ 基準。

| 対象 | 公開props/実物 | 実在する使用 |
|---|---|---|
| 通常Icon | src/constants/icons.tsx:23: size number|string、color string、weight string、className、style CSSProperties。:98でforwardRef、:101でrefを同じSVGへ渡す。:99既定size24。color/styleを:104/:106へ渡す。weightは受け取らず使用しない | 呼出側color指定0、ref指定0、spread0。style指定はGoogleCalendarStatusBar.tsx:168の1か所: marginRight=var(--space-2)、flexShrink=0。:150のcfg.Iconは:112以降のCheck/Xから選ぶ。固定色やwidth/heightのstyle指定ではない |
| PlatformIcon | icons.tsx:312: platformとsize?:numberのみ、既定16。style/color/ref/spread/tone APIなし。:317/336以降でsize×0.7/0.70/0.80/0.72をMath.roundし内側画像寸法に使う | InboxConversationList.tsx:219の1か所、platform=conv.platform、size=ICON.base(20)。内部spanのstyleはwidth/heightだけ(:319,329,343)。mailの内部EnvelopeIconのみcolor=white(:320) |
| LeadChatIcon | icons.tsx:407: size?:number（既定20）/classNameのみ。native SVGへwidth/height、aria-hidden=trueを明示。ref/style/color/spread APIなし | DesktopShell.tsx:249、MobileShell.tsx:248の2か所。いずれもsize=ICON.base(20)。後者のaria-hidden呼出属性は関数では受け取らないが、出力側に常時true指定あり |
| Spinner | src/components/loading/Spinner.tsx:5–14: size sm/md/lg、color、onAccent、className、label。style/ref/tone/spread APIなし。:22でcolorがあればborderTopColorだけの内部styleを生成。:26はspan | Button.tsx:81（size=sm,onAccent=variant===primary）、loading/SaveIndicator.tsx:15（size=sm,label=Saving）の2か所。外部color/className/style/ref/spread/tone指定はいずれも0 |

調査方法: 全TSXをTypeScript構文解析。Icon/ICON/Spinner等のタグ候補163（実運用候補129、見本/テストを含む総数）を抽出し、さらに constants/icons から直接importする全識別子のJSXを別途照合。ローカルcfg.Iconは原宣言へ追跡。候補数を通常Iconの正式採用数とは呼ばない。原抽出は `/tmp/icon-props-final-audit.json`。

追加の実物制約:

- 通常Iconのhi()はsize/color/className/styleしか取り出さないため、呼出側aria-hidden等をSVGへ汎用転送していない。`{...rest}`もない。呼出側に属性があることと出力にあることを混同しない。
- 通常Iconのrefは外部利用0でもforwardRefの公開契約がある。削除しない。
- `loading/icons.tsx`のCheckIcon/CloseIconは別実装。classNameのみを受け取り1em SVGとcurrentColorを使う。通常Iconへのstyle/color全許可の根拠にはならない。
- `loading-animations.css:66`は通常Spinnerのhead=var(--accent)、track=var(--border)。:79/:85/:91でsm/md/lg寸法を定義。:95のon-accentは--spinner-on-accent-track/head。これらの色APIを移す際、trackとheadを取り違えない。

## 移管契約案（任意style/colorの無条件許可はしない）

1. 通常Icon: 数値sizeと既存既定24を維持。ICONの5段階値はCSS正本から生成する数値派生物を参照。現在number|stringを受け取るAPIを移行途中でCSS文字列へ一括置換しない。既存svg classNameによる用途色は登録した所有元のCSSトークンから継承する。
2. 通常Iconの唯一のstyle使用: GoogleCalendarStatusBarの margin-right=var(--space-2)、flex-shrink=0を、同じSVGに付与する名前付き配置classへ移す。wrapperを加えず、現在のバーのcfg.colorからの継承を維持。呼出側styleが0になった後に一般CSSProperties入口を廃止/禁止する。新たな任意styleの例外口を作らない。
3. 通常Icon color: 外部指定0。固定colorを一般公開する必要の証拠はない。共通アダプター内のcolor転送は削除可能な設計候補だが、署名変更と利用0を同一PRで再確認する。通常の色は用途CSSのcurrentColorへ。refは同じSVGへのforwardRefを維持。
4. PlatformIcon: sizeは数値のまま維持し、内側画像の丸め比率を変更しない。内部width/heightは計算済み寸法だけの限定styleとしてowner登録する（一般style転送ではない）。mailのwhiteは--icon-platform-mail→--on-solidによる同値用途色へ移管し、内部SVGはcurrentColorを継承。wrapper形状/画像URL/alt/aria-hiddenは保持する。
5. LeadChatIcon: size数値/既定20/同SVG/className/aria-hiddenを維持。外部color/style/refの新設は不要。用途色はナビCSSから継承。
6. Spinner: 実在color指定0なので、固定文字列color→内部borderTopColorの自由指定口は撤去候補。新しいAPIは既存設計のtone=inherit（Button内部のみ）を追加し、CSSでborder-top-color:currentColor。既存onAccentは後方互換の状態名として残せるが、Buttonの呼出しはtone=inheritに移す。tone=inherit時はonAccentより優先し、headは文字色へ追従。trackは通常/既存onAccentの各tokenを保持する。これは新規API案であり、現在toneが動くという事実ではない。
7. SpinnerのSaveIndicator側は現在の通常tone・sm・labelを維持。Button側は既存設計のdecorative扱いを適用し、Button自身のbusy/nameと二重に読まない。Spinnerに任意style/ref/spreadを追加しない。
8. 通常Iconのaria属性は現状欠落を放置せず、必要なaria-hidden/label等だけを型と出力へ明示的に通す設計が必要。任意rest全転送によってstyle/color制約を復活させない。これは既存の属性転送不足の修正であり、現状維持とは説明しない。

## 検証条件と限界

- 移行後に外部Icon.style=0、Icon.color=0、Spinner.color=0を再走査。内部Platform寸法styleだけが限定ownerに残ることを確認。
- TS型検査で既存size/forwardRef契約を確認。Platformの20px入力時の内側寸法はmail14、Instagram14、真円16、その他14（Math.round(14.4)）を維持する。
- Spinner通常/onAccent/継承のhead/track、Buttonのdisabled/loading時、light/darkを検証。onAccentとtoneの優先順位はテスト対象。
- この照合は既存使用の読み取りであり、ブラウザー実表示・ref動作・CSS適用テストは未実行。
