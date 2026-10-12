# ay2a-class-split（AY-2a 手順1。旧ページ規則の宣言を 外観 / 配置 / 状態 に分類した事実の表）

base HEAD 08f59418c772fab0bed6137e818d5e87de5c91f2。全利用の列挙は /tmp/CC報告ファイル/ay2a-1-grep.txt（54行）。

分類の定義（カード手順1）: 外観＝色・枠・余白・文字・角丸・影・背景・高さ／配置＝幅・flex・margin・位置／状態＝条件付きで表示を切り替えるもの。外観は金型の種類へ移す。配置・状態はページに残す。

## 規則別

| class | file:line（変更前） | 宣言 | 分類 | 移管後の扱い |
|---|---|---|---|---|
| `.right-panel-field` | InboxPage.css:1160 | `width:100%` | 配置（金型の基本規則も 100% で同値） | 本体は a(InboxKartePanel.tsx:365)・button(SalesFormMultiSelect.tsx:105 `sales-form-trigger`) が使うため保持 |
| 〃 | 〃 | `box-sizing:border-box` | 外観（金型の基本規則と同値） | 〃 |
| 〃 | 〃 | `background:var(--karte-field-bg)` `border:0.5px solid var(--karte-field-bd)` `border-radius:var(--radius-md)` `padding:var(--karte-field-py) var(--karte-field-px)` `font-size:var(--font-sm)` `color:var(--text-primary)` `font-family:inherit` `transition:border-color var(--transition-micro)` | 外観 | 種類 karte に写した。本体は a・button 用に保持（input 専用の宣言なし: 上記は a・button にも効く宣言のみ） |
| 〃 | InboxPage.css:1168 `::placeholder` | `color:var(--text-muted)` | 外観（input 専用） | 種類 karte に写した。移管後 `.right-panel-field` を持つのは a と button だけで placeholder を持たないため利用0 → 規則ごと削除 |
| 〃 | InboxPage.css:1169 `:focus` | `outline:none` `border-color:var(--accent)` | 外観（擬似クラス） | 種類 karte の :focus に写した。a・button の :focus に効くため保持 |
| `.karte-field-empty` | InboxPage.css:1339 `input[type="date"].karte-field-empty:not(:focus)::-webkit-datetime-edit` | `color:transparent` | 状態（値が空のとき日付の mm/dd/yyyy を隠す） | 保持（className `karte-field-empty` を条件付きで残す） |
| `.sales-form-other-input` | InboxPage.css:1630 | `margin-top:var(--space-1)` `width:100%` | 配置 | 保持（className 残す。data-testid `sales-form-other-input` は別） |
| `.search-input-field` | components.css:67 | `border:1px solid var(--border-strong)` `border-radius:var(--radius-md)` `background:var(--bg-subtle)` `font-size:var(--font-base)` `color:var(--text-primary)` `outline:none` `box-sizing:border-box` `transition:border-color/box-shadow var(--transition-micro)` | 外観 | 種類 search に写した（金型と同値の宣言は省略）。他の利用0 → 規則ごと削除 |
| 〃 | components.css:77 `::placeholder` | `color:var(--text-secondary)` | 外観 | 種類 search に写した。削除 |
| 〃 | components.css:80 `:focus` | `border-color:var(--accent)` `box-shadow:var(--search-focus-glow)` | 外観 | 種類 search の :focus に写した。削除 |
| `.inbox-search-input` | InboxPage.css:116 | `width:100%` | 配置 | 保持（className 残す） |
| 〃 | 〃 | `padding: calc(var(--space-2) + 1.5px) var(--space-3) calc(var(--space-2) + 1.5px) calc(var(--space-3) + 16px + var(--space-2))`（コメント「inbox固有: width と icon用 padding-left のみ上書き」） | **外観（余白）。ただし検索アイコン(`.inbox-search-icon`)分の左余白を含むため配置とも読める＝分類に迷う宣言** | カードの定義（余白＝外観）に従い種類 search に写し、ページ側から削除した。種類 search の利用は現状この1件のみ。切り戻す場合は FormField.css の search 規則の padding を外しページ規則へ戻す（特異度は種類 (0,2,0) がページ規則 (0,1,0) に勝つため、ページに残す場合は選択子を強める必要がある） |
| `.schedule-input` | schedule.css:813 | `width:100%` | 配置（金型と同値） | 利用0 → 規則ごと削除 |
| 〃 | 〃 | `border:1px solid var(--border)` `border-radius:var(--radius-md)` `background:var(--bg-surface)` `color:var(--text-primary)` `font-size:var(--font-sm)` | 外観 | 種類 schedule に写した（金型と同値の border・background・color は省略）。削除 |
| 〃 | schedule.css:822 | `min-height:var(--comp-input-height-sm)` `padding:0 var(--space-3)` | 外観 | 種類 schedule に写した。削除 |
| 〃 | schedule.css:827 `:focus` | `outline:none` `border-color:var(--accent)` `box-shadow:var(--focus-ring-shadow)` | 外観 | 金型の :focus と同値のため種類側の :focus 規則は不要。削除 |
| `.db-weekly-composer-input` | WeeklyAdvisorSection.css:205 | `width:100%` | 配置（金型と同値） | 利用0 → 規則ごと削除 |
| 〃 | 〃 | `border-radius:var(--radius-md)` `background:var(--bg-primary)` `color:var(--text-primary)` `padding:var(--space-2) var(--space-3)` `font:inherit` `resize:vertical` | 外観 | 種類 composer に写した（color・padding は金型と同値で省略）。削除 |
| 〃 | 〃 | `border:1px solid var(--border-subtle)` | 外観。`--border-subtle` は未定義のため無効（computed は枠なし） | 種類 composer は `border:none`（computed 同値）。削除 |
| 〃 | WeeklyAdvisorSection.css:216 `:focus` | `outline:2px solid var(--accent)` `outline-offset:1px` | 外観 | 種類 composer の :focus に写した。削除 |

## 試験・コードが参照する class の確認

`git grep right-panel-field|search-input-field|inbox-search-input|schedule-input|db-weekly-composer-input|karte-field-empty|sales-form-other-input -- frontend` を frontend/tests-e2e・frontend 内の *.test.*・tests に限定すると該当は tests/qa-smoke/scene-09.spec.ts:164 の `[data-testid='sales-form-other-input']`（属性セレクタ。class ではなく data-testid で、本便は変更しない）の1件のみ。class を参照する試験は0件。
