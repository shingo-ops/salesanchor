# design: Record Drawer ロールアウト

> 作成: 2026-06-10 | 担当: architect
> recon: `docs/handoff/record-drawer-rollout/recon.md`
> ADR参照: ADR-122（Modal標準化）

---

## 1. KGI

**「行クリック→スライド→フルページ」を全対象ページのデフォルト動作にする。**

| 基準 | 検証方法 |
|------|---------|
| 対象 10 ページ（Suppliers 含む）で行クリック → Drawer が開く | Evaluator（Playwright: 各ページで行クリック確認） |
| フルページ遷移が正常動作 | Evaluator（↗ボタン → EditPage へ遷移・保存） |
| 既存の新規作成・削除 UX が壊れていない | Evaluator（既存フロー regression テスト） |
| `useRecordDrawer` フックで Suppliers が動作 | CI + Evaluator（Suppliers の既存テスト全件 pass） |
| バッチ C 不適合は例外フラグ記録 | recon 更新 + PO 確認 |

---

## 2. 外部・過去事例の参照と応用

外部 SaaS 製品（HubSpot・Salesforce・Notion・Linear）と社内経緯（ADR-122・Suppliers パイロット PR #1877）を参照し、設計判断の根拠とした。

### 外部事例

| 製品 | パターン | 応用 |
|------|---------|------|
| Notion「サイドピーク」 | 一覧→右スライド→フルページ | Drawer 設計の参考（既に Drawer.tsx で採用済み） |
| HubSpot CRM | 一覧行クリック→右スライドに要点（会社名・ステータス・担当者）→詳細ページボタン | 「要点 in スライド、全項目 in フルページ」分割の根拠 |
| Linear issue サイドピーク | 項目数に関わらず右スライドで表示（スクロール可）→ Cmd+クリックでフルページ | 多項目ページでもスクロールで対応できる事例 |
| Salesforce Lightning | レコード行クリック → クイック編集（要点）→「詳細を開く」で全項目 | 要点フォームと全項目フォームの分離パターンの定番 |

### 社内経緯

- **ADR-122**（2026-06）: modal-overlay パターンを標準 Modal に置換。同 ADR で「次のフェーズは Drawer への移行」と記録。本設計はその継続。
- **Suppliers パイロット**（PR #1877）: `useRecordDrawer` フック化の前段として動作実証済み。リファクタリスクが最小と判断できる根拠。

### 応用判断

- 「**要点 in スライド / 全項目 in フルページ**」は HubSpot・Salesforce の定番パターン。
- 項目数 ≤ 10 はスライドに全部出してよい（Linear 事例）。項目数 > 10 は要点のみ（HubSpot パターン）。
- `useRecordDrawer` フック化は Angular CDK や React Query のカスタムフック慣習に倣う（状態管理ロジックを再利用可能単位に分離）。

---

## 3. 技術 How

### 3-1. `useRecordDrawer<T, F>` フック設計

**配置先**: `frontend/src/hooks/useRecordDrawer.ts`（新規作成）

```typescript
interface UseRecordDrawerOptions<T, F> {
  /** レコード → フォーム状態への変換 */
  toForm: (record: T) => F;
  /** 空フォーム（新規・クリア時） */
  emptyForm: F;
}

interface UseRecordDrawerReturn<T, F> {
  drawerOpen: boolean;
  editId: number | null;
  editForm: F;
  handleRowClick: (record: T & { id: number }) => void;
  closeDrawer: () => void;
  setEditForm: React.Dispatch<React.SetStateAction<F>>;
}

export function useRecordDrawer<T extends { id: number }, F>(
  options: UseRecordDrawerOptions<T, F>
): UseRecordDrawerReturn<T, F>
```

**フックが管理するもの**: `drawerOpen` / `editId` / `editForm` / `handleRowClick` / `closeDrawer`

**フックが管理しないもの（各ページの責任）**:
- フォーム型定義・フォーム UI
- API 呼び出し（GET/PATCH）
- 保存後の `load()` コールバック
- Drawer タイトル・権限キー・フルページ route

### 3-2. 各ページの実装パターン（フック利用後）

```tsx
// ① フックを呼ぶ（5行）
const { drawerOpen, editId, editForm, handleRowClick, closeDrawer, setEditForm } =
  useRecordDrawer<MyRecord, MyFormState>({ toForm, emptyForm });

// ② Drawer をマウント（変わらず）
<Drawer
  open={drawerOpen}
  onClose={closeDrawer}
  title={t("xxx.editTitle")}
  onOpenFullPage={editId ? () => { closeDrawer(); navigate(`/xxx/${editId}/edit`); } : undefined}
>
  <form onSubmit={handleSave}>
    <MyFormFields form={editForm} onChange={...} />
    ...
  </form>
</Drawer>

// ③ DataTable に渡す（1行）
onRowClick={hasPermission("xxx.update") ? handleRowClick : undefined}
```

