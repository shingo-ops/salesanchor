# 旧rawボタン最新監査

固定SHA: 7606ca9a041e315b81040373e8f4ddebbc562133。git show追跡原文のみ、製品/正式文書変更なし。raw-audit.cjs → raw-audit-enrich.py → raw-audit-finalize.pyで再現。

## 件数と分類

{
  "sha": "7606ca9a041e315b81040373e8f4ddebbc562133",
  "count": 352,
  "files": 89,
  "tags": {
    "button": 344,
    "Link": 1,
    "a": 7
  },
  "types": {
    "\"button\"": 127,
    "\"submit\"": 61,
    "omitted": 164
  },
  "groups": {
    "components": 21,
    "features/tcg-distribution": 14,
    "pages/account-settings": 2,
    "pages/admin": 8,
    "pages/archives": 1,
    "pages/badges": 3,
    "pages/bots": 11,
    "pages/buddy": 4,
    "pages/channels": 7,
    "pages/commission-settings": 1,
    "pages/commissions": 1,
    "pages/companies": 7,
    "pages/company-detail": 10,
    "pages/contacts": 10,
    "pages/design-system": 6,
    "pages/erp": 1,
    "pages/goal-setting": 2,
    "pages/inbox": 11,
    "pages/integrations": 28,
    "pages/inventory": 9,
    "pages/invoice-create": 8,
    "pages/invoice-detail": 11,
    "pages/invoices": 2,
    "pages/leads": 12,
    "pages/login": 2,
    "pages/notifications": 4,
    "pages/orders": 11,
    "pages/products": 10,
    "pages/purchase-orders": 11,
    "pages/quote-create": 5,
    "pages/quote-detail": 6,
    "pages/quotes": 3,
    "pages/register": 6,
    "pages/roles": 10,
    "pages/sales": 1,
    "pages/schedule": 1,
    "pages/shifts": 4,
    "pages/staff-reports": 3,
    "pages/staff": 9,
    "pages/super-admin": 53,
    "pages/suppliers": 11,
    "pages/teams": 12
  },
  "attributes": {
    "type": 188,
    "ref": 0,
    "form": 4,
    "name": 0,
    "value": 0,
    "disabled": 107,
    "aria-label": 15,
    "aria-pressed": 3,
    "aria-expanded": 1,
    "style": 23,
    "className": 352,
    "spread": 0,
    "onClick": 278,
    "onChange": 0,
    "onKeyDown": 0,
    "onMouseDown": 0,
    "onMouseEnter": 0,
    "onMouseLeave": 0
  },
  "inlineStopPropagation": 19,
  "selectorKinds": {
    "btn-prefix": 332,
    "dedicated-btn-substring": 20
  },
  "classifications": {
    "Button": 236,
    "TableSortButton": 1,
    "PaginationAction(Button)": 10,
    "Button(type=submit)": 61,
    "NavigationAction(native button)": 18,
    "link": 8,
    "CatalogDemo": 6,
    "UploadAction(Button)": 2,
    "FilterDisclosureButton": 1,
    "ModeSelector(Button active)": 2,
    "ReorderModeButton": 1,
    "NavigateWithSelection(Button)": 2,
    "StatusFilterButton": 1,
    "Button(iconOnly,danger)": 1,
    "ExistingRoleTab": 1,
    "DisclosureAction(Button)": 1
  },
  "allEventAttributes": {
    "onClick": 278
  },
  "allAriaAttributes": {
    "aria-label": 15,
    "aria-expanded": 1,
    "aria-pressed": 3,
    "aria-selected": 1
  },
  "buttonOnlyTypes": {
    "\"button\"": 127,
    "\"submit\"": 61,
    "omitted": 156
  },
  "autoFocus": 1,
  "limitations": [
    "352 preserves previous broad regex cohort; 332 btn-prefix versus 20 dedicated btn-substring, not 352 global CSS consumers",
    "JSX call-site/static counts, not rendered instances",
    "inline stopPropagation19 excludes uninspected named-handler internals",
    "Existing BSA matches require same file and whitespace-normalized entire JSX; not an assumption based on old line number",
    "Classification describes UI trigger; business function internal exhaustive tests and browser CSS precedence not performed",
    "design-system catalog6 is included to match prior scope; stories/test/spec/design-preview excluded"
  ]
}

## 最初の小口候補

推奨: ConfirmModalの2個で機能/autoFocus/危険分岐を検証、または同じ条件で以下6部品16個を一便に束ねる。既存BSAの全JSX一致、追加class/style/ref/spread0なので新しい装飾判断を増やさずに移行できる。単独btn-sm2個は既存設計どおりsecondary/sm。危険分岐、submit、form、disabled、type省略、callback本文、翻訳文言は保持する。

### frontend/src/components/ConfirmModal.tsx (2)

- :33 BSA-005 {"variant": "secondary", "size": "md"}; {"type": "\"button\"", "className": "\"btn-secondary\"", "onClick": "{onCancel}"}
- :34 BSA-006 {"variant": "danger ? danger : primary（既存danger propの分岐保持）", "size": "md"}; {"type": "\"button\"", "className": "{danger ? \"btn-danger\" : \"btn-primary\"}", "onClick": "{onConfirm}", "autoFocus": true}
### frontend/src/components/CommissionPanel.tsx (3)

