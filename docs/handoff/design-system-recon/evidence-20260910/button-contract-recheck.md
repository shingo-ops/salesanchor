# Button機能先行便の再監査（2026-09-11）

何の文書か: 処理中表示と操作を揃える前に、今の画面が依存する条件を確認した記録。
親: [recon](../recon.md)。基準main57eb951e。読み取り担当の報告を設計担当が確認しADへ反映。試験実施結果ではない。

Button67箇所/18ファイル、className18、style/ref/spread0、type明示26（button21/submit5）省略41。src TSXからstories/test/spec/design-preview除外、design-systemを含む。Spinner呼出2（Button/SaveIndicator）。

追加class18はCompanyDetailタブ6（company-forms.css:48–74）、dashboard5（nowrap3/margin-left:auto2）、schedule7（作成1/mini-nav2/nav2/shell2）。Button.css:59–66の旧btn全体モバイル44px指定、components.css:697–705のヘッダー上書きも存在する。このため本便は外観CSSを変更せず、利用先/寸法の移行は後続へ分離。

Button.tsx:76–79のrestによるaria上書き順、type省略、native form/name/value、イベントを保持する。Spinnerは現在role=status/label=Loadingで、Button側だけdecorative/inheritを指定。main.tsxがloading-animations.cssを読むがStorybookはindex.cssだけのため、Spinner自身も同じ既存CSSをimportする。

既存CIはpackage.json:44、Vitestはvitest.unit.config.ts:33–36のsrc/**/*.test.tsxを読み込む。専用Button/Spinner試験は現状0であり本便で追加。design.md§ADの5ファイル実装と検証カードを正式card-lint exit0で検査後Generatorへ渡した。L24長文警告は非停止の既存仕様。新CIなし。

新PO要望の読み取りやすさはdesign.md§ACへ保存。W3C認知アクセシビリティ指針とコントラストの規格を根拠にし、脳活動や理解速度の改善を実証済みとしない。最終PO目視・全画面移行・最終CIは未完了。
