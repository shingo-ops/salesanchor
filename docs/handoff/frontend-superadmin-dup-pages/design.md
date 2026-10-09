# AY-2g design: LINE解析と重複するスーパー管理3ページの削除

正本は docs/specs/design-system/design.md の「#### AY-2g LINE解析と重複するスーパー管理3ページの削除（2026-10-10）」節。本ファイルは PR 用の写しで、内容は同節と同じ。recon は docs/handoff/frontend-superadmin-dup-pages/recon.md。対象 ADR は ADR-027（docs/adr/ADR-027-ui-internationalization.md）と ADR-144。
PO 決定（2026-10-10）: 「同じものが別にある3ページを削除して、取り込み後の戻り先を LINE解析の『商品マスタ』『仕入元マスタ』に変えてよいですか」に「y」。

#### AY-2g LINE解析と重複するスーパー管理3ページの削除（2026-10-10）

mode: handoff。PO 決定（2026-10-10、本セッション）: 「同じものが別にある3ページを削除して、取り込み後の戻り先を LINE解析の『商品マスタ』『仕入元マスタ』に変えてよいですか」への回答「y」。GO は ADR-1003 の委任に基づく Claude Opus 発行。POのGO原文は創作しない。

現在地（origin/main c59e0fe02。調査 /tmp/CC報告ファイル/super-admin-menu/。本番アクセスは prod-access-30d.md）:
- 対象3ページと、LINE解析の中で同じ働きをする画面（AnalysisRulesPage の ?section=）の対応:
  - TcgSupplierQualityPage.tsx（59行） → section=accuracy-management（AccuracyManagementPanel）
    - 3コンポーネントをそのまま共有している。AnalysisRulesPage.tsx:56 に「TcgSupplierQualityPage の内容を移植」とある。
  - TcgProductMasterPage.tsx（95行） → section=product-master（ProductMasterPanel）
    - 同じ API と Drawer を使う。ProductMasterPanel.tsx:4 に「ページの内容を PageLayout なしで抽出」とある。
  - SupplierMasterPage.tsx（462行） → section=supplier-master（SupplierMasterPanel）
    - 同じ API を使う。違いは行ごとの編集ボタンだけで、Panel でも行をクリックすれば編集できる。
- 3ページだけが使う子ファイル・CSS・api 関数・型は0件。どれも Panel 側が使っている。
- ?section= の読み取り:
  - AnalysisRulesPage.tsx:101-104 が、初回表示のときに1回だけ読む。
  - 3つの key は AnalysisRulesSidebar.tsx の :13、:20、:24 で有効。
  - 既存の実例がある: tests-e2e/analysis-rules-line-guide.spec.ts:142 と LineWorkflowGuidePanel.test.tsx:14。
- 本番の直接アクセス（直近30日・重複を除いた概数）:
  - product-master 約37回（最後は 9/25頃）
  - supplier-quality 約3回（最後は 10/1頃）
  - supplier-master 約2回（最後は 9/18頃）
  - ブックマークがある可能性があるため、古い URL は移し先へ転送する。
- 古い URL の参照:
  - App.tsx: :300、:314-316、:333-335。import は :90、:93、:98。
  - 取り込み画面: TcgProductImportPage.tsx:13-14、SupplierImportPage.tsx:131-132。
  - e2e: tcg-product-detail.spec.ts:43、tcg-product-import.spec.ts:40、:77、:114、:152。
  - routeTitles・メニュー・backend・通知での参照は0件。
- Navigate の書式: react-router の `Navigate` の `to` は string | Path を受け取る（Context7 /remix-run/react-router の docs/api/components/Navigate.md）。navigate("/some/route?search=param") の例が公式にある。App.tsx の前例は `<Route path="/leads" element={<Navigate to="/crm/leads" replace />} />`。
- 試験:
  - TcgProductMasterPage.test.tsx（174行、it 9本）はページを直接描画している。ProductMasterPanel の単体試験は0件。
  - e2e は CI で実行されていない（e2e.yml:105 `if: false`）。

AY-2g 変更契約:
1. App.tsx:
   - 3つの import を削除する。
   - 3つの Route の element を Navigate に置き換える。path はそのまま残す。
     - `/super-admin/tcg-supplier-quality` → `<Navigate to="/super-admin/analysis-rules?section=accuracy-management" replace />`
     - `/super-admin/tcg-product-master` → `<Navigate to="/super-admin/analysis-rules?section=product-master" replace />`
     - `/super-admin/supplier-master` → `<Navigate to="/super-admin/analysis-rules?section=supplier-master" replace />`
   - 前例の1行形に揃える。残すルート（:301 の tcg-product-master/import、:341 の masters/suppliers/import）は変えない。
