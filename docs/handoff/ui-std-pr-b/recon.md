# recon — UI標準化 PR-B (Company系3ファイル)

**仕事名**: UI標準化 PR-B  
**日付**: 2026-06-14  
**対象ADR**: ADR-067  
**担当**: Hikky-dev

---

## file:line 引用表

### MergeCompanyModal.tsx

| 引用先 | 確認内容 |
|--------|---------|
| `frontend/src/components/MergeCompanyModal.tsx:22` | Button import 追加 |
| `frontend/src/components/MergeCompanyModal.tsx:23` | TextField import 追加 |
| `frontend/src/components/MergeCompanyModal.tsx:24` | Textarea import 追加 |
| `frontend/src/components/MergeCompanyModal.tsx:158` | 検索フィールド TextField 置換 |
| `frontend/src/components/MergeCompanyModal.tsx:220` | radio input 残置（専用コンポーネント未実装） |
| `frontend/src/components/MergeCompanyModal.tsx:246` | reason Textarea 置換 |
| `frontend/src/components/MergeCompanyModal.tsx:256` | cancel Button(secondary) 置換 |
| `frontend/src/components/MergeCompanyModal.tsx:261` | next Button(primary) 置換 |
| `frontend/src/components/MergeCompanyModal.tsx:320` | back Button(secondary) 置換 |
| `frontend/src/components/MergeCompanyModal.tsx:327` | merge Button(danger) 置換 |

### CompanyAddressModal.tsx

| 引用先 | 確認内容 |
|--------|---------|
| `frontend/src/pages/company-detail/CompanyAddressModal.tsx:11` | Button import 追加 |
| `frontend/src/pages/company-detail/CompanyAddressModal.tsx:12` | TextField import 追加 |
| `frontend/src/pages/company-detail/CompanyAddressModal.tsx:13` | Select import 追加 |
| `frontend/src/pages/company-detail/CompanyAddressModal.tsx:84` | billing/delivery Select 置換 |
| `frontend/src/pages/company-detail/CompanyAddressModal.tsx:96` | branch_name TextField 置換 |
| `frontend/src/pages/company-detail/CompanyAddressModal.tsx:100` | name TextField 置換 |
| `frontend/src/pages/company-detail/CompanyAddressModal.tsx:104` | email TextField 置換 |
| `frontend/src/pages/company-detail/CompanyAddressModal.tsx:108` | telephone TextField 置換（error prop統合） |
| `frontend/src/pages/company-detail/CompanyAddressModal.tsx:113` | tax_id TextField 置換 |
| `frontend/src/pages/company-detail/CompanyAddressModal.tsx:117` | address_line_1 TextField 置換 |
| `frontend/src/pages/company-detail/CompanyAddressModal.tsx:121` | address_line_2 TextField 置換 |
| `frontend/src/pages/company-detail/CompanyAddressModal.tsx:125` | address_line_3 TextField 置換 |
| `frontend/src/pages/company-detail/CompanyAddressModal.tsx:129` | city TextField 置換 |
| `frontend/src/pages/company-detail/CompanyAddressModal.tsx:133` | state TextField 置換 |
| `frontend/src/pages/company-detail/CompanyAddressModal.tsx:137` | zip TextField 置換 |
| `frontend/src/pages/company-detail/CompanyAddressModal.tsx:141` | country_code TextField 置換 |
| `frontend/src/pages/company-detail/CompanyAddressModal.tsx:145` | checkbox 残置（専用コンポーネント未実装） |
| `frontend/src/pages/company-detail/CompanyAddressModal.tsx:153` | cancel Button(secondary) 置換 |
| `frontend/src/pages/company-detail/CompanyAddressModal.tsx:154` | save Button(primary) 置換 |

### CompanyDetailPage.tsx

| 引用先 | 確認内容 |
|--------|---------|
| `frontend/src/pages/company-detail/CompanyDetailPage.tsx:16` | Button import 追加 |
| `frontend/src/pages/company-detail/CompanyDetailPage.tsx:76` | back Button(secondary) 置換（no-data状態） |
| `frontend/src/pages/company-detail/CompanyDetailPage.tsx:149` | back Button(sm/secondary) 置換（ヘッダー） |
| `frontend/src/pages/company-detail/CompanyDetailPage.tsx:155` | reg link Button(sm/primary) 置換 |
| `frontend/src/pages/company-detail/CompanyDetailPage.tsx:165` | addr link Button(sm/secondary) 置換 |
| `frontend/src/pages/company-detail/CompanyDetailPage.tsx:173` | billing link Button(sm/secondary) 置換 |
| `frontend/src/pages/company-detail/CompanyDetailPage.tsx:192` | reg copy Button(sm/secondary) 置換 |
| `frontend/src/pages/company-detail/CompanyDetailPage.tsx:201` | addr copy Button(sm/secondary) 置換 |
| `frontend/src/pages/company-detail/CompanyDetailPage.tsx:210` | billing copy Button(sm/secondary) 置換 |
| `frontend/src/pages/company-detail/CompanyDetailPage.tsx:220` | basic タブ Button(ghost) 置換 |
| `frontend/src/pages/company-detail/CompanyDetailPage.tsx:223` | addresses タブ Button(ghost) 置換 |
| `frontend/src/pages/company-detail/CompanyDetailPage.tsx:226` | contacts タブ Button(ghost) 置換 |
| `frontend/src/pages/company-detail/CompanyDetailPage.tsx:229` | channels タブ Button(ghost) 置換 |
| `frontend/src/pages/company-detail/CompanyDetailPage.tsx:232` | discord タブ Button(ghost) 置換 |
| `frontend/src/pages/company-detail/CompanyDetailPage.tsx:235` | convHistory タブ Button(ghost) 置換 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | checkbox/radio の標準コンポーネントがあるか | 既存 PR-A の方針を確認 | ✅ 解消済み（未実装のため残置） |

**未解決ゼロ確認**: 全て解消済み
