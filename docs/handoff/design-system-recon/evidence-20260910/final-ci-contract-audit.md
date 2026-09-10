# 最後に入れるCIの限定契約案（root審査後に縮小改訂）

2026-09-10、担当 /root/ci_preflight_readonly。以前の汎用JS解析・runtime入力検証・全計算adapter移管案を本書で置換する。正式文書・製品・CIは未変更。

## 観測

固定origin/main: `3bdf33d55d1dc7ee90a7eea7fd112dc76d51b1fe`。git showで観測し、最新mainとの一致は主張しない。文書参照はPR #3407 head f8c4b19f。

| 実物（固定SHA） | 確認事実 |
|---|---|
| scripts/check-ui-governance.js:36/333 | pagesの変更分だけ、同種件数が増えた場合のみ失敗 |
| 同:51/66/120 | show/diff失敗を空へ変換、ui-allowで免除 |
| frontend/scripts/check-css-hardcoded-colors.js:20/42/58 | basenameでindex/tokens除外、変数定義行も除外 |
| check-css-hardcoded-values.js PATTERNS | px中心。var/calcを含む値をskipするパターンあり |
| check-icon-sync.js:38/54 | 両側抽出0件でも一致成功 |
| check-dark-parity.js | 最初のroot/darkを抽出。全条件の解析ではない |
| check-color-token-sync.js | 最初のrootと8接頭辞のカタログ掲載を比較 |
| frontend/eslint.config.js:221–230 | PageLayout/SchedulePageはno-restricted-syntax全体off |
| .github/workflows/ui-governance-gate.yml:12–39 | 全PR・Node22・npm ciなし・旧22テストと旧本体 |
| .github/workflows/frontend-check.yml:5/26/34/38 | frontend/**で起動・npm ci/check:all/tsc |

lock値: TypeScript5.9.3、PostCSS8.5.15、postcss-value-parser4.2.0、postcss-selector-parser7.1.1。TSは既存直接依存、CSSパーサーを直接使う場合は最後のCI便で直接devDependenciesへ明示する。間接依存の偶然の配置に依存しない。

## 責任と導入条件

CIの責任は、native要素の登録owner照合、共通部品の禁止style/className上書き、CSS定数/所有selector、数値生成同期、ui-allow脱却に限定する。画面の意味・任意JSの完全解析・顧客入力の新しい安全検査は含めない。

画面移行が終わった後に入れる。baseline・既存件数許容・初回免除は作らない。対象全件で違反0・検査不能0が合格。移行途中を許可登録で緑にしない。配置/幅/比率の既存所有元は保持する。全計算を共通部品へ移すことは目的ではない。利用者色の名前付き入口は既存所有関数内に限定し、新しいラッパーは作らない。

## 有限な検査方式

1. frontend/srcのts/tsx/js/jsx/cssを全件走査する。物理除外はtest/spec、story、catalogの確定したパスのみ。components/features/hooks/constantsは除外しない。index.css/tokens.cssはパレット/非色定義を許可する宣言位置だけ特例とし、ファイル全体をskipしない。
2. TypeScript既存APIでJSX属性・タグ、import、トップレベルexportとその本体を走査する。対応構文は関数宣言、arrow、明示したforwardRef/memoパターン、通常のimport alias/re-export。汎用コンパイラ/実行時データフローエンジンを作らない。対応外の所有部品定義は診断を出し、標準構文へ整理するか個別レビュー後に限定パターンを追加する。
3. owner keyは完全module相対パス+exportName+nativeTag+inputType。helperの許可はimplementationBindingを明示した場合のみ。フォルダー全体・同ファイル別exportへ許可を拡張しない。登録不存在、重複、対象不一致、使われない登録は規則違反exit1。ファイル読取/parse失敗だけはexit2。
4. native button/select/textarea/input/tableと表構造、統一対象のroleを登録対象にする。input省略はtext。共通入力の動的typeは公開型の有限unionとtscで検証する。独自any/動的タグで解析を回避するコードは、限定検査の「対応外構文」違反exit1として実装役へ戻す。通常の業務データに型制約を追加しない。
5. 共通部品の公開APIから自由なstyle/classNameを外し、必要なvariant/density等を有限指定にする。tscで全呼出しを確認。限定AST検査は明示した禁止属性と、共通部品への未確認spreadを拒否する。既存のevent/ref/aria/data属性の受け渡しは専用props型で保ち、製品一般のspreadを禁止しない。tsc回避のany/assertionを用いた共通外観の上書きはレビュー対象として残す。
6. CSSは宣言とselectorを構文で検査する。パレット直色/非色数値の定義元は完全パスと許可する宣言に限定。varと直値の混在を行単位でskipしない。部品所有selectorは所有CSSだけで定義し、ページ側の同class/子孫selectorによる上書きを拒否。:is/:where/@media/@layer等の現行使用パターンはfixtureで固定する。任意selectorの数学的な全一致判定は保証しない。
7. 動的配置/列幅/カレンダー座標/進捗計算は既存関数と一般layout styleに保持する。禁止style/className検査は共通部品呼出しの外観上書きに限定し、ページの一般layout styleを一律禁止しない。共通UI内部の装飾だけ共通propsへ移し、利用者色は既存owner内の名前付き色入口・指定propertyで保持する。値clamp、形式検証、fallback、NaN扱い、アクセス制限を新設しない。既存のMath.min/Math.max/||/??や判定閾値はそのまま保つ。変更が必要なら外観SSOTとは別修正。
8. icon TS生成物はCSSを元に一時生成しbytes比較。必須sm/md/base/lg/xlの5キー存在、重複/不正単位を確認。CIは自動修正しない。
9. ui-allowコメントは新検査の免除として使わない。検査/登録/除外の変更は人がPRレビューする。本人認証API、本文文字列を本人認証扱いする仕組み、新しいRuleset操作を追加しない。

## layoutClassNameの有限契約（root確定）

共通部品に渡すlayoutClassNameの配置classだけを対象とする。ページ一般のlayout styleを一律禁止する規則ではない。許可propertyの上限は次の完全リスト。実物から得た19propertyを含むことはrootの照合報告であり、本追補で独立再測定はしていない。

```text
display, position, inset, top, right, bottom, left, z-index,
width, min-width, max-width, height, min-height, max-height,
margin, margin-top, margin-right, margin-bottom, margin-left,
margin-inline, margin-inline-start, margin-inline-end,
margin-block, margin-block-start, margin-block-end,
flex, flex-grow, flex-shrink, flex-basis, align-self, justify-self, order,
grid-area, grid-column, grid-column-start, grid-column-end,
grid-row, grid-row-start, grid-row-end
```

padding/gap/color/font/border/outline/shadow/radius/opacity/transformと独自CSS変数宣言は許可しない。上限リスト外のproperty、!important、定義を解決できないclassは規則違反exit1。CSS自体を読めない・解析できない場合はexit2。各classの関連宣言を有限selectorパターンで照合し、装飾を配置という名前で免除しない。

部品が所有する寸法は上限リストからさらに除く。
- Button/Toggle/Checkbox/Radio/通常TextField/Select: height/min-height/max-heightを禁止。size propsと所有CSSが管理する。
- Icon: width/min-width/max-width/height/min-height/max-heightを禁止。sizeが管理する。
- Textarea: min-heightを許可。Card等containerの寸法も許可。
- Button幅: fullWidth等の共通propsを優先。既存明示幅が必要な登録済み配置だけを保持する。

値に関する既存token規則は維持する。許可propertyだから直値全てが自由になるわけではない。新しい入力補正やラッパーは追加しない。

## 動的指定の実在棚卸し

再実行可能な調査スクリプト: `dynamic-style-fixed-audit.cjs`。固定git treeをTypeScript ASTで読み取り。詳細172行は `dynamic-style-fixed-audit.json` のDS-001〜172（file/line/式/分類）。これは検査実装ではなく調査用。

232 TS/TSX/JS/JSXファイル、JSX style属性924。非リテラル候補172項目＝property103＋style式52＋style内spread17。1つのstyleに複数項目を数えるため、172はstyle属性数でも実行時変化数でも違反数でもない。JSX spread属性は別に6。

| 最終責任 | 件数 | 扱い |
|---|---:|---|
| ①共通UI外観props/所有CSS | 113 | 状態条件は保ち、Tableの既存TA表/部品契約へ。既存色token参照もそのまま活用 |
| ②既存の配置/幅/比率/数値所有元 | 38 | 元の関数・式を保持。新adapter不要。内訳は元の配置26＋icon数値6＋Skeleton内部幅1＋一般layout5 |
| ③利用者指定色の既存owner入口 | 13 | role/owner色を既存関数内の指定propertyへ。色だけの入口で部品外観全体を上書きしない |
| ④カレンダー用途色token | 8 | 既存関数のcategory値を用途色正本へ接続 |
| 未写像 | 0 | 全172項目の設計責任を割当。実装/視覚試験の完了ではない |

JSONのfinalMapping/既存関数chain/式が一対一の対応表。172件のadapter未割当という前提は撤回。既存表239属性と重なる①は同じTA表と統合し、独立した違反許可台帳を増やさない。

### 既存動作を保存すべき具体箇所

- InventoryPicker.tsx:255–257、InventorySearchBar.tsx:363–368: getBoundingClientRect由来のtop/left/widthと既存Math.max/min。既存InventoryPicker/InventorySearchBar内で保持。新しい部品・上限・補正を加えない。
- loading/ProgressBar.tsx:25/59、DashboardPage.tsx:206–221、FunnelSection.tsx:63–76、FunnelRevenuePage.tsx:79/112: pct/clamped/達成率。既存関数内で保持。既存Math.minと閾値を保つ。
- schedule/SchedulePageImpl.tsx:195/203、674/684/700–703: buildPopoverPosition、時刻とlane座標。既存SchedulePopover/ScheduleWeekGrid内で保持。新しいラッパーや座標validatorを作らない。
- roles/RolesPage.tsx:355/381/500/516/560: role色、入力中の色、選択パレット。既存RolesPage内のrole色入口として名前付け。現行|| fallbackと入力値を保持。新しいラッパーなし。
- schedule/SchedulePageImpl.tsx:517/525/548/556/638/704/788、ScheduleSettingsPage.tsx:20: owner色/背景/checkbox accent。既存ScheduleSidebar/WeekGrid/MonthGrid/OwnerBadge内で色入口を名前付け。既存owner?.color ?? DEFAULT_OWNER_COLORを維持。新しいラッパーなし。
- GoogleCalendarStatusBar.tsx:115–149: cfgは状態別token表。顧客自由色に分類しない。
- TcgLineImportPage.tsx:590–625: thStyle/tdStyleは装飾定数、colorMapはstatus用途色。TcgParallelReportPage.tsx:106–111のdiffColorは閾値に応じた既存用途色。任意外部色adapterにしない。
- ProductsPage.tsx:333–334: rowStyleはis_archived時opacity。Table行状態の移行へ接続。
- ReviewSection.tsx:378–384: sectionStyleは固定装飾。動的配置の例外にしない。
- Skeleton.tsx:14–81: barへのstyleは有限な内部presetと幅。Spinner.tsx:22とicons.tsx:97–106のcolor/style propsは公開互換の移行調査を必要とする。

### HTML/DOM書込

固定treeのgit grepによるdangerouslySetInnerHTML/setProperty検索は一致0（exit1）。ASTの明示dangerouslySetInnerHTML属性、property access setProperty呼出し、innerHTML/cssText代入も0件。対応外の別名呼出し、文字列生成、外部ライブラリ内部が不存在という証明ではない。実在0なのでHTML用の架空adapter・新しいHTML安全検査は設計に追加しない。

## CIへの接続と終了値

提案CLI frontend/scripts/check-design-system.js とfixtureテストを追加し、check:allへ接続。既存UI governance job名/全PR起動を維持し、Node22 setup後にfrontend/npm ciを加えて限定検査テストと全件検査を実行する。検査本体/登録/CIだけの変更でも動く。既存check:allとtscを併用する。

exit0＝全件検査完了・違反0。exit1＝規則違反（登録不整合、禁止属性、対応外構文等）。exit2＝列挙/読取/parse/ツール起動不能。対象src不存在/対象0/正本読取不能はexit2。結果識別子は1回のみ、errorからpass/no-targetへ変換しない。スキャンSHA、対象件数、file/line/ruleを出す。

旧22ケースのui-allow成功/table非検出は新方針と矛盾するため期待を更新。旧22期待維持を義務付けた旧第一便案はそのまま流用しない。BASE/HEAD差分比較自体を全件検査へ置換するため、旧比較器の独立修復を先行しない。

## 受入ケース（未実行・最低27 ID）

| ID | 入力 | 期待 |
|---|---|---|
| C01 | 変更なしだが未移行buttonが存在 | exit1 |
| C02 | featuresの生select、componentsの未登録input | 各exit1 |
| C03 | 生table削除1/追加1 | exit1 |
| C04 | 正規ownerのnative | exit0 |
| C05 | 同module別exportにnative | exit1 |
| C06 | 正規import aliasと同名偽物 | 正規exit0、偽物exit1 |
| C07 | registry不在module/export・重複・unused・未対応HOC | 全てexit1 |
| C08 | 所有inputの省略/有限union/無制限type | text照合・有限union照合、無制限exit1 |
| C09 | ui-allow付き生select | exit1 |
| C10 | test/story/catalogの明示除外 | 対象外。製品ファイルの除外追加はレビューで拒否 |
| C11 | 共通部品にstyle/className/未確認spread | CLIはexit1。公開型違反の別fixtureではtscも非0 |
| C12 | 有限なevent/ref/aria props | exit0＋tsc成功 |
| C13 | ページCSSから所有selectorを上書き | exit1 |
| C14 | 定義元パレットと用途alias/ページ直色 | 前者exit0、後者exit1 |
| C15 | 別dir/index.css/変数宣言に直色 | exit1 |
| C16 | varと直値混在/%23/現行色表現 | 契約外exit1、コメントは非検出 |
| C17 | 同条件token重複/参照欠落 | exit1 |
| C18 | 正当media切替/必須dark用途色欠落 | 前者exit0、後者exit1 |
| C19 | ScheduleWeekGridのlane座標/InventoryPickerのrect幅を既存styleに保持 | exit0。式は現状と同一、新adapterなし |
| C20 | RolesPageのrole色とOwnerBadgeのowner色を既存owner入口へ | exit0。同入力の色/fallbackが一致、新clamp/ラッパーなし |
| C21 | icon両側0/キー不足/生成物手修正 | exit1 |
| C22 | PageLayout/SchedulePageの同じ違反 | 共にexit1（eslint offに依存しない） |
| C23 | 列挙/読取/parse不能・srcなし/対象0 | exit2、passなし |
| C24 | 検査/registry/workflowのみ変更 | 実CI jobが起動しfixture/全件検査成功 |
| C25 | 正常全件fixture | exit0、件数/SHA/判定を表示 |
| C26 | layoutClassNameのmargin/textarea min-height、同classへのpaint混入/!important/未定義class | 前2例exit0、後3例それぞれexit1 |
| C27 | layoutClassNameによるButtonのheight/min-height/max-height、Iconのwidth/height/minmax | 全例exit1。正規size propsと所有CSSはexit0 |

C01〜27は上記具体入力のfixtureを作る仕様で、実行済みではない。C11の禁止styleは共通Button等への属性、C19の一般layout styleは許可という対照を必須にする。失敗fixtureは一時領域で行い、製品treeを書き換えない。既存clamp/fallbackを保存する比較は受入試験であり新しい製品runtime制約ではない。

## ADR変更と保証限界

ADR-144を正式に改訂してからカードを出す。変更点: pages差分→全src、増分だけ→違反0、3対象→合意した所有部品、ui-allow免除→owner登録、旧AC5/AC6の期待更新。共通部品優先・業務挙動保持・人のPRレビューは維持。

有限構文と公開APIの型で防ぐ範囲を保証する。任意JSの実行結果、同じ見た目を別名divで再発明した意味、複雑なselectorの全到達先、外部ライブラリ内部まで自動判定したとは言わない。用途分類/公開API/対応外構文はレビューで確認する。CIだけで見た目や業務挙動の全てを証明しない。

Context7は利用可能ツール0件。許可された公式資料代替を使用: TypeScript https://github.com/microsoft/TypeScript/wiki/Using-the-Compiler-API 、PostCSS https://postcss.org/api/ 、ESLint https://eslint.org/docs/latest/use/configure/rules （2026-09-10確認）。既存パーサーと有限fixtureに限定し、外部事例の改善率は主張しない。

## 13利用者色・8用途色・6icon寸法の全件と実在関数

SchedulePopover/Sidebar/WeekGrid/MonthGridはSchedulePageImpl.tsx内の非export関数、OwnerBadgeはScheduleSettingsPage.tsx内の非export関数。exportを増やさず既存export+implementationBindingで所有を特定する。RolesPageはdefault export、PlatformIconはnamed export（constants/icons.tsx:312）。

| ID | 既存箇所 | 関数 | 式 | 責任 |
|---|---|---|---|---|
| DS-032 | frontend/src/constants/icons.tsx:319 | PlatformIcon | `width: size` | 2 |
| DS-033 | frontend/src/constants/icons.tsx:319 | PlatformIcon | `height: size` | 2 |
| DS-034 | frontend/src/constants/icons.tsx:329 | PlatformIcon | `width: size` | 2 |
| DS-035 | frontend/src/constants/icons.tsx:329 | PlatformIcon | `height: size` | 2 |
| DS-036 | frontend/src/constants/icons.tsx:343 | PlatformIcon | `width: size` | 2 |
| DS-037 | frontend/src/constants/icons.tsx:343 | PlatformIcon | `height: size` | 2 |
| DS-071 | frontend/src/pages/roles/RolesPage.tsx:355 | RolesPage | `borderLeft: `4px solid ${r.color &#124;&#124; "var(--border-color)"}`` | 3 |
| DS-072 | frontend/src/pages/roles/RolesPage.tsx:381 | RolesPage | `background: selectedRole.color &#124;&#124; "var(--bg-hover)"` | 3 |
| DS-073 | frontend/src/pages/roles/RolesPage.tsx:500 | RolesPage | `background: roleForm.color` | 3 |
| DS-074 | frontend/src/pages/roles/RolesPage.tsx:516 | RolesPage | `background: c` | 3 |
| DS-075 | frontend/src/pages/roles/RolesPage.tsx:560 | RolesPage | `background: r.color &#124;&#124; "var(--bg-hover)"` | 3 |
| DS-077 | frontend/src/pages/schedule/SchedulePageImpl.tsx:212 | SchedulePopover | `background: cssVar(meta.tintVar)` | 4 |
| DS-078 | frontend/src/pages/schedule/SchedulePageImpl.tsx:212 | SchedulePopover | `color: cssVar(meta.textVar)` | 4 |
| DS-079 | frontend/src/pages/schedule/SchedulePageImpl.tsx:517 | ScheduleSidebar | `background: owner.color` | 3 |
| DS-080 | frontend/src/pages/schedule/SchedulePageImpl.tsx:525 | ScheduleSidebar | `accentColor: owner.color` | 3 |
| DS-081 | frontend/src/pages/schedule/SchedulePageImpl.tsx:548 | ScheduleSidebar | `background: owner.color` | 3 |
| DS-082 | frontend/src/pages/schedule/SchedulePageImpl.tsx:556 | ScheduleSidebar | `accentColor: owner.color` | 3 |
| DS-083 | frontend/src/pages/schedule/SchedulePageImpl.tsx:638 | ScheduleWeekGrid | `background: ownerMeta.color` | 3 |
| DS-084 | frontend/src/pages/schedule/SchedulePageImpl.tsx:645 | ScheduleWeekGrid | `background: cssVar(meta.tintVar)` | 4 |
| DS-085 | frontend/src/pages/schedule/SchedulePageImpl.tsx:645 | ScheduleWeekGrid | `color: cssVar(meta.textVar)` | 4 |
| DS-092 | frontend/src/pages/schedule/SchedulePageImpl.tsx:704 | ScheduleWeekGrid | `background: ownerMeta.color` | 3 |
| DS-093 | frontend/src/pages/schedule/SchedulePageImpl.tsx:715 | ScheduleWeekGrid | `background: cssVar(meta.tintVar)` | 4 |
| DS-094 | frontend/src/pages/schedule/SchedulePageImpl.tsx:715 | ScheduleWeekGrid | `color: cssVar(meta.textVar)` | 4 |
| DS-095 | frontend/src/pages/schedule/SchedulePageImpl.tsx:788 | ScheduleMonthGrid | `background: ownerMeta.color` | 3 |
| DS-096 | frontend/src/pages/schedule/SchedulePageImpl.tsx:798 | ScheduleMonthGrid | `background: cssVar(meta.tintVar)` | 4 |
| DS-097 | frontend/src/pages/schedule/SchedulePageImpl.tsx:798 | ScheduleMonthGrid | `color: cssVar(meta.textVar)` | 4 |
| DS-098 | frontend/src/pages/schedule/ScheduleSettingsPage.tsx:20 | OwnerBadge | `background: owner.color` | 3 |

## 限定設計判断の確認

rootが配置propertyの有限リストと部品寸法の除外を確定したため、本契約について追加の設計判断はない。最終owner/配置登録表の作成、全対応IDと未移行0の照合、C01〜C27とtsc・実CIの実行は実装/検証工程。ADR改訂の正式承認確認後にCIカードを発行し、UI先行・CI最後を維持する。実行結果を設計段階に創作しない。
