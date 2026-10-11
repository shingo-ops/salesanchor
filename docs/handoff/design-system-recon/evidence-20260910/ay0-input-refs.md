# ay-refs

base HEAD f0f7ef8c7d89c97d42950e0ab111644b316dd99d

## text-like input の ref（ページ側。AST: ay-inventory.json の has.ref）= 2件

| 場所 | 用途 | 根拠行 |
|---|---|---|
| frontend/src/components/InventoryPicker.tsx:218 | ref={inputRef}。getBoundingClientRect で候補リスト座標計算(:100-101)、外側mousedown判定 inputRef.current?.contains(target)(:125) | :93 `const inputRef = useRef<HTMLInputElement \| null>(null);` / :101 `const r = inputRef.current.getBoundingClientRect();` |
| frontend/src/components/InventorySearchBar.tsx:273 | 同上(:126-127, :152) | :119 `const inputRef = useRef<HTMLInputElement \| null>(null);` / :127 `const r = inputRef.current.getBoundingClientRect();` |

focus() 呼出し: 上記2ファイルに `.focus()` なし（grep 結果）。autoFocus 属性: text-like 0件。

## text-like 以外の ref（参考、金型対象外）
- DataTable.tsx:174 checkbox / AvatarUpload.tsx:114 file / InboxMessageThread.tsx:755 file / FedexEtdSetupGuide.tsx:509,538 file / TcgLineImportPage.tsx:325 file / AnalysisDashboardPanel.tsx:770 file

## textarea 先例（InboxMessageThread）
- frontend/src/pages/inbox/InboxMessageThread.tsx:20 `import { TextareaControl } from "../../components/Textarea";`
- :99 `const textareaRef = useRef<HTMLTextAreaElement>(null);` / :113,:126 `textareaRef.current?.focus();` / :737-738 `<TextareaControl ref={textareaRef}`
- Textarea.tsx:44 `forwardRef<HTMLTextAreaElement, TextareaControlProps>`、:56 `<textarea ref={ref} id={id} className={controlClass} {...rest} />`

## onKeyDown（text-like 7件）
- components/InventoryPicker.tsx:226（ハンドラ :188）、components/InventorySearchBar.tsx:281（:231）
- pages/super-admin/DexTab.tsx:204 / KnowledgeAliasesTab.tsx:300,:379（Enter検索）/ pages/inventory/InventoryPage.tsx:394（Enter検索。※type=search） / features/tcg-analysis-review/ProductMasterDrawer.tsx:473（Enter検索）
- <TextField> 経由でも onKeyDown が 9 件渡されている（TextField は ...rest を input に渡すため通る）。

## 現行 TextField の ref
- TextField.tsx:29 は通常の関数コンポーネントで forwardRef なし。ref を渡す利用は <TextField> 220件中 0件（moldAttrCounts に ref なし）。React 18 では関数コンポーネントに ref を渡しても転送されない。