### 3-3. フォーム分割ルール（要点 / 全項目）

| 基準 | スライド内容 | フルページ内容 |
|------|------------|-------------|
| inputs ≤ 10 | **全項目**（スクロール不要） | 同じ全項目（重複 OK） |
| inputs 11〜20 | **要点**（名前・ステータス・主要連絡先等） | 全項目 |
| inputs > 20 | **要点**（名前・ステータスのみ） | 全項目 |

**要点フィールドの選定基準**: 「一目で誰・何かわかる」「最も更新頻度が高い」フィールドを優先。

### 3-4. 各ページの要点 vs 全項目 切り分け

| ページ | inputs 総数 | スライド内（要点） | フルページ（全項目） |
|--------|-----------|-----------------|-----------------|
| Suppliers | 6 | 全項目（完了済み） | 全項目 |
| Teams | **8** | 全項目（name / leader_id / description） | 全項目 |
| Bots | **14** | 要点（name / webhook_url / enabled 等 6項目） | 全項目 |
| Contacts | **14** | 要点（name / email / phone / company 等 6項目） | 全項目 |
| Staff | **24** | 要点（name / email / role / status 等 6項目） | 全項目 |
| Deals | **25** | 要点（title / status / amount / company 等 5項目） + CompanyContactSelector は**フルページのみ** | 全項目 |
| Leads | **31** | 要点（name / email / status / source 等 6項目） | 全項目 |
| Companies | **29** | 要点（name / name_en / status / notes 等 6項目）→ フルページは既存 CompanyDetailPage（5タブ） | CompanyDetailPage |

### 3-5. Companies の特殊処理

`/crm/companies/:id` に 5タブ詳細ページ（`CompanyDetailPage`）が既存。

- `onOpenFullPage` → `navigate('/crm/companies/:id')` （EditPage を新規作成しない）
- Drawer 内フォームは「**要点6項目の Quick Edit**」として実装
- 住所・住所帳は CompanyDetailPage の「住所タブ」で編集

### 3-6. EditPage テンプレート（SupplierEditPage 準拠）

```
pages/{entity}/{Entity}EditPage.tsx
```

- `useParams<{ id: string }>()` で ID 取得
- `api.get<Record>('/entity/:id')` → フォーム初期化
- `api.patch('/entity/:id', payload)` → 保存
- 保存後: `navigate('/entity-list-path')`
- `<PageLayout>` + `<EntityFormFields>` 再利用

---

## 4. バッチ計画

| バッチ | 対象ページ | PR 構成 | 優先度 |
|-------|---------|--------|------|
| **前提** | `useRecordDrawer` フック作成 + Suppliers リファクタ | PR-S（1本）| 最優先 |
| **バッチ A** | Teams / Bots | PR-A1（Teams）+ PR-A2（Bots） | 高（軽量・検証容易） |
| **バッチ B** | Contacts / Staff | PR-B1（Contacts）+ PR-B2（Staff） | 高 |
| **バッチ C** | Companies / Deals / Leads | PR-C1（Companies）+ PR-C2（Deals）+ PR-C3（Leads） | 中（複雑・要実機確認） |
| **バッチ D（要判断）** | PurchaseOrders / Sales / Commissions | 実機確認後 → 適合なら PR / 不適合なら例外フラグ | PO 確認後 |

> **バッチ A を B より先にした理由**: Teams/Bots はフォームが軽量（≤14 inputs）でリスクが低く、フックの実証がより早く完了する。

### 各 PR の成果物

各 PR には以下を含める:
1. `*FormFields.tsx`（フォームフィールド部品）
2. `*EditPage.tsx`（フルページ編集）
3. `*Page.tsx` の Drawer 移行（Modal → Drawer 置換）
4. `App.tsx` への route 追加
5. `ja.json` / `en.json` への i18n キー追加

### 例外フラグの記録方法

バッチ D で不適合と判断した場合:

```markdown
<!-- docs/handoff/record-drawer-rollout/exceptions.md に記録 -->
| ページ | 理由 | 代替案 | PO 確認日 |
```

---

## 5. 受け入れ基準と検証方法

