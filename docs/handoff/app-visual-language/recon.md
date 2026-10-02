# アプリ視覚デザイン言語 — 現状調査（recon）

> この文書は何か（専門用語なしの1行）: アプリの画面部品（金型）の見た目とスマホ対応が、今どうなっているかを数えて記録したもの。

親: [design-system/visual-language/README.md](../../specs/design-system/visual-language/README.md)

調査日: 2026-10-02 / 基準コミット: 946e6dbcdffa7e314b119cb9cd67b400182a679a / 調査者: Sonnet（読み取りのみ）

### R1 ADR検索

```bash
git grep -il -e "design token" -e "デザイントークン" -e responsive -e "レスポンシブ" -e mobile -e "スマホ" -e breakpoint -e typography -e "金型" docs/adr/ | sort
```

```
docs/adr/ADR-021-order-management.md
docs/adr/ADR-046-lp-redesign.md
docs/adr/ADR-049-lp-section-completion.md
docs/adr/ADR-054-lp-hubspot-style-restructure.md
docs/adr/ADR-057-lp-premium-restyle.md
docs/adr/ADR-067-design-token-enforcement.md
docs/adr/ADR-073-design-system-kgi-rubric.md
docs/adr/ADR-074-worktree-agent-enforcement.md
docs/adr/ADR-095-sa-ssot-two-backbone-architecture.md
docs/adr/ADR-101-sa-quotation-invoice-generation.md
docs/adr/ADR-108-inbox-karte-panel-redesign.md
docs/adr/ADR-109-leads-status-ssot-immutable-codes.md
docs/adr/ADR-139-funnel-kgi-dashboard-frontend.md
docs/adr/ADR-140-mobile-nav-bottom-tabs.md
docs/adr/ADR-144-ui-component-governance.md
docs/adr/ADR-159-staff-identity-on-discord.md
docs/adr/README.md
```

件数: 17（コマンド出力の行数: wc -l）

```bash
grep -n -i -e design -e mobile -e "金型" -e UI docs/adr/FEATURE-INDEX.md
```

```
35:| i18n / 国際化 / ja.json / en.json | **ADR-027** | 全 UI 文字列 `t()` 経由・キー同期必須 |
```

件数: 1（コマンド出力の行数: wc -l）

```bash
ls docs/adr | grep -E '^ADR-1(3[7-9]|4[0-9]|5[0-9]|60)'
```

```
ADR-137-fedex-etd-paperless-trade.md
ADR-137-nginx-config-deploy-reliability.md
ADR-137-v-company-stats-ssot-filter.md
ADR-138-funnel-dashboard-stage1.md
ADR-138-remove-password-hash.md
ADR-139-funnel-kgi-dashboard-frontend.md
ADR-140-mobile-nav-bottom-tabs.md
ADR-141-inbound-translation-entry.md
ADR-142-tenant-provisioning-completeness.md
ADR-143-inventory-public-v2-canonical.md
ADR-143-send-guard.md
ADR-144-ui-component-governance.md
ADR-145-public-products-force-rls.md
ADR-147-common-6roles-standardization.md
ADR-148-fx-rate-ssot.md
ADR-149-submenu-ssot-link-mode.md
ADR-150-agent-domain-windows.md
ADR-151-jst-date-basis.md
ADR-152-frontend-api-path-no-prefix.md
ADR-153-data-durability.md
ADR-154-tcg-parity02-gas-python-migration.md
ADR-155-product-master-ssot-csv-app.md
ADR-156-product-classification-tree-and-master-separation.md
ADR-157-buyback-price-logger.md
ADR-158-product-level-supersession.md
ADR-159-staff-identity-on-discord.md
```

件数: 26（コマンド出力の行数: wc -l）

### R2 specs境界

```bash
cat -n docs/specs/design-system/README.md | sed -n '1,30p'
```

```
     1	# UI/UXデザインシステム（design-system）— 表紙
     2	
     3	> この文書は何か（専門用語なしの1行）:
     4	> 画面の色や部品の設計図を1ヵ所に集め、1ヵ所直せば全ページが変わる仕組みの正本一式の入口。
     5	
     6	配置: docs/specs/design-system/README.md
     7	日付: 2026-07-04
     8	PO: しんご
     9	状態: あるべき姿・KGI・理想設計 PO承認済（2026-07-04）
    10	
    11	## 境界
    12	- 対象: フロントエンドUI全般（トークン・共通部品・ページの参照構造・カタログ・関所）
    13	- 対象外: 見た目の質（配色・デザインの良し悪し）の判断は部品デザイン確定時に別途行う
    14	
    15	## 子文書一覧（親→子リンク）
    16	- [ideal-state.md](ideal-state.md) — あるべき姿（PO自筆・正本。書き換え禁止）
    17	- [kgi.md](kgi.md) — KGI 6項目（承認済）
    18	- [design.md](design.md) — 理想の設計図（承認済）
    19	- [../component-standard.md](../component-standard.md) — 画面部品の確定値（既存・本テーマの子）
    20	- [../../handoff/design-system-recon/recon.md](../../handoff/design-system-recon/recon.md) — 現状実測(recon)
    21	- [migration.md](migration.md) — 移行計画（既存→理想・便0〜6・部品台帳）
    22	- [track-record.md](track-record.md) — 便履歴と逸脱ログ
    23	
    24	## 後続予定（未作成・在るだけ詐称をしないための明記）
    25	- 関所実装（design.md 維持の仕組み欄参照）
    26	
    27	## 2026-09-10 再設計の草案
    28	
    29	既存の承認済み設計に対して、[追加実測](../../handoff/design-system-recon/recon.md#2026-09-10-追加調査と訂正) と [統一定義の全体案](design.md#2026-09-10-統一定義全体設計案未承認) を追補。草案は未承認・自己審査REVISE・製品実装未着手。
    30	
```

件数: 30（コマンド出力の行数: wc -l）

```bash
grep -n "見た目" docs/specs/design-system/*.md
```

```
docs/specs/design-system/design.md:220:1. 同じ用途・状態・画面幅で見た目を決める定義元が各1か所。
docs/specs/design-system/design.md:231:- pagesに生button395箇所。ただし292は静的btn-*クラスを含む。見た目を共有する経路とReact部品を共有する経路を区別して移行できる。
docs/specs/design-system/design.md:246:| 各部品の見た目と状態 | 既存componentsの該当TSX/CSS | 業務部品・ページ |
docs/specs/design-system/design.md:286:1. 共通部品の見た目は部品自身で決める。任意style/classNameから内部の外観を変更する入口を、互換移行後に閉じる。
docs/specs/design-system/design.md:287:2. 外側の配置・伸縮はPageLayout/ContentToolbar等のコンテナで扱う。見た目の変更と外側の配置を混同しない。
docs/specs/design-system/design.md:316:| 4 表・カード・タブ等 | 部品ごと、1ページ1部品 | 列固定・行選択・ページ送り等の互換確認 | データ・機能が同一、見た目が基準一致 |
docs/specs/design-system/design.md:321:見た目の検証条件案: light/dark × 390/767/768/1279/1280px。幅の境界は既存仕様、390pxは狭幅代表の提案。
docs/specs/design-system/design.md:535:#0f172aは現行darkのbg-primary、#7baee0は現行darkのlinkと同じ素材値。ボタンを「リンクの意味」に依存させないため、新しい素材名をindex.css内に各1か所置き、既存の用途名とボタン用途名がその素材を参照する。命名案: palette-ink-deep / palette-blue-soft。既存のlinkやbg-primaryの見た目はこのalias化で変えない。値をもう一つ手書きする案ではない。部品のCSSにhex値を置かない。
docs/specs/design-system/design.md:677:背景bg-surface、見出し背景bg-subtle、罫線border、本文text-primary、補助と見出しtext-secondary。指定色と実表示の通常文字4.5以上を受入条件とし、現行text-mutedを無条件に正解にしない。値は色/非色token、見た目の組合せはTable共通CSSの一か所で管理する。
docs/specs/design-system/design.md:824:配置用の幅・最小高さ・余白・flexは元のDOM上で維持し、同値の名前付き配置tokenに移す。公開口は意味のある配置classの登録に限定し、登録CSSに色・枠・文字の宣言を禁止する。表の列幅は列の所有元へ接続し、入力ごとに列幅の写しを持たない。既存field-h-md/field-w-sm/mdの適用先が外側divかnativeかを変えない。定義のない旧classの見た目を名称から創作しない。
docs/specs/design-system/design.md:838:#### Overlay：共通の見た目と異なる開閉動作
docs/specs/design-system/design.md:874:Badgeはspanのままtitle/aria/data/events/refを透過。表示文字や業務ステータスを共通部品へ埋め込まない。同値移管の見た目は現在のbadgeVariantと実CSSの対応を使い、既存statusPresentationへ表示用写像を追加する。prospectRankの仮Cはbucket=neutralでも現行pendingがwarning色のため、warning表示を保持する。論理bucket/API/ラベルを変更しない。appearanceにplain（枠/背景なしの数値・注釈）とcount（未読数）を追加する案。未読数の絶対配置は利用先の配置責任、桁数増加を切り捨てない。role.color等のデータ色は専用adapterが既存の背景式とvar(--on-accent)の前景をdataBackground/dataForegroundへ渡し、Badge素材を利用する。前景の自動算出や値補正を新設しない。通常UIの固定色をdataColorに流して免除しない。
docs/specs/design-system/design.md:938:本物のTabsとページ移動/絞込みの外観共有はTabControl（Tabs.tsx）を内部の共通button表示ownerにする。role/ariaは用途側で既存に合わせて渡し、見た目が似ているだけでrole=tabを追加しない。既存Button variant=tabの互換APIは維持するが、新しい用途をこのARIA既定へ強制しない。
docs/specs/design-system/design.md:988:- calendar21用途、未使用token削除、影のcolor-mix化、リンク/背景/文字の配色変更、useEffect修正、Iconの汎用style/ref/API再編、CI変更は別便。新しい見た目の判断を混載しない。
docs/specs/design-system/design.md:1042:目的: 親から通知関数onSyncStatusChangeが差し替えられた場合に、checkStatusが古い通知関数を使い続けないようにする。見た目やIcon契約の変更とは別PRとする。
docs/specs/design-system/design.md:1129:代替: raw352の外観同時変更は操作/画面検証を混載し大き過ぎるため後続へ分離。旧classの上に新色を重ねる案はページの上書きが残るため採らない。Buttonのみの独立classと全70のAPI移管を同便にする。リスクは見た目の意図的変化、長文/狭幅/focus外周の欠け。実部品見本・対象操作・raw同値比較で検証し、PO目視は完成後。心理学的効果数値は未測定。外部事例は不要（既存契約と実部品の測定が根拠）。Context7ツール0を今回確認、既読React18/公式W3C資料の契約と現物を継承、新ライブラリなし。
docs/specs/design-system/design.md:1178:変更前後: 旧btn-smの独自色等と通常ボタン旧寸法から、AGの共通variant/sizeへ意図して揃える。見た目を前後同値とは呼ばない。原色/寸法の変更元を増やさずButton.cssを参照するだけなので、新色トークンは不要。ロール割当ボタンは1JSXが5ロールへ繰返され、16は画面上の実DOM個数ではなくソース利用数。
docs/specs/design-system/design.md:1569:保存中の連投防止が無い点は観測事実であり、この見た目移管便では仕様変更しない。合成APIのpending2回送信で前後の送信回数が同じことを確認し、本番で連投試験はしない。新たなロック追加が必要なら別の目的・設計・承認で扱う。
docs/specs/design-system/design.md:1643:LeadFormFields.tsx:44〜56のhelperはstatus!=lostで追加キー0、lostならclose_reason_memo（空null/原値）とclose_reasons（選択なし[]、選択あり[{reason_id:Number(id),is_primary:true}]）を追加。LeadsPage.tsx:100〜110とLeadEditPage.tsx:84〜105は既存失注理由を入力へ復元せず空で初期化する。これは変更前の観測であり、保存によるDB上の実際の消去を今回実測したとはしない。今回の見た目変更で修正せず、空の再送信を含む前後のpayload一致を検査する。必要なら別テーマで検討する。
docs/specs/design-system/design.md:1669:Button.tsx:38/49〜87はnative属性を転送でき、対象6件に特殊属性はない。6件移管を逆変換で隔離し、3種類のpayloadとlost分岐を実ページで照合できるため、見た目の集約と業務挙動の維持を個別に判定できる。AOの成功件数をAP成功へ転用しない。外部導入事例・新ライブラリ調査は不要（既存社内部品への機械的移管）。ADR-113/067/027/073/122を継承、リード状態はADR-109、統合はADR-119の境界に従う。新ADR不要、将来のWhyには本監査と上記代替比較を利用できる。
docs/specs/design-system/design.md:1729:既存Buttonのnative属性契約をそのまま使い、業務本文の逆変換差分0と実ページの5キーpayloadを独立検証するため、見た目の正本集約と業務維持を切り分けられる。新ライブラリ/外部導入事例は不要（既存金型への限定移管で、外部事例で成功を保証しない）。関連ADR-113/067/027/073/122、親README/recon/migrationを継承。新ADR不要。
docs/specs/design-system/migration.md:12:2. 同値置換: 色の集約は値を変えず名前に置き換えるだけ。見た目の質の変更は移行完了後の別テーマ。移行とデザイン変更を混ぜない。
docs/specs/design-system/migration.md:23:| 便1b | 色の同値置換②: RolesPage.tsx 13＋schedule-owner 1＋Dashboard 1＝15件 | 便0.5 | 該当生hex 0・見た目一致 |
docs/specs/design-system/README.md:13:- 対象外: 見た目の質（配色・デザインの良し悪し）の判断は部品デザイン確定時に別途行う
```

