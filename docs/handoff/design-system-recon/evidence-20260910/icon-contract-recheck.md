# 通常アイコンの入口再照合（2026-09-11）

[設計§AE](../../../specs/design-system/design.md)の実装前根拠。基準76c6dff98e3fa68f47c381d044e86fd0564d9509。

読み取り担当overlay_contract_auditがTypeScriptのIconProps呼出signatureで直接/別名/辞書/動的JSXを再照合。全152、stories/test/spec/design-previewを除く118箇所/39ファイル。外部style1/color0/ref0/spread0、aria-hidden86（全文字列true）、aria-label/labelledby/describedby/role/focusable各0、weight17。除外後件数を全ソース件数と混同しない。

- constants/icons.tsx:23–32/97–110: 公開propsとhi。size既定24、number|string、同SVG ref保持。
- components/GoogleCalendarStatusBar.tsx:168–172: 唯一style、marginRight=var(--space-2)/flexShrink0。同部品参照はstories.tsx:9のみ。cfg.colorの継承は保持。
- pages/RolesPage.tsx:414–423、pages/AdminHubPage.tsx:64–72、GoogleCalendarStatusBar:112–150の動的経路も照合。cloneElement/createElementでの属性追加検出0。
- lock:2021–2022と配布Heroicons2.2.0 CheckIcon.js:7–15。aria-hidden=trueの後にpropsが上書き。静的HTMLで未指定true、undefined転送は属性消失、falseはfalse、label+roleだけではtrueを確認（担当実行、rootは報告とソースを確認）。

rootは実TSXの親color/size14/style2宣言と公式React common資料を確認。Context7ツール0、許可された公式代替でHeroicons生成scriptを確認。生成物GitHubURLは404だったため根拠には採用せず、生成scriptと配布物を使用。詳細な契約/対処/受入/自己審査は設計§AE。製品実装・実ブラウザー検証は未実施。過去のSpinner草案のtrack案や存在しないon-solid参照は今回の根拠にしない。


保存した実物: [全152対象と集計](icon-contract-targets.json)、[型照合スクリプト](icon-contract-audit.cjs)、[Heroicons HTML5ケース](icon-contract-aria-baseline.txt)。同一SHAで全一覧を回収し件数一致を担当確認、rootがJSON/HTML/スクリプトを直接読んだ。型名IconPropsを含むcall signatureを抽出する有限手法であり任意JavaScriptの意味解析の完全性は主張しない。