| # | 基準 | 検証方法 | ゲート |
|---|------|---------|------|
| AC1 | `useRecordDrawer` フック確立 | TypeScript コンパイル通過 + Suppliers の既存テスト全件 pass | CI |
| AC2 | Suppliers がフック利用後も regression なし | Playwright: 行クリック→Drawer 開 / フォーム保存 / フルページ遷移 | Evaluator |
| AC3 | 各バッチページで「行クリック → Drawer 開く」動作 | Playwright: `onRowClick` 発火確認 | Evaluator |
| AC4 | 「↗ フルページで開く」→ `*EditPage` へ遷移・保存 | Playwright: ボタンクリック→URL変化→保存→一覧へ戻る | Evaluator |
| AC5 | 既存「新規作成（Modal）」「削除（ConfirmModal）」が壊れていない | Playwright: 既存フロー実行確認 | Evaluator |
| AC6 | Deals の `CompanyContactSelector` がスライドに入らない場合 → フルページのみに配置 | 実機での表示確認（スクロール・レイアウト崩れなし） | Evaluator（実機） |
| AC7 | Companies の Drawer が `CompanyDetailPage` へ正しく遷移 | Playwright: ↗ ボタン → `/crm/companies/:id` | Evaluator |
| AC8 | 権限なし（`*.update` 未保持）ではスライドが開かない | Playwright: 権限なしユーザーで行クリック → 無反応 | Evaluator |
| AC9 | i18n: 全キーが `ja.json` / `en.json` 両方に存在 | CI の ESLint local/no-japanese-literal チェック | CI |
| AC10 | 対象外ページ（Products 等）が変更されていない | git diff でファイル変更なし確認 | Reviewer |

---

## 6. 弊害・トレードオフ

| リスク | 重篤度 | 対策 |
|--------|-------|------|
| `useRecordDrawer` フック化で Suppliers が regression | 中 | Suppliers の Playwright テストを PR-S の必須ゲートにする |
| Deals の `CompanyContactSelector` がスライドに入らず UX 崩壊 | 中 | AC6 で実機確認。入らなければフルページのみ（スライドに簡易版）|
| Companies: Quick Edit と CompanyDetailPage の二重管理 | 低 | Quick Edit は「要点6項目のみ」スコープに厳密に絞る |
| バッチ数が多く develop/main 乖離リスク | 低 | 各バッチを develop マージ後すぐ main デプロイ（Shingo GO） |
| Staff/Leads の大型フォーム（24〜31 inputs）でスライドが長大 | 低 | 要点6項目のみ出し、フルページへ誘導する（ルール §3-3） |
| 各 PR で同じ App.tsx を触るコンフリクト | 低 | バッチを直列に進める（並列 PR は App.tsx を同時に触らない） |

---

## 7. スプリント計画票

| Sprint | 内容 | PR | 成果物 |
|--------|------|---|--------|
| S0 | `useRecordDrawer` フック作成 + Suppliers リファクタ | PR-S | `hooks/useRecordDrawer.ts` + Suppliers の Drawer 移行 |
| A1 | Teams: Drawer 移行 | PR-A1 | `TeamsFormFields.tsx` + `TeamsEditPage.tsx` + `TeamsPage.tsx` 更新 |
| A2 | Bots: Drawer 移行 | PR-A2 | `BotsFormFields.tsx` + `BotsEditPage.tsx` + `BotsPage.tsx` 更新 |
| B1 | Contacts: Drawer 移行 | PR-B1 | `ContactsFormFields.tsx` + `ContactsEditPage.tsx` + `ContactsPage.tsx` 更新 |
| B2 | Staff: Drawer 移行 | PR-B2 | `StaffFormFields.tsx` + `StaffEditPage.tsx` + `StaffPage.tsx` 更新 |
| C1 | Companies: Quick Edit Drawer + CompanyDetailPage 接続 | PR-C1 | `CompaniesQuickEditFields.tsx` + `CompaniesPage.tsx` 更新 |
| C2 | Deals: Drawer 移行（CompanyContactSelector 実機確認後） | PR-C2 | `DealsFormFields.tsx` + `DealsEditPage.tsx` + `DealsPage.tsx` 更新 |
| C3 | Leads: Drawer 移行 | PR-C3 | `LeadsFormFields.tsx` + `LeadsEditPage.tsx` + `LeadsPage.tsx` 更新 |
| D | PurchaseOrders / Sales / Commissions: 実機判断 | PR-D or 例外フラグ | 適合: PR / 不適合: `exceptions.md` + PO 確認 |

---

## 8. 不明ゼロ宣言

recon §8 の不明点はすべて本設計で解消済み:

| recon §8 不明点 | 解消内容 |
|----------------|---------|
| Companies: どこまで編集させるか | 要点6項目の Quick Edit → CompanyDetailPage で全項目（§3-4） |
| Deals/Leads のフォームがスライドに収まるか | 要点6項目のみ表示。CompanyContactSelector はフルページのみ（§3-4, AC6） |
| `CompanyContactSelector` がスライドサイズで動作するか | スライドには出さない（フルページのみ）（§3-4） |
| `useRecordDrawer` フック化 vs コピー | フック化に決定（PO 承認済み）（§3-1） |
| Products: Drawer を入れるか | 現状維持（直接遷移パターン）（対象外） |
| Shifts: 対象に含めるか | 対象外（バッチ D 以降で別途検討）|

---

## 9. 継続（完了後の運用）

- 新規ページ追加時は `useRecordDrawer` を使うことをデフォルトとする（新 ADR に記録予定）
- バッチ D の例外ページは `exceptions.md` に記録し、別スプリントで再検討
- `SupplierEditPage` を EditPage の実装テンプレートとして `docs/` に参照リンクを置く