件数: 24（コマンド出力の行数: wc -l）

### R3 トークン定義

```bash
grep -nE '^\s*--(font|space|radius|breakpoint|line-height|leading|tracking|letter|role|shadow|duration|transition)' frontend/src/tokens.css frontend/src/index.css
```

出力行数: 98

<details><summary>全文（98行）</summary>

```
frontend/src/tokens.css:13:  --font-2xs:           0.7rem;     /* 11.2px — 極小ラベル */
frontend/src/tokens.css:14:  --font-xs:            0.75rem;    /* 12px   — バッジ・フッタ */
frontend/src/tokens.css:15:  --font-sm:            0.85rem;    /* 13.6px — サブテキスト（0.82〜0.88rem を吸収） */
frontend/src/tokens.css:16:  --font-base:          0.9rem;     /* 14.4px — 本文・入力（0.9〜0.95rem を吸収） */
frontend/src/tokens.css:17:  --font-md:            1rem;       /* 16px   — 標準テキスト */
frontend/src/tokens.css:18:  --font-lg:            1.1rem;     /* 17.6px — セクション見出し（1.1〜1.2rem を吸収） */
frontend/src/tokens.css:19:  --font-xl:            1.25rem;    /* 20px   — ページ見出し（1.25〜1.3rem を吸収） */
frontend/src/tokens.css:20:  --font-2xl:           1.5rem;     /* 24px   — KPI値・大見出し */
frontend/src/tokens.css:21:  --font-3xl:           2rem;      /* 32px   — バッジアイコン等の特大表示 */
frontend/src/tokens.css:24:  --font-sidebar-brand: 1.6rem;    /* サイドバーブランドロゴ文字 */
frontend/src/tokens.css:25:  --font-display:       1.6rem;    /* ダッシュボード大数値 */
frontend/src/tokens.css:28:  --font-weight-normal: 400;
frontend/src/tokens.css:29:  --font-weight-medium: 500;
frontend/src/tokens.css:30:  --font-weight-semi:   600;
frontend/src/tokens.css:31:  --font-weight-bold:   700;
frontend/src/tokens.css:34:  --line-height-tight:  1.25;
frontend/src/tokens.css:35:  --line-height-base:   1.5;
frontend/src/tokens.css:42:  --role-page-title-size:   var(--font-2xl);
frontend/src/tokens.css:43:  --role-page-title-weight: var(--font-weight-semi);
frontend/src/tokens.css:44:  --role-page-title-color:  var(--text-primary);
frontend/src/tokens.css:45:  --role-page-title-lh:     var(--line-height-tight);
frontend/src/tokens.css:48:  --role-section-title-size:   var(--font-lg);
frontend/src/tokens.css:49:  --role-section-title-weight: var(--font-weight-semi);
frontend/src/tokens.css:50:  --role-section-title-color:  var(--text-primary);
frontend/src/tokens.css:53:  --role-card-title-size:   var(--font-md);
frontend/src/tokens.css:54:  --role-card-title-weight: var(--font-weight-semi);
frontend/src/tokens.css:55:  --role-card-title-color:  var(--text-primary);
frontend/src/tokens.css:58:  --role-body-size:   var(--font-base);
frontend/src/tokens.css:59:  --role-body-weight: var(--font-weight-normal);
frontend/src/tokens.css:60:  --role-body-color:  var(--text-secondary);
frontend/src/tokens.css:63:  --role-caption-size:   var(--font-xs);
frontend/src/tokens.css:64:  --role-caption-weight: var(--font-weight-normal);
frontend/src/tokens.css:65:  --role-caption-color:  var(--text-muted);
frontend/src/tokens.css:68:  --space-1:  4px;
frontend/src/tokens.css:69:  --space-2:  8px;
frontend/src/tokens.css:70:  --space-3:  12px;
frontend/src/tokens.css:71:  --space-4:  16px;
frontend/src/tokens.css:72:  --space-5:  20px;
frontend/src/tokens.css:73:  --space-6:  24px;
frontend/src/tokens.css:74:  --space-8:  32px;
frontend/src/tokens.css:75:  --space-9:  36px;   /* アイコンボタン・中型クリックターゲット（.modal-icon-btn 等） */
frontend/src/tokens.css:76:  --space-10: 40px;
frontend/src/tokens.css:77:  --space-12: 48px;
frontend/src/tokens.css:80:  --space-1px:  1px;   /* 未読バッジ縦余白（Meta実測値） */
frontend/src/tokens.css:81:  --space-2px:  2px;   /* バッジ縦余白・極小調整 */
frontend/src/tokens.css:82:  --space-3px:  3px;   /* ランクバッジ縦余白 */
frontend/src/tokens.css:83:  --space-6px:  6px;   /* コンパクトギャップ・小ボタン余白 */
frontend/src/tokens.css:84:  --space-10px: 10px;  /* 中間パディング（セクション・フォーム） */
frontend/src/tokens.css:85:  --space-14px: 14px;  /* ボタン横余白 */
frontend/src/tokens.css:88:  --radius-2xs:  3px;   /* btn-sm・コードラベルの極小角丸 */
frontend/src/tokens.css:89:  --radius-xs:   2px;   /* アバター・小アイコン・サムネイルの極小角丸 */
frontend/src/tokens.css:90:  --radius-sm:   4px;
frontend/src/tokens.css:91:  --radius-md:   6px;
frontend/src/tokens.css:92:  --radius-lg:   8px;
frontend/src/tokens.css:93:  --radius-xl:   12px;
frontend/src/tokens.css:94:  --radius-badge: 10px;  /* バッジ・status-badge・dedup-summary */
frontend/src/tokens.css:95:  --radius-pill: 20px;   /* ピル型ボタン・バッジ・入力欄の角丸（意味的例外トークン） */
frontend/src/tokens.css:96:  --radius-full: 9999px;
frontend/src/tokens.css:97:  --radius-bubble-out: 20.8px;                      /* Messenger outbound バブル（Meta実測値） */
frontend/src/tokens.css:98:  --radius-bubble-in:  20.8px 20.8px 20.8px 4.8px; /* Messenger inbound バブル（テール付き） */
frontend/src/tokens.css:113:  --breakpoint-mobile-max:   767px;  /* モバイル上限     スマートフォン    */
frontend/src/tokens.css:114:  --breakpoint-tablet-min:   768px;  /* タブレット下限   iPad縦向き以上    */
frontend/src/tokens.css:115:  --breakpoint-tablet-max:  1279px;  /* タブレット上限   デスクトップ境界-1 */
frontend/src/tokens.css:116:  --breakpoint-desktop-min: 1280px;  /* デスクトップ下限 MBP 13in以上      */
frontend/src/tokens.css:117:  --breakpoint-xl-min:      1440px;  /* ワイド下限       FHD大画面（将来用）*/
frontend/src/tokens.css:133:  --duration-base:      200ms;                               /* animation で easing を別指定する場合の duration 単体 */
frontend/src/tokens.css:134:  --duration-spinner:   800ms;                               /* Spinner 回転 */
frontend/src/tokens.css:135:  --duration-shimmer:  1500ms;                               /* Skeleton shimmer */
frontend/src/tokens.css:136:  --duration-striped:    700ms;                               /* Progress striped */
frontend/src/tokens.css:137:  --duration-bounce:    1300ms;                              /* Splash dots bounce */
frontend/src/tokens.css:138:  --duration-blink:     1300ms;                              /* Splash logo blink */
frontend/src/tokens.css:139:  --duration-toast-in:    350ms;                              /* Toast enter */
frontend/src/tokens.css:140:  --duration-toast-out:   300ms;                              /* Toast exit */
frontend/src/tokens.css:141:  --duration-fade-up:     400ms;                              /* Empty state fade-up */
frontend/src/tokens.css:142:  --transition-micro:   100ms ease;                          /* ボタン押下・スウォッチ */
frontend/src/tokens.css:143:  --transition-fast:    150ms ease;                          /* hover・カラー変化 */
frontend/src/tokens.css:144:  --transition-base:    200ms ease;                          /* フェードイン・スケール */
frontend/src/tokens.css:145:  --transition-highlight: 600ms ease;                        /* 行ハイライト */
frontend/src/tokens.css:146:  --transition-sidebar: 250ms ease;                          /* サイドバー幅アニメーション */
frontend/src/tokens.css:147:  --transition-slow:    280ms cubic-bezier(0.4, 0, 0.2, 1); /* ドロワー・モーダル展開 */
frontend/src/index.css:68:  --shadow-xs:    0 1px 2px rgba(0, 0, 0, 0.05);
frontend/src/index.css:69:  --shadow-sm:    0 1px 3px rgba(0, 0, 0, 0.08);
frontend/src/index.css:70:  --shadow-md:    0 4px 12px rgba(0, 0, 0, 0.08);
frontend/src/index.css:71:  --shadow-lg:    0 10px 15px rgba(0, 0, 0, 0.08), 0 4px 6px rgba(0, 0, 0, 0.05);
frontend/src/index.css:72:  --shadow-xl:    0 20px 25px rgba(0, 0, 0, 0.08), 0 8px 10px rgba(0, 0, 0, 0.04);
frontend/src/index.css:73:  --shadow-modal:        0 8px 32px rgba(0, 0, 0, 0.2);  /* モーダル専用（意図的に重め） */
frontend/src/index.css:74:  --shadow-dropdown:     0 2px 12px rgba(0, 0, 0, 0.15); /* ドロップダウン・ポップオーバー */
frontend/src/index.css:75:  --shadow-drop-sm:      0 2px 4px rgba(0, 0, 0, 0.2);   /* color-swatch 選択時 */
frontend/src/index.css:76:  --shadow-accent-hover: 0 2px 6px rgba(30, 58, 138, 0.15); /* permission-item hover（--accent #1e3a8a） */
frontend/src/index.css:264:  --shadow-xs:    0 1px 2px rgba(0, 0, 0, 0.3);
frontend/src/index.css:265:  --shadow-sm:    0 1px 3px rgba(0, 0, 0, 0.4);
frontend/src/index.css:266:  --shadow-md:    0 4px 12px rgba(0, 0, 0, 0.4);
frontend/src/index.css:267:  --shadow-lg:    0 10px 15px rgba(0, 0, 0, 0.4), 0 4px 6px rgba(0, 0, 0, 0.3);
frontend/src/index.css:268:  --shadow-xl:    0 20px 25px rgba(0, 0, 0, 0.5), 0 8px 10px rgba(0, 0, 0, 0.4);
frontend/src/index.css:269:  --shadow-modal:        0 8px 32px rgba(0, 0, 0, 0.5);
frontend/src/index.css:270:  --shadow-dropdown:     0 2px 12px rgba(0, 0, 0, 0.35);
frontend/src/index.css:271:  --shadow-drop-sm:      0 2px 4px rgba(0, 0, 0, 0.35);       /* dark: やや濃く */
frontend/src/index.css:272:  --shadow-accent-hover: 0 2px 6px rgba(91, 141, 217, 0.2);   /* dark: --accent #5b8dd9 */
```

