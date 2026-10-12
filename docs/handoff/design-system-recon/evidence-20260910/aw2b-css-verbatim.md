
## frontend/src/components.css lines 15,75
```
    15	  color: var(--text-secondary);
    16	  margin-bottom: var(--space-1);
    17	}
    18	
    19	.form-group input,
    20	.form-group select,
    21	.form-group textarea {
    22	  width: 100%;
    23	  padding: var(--space-2) var(--space-3);
    24	  border: 1px solid var(--border);
    25	  border-radius: var(--radius-sm);
    26	  font-size: var(--font-base);
    27	  color: var(--text-primary);
    28	  background: var(--bg-surface);
    29	  box-sizing: border-box;
    30	}
    31	
    32	.form-group input:focus,
    33	.form-group select:focus,
    34	.form-group textarea:focus {
    35	  outline: none;
    36	  border-color: var(--accent);
    37	  box-shadow: var(--focus-ring-shadow);
    38	}
    39	
    40	/* stylelint-disable-next-line no-descending-specificity -- intentional: textarea size after focus state */
    41	.form-group textarea {
    42	  min-height: var(--textarea-min-h);
    43	  resize: vertical;
    44	}
    45	
    46	.form-actions {
    47	  display: flex;
    48	  justify-content: flex-end;
    49	  gap: var(--space-2);
    50	  margin-top: var(--space-5);
    51	}
    52	
    53	/* --- Search / Filter --- */
    54	.search-bar,
    55	.filter-bar {
    56	  margin-bottom: var(--space-4);
    57	}
    58	
    59	/* stylelint-disable no-descending-specificity -- intentional: search/filter context overrides form-group styles */
    60	.search-bar input,
    61	.filter-bar select {
    62	  padding: var(--space-2) var(--space-3);
    63	  border: 1px solid var(--border);
    64	  border-radius: var(--radius-sm);
    65	  font-size: var(--font-base);
    66	  min-width: var(--input-select-min-w);
    67	  background: var(--bg-surface);
    68	  color: var(--text-primary);
    69	}
    70	/* stylelint-enable no-descending-specificity */
    71	
    72	/* --- Search Input Field (Single Source of Truth) ---
    73	 * 検索欄のデザイントークン。すべてのページでこのクラスを使う。
    74	 * ページ固有のwidth/paddingのみ各ページのCSSで上書きすること。
    75	 * --search-focus-glow / --accent は index.css で定義。
```

