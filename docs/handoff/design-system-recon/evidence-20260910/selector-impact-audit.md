# 今回のnative/class置換に限定したCSS影響照合

全314候補をselector parserの構造で再確認。4つの:not内checkbox/radio属性を通常入力の除外条件として訂正した。以下はroot設計担当案であり、PO自筆決定・実装済み・実表示済みの意味ではない。

Button/裸Controlは同native1要素。新wrapperなし。selector保持・owner保持と宣言値の維持は別。

| 判定 | selector数 |
|---|---|
| 外配置へ移管＋部品CSSへ削除移管 | 24 |
| 部品CSSへ削除移管 | 219 |
| 維持 | 54 |
| 外配置へ移管 | 3 |
| 対象外 | 14 |

## 訂正・整合

- CSSI-0005/0012/0015/0026: checkbox/radioを除く通常入力。外観は裸TextControlへ移管。
- CSSI-0038: DataTable checkboxの寸法/accent-color/cursorは共通Checkbox owner。
- Button.css ownerは維持するが、md36px・iconOnly6px角丸/28,36,44px・mobile全辺44pxの契約へ値を更新。
- CSSI-0209: embedded/resize noneと共通入力token、flex/minwidthは同native配置。
- CSSI-0231: indicator none、native select1個、追加矢印DOMなし。
- CSSI-0233: resize none、min-height用途tokenは同native配置。

## 個別表