2. 取り込み画面の戻り先（完了時と「戻る」の2か所ずつ）を変える:
   - TcgProductImportPage.tsx:13-14 → `/super-admin/analysis-rules?section=product-master`
   - SupplierImportPage.tsx:131-132 → `/super-admin/analysis-rules?section=supplier-master`
   - ほかの取り込み画面は変えない（PO 決定の範囲外）。
3. 削除するファイル: TcgSupplierQualityPage.tsx、TcgProductMasterPage.tsx、SupplierMasterPage.tsx。
4. 試験:
   - TcgProductMasterPage.test.tsx を ProductMasterPanel.test.tsx に移す。
     - 描画する対象を ProductMasterPanel に替えるのに必要な最小限だけを直す。PageLayout の見出しに関する検査は、Panel に該当するものが無いので外す。
     - :48 の非管理者の it は外す。管理者かどうかの判定は AnalysisRulesPage 側にあるため。
     - 外した it と、その理由を記録する。
     - 残す it の検査内容（expect）は変えない。
   - e2e: tcg-product-detail.spec.ts と tcg-product-import.spec.ts の一覧への goto を、新しい URL に変える。
     - :147-155 の非管理者の test は、古い URL を開くと analysis-rules?section=product-master に移り、AnalysisRulesPage の非管理者表示（superAdmin.supplierQuality.superAdminOnly の文言）が出ることを確かめる形に直す。
   - 古い URL から移り先へ転送されることを確かめる単体試験を1つ追加する（App のルートか MemoryRouter で、3つの URL それぞれ）。
5. i18n: nav.superAdminTcgProductMaster、nav.superAdminTcgSupplierQuality、nav.superAdminSupplierMaster を ja と en から削除する。実装時に、試験を含めて参照0件を再確認する。
6. 変更しないもの:
   - AnalysisRulesPage と Panel 本体、メニュー、ほかの取り込み画面
   - tcg-sold-out と tcg-parallel-report（PO の判断待ち）
   - backend、CSS、トークン、CI、依存
7. design.md: 本節と実装結果を追記する。docs/handoff/analysis-rules-master-panels/design.md:33-34 の旧基準「スタンドアロンが引き続き動作する」は、本節で上書きされたことを記録する（旧文書は書き換えない）。

前後表:

| 対象 | 変更前 | 変更後 |
|---|---|---|
| 古い3つの URL を開く | 単独ページ | LINE解析の該当画面へ自動で移る |
| 商品の取り込みの完了・戻る | 単独の商品マスタページ | LINE解析の「商品マスタ」 |
| 仕入元の取り込みの完了・戻る | 単独の仕入元マスタページ | LINE解析の「仕入元マスタ」 |
| メニュー・LINE解析の中 | — | 変化0 |

受入:

| 基準 | 検証方法 |
|---|---|
| 転送 | 追加した単体試験で、3つの URL がそれぞれ移り先の URL（パスと ?section=）になる |
| 戻り先 | 2つの取り込み画面の試験（既存があれば）、または実画面で、完了・戻るの遷移先が新しい URL になる |
| 実画面 | 開発モードの build と preview に偽ログインと API モックを使い、古い3つの URL を開く。移り先の画面で、該当のサイドバー項目が選ばれ、中身が表示されることをスクリーンショットで確かめる（設計者が目視） |
| 試験の移設 | 移した it の expect が元と同じであることを差分で示す。外した it と理由を一覧にする |
| 参照0 | 3ページの部品名と、3つの nav キーの参照が0件 |
| e2e | 書き換えた2 spec を、ローカルでその spec だけ実行して結果を記録する。実行できなければ、止まった出力をそのまま記録する |
| 品質 | generate を実行したあとの tsc、lint、check:all、test:coverage（maxWorkers=1）、build、build-storybook、CI の必須チェックがすべて成功する |
| 本番 | Deploy 成功。本番で古い3つの URL を開くと、アプリが 200 を返す（SPA）。app 200、/api/health 200 |

Architect 自己審査（AY-2g）: APPROVE。同一AI（Opus）による自己審査であり、独立した第二者のレビューではない。外部事例は不要（既存の Panel への一本化で、転送は既存の前例の型を使う）。
- 根拠:
  - 重複していることと、3ページだけが使う部品が0件であることを file:line で確かめた。
  - 古い URL は転送するので、ブックマークが壊れない。
  - 戻り先は PO 決定どおり。
  - 単体試験は Panel へ移すので、0件にならない。
  - 配線・データ・backend は変えない。