## frontend/src/company-forms.css lines 95,200
```
    95	  font-size: var(--font-sm);
    96	  font-weight: var(--font-weight-medium);
    97	  color: var(--text-secondary);
    98	}
    99	
   100	.form-grid > .form-row input:not([type="checkbox"]):not([type="radio"]),
   101	.form-grid > .form-row select,
   102	.form-grid > .form-row textarea {
   103	  padding: var(--space-2) var(--space-3);
   104	  border: 1px solid var(--border-strong);
   105	  border-radius: var(--radius-md);
   106	  font-size: var(--font-base);
   107	  background: var(--bg-surface);
   108	  color: var(--text-primary);
   109	  width: 100%;
   110	  box-sizing: border-box;
   111	  font-family: inherit;
   112	}
   113	
   114	.form-grid > .form-row textarea {
   115	  min-height: var(--textarea-min-h);
   116	  resize: vertical;
   117	}
   118	
   119	/* stylelint-disable no-descending-specificity -- intentional: focus state after general input style */
   120	.form-grid > .form-row input:focus,
   121	.form-grid > .form-row select:focus,
   122	.form-grid > .form-row textarea:focus {
   123	  outline: none;
   124	  border-color: var(--accent);
   125	  box-shadow: var(--focus-ring-shadow);
   126	}
   127	/* stylelint-enable no-descending-specificity */
   128	
   129	.form-grid > .form-actions {
   130	  display: flex;
   131	  justify-content: flex-end;
   132	  gap: var(--space-3);
   133	  margin-top: var(--space-2);
   134	  grid-column: 1 / -1;
   135	  padding-top: var(--space-4);
   136	  border-top: 1px solid var(--border);
   137	}
   138	
   139	/* MergeCompanyModal 等、modal 内で使われる form-row は単カラム */
   140	.modal-content .form-row,
   141	.modal-content-wide .form-row {
   142	  display: flex;
   143	  flex-direction: column;
   144	  gap: var(--space-6px);
   145	  margin-bottom: var(--space-4);
   146	}
   147	
   148	.modal-content .form-row > label,
   149	.modal-content-wide .form-row > label {
   150	  font-size: var(--font-sm);
   151	  font-weight: var(--font-weight-medium);
   152	  color: var(--text-secondary);
   153	}
   154	
   155	/* stylelint-disable no-descending-specificity -- intentional: modal context overrides grid styles */
   156	.modal-content .form-row input:not([type="checkbox"]):not([type="radio"]),
   157	.modal-content .form-row select,
   158	.modal-content .form-row textarea,
   159	.modal-content-wide .form-row input:not([type="checkbox"]):not([type="radio"]),
   160	.modal-content-wide .form-row select,
   161	.modal-content-wide .form-row textarea {
   162	  padding: var(--space-2) var(--space-3);
   163	  border: 1px solid var(--border-strong);
   164	  border-radius: var(--radius-md);
   165	  font-size: var(--font-base);
   166	  background: var(--bg-surface);
   167	  color: var(--text-primary);
   168	  width: 100%;
   169	  box-sizing: border-box;
   170	  font-family: inherit;
   171	}
   172	
   173	.modal-content .form-row textarea,
   174	.modal-content-wide .form-row textarea {
   175	  min-height: var(--textarea-min-h);
   176	  resize: vertical;
   177	}
   178	/* stylelint-enable no-descending-specificity */
   179	
   180	/* stylelint-disable no-descending-specificity -- intentional: modal focus overrides grid focus style */
   181	.modal-content .form-row input:focus,
   182	.modal-content .form-row select:focus,
   183	.modal-content .form-row textarea:focus,
   184	.modal-content-wide .form-row input:focus,
   185	.modal-content-wide .form-row select:focus,
   186	.modal-content-wide .form-row textarea:focus {
   187	  outline: none;
   188	  border-color: var(--accent);
   189	  box-shadow: var(--focus-ring-shadow);
   190	}
   191	/* stylelint-enable no-descending-specificity */
   192	
   193	/* タブレット縦 (~ 768px) では form-grid を 1 カラムに */
   194	@media (max-width: 768px) {
   195	  .form-grid {
   196	    grid-template-columns: 1fr;
   197	    padding: var(--space-4);
   198	  }
   199	
   200	  .page-container {
```

## frontend/src/company-forms.css lines 250,275
```
   250	  align-items: start;
   251	}
   252	
   253	.product-edit-form fieldset > legend,
   254	.product-edit-form fieldset > .form-group-full {
   255	  grid-column: 1 / -1;
   256	}
   257	
   258	/* 入力枠が薄くて見えない問題の解消（--border → --border-strong で輪郭を明確に） */
   259	/* stylelint-disable no-descending-specificity -- 既存 .form-row *:focus より後段になるが、商品マスタ編集専用スコープの枠線上書きで意図的 */
   260	.product-edit-form .form-group input:not([type="checkbox"]):not([type="radio"]),
   261	.product-edit-form .form-group select,
   262	.product-edit-form .form-group textarea {
   263	  border: 1px solid var(--border-strong);
   264	}
   265	/* stylelint-enable no-descending-specificity */
```

## frontend/src/pages/goal-setting/GoalSettingPage.css lines 550,572
```
   550	  display: flex;
   551	  align-items: center;
   552	  gap: var(--space-3);
   553	}
   554	
   555	.gs-select {
   556	  flex: 1;
   557	  padding: var(--space-2) var(--space-3);
   558	  border: 1px solid var(--border);
   559	  border-radius: var(--radius-md);
   560	  background: var(--bg-surface);
   561	  color: var(--text-primary);
   562	  font-size: var(--font-sm);
   563	  cursor: pointer;
   564	}
   565	
   566	/* ── 権限なしメッセージ ── */
   567	.gs-no-permission {
   568	  font-size: var(--font-sm);
   569	  color: var(--text-secondary);
   570	  margin: 0;
   571	  padding: var(--space-3);
   572	  background: var(--bg-primary);
```

