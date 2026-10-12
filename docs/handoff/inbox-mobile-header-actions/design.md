# 設計: 受信箱のヘッダー操作行をスマホの一覧で出さず、絞り込みを検索欄へ移す

対象 ADR: ADR-137（MobileShell の独立 DOM・`useIsMobile`）／ADR-067（デザイントークン強制）／ADR-144（UI共通部品のガバナンス）
recon: [recon.md](./recon.md)（`docs/handoff/inbox-mobile-header-actions/recon.md`）
PO 指定: 2026-10-13「ヘッダーアクションもスレッドでしか必要ないのでスマホ版では非表示にして。受信箱の顧客一覧表示では表示しなくていい」＋選択「4つ消して絞り込みは検索欄の横へ移す」

## 1. なぜ直すのか（事実のみ）

- 操作行（テンプレート / FAQ / 絞り込み / 受信箱の設定）は**一覧でも会話でも同じ位置に出ている**（recon A5・実機で同一座標）。
- 一覧を見ているときに テンプレート / FAQ / 設定 を押す場面はない（PO 判断）。行は 54dp を占める（recon A6）。
- ただし**絞り込みは一覧専用**（開くのは一覧のステータスタブ・recon B2）。4つまとめて消すとスマホで絞り込みができなくなるため、**検索欄の横へ移す**（PO 選択）。検索と絞り込みは「一覧を絞る」点で役割が近く、お手本（WhatsApp の一覧画面）も上部に検索と絞り込みをまとめている。

## 2. 変更するファイルと、変更前後

### 2-1. `frontend/src/pages/inbox/InboxConversationList.tsx`

検索欄（`.inbox-search-row`）の検索と管理の**あいだ**に絞り込みボタンを置く。Props に `mobileFiltersOpen` / `toggleMobileFilters` / `hasActiveFilter` を追加。

```tsx
// 変更後（検索の直後）
</div>
{/* スマホ用の絞り込み。検索と役割が近いので検索欄の隣に置く（PC・タブレットでは CSS で非表示） */}
<button
  type="button"
  className={`icon-btn inbox-mobile-filter-toggle${hasActiveFilter ? " has-active" : ""}`}
  aria-expanded={mobileFiltersOpen}
  onClick={toggleMobileFilters}
  aria-label={t("inbox.mobileFilters")}
  data-tooltip={t("inbox.mobileFilters")}
>
  <NAV_ICONS.filter size={ICON.md} aria-hidden="true" />
</button>
<div className="inbox-manage-wrap" ref={manageRef}>
```

### 2-2. `frontend/src/pages/inbox/InboxPage.tsx`

1. 絞り込みボタンを `headerActions` から削除（2-1 へ移設）。
2. 操作行を**スマホの一覧表示では渡さない**。

```tsx
const isMobile = useIsMobile();
const showHeaderActions = !isMobile || selectedLeadId != null;
const headerActions = showHeaderActions ? headerActionsContent : undefined;
```

`PageLayout` は `headerAction` が未指定なら行ごと描かない（recon A2）ため、空の枠は残らない。見出し `h2.text-page-title` は常に描かれる（recon A3）ので読み上げでの現在地は保たれる。

3. `InboxConversationList` に3つの props を渡す。

### 2-3. `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts`

検査を1件追加（スマホ）＋ PC・タブレット側に2行追加。§5 を機械で守る。

**CSS は変更しない。** 絞り込みの表示条件（`frontend/src/pages/inbox/InboxPage.css:996` と `:1181-1182`）はクラス名に対する指定で、置き場所を変えてもそのまま効く。

## 3. 触らない範囲（明示）

- **PC・タブレット**: `showHeaderActions` は `!isMobile` で常に真。操作行は従来どおり出る。
- **CSS**: 1行も変更しない。
- **絞り込みの当たり判定（37x36dp）**: 44px 未満だが**この便では変えない**（第2便の対象・recon B4）。移設だけを行い、大きさの変更は別便で検証する。
- **`PageLayout`**: 変更しない（既存の `headerAction` の仕組みをそのまま使う）。
- **API・DB・migrations**: 触らない。

## 4. 守る決まり（CI が検査する）

`check:all`（25項目）／`Lint & Dark Mode Check (ADR-067)`／`UI governance gate`／`画面検査（受信箱 3幅 Playwright）`／`Frontend lint & custom checks`（単体テスト含む）。

## 5. 検証方法（受け入れ基準）

| # | 基準 | 検証方法 |
|---|---|---|
| 1 | 390px の**一覧では操作行が出ない** | `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts` で `.page-header-actions` が `toHaveCount(0)` |
| 2 | 390px の一覧で**絞り込みが検索欄の中に見える** | 同検査で `.inbox-search-row .inbox-mobile-filter-toggle` が `toBeVisible()` |
| 3 | 390px で**絞り込みが実際に効く**（押すとタブが開き、もう一度押すと閉じる） | 同検査で `.inbox-full-tab-bar` の表示/非表示を往復で確認 |
| 4 | 390px で**会話を開くと操作行が出る**（返信中に使う） | 同検査で `.page-header-actions` が `toHaveCount(1)` |
| 5 | 390px で会話を開くと**一覧専用の絞り込みは見えない** | 同検査で `toBeHidden()` |
| 6 | **1280px / 768px では操作行が一覧でも出る**（PC 不変） | 同検査の PC・タブレット側で `.page-header-actions` が `toHaveCount(1)`、絞り込みは `toBeHidden()` |
| 7 | 読み上げで**現在地が分かる**（ページ名が見出しとして残る） | 既存の検査（`getByRole("heading", { name: "受信箱" })`）が緑のまま |
| 8 | `npm run check:all` 25/25 ／ 単体テスト全件合格 | 実行して出力を PR に貼る |
| 9 | 1画面1ページの往復が壊れていない | 既存の「スマホ: 一覧 → 会話 → 一覧」が緑のまま |

