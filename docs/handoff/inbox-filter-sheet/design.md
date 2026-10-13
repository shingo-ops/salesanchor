# 設計: 絞り込みを下から出るシートにする（Sheet 金型の新設を含む）

対象 ADR: ADR-144（UI共通部品のガバナンス・§4 新規金型の手順）／ADR-067（デザイントークン強制）／ADR-027（i18n）／ADR-073（stories 必須）
recon: [recon.md](./recon.md)（`docs/handoff/inbox-filter-sheet/recon.md`）
PO 指示・許可: 2026-10-13「ポップアップで画面に表示してその時に選択して閉じる」／形は**下から出るシート**／金型の新設に**明示の許可**（「進める」）

## 1. なぜ直すのか（事実のみ）

- 現状は絞り込みを押すと**画面内の帯**が現れ、**選んでも閉じない**（recon A2・A4）。
- PO 指示は「選んで閉じる」こと。下から出る形の金型は**既存に無い**（recon B）。
- `Drawer` は向きが違う上に **22 ページで使用中**で、改造の波及が大きい（recon B）。

## 2. 変更するファイルと、変更前後

### 2-1. 新設: `frontend/src/components/Sheet.tsx`（金型）

`frontend/src/components/Drawer.tsx` の a11y をそのまま踏襲し、出る向きと重ね順だけ変える。

| 引数 | 意味 |
|---|---|
| `open` | 開いているか |
| `onClose` | 閉じる要求（Esc・背景クリック・閉じるボタン） |
| `title` | 見出し。`aria-labelledby` にも使う |
| `children` | 中身 |
| `footer?` | 省略可のフッタ |

備える性質（recon C1・C2）: Esc で閉じる／背景クリックで閉じる／フォーカストラップ／閉じたら元の要素へフォーカス復帰／`role="dialog"`・`aria-modal`・`aria-labelledby`／`document.body` へポータル描画／閉じるラベルは `t("common.close")`。

### 2-2. 新設: `frontend/src/components/Sheet.css`（`var()` のみ）

- オーバーレイ: `--overlay-bg` / `--z-backdrop`
- 本体: 下端に固定・`max-height: 80dvh`・`--bg-surface` / `--shadow-modal` / `--radius-xl`（上2角）/ `--z-modal`
- 下から出るスライド: `translateY(100%) → 0`・`--transition-slow`
- 本体の下余白に `env(safe-area-inset-bottom)` を足す（recon C5 の作法）
- **生の値・色コードは書かない**（`check:css-colors` / `check:css-values` / `check:css-var-fallbacks` / `stylelint` を通過済み）

### 2-3. 新設: `frontend/src/components/Sheet.stories.tsx`

3つ: 基本表示（選んで閉じる）／フッタあり／中身が多い（80dvh を上限に内側スクロール）。`check:stories` を通過済み（全48部品に stories あり）。

### 2-4. `frontend/src/pages/inbox/InboxPage.tsx`

- wrapper の `filters-open` クラスを**外す**（帯の開閉をやめるため）。
- `</PageLayout>` の後に `<Sheet open={mobileFiltersOpen} …>` を置き、中身に **ステータス6つ ＋ 未読・未返信 ＋ プラットフォーム選択**を入れる。
- **どれを選んでも `setMobileFiltersOpen(false)` で閉じる**。

### 2-5. `frontend/src/pages/inbox/InboxPage.css`

- `@media (max-width: 767px)` の中: 帯（`.inbox-full-tab-bar` / `.inbox-sub-filter-bar`）は**常に非表示**にし、`filters-open` の表示指定を削除。
- シートの中身の見た目（`.inbox-filter-sheet*`）を追加。選択肢の高さは `--size-icon-btn-lg`（44px・WCAG 2.5.5）。選択中は `--accent` ＋ `--on-accent`。

### 2-6. `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts`

既存の「押すと帯が開く」基準を**シート方式に書き換える**（recon D）。

## 3. 触らない範囲（明示）

- **PC・タブレット**: 帯は従来どおり常時表示。絞り込みボタンはそもそも出ない（recon A5）。ADR-064 の範囲には触らない。
- **`Drawer` / `Modal` / `Popover`**: 1行も変更しない（22ページへの波及を避ける）。
- **トークン**: 追加・変更しない（既存のみ）。
- **絞り込みの条件そのもの**（`statusTab` / `unreadOnly` / `followUpOnly` / `platformFilter` の意味）: 変更しない。置き場所と閉じ方だけ変える。
- **API・DB・migrations**: 触らない。

## 4. 守る決まり（CI が検査する）

`check:all`（25項目／`check:stories`・`check:css-colors`・`check:css-values`・`check:css-var-fallbacks`・`stylelint`・`lint`（i18n）を含む）／`UI governance gate`／`画面検査（受信箱 3幅 Playwright）`／`Frontend lint & custom checks`（単体テスト）。

## 5. 検証方法（受け入れ基準）