- 残るリスク（LOW）: ?section= に知らない値が入ると、右側の画面が空になる。既存の挙動で、本便では触らない。

維持の仕組み:
- 守り手: tsc、追加する転送試験、ProductMasterPanel.test.tsx、check-i18n-missing-keys、frontend-check。
- 守っていないもの: e2e（CI で停止中）。
- 切戻し: 本 PR の merge commit を revert する（DB への影響なし）。

#### AY-2g 実装結果

実装: 変更契約1〜6のとおり。App.tsx の3 Route は Navigate に置き換え（App.tsx:297・:310・:326）、3つの import を削除した。取り込み画面2つ（TcgProductImportPage.tsx・SupplierImportPage.tsx）の戻り先（完了と「戻る」の各2か所）を `/super-admin/analysis-rules?section=product-master` と `?section=supplier-master` に変えた。TcgSupplierQualityPage.tsx・TcgProductMasterPage.tsx・SupplierMasterPage.tsx を git rm した。nav.superAdminTcgProductMaster・nav.superAdminTcgSupplierQuality・nav.superAdminSupplierMaster を ja.json と en.json から削除した（各3行）。

変更契約の補足（設計者指示）:
- ProductMasterPanel.test.tsx の it「R10 export failure permits retry and denied users cannot export」から、denied 部分（元の :44-46、cleanup から getBlob の回数を確かめる expect まで）だけを外した。前半の expect は変えていない。外した理由は、管理者判定が AnalysisRulesPage.tsx:124 側にあるため。it の題名は内容に合わせて「R10 export failure permits retry」に直した。
- AnalysisRulesPage.tsx:56、ProductMasterPanel.tsx:4、SupplierMasterPanel.tsx:4 のコメントだけを「旧スタンドアロンページ（AY-2g で削除）の内容を移植／抽出」の趣旨に書き換えた。コードは変えていない（消える部品名に触れていたため）。
- 管理者でない人の拒否を守る既存の単体試験は git grep で見つからなかった（AnalysisRulesPage の試験は0件）。AnalysisRulesPage.test.tsx を1本追加した。isSuperAdmin:false で ?section=product-master を描画したとき、superAdminOnly の文言が出ること、「Export update CSV」ボタンが無いこと、api.get が呼ばれていないことを確かめる。api.get が呼ばれない点は、先に実物で通ることを確かめてから expect にした。

試験の移設:
- TcgProductMasterPage.test.tsx を git mv で components/ProductMasterPanel.test.tsx に移した。変えたのは import 行・vi.mock のパス・描画する対象（`<ProductMasterPanel />`）と、上の外し方だけ。残した it の expect は変えていない（差分は ay2g-test-move-diff.txt）。
- 外した it と理由:
  - 「does not request or expose import for non-admin」（元の :48-52）。理由: 管理者判定は AnalysisRulesPage.tsx:124 側にあり、ProductMasterPanel は useSuperAdmin を使わない。
  - 「R10 export failure permits retry and denied users cannot export」の後半（元の :44-46）。理由は同じ。
  - PageLayout の見出しに関する検査: 元の試験に該当する it は無かったので外したものは0本。
- 追加した試験: legacyPageRedirects.test.tsx（3つの古い URL がそれぞれ移り先のパスと ?section= になる。App.tsx と同じ3つの Route を MemoryRouter で描画し、App.tsx の行番号を冒頭コメントに書いた。App 全体は描画していない）、AnalysisRulesPage.test.tsx（上記）。移り先の URL 文字列は legacyPageRedirects.test.tsx の定数に1回だけ書いた。新しい共有モジュールは作っていない。
- e2e: tcg-product-detail.spec.ts の goto 1か所と tcg-product-import.spec.ts の goto 3か所を新しい URL に変えた。非管理者の test は、古い URL を開くと analysis-rules?section=product-master に移り、「super_admin」を含む文言が出て tablist が無いことを確かめる形に直した。

