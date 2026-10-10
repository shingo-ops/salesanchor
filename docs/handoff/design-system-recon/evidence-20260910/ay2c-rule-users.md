# AY-2c 削除対象規則（company-forms.css :100 / :147-148）が当たる生 input の再列挙

実行: 削除前の worktree（HEAD 1ce66d21f）で tools/targets.cjs（祖先連鎖・部品経由の再帰たどり）。結果は調査時（c6c4fdc51）と位置まで一致（54 行、うち基本規則に当たる 49）。

- 基本規則に当たる生 input: 49 件（omitted 44・email 2・number 2・text 1）。移管対象 49 件以外の生 input は 0。UNDETERMINED は 0。
- checkbox 5 件は :not で基本規則から除外（focus 規則のみ当たる）。

| file | line | type | 当たる規則 |
|---|---|---|---|
| frontend/src/components/ContactChannelForm.tsx | 227 | checkbox | none(:not除外) |
| frontend/src/components/MergeLeadModal.tsx | 146 | text | R2(:147) |
| frontend/src/pages/companies/CompaniesPage.tsx | 452 | omitted | R1+R2 |
| frontend/src/pages/companies/CompaniesPage.tsx | 456 | omitted | R1+R2 |
| frontend/src/pages/companies/CompaniesPage.tsx | 460 | omitted | R1+R2 |
| frontend/src/pages/companies/CompaniesPage.tsx | 464 | omitted | R1+R2 |
| frontend/src/pages/companies/CompaniesPage.tsx | 468 | omitted | R1+R2 |
| frontend/src/pages/companies/CompaniesPage.tsx | 472 | omitted | R1+R2 |
| frontend/src/pages/companies/CompaniesPage.tsx | 476 | omitted | R1+R2 |
| frontend/src/pages/companies/CompaniesPage.tsx | 480 | number | R1+R2 |
| frontend/src/pages/companies/CompaniesPage.tsx | 484 | omitted | R1+R2 |
| frontend/src/pages/companies/CompaniesPage.tsx | 488 | omitted | R1+R2 |
| frontend/src/pages/companies/CompaniesPage.tsx | 492 | omitted | R1+R2 |
| frontend/src/pages/companies/CompaniesPage.tsx | 496 | omitted | R1+R2 |
| frontend/src/pages/companies/CompaniesPage.tsx | 504 | omitted | R1+R2 |
| frontend/src/pages/companies/CompaniesPage.tsx | 533 | omitted | R1+R2 |
| frontend/src/pages/companies/CompaniesPage.tsx | 535 | omitted | R1+R2 |
| frontend/src/pages/companies/CompaniesPage.tsx | 536 | email | R1+R2 |
| frontend/src/pages/companies/CompaniesPage.tsx | 539 | omitted | R1+R2 |
| frontend/src/pages/companies/CompaniesPage.tsx | 542 | omitted | R1+R2 |
| frontend/src/pages/companies/CompaniesPage.tsx | 543 | omitted | R1+R2 |
| frontend/src/pages/companies/CompaniesPage.tsx | 544 | omitted | R1+R2 |
| frontend/src/pages/companies/CompaniesPage.tsx | 545 | omitted | R1+R2 |
| frontend/src/pages/companies/CompaniesPage.tsx | 546 | omitted | R1+R2 |
| frontend/src/pages/companies/CompaniesPage.tsx | 547 | omitted | R1+R2 |
| frontend/src/pages/companies/CompaniesPage.tsx | 548 | omitted | R1+R2 |
| frontend/src/pages/company-detail/CompanyAddressModal.tsx | 147 | checkbox | none(:not除外) |
| frontend/src/pages/company-detail/CompanyBasicTab.tsx | 38 | omitted | R1(:100) |
| frontend/src/pages/company-detail/CompanyBasicTab.tsx | 42 | omitted | R1(:100) |
| frontend/src/pages/company-detail/CompanyBasicTab.tsx | 46 | omitted | R1(:100) |
| frontend/src/pages/company-detail/CompanyBasicTab.tsx | 50 | omitted | R1(:100) |
| frontend/src/pages/company-detail/CompanyBasicTab.tsx | 54 | omitted | R1(:100) |
| frontend/src/pages/company-detail/CompanyBasicTab.tsx | 58 | omitted | R1(:100) |
| frontend/src/pages/company-detail/CompanyBasicTab.tsx | 62 | number | R1(:100) |
| frontend/src/pages/company-detail/CompanyBasicTab.tsx | 66 | omitted | R1(:100) |
| frontend/src/pages/company-detail/CompanyBasicTab.tsx | 70 | omitted | R1(:100) |
| frontend/src/pages/company-detail/CompanyBasicTab.tsx | 74 | omitted | R1(:100) |
| frontend/src/pages/company-detail/CompanyBasicTab.tsx | 78 | omitted | R1(:100) |
| frontend/src/pages/company-detail/CompanyChannelsTab.tsx | 32 | omitted | R1(:100) |
| frontend/src/pages/company-detail/CompanyContactsTab.tsx | 206 | checkbox | none(:not除外) |
| frontend/src/pages/company-detail/CompanyDiscordTab.tsx | 42 | checkbox | none(:not除外) |
| frontend/src/pages/company-detail/CompanyDiscordTab.tsx | 53 | omitted | R1(:100) |
| frontend/src/pages/company-detail/CompanyDiscordTab.tsx | 62 | omitted | R1(:100) |
| frontend/src/pages/company-detail/CompanyDiscordTab.tsx | 71 | omitted | R1(:100) |
| frontend/src/pages/company-detail/CompanyDiscordTab.tsx | 80 | omitted | R1(:100) |
| frontend/src/pages/contacts/ContactsPage.tsx | 306 | omitted | R1+R2 |
| frontend/src/pages/contacts/ContactsPage.tsx | 316 | omitted | R1+R2 |
| frontend/src/pages/contacts/ContactsPage.tsx | 319 | omitted | R1+R2 |
| frontend/src/pages/contacts/ContactsPage.tsx | 322 | omitted | R1+R2 |
| frontend/src/pages/contacts/ContactsPage.tsx | 325 | omitted | R1+R2 |
| frontend/src/pages/contacts/ContactsPage.tsx | 328 | omitted | R1+R2 |
| frontend/src/pages/contacts/ContactsPage.tsx | 332 | checkbox | none(:not除外) |
| frontend/src/pages/contacts/ContactsPage.tsx | 337 | email | R1+R2 |
| frontend/src/pages/contacts/ContactsPage.tsx | 340 | omitted | R1+R2 |
