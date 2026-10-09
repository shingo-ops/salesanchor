# AX-2b inline style の事実表（分類の判断はしない。測定値のみ）

分類欄は design.md §Z の layoutClassName 許可リスト（width/height/min-height 等のレイアウト系プロパティ）に宣言のプロパティが含まれるか否かの機械判定。「標準への効果」は、標準 TextareaControl（after 状態）に宣言を1つだけ足したときの computed の変化（normal、代表シグネチャ）。

## pages/conditions/ConditionsPage.tsx:340（現行 class: field field-h-md / rows=未指定）

- inline 原文: `height:80px;resize:vertical;width:100%`
- 標準（after・inline なし）の値: height 80px / min-height 80px / width 1200px / resize vertical / font-family -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Fira / font-size 14.4px / box-sizing border-box
- 現行（before）の値: height 80px / min-height 80px / width 1200px

| 宣言 | 分類(機械判定) | 標準に足したときの変化（normal） |
|---|---|---|
| `height: 80px` | レイアウト系 | 変化なし（標準と同じ値） |
| `resize: vertical` | 外観系 | 変化なし（標準と同じ値） |
| `width: 100%` | レイアウト系 | 変化なし（標準と同じ値） |

- 全宣言を足したとき標準との差: なし
- 現行（before）と「標準＋全宣言」の差: border-radius: 4px → 6px; font-family: monospace → -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Fira; line-height: normal → 21.6px; transition-property: all → border-color, box-shadow; transition-duration: 0s → 0.1s, 0.1s

## pages/conditions/ConditionsPage.tsx:350（現行 class: field field-h-md / rows=未指定）

- inline 原文: `height:80px;resize:vertical;width:100%`
- 標準（after・inline なし）の値: height 80px / min-height 80px / width 1200px / resize vertical / font-family -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Fira / font-size 14.4px / box-sizing border-box
- 現行（before）の値: height 80px / min-height 80px / width 1200px

| 宣言 | 分類(機械判定) | 標準に足したときの変化（normal） |
|---|---|---|
| `height: 80px` | レイアウト系 | 変化なし（標準と同じ値） |
| `resize: vertical` | 外観系 | 変化なし（標準と同じ値） |
| `width: 100%` | レイアウト系 | 変化なし（標準と同じ値） |

- 全宣言を足したとき標準との差: なし
- 現行（before）と「標準＋全宣言」の差: border-radius: 4px → 6px; font-family: monospace → -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Fira; line-height: normal → 21.6px; transition-property: all → border-color, box-shadow; transition-duration: 0s → 0.1s, 0.1s

## pages/staff-reports/StaffReportsPage.tsx:90（現行 class: なし / rows=未指定）

- inline 原文: `min-height:var(--textarea-min-h-lg)`
- 標準（after・inline なし）の値: height 80px / min-height 80px / width 1200px / resize vertical / font-family -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Fira / font-size 14.4px / box-sizing border-box
- 現行（before）の値: height 120px / min-height 120px / width 1200px

| 宣言 | 分類(機械判定) | 標準に足したときの変化（normal） |
|---|---|---|
| `min-height: var(--textarea-min-h-lg)` | レイアウト系 | height: 80px → 120px; min-height: 80px → 120px; offsetHeight: 80 → 120 |

- 全宣言を足したとき標準との差: height: 80px → 120px; min-height: 80px → 120px; offsetHeight: 80 → 120
- 現行（before）と「標準＋全宣言」の差: border-radius: 4px → 6px; font-family: monospace → -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Fira; line-height: normal → 21.6px; transition-property: all → border-color, box-shadow; transition-duration: 0s → 0.1s, 0.1s

## pages/super-admin/ExtractionPromptConfigTab.tsx:222（現行 class: なし / rows=16）

- inline 原文: `width:100%;font-family:var(--font-mono, monospace);font-size:var(--font-sm);box-sizing:border-box`
- 標準（after・inline なし）の値: height 363.75px / min-height 80px / width 1232px / resize vertical / font-family -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Fira / font-size 14.4px / box-sizing border-box
- 現行（before）の値: height 242px / min-height 0px / width 1232px