## frontend/src/pages/account-settings/account-settings.css lines 145,170
```
   145	}
   146	
   147	.toggle-switch input:focus-visible + .toggle-slider {
   148	  box-shadow: var(--focus-ring-shadow);
   149	}
   150	
   151	/* Language select */
   152	.account-settings-lang-select {
   153	  padding: var(--space-1) var(--space-3);
   154	  border: 1px solid var(--border);
   155	  border-radius: var(--radius-sm);
   156	  background: var(--bg-surface);
   157	  color: var(--text-primary);
   158	  font-size: var(--font-sm);
   159	  cursor: pointer;
   160	  min-width: var(--size-lang-select-min);
   161	}
   162	
   163	.account-settings-lang-select:focus {
   164	  outline: none;
   165	  border-color: var(--accent);
   166	  box-shadow: var(--focus-ring-shadow);
   167	}
   168	
   169	.account-settings-success {
   170	  font-size: var(--font-sm);
```

## frontend/src/pages/inbox/InboxPage.css lines 395,425
```
   395	.inbox-page-filter-wrap {
   396	  padding: var(--space-1) var(--space-3) var(--space-6px);
   397	}
   398	.inbox-page-filter-select {
   399	  width: 100%;
   400	  padding: var(--space-1) var(--space-2);
   401	  font-size: var(--font-xs);
   402	  border-radius: var(--radius-xl);
   403	  border: 1px solid var(--border);
   404	  background: var(--bg-surface);
   405	  color: var(--text-primary);
   406	  font-family: inherit;
   407	  box-sizing: border-box;
   408	}
   409	
   410	/* ---- 中央パネル ---- */
   411	.inbox-center {
   412	  flex: 1;
   413	  display: flex;
   414	  flex-direction: column;
   415	  overflow: hidden;
   416	  background: var(--bg-surface);
   417	  min-width: 0;
   418	  /* ドロップ用オーバーレイの基準（2026-09-04 追加） */
   419	  position: relative;
   420	}
   421	
   422	/* ドラッグ&ドロップの受け入れ表示。
   423	   スレッド内に限定するため fixed ではなく absolute を使う。 */
   424	.inbox-drop-overlay {
   425	  position: absolute;
```

## frontend/src/pages/inbox/InboxPage.css lines 1420,1445
```
  1420	  display: flex; align-items: center; justify-content: space-between;
  1421	  padding: var(--space-2) 0; border-bottom: 1px solid var(--border);
  1422	}
  1423	.inbox-settings-label { font-size: var(--font-sm); color: var(--text-primary); }
  1424	.inbox-settings-select {
  1425	  background: var(--bg-primary); border: 1px solid var(--border);
  1426	  border-radius: var(--radius-sm); padding: var(--space-1) var(--space-2);
  1427	  font-size: var(--font-sm); color: var(--text-primary);
  1428	  cursor: pointer;
  1429	}
  1430	.inbox-settings-close-btn {
  1431	  margin-top: var(--space-5); width: 100%;
  1432	  background: var(--accent); color: var(--on-accent);
  1433	  border: none; border-radius: var(--radius-sm); padding: var(--space-2) var(--space-4);
  1434	  font-size: var(--font-sm); font-weight: 500; cursor: pointer;
  1435	  transition: opacity var(--transition-micro);
  1436	}
  1437	.inbox-settings-close-btn:hover { opacity: var(--opacity-dim); }
  1438	
  1439	/* ====== トグルスイッチ ====== */
  1440	.inbox-toggle { position: relative; display: inline-flex; width: var(--toggle-width); height: var(--toggle-height); cursor: pointer; }
  1441	.inbox-toggle input { opacity: 0; width: 0; height: 0; }
  1442	.inbox-toggle-slider {
  1443	  position: absolute; inset: 0;
  1444	  background: var(--border); border-radius: var(--radius-full);
  1445	  transition: background var(--transition-micro);
```