</details>

件数: 98（コマンド出力の行数: wc -l）

### R4 ブレークポイント使用

```bash
grep -rnoE '@media[^{]*' frontend/src --include=*.css --exclude=*.test.* --exclude=*.stories.* --exclude-dir=node_modules
```

```
frontend/src/loading-animations.css:543:@media (prefers-reduced-motion: reduce) 
frontend/src/topbar.css:268:@media (max-width: 767px) 
frontend/src/features/tcg-import-workflow/import-workflow.css:27:@media (width <= 767px) 
frontend/src/features/tcg-analysis-review/source-raw-pane.css:99:@media (prefers-reduced-motion: reduce) 
frontend/src/tokens.css:100:@media 条件式では使用不可。
frontend/src/tokens.css:102:@media に書く値はここと一致させること。JS側は constants/breakpoints.ts を参照。
frontend/src/tokens.css:569:@media (max-width: 1279px) 
frontend/src/pages-layout.css:114:@media (max-width: 767px) 
frontend/src/pages-layout.css:307:@media (max-width: 767px) 
frontend/src/components/Drawer.css:104:@media (max-width: 767px) 
frontend/src/components/FormField.css:13:@media
frontend/src/components/FormField.css:191:@media (max-width: 767px) 
frontend/src/components/Card.css:34:@media (max-width: 767px) 
frontend/src/components/Modal.css:97:@media (max-width: 767px) 
frontend/src/components/Button.css:154:@media (max-width: 767px) 
frontend/src/responsive.css:18:@media (max-width: 767px) 
frontend/src/hub-shell.css:89:@media (max-width: 767px) 
frontend/src/pages/inbox/InboxPage.css:1039:@media (max-width: 1279px) 
frontend/src/pages/inbox/InboxPage.css:1151:@media (max-width: 767px) 
frontend/src/pages/inbox/InboxPage.css:1490:@media (max-width: 560px) 
frontend/src/pages/inbox/InboxPage.css:1785:@media (hover: hover) 
frontend/src/pages/goal-setting/GoalSettingPage.css:66:@media (max-width: 920px) 
frontend/src/pages/goal-setting/GoalSettingPage.css:113:@media (max-width: 720px) 
frontend/src/pages/goal-setting/GoalSettingPage.css:205:@media (max-width: 720px) 
frontend/src/pages/goal-setting/GoalSettingPage.css:242:@media (max-width: 920px) 
frontend/src/pages/goal-setting/GoalSettingPage.css:304:@media (min-width: 921px) 
frontend/src/pages/goal-setting/GoalSettingPage.css:407:@media (max-width: 720px) 
frontend/src/pages/goal-setting/GoalSettingPage.css:443:@media (max-width: 720px) 
frontend/src/pages/dashboard/FunnelRevenuePage.css:26:@media (max-width: 640px) 
frontend/src/pages/dashboard/DashboardPage.css:66:@media (max-width: 960px) 
frontend/src/pages/dashboard/FunnelSection.css:35:@media (max-width: 900px) 
frontend/src/pages/dashboard/FunnelSection.css:41:@media (max-width: 540px) 
frontend/src/pages/dashboard/FunnelSection.css:55:@media (max-width: 720px) 
frontend/src/pages/integrations/FedexLabelValidationTab.css:332:@media (max-width: 768px) 
frontend/src/pages/super-admin/components/ShadowAccuracyPanel.css:105:@media (max-width: 1023px) 
frontend/src/pages/super-admin/ParseReviewPage.css:79:@media (max-width: 1023px) 
frontend/src/pages/schedule.css:1309:@media (max-width: 1023px) 
frontend/src/pages/schedule.css:1329:@media (max-width: 767px) 
frontend/src/pages/design-preview/DesignPreviewPage.css:111:@media (max-width: 767px) 
frontend/src/pages/design-preview/DesignPreviewPage.css:150:@media (max-width: 767px) 
frontend/src/pages/design-preview/DesignPreviewPage.css:163:@media (max-width: 767px) 
frontend/src/pages/design-preview/DesignPreviewPage.css:281:@media (max-width: 767px) 
frontend/src/company-forms.css:194:@media (max-width: 768px) 
frontend/src/company-forms.css:206:@media (max-width: 480px) 
```

件数: 44（コマンド出力の行数: wc -l）

```bash
grep -rhoE '@media[^{]*' frontend/src --include=*.css --exclude=*.test.* --exclude=*.stories.* --exclude-dir=node_modules | sort | uniq -c | sort -rn
```

```
  16 @media (max-width: 767px) 
   5 @media (max-width: 720px) 
   3 @media (max-width: 1023px) 
   2 @media (prefers-reduced-motion: reduce) 
   2 @media (max-width: 920px) 
   2 @media (max-width: 768px) 
   2 @media (max-width: 1279px) 
   1 @media 条件式では使用不可。
   1 @media に書く値はここと一致させること。JS側は constants/breakpoints.ts を参照。
   1 @media (width <= 767px) 
   1 @media (min-width: 921px) 
   1 @media (max-width: 960px) 
   1 @media (max-width: 900px) 
   1 @media (max-width: 640px) 
   1 @media (max-width: 560px) 
   1 @media (max-width: 540px) 
   1 @media (max-width: 480px) 
   1 @media (hover: hover) 
   1 @media
```

件数: 19（コマンド出力の行数: wc -l）

### R5 トークン外のタイポグラフィ値

```bash
grep -rnE 'line-height:\s*[0-9.]' frontend/src --include=*.css --exclude=*.test.* --exclude=*.stories.* --exclude-dir=node_modules
```

```
frontend/src/topbar.css:129:  line-height: 1;
frontend/src/topbar.css:196:  line-height: 1;
frontend/src/features/tcg-distribution/distribution.css:278:  line-height: 1.5;
frontend/src/features/tcg-analysis-review/supplier-detail-view.css:235:  line-height: 1;
frontend/src/index.css:433:  line-height: 1.6;
frontend/src/mobile-shell.css:166:  line-height: 1;
frontend/src/mobile-shell.css:263:  line-height: 1;
frontend/src/pages-layout.css:48:  line-height: 1.4;
frontend/src/pages-layout.css:644:  line-height: 1.3;
frontend/src/pages-layout.css:725:  line-height: 1.5;
frontend/src/components/FormField.css:42:  line-height: 1;
frontend/src/components/EmptyState.css:34:  line-height: 1;
frontend/src/components/IconToggleButton.css:21:  line-height: 1;
frontend/src/components/Badge.css:20:  line-height: 1;
frontend/src/sidebar.css:148:  line-height: 1.4;
frontend/src/sidebar.css:297:  line-height: 1;
frontend/src/pages/inbox/InboxPage.css:336:  line-height: 0;
frontend/src/pages/inbox/InboxPage.css:541:  line-height: 1.45;
frontend/src/pages/inbox/InboxPage.css:602:  line-height: 1.4;
frontend/src/pages/inbox/InboxPage.css:670:  line-height: 1.4;
frontend/src/pages/inbox/InboxPage.css:973:  line-height: 1.5;
frontend/src/pages/inbox/InboxPage.css:1295:  line-height: 1;
frontend/src/pages/inbox/InboxPage.css:1344:  line-height: 1.3;
frontend/src/pages/inbox/InboxPage.css:1544:  padding: var(--space-3); white-space: pre-wrap; line-height: 1.5;
frontend/src/pages/inbox/InboxPage.css:1566:  line-height: 1.5; font-family: inherit;
frontend/src/pages/inbox/InboxPage.css:1813:  line-height: 1;
frontend/src/pages/goal-setting/GoalSettingPage.css:96:  line-height: 1.7;
frontend/src/pages/goal-setting/GoalSettingPage.css:166:  line-height: 1.6;
frontend/src/pages/goal-setting/GoalSettingPage.css:232:  line-height: 1.6;
frontend/src/pages/goal-setting/GoalSettingPage.css:390:  line-height: 1.7;
frontend/src/pages/goal-setting/GoalSettingPage.css:398:  line-height: 1.7;
frontend/src/pages/dashboard/FunnelReasonsPage.css:161:  line-height: 1.6;
frontend/src/pages/dashboard/DashboardPage.css:474:  line-height: 1.6;
frontend/src/pages/dashboard/FunnelSection.css:125:  line-height: 1.1;
frontend/src/pages/dashboard/FunnelSection.css:202:  line-height: 1.1;
frontend/src/pages/integrations/FedexLabelValidationTab.css:151:  line-height: 1.3;
frontend/src/pages/super-admin/components/PipelineMapPanel.css:96:  line-height: 1.4;
frontend/src/pages/super-admin/components/PipelineMapPanel.css:103:  line-height: 1.5;
frontend/src/pages/super-admin/components/PipelineMapPanel.css:158:  line-height: 1.4;
frontend/src/pages/schedule.css:39:  line-height: 1.2;
frontend/src/pages/schedule.css:134:  line-height: 1.4;
frontend/src/pages/schedule.css:418:  line-height: 1;
frontend/src/pages/schedule.css:559:  line-height: 1.25;
frontend/src/pages/schedule.css:906:  line-height: 1.15;
frontend/src/pages/design-preview/DesignPreviewPage.css:140:  line-height: 1.6;
```