| 宣言 | 分類(機械判定) | 標準に足したときの変化（normal） |
|---|---|---|
| `width: 100%` | レイアウト系 | 変化なし（標準と同じ値） |
| `font-family: var(--font-mono, monospace)` | 外観系 | font-family: -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Fira → monospace |
| `font-size: var(--font-sm)` | 外観系 | font-size: 14.4px → 13.6px; line-height: 21.6px → 20.4px; height: 363.75px → 344.25px; offsetHeight: 364 → 344 |
| `box-sizing: border-box` | 外観系 | 変化なし（標準と同じ値） |

- 全宣言を足したとき標準との差: font-size: 14.4px → 13.6px; font-family: -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Fira → monospace; line-height: 21.6px → 20.4px; height: 363.75px → 344.25px; offsetHeight: 364 → 344
- 現行（before）と「標準＋全宣言」の差: padding: 0px → 8px / 12px / 8px / 12px; border-color: rgb(118, 118, 118) → rgb(226, 232, 240); border-radius: 0px → 6px; line-height: normal → 20.4px; color: rgb(0, 0, 0) → rgb(26, 32, 44); height: 242px → 344.25px; min-height: 0px → 80px; resize: both → vertical; outline-color: rgb(0, 0, 0) → rgb(26, 32, 44); transition-property: all → border-color, box-shadow; transition-duration: 0s → 0.1s, 0.1s; offsetHeight: 242 → 344

## pages/super-admin/components/ConditionsMasterPanel.tsx:367（現行 class: なし / rows=3）

- inline 原文: `width:100%;resize:vertical`
- 標準（after・inline なし）の値: height 82.8281px / min-height 80px / width 432px / resize vertical / font-family -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Fira / font-size 14.4px / box-sizing border-box
- 現行（before）の値: height 80px / min-height 80px / width 432px

| 宣言 | 分類(機械判定) | 標準に足したときの変化（normal） |
|---|---|---|
| `width: 100%` | レイアウト系 | 変化なし（標準と同じ値） |
| `resize: vertical` | 外観系 | 変化なし（標準と同じ値） |

- 全宣言を足したとき標準との差: なし
- 現行（before）と「標準＋全宣言」の差: border-radius: 4px → 6px; font-family: monospace → -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Fira; line-height: normal → 21.6px; height: 80px → 82.8281px; transition-property: all → border-color, box-shadow; transition-duration: 0s → 0.1s, 0.1s; offsetHeight: 80 → 83

## pages/super-admin/components/ConditionsMasterPanel.tsx:380（現行 class: なし / rows=3）

- inline 原文: `width:100%;resize:vertical`
- 標準（after・inline なし）の値: height 82.8281px / min-height 80px / width 432px / resize vertical / font-family -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Fira / font-size 14.4px / box-sizing border-box
- 現行（before）の値: height 80px / min-height 80px / width 432px

| 宣言 | 分類(機械判定) | 標準に足したときの変化（normal） |
|---|---|---|
| `width: 100%` | レイアウト系 | 変化なし（標準と同じ値） |
| `resize: vertical` | 外観系 | 変化なし（標準と同じ値） |

- 全宣言を足したとき標準との差: なし
- 現行（before）と「標準＋全宣言」の差: border-radius: 4px → 6px; font-family: monospace → -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Fira; line-height: normal → 21.6px; height: 80px → 82.8281px; transition-property: all → border-color, box-shadow; transition-duration: 0s → 0.1s, 0.1s; offsetHeight: 80 → 83

## 既存の寸法クラス（frontend/src/components/field-size.css:7-9,13-18）と同値の有無

| クラス | 宣言 | トークン定義 | 上の inline の値との一致 |
|---|---|---|---|
| .field-h-sm | min-height: var(--field-h-sm, 28px) | tokens.css:162 = 28px | height:80px・min-height:120px(--textarea-min-h-lg) のどちらとも不一致 |
| .field-h-md | min-height: var(--field-h-md, 36px) | tokens.css:163 = 36px | 同上（不一致）。ConditionsPage の textarea 2件は現在この class を付けているが、`.form-group textarea` の min-height(80px, 詳細度(0,1,1)) が勝つため実効は 80px |
| .field-h-lg | min-height: var(--field-h-lg, 44px) | tokens.css:164 = 44px | 不一致 |
| .field-w-sm/md/lg | width 160px / 280px / 100% + max-width 480px | tokens.css:165-167 | width:100% は標準が既に 100% |
| （参考）トークン | --textarea-min-h = 80px（tokens.css:170）、--textarea-min-h-lg = 120px（:444） | | 標準の min-height は --textarea-min-h(80px)。StaffReports:90 の inline は --textarea-min-h-lg(120px) |