## frontend/src/pages/inventory/InventoryPage.tsx lines 468,500
```
   468	              <button
   469	                key={code}
   470	                className={activeTab === code ? "tab active" : "tab"}
   471	                onClick={() => { setActiveTab(code); setPage(1); }}
   472	              >{label}</button>
   473	            );
   474	          })}
   475	          {tcgTypes.filter((tt) => !["pokemon_booster_box", "one_piece", "dragon_ball"].includes(tt.code)).length > 0 && (
   476	            // ui-allow: TCG "other types" dropdown from main back-merge, ADR-143 D-1 (#2624)
   477	            <select
   478	              value={["pokemon_booster_box", "one_piece", "dragon_ball", "all"].includes(activeTab) ? "" : activeTab}
   479	              onChange={(e) => { if (e.target.value) { setActiveTab(e.target.value); setPage(1); } }}
   480	              aria-label={t("inventory.filter.otherTypes")}
   481	              style={{ fontSize: "var(--font-xs)", padding: "var(--space-1) var(--space-10px)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", background: "var(--bg-surface)" }}
   482	            >
   483	              <option value="">{t("inventory.filter.otherTypes")}</option>
   484	              {tcgTypes
   485	                .filter((tt) => !["pokemon_booster_box", "one_piece", "dragon_ball"].includes(tt.code))
   486	                .map((tt) => (
   487	                  <option key={tt.code} value={tt.code}>{tt.name_ja}</option>
   488	                ))}
   489	            </select>
   490	          )}
   491	        </div>
   492	        <p
   493	          data-testid="inventory-expiry-warning"
   494	          style={{ margin: 0, marginLeft: "auto", flexShrink: 0, fontSize: "var(--font-xs)", color: "var(--text-secondary)", whiteSpace: "nowrap" }}
   495	        >
   496	          {"※"}{t("inventory.expiryWarning")}
   497	        </p>
   498	      </div>
   499	
   500	      {/* 列を分割して表示。狭幅では横スクロール。フォントは少し大きめ。 */}
```

## frontend/src/components/field-size.css (full)
```
     1	/* 入力部品 寸法金型（field-size）— design-system/component-ssot/field-size/design.md §1
     2	   高さ3段(h-sm/md/lg)×幅3段(w-sm/md/lg)を独立クラスで付与。
     3	   既存の .comp-field 等には手を入れず、この金型クラスを足した要素だけに効く。
     4	   字体・角丸・枠線は既存トークン管轄（本金型は高さ・幅のみ担当）。 */
     5	
     6	/* --- 高さ3段（min-heightで統一・box-sizing:border-boxで枠込み固定）--- */
     7	.field-h-sm { min-height: var(--field-h-sm, 28px); box-sizing: border-box; }
     8	.field-h-md { min-height: var(--field-h-md, 36px); box-sizing: border-box; }
     9	.field-h-lg { min-height: var(--field-h-lg, 44px); box-sizing: border-box; }
    10	
    11	/* --- 幅3段（widthで固定。lgは伸びるが上限あり）--- */
    12	.field-w-sm { width: var(--field-w-sm, 160px); }
    13	.field-w-md { width: var(--field-w-md, 280px); }
    14	.field-w-lg { width: 100%; max-width: var(--field-w-lg-max, 480px); }
    15	
    16	/* 操作台の中で使うとき、金型付き入力は縦積みラッパーの癖を打ち消す
    17	   （.comp-field の flex-column/margin-bottom/width:100% を金型側で上書き）*/
    18	.content-toolbar .field-w-sm,
    19	.content-toolbar .field-w-md,
    20	.content-toolbar .field-w-lg { margin-bottom: 0; }
```

# Per-select detail for #6 #21 #22 #23 #27 #38 (verbatim from aw2b-plan.md)