| # | 基準 | 検証方法 |
|---|---|---|
| 1 | 390px で**帯が常に出ない** | `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts` で `.inbox-full-tab-bar` が `toBeHidden()` |
| 2 | 390px で**絞り込みを押すとシートが開く** | 同検査で `[data-testid="sheet-panel"].comp-sheet-panel--open` が1件 |
| 3 | シートに**見出しがある**（読み上げ名） | 同検査で `getByRole("heading")` が見える |
| 4 | **選ぶと閉じて絞り込みが効く** | 同検査で「未読」を押す → シートが0件・絞り込みボタンに `has-active` が付く |
| 5 | **選択肢が 44px 以上** | 同検査で `boundingBox().height >= 44` |
| 6 | **背景タップで閉じる** | 同検査で `.comp-sheet-overlay` を押す → シートが0件 |
| 7 | **1280px / 768px では帯が常時出てシートは開かない** | 同検査の PC・タブレット側 |
| 8 | 既存の基準がすべて緑のまま | 同ファイルの既存7本 |
| 9 | `npm run check:all` 25/25 ／ 単体テスト全件合格 | 実行して出力を PR に貼る |
| 10 | **投入後の実機でシートが下から出て選ぶと閉じる** | デプロイ後に構造データで確認し PR に追記 |

## 6. 戻し方

このPRの revert のみ。新設した3ファイルが消え、帯の開閉が戻る。既存の金型・トークン・API・DB を変更しないため波及はない。

## 7. 残るリスク（正直に）

1. **新しい金型を1つ増やす**。保守対象が増える。ただし `Drawer` を改造して 22 ページに波及させるより安全と判断した（recon B）。
2. **シートは `--z-modal`（400）に置く**ため、他のモーダルと同時に開くと重なり順が同値になる。受信箱では絞り込みシートと設定モーダルが同時に開く導線は無いが、将来追加するときは注意が必要。
3. **帯をスマホで完全に出さなくした**ため、絞り込み中であることは**ボタンの印（`has-active`）だけ**で示される。選択中の条件を一覧の上に出す表示は無い。気になる場合は別便で「選択中の条件をピルで出す」を検討する。
4. **プラットフォーム選択は `SelectControl`（生の `<select>` ではない金型）をシート内に置いた**。選ぶとシートが閉じるため、選び直すには再度開く必要がある。
5. お手本（WhatsApp）の絞り込み中の画面は**未取得**（検索欄を触るとキーボードが開くため当時保留）＝**比較材料がない**。本便は PO 判断に基づく。

## 8. 相互参照

- **recon**: [recon.md](./recon.md)（`docs/handoff/inbox-filter-sheet/recon.md`）— A の現状、B の金型の在庫と `Drawer` の使用22件、C の写すべき性質とトークン、D の検査への影響、E の ADR 関係。
- **ADR-144**（UI共通部品のガバナンス）: §4 の手順どおり「止める → PO 許可 → Xxx.tsx ＋ Xxx.css（var() のみ）＋ Xxx.stories.tsx」で新設した。既存の `Drawer` / `Modal` / `Popover` は触らない。
- **ADR-067**（デザイントークン強制）: 新設 CSS は既存トークンの `var()` のみ。4つの CSS 関所を通過。
- **ADR-027**（i18n）: 文言は既存キー（`inbox.mobileFilters` / `inbox.tab*` / `inbox.filterUnread` / `inbox.filterFollowUp` / `inbox.platform*` / `common.close`）。新規キーなし。
- **ADR-073**（stories 必須）: `frontend/src/components/Sheet.stories.tsx` を3本用意。`check:stories` 緑。
- **ADR-064**（PC の Meta 再現）: PC の帯は従来どおり。抵触しない。
- **直前の便**: [../inbox-manage-icon/design.md](../inbox-manage-icon/design.md)（管理ボタンのアイコン化）。同じ検索欄のボタンを扱う。

## 9. 外部・過去事例の参照と我々への応用

| 事例 | 何を参照したか | 我々への応用 |
|---|---|---|
| **社内の `Drawer` 金型** | Esc・背景クリック・フォーカストラップ・フォーカス復帰・ポータル描画・`role="dialog"` の実装 | **そのまま踏襲**した。新しい作法を発明していない |
| **社内のカルテ（受信箱）** | スマホでは下から出るボトムシートにしている（`.inbox-right-panel` を `@media` で変換） | 「スマホは下から出す」が社内の既存の作法であることの裏付け |
| **社内の MobileShell の「もっと」シート** | 下から出るシートでメニューを出す | 同上 |
| **WhatsApp の絞り込み中の画面** | **未取得**（検索欄を触るとキーボードが開くため当時保留・benchmark の未取得リスト1番） | **比較材料が無いことを明記**し、PO 判断に基づいて進めた |

**採用しなかったもの**: `Modal`（画面中央・PO 選択は下から出る形）。`Popover`（360px で端に寄って切れる恐れ・会話ヘッダで実際に起きている）。`Drawer` の改造（22ページへ波及）。

## 10. 維持の仕組み

- 守り手: `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts`（基準 #1〜#8 を3幅で検査）、`.github/workflows/e2e.yml` のジョブ `visual-language`、`frontend/package.json` の `check:all`（`check:stories` と4つの CSS 関所を含む）、`UI governance gate`。
- 対象: 帯の復活、シートが開かない／閉じない、選択肢が 44px 未満になる、PC・タブレットへの波及、生の値・色コードの直書き、stories の欠落。
- 関所が無い部分: **シートが「下から」出ているか（動きの向き）は機械で検査していない**。`transform: translateY` の指定は CSS にあるが、画面検査は開閉の有無だけを見る。向きの確認は**投入後の実機**で行う（基準 #10）。