- :227 BSA-002 {"variant": "secondary", "size": "sm"}; {"className": "\"btn-sm\"", "type": "\"button\"", "data-testid": "{`commission-unassign-${key}`}", "disabled": "{savingRole === key}", "onClick": "{() => handleUnassign(key)}"}
- :254 BSA-003 {"variant": "primary", "size": "md"}; {"type": "\"button\"", "className": "\"btn-primary\"", "onClick": "{handleRecalc}", "disabled": "{recalcing}", "data-testid": "\"commission-recalc\""}
- :263 BSA-004 {"variant": "secondary", "size": "md"}; {"type": "\"button\"", "className": "\"btn-secondary\"", "onClick": "{onClose}"}
### frontend/src/components/PriorityScoreOverride.tsx (3)

- :66 BSA-027 {"variant": "secondary", "size": "sm"}; {"className": "\"btn-sm\"", "onClick": "{() => setOpen(true)}"}
- :101 BSA-028 {"variant": "secondary", "size": "md"}; {"type": "\"button\"", "className": "\"btn-secondary\"", "onClick": "{() => setOpen(false)}"}
- :108 BSA-029 {"variant": "primary", "size": "md"}; {"type": "\"submit\"", "className": "\"btn-primary\"", "disabled": "{saving}"}
### frontend/src/components/OrderFinancialPanel.tsx (2)

- :276 BSA-025 {"variant": "secondary", "size": "md"}; {"type": "\"button\"", "className": "\"btn-secondary\"", "onClick": "{onClose}", "disabled": "{saving}"}
- :284 BSA-026 {"variant": "primary", "size": "md"}; {"type": "\"submit\"", "className": "\"btn-primary\"", "disabled": "{saving}", "data-testid": "\"fin-save\""}
### frontend/src/components/PurchaseDetailPanel.tsx (3)

- :264 BSA-030 {"variant": "secondary", "size": "md"}; {"type": "\"button\"", "className": "\"btn-secondary\"", "onClick": "{handleConfirm}", "disabled": "{!existing || confirming}", "data-testid": "\"pur-confirm\"", "title": "{\n          existing\n            ? t(\"purchase.confirmTitle\")\n            : t(\"purchase.confirmTitleDisabled\")\n        }"}
- :278 BSA-031 {"variant": "secondary", "size": "md"}; {"type": "\"button\"", "className": "\"btn-secondary\"", "onClick": "{onClose}", "disabled": "{saving}"}
- :286 BSA-032 {"variant": "primary", "size": "md"}; {"form": "\"purchase-detail-form\"", "type": "\"submit\"", "className": "\"btn-primary\"", "disabled": "{saving}", "data-testid": "\"pur-save\""}
### frontend/src/components/ShippingDetailPanel.tsx (3)

- :337 BSA-033 {"variant": "secondary", "size": "md"}; {"type": "\"button\"", "className": "\"btn-secondary\"", "onClick": "{handleDownloadCsv}", "disabled": "{!existing || downloading}", "data-testid": "\"ship-download-csv\"", "title": "{\n          existing\n            ? t(\"shipping.downloadCsvTitle\")\n            : t(\"shipping.downloadCsvTitleDisabled\")\n        }"}
- :351 BSA-034 {"variant": "secondary", "size": "md"}; {"type": "\"button\"", "className": "\"btn-secondary\"", "onClick": "{onClose}", "disabled": "{saving}"}
- :359 BSA-035 {"variant": "primary", "size": "md"}; {"form": "\"shipping-detail-form\"", "type": "\"submit\"", "className": "\"btn-primary\"", "disabled": "{saving}", "data-testid": "\"ship-save\""}

ConfirmModal:34のautoFocusを保持。PriorityScoreOverride:66のtype省略をbuttonへ変えない。PurchaseDetailPanel:286とShippingDetailPanel:359は外部form ID保持必須。callback処理は移管しない。

## 今回分離する操作

リンク8はa7/Link1のhref/to/target/relを保持するButtonLink便へ。DataTable:197はソート専用、:286/:298はページ操作だが英語aria-label直書きあり次便候補から分離。InventoryPage:400のfilterEnabledとshowFilterPanelは異なる状態で、pressed/expandedを統合しない。ProductsPage:234のreorder、QuotesPage:100のstatusFilter、ProductMastersTab:332の既存role=tab/aria-selected、InvoiceCreatePage:233/240の2モード、TcgSeriesTab:197の開閉は通常単発操作と別契約。send-guard3は翻訳/そのまま送信/取消の順序を保持。専用dist15、modal-icon1、table-sort1もグローバルbtnクラス使用と区別する。

## 検証条件

6部品16個のクリック1回/無効0、submitに既存formが1回応答、外部form関連付け、ConfirmModalのautoFocusとdanger分岐、旧type省略、title/data属性・翻訳済みchildren保持。CSSは共通Button外観へ意図した統一。旧未移行rawと専用部品の表示差分0を対照する。業務APIを実行する実データ試験はここでは行っていない。