| ID | 根拠 | selector / media | 判定 | 理由/値の更新 |
|---|---|---|---|---|
| CSSI-0001 | src/company-forms.css:48 | .tabs .tab [] | 外配置へ移管＋部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0002 | src/company-forms.css:62 | .tabs .tab:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0003 | src/company-forms.css:67 | .tabs .tab.active [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0004 | src/company-forms.css:73 | .tabs .tab.active:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0005 | src/company-forms.css:100 | .form-grid > .form-row input:not([type="checkbox"]):not([type="radio"]) [] | 部品CSSへ削除移管 | selector AST上の:not([type=checkbox]):not([type=radio])はcheckbox/radioを除く通常入力。元の特殊入力維持判定を訂正。外観は共通裸TextControlへ移しnative要素とtypeを維持  |
| CSSI-0006 | src/company-forms.css:100 | .form-grid > .form-row select [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0007 | src/company-forms.css:100 | .form-grid > .form-row textarea [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0008 | src/company-forms.css:114 | .form-grid > .form-row textarea [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0009 | src/company-forms.css:120 | .form-grid > .form-row input:focus [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0010 | src/company-forms.css:120 | .form-grid > .form-row select:focus [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0011 | src/company-forms.css:120 | .form-grid > .form-row textarea:focus [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0012 | src/company-forms.css:156 | .modal-content .form-row input:not([type="checkbox"]):not([type="radio"]) [] | 部品CSSへ削除移管 | selector AST上の:not([type=checkbox]):not([type=radio])はcheckbox/radioを除く通常入力。元の特殊入力維持判定を訂正。外観は共通裸TextControlへ移しnative要素とtypeを維持  |
| CSSI-0013 | src/company-forms.css:156 | .modal-content .form-row select [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0014 | src/company-forms.css:156 | .modal-content .form-row textarea [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0015 | src/company-forms.css:156 | .modal-content-wide .form-row input:not([type="checkbox"]):not([type="radio"]) [] | 部品CSSへ削除移管 | selector AST上の:not([type=checkbox]):not([type=radio])はcheckbox/radioを除く通常入力。元の特殊入力維持判定を訂正。外観は共通裸TextControlへ移しnative要素とtypeを維持  |
| CSSI-0016 | src/company-forms.css:156 | .modal-content-wide .form-row select [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0017 | src/company-forms.css:156 | .modal-content-wide .form-row textarea [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0018 | src/company-forms.css:173 | .modal-content .form-row textarea [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0019 | src/company-forms.css:173 | .modal-content-wide .form-row textarea [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0020 | src/company-forms.css:181 | .modal-content .form-row input:focus [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0021 | src/company-forms.css:181 | .modal-content .form-row select:focus [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0022 | src/company-forms.css:181 | .modal-content .form-row textarea:focus [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0023 | src/company-forms.css:181 | .modal-content-wide .form-row input:focus [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0024 | src/company-forms.css:181 | .modal-content-wide .form-row select:focus [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0025 | src/company-forms.css:181 | .modal-content-wide .form-row textarea:focus [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0026 | src/company-forms.css:260 | .product-edit-form .form-group input:not([type="checkbox"]):not([type="radio"]) [] | 部品CSSへ削除移管 | selector AST上の:not([type=checkbox]):not([type=radio])はcheckbox/radioを除く通常入力。元の特殊入力維持判定を訂正。外観は共通裸TextControlへ移しnative要素とtypeを維持  |
| CSSI-0027 | src/company-forms.css:260 | .product-edit-form .form-group select [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0028 | src/company-forms.css:260 | .product-edit-form .form-group textarea [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0029 | src/components/Button.css:60 | .btn-primary ['@media (max-width: 767px)'] | 維持 | 既存共通部品CSSの所有を維持。裸Control追加は既存wrapperを新設しない。既存Field wrapperで使うerror/size selectorは残す Button CSS owner維持。宣言全維持ではない。md min-heightは--field-h-md=36pxへ明示変更（旧--btn-min-height-md40pxと異なる）。iconOnlyはradius6px,width/height/min-height=sm28/md36/lg44、mobileは全辺44。通常lg min-height48の競合を除く |
| CSSI-0030 | src/components/Button.css:60 | .btn-secondary ['@media (max-width: 767px)'] | 維持 | 既存共通部品CSSの所有を維持。裸Control追加は既存wrapperを新設しない。既存Field wrapperで使うerror/size selectorは残す Button CSS owner維持。宣言全維持ではない。md min-heightは--field-h-md=36pxへ明示変更（旧--btn-min-height-md40pxと異なる）。iconOnlyはradius6px,width/height/min-height=sm28/md36/lg44、mobileは全辺44。通常lg min-height48の競合を除く |
| CSSI-0031 | src/components/Button.css:60 | .btn-ghost ['@media (max-width: 767px)'] | 維持 | 既存共通部品CSSの所有を維持。裸Control追加は既存wrapperを新設しない。既存Field wrapperで使うerror/size selectorは残す Button CSS owner維持。宣言全維持ではない。md min-heightは--field-h-md=36pxへ明示変更（旧--btn-min-height-md40pxと異なる）。iconOnlyはradius6px,width/height/min-height=sm28/md36/lg44、mobileは全辺44。通常lg min-height48の競合を除く |
| CSSI-0032 | src/components/Button.css:60 | .btn-danger ['@media (max-width: 767px)'] | 維持 | 既存共通部品CSSの所有を維持。裸Control追加は既存wrapperを新設しない。既存Field wrapperで使うerror/size selectorは残す Button CSS owner維持。宣言全維持ではない。md min-heightは--field-h-md=36pxへ明示変更（旧--btn-min-height-md40pxと異なる）。iconOnlyはradius6px,width/height/min-height=sm28/md36/lg44、mobileは全辺44。通常lg min-height48の競合を除く |
| CSSI-0033 | src/components/Button.css:83 | button.comp-btn--icon-only [] | 維持 | 既存共通部品CSSの所有を維持。裸Control追加は既存wrapperを新設しない。既存Field wrapperで使うerror/size selectorは残す Button CSS owner維持。宣言全維持ではない。md min-heightは--field-h-md=36pxへ明示変更（旧--btn-min-height-md40pxと異なる）。iconOnlyはradius6px,width/height/min-height=sm28/md36/lg44、mobileは全辺44。通常lg min-height48の競合を除く |
| CSSI-0034 | src/components/DataTable.css:76 | .comp-table__sort-btn [] | 維持 | 既存共通部品CSSの所有を維持。裸Control追加は既存wrapperを新設しない。既存Field wrapperで使うerror/size selectorは残す  |
| CSSI-0035 | src/components/DataTable.css:92 | .comp-table__sort-btn:hover [] | 維持 | 既存共通部品CSSの所有を維持。裸Control追加は既存wrapperを新設しない。既存Field wrapperで使うerror/size selectorは残す  |
| CSSI-0036 | src/components/DataTable.css:96 | .comp-table__sort-btn--active [] | 維持 | 既存共通部品CSSの所有を維持。裸Control追加は既存wrapperを新設しない。既存Field wrapperで使うerror/size selectorは残す  |
| CSSI-0037 | src/components/DataTable.css:106 | .comp-table__sort-btn--active .comp-table__sort-icon [] | 維持 | 既存共通部品CSSの所有を維持。裸Control追加は既存wrapperを新設しない。既存Field wrapperで使うerror/size selectorは残す  |
| CSSI-0038 | src/components/DataTable.css:136 | .comp-table__check [] | 外配置へ移管＋部品CSSへ削除移管 | Checkboxの外観/寸法/accent-colorは共通Checkbox ownerへ。既存行/セル配置用margin/flexは同じnative要素の配置専用classへ。DataTable所有のcheckbox外観を残さない  |
| CSSI-0039 | src/components/FormField.css:47 | .comp-field__input [] | 維持 | 既存共通部品CSSの所有を維持。裸Control追加は既存wrapperを新設しない。既存Field wrapperで使うerror/size selectorは残す  |
| CSSI-0040 | src/components/FormField.css:47 | .comp-field__textarea [] | 維持 | 既存共通部品CSSの所有を維持。裸Control追加は既存wrapperを新設しない。既存Field wrapperで使うerror/size selectorは残す  |
| CSSI-0041 | src/components/FormField.css:65 | .comp-field__textarea [] | 維持 | 既存共通部品CSSの所有を維持。裸Control追加は既存wrapperを新設しない。既存Field wrapperで使うerror/size selectorは残す  |
| CSSI-0042 | src/components/FormField.css:95 | .comp-field__input:focus [] | 維持 | 既存共通部品CSSの所有を維持。裸Control追加は既存wrapperを新設しない。既存Field wrapperで使うerror/size selectorは残す  |
| CSSI-0043 | src/components/FormField.css:95 | .comp-field__textarea:focus [] | 維持 | 既存共通部品CSSの所有を維持。裸Control追加は既存wrapperを新設しない。既存Field wrapperで使うerror/size selectorは残す  |
| CSSI-0044 | src/components/FormField.css:105 | .comp-field__input:disabled [] | 維持 | 既存共通部品CSSの所有を維持。裸Control追加は既存wrapperを新設しない。既存Field wrapperで使うerror/size selectorは残す  |
| CSSI-0045 | src/components/FormField.css:105 | .comp-field__textarea:disabled [] | 維持 | 既存共通部品CSSの所有を維持。裸Control追加は既存wrapperを新設しない。既存Field wrapperで使うerror/size selectorは残す  |
| CSSI-0046 | src/components/FormField.css:115 | .comp-field--error .comp-field__input [] | 維持 | 既存共通部品CSSの所有を維持。裸Control追加は既存wrapperを新設しない。既存Field wrapperで使うerror/size selectorは残す  |
| CSSI-0047 | src/components/FormField.css:115 | .comp-field--error .comp-field__textarea [] | 維持 | 既存共通部品CSSの所有を維持。裸Control追加は既存wrapperを新設しない。既存Field wrapperで使うerror/size selectorは残す  |
| CSSI-0048 | src/components/FormField.css:134 | .comp-field--sm .comp-field__input [] | 維持 | 既存共通部品CSSの所有を維持。裸Control追加は既存wrapperを新設しない。既存Field wrapperで使うerror/size selectorは残す  |
| CSSI-0049 | src/components/FormField.css:148 | .comp-field--sm .comp-field__textarea [] | 維持 | 既存共通部品CSSの所有を維持。裸Control追加は既存wrapperを新設しない。既存Field wrapperで使うerror/size selectorは残す  |
| CSSI-0050 | src/components/FormField.css:158 | .comp-field--lg .comp-field__input [] | 維持 | 既存共通部品CSSの所有を維持。裸Control追加は既存wrapperを新設しない。既存Field wrapperで使うerror/size selectorは残す  |
| CSSI-0051 | src/components/FormField.css:158 | .comp-field--lg .comp-field__textarea [] | 維持 | 既存共通部品CSSの所有を維持。裸Control追加は既存wrapperを新設しない。既存Field wrapperで使うerror/size selectorは残す  |
| CSSI-0052 | src/components/FormField.css:183 | .comp-field--error .comp-field__input:focus [] | 維持 | 既存共通部品CSSの所有を維持。裸Control追加は既存wrapperを新設しない。既存Field wrapperで使うerror/size selectorは残す  |
| CSSI-0053 | src/components/FormField.css:183 | .comp-field--error .comp-field__textarea:focus [] | 維持 | 既存共通部品CSSの所有を維持。裸Control追加は既存wrapperを新設しない。既存Field wrapperで使うerror/size selectorは残す  |
| CSSI-0054 | src/components/FormField.css:192 | .comp-field__input ['@media (max-width: 767px)'] | 維持 | 既存共通部品CSSの所有を維持。裸Control追加は既存wrapperを新設しない。既存Field wrapperで使うerror/size selectorは残す  |
| CSSI-0055 | src/components/SubMenu.css:75 | .comp-subnav__item [] | 維持 | 既存共通部品CSSの所有を維持。裸Control追加は既存wrapperを新設しない。既存Field wrapperで使うerror/size selectorは残す  |
| CSSI-0056 | src/components/SubMenu.css:94 | .comp-subnav__item--active [] | 維持 | 既存共通部品CSSの所有を維持。裸Control追加は既存wrapperを新設しない。既存Field wrapperで使うerror/size selectorは残す  |
| CSSI-0057 | src/components/SubMenu.css:101 | .comp-subnav__item--disabled [] | 維持 | 既存共通部品CSSの所有を維持。裸Control追加は既存wrapperを新設しない。既存Field wrapperで使うerror/size selectorは残す  |
| CSSI-0058 | src/components/SubMenu.css:114 | .comp-subnav__item:hover:not(:disabled) [] | 維持 | 既存共通部品CSSの所有を維持。裸Control追加は既存wrapperを新設しない。既存Field wrapperで使うerror/size selectorは残す  |
| CSSI-0059 | src/components/SubMenu.css:120 | .comp-subnav__item--active:hover:not(:disabled) [] | 維持 | 既存共通部品CSSの所有を維持。裸Control追加は既存wrapperを新設しない。既存Field wrapperで使うerror/size selectorは残す  |
| CSSI-0060 | src/components/field-size.css:8 | .field-h-md [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0061 | src/components/field-size.css:12 | .field-w-sm [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0062 | src/components/field-size.css:13 | .field-w-md [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0063 | src/components/field-size.css:18 | .content-toolbar .field-w-sm [] | 外配置へ移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0064 | src/components/field-size.css:18 | .content-toolbar .field-w-md [] | 外配置へ移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0065 | src/components.css:19 | .form-group input [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0066 | src/components.css:19 | .form-group select [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0067 | src/components.css:19 | .form-group textarea [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0068 | src/components.css:32 | .form-group input:focus [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0069 | src/components.css:32 | .form-group select:focus [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0070 | src/components.css:32 | .form-group textarea:focus [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0071 | src/components.css:41 | .form-group textarea [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0072 | src/components.css:54 | .btn-primary [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0073 | src/components.css:65 | .btn-primary:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0074 | src/components.css:66 | .btn-primary:disabled [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0075 | src/components.css:68 | .btn-secondary [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0076 | src/components.css:78 | .btn-secondary:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0077 | src/components.css:81 | .btn-ghost [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0078 | src/components.css:93 | .btn-ghost:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0079 | src/components.css:95 | .btn-sm [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0080 | src/components.css:105 | .btn-sm:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0081 | src/components.css:107 | .btn-danger [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0082 | src/components.css:122 | .btn-danger:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0083 | src/components.css:149 | .btn-sm.btn-secondary [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0084 | src/components.css:149 | .btn-sm.btn-danger [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0085 | src/components.css:157 | .btn-sm.btn-primary [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0086 | src/components.css:163 | .btn-sm.btn-primary:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0087 | src/components.css:172 | .search-bar input [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0088 | src/components.css:172 | .filter-bar select [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0089 | src/components.css:189 | .search-input-field [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0090 | src/components.css:199 | .search-input-field::placeholder [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0091 | src/components.css:202 | .search-input-field:focus [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0092 | src/components.css:518 | .modal-icon-btn [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0093 | src/components.css:532 | .modal-icon-btn:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0094 | src/components.css:537 | .modal-icon-btn--danger:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0095 | src/components.css:688 | .page-header-actions .btn-ghost [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0096 | src/components.css:688 | .page-header-actions .icon-btn [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0097 | src/components.css:692 | .page-header-actions .btn-ghost:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0098 | src/components.css:692 | .page-header-actions .icon-btn:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0099 | src/components.css:697 | .page-header-actions .btn-ghost [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0100 | src/components.css:697 | .page-header-actions .btn-primary [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0101 | src/components.css:697 | .page-header-actions .btn-secondary [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0102 | src/components.css:711 | .page-header-select [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0103 | src/components.css:726 | .page-header-select:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0104 | src/components.css:730 | .page-header-select:focus [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0105 | src/components.css:738 | .icon-btn [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0106 | src/components.css:753 | .icon-btn:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0107 | src/components.css:754 | .icon-btn.danger:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0108 | src/components.css:785 | .tab-item.active [] | 対象外 | active/selected等の汎用状態名だけの一致。今回411個の置換対象classとして特定されない  |
| CSSI-0109 | src/components.css:808 | .filter-pill.active [] | 対象外 | active/selected等の汎用状態名だけの一致。今回411個の置換対象classとして特定されない  |
| CSSI-0110 | src/components.css:907 | .toggle-switch input [] | 部品CSSへ削除移管 | checked/focus-visibleと隣接sliderの結合をToggle専用ownerへ移す。裸TextControlの共通外観は適用しない  |
| CSSI-0111 | src/components.css:919 | .toggle-switch input:checked + .toggle-switch-slider [] | 部品CSSへ削除移管 | checked/focus-visibleと隣接sliderの結合をToggle専用ownerへ移す。裸TextControlの共通外観は適用しない  |
| CSSI-0112 | src/components.css:920 | .toggle-switch input:checked + .toggle-switch-slider::before [] | 部品CSSへ削除移管 | checked/focus-visibleと隣接sliderの結合をToggle専用ownerへ移す。裸TextControlの共通外観は適用しない  |
| CSSI-0113 | src/features/tcg-analysis-review/source-raw-pane.css:48 | .source-search input [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0114 | src/features/tcg-analysis-review/supplier-detail-view.css:14 | .supplier-detail-back [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0115 | src/features/tcg-analysis-review/supplier-detail-view.css:24 | .supplier-detail-back:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0116 | src/features/tcg-analysis-review/supplier-detail-view.css:90 | .supplier-detail-correct-btn [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0117 | src/features/tcg-analysis-review/supplier-detail-view.css:102 | .supplier-detail-correct-btn:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0118 | src/features/tcg-analysis-review/supplier-detail-view.css:227 | .pmd-head button [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0119 | src/features/tcg-analysis-review/supplier-detail-view.css:244 | .pmd-field input [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0120 | src/features/tcg-analysis-review/supplier-detail-view.css:244 | .pmd-field textarea [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0121 | src/features/tcg-analysis-review/supplier-detail-view.css:255 | .pmd-field textarea [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0122 | src/features/tcg-analysis-review/supplier-detail-view.css:260 | .pmd-actions button [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0123 | src/features/tcg-analysis-review/supplier-detail-view.css:293 | .pmd-search-candidate button [] | 維持 | 候補行/メニュー行/アバター等の既存専用ownerを維持。通常Buttonの箱へ置換しない。token参照への集約は当該ownerで行う  |
| CSSI-0124 | src/features/tcg-analysis-review/supplier-detail-view.css:309 | .pmd-actions button:disabled [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0125 | src/features/tcg-distribution/distribution.css:141 | .dist-btn [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0126 | src/features/tcg-distribution/distribution.css:155 | .dist-btn:disabled [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0127 | src/features/tcg-distribution/distribution.css:160 | .dist-btn--primary [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0128 | src/features/tcg-distribution/distribution.css:165 | .dist-btn--primary:hover:not(:disabled) [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0129 | src/features/tcg-distribution/distribution.css:169 | .dist-btn--ghost [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0130 | src/features/tcg-distribution/distribution.css:175 | .dist-btn--ghost:hover:not(:disabled) [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0131 | src/features/tcg-distribution/distribution.css:179 | .dist-btn--danger [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0132 | src/features/tcg-distribution/distribution.css:185 | .dist-btn--danger:hover:not(:disabled) [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0133 | src/features/tcg-distribution/distribution.css:227 | .dist-drawer-close [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0134 | src/features/tcg-distribution/distribution.css:239 | .dist-drawer-close:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0135 | src/features/tcg-distribution/distribution.css:322 | .dist-input [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0136 | src/features/tcg-distribution/distribution.css:334 | .dist-input:focus [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0137 | src/features/tcg-distribution/distribution.css:340 | .dist-input--error [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0138 | src/hub-shell.css:65 | .hub-subnav-item.active [] | 対象外 | active/selected等の汎用状態名だけの一致。今回411個の置換対象classとして特定されない  |
| CSSI-0139 | src/loading-animations.css:389 | .sa-drawer__close [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0140 | src/mobile-shell.css:88 | .mobile-menu-action [] | 維持 | 候補行/メニュー行/アバター等の既存専用ownerを維持。通常Buttonの箱へ置換しない。token参照への集約は当該ownerで行う  |
| CSSI-0141 | src/mobile-shell.css:103 | .mobile-menu-action:hover [] | 維持 | 候補行/メニュー行/アバター等の既存専用ownerを維持。通常Buttonの箱へ置換しない。token参照への集約は当該ownerで行う  |
| CSSI-0142 | src/mobile-shell.css:107 | .mobile-menu-action--danger [] | 維持 | 候補行/メニュー行/アバター等の既存専用ownerを維持。通常Buttonの箱へ置換しない。token参照への集約は当該ownerで行う  |
| CSSI-0143 | src/mobile-shell.css:111 | .mobile-menu-action--danger:hover [] | 維持 | 候補行/メニュー行/アバター等の既存専用ownerを維持。通常Buttonの箱へ置換しない。token参照への集約は当該ownerで行う  |
| CSSI-0144 | src/pages/account-settings/account-settings.css:106 | .toggle-switch input [] | 部品CSSへ削除移管 | checked/focus-visibleと隣接sliderの結合をToggle専用ownerへ移す。裸TextControlの共通外観は適用しない  |
| CSSI-0145 | src/pages/account-settings/account-settings.css:134 | .toggle-switch input:checked + .toggle-slider [] | 部品CSSへ削除移管 | checked/focus-visibleと隣接sliderの結合をToggle専用ownerへ移す。裸TextControlの共通外観は適用しない  |
| CSSI-0146 | src/pages/account-settings/account-settings.css:138 | .toggle-switch input:checked + .toggle-slider::before [] | 部品CSSへ削除移管 | checked/focus-visibleと隣接sliderの結合をToggle専用ownerへ移す。裸TextControlの共通外観は適用しない  |
| CSSI-0147 | src/pages/account-settings/account-settings.css:142 | .toggle-switch input:focus-visible + .toggle-slider [] | 部品CSSへ削除移管 | checked/focus-visibleと隣接sliderの結合をToggle専用ownerへ移す。裸TextControlの共通外観は適用しない  |
| CSSI-0148 | src/pages/account-settings/account-settings.css:147 | .account-settings-lang-select [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0149 | src/pages/account-settings/account-settings.css:158 | .account-settings-lang-select:focus [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0150 | src/pages/admin/admin-hub.css:55 | .admin-hub-tab.active [] | 対象外 | active/selected等の汎用状態名だけの一致。今回411個の置換対象classとして特定されない  |
| CSSI-0151 | src/pages/dashboard/DashboardPage.css:32 | .db-tab [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0152 | src/pages/dashboard/DashboardPage.css:45 | .db-tab.active [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0153 | src/pages/dashboard/DashboardPage.css:50 | .db-tab:hover:not(.active) [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0154 | src/pages/dashboard/FollowUpsPage.css:14 | .fu-filter-chip [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0155 | src/pages/dashboard/FollowUpsPage.css:28 | .fu-filter-chip:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0156 | src/pages/dashboard/FollowUpsPage.css:32 | .fu-filter-chip.active [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0157 | src/pages/dashboard/FollowUpsPage.css:48 | .fu-filter-chip:not(.active) .fu-chip-count [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0158 | src/pages/dashboard/FunnelReasonsPage.css:14 | .frr-tab [] | 外配置へ移管＋部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0159 | src/pages/dashboard/FunnelReasonsPage.css:27 | .frr-tab:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0160 | src/pages/dashboard/FunnelReasonsPage.css:29 | .frr-tab.active [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0161 | src/pages/dashboard/FunnelSection.css:440 | .fn-link-btn [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0162 | src/pages/dashboard/FunnelSection.css:453 | .fn-link-btn:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0163 | src/pages/dashboard/FunnelSection.css:457 | .fn-link-btn:focus-visible [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0164 | src/pages/dashboard/WeeklyAdvisorSection.css:209 | .db-weekly-composer-input [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0165 | src/pages/dashboard/WeeklyAdvisorSection.css:220 | .db-weekly-composer-input:focus [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0166 | src/pages/goal-setting/GoalSettingPage.css:119 | .gs-advisor__monthly-input [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0167 | src/pages/goal-setting/GoalSettingPage.css:133 | .gs-advisor__toggle-btn [] | 部品CSSへ削除移管 | checked/focus-visibleと隣接sliderの結合をToggle専用ownerへ移す。裸TextControlの共通外観は適用しない  |
| CSSI-0168 | src/pages/goal-setting/GoalSettingPage.css:145 | .gs-advisor__toggle-btn.is-active [] | 部品CSSへ削除移管 | checked/focus-visibleと隣接sliderの結合をToggle専用ownerへ移す。裸TextControlの共通外観は適用しない  |
| CSSI-0169 | src/pages/goal-setting/GoalSettingPage.css:151 | .gs-advisor__run-btn [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0170 | src/pages/goal-setting/GoalSettingPage.css:277 | .gs-advisor__metric-input [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0171 | src/pages/goal-setting/GoalSettingPage.css:281 | .gs-advisor__toggle-btn:focus-visible [] | 部品CSSへ削除移管 | checked/focus-visibleと隣接sliderの結合をToggle専用ownerへ移す。裸TextControlの共通外観は適用しない  |
| CSSI-0172 | src/pages/goal-setting/GoalSettingPage.css:281 | .gs-advisor__run-btn:focus-visible [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0173 | src/pages/goal-setting/GoalSettingPage.css:281 | .gs-advisor__metric-input:focus-visible [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0174 | src/pages/goal-setting/GoalSettingPage.css:510 | .gs-input [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0175 | src/pages/goal-setting/GoalSettingPage.css:522 | .gs-input:focus [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0176 | src/pages/goal-setting/GoalSettingPage.css:527 | .gs-input.gs-input-saved [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0177 | src/pages/goal-setting/GoalSettingPage.css:544 | .gs-save-btn [] | 外配置へ移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0178 | src/pages/goal-setting/GoalSettingPage.css:555 | .gs-select [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0179 | src/pages/inbox/InboxPage.css:38 | .inbox-full-tab [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0180 | src/pages/inbox/InboxPage.css:56 | .inbox-full-tab:hover:not(.active) [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0181 | src/pages/inbox/InboxPage.css:61 | .inbox-full-tab.active [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0182 | src/pages/inbox/InboxPage.css:69 | .inbox-platform-select [] | 外配置へ移管＋部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0183 | src/pages/inbox/InboxPage.css:82 | .inbox-platform-select:focus [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0184 | src/pages/inbox/InboxPage.css:130 | .inbox-search-input [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0185 | src/pages/inbox/InboxPage.css:157 | .inbox-manage-btn.active [] | 対象外 | active/selected等の汎用状態名だけの一致。今回411個の置換対象classとして特定されない  |
| CSSI-0186 | src/pages/inbox/InboxPage.css:162 | .inbox-manage-btn.active:hover [] | 対象外 | active/selected等の汎用状態名だけの一致。今回411個の置換対象classとして特定されない  |
| CSSI-0187 | src/pages/inbox/InboxPage.css:174 | .inbox-bulk-check-all [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0188 | src/pages/inbox/InboxPage.css:186 | .inbox-bulk-action [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0189 | src/pages/inbox/InboxPage.css:198 | .inbox-bulk-action:hover:not(:disabled) [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0190 | src/pages/inbox/InboxPage.css:200 | .inbox-bulk-action:disabled [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0191 | src/pages/inbox/InboxPage.css:201 | .inbox-bulk-delete [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0192 | src/pages/inbox/InboxPage.css:202 | .inbox-bulk-delete:hover:not(:disabled) [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0193 | src/pages/inbox/InboxPage.css:231 | .conv-item.bulk-selected [] | 維持 | 候補行/メニュー行/アバター等の既存専用ownerを維持。通常Buttonの箱へ置換しない。token参照への集約は当該ownerで行う  |
| CSSI-0194 | src/pages/inbox/InboxPage.css:242 | .inbox-sub-filter-pill [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0195 | src/pages/inbox/InboxPage.css:257 | .inbox-sub-filter-pill.active [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0196 | src/pages/inbox/InboxPage.css:262 | .inbox-sub-filter-pill:hover:not(.active) [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0197 | src/pages/inbox/InboxPage.css:275 | .conv-item [] | 維持 | 候補行/メニュー行/アバター等の既存専用ownerを維持。通常Buttonの箱へ置換しない。token参照への集約は当該ownerで行う  |
| CSSI-0198 | src/pages/inbox/InboxPage.css:292 | .conv-item:hover [] | 維持 | 候補行/メニュー行/アバター等の既存専用ownerを維持。通常Buttonの箱へ置換しない。token参照への集約は当該ownerで行う  |
| CSSI-0199 | src/pages/inbox/InboxPage.css:293 | .conv-item.selected [] | 維持 | 候補行/メニュー行/アバター等の既存専用ownerを維持。通常Buttonの箱へ置換しない。token参照への集約は当該ownerで行う  |
| CSSI-0200 | src/pages/inbox/InboxPage.css:295 | .conv-item.selected::after [] | 維持 | 候補行/メニュー行/アバター等の既存専用ownerを維持。通常Buttonの箱へ置換しない。token参照への集約は当該ownerで行う  |
| CSSI-0201 | src/pages/inbox/InboxPage.css:324 | .conv-item .conv-avatar [] | 維持 | 候補行/メニュー行/アバター等の既存専用ownerを維持。通常Buttonの箱へ置換しない。token参照への集約は当該ownerで行う  |
| CSSI-0202 | src/pages/inbox/InboxPage.css:412 | .inbox-page-filter-select [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0203 | src/pages/inbox/InboxPage.css:498 | .inbox-thread-action-btn [] | 外配置へ移管＋部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0204 | src/pages/inbox/InboxPage.css:513 | .inbox-thread-action-btn:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0205 | src/pages/inbox/InboxPage.css:517 | .inbox-thread-action-btn.danger:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0206 | src/pages/inbox/InboxPage.css:570 | .msg-translate-btn [] | 外配置へ移管＋部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0207 | src/pages/inbox/InboxPage.css:585 | .msg-translate-btn:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0208 | src/pages/inbox/InboxPage.css:589 | .msg-translate-btn:disabled [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0209 | src/pages/inbox/InboxPage.css:656 | .inbox-textarea [] | 外配置へ移管＋部品CSSへ削除移管 | root§Z設計案で解決: TextareaControl appearance=embedded,resize=none。border0/padding0/transparent/line-height1.4は専用共通入力tokenへ。flex1/min-width0は同native配置class。wrapperなし {'appearance': 'embedded', 'resize': 'none', 'shared_input_tokens': {'border': '0', 'padding': '0', 'background': 'transparent', 'line-height': '1.4'}, 'same_native_layout': {'flex': '1', 'min-width': '0'}} |
| CSSI-0210 | src/pages/inbox/InboxPage.css:670 | .inbox-textarea:disabled [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0211 | src/pages/inbox/InboxPage.css:672 | .send-attach-btn [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0212 | src/pages/inbox/InboxPage.css:687 | .send-attach-btn:hover:not(:disabled) [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0213 | src/pages/inbox/InboxPage.css:692 | .send-attach-btn:disabled [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0214 | src/pages/inbox/InboxPage.css:717 | .send-preview-remove [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0215 | src/pages/inbox/InboxPage.css:732 | .send-preview-remove:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0216 | src/pages/inbox/InboxPage.css:751 | .inbox-send-btn [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0217 | src/pages/inbox/InboxPage.css:766 | .inbox-send-btn:hover:not(:disabled) [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0218 | src/pages/inbox/InboxPage.css:768 | .inbox-send-btn:disabled [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0219 | src/pages/inbox/InboxPage.css:923 | .karte-open-link [] | 外配置へ移管＋部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0220 | src/pages/inbox/InboxPage.css:935 | .karte-open-link:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0221 | src/pages/inbox/InboxPage.css:1022 | .karte-toggle-btn [] | 部品CSSへ削除移管 | checked/focus-visibleと隣接sliderの結合をToggle専用ownerへ移す。裸TextControlの共通外観は適用しない  |
| CSSI-0222 | src/pages/inbox/InboxPage.css:1036 | .karte-toggle-btn ['@media (max-width: 1279px)'] | 部品CSSへ削除移管 | checked/focus-visibleと隣接sliderの結合をToggle専用ownerへ移す。裸TextControlの共通外観は適用しない  |
| CSSI-0223 | src/pages/inbox/InboxPage.css:1045 | .karte-toggle-btn:hover ['@media (max-width: 1279px)'] | 部品CSSへ削除移管 | checked/focus-visibleと隣接sliderの結合をToggle専用ownerへ移す。裸TextControlの共通外観は適用しない  |
| CSSI-0224 | src/pages/inbox/InboxPage.css:1082 | .karte-close-btn ['@media (max-width: 1279px)'] | 外配置へ移管＋部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0225 | src/pages/inbox/InboxPage.css:1090 | .karte-close-btn:hover ['@media (max-width: 1279px)'] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0226 | src/pages/inbox/InboxPage.css:1138 | .inbox-header-menu-item.danger ['@media (max-width: 1279px)'] | 対象外 | active/selected等の汎用状態名だけの一致。今回411個の置換対象classとして特定されない  |
| CSSI-0227 | src/pages/inbox/InboxPage.css:1139 | .inbox-header-menu-item.danger:hover ['@media (max-width: 1279px)'] | 対象外 | active/selected等の汎用状態名だけの一致。今回411個の置換対象classとして特定されない  |
| CSSI-0228 | src/pages/inbox/InboxPage.css:1162 | .inbox-send-btn ['@media (max-width: 767px)'] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0229 | src/pages/inbox/InboxPage.css:1188 | .right-panel-field [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0230 | src/pages/inbox/InboxPage.css:1196 | .right-panel-field::placeholder [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0231 | src/pages/inbox/InboxPage.css:1198 | select.right-panel-field [] | 部品CSSへ削除移管 | root設計案で解決: SelectControl indicator=none。現行appearance:noneと矢印なしを維持。native select1個、追加矢印DOMなし {'indicator': 'none', 'appearance': 'none', 'native_elements': 1, 'additional_arrow_dom': False} |
| CSSI-0232 | src/pages/inbox/InboxPage.css:1199 | .right-panel-field:focus [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0233 | src/pages/inbox/InboxPage.css:1200 | textarea.right-panel-field [] | 外配置へ移管＋部品CSSへ削除移管 | root設計案で解決: TextareaControl resize=none。min-height=var(--inbox-textarea-min-h)は同nativeの名前付き配置classで保持。wrapperなし {'resize': 'none', 'same_native_layout': {'min-height': 'var(--inbox-textarea-min-h)'}, 'new_wrapper': False} |
| CSSI-0234 | src/pages/inbox/InboxPage.css:1217 | .right-panel-tab [] | 外配置へ移管＋部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0235 | src/pages/inbox/InboxPage.css:1225 | .right-panel-tab:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0236 | src/pages/inbox/InboxPage.css:1226 | .right-panel-tab.active [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0237 | src/pages/inbox/InboxPage.css:1247 | .right-panel-save-indicator .saved [] | 対象外 | active/selected等の汎用状態名だけの一致。今回411個の置換対象classとして特定されない  |
| CSSI-0238 | src/pages/inbox/InboxPage.css:1262 | .karte-action-primary [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0239 | src/pages/inbox/InboxPage.css:1275 | .karte-action-primary:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0240 | src/pages/inbox/InboxPage.css:1306 | .karte-overflow-menu button [] | 維持 | 候補行/メニュー行/アバター等の既存専用ownerを維持。通常Buttonの箱へ置換しない。token参照への集約は当該ownerで行う  |
| CSSI-0241 | src/pages/inbox/InboxPage.css:1319 | .karte-overflow-menu button:last-child [] | 維持 | 候補行/メニュー行/アバター等の既存専用ownerを維持。通常Buttonの箱へ置換しない。token参照への集約は当該ownerで行う  |
| CSSI-0242 | src/pages/inbox/InboxPage.css:1320 | .karte-overflow-menu button:hover [] | 維持 | 候補行/メニュー行/アバター等の既存専用ownerを維持。通常Buttonの箱へ置換しない。token参照への集約は当該ownerで行う  |
| CSSI-0243 | src/pages/inbox/InboxPage.css:1370 | input[type="date"].karte-field-empty:not(:focus)::-webkit-datetime-edit [] | 維持 | 空のdate入力でブラウザー補助表示を隠す機能状態。type=date、empty class、focus条件と::-webkit-datetime-editを維持  |
| CSSI-0244 | src/pages/inbox/InboxPage.css:1432 | .inbox-settings-select [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0245 | src/pages/inbox/InboxPage.css:1449 | .inbox-toggle input [] | 部品CSSへ削除移管 | checked/focus-visibleと隣接sliderの結合をToggle専用ownerへ移す。裸TextControlの共通外観は適用しない  |
| CSSI-0246 | src/pages/inbox/InboxPage.css:1461 | .inbox-toggle input:checked + .inbox-toggle-slider [] | 部品CSSへ削除移管 | checked/focus-visibleと隣接sliderの結合をToggle専用ownerへ移す。裸TextControlの共通外観は適用しない  |
| CSSI-0247 | src/pages/inbox/InboxPage.css:1462 | .inbox-toggle input:checked + .inbox-toggle-slider::before [] | 部品CSSへ削除移管 | checked/focus-visibleと隣接sliderの結合をToggle専用ownerへ移す。裸TextControlの共通外観は適用しない  |
| CSSI-0248 | src/pages/inbox/InboxPage.css:1475 | .inbox-profile-modal-close [] | 外配置へ移管＋部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0249 | src/pages/inbox/InboxPage.css:1481 | .inbox-profile-modal-close:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0250 | src/pages/inbox/InboxPage.css:1487 | .inbox-translate-outbound-btn [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0251 | src/pages/inbox/InboxPage.css:1495 | .inbox-translate-outbound-btn:disabled [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0252 | src/pages/inbox/InboxPage.css:1496 | .inbox-translate-outbound-btn:hover:not(:disabled) [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0253 | src/pages/inbox/InboxPage.css:1521 | .outbound-translation-close [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0254 | src/pages/inbox/InboxPage.css:1527 | .outbound-translation-close:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0255 | src/pages/inbox/InboxPage.css:1554 | .outbound-translation-edit [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0256 | src/pages/inbox/InboxPage.css:1560 | .outbound-translation-edit:focus [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0257 | src/pages/inbox/InboxPage.css:1578 | .outbound-translation-send-btn [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0258 | src/pages/inbox/InboxPage.css:1585 | .outbound-translation-send-btn:disabled [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0259 | src/pages/inbox/InboxPage.css:1586 | .outbound-translation-send-btn:hover:not(:disabled) [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0260 | src/pages/inbox/InboxPage.css:1665 | .sales-form-option input[type="checkbox"] [] | 外配置へ移管＋部品CSSへ削除移管 | Checkboxの外観/寸法/accent-colorは共通Checkbox ownerへ。既存行/セル配置用margin/flexは同じnative要素の配置専用classへ。DataTable所有のcheckbox外観を残さない  |
| CSSI-0261 | src/pages/inbox/InboxPage.css:1674 | .sales-form-other-input [] | 外配置へ移管＋部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0262 | src/pages/inbox/InboxPage.css:1718 | .send-guard-btn [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0263 | src/pages/inbox/InboxPage.css:1728 | .send-guard-btn--translate [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0264 | src/pages/inbox/InboxPage.css:1732 | .send-guard-btn--asis [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0265 | src/pages/inbox/InboxPage.css:1737 | .send-guard-btn--cancel [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0266 | src/pages/inbox/InboxPage.css:1741 | .send-guard-btn:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0267 | src/pages/inbox/InboxPage.css:1743 | :root.force-dark .send-guard-btn--asis [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0268 | src/pages/integrations/CarrierIntegrationPage.css:92 | .carrier-env-card__delete-btn [] | 外配置へ移管＋部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0269 | src/pages/integrations/CarrierIntegrationPage.css:97 | .carrier-env-card__delete-btn:hover:not(:disabled) [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0270 | src/pages/schedule.css:272 | .schedule-calendar-checkbox [] | 外配置へ移管＋部品CSSへ削除移管 | Checkboxの外観/寸法/accent-colorは共通Checkbox ownerへ。既存行/セル配置用margin/flexは同じnative要素の配置専用classへ。DataTable所有のcheckbox外観を残さない  |
| CSSI-0271 | src/pages/schedule.css:843 | .schedule-input [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0272 | src/pages/schedule.css:843 | .schedule-textarea [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0273 | src/pages/schedule.css:853 | .schedule-input [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0274 | src/pages/schedule.css:858 | .schedule-textarea [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0275 | src/pages/schedule.css:863 | .schedule-input:focus [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0276 | src/pages/schedule.css:863 | .schedule-textarea:focus [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0277 | src/pages/schedule.css:1272 | .schedule-settings .toggle-switch input:checked + .toggle-switch-slider [] | 部品CSSへ削除移管 | checked/focus-visibleと隣接sliderの結合をToggle専用ownerへ移す。裸TextControlの共通外観は適用しない  |
| CSSI-0278 | src/pages/schedule.css:1272 | .schedule-page .toggle-switch input:checked + .toggle-switch-slider [] | 部品CSSへ削除移管 | checked/focus-visibleと隣接sliderの結合をToggle専用ownerへ移す。裸TextControlの共通外観は適用しない  |
| CSSI-0279 | src/pages/schedule.css:1277 | .schedule-settings .toggle-switch input:checked + .toggle-switch-slider::before [] | 部品CSSへ削除移管 | checked/focus-visibleと隣接sliderの結合をToggle専用ownerへ移す。裸TextControlの共通外観は適用しない  |
| CSSI-0280 | src/pages/schedule.css:1277 | .schedule-page .toggle-switch input:checked + .toggle-switch-slider::before [] | 部品CSSへ削除移管 | checked/focus-visibleと隣接sliderの結合をToggle専用ownerへ移す。裸TextControlの共通外観は適用しない  |
| CSSI-0281 | src/pages/schedule.css:1282 | .schedule-banner__close [] | 外配置へ移管＋部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0282 | src/pages-layout.css:227 | .sr-only [] | 維持 | 視覚非表示/色選択/checkbox等の機能用配置。通常TextControlの外観に置換しない。native typeとclassを保つ  |
| CSSI-0283 | src/pages-layout.css:246 | .login-card .form-group input [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0284 | src/pages-layout.css:255 | .login-card .form-group input:focus [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0285 | src/pages-layout.css:262 | .login-card .btn-primary [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0286 | src/pages-layout.css:275 | .login-card .btn-primary:hover:not(:disabled) [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0287 | src/pages-layout.css:280 | .login-forgot-link [] | 外配置へ移管＋部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0288 | src/pages-layout.css:292 | .login-forgot-link:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0289 | src/pages-layout.css:307 | .login-back-link [] | 外配置へ移管＋部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0290 | src/pages-layout.css:320 | .login-back-link:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0291 | src/pages-layout.css:354 | .color-swatch.selected [] | 対象外 | active/selected等の汎用状態名だけの一致。今回411個の置換対象classとして特定されない  |
| CSSI-0292 | src/pages-layout.css:372 | .color-swatch input[type="radio"] [] | 維持 | 視覚非表示/色選択/checkbox等の機能用配置。通常TextControlの外観に置換しない。native typeとclassを保つ  |
| CSSI-0293 | src/pages-layout.css:442 | .tab-nav button [] | 外配置へ移管＋部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0294 | src/pages-layout.css:451 | .tab-nav button:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0295 | src/pages-layout.css:454 | .tab-nav button.tab-active [] | 維持 | 候補行/メニュー行/アバター等の既存専用ownerを維持。通常Buttonの箱へ置換しない。token参照への集約は当該ownerで行う  |
| CSSI-0296 | src/pages-layout.css:527 | .role-item.active [] | 対象外 | active/selected等の汎用状態名だけの一致。今回411個の置換対象classとして特定されない  |
| CSSI-0297 | src/pages-layout.css:532 | .role-item.active:hover [] | 対象外 | active/selected等の汎用状態名だけの一致。今回411個の置換対象classとして特定されない  |
| CSSI-0298 | src/pages-layout.css:546 | .btn-block [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0299 | src/pages-layout.css:631 | .chk-label input[type="checkbox"] [] | 外配置へ移管＋部品CSSへ削除移管 | Checkboxの外観/寸法/accent-colorは共通Checkbox ownerへ。既存行/セル配置用margin/flexは同じnative要素の配置専用classへ。DataTable所有のcheckbox外観を残さない  |
| CSSI-0300 | src/pages-layout.css:655 | .permission-item input[type="checkbox"] [] | 外配置へ移管＋部品CSSへ削除移管 | Checkboxの外観/寸法/accent-colorは共通Checkbox ownerへ。既存行/セル配置用margin/flexは同じnative要素の配置専用classへ。DataTable所有のcheckbox外観を残さない  |
| CSSI-0301 | src/pages-layout.css:801 | .carrier-env-card__delete-btn [] | 外配置へ移管＋部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0302 | src/pages-layout.css:806 | .carrier-env-card__delete-btn:hover:not(:disabled) [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0303 | src/sidebar.css:156 | .sidebar-item.active [] | 対象外 | active/selected等の汎用状態名だけの一致。今回411個の置換対象classとして特定されない  |
| CSSI-0304 | src/sidebar.css:244 | .sidebar-sub-item.active [] | 対象外 | active/selected等の汎用状態名だけの一致。今回411個の置換対象classとして特定されない  |
| CSSI-0305 | src/topbar.css:44 | .topbar-search input [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0306 | src/topbar.css:54 | .topbar-search input::placeholder [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0307 | src/topbar.css:109 | .avatar-btn [] | 維持 | 候補行/メニュー行/アバター等の既存専用ownerを維持。通常Buttonの箱へ置換しない。token参照への集約は当該ownerで行う  |
| CSSI-0308 | src/topbar.css:132 | .avatar-btn:hover [] | 維持 | 候補行/メニュー行/アバター等の既存専用ownerを維持。通常Buttonの箱へ置換しない。token参照への集約は当該ownerで行う  |
| CSSI-0309 | src/topbar.css:187 | .user-drawer-close [] | 外配置へ移管＋部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0310 | src/topbar.css:200 | .user-drawer-close:hover [] | 部品CSSへ削除移管 | 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持  |
| CSSI-0311 | src/topbar.css:236 | .user-drawer-action [] | 維持 | 候補行/メニュー行/アバター等の既存専用ownerを維持。通常Buttonの箱へ置換しない。token参照への集約は当該ownerで行う  |
| CSSI-0312 | src/topbar.css:252 | .user-drawer-action:hover [] | 維持 | 候補行/メニュー行/アバター等の既存専用ownerを維持。通常Buttonの箱へ置換しない。token参照への集約は当該ownerで行う  |
| CSSI-0313 | src/topbar.css:256 | .user-drawer-action--danger [] | 維持 | 候補行/メニュー行/アバター等の既存専用ownerを維持。通常Buttonの箱へ置換しない。token参照への集約は当該ownerで行う  |
| CSSI-0314 | src/topbar.css:261 | .user-drawer-action--danger:hover [] | 維持 | 候補行/メニュー行/アバター等の既存専用ownerを維持。通常Buttonの箱へ置換しない。token参照への集約は当該ownerで行う  |

宣言原値・移管先・AST上の肯定/否定type条件はJSON参照。移管設計の割当と実CSS適用の検証を混同しない。