件数: 45（コマンド出力の行数: wc -l）

```bash
grep -rnE 'letter-spacing:\s*-?[0-9.]' frontend/src --include=*.css --exclude=*.test.* --exclude=*.stories.* --exclude-dir=node_modules
```

```
frontend/src/mobile-shell.css:283:  letter-spacing: 0.05em;
frontend/src/pages-layout.css:764:  letter-spacing: 0.04em;
frontend/src/components/SubMenu.css:42:  letter-spacing: 0.06em;
frontend/src/sidebar.css:93:  letter-spacing: 0.05em;
frontend/src/sidebar.css:254:  letter-spacing: 4px;
frontend/src/hub-shell.css:39:  letter-spacing: 0.06em;
frontend/src/components.css:113:  letter-spacing: 0.05em;
frontend/src/pages/inbox/InboxPage.css:859:  letter-spacing: 0.02em;
frontend/src/pages/inbox/InboxPage.css:989:  letter-spacing: 0.02em;
frontend/src/pages/inbox/InboxPage.css:1432:  text-transform: uppercase; letter-spacing: 0.05em;
frontend/src/pages/goal-setting/GoalSettingPage.css:49:  letter-spacing: 0.04em;
frontend/src/pages/goal-setting/GoalSettingPage.css:89:  letter-spacing: -0.01em;
frontend/src/pages/goal-setting/GoalSettingPage.css:217:  letter-spacing: 0.06em;
frontend/src/pages/goal-setting/GoalSettingPage.css:482:  letter-spacing: 0.05em;
frontend/src/pages/dashboard/FunnelRevenuePage.css:44:  letter-spacing: 0.04em;
frontend/src/pages/dashboard/PriorityProspectsSection.css:26:  letter-spacing: 0.04em;
frontend/src/pages/dashboard/FunnelReasonsPage.css:65:  letter-spacing: 0.04em;
frontend/src/pages/dashboard/DashboardPage.css:145:  letter-spacing: 0.05em;
frontend/src/pages/dashboard/DashboardPage.css:449:  letter-spacing: 0.05em;
frontend/src/pages/dashboard/WeeklyAdvisorSection.css:24:  letter-spacing: 0.04em;
frontend/src/pages/dashboard/FunnelSection.css:98:  letter-spacing: 0.04em;
frontend/src/pages/integrations/FedexLabelValidationTab.css:54:  letter-spacing: 0.08em;
frontend/src/pages/integrations/FedexLabelValidationTab.css:261:  letter-spacing: 0.06em;
frontend/src/pages/integrations/FedexLabelValidationTab.css:561:  letter-spacing: 0.05em;
frontend/src/pages/design-system/DesignSystemPage.css:75:  letter-spacing: 0.05em;
frontend/src/pages/schedule.css:715:  letter-spacing: 0.08em;
frontend/src/pages/schedule.css:780:  letter-spacing: 0.05em;
frontend/src/pages/schedule.css:898:  letter-spacing: 0.08em;
frontend/src/pages/schedule.css:1064:  letter-spacing: 0.08em;
frontend/src/pages/schedule.css:1283:  letter-spacing: 0.08em;
frontend/src/pages/design-preview/DesignPreviewPage.css:184:  letter-spacing: 0.05em;
```

件数: 31（コマンド出力の行数: wc -l）

```bash
grep -rnE 'font-weight:\s*[0-9]' frontend/src --include=*.css --exclude=*.test.* --exclude=*.stories.* --exclude-dir=node_modules
```

```
frontend/src/features/tcg-distribution/distribution.css:26:  font-weight: 700;
frontend/src/features/tcg-distribution/distribution.css:32:  font-weight: 400;
frontend/src/features/tcg-distribution/distribution.css:68:  font-weight: 600;
frontend/src/features/tcg-distribution/distribution.css:117:  font-weight: 600;
frontend/src/features/tcg-distribution/distribution.css:224:  font-weight: 600;
frontend/src/features/tcg-distribution/distribution.css:271:  font-weight: 600;
frontend/src/features/tcg-distribution/distribution.css:308:  font-weight: 600;
frontend/src/features/tcg-distribution/distribution.css:398:  font-weight: 600;
frontend/src/features/tcg-distribution/distribution.css:427:  font-weight: 600;
frontend/src/features/tcg-import-workflow/import-workflow.css:7:.pmg-workflow__metric { font-size: var(--font-3xl); font-weight: 700; margin: var(--space-2) 0; }
frontend/src/features/tcg-import-workflow/import-workflow.css:8:.pmg-workflow__metric span { font-size: var(--font-sm); font-weight: 400; color: var(--text-secondary); }
frontend/src/features/tcg-import-workflow/import-workflow.css:12:.pmg-workflow .pmg-workflow__summary-badge.comp-badge { font-size: var(--font-xl); font-weight: 700; }
frontend/src/features/tcg-import-workflow/import-workflow.css:13:.pmg-workflow .pmg-workflow__review-badge.comp-badge { font-size: var(--font-lg); font-weight: 700; }
frontend/src/features/tcg-import-workflow/import-workflow.css:15:.pmg-workflow__details summary { cursor: pointer; font-weight: 600; }
frontend/src/features/tcg-import-workflow/import-workflow.css:21:.pmg-workflow__table th { white-space: nowrap; color: var(--text-secondary); font-weight: 600; }
frontend/src/features/tcg-analysis-review/supplier-detail-view.css:169:  font-weight: 500;
frontend/src/features/tcg-analysis-review/supplier-detail-view.css:220:  font-weight: 600;
frontend/src/features/tcg-analysis-review/supplier-detail-view.css:240:  font-weight: 600;
frontend/src/features/tcg-analysis-review/supplier-detail-view.css:272:  font-weight: 600;
frontend/src/features/tcg-analysis-review/supplier-detail-view.css:349:  font-weight: 500;
frontend/src/features/tcg-analysis-review/source-raw-pane.css:88:  font-weight: 500;
frontend/src/features/tcg-analysis-review/components/data-list.css:19:  font-weight: 600;
frontend/src/features/tcg-analysis-review/components/status-badge.css:12:  font-weight: 600;
frontend/src/pages/inbox/InboxPage.css:45:  font-weight: 400;
frontend/src/pages/inbox/InboxPage.css:64:  font-weight: 700;
frontend/src/pages/inbox/InboxPage.css:149:  font-weight: 600;
frontend/src/pages/inbox/InboxPage.css:247:  font-weight: 400;
frontend/src/pages/inbox/InboxPage.css:260:  font-weight: 700;
frontend/src/pages/inbox/InboxPage.css:320:  font-weight: 700;
frontend/src/pages/inbox/InboxPage.css:354:  font-weight: 400;
frontend/src/pages/inbox/InboxPage.css:362:.conv-name.unread { font-weight: 700; }
frontend/src/pages/inbox/InboxPage.css:396:  font-weight: 700;
frontend/src/pages/inbox/InboxPage.css:404:  font-weight: 700;
frontend/src/pages/inbox/InboxPage.css:475:  font-weight: 700;
frontend/src/pages/inbox/InboxPage.css:814:  font-weight: 700;
frontend/src/pages/inbox/InboxPage.css:820:  font-weight: 700;
frontend/src/pages/inbox/InboxPage.css:838:  font-weight: 600;
frontend/src/pages/inbox/InboxPage.css:864:  font-weight: 500;
frontend/src/pages/inbox/InboxPage.css:878:  font-weight: 400;
frontend/src/pages/inbox/InboxPage.css:933:  font-weight: 500;
frontend/src/pages/inbox/InboxPage.css:955:  font-weight: 700;
frontend/src/pages/inbox/InboxPage.css:963:  font-weight: 700;
frontend/src/pages/inbox/InboxPage.css:986:  font-weight: 400;
frontend/src/pages/inbox/InboxPage.css:1088:    font-size: var(--font-sm); font-weight: 600; color: var(--text-primary);
frontend/src/pages/inbox/InboxPage.css:1210:  font-weight: 600; font-size: var(--font-base); text-align: left;
frontend/src/pages/inbox/InboxPage.css:1218:  font-size: var(--font-base); font-weight: 600; color: var(--text-primary);
frontend/src/pages/inbox/InboxPage.css:1234:.right-panel-tab.active { color: var(--accent); border-bottom-color: var(--accent); font-weight: 600; } /* 方向A: --accent = ブランドネイビー */
frontend/src/pages/inbox/InboxPage.css:1239:  font-weight: 500; /* 見本: 500（bold→medium） */
frontend/src/pages/inbox/InboxPage.css:1278:  font-weight: 600;
frontend/src/pages/inbox/InboxPage.css:1359:  font-weight: 600;
frontend/src/pages/inbox/InboxPage.css:1404:  font-weight: 600;
frontend/src/pages/inbox/InboxPage.css:1409:  font-weight: 400;
frontend/src/pages/inbox/InboxPage.css:1427:  font-size: var(--font-lg); font-weight: 600; color: var(--text-primary);
frontend/src/pages/inbox/InboxPage.css:1431:  font-size: var(--font-xs); font-weight: 600; color: var(--text-muted);
frontend/src/pages/inbox/InboxPage.css:1450:  font-size: var(--font-sm); font-weight: 500; cursor: pointer;
frontend/src/pages/inbox/InboxPage.css:1507:.inbox-translate-outbound-label { font-size: var(--font-xs); font-weight: 600; }
frontend/src/pages/inbox/InboxPage.css:1527:  font-size: var(--font-sm); font-weight: 600; color: var(--text);
frontend/src/pages/inbox/InboxPage.css:1538:  font-size: var(--font-xs); font-weight: 600; color: var(--text-muted);
frontend/src/pages/inbox/InboxPage.css:1548:  font-size: var(--font-xs); font-weight: 600;
frontend/src/pages/inbox/InboxPage.css:1557:  font-size: var(--font-xs); font-weight: 600; color: var(--warning-text);
frontend/src/pages/inbox/InboxPage.css:1560:.outbound-translation-flag-term { font-weight: 600; }
frontend/src/pages/inbox/InboxPage.css:1590:  font-size: var(--font-sm); font-weight: 600; cursor: pointer;
frontend/src/pages/inbox/InboxPage.css:1670:  font-weight: 500;
frontend/src/pages/inbox/InboxPage.css:1712:  font-weight: 700;
frontend/src/pages/inbox/InboxPage.css:1730:  font-weight: 600;
frontend/src/pages/schedule.css:38:  font-weight: 400;
```

件数: 66（コマンド出力の行数: wc -l）

```bash
grep -rnE 'font-size:\s*[0-9.]' frontend/src --include=*.css --exclude=*.test.* --exclude=*.stories.* --exclude-dir=node_modules | wc -l
```

```
       0
```

### R6 役割トークン採用数

```bash
grep -rE 'var\(--role-' frontend/src --include=*.css --include=*.tsx --exclude=*.test.* --exclude=*.stories.* --exclude-dir=node_modules | wc -l
```