計測（evidence-20260910/ay2g-*）:
- 参照0件（ay2g-ref-zero.txt）: 3ページの部品名と3つの nav キーは frontend/src と backend で git grep 0件。docs/ 配下の過去文書には名前が残る（書き換えない）。
- 試験の差分（ay2g-test-move-diff.txt）: 上記のとおり。
- 実画面（ay2g-realscreen.json、ay2g-*.png。開発モード build と vite preview、偽ログインと API モック、Chromium、幅1280）:
  - /super-admin/tcg-product-master → /super-admin/analysis-rules?section=product-master、サイドバー「商品マスタ」が選択、右に商品マスタのパネル。
  - /super-admin/tcg-supplier-quality → /super-admin/analysis-rules?section=accuracy-management、サイドバー「解析精度管理」が選択。
  - /super-admin/supplier-master → /super-admin/analysis-rules?section=supplier-master、サイドバー「仕入元マスタ」が選択、右に仕入元マスタの表。
  - 取り込み画面2つで「戻る」（管理者）を押した先は /super-admin/analysis-rules?section=product-master と ?section=supplier-master。非管理者の「戻る」も同じ URL。
  - 取り込み完了後の onDone は実画面で通していない（コミット操作のモックが重いため）。「戻る」と同じ onDone 関数に同じ URL を渡している。
- e2e（ay2g-e2e-run.txt）: 書き換えた2 spec をローカルで実行して 22 本中 7 本成功、15 本失敗。変更前の origin/main（99a970545）で同じ2 spec を実行すると同じ 15 本が失敗し、同じ 7 本が成功した（ay2g-e2e-baseline-main-99a970545.txt、失敗した題名の集合は完全に一致）。失敗は行の Enter で詳細 Drawer が開かない・R10 の download が取れない、など。今回の変更が原因ではない（e2e は CI で停止中、e2e.yml:105 `if: false`）。非管理者の2 test は成功。
- 品質（ay2g-chk-*.txt）: tsc 0、lint 0（警告139・エラー0）、check:all 0、test:coverage --maxWorkers=1 0（77 files・951 tests 成功。AY-2f 時点は74 files・944）、build 0、build-storybook 0。frontend/coverage は worktree 外へ移動した。

限界: 本番反映後の確認（Deploy・古い3つの URL が 200・/api/health 200）は merge 後。ProductMasterPanel 本体は、管理者判定を持たない（AnalysisRulesPage が持つ）。?section= に知らない値が入ると右側が空になる既存の挙動は未変更。切戻し: 本PRの merge commit を revert（DB 影響なし）。

変更契約の補足（設計者指示・レビュー対応）:
- 転送の対応表を frontend/src/pages/super-admin/legacyPageRedirects.ts の `LEGACY_SUPER_ADMIN_REDIRECTS`（3組）に1か所へまとめた。App.tsx は、この配列を map した Route（`<Route key={r.from} path={r.from} element={<Navigate to={r.to} replace />} />`）に置き換えた（3行の Navigate Route を1行の map にし、位置は tcg-product-master の位置）。legacyPageRedirects.test.tsx は同じ配列を import し、(a) 配列が期待する3組と完全一致すること（期待値は直書き）、(b) 各 from を MemoryRouter（配列の map と、残すルート tcg-product-master/import を含む）で開くと to の pathname と search に移ることを確かめる。tcg-product-master/import との一致は、React Router がパスの具体性で順位を決めるため並び順に依存せず、(b) と実画面（取り込み画面の表示）で確認した。取り込み画面2つの戻り先 URL は配列と共有していない（対象外）。
- AnalysisRulesPage.test.tsx に肯定の対照を1本追加した。isSuperAdmin:true で ?section=product-master を描画すると「Export update CSV」ボタンが出て、superAdminOnly の文言は出ない（api.get のモック値は ProductMasterPanel.test.tsx と同じ形。実際に動かして通ることを確認してから expect にした）。
- 再計測: tsc 0、lint 0、check:all 0、test:coverage --maxWorkers=1 0（77 files・953 tests 成功）、build 0。開発モード build と preview で、古い3つの URL の転送・戻る の先を再記録した（ay2g-realscreen.json。結果は前回と同じ）。

## 維持の仕組み
守り手: tsc、追加した転送試験（legacyPageRedirects.test.tsx）、AnalysisRulesPage.test.tsx、ProductMasterPanel.test.tsx、frontend/scripts/check-i18n-missing-keys.js、frontend-check。守っていないもの: e2e（CI で停止中、.github/workflows/e2e.yml:105）。切戻しは本PRの merge commit を revert する（DB 影響なし）。

## 外部・過去事例の参照と我々への応用
外部事例: 不要（既存の Panel への一本化。転送は App.tsx の既存前例 `<Route path="/leads" element={<Navigate to="/crm/leads" replace />} />` の型）。過去事例: AY-2f（PR #4098）の未使用部品の削除と同じ進め方。
