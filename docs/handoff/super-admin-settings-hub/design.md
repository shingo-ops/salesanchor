# design: 運営のメニューを「利用者管理」「全体設定」へ組み替える

- 状態: 設計案作成済み・同じ AI による自己審査済み（独立した第二者の審査ではない）・PO の方向の承認あり（2026-11-11「1、LINE解析に入っているマスタも全体設定に移動させてくれ」）・実装は本 PR で行う
- 根拠: [recon.md](./recon.md)。対象 ADR: ADR-149（SubMenu）・ADR-087・ADR-067・ADR-144・ADR-027・ADR-1061 決定10
- 区分: 画面だけ（frontend）。backend・DB・CI の設定・本番の手順は触らない

## 1. 目的

運営の人が、左のメニューで「人のこと」と「全体の設定」を迷わず開けるようにする。LINE解析の画面からマスタを外し、解析の仕事だけを残す。

## 2. 対象と対象外

対象:
- 左メニュー（PC・スマホ）の運営の行: LINE解析・買取相場・利用者管理・全体設定（スマホは今ある「解析の抽出ルール」も残す）
- 新しい「全体設定」画面（画面の中に小さなメニュー）: 金額の設定（為替レート管理・税率・商材とプラン）とマスタ管理（11件）
- 「利用者管理」: 閲覧者の画面とログインの許可待ちの画面に同じ小さなメニュー
- LINE解析からマスタ管理の11件を外す。古い URL は新しい場所へ転送

対象外:
- 税率と商材とプランの中身（次の便。この便は「準備中」）
- 状態ルール（conditions-master）と単位ルール（unit-master）。名前が「ルール」で「ルール管理」の組にあるため、LINE解析に残す（PO への報告で読みを伝える）
- 延長ボタンを契約手続き中にも出す件（別の便）
- 管理センター（会社ごとの画面）

## 3. 変更前と変更後

### 3-1. 道（URL）

| 画面 | 変更前 | 変更後 |
|---|---|---|
| 全体設定 | 無し | `/super-admin/settings`（開くと為替へ） |
| 為替レート管理 | `/super-admin/fx-rate` | `/super-admin/settings/fx-rate` |
| 税率 | 無し | `/super-admin/settings/tax-rates`（準備中） |
| 商材とプラン | 無し | `/super-admin/settings/sa-products`（準備中） |
| マスタ11件 | `/super-admin/analysis-rules?section=<key>` | `/super-admin/settings/masters/<key>`（key はそのまま） |
| 利用者管理 | 無し | `/super-admin/users`（開くと閲覧者へ） |
| 閲覧者 | `/super-admin/viewers` | `/super-admin/users/viewers` |
| ログインの許可待ち | `/super-admin/login-requests` | `/super-admin/users/login-requests` |
| テンプレート | `/super-admin/viewer-templates` | `/super-admin/users/viewer-templates` |

古い4つの道（fx-rate・viewers・login-requests・viewer-templates）は `frontend/src/pages/super-admin/legacyPageRedirects.ts` に足して転送する。既存の2件（tcg-product-master・supplier-master）の行き先も新しい道へ直す。`?section=<マスタ11件>` で LINE解析を開いたら、新しい道へ置き換えで転送する。

### 3-2. 正本（1か所）

新しいファイル `frontend/src/pages/super-admin/settings/settingsNav.ts` に、全体設定の項目を1か所で持つ:
- `SETTINGS_MONEY_ITEMS`: `{ key: "fx-rate", labelKey: "nav.superAdminFxRate" }`・`{ key: "tax-rates", labelKey: "nav.superAdminTaxRates" }`・`{ key: "sa-products", labelKey: "nav.superAdminSaProducts" }`
- `SETTINGS_MASTER_ITEMS`: 11件 `{ key, labelKey }`。key は今の section の名前、labelKey は今の `analysisRules.sidebar.*`（新しい言葉を作らない）。並びは今の LINE解析と同じ
- `settingsMasterPath(key)` → `/super-admin/settings/masters/${key}`、`isSettingsMasterKey(key)`

部品の対応（key → Panel）は `frontend/src/pages/super-admin/settings/SettingsMasterPage.tsx` の1つの表に持つ。App.tsx の Route・全体設定の小さなメニュー・LINE解析の転送・転送表・取込画面の戻り先は、すべてこの正本を読む。

### 3-3. 新しい画面