```
      37
```

```bash
grep -rE 'font-size:\s*var\(--font-' frontend/src --include=*.css --include=*.tsx --exclude=*.test.* --exclude=*.stories.* --exclude-dir=node_modules | wc -l
```

```
     561
```

### R7 変数を使わない box-shadow

```bash
grep -rnE 'box-shadow:' frontend/src --include=*.css --exclude=*.test.* --exclude=*.stories.* --exclude-dir=node_modules | grep -v 'var(--'
```

```
frontend/src/pages-layout.css:311:    box-shadow: none;
frontend/src/components.css:190:  box-shadow: none;
frontend/src/pages/super-admin/ParseReviewPage.css:129:  box-shadow: none;
```

件数: 3（コマンド出力の行数: wc -l）

```bash
grep -rnE 'box-shadow:' frontend/src --include=*.css --exclude=*.test.* --exclude=*.stories.* --exclude-dir=node_modules | wc -l
```

```
      95
```

### R8 グラデーション

```bash
grep -rnE '(linear|radial)-gradient' frontend/src --include=*.css --include=*.tsx --exclude=*.test.* --exclude=*.stories.* --exclude-dir=node_modules
```

```
frontend/src/loading-animations.css:108:  background: linear-gradient(90deg, var(--bg-active) 0%, var(--bg-subtle) 50%, var(--bg-active) 100%);
frontend/src/loading-animations.css:142:  background-image: linear-gradient(
frontend/src/index.css:173:    radial-gradient(103.89% 81.75% at 95.41% 106.34%,
frontend/src/index.css:175:    radial-gradient(297.85% 151.83% at -21.39% 8.81%,
frontend/src/index.css:377:    radial-gradient(103.89% 81.75% at 95.41% 106.34%,
frontend/src/index.css:379:    radial-gradient(297.85% 151.83% at -21.39% 8.81%,
frontend/src/pages/goal-setting/GoalSettingPage.css:15:    radial-gradient(120% 120% at 0% 0%, var(--accent-bg-subtle) 0%, transparent 46%),
frontend/src/pages/goal-setting/GoalSettingPage.css:16:    linear-gradient(180deg, var(--bg-surface) 0%, var(--bg-subtle) 100%);
frontend/src/pages/goal-setting/GoalSettingPage.css:25:    linear-gradient(90deg, transparent 0, transparent 72%, color-mix(in srgb, var(--accent) 12%, transparent) 100%),
frontend/src/pages/goal-setting/GoalSettingPage.css:26:    linear-gradient(180deg, color-mix(in srgb, var(--accent) 6%, transparent) 0, transparent 24%);
frontend/src/pages/goal-setting/GoalSettingPage.css:300:  background: linear-gradient(180deg, var(--bg-surface) 0%, var(--bg-primary) 100%);
frontend/src/pages/dashboard/PriorityProspectsSection.css:6:  background: linear-gradient(180deg, var(--success-bg-subtle), var(--bg-surface) 58%);
frontend/src/pages/schedule.css:490:    repeating-linear-gradient(
```

件数: 13（コマンド出力の行数: wc -l）

### R9 px直書きの余白

```bash
grep -rnE '(padding|margin|gap)[a-z-]*:\s*[^;]*[0-9]+px' frontend/src --include=*.css --exclude=*.test.* --exclude=*.stories.* --exclude-dir=node_modules | grep -v 'var(--'
```

```
frontend/src/tokens.css:189:  --page-padding-y:  10px;            /* 10px — 上下余白 */
frontend/src/tokens.css:321:  --karte-hd-gap:       11px;  /* カルテヘッダー hd-top gap / hd-meta margin-top（見本） */
frontend/src/tokens.css:332:  --sidebar-item-padding-v:  11px;   /* サイドバー項目垂直パディング（実測値） */
frontend/src/tokens.css:347:  --coming-soon-margin-top:  80px;   /* 準備中ページ上余白 */
frontend/src/mobile-shell.css:68:  padding-bottom: env(safe-area-inset-bottom, 0px);
frontend/src/mobile-shell.css:127:  padding-bottom: env(safe-area-inset-bottom, 0px);
frontend/src/pages-layout.css:78:  margin-bottom: -3px;  /* lh=1.25 × 24px の half-leading(3px) を相殺してサブタイトルと 0px に */
frontend/src/pages-layout.css:232:  margin: -1px;
frontend/src/pages-layout.css:431:  margin-bottom: -1px;
frontend/src/components/Tabs.css:88:  margin-bottom: -1px;
frontend/src/pages/inbox/InboxPage.css:945:  margin: 2px 0 0;
frontend/src/pages/inbox/InboxPage.css:951:  margin-top: 6px;
frontend/src/pages/inbox/InboxPage.css:1010:  margin-bottom: 6px;
frontend/src/pages/inbox/InboxPage.css:1231:  margin-bottom: -1px;
frontend/src/pages/goal-setting/GoalSettingPage.css:344:  gap: 2px;
frontend/src/pages/goal-setting/GoalSettingPage.css:416:  gap: 2px;
frontend/src/pages/dashboard/FunnelReasonsPage.css:23:  margin-bottom: -2px;
frontend/src/pages/dashboard/DashboardPage.css:8:/* margin-left: auto（右端寄せ）を 30px で上書きし、タイトル直後に固定 */
frontend/src/pages/dashboard/DashboardPage.css:10:  margin-left: 30px;
frontend/src/pages/dashboard/WeeklyAdvisorSection.css:180:  gap: 2px;
frontend/src/pages/schedule.css:60:  padding: 2px;
frontend/src/pages/schedule.css:376:  padding-bottom: 6px;
frontend/src/pages/schedule.css:389:  gap: 2px;
frontend/src/pages/schedule.css:538:  gap: 2px;
frontend/src/pages/schedule.css:773:  gap: 2px;
frontend/src/pages/schedule.css:1016:  gap: 2px;
frontend/src/pages/schedule.css:1274:  gap: 2px;
frontend/src/company-forms.css:58:  margin-bottom: -2px;
```

件数: 28（コマンド出力の行数: wc -l）

### R10 カードの余白

```bash
find frontend/src -name '*.css' -print0 | xargs -0 grep -n -A6 -E '^\.(card|db-section-card)\b'
```

```
frontend/src/components.css:234:.card {
frontend/src/components.css-235-  background: var(--bg-surface);
frontend/src/components.css-236-  border-radius: var(--radius-lg);
frontend/src/components.css-237-  padding: var(--space-5);
frontend/src/components.css-238-  box-shadow: var(--shadow-sm);
frontend/src/components.css-239-  margin-bottom: var(--space-4);
frontend/src/components.css-240-}
--
frontend/src/components.css:242:.card h3 {
frontend/src/components.css-243-  font-size: var(--font-md);
frontend/src/components.css-244-  font-weight: var(--font-weight-semi);
frontend/src/components.css-245-  color: var(--text-primary);
frontend/src/components.css-246-  margin: 0 0 var(--space-3);
frontend/src/components.css-247-}
frontend/src/components.css-248-
frontend/src/components.css:249:.card table {
frontend/src/components.css-250-  width: 100%;
frontend/src/components.css-251-  border-collapse: collapse;
frontend/src/components.css-252-}
frontend/src/components.css-253-
frontend/src/components.css:254:.card th {
frontend/src/components.css-255-  text-align: left;
frontend/src/components.css-256-  padding: var(--space-2) 0;
frontend/src/components.css-257-  font-size: var(--font-xs);
frontend/src/components.css-258-  color: var(--text-muted);
frontend/src/components.css-259-  border-bottom: 1px solid var(--border);
frontend/src/components.css-260-}
--
frontend/src/components.css:263:.card td {
frontend/src/components.css-264-  padding: var(--space-2) 0;
frontend/src/components.css-265-  font-size: var(--font-sm);
frontend/src/components.css-266-  color: var(--text-primary);
frontend/src/components.css-267-  border-bottom: 1px solid var(--border);
frontend/src/components.css-268-}
frontend/src/components.css-269-
--
frontend/src/pages/dashboard/DashboardPage.css:74:.db-section-card {
frontend/src/pages/dashboard/DashboardPage.css-75-  background: var(--bg-surface);
frontend/src/pages/dashboard/DashboardPage.css-76-  border-radius: var(--radius-lg);
frontend/src/pages/dashboard/DashboardPage.css-77-  padding: var(--space-4);
frontend/src/pages/dashboard/DashboardPage.css-78-  box-shadow: var(--shadow-sm);
frontend/src/pages/dashboard/DashboardPage.css-79-}
frontend/src/pages/dashboard/DashboardPage.css-80-
```

件数: 43（コマンド出力の行数: wc -l）

```bash
grep -n -i -B2 -A8 'card' docs/specs/component-standard.md | head -80
```