## textStyle="code" 用のトークン確認

- frontend/src/tokens.css と index.css に `--font-mono` の定義は 0 件、monospace を値に持つトークンも 0 件（`grep -n "mono\|font-family" tokens.css` は空。フォント系トークンは --font-2xs…--font-3xl、--font-weight-* のみ。index.css の font-family は body 用の 1 件 :426）。
- ExtractionPromptConfigTab.tsx:235 は `fontFamily: "var(--font-mono, monospace)"`（未定義変数のフォールバックで実効は `monospace`）。同じ書き方が features/tcg-distribution/distribution.css:106,289 と pages/design-preview/DesignPreviewPage.css:83,126,196,212 にもある。
- 他の monospace の直書き: pages-layout.css:442 `ui-monospace, SFMono-Regular, Menlo, monospace`、pages-layout.css:760 `monospace`、pages/admin/discord-config.css:51、pages/integrations/FedexLabelValidationTab.css:477,574、pages/integrations/CarrierIntegrationPage.css:79、pages/design-system/DesignSystemPage.css:87,119（`ui-monospace, "SF Mono", Menlo, monospace`）、pages/super-admin/TcgParallelReportPage.tsx:127（inline `fontFamily: "monospace"`）。
- design.md:817 に `textStyle?: normal/secondary/code` の契約はあるが、frontend/src の .ts/.tsx に `textStyle` の実装は 0 件（grep）。
- 現行 ExtractionPromptConfigTab の実測 font-family: monospace。標準は -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Fira。

## 追加測定（ax2b-extra.cjs。Chromium 147.0.7727.15、幅1280・light、normal、旧規則を取り除いた CSS）

### pages/super-admin/components/ConditionsMasterPanel.tsx:367（rows=3、祖先シグネチャ0: div.form-group < div < form < div.comp-drawer-body < div.comp-drawer-panel < div.analysis-panel-content < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell）

現行（before）: height 80px / min-height 80px / width 432px / resize vertical / font-family monospace / font-size 14.4px / line-height normal

| 条件 | 標準との差 | 現行(before)との差 |
|---|---|---|
| 標準（inline なし） | 差なし | border-top-left-radius: 4px → 6px; font-family: monospace → -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar; line-height: normal → 21.6px; height: 80px → 82.8281px; offsetHeight: 80 → 83 |
| 標準＋width:100% | 差なし | border-top-left-radius: 4px → 6px; font-family: monospace → -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar; line-height: normal → 21.6px; height: 80px → 82.8281px; offsetHeight: 80 → 83 |
| 標準＋resize:vertical | 差なし | border-top-left-radius: 4px → 6px; font-family: monospace → -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar; line-height: normal → 21.6px; height: 80px → 82.8281px; offsetHeight: 80 → 83 |
| 標準＋両方（現行の inline 全部） | 差なし | border-top-left-radius: 4px → 6px; font-family: monospace → -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar; line-height: normal → 21.6px; height: 80px → 82.8281px; offsetHeight: 80 → 83 |

### pages/super-admin/components/ConditionsMasterPanel.tsx:380（rows=3、祖先シグネチャ0: div.form-group < div < form < div.comp-drawer-body < div.comp-drawer-panel < div.analysis-panel-content < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell）

現行（before）: height 80px / min-height 80px / width 432px / resize vertical / font-family monospace / font-size 14.4px / line-height normal