- `frontend/src/pages/super-admin/settings/SettingsHubPage.tsx`: 管理センターと同じ形。`useSuperAdmin` で守り、読み込み中は `LoadingBlock`、運営でなければ `superAdmin.accessDenied` を出して Outlet を出さない。`<PageLayout navKey="nav.superAdminSettings" noScroll><div className="hub-shell"><SubMenu variant="grouped" className="hub-subnav" groups activeKey/><div className="hub-content"><Outlet/></div></div></PageLayout>`。組の題: 金額の設定 `superAdmin.settings.groupMoney`・マスタ管理 `analysisRules.sidebar.groupMasterManagement`。項目の `to` は相対（`fx-rate`・`masters/product-master` など）。activeKey は管理センターと同じく pathname の末尾で決める
- `frontend/src/pages/super-admin/settings/SettingsMasterPage.tsx`: `useParams` の key を表で引き、`<PageLayout titleText={t(labelKey)}><Panel/></PageLayout>`。表に無い key は `Navigate to="/super-admin/settings" replace`
- 税率・商材とプラン: 既存の `ComingSoonPage`（title は nav の言葉、description は `superAdmin.settings.comingSoon`）
- `frontend/src/pages/super-admin/users/UserManagementSubMenu.tsx`: 閲覧者の画面とログインの画面が共有する SubMenu（`variant="grouped"`・`className="hub-subnav"`）。1つ目の組は題「閲覧者」（すべて＋状態ごと）。2つ目の組は題を付けず、ログインの許可待ちの1項目だけ（`to: "/super-admin/users/login-requests"`）。閲覧者の画面では今の数と `?status=` の切り替えをそのまま渡す。ログインの画面では数を出さず、状態を押すと `/super-admin/users/viewers?status=<key>`（すべては `?` 無し）へ移る
- `LoginRequestsPage` は中身を `hub-shell`（小さなメニュー＋`hub-content`）で包む。`ViewerAccountsPage` は今の flat の SubMenu を共有の部品に置き換える
- 新しい色・大きさの直書きは無し。部品は SubMenu・PageLayout・ComingSoonPage・既存の hub-shell の class だけ（ADR-144）

### 3-4. LINE解析

- `frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx`: マスタ管理の組（`:106-121` あたりの見出しと11行）を消す。型 `AnalysisSection` から11件を外す
- `frontend/src/pages/super-admin/AnalysisRulesPage.tsx`: 11件の Panel の import と描き分けを消す。最初の `?section=` が `isSettingsMasterKey` なら `<Navigate to={settingsMasterPath(key)} replace />`。`handleSectionChange` は `isSettingsMasterKey` なら `navigate(settingsMasterPath(key))`。ダッシュボードの `onNavigate` を `handleSectionChange` に変える（押すとマスタの新しい場所へ移る）
- AnalysisDashboardPanel・LineWorkflowGuidePanel の中の key の文字は変えない（受け手が転送する）

### 3-5. 左メニュー

- `frontend/src/components/DesktopShell.tsx` の `saasAdminItems`: LINE解析・買取相場・利用者管理 `{ to: "/super-admin/users", labelKey: "nav.superAdminViewers" }`・全体設定 `{ to: "/super-admin/settings", labelKey: "nav.superAdminSettings" }`。為替とログインの行を消す
- `frontend/src/components/MobileShell.tsx`: viewerAccounts の道を `/super-admin/users` に、loginRequests を消し、`resolveItem("superAdminSettings", "nav.superAdminSettings", <NAV_ICONS.saasAdmin …/>, "/super-admin/settings")` を足す

### 3-6. 言葉（ja / en・同じキー）

| キー | ja | en |
|---|---|---|
| nav.superAdminViewers（値を変更） | 利用者管理 | User Management |
| nav.superAdminSettings（新） | 全体設定 | Global Settings |
| nav.superAdminTaxRates（新） | 税率 | Tax Rates |
| nav.superAdminSaProducts（新） | 商材とプラン | Products & Plans |
| superAdmin.settings.groupMoney（新） | 金額の設定 | Pricing |
| superAdmin.settings.comingSoon（新） | この画面は準備中です。 | This page is coming soon. |
| superAdmin.users.groupViewers（新） | 閲覧者 | Viewers |
| superAdmin.viewers.backToViewers（値を変更） | 利用者管理へ戻る | Back to User Management |

`frontend/src/config/routeTitles.ts` に新しい道（settings・settings/fx-rate・tax-rates・sa-products・users/viewers・users/login-requests・users/viewer-templates）を足す。

### 3-7. 道を指す所の直し

- 取込画面の戻り先: TcgProductImportPage → `settingsMasterPath("product-master")`・SupplierImportPage → supplier-master・NoteMasterImportPage → note-master・ProductCategoriesImportPage → product-categories-master
- ViewerAccountsPage のテンプレートのボタン → `/super-admin/users/viewer-templates`。ViewerTemplatesPage の戻る → `/super-admin/users/viewers`
- `tests/prod-check/page-speed-targets.ts`: fx-rate・11件の section・viewers・viewer-templates を新しい道に（login-requests・settings は足さない）