### 6. pages/account-settings/PreferencesSection.tsx:38  (PreferencesSection)
- opening tag: `<select id="language-select" value={locale} onChange={(e) => changeLanguage(e.target.value)} className="account-settings-lang-select" >`
- className expr: `"account-settings-lang-select"` | inline style: (none)
- children kind: static-option (["option","option"]), disabledOption=false, onChange=`{(e) => changeLanguage(e.target.value)}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - `.account-settings-lang-select` @ frontend/src/pages/account-settings/account-settings.css:152 (0,1,0) state=base [definite]
    - LAYOUT: min-width: var(--size-lang-select-min) (L160)
    - DECORATION: padding: var(--space-1) var(--space-3) (L153); border: 1px solid var(--border) (L154); border-radius: var(--radius-sm) (L155); background: var(--bg-surface) (L156); color: var(--text-primary) (L157); font-size: var(--font-sm) (L158); cursor: pointer (L159)
  - `.account-settings-lang-select:focus` @ frontend/src/pages/account-settings/account-settings.css:163 (0,2,0) state=self:focus [definite]
    - DECORATION: outline: none (L164); border-color: var(--accent) (L165); box-shadow: var(--focus-ring-shadow) (L166)
- nearest mold size: **sm** (font-size token; font-size=var(--font-sm)); padding T/R/B/L = var(--space-1) / var(--space-3) / var(--space-1) / var(--space-3); width=unset -> fullWidth=false
- layout-only residue to keep as layoutClassName/className: min-width: var(--size-lang-select-min) [.account-settings-lang-select]
- before -> after vs SelectControl bare sm (6/13 equal):
  - padding-top: var(--space-1) -> var(--space-1)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-1) -> var(--space-1)  (same)
  - padding-left: var(--space-3) -> var(--space-2)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-sm) -> var(--font-sm)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> var(--comp-input-height-sm)
  - line-height: (unset: browser default) -> var(--line-height-base)


### 21. pages/goal-setting/GoalSettingPage.tsx:711  (GoalSettingPage)
- opening tag: `<select className="gs-select" value={selectedTeamId ?? ""} onChange={(e) => setSelectedTeamId(Number(e.target.value))} >`
- className expr: `"gs-select"` | inline style: (none)
- children kind: map (["map"]), disabledOption=false, onChange=`{(e) => setSelectedTeamId(Number(e.target.value))}`, reads=["target.value"], numericConverted=true
- applied CSS rules:
  - `.gs-select` @ frontend/src/pages/goal-setting/GoalSettingPage.css:555 (0,1,0) state=base [definite]
    - LAYOUT: flex: 1 (L556)
    - DECORATION: padding: var(--space-2) var(--space-3) (L557); border: 1px solid var(--border) (L558); border-radius: var(--radius-md) (L559); background: var(--bg-surface) (L560); color: var(--text-primary) (L561); font-size: var(--font-sm) (L562); cursor: pointer (L563)
- nearest mold size: **sm** (font-size token; font-size=var(--font-sm)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=unset -> fullWidth=false
- layout-only residue to keep as layoutClassName/className: flex: 1 [.gs-select]
- before -> after vs SelectControl bare sm (4/13 equal):
  - padding-top: var(--space-2) -> var(--space-1)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-1)
  - padding-left: var(--space-3) -> var(--space-2)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-md) -> var(--comp-input-radius)
  - font-size: var(--font-sm) -> var(--font-sm)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> var(--comp-input-height-sm)
  - line-height: (unset: browser default) -> var(--line-height-base)


### 22. pages/inbox/InboxConversationList.tsx:147  (InboxConversationList)
- opening tag: `<select value={pageIdFilter} onChange={(e) => onPageFilterChange(e.target.value)} aria-label="Filter by Page" className="inbox-page-filter-select" >`
- className expr: `"inbox-page-filter-select"` | inline style: (none)
- children kind: map (["option","map"]), disabledOption=false, onChange=`{(e) => onPageFilterChange(e.target.value)}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - `.inbox-page-filter-select` @ frontend/src/pages/inbox/InboxPage.css:398 (0,1,0) state=base [definite]
    - LAYOUT: width: 100% (L399)
    - DECORATION: padding: var(--space-1) var(--space-2) (L400); font-size: var(--font-xs) (L401); border-radius: var(--radius-xl) (L402); border: 1px solid var(--border) (L403); background: var(--bg-surface) (L404); color: var(--text-primary) (L405); font-family: inherit (L406); box-sizing: border-box (L407)