| 条件 | 標準との差 | 現行(before)との差 |
|---|---|---|
| 標準（inline なし） | 差なし | border-top-left-radius: 4px → 6px; font-family: monospace → -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar; line-height: normal → 21.6px; height: 80px → 82.8281px; offsetHeight: 80 → 83 |
| 標準＋width:100% | 差なし | border-top-left-radius: 4px → 6px; font-family: monospace → -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar; line-height: normal → 21.6px; height: 80px → 82.8281px; offsetHeight: 80 → 83 |
| 標準＋resize:vertical | 差なし | border-top-left-radius: 4px → 6px; font-family: monospace → -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar; line-height: normal → 21.6px; height: 80px → 82.8281px; offsetHeight: 80 → 83 |
| 標準＋両方（現行の inline 全部） | 差なし | border-top-left-radius: 4px → 6px; font-family: monospace → -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar; line-height: normal → 21.6px; height: 80px → 82.8281px; offsetHeight: 80 → 83 |

### pages/super-admin/ExtractionPromptConfigTab.tsx:222（rows=16、祖先シグネチャ0: section < div < div.analysis-panel-content < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell）

現行（before）: height 242px / min-height 0px / width 1232px / resize both / font-family monospace / font-size 13.6px / line-height normal

| 条件 | 標準との差 | 現行(before)との差 |
|---|---|---|
| 標準（inline なし） | 差なし | padding-top: 0px → 8px; padding-right: 0px → 12px; padding-bottom: 0px → 8px; padding-left: 0px → 12px; border-top-color: rgb(118, 118, 118) → rgb(226, 232, 240); border-top-left-radius: 0px → 6px; font-size: 13.6px → 14.4px; font-family: monospace → -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar; line-height: normal → 21.6px; color: rgb(0, 0, 0) → rgb(26, 32, 44); height: 242px → 363.75px; min-height: 0px → 80px; resize: both → vertical; outline-color: rgb(0, 0, 0) → rgb(26, 32, 44); offsetHeight: 242 → 364 |
| 標準＋font-family だけ monospace（font-size は標準のまま） | font-family: -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar → monospace | padding-top: 0px → 8px; padding-right: 0px → 12px; padding-bottom: 0px → 8px; padding-left: 0px → 12px; border-top-color: rgb(118, 118, 118) → rgb(226, 232, 240); border-top-left-radius: 0px → 6px; font-size: 13.6px → 14.4px; line-height: normal → 21.6px; color: rgb(0, 0, 0) → rgb(26, 32, 44); height: 242px → 363.75px; min-height: 0px → 80px; resize: both → vertical; outline-color: rgb(0, 0, 0) → rgb(26, 32, 44); offsetHeight: 242 → 364 |
| 標準＋font-family と font-size(--font-sm) の両方 | font-size: 14.4px → 13.6px; font-family: -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar → monospace; line-height: 21.6px → 20.4px; height: 363.75px → 344.25px; offsetHeight: 364 → 344 | padding-top: 0px → 8px; padding-right: 0px → 12px; padding-bottom: 0px → 8px; padding-left: 0px → 12px; border-top-color: rgb(118, 118, 118) → rgb(226, 232, 240); border-top-left-radius: 0px → 6px; line-height: normal → 20.4px; color: rgb(0, 0, 0) → rgb(26, 32, 44); height: 242px → 344.25px; min-height: 0px → 80px; resize: both → vertical; outline-color: rgb(0, 0, 0) → rgb(26, 32, 44); offsetHeight: 242 → 344 |
| 標準＋現行の inline 全部（width/font-family/font-size/box-sizing） | font-size: 14.4px → 13.6px; font-family: -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar → monospace; line-height: 21.6px → 20.4px; height: 363.75px → 344.25px; offsetHeight: 364 → 344 | padding-top: 0px → 8px; padding-right: 0px → 12px; padding-bottom: 0px → 8px; padding-left: 0px → 12px; border-top-color: rgb(118, 118, 118) → rgb(226, 232, 240); border-top-left-radius: 0px → 6px; line-height: normal → 20.4px; color: rgb(0, 0, 0) → rgb(26, 32, 44); height: 242px → 344.25px; min-height: 0px → 80px; resize: both → vertical; outline-color: rgb(0, 0, 0) → rgb(26, 32, 44); offsetHeight: 242 → 344 |