## 6. 戻し方

このPRの revert のみ。CSS・トークン・API・DB を変更しないため波及はない。

## 7. 残るリスク（正直に）

1. **スマホの一覧から テンプレート / FAQ / 受信箱の設定 に行けなくなる。** テンプレートと FAQ は下部タブの「メニュー」から開ける画面だが、**受信箱の設定はこのボタンしか入口が無い**。会話を1件開けば出るため到達は可能だが、「一覧だけ見ている状態」からは開けない。気になる場合は設定を「メニュー」シートか一覧側へ置く別便が必要。
2. **絞り込みの当たり判定は 37x36dp のまま**（44px 未満）。移設しただけで大きさは変えていない（第2便の対象）。
3. **JS 判定（`useIsMobile`）と CSS の切替点が二重管理になる。** どちらも 767px（`frontend/src/tokens.css:113-117` と `frontend/src/constants/breakpoints.ts`）を参照するが、値が一致していることは `check:breakpoint-sync` が CSS 側のみ検査する。JS 側は `useIsMobile` が `BREAKPOINTS.MOBILE_MAX` を参照するため実質1箇所。
4. 幅の境界（767/768px）でブラウザを横に伸縮させた瞬間の描き替えは `matchMedia` のイベントに依るため、既存の `MobileShell` 切替と同じ挙動になる（新しいリスクではない）。

## 8. 相互参照

- **recon**: [recon.md](./recon.md)（`docs/handoff/inbox-mobile-header-actions/recon.md`）— A1〜E の事実を前提とする。操作行の構造（A1・A2）、絞り込みが一覧専用であること（B2）、検索欄が左パネル内にあること（C3）、`useIsMobile` の存在（D1）を file:line で確認した。
- **ADR-137**（MobileShell の独立 DOM）: スマホ判定は `useIsMobile`（`matchMedia` ＋ `BREAKPOINTS.MOBILE_MAX`）を使う。新しい判定手段を作らない。
- **ADR-067**（デザイントークン強制）: CSS を変更しないため新しい値は増えない。`check:css-values` / `check:css-colors` が機械的に強制する。
- **ADR-144**（UI共通部品のガバナンス）: 移設する絞り込みは既存の `icon-btn` を使い、新しい部品を作らない。§5「移行は別トラック」に従い `ListRow` 金型への置き換えは行わない。
- **ADR-027**（i18n）: 文言は既存キー `inbox.mobileFilters` をそのまま使う。新規キーなし。
- **直前の作業**: [../app-visual-language/card-stage4b-inbox-mobile.md](../app-visual-language/card-stage4b-inbox-mobile.md) §13（3幅の画面検査の恒久化）／[../mobile-topbar-removal/design.md](../mobile-topbar-removal/design.md)（上部のページ名バーの削除）。本便はこの2つの続きで、同じ検査ファイルに受け入れ基準を足す。

## 9. 外部・過去事例の参照と我々への応用

| 事例 | 何を参照したか | 我々への応用 |
|---|---|---|
| **WhatsApp（Android）の実測** | 一覧画面の上部は**検索**と**絞り込み**が同じ帯にまとまり、会話を書くための操作は一覧側に出さない | 絞り込みを検索欄の横へ移す形にした。一覧から「返信のための操作」を外す方針もここに合わせた |
| **Meta Business Suite（Android）の実測** | 受信箱の一覧では操作ボタンを最小にし、会話を開いてから操作が増える | 「一覧は見るため・会話は操作するため」という分け方の裏付け |
| **#4176（直前の社内事例）** | スマホ上部のページ名バーを消し、56px を本文に回した | 同じ考え方の続き。今回はさらに 54dp を一覧に回す |
| **#4155（社内事例）** | ステータスタブをスマホで隠し、絞り込みボタンで開く形にした | その絞り込みボタンの**置き場所**を今回見直す。開閉の仕組み（`filters-open`）は変えない |

**採用しなかったもの**: 「一覧でも4つ全部出し続ける」案は採らない（PO 指定）。「絞り込みも消す」案も採らない（スマホで絞り込みができなくなるため）。

## 10. 維持の仕組み

- 守り手: `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts`（§5 の #1〜#7 を3幅で検査）と `.github/workflows/e2e.yml` のジョブ `visual-language`、`frontend/package.json` の `check:all`（25項目）。
- 対象: 一覧での操作行の復活、絞り込みの消失・機能不全（押しても開かない）、会話側で操作行が出なくなること、PC・タブレットでの操作行の消失、読み上げ用の見出しの消失。
- 関所が無い部分: **受信箱の設定への入口が一覧から無くなること自体は検査していない**（§7-1）。入口の設計は PO 判断が必要な事項であり、機械で守る対象にしない。必要になれば別便で入口を足し、そのときに検査を追加する。