- nearest mold size: **sm** (font-size token; font-size=var(--font-xs)); padding T/R/B/L = var(--space-1) / var(--space-2) / var(--space-1) / var(--space-2); width=100% @frontend/src/pages/inbox/InboxPage.css:399 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.inbox-page-filter-select]
- before -> after vs SelectControl bare sm (6/13 equal):
  - padding-top: var(--space-1) -> var(--space-1)  (same)
  - padding-right: var(--space-2) -> var(--space-5)
  - padding-bottom: var(--space-1) -> var(--space-1)  (same)
  - padding-left: var(--space-2) -> var(--space-2)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-xl) -> var(--comp-input-radius)
  - font-size: var(--font-xs) -> var(--font-sm)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> var(--comp-input-height-sm)
  - line-height: (unset: browser default) -> var(--line-height-base)


### 23. pages/inbox/InboxSettingsModal.tsx:37  (InboxSettingsModal)
- opening tag: `<select className="inbox-settings-select" value={inboxSettings.defaultTab} onChange={(e) => updateInboxSetting("defaultTab", e.target.value as StatusTabKey)}>`
- className expr: `"inbox-settings-select"` | inline style: (none)
- children kind: static-option (["option","option","option","option","option","option"]), disabledOption=false, onChange=`{(e) => updateInboxSetting("defaultTab", e.target.value as StatusTabKey)}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - `.inbox-settings-select` @ frontend/src/pages/inbox/InboxPage.css:1424 (0,1,0) state=base [definite]
    - DECORATION: background: var(--bg-primary) (L1425); border: 1px solid var(--border) (L1425); border-radius: var(--radius-sm) (L1426); padding: var(--space-1) var(--space-2) (L1426); font-size: var(--font-sm) (L1427); color: var(--text-primary) (L1427); cursor: pointer (L1428)
- nearest mold size: **sm** (font-size token; font-size=var(--font-sm)); padding T/R/B/L = var(--space-1) / var(--space-2) / var(--space-1) / var(--space-2); width=unset -> fullWidth=false
- layout-only residue to keep as layoutClassName/className: (none)
- before -> after vs SelectControl bare sm (6/13 equal):
  - padding-top: var(--space-1) -> var(--space-1)  (same)
  - padding-right: var(--space-2) -> var(--space-5)
  - padding-bottom: var(--space-1) -> var(--space-1)  (same)
  - padding-left: var(--space-2) -> var(--space-2)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-sm) -> var(--font-sm)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-primary) -> var(--bg-surface)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> var(--comp-input-height-sm)
  - line-height: (unset: browser default) -> var(--line-height-base)


### 27. pages/inventory/InventoryPage.tsx:477  (InventoryPage)
- opening tag: `<select value={["pokemon_booster_box", "one_piece", "dragon_ball", "all"].includes(activeTab) ? "" : activeTab} onChange={(e) => { if (e.target.value) { setActiveTab(e.target.value); setPage(1); } }} aria-label={t("inventory.filter.otherTypes")} style={{ fontSize: "var(--font-xs)", padding: "var(--space-1) var(--space-10px)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", background: "var(--bg-surface)" }} >`
- className expr: (none) | inline style: `{{ fontSize: "var(--font-xs)", padding: "var(--space-1) var(--space-10px)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", background: "var(--bg-surface)" }}`
- children kind: map (["option","map"]), disabledOption=false, onChange=`{(e) => { if (e.target.value) { setActiveTab(e.target.value); setPage(1); } }}`, reads=["target.value"], numericConverted=false
- ui-allow (verbatim): `// ui-allow: TCG "other types" dropdown from main back-merge, ADR-143 D-1 (#2624)` (L476, preceding)
- applied CSS rules:
  - (none) -> unstyled