## 4. 代替案と選んだ理由

- 形2（左メニューの中で開く）→ 取らない。PO が形1 を選んだ（2026-11-11「1」）。形1 は管理センターと同じ部品と並べ方で、新しい部品が要らない
- 道を変えずにメニューだけ変える案 → 取らない。左メニューの光り方は道の頭で決まる（DesktopShell の NavLink、`end` 無し）。ログインの画面を開いたときに「利用者管理」を光らせるには、道を `/super-admin/users/` の下にそろえる必要がある
- 状態ルール・単位ルールも移す案 → この便では取らない。名前が「ルール」で、LINE解析の「ルール管理」の組にある。PO の言葉は「マスタ」。報告で読みを伝え、違えば次の便で移す

## 5. リスクと対処

| リスク | 対処 |
|---|---|
| 古い URL のブックマークが切れる | 転送表に4件足す。`?status=` などの後ろは落ちる（中の画面は開く） |
| LINE解析の中のボタンが古い区画を指したまま | 受け手（AnalysisRulesPage）が11件を新しい道へ転送。ダッシュボードの onNavigate も道を動かす形へ |
| 運営でない人が全体設定を開く | ハブが useSuperAdmin で止め、Outlet を出さない。API 側も今の super admin の守りのまま |
| 入れ子の PageLayout で見出しが2つ出る | 管理センターと同じ形（先例あり）。evaluator の画面確認で見る |

戻し方: この PR の merge commit を `git revert -m 1` で戻す（画面だけ、DB 変更なし）。

## 6. 受入条件

| 基準 | 検証方法 |
|---|---|
| K1 PC の左メニューの運営の行が「LINE解析・買取相場・利用者管理・全体設定」の4つだけ | DesktopShell の試験＋本番の画面 |
| K2 全体設定を押すと、画面の中の小さなメニューに「金額の設定: 為替レート管理・税率・商材とプラン」「マスタ管理: 11件」が出て、為替の画面が開く | SettingsHubPage の試験（vitest）＋本番の画面 |
| K3 税率と商材とプランは「準備中」が出る | vitest |
| K4 マスタ11件を押すと、今の LINE解析で見ていたのと同じ表が出る | vitest（各 key で Panel が出る）＋本番で商品マスタを開く |
| K5 LINE解析の左にマスタ管理の組が無い。状態ルール・単位ルールは残る | AnalysisRulesSidebar／Page の試験 |
| K6 `?section=product-master` などで LINE解析を開くと、全体設定の同じマスタへ移る | AnalysisRulesPage の試験＋e2e |
| K7 利用者管理を押すと閲覧者の一覧が開き、小さなメニューに「閲覧者（すべて・状態）」と、その下にログインの許可待ちの1項目が出る。ログインの許可待ちを開いても同じメニューが出て、左は「利用者管理」が光る | ViewerAccountsPage・LoginRequestsPage の試験＋本番の画面 |
| K8 古い6つの道（fx-rate・viewers・login-requests・viewer-templates・tcg-product-master・supplier-master）が新しい道へ移る | legacyPageRedirects.test |
| K9 運営でない人は全体設定の中身が出ない | SettingsHubPage の試験 |
| K10 ja/en の同じキー・直書きの日本語0・CI 全部緑 | CI（i18n・lint・vitest・e2e） |

## 7. 外部・過去事例

- 社内の先例: 管理センター（ADR-069・ADR-149）が同じ「左の大きなメニュー＋画面の中の小さなメニュー」で動いている（ManagementCenterPage.tsx:220-237）。この便はその形を写すだけ
- 外部事例は使わない。理由: 新しい作りを足さず、社内の動いている形を写すため、外部の数字で正しさを示す必要がない

## 8. 実装カード（クラウドの Sonnet へ）

§3 をそのまま作る。触らない範囲: backend・migrations・.github・本番の scripts・11の Panel の中身・AnalysisDashboardPanel と LineWorkflowGuidePanel の key の文字・管理センター。終わったら `npm run lint`・`npx tsc --noEmit`・関係する vitest を回し、生出力をファイルに残す。

## 維持の仕組み

- 項目の正本は `frontend/src/pages/super-admin/settings/settingsNav.ts` の1か所。足すときはここに1行と Panel の表に1行
- 古い道の転送は `frontend/src/pages/super-admin/legacyPageRedirects.ts` と、その配列を固定で比べる試験が守る
- 文字は CI の i18n の点検（ja/en の同じキー・直書き禁止）が守る
- 部品は ADR-144 の見張り（生の部品・色の直書き禁止）が守る