```
5-
6-**確定日**: 2026-06-07  
7:**PR**: feature/morimoto/token-button-card-preview  
8-［転記省略: この行は存在しないファイル名をパス表記で含み、PRゲートの引用検査に掛かるため。原文は docs/specs/component-standard.md の8行目］
9-
10----
11-
12-## 採用した標準値
13-
14-| 観点 | 標準値 | トークン | 根拠 |
15-|---|---|---|---|
16-| ボタン角丸 | **6px** | `--comp-btn-radius` → `--radius-md` | btn-ghost 実値・タスク仕様と一致 |
17:| カード角丸 | **8px** | `--comp-card-radius` → `--radius-lg` | .card / db-section-card と一致 |
18:| カード余白 (PC/タブレット) | **24px** | `--comp-card-padding` → `--space-6` | 仕様値（下記「食い違い」欄参照） |
19:| カード余白 (mobile) | **16px** | `--comp-card-padding-compact` → `--space-4` | ダッシュボード実値と一致・8の倍数 |
20:| カード間ギャップ | **24px** | `--comp-card-gap` → `--space-6` | 仕様値（下記「食い違い」欄参照） |
21-| 画面幅バンド (mobile) | **〜767px** | `--breakpoint-mobile-max` | 既存トークンと一致 |
22-| 画面幅バンド (tablet) | **768–1279px** | `--breakpoint-tablet-min/max` | 既存トークンと一致 |
23-| 画面幅バンド (PC) | **1280px〜** | `--breakpoint-desktop-min` | 既存トークンと一致 |
24-| モバイル最小タップ領域 | **44px** | `--btn-min-height-mobile` | WCAG 2.5.5 Target Size |
25-
26----
27-
28-## ダッシュボード実値との食い違い・採否
--
30-| 観点 | タスク仕様 | ダッシュボード実値 | 採用値 | 採否理由 |
31-|---|---|---|---|---|
32:| カード余白 (PC) | 24px | `db-section-card`: 16px (`--space-4`) | **24px（仕様採用）** | ダッシュボードのコンパクト設計は db-* クラスで維持。新 Card 金型は 24px を標準に設定。Task 1E でどちらに統一するか判断。 |
33-| カード間ギャップ | 24px | `db-content-stack` gap: 16px (`--space-4`) | **24px（仕様採用）** | 同上。既存実画面は変更しない。 |
34:| カード余白 (compact/mobile) | 16px | `db-section-card`: 16px | **16px（ダッシュボード一致）** | 一致のため採否なし。 |
35:| 既存 `.card` padding | — | 20px (`--space-5`) | **変更なし** | 既存クラス変更禁止のため。`--comp-card-padding` 24px とは 4px の差。Task 1E で統一候補。 |
36-
37----
38-
39-## Button 金型仕様
40-
41-### バリアント → 既存 CSS クラスのマッピング
42-
43-| variant | 既存クラス |
--
68----
69-
70:## Card 金型仕様
71-
72-### バリアント
73-
74-| variant | 追加スタイル |
75-|---|---|
76-| `container` | ベースのみ（白背景・8px角丸・shadow-sm） |
77-| `interactive` | hover: shadow-md + translateY(-1px) / focus-visible: accent outline |
78-| `metric` | border-top: 3px solid accent |
--
82-| density | padding |
83-|---|---|
84:| `default` | `var(--comp-card-padding)` = 24px |
85:| `compact` | `var(--comp-card-padding-compact)` = 16px |
86-
87-- モバイル（≤767px）: `default` も自動的に `compact` (16px) に縮小
88-
89----
90-
91-## プレビュー確認方法
92-
93-```bash
--
106-［転記省略: 短縮ファイル名のパス表記を含みPRゲートの引用検査に掛かるため。原文は docs/specs/component-standard.md の106行目］
107-［転記省略: 同上。原文は docs/specs/component-standard.md の107行目］
108:3. カード余白の統一判断: 24px (`--comp-card-padding`) / 20px (`.card`) / 16px (`db-section-card`) のどれを SSoT にするか
109-4. `btn-sm` 再設計: 現状は独立カラー（`bg-hover`）を持ちバリアントと合成不可 → `comp-btn--sm` に一本化するか
110-
111----
112-
113-## フォーム入力 標準トークン（Task 2C 追加）
114-
115-| トークン | 値 | 説明 |
116-|---|---|---|
```

件数: 76（コマンド出力の行数: wc -l）

### R11 金型（部品）

```bash
ls frontend/src/components
```

出力行数: 140

<details><summary>全文（140行）</summary>

```
AccountCompanySaveButtonMigration.test.tsx
AdminMasterSaveButtonMigration.test.tsx
AllLegacyButtonDynamicMigration.test.tsx
AllLegacyButtonOperationMigration.test.tsx
AvatarUpload.css
AvatarUpload.stories.tsx
AvatarUpload.test.tsx
AvatarUpload.tsx
Badge.css
Badge.stories.tsx
Badge.tsx
BotFormButtonMigration.test.tsx
Button.css
Button.stories.tsx
Button.test.tsx
Button.tsx
buttonAppearance.ts
ButtonLink.stories.tsx
ButtonLink.test.tsx
ButtonLink.tsx
Card.css
Card.stories.tsx
Card.tsx
ChannelTypeCombobox.stories.tsx
ChannelTypeCombobox.tsx
CommerceNavigationButtonMigration.test.tsx
CommerceSubmitButtonMigration.test.tsx
CommissionPanel.stories.tsx
CommissionPanel.tsx
CompanyContactSelector.stories.tsx
CompanyContactSelector.tsx
ConfirmModal.stories.tsx
ConfirmModal.tsx
ContactChannelForm.stories.tsx
ContactChannelForm.tsx
ContactChannelLinks.stories.tsx
ContactChannelLinks.tsx
ContentToolbar.css
ContentToolbar.stories.tsx
ContentToolbar.tsx
CountryCombobox.stories.tsx
CountryCombobox.tsx
DataTable.css
DataTable.stories.tsx
DataTable.tsx
DesktopShell.stories.tsx
DesktopShell.test.tsx
DesktopShell.tsx
Drawer.css
Drawer.stories.tsx
Drawer.tsx
EmptyState.css
EmptyState.stories.tsx
EmptyState.tsx
FeatureGate.tsx
FedExRateModal.stories.tsx
FedExRateModal.test.tsx
FedExRateModal.tsx
field-size.css
FormActionButtonMigration.test.tsx
FormField.css
FullPageFormButtonMigration.test.tsx
GoogleCalendarStatusBar.css
GoogleCalendarStatusBar.stories.tsx
GoogleCalendarStatusBar.test.tsx
GoogleCalendarStatusBar.tsx
HeaderButton.stories.tsx
HeaderButton.test.tsx
HeaderButton.tsx
IconToggleButton.css
IconToggleButton.stories.tsx
IconToggleButton.test.tsx
IconToggleButton.tsx
IntegrationLaunchButtonMigration.test.tsx
InventoryPicker.stories.tsx
InventoryPicker.tsx
InventorySearchBar.stories.tsx
InventorySearchBar.tsx
LeadFormButtonMigration.test.tsx
loading
master-list-editor
MasterSearchButtonMigration.test.tsx
MergeCompanyModal.stories.tsx
MergeCompanyModal.tsx
MergeContactModal.stories.tsx
MergeContactModal.tsx
MergeLeadModal.stories.tsx
MergeLeadModal.tsx
MobileShell.stories.tsx
MobileShell.test.tsx
MobileShell.tsx
Modal.css
Modal.stories.tsx
Modal.tsx
NavDropdown.stories.tsx
NavDropdown.tsx
NavItemList.stories.tsx
NavItemList.test.tsx
NavItemList.tsx
OrderFinancialPanel.stories.tsx
OrderFinancialPanel.tsx
OrderLeadButtonMigration.test.tsx
PageFormButtonMigration.test.tsx
PageLayout.stories.tsx
PageLayout.tsx
Popover.css
Popover.stories.tsx
Popover.tsx
PriorityScoreBadge.stories.tsx
PriorityScoreBadge.test.tsx
PriorityScoreBadge.tsx
PriorityScoreOverride.stories.tsx
PriorityScoreOverride.tsx
ProtectedRoute.tsx
PurchaseAdminEditorButtonMigration.test.tsx
PurchaseDetailPanel.stories.tsx
PurchaseDetailPanel.tsx
RoleKnowledgeButtonMigration.test.tsx
Select.stories.tsx
Select.tsx
SharedButtonMigration.test.tsx
ShippingDetailPanel.stories.tsx
ShippingDetailPanel.tsx
StaffFormButtonMigration.test.tsx
StaffReportFormButtonMigration.test.tsx
SubMenu.css
SubMenu.stories.tsx
SubMenu.test.tsx
SubMenu.tsx
Tabs.css
Tabs.stories.tsx
Tabs.tsx
TeamFormButtonMigration.test.tsx
Textarea.stories.tsx
Textarea.tsx
TextField.stories.tsx
TextField.tsx
Tooltip.css
Tooltip.stories.tsx
Tooltip.tsx
```

</details>

件数: 140（コマンド出力の行数: wc -l）

```bash
find frontend/src -name '*.stories.tsx' | wc -l
```

```
      50
```

```bash
cat -n docs/CC_UI_GOVERNANCE.md | sed -n '1,40p'
```

```
     1	# CC UI ガバナンス遵守テンプレ（ADR-144）
     2	
     3	CC（Claude Code）が UI 部品を新設・修正するたびに参照すること。
     4	
     5	---
     6	
     7	## 必須チェック（UI 部品を実装する前に）
     8	
     9	1. **`components/` に金型があるか先に確認する**
    10	   - `<Select>` / `<TextField>` / `<SearchBar>` / `<Tabs>` / `<OverflowTabs>` 等が既に存在するか
    11	   - `frontend/src/components/` を grep または Glob で確認する
    12	2. **あれば必ずそれを使う**（独自実装を重複させない）
    13	3. **無ければ実装しない・止めて報告する**
    14	   - PO 許可を得てから `components/` に金型を登録してから使う
    15	［転記省略: 雛形ファイル名のパス表記を含みPRゲートの引用検査に掛かるため。原文は docs/CC_UI_GOVERNANCE.md の15行目（部品は tsx・css・stories の3ファイル一組で作る、という作法）］
    16	
    17	---
    18	
    19	## 禁止事項（CI ゲートが赤にする）
    20	
    21	| 禁止 | 理由 |
    22	|------|------|
    23	| 生 `<select>` | `<Select>` 金型を使うこと |
    24	| 生 `<input type="text"\|"search"\|省略>` | `<TextField>` / `SearchBar` 等を使うこと |
    25	| 自作タブ（className に `tab` 語を含む div/nav 等） | `<Tabs>` / `OverflowTabs` を使うこと |
    26	| 色直値（`#xxx` / `rgba()`）のインラインスタイル | CSS 変数 `var(--color-*)` を使うこと（ADR-067）|
    27	| 生 px 数値のインラインスタイル（例 `width: 24`）| デザイントークン `var(--size-*)` を使うこと（ADR-067）|
    28	
    29	---
    30	
    31	## どうしても生実装が必要な場合の例外コメント
    32	
    33	```jsx
    34	{/* ui-allow: <理由> (#<課題番号>) */}
    35	<select value={x} onChange={f}>
    36	```
    37	
    38	**書式ルール（両方必須・どちらか欠けると無効＝赤のまま）:**
    39	- `<理由>`: 空でない文字列で理由を明記する
    40	- `(#<番号>)`: GitHub Issue / 課題番号を `#123` 形式で記載する
```

件数: 40（コマンド出力の行数: wc -l）

### R12 モバイル対応の採用

```bash
grep -rln -e useIsMobile -e MobileShell frontend/src --include=*.tsx --include=*.ts | grep -v -e test -e stories
```

```
frontend/src/App.tsx
frontend/src/components/DesktopShell.tsx
frontend/src/components/MobileShell.tsx
frontend/src/components/NavItemList.tsx
frontend/src/hooks/useIsMobile.ts
```

件数: 5（コマンド出力の行数: wc -l）

```bash
find frontend/src/pages -name '*.tsx' ! -name '*.test.tsx' ! -name '*.stories.tsx' | wc -l
```

```
     191