- inline style props: font-size: var(--font-xs) [decoration]; padding: var(--space-1) var(--space-10px) [decoration]; border: 1px solid var(--border) [decoration]; border-radius: var(--radius-sm) [decoration]; background: var(--bg-surface) [decoration]  | non-var() residue: [{"prop":"border","value":"1px solid var(--border)","residual":"1px solid"}]
- nearest mold size: **sm** (font-size token; font-size=var(--font-xs)); padding T/R/B/L = var(--space-1) / var(--space-10px) / var(--space-1) / var(--space-10px); width=unset -> fullWidth=false
- layout-only residue to keep as layoutClassName/className: (none)
- before -> after vs SelectControl bare sm (4/13 equal):
  - padding-top: var(--space-1) -> var(--space-1)  (same)
  - padding-right: var(--space-10px) -> var(--space-5)
  - padding-bottom: var(--space-1) -> var(--space-1)  (same)
  - padding-left: var(--space-10px) -> var(--space-2)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-xs) -> var(--font-sm)
  - color: (unset: browser default) -> var(--text-primary)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> var(--comp-input-height-sm)
  - line-height: (unset: browser default) -> var(--line-height-base)


### 38. pages/status-master/StatusMasterPage.tsx:260  (renderFormFields)
- opening tag: `<select className="field field-h-md" value={form.match_type} onChange={e => setForm({ ...form, match_type: e.target.value })} required >`
- className expr: `"field field-h-md"` | inline style: (none)
- children kind: map (["map"]), disabledOption=false, onChange=`{e => setForm({ ...form, match_type: e.target.value })}`, reads=["target.value"], numericConverted=false
- ui-allow (verbatim): `{/* ui-allow: enum select for status match_type; no SelectControl variant with option map (#3594) */}` (L259, preceding)
- applied CSS rules:
  - `.field-h-md` @ frontend/src/components/field-size.css:8 (0,1,0) state=base [definite]
    - DIMENSION owned by mold: min-height: var(--field-h-md, 36px) (L8)
    - DECORATION: box-sizing: border-box (L8)
  - `.form-group select` @ frontend/src/components.css:19 (0,1,1) state=base [definite]
    - LAYOUT: width: 100% (L22)
    - DECORATION: padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
  - `.form-group select:focus` @ frontend/src/components.css:32 (0,2,1) state=self:focus [definite]
    - DECORATION: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/components.css:22 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-group select]
- before -> after vs SelectControl bare md (7/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: var(--field-h-md, 36px) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)


# Definite existing mold usages (8): what changes when bare-tag rules stop applying