```

### R13 Playwright

```bash
cat -n frontend/playwright.config.ts
```

```
     1	/**
     2	 * Playwright config (Phase 1-E F2-S3).
     3	 *
     4	 * 撮影台本 docs/META_APP_REVIEW_SCREENCAST_SCRIPT.md の 7 シーン + Data Deletion を
     5	 * frontend E2E でカバーする。実機 Meta OAuth は通さず、API レイヤを mock する。
     6	 *
     7	 * - baseURL: Vite dev server (localhost:5173)
     8	 * - browser: chromium 単体（CI 時間短縮 / multi-browser は後追い）
     9	 * - webServer: 自動で `npm run dev` を起動する
    10	 * - retain-on-failure: trace / video / screenshot を artifact 化
    11	 *
    12	 * 使い方:
    13	 *   npm run test:e2e:install   # browser を一度だけ install
    14	 *   npm run test:e2e
    15	 *   npm run test:e2e:ui        # interactive UI mode
    16	 */
    17	
    18	import { defineConfig, devices } from "@playwright/test";
    19	
    20	const PORT = Number(process.env.PORT || 5173);
    21	const BASE_URL = process.env.E2E_BASE_URL || `http://localhost:${PORT}`;
    22	
    23	export default defineConfig({
    24	  testDir: "./tests-e2e",
    25	  // spec ファイル間は並列実行。各 spec 内のテストは順序依存があるため直列のまま。
    26	  fullyParallel: true,
    27	  forbidOnly: !!process.env.CI,
    28	  retries: process.env.CI ? 1 : 0,
    29	  // CI: 4 workers で並列実行（GitHub Actions ubuntu-latest は 4 vCPU）
    30	  // local: CPU コア数に応じて自動調整（undefined = Playwright デフォルト）
    31	  workers: process.env.CI ? 4 : undefined,
    32	  reporter: process.env.CI
    33	    ? [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]]
    34	    : [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
    35	
    36	  use: {
    37	    baseURL: BASE_URL,
    38	    // CI のフレーク削減: trace を毎回 retain（失敗時 artifact 化）
    39	    trace: "retain-on-failure",
    40	    screenshot: "only-on-failure",
    41	    video: "retain-on-failure",
    42	    actionTimeout: 15_000,
    43	    navigationTimeout: 30_000,
    44	  },
    45	
    46	  expect: {
    47	    toHaveScreenshot: {
    48	      // アンチエイリアス差（~0.3%）を吸収しつつ、5px+ の配置ズレを検出するしきい値
    49	      maxDiffPixelRatio: 0.005,
    50	      // ピクセルごとの色距離（0〜1）: 0.15 = サブピクセル差を許容
    51	      threshold: 0.15,
    52	    },
    53	  },
    54	
    55	  projects: [
    56	    {
    57	      name: "chromium",
    58	      use: { ...devices["Desktop Chrome"] },
    59	    },
    60	  ],
    61	
    62	  // Vite dev server を自動起動する。E2E 用の env で Firebase config を空にし、
    63	  // tests-e2e/utils/auth.ts の addInitScript と組み合わせて認証を bypass する。
    64	  webServer: process.env.E2E_NO_WEBSERVER
    65	    ? undefined
    66	    : {
    67	        command: "npm run dev -- --port " + PORT,
    68	        url: BASE_URL,
    69	        reuseExistingServer: !process.env.CI,
    70	        timeout: 60_000,
    71	        env: {
    72	          // Firebase 実機 IDP に飛ばないようダミー値を設定（mock により無視される）
    73	          VITE_FIREBASE_API_KEY: "AIzaSyE2E-dummy-api-key",
    74	          VITE_FIREBASE_AUTH_DOMAIN: "e2e-fixture.firebaseapp.com",
    75	          VITE_GCP_PROJECT_ID: "e2e-fixture",
    76	          // ファネルダッシュボード: E2E はモックデータで実行
    77	          VITE_FUNNEL_DASHBOARD: "mock",
    78	        },
    79	      },
    80	});
```

件数: 80（コマンド出力の行数: wc -l）

```bash
grep -rn setViewportSize frontend/tests-e2e
```

```
frontend/tests-e2e/inbox-header-ui-screenshots.spec.ts:65:    await page.setViewportSize({ width: 1440, height: 900 });
frontend/tests-e2e/inbox-header-ui-screenshots.spec.ts:73:    await page.setViewportSize({ width: 1440, height: 900 });
frontend/tests-e2e/inbox-header-ui-screenshots.spec.ts:80:    await page.setViewportSize({ width: 1440, height: 900 });
frontend/tests-e2e/inbox-header-ui-screenshots.spec.ts:94:    await page.setViewportSize({ width: 1440, height: 900 });
frontend/tests-e2e/inbox-header-ui-screenshots.spec.ts:106:    await page.setViewportSize({ width: 1440, height: 900 });
frontend/tests-e2e/inbox-header-ui-screenshots.spec.ts:115:    await page.setViewportSize({ width: 1440, height: 900 });
frontend/tests-e2e/inbox-header-ui-screenshots.spec.ts:125:    await page.setViewportSize({ width: 1024, height: 768 }); // ≤1279px で三点メニュー表示
frontend/tests-e2e/inbox-header-ui-screenshots.spec.ts:137:    await page.setViewportSize({ width: 1440, height: 900 });
frontend/tests-e2e/tcg-product-detail.spec.ts:51:      await page.setViewportSize({ width, height: 900 });
frontend/tests-e2e/tcg-import-workflow.spec.ts:201:    await page.setViewportSize({ width: 390, height: 844 });
frontend/tests-e2e/tcg-import-workflow.spec.ts:265:    await page.setViewportSize({ width: 390, height: 844 });
frontend/tests-e2e/tcg-import-workflow.spec.ts:352:    await page.setViewportSize({ width: configuration.width, height: 1000 });
frontend/tests-e2e/tcg-import-workflow.spec.ts:400:    await page.setViewportSize({ width, height: 1000 });
frontend/tests-e2e/horizontal-overflow.spec.ts:50:    await page.setViewportSize(MOBILE_VIEWPORT);
frontend/tests-e2e/send-guard-screenshots.spec.ts:60:    await page.setViewportSize({ width: 1440, height: 900 });
frontend/tests-e2e/send-guard-screenshots.spec.ts:68:    await page.setViewportSize({ width: 1440, height: 900 });
frontend/tests-e2e/send-guard-screenshots.spec.ts:78:    await page.setViewportSize({ width: 1440, height: 900 });
frontend/tests-e2e/send-guard-screenshots.spec.ts:85:    await page.setViewportSize({ width: 1440, height: 900 });
frontend/tests-e2e/send-guard-screenshots.spec.ts:95:    await page.setViewportSize({ width: 1440, height: 900 });
frontend/tests-e2e/send-guard-screenshots.spec.ts:105:    await page.setViewportSize({ width: 1440, height: 900 });
frontend/tests-e2e/tcg-product-import.spec.ts:24:    await page.setViewportSize({ width, height: 900 });
frontend/tests-e2e/tcg-product-import.spec.ts:95:    await page.setViewportSize({ width: 390, height: 844 });
frontend/tests-e2e/tcg-product-import.spec.ts:173:    await page.setViewportSize({ width: 390, height: 844 });
frontend/tests-e2e/desktop-shell.spec.ts:35:    await page.setViewportSize(DESKTOP_VIEWPORT);
frontend/tests-e2e/desktop-shell.spec.ts:81:    await page.setViewportSize({ width: 1440, height: 900 });
frontend/tests-e2e/mobile-shell.spec.ts:55:    await page.setViewportSize(MOBILE_VIEWPORT);
frontend/tests-e2e/mobile-shell.spec.ts:78:    await page.setViewportSize({ width: 390, height: 844 });
frontend/tests-e2e/mobile-shell.spec.ts:95:    await page.setViewportSize(MOBILE_VIEWPORT);
frontend/tests-e2e/mobile-shell.spec.ts:120:    await page.setViewportSize(MOBILE_VIEWPORT);
frontend/tests-e2e/mobile-shell.spec.ts:142:    await page.setViewportSize(MOBILE_VIEWPORT);
frontend/tests-e2e/mobile-shell.spec.ts:210:    await page.setViewportSize(MOBILE_VIEWPORT);
frontend/tests-e2e/mobile-shell.spec.ts:243:    await page.setViewportSize(PC_VIEWPORT);
frontend/tests-e2e/mobile-shell.spec.ts:254:    await page.setViewportSize(PC_VIEWPORT);
frontend/tests-e2e/mobile-shell.spec.ts:271:    await page.setViewportSize(MOBILE_VIEWPORT);
frontend/tests-e2e/analysis-rules-line-guide.spec.ts:26:  await page.setViewportSize({ width: configuration.width, height: 900 });
frontend/tests-e2e/inbox-header-menu.spec.ts:38:    await page.setViewportSize({ width: 1024, height: 768 });
frontend/tests-e2e/inbox-header-menu.spec.ts:49:    await page.setViewportSize({ width: 1024, height: 768 });
frontend/tests-e2e/inbox-header-menu.spec.ts:69:    await page.setViewportSize({ width: 1024, height: 768 });
frontend/tests-e2e/inbox-header-menu.spec.ts:85:    await page.setViewportSize({ width: 1440, height: 900 });
frontend/tests-e2e/mobile-bp-token-g5.spec.ts:47:    await page.setViewportSize(TABLET_BOUNDARY_VIEWPORT);
```

件数: 40（コマンド出力の行数: wc -l）

```bash
grep -rln toHaveScreenshot frontend/tests-e2e
```

```
frontend/tests-e2e/karte-screenshot-compare.spec.ts
frontend/tests-e2e/karte-visual-gate.spec.ts
frontend/tests-e2e/funnel-dashboard.spec.ts
frontend/tests-e2e/funnel-dashboard-subpages.spec.ts
```

件数: 4（コマンド出力の行数: wc -l）

### R14 受信箱画面（ベンチマーク対象）

```bash
grep -rn 'lead-chat' frontend/src --include=*.tsx --exclude=*.test.* --exclude=*.stories.* --exclude-dir=node_modules | head -20
```

```
frontend/src/App.tsx:194:                  <Route path="/lead-chat" element={<InboxPage />} />
frontend/src/constants/icons.tsx:415:// Layout.tsx の /lead-chat ナビアイテム用（outline バリアント — サイドバー統一仕様）
frontend/src/components/DesktopShell.tsx:116:  const isInbox = location.pathname === "/lead-chat";
frontend/src/components/DesktopShell.tsx:246:                  to="/lead-chat"
frontend/src/components/MobileShell.tsx:19: *   │   ├── NavLink(受信箱: /lead-chat) — prefs.show_chat_menu 条件付き
frontend/src/components/MobileShell.tsx:266:            to="/lead-chat"
```

件数: 6（コマンド出力の行数: wc -l）

```bash
grep -n 'InboxPage' frontend/src/App.tsx | head -3
```

```
67:import InboxPage from "./pages/inbox/InboxPage";
194:                  <Route path="/lead-chat" element={<InboxPage />} />
```

件数: 2（コマンド出力の行数: wc -l）

```bash
wc -l frontend/src/pages/inbox/*.tsx frontend/src/pages/inbox/*.ts frontend/src/pages/inbox/*.css frontend/src/hooks/useInboxSSE.ts | grep -v -e test -e stories
```

```
     251 frontend/src/pages/inbox/InboxConversationList.tsx
     863 frontend/src/pages/inbox/InboxKartePanel.tsx
     841 frontend/src/pages/inbox/InboxMessageThread.tsx
     237 frontend/src/pages/inbox/InboxPage.tsx
     273 frontend/src/pages/inbox/InboxProfileModal.tsx
      91 frontend/src/pages/inbox/InboxSettingsModal.tsx
     203 frontend/src/pages/inbox/ManualRecordSection.tsx
      68 frontend/src/pages/inbox/MessageReactionBadges.tsx
     188 frontend/src/pages/inbox/OutboundTranslationPreview.tsx
     160 frontend/src/pages/inbox/SalesFormMultiSelect.tsx
      67 frontend/src/pages/inbox/discordSendError.ts
     186 frontend/src/pages/inbox/inbox.types.ts
       2 frontend/src/pages/inbox/reactionEmojiPresets.ts
      35 frontend/src/pages/inbox/reactionHeart.ts
      16 frontend/src/pages/inbox/reactionPaths.ts
     976 frontend/src/pages/inbox/useInboxState.ts
      54 frontend/src/pages/inbox/useLongPressReveal.ts
    1822 frontend/src/pages/inbox/InboxPage.css
      15 frontend/src/hooks/useInboxSSE.ts
    6947 total
```

件数: 20（コマンド出力の行数: wc -l）

```bash
grep -n '@media' frontend/src/pages/inbox/*.tsx frontend/src/pages/inbox/*.ts frontend/src/pages/inbox/*.css frontend/src/hooks/useInboxSSE.ts
```

```
frontend/src/pages/inbox/InboxPage.css:1039:@media (max-width: 1279px) {
frontend/src/pages/inbox/InboxPage.css:1151:@media (max-width: 767px) {
frontend/src/pages/inbox/InboxPage.css:1490:@media (max-width: 560px) {
frontend/src/pages/inbox/InboxPage.css:1785:@media (hover: hover) {
```

件数: 4（コマンド出力の行数: wc -l）

```bash
grep -n -e 'api\.' -e 'fetch(' -e 'useQuery' -e 'apiClient' frontend/src/pages/inbox/*.tsx frontend/src/pages/inbox/*.ts frontend/src/pages/inbox/*.css frontend/src/hooks/useInboxSSE.ts | grep -v -e '\.test\.' -e stories
```

```
frontend/src/pages/inbox/InboxKartePanel.tsx:102:    api.get<{ guild_id: string | null }>("/admin/discord-config")
frontend/src/pages/inbox/InboxKartePanel.tsx:253:      const res = await api.post("/registration-tokens", { lead_id: leadId, type }) as { registration_url: string };
frontend/src/pages/inbox/InboxKartePanel.tsx:623:        const msgData = await api.get<{ messages: Array<{ created_at: string }> }>(
frontend/src/pages/inbox/InboxKartePanel.tsx:637:        const stats = await api.get<LeadStats>(`/leads/${leadId}/stats`);
frontend/src/pages/inbox/InboxKartePanel.tsx:720:      await api.post(`/discord/channel-invite/${leadId}`, {});
frontend/src/pages/inbox/InboxKartePanel.tsx:762:      await api.post(`/discord/sync-role/${leadId}`, {});
frontend/src/pages/inbox/InboxKartePanel.tsx:819:      await api.post(`/discord/${action}/${leadId}`, {});
frontend/src/pages/inbox/InboxMessageThread.tsx:292:        const res = await fetch(
frontend/src/pages/inbox/ManualRecordSection.tsx:73:      await api.post(`/api/v1/leads/${leadId}/conv-logs`, {
frontend/src/pages/inbox/useInboxState.ts:358:      const data = await api.get<LeadDetail>(`/leads/${leadId}`);
frontend/src/pages/inbox/useInboxState.ts:397:    await api.post<void>(
frontend/src/pages/inbox/useInboxState.ts:407:    await api.delete(buildReactionDeletePath(selectedLeadId, messageId, emojiName, emojiId));
frontend/src/pages/inbox/useInboxState.ts:437:      const updated = await api.patch<LeadDetail>(`/leads/${leadDetail.id}`, payload);
frontend/src/pages/inbox/useInboxState.ts:572:    api.get<{ language: string | null; total_records: number; confident: boolean }>(
frontend/src/pages/inbox/useInboxState.ts:788:      await api.patch<void>(`/leads/${selectedLeadId}`, { status: "out_of_scope" });
frontend/src/pages/inbox/useInboxState.ts:798:      await api.delete(`/leads/${selectedLeadId}`);
frontend/src/pages/inbox/useInboxState.ts:842:    await Promise.all(targets.map((id) => api.patch<void>(`/leads/${id}`, { status: "out_of_scope" })));
frontend/src/pages/inbox/useInboxState.ts:851:    await Promise.all(targets.map((id) => api.delete(`/leads/${id}`)));
```

件数: 18（コマンド出力の行数: wc -l）

### R15 ガードチェック

```bash
cat -n frontend/package.json | sed -n '1,80p'
```

```
     1	{
     2	  "name": "salesanchor-frontend",
     3	  "private": true,
     4	  "version": "1.0.0",
     5	  "type": "module",
     6	  "scripts": {
     7	    "dev": "vite",
     8	    "build": "tsc && vite build",
     9	    "preview": "vite preview",
    10	    "test:e2e": "playwright test",
    11	    "test:e2e:ui": "playwright test --ui",
    12	    "test:e2e:install": "playwright install --with-deps chromium",
    13	    "lint": "eslint src",
    14	    "lint:fix": "eslint src --fix",
    15	    "check:css-colors": "node scripts/check-css-hardcoded-colors.js",
    16	    "check:dark-parity": "node scripts/check-dark-parity.js",
    17	    "check:jsx-emoji": "node scripts/check-jsx-emoji.js",
    18	    "check:css-var-fallbacks": "node scripts/check-css-var-fallbacks.js",
    19	    "check:css-values": "node scripts/check-css-hardcoded-values.js",
    20	    "check:nav-sync": "node scripts/check-nav-title-sync.js",
    21	    "check:claude-size": "node scripts/check-claude-size.js",
    22	    "check:page-layout": "node scripts/check-page-layout.js",
    23	    "check:content-toolbar": "node scripts/check-content-toolbar.js",
    24	    "check:page-folder": "node scripts/check-page-folder.js",
    25	    "check:icon-sync": "node scripts/check-icon-sync.js",
    26	    "check:i18n-missing-keys": "node scripts/check-i18n-missing-keys.js",
    27	    "fix:icon-sync": "node scripts/check-icon-sync.js --fix",
    28	    "check:breakpoint-sync": "node scripts/check-breakpoint-sync.js",
    29	    "check:mobile-responsive-structure2": "node scripts/check-mobile-responsive-structure2.js",
    30	    "check:css-fixed-position": "node scripts/check-css-fixed-position.js",
    31	    "check:page-size": "node scripts/check-page-size.js",
    32	    "check:stories": "node scripts/check-stories-count.js",
    33	    "audit:unused-tokens": "node scripts/check-unused-tokens.js",
    34	    "check:color-token-sync": "node scripts/check-color-token-sync.js",
    35	    "check:onboarding-doc": "node scripts/check-onboarding-doc.js",
    36	    "check:concurrently": "node scripts/check-concurrently-usage.js",
    37	    "check:sidebar-outline": "node scripts/check-sidebar-outline.js",
    38	    "check:new-tokens": "node scripts/check-new-tokens.js",
    39	    "check:stylelint": "stylelint \"src/**/*.css\"",
    40	    "check:css-class-naming": "node scripts/check-css-class-naming.js",
    41	    "check:status-direct-writes": "node scripts/check-status-direct-writes.js",
    42	    "test:unit": "vitest run --config vitest.unit.config.ts --project unit",
    43	    "test:coverage": "vitest run --config vitest.unit.config.ts --project unit --coverage",
    44	    "check:all": "concurrently --kill-others-on-fail --max-processes 6 \"npm run check:claude-size\" \"npm run lint\" \"npm run check:css-colors\" \"npm run check:dark-parity\" \"npm run check:jsx-emoji\" \"npm run check:css-var-fallbacks\" \"npm run check:css-values\" \"npm run check:nav-sync\" \"npm run check:page-layout\" \"npm run check:content-toolbar\" \"npm run check:page-folder\" \"npm run check:icon-sync\" \"npm run check:i18n-missing-keys\" \"npm run check:css-fixed-position\" \"npm run check:breakpoint-sync\" \"npm run check:mobile-responsive-structure2\" \"npm run check:page-size\" \"npm run check:stories\" \"npm run check:color-token-sync\" \"npm run check:onboarding-doc\" \"npm run check:concurrently\" \"npm run check:sidebar-outline\" \"npm run check:stylelint\" \"npm run check:css-class-naming\" \"npm run check:status-direct-writes\"",
    45	    "prepare": "cd .. && husky frontend/.husky",
    46	    "storybook": "storybook dev -p 6006",
    47	    "build-storybook": "storybook build",
    48	    "generate:icon-sizes": "node scripts/generate-icon-sizes.js",
    49	    "predev": "npm run generate:icon-sizes",
    50	    "prebuild": "npm run generate:icon-sizes"
    51	  },
    52	  "lint-staged": {
    53	    "src/**/*.{ts,tsx}": [
    54	      "eslint --max-warnings=0",
    55	      "node scripts/check-jsx-emoji.js",
    56	      "node scripts/check-css-var-fallbacks.js"
    57	    ],
    58	    "src/**/*.css": [
    59	      "node scripts/check-css-hardcoded-colors.js",
    60	      "node scripts/check-css-var-fallbacks.js",
    61	      "node scripts/check-css-hardcoded-values.js",
    62	      "node scripts/check-css-fixed-position.js",
    63	      "stylelint"
    64	    ],
    65	    "src/index.css": [
    66	      "node scripts/check-dark-parity.js"
    67	    ]
    68	  },
    69	  "dependencies": {
    70	    "@fullcalendar/core": "^6.1.20",
    71	    "@fullcalendar/daygrid": "^6.1.20",
    72	    "@fullcalendar/interaction": "^6.1.20",
    73	    "@fullcalendar/react": "^6.1.20",
    74	    "@fullcalendar/timegrid": "^6.1.20",
    75	    "@heroicons/react": "^2.2.0",
    76	    "@types/react-big-calendar": "^1.16.3",
    77	    "@xyflow/react": "^12.12.0",
    78	    "date-fns": "^4.3.0",
    79	    "firebase": "^11.0.0",
    80	    "i18next": "^26.1.0",
```

件数: 80（コマンド出力の行数: wc -l）

```bash
ls frontend/node_modules 2>&1 | head -1
```

```
ls: frontend/node_modules: No such file or directory
```

件数: 1（コマンド出力の行数: wc -l）

未実行: node_modules なし（npm ci 未実施）

## 既存ADR検索の結果

R1 の1つ目のコマンドが返したファイル名（解釈なし）:

- docs/adr/ADR-021-order-management.md
- docs/adr/ADR-046-lp-redesign.md
- docs/adr/ADR-049-lp-section-completion.md
- docs/adr/ADR-054-lp-hubspot-style-restructure.md
- docs/adr/ADR-057-lp-premium-restyle.md
- docs/adr/ADR-067-design-token-enforcement.md
- docs/adr/ADR-073-design-system-kgi-rubric.md
- docs/adr/ADR-074-worktree-agent-enforcement.md
- docs/adr/ADR-095-sa-ssot-two-backbone-architecture.md
- docs/adr/ADR-101-sa-quotation-invoice-generation.md
- docs/adr/ADR-108-inbox-karte-panel-redesign.md
- docs/adr/ADR-109-leads-status-ssot-immutable-codes.md
- docs/adr/ADR-139-funnel-kgi-dashboard-frontend.md
- docs/adr/ADR-140-mobile-nav-bottom-tabs.md
- docs/adr/ADR-144-ui-component-governance.md
- docs/adr/ADR-159-staff-identity-on-discord.md
- docs/adr/README.md

## この調査でわからなかったこと

- R15: node_modules が無いため npm run check:all は未実行。
- R14: InboxPage 関連ファイルは App.tsx:67 の import 先 frontend/src/pages/inbox/ と hooks/useInboxSSE.ts を対象にした（ファイル名の inbox 一致で選定）。