- pages/company-detail/CompanyAddressModal.tsx:84 `<Select>` size=md fullWidth=false appearance=field(Select) indicator=default variant=standard className=- | **definite**
  - rules: company-forms.css:100 .form-grid > .form-row select [definite] ; company-forms.css:120 .form-grid > .form-row select:focus [definite] ; company-forms.css:156 .modal-content-wide .form-row select [definite] ; company-forms.css:181 .modal-content-wide .form-row select:focus [definite]
  - [base] padding-right: var(--space-3) (@company-forms.css:162) -> var(--space-5) (@components/FormField.css:79)
  - [base] border: 1px solid var(--border-strong) (@company-forms.css:163) -> 1px solid var(--border) (@components/FormField.css:53)
  - [base] border-radius: var(--radius-md) (@company-forms.css:164) -> var(--comp-input-radius) (@components/FormField.css:54)
  - [base] background-image: none (@company-forms.css:166) -> arrow-svg(url data:image/svg+xml chevron #888) (@components/FormField.css:80)

- pages/note-master/NoteMasterPage.tsx:290 `<Select>` size=md fullWidth=true appearance=field(Select) indicator=default variant=standard className=- | **definite**
  - rules: components.css:19 .form-group select [definite] ; components.css:32 .form-group select:focus [definite]
  - [base] padding-right: var(--space-3) (@components.css:23) -> var(--space-5) (@components/FormField.css:79)
  - [base] border-radius: var(--radius-sm) (@components.css:25) -> var(--comp-input-radius) (@components/FormField.css:54)
  - [base] background-image: none (@components.css:28) -> arrow-svg(url data:image/svg+xml chevron #888) (@components/FormField.css:80)

- pages/super-admin/components/NoteMasterPanel.tsx:278 `<Select>` size=md fullWidth=true appearance=field(Select) indicator=default variant=standard className=- | **definite**
  - rules: components.css:19 .form-group select [definite] ; components.css:32 .form-group select:focus [definite]
  - [base] padding-right: var(--space-3) (@components.css:23) -> var(--space-5) (@components/FormField.css:79)
  - [base] border-radius: var(--radius-sm) (@components.css:25) -> var(--comp-input-radius) (@components/FormField.css:54)
  - [base] background-image: none (@components.css:28) -> arrow-svg(url data:image/svg+xml chevron #888) (@components/FormField.css:80)

- pages/super-admin/components/ProductFormatsMasterPanel.tsx:279 `<SelectControl>` size=md fullWidth=true appearance=bare indicator=default variant=standard className=- | **definite**
  - rules: components.css:19 .form-group select [definite] ; components.css:32 .form-group select:focus [definite]
  - [base] padding-right: var(--space-3) (@components.css:23) -> var(--space-5) (@components/FormField.css:79)
  - [base] border-radius: var(--radius-sm) (@components.css:25) -> var(--comp-input-radius) (@components/FormField.css:54)
  - [base] background-image: none (@components.css:28) -> arrow-svg(url data:image/svg+xml chevron #888) (@components/FormField.css:80)

- pages/super-admin/components/ProductFormatsMasterPanel.tsx:293 `<SelectControl>` size=md fullWidth=true appearance=bare indicator=default variant=standard className=- | **definite**
  - rules: components.css:19 .form-group select [definite] ; components.css:32 .form-group select:focus [definite]
  - [base] padding-right: var(--space-3) (@components.css:23) -> var(--space-5) (@components/FormField.css:79)
  - [base] border-radius: var(--radius-sm) (@components.css:25) -> var(--comp-input-radius) (@components/FormField.css:54)
  - [base] background-image: none (@components.css:28) -> arrow-svg(url data:image/svg+xml chevron #888) (@components/FormField.css:80)

- pages/super-admin/components/ProductLinesMasterPanel.tsx:278 `<SelectControl>` size=md fullWidth=true appearance=bare indicator=default variant=standard className=- | **definite**
  - rules: components.css:19 .form-group select [definite] ; components.css:32 .form-group select:focus [definite]
  - [base] padding-right: var(--space-3) (@components.css:23) -> var(--space-5) (@components/FormField.css:79)
  - [base] border-radius: var(--radius-sm) (@components.css:25) -> var(--comp-input-radius) (@components/FormField.css:54)
  - [base] background-image: none (@components.css:28) -> arrow-svg(url data:image/svg+xml chevron #888) (@components/FormField.css:80)

- pages/super-admin/components/ProductLinesMasterPanel.tsx:292 `<SelectControl>` size=md fullWidth=true appearance=bare indicator=default variant=standard className=- | **definite**
  - rules: components.css:19 .form-group select [definite] ; components.css:32 .form-group select:focus [definite]
  - [base] padding-right: var(--space-3) (@components.css:23) -> var(--space-5) (@components/FormField.css:79)
  - [base] border-radius: var(--radius-sm) (@components.css:25) -> var(--comp-input-radius) (@components/FormField.css:54)
  - [base] background-image: none (@components.css:28) -> arrow-svg(url data:image/svg+xml chevron #888) (@components/FormField.css:80)

- pages/super-admin/components/TypeMasterPanel.tsx:253 `<SelectControl>` size=md fullWidth=true appearance=bare indicator=default variant=standard className=- | **definite**
  - rules: components.css:19 .form-group select [definite] ; components.css:32 .form-group select:focus [definite]
  - [base] padding-right: var(--space-3) (@components.css:23) -> var(--space-5) (@components/FormField.css:79)
  - [base] border-radius: var(--radius-sm) (@components.css:25) -> var(--comp-input-radius) (@components/FormField.css:54)
  - [base] background-image: none (@components.css:28) -> arrow-svg(url data:image/svg+xml chevron #888) (@components/FormField.css:80)

