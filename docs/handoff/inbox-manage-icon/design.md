# 設計: 管理ボタンを丸いチェックのアイコンだけにする

対象 ADR: ADR-067（デザイントークン強制）／ADR-144（UI共通部品のガバナンス）／ADR-027（i18n）
recon: [recon.md](./recon.md)（`docs/handoff/inbox-manage-icon/recon.md`）
PO 指摘・選択: 2026-10-13「同じアイコンが2つ並んでるので分かりづらい、管理側をアイコンだけにしたい」／アイコンは**丸いチェック**

## 1. なぜ直すのか（事実のみ）

- 検索欄の右に並ぶ2つのボタンが**同じ `filter` アイコン**を使っていた（recon A）。実機で隣り合っていることも確認済み。
- 管理ボタンの主な動作は**選択モードに入る**こと（recon D1）。`filter`（漏斗）は意味が合っていない。
- あわせて `size={13}` という**生の数値**が入っていた（recon B1）。

## 2. 変更するファイルと、変更前後

### 2-1. `frontend/src/constants/icons.tsx`（アイコンの登録）

```tsx
// outline の import に追加
CheckCircleIcon as CheckCircleOutlineIcon,

// ラッパ
const CheckCircleOutline = hi(CheckCircleOutlineIcon);

// INBOX_ACTION_ICONS に追加
select: CheckCircleOutline, // CheckCircleIcon outline — 選択モード
```

**outline を選ぶ理由**: 未選択の状態で「すでに選び終わった」ように見せないため。`heart`（outline）/`heartFilled`（solid）と同じ使い分け（recon C4）。

### 2-2. `frontend/src/pages/inbox/InboxConversationList.tsx`

```tsx
<button
  className={`inbox-manage-btn${selectMode ? " active" : ""}`}
  onClick={toggleSelectMode}
  aria-pressed={selectMode}
  aria-label={t("inbox.manage")}        {/* 追加: アイコンだけでも読み上げで分かる */}
>
  <INBOX_ACTION_ICONS.select size={ICON.md} aria-hidden="true" />   {/* filter → select / 13 → ICON.md */}
  <span className="inbox-manage-label">{t("inbox.manage")}</span>   {/* 文言を包んで CSS で隠せるようにする */}
</button>
```

あわせて同ファイルの `size={14}`（5箇所）を `ICON.sm` に直す。**`ICON.sm` は 14 なので見た目は変わらない**（recon B2）。

### 2-3. `frontend/src/pages/inbox/InboxPage.css`（`@media (max-width: 767px)` の内側のみ）

```css
.inbox-manage-label { display: none; }
```

**スマホだけ文言を隠す**。PC・タブレットでは「管理」の文言を残す（recon F の判断）。

### 2-4. `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts`

検査を1件追加（スマホ）＋ PC 側に1行追加。

## 3. 触らない範囲（明示）

- **ボタンの動作**（`toggleSelectMode`・ドロップダウン・一括アクションバー）: 変更しない。
- **絞り込みボタン**: 変更しない（`filter` のまま。漏斗は絞り込みに合っている）。
- **`frontend/src/constants/iconSizes.ts`**: 自動生成ファイルなので触らない（recon B3）。既存の値だけ使う。
- **PC の文言**: 残す。
- **API・DB・migrations**: 触らない。

## 4. 守る決まり（CI が検査する）

`check:all`（25項目／`check:icon-sync`・`lint`（i18n ハードコード検出）を含む）／`Lint & Dark Mode Check (ADR-067)`／`画面検査（受信箱 3幅 Playwright）`／`Frontend lint & custom checks`（単体テスト）。

## 5. 検証方法（受け入れ基準）

| # | 基準 | 検証方法 |
|---|---|---|
| 1 | 390px で**2つのボタンのアイコンが別物** | `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts` で svg の `path` の `d` を比べ、一致しないこと |
| 2 | 390px で**管理の文言が出ない** | 同検査で `innerText` が空であること |
| 3 | **文言が無くても読み上げで分かる** | 同検査で `aria-label` が入っていること |
| 4 | **PC・タブレットでは文言が出る** | 同検査の PC・タブレット側で `.inbox-manage-label` が表示されること |
| 5 | 実測値が記録に残る | 同検査の `search-row-buttons` 添付 |
| 6 | 既存の基準がすべて緑のまま | 同ファイルの既存7件 |
| 7 | `npm run check:all` 25/25 ／ 単体テスト全件合格 | 実行して出力を PR に貼る |
| 8 | **投入後の実機で2つのアイコンが見分けられる** | デプロイ後に撮影して確認し PR に追記 |

## 6. 戻し方

このPRの revert のみ。トークン・API・DB を変更しないため波及はない。

## 7. 残るリスク（正直に）

1. **アイコンの差し替えは PC にも及ぶ**（文言は残る）。PC では「丸いチェック＋管理」になる。`filter` は意味が合っていなかったので改善だが、見た目は変わる。ADR-064 は管理ボタンに言及していない（recon E1）。
2. **`aria-label` と見える文言が重複する**（PC では両方 `t("inbox.manage")`）。値が同一なので読み上げ名は変わらない。
3. **選択モード中もアイコンは outline のまま**（variant は import 時に固定で、CSS で solid へ切り替えられない）。選択中は `.active` クラスで色が変わる既存の作りに任せる。
4. 同ファイルの `size={14}` → `ICON.sm` は同値だが、**万一ブラウザの丸めが違えば1px ずれる可能性**がある（14 と 14 なので実質ゼロ）。

## 8. 相互参照

- **recon**: [recon.md](./recon.md)（`docs/handoff/inbox-manage-icon/recon.md`）— A の事実確認、B の規約違反、C の供給元と在庫、D の動作、E の ADR 関係、F の範囲判断。
- **ADR-144**（UI共通部品のガバナンス）: 新しい部品は作らず、登録済みのアイコン群に1つ追加するだけ（recon E2）。
- **ADR-067**（デザイントークン強制）: サイズは `frontend/src/constants/iconSizes.ts` のトークン（ICON.md / `ICON.sm`）経由にした。生の数値を6箇所（13×1・14×5）除去。
- **ADR-027**（i18n）: 文言は既存キー `inbox.manage` をそのまま使う。新規キーなし。`aria-label` も `t()` 経由。
- **ADR-064**（Inbox Meta 完全再現・PC）: 管理ボタンに言及がないため抵触しない（recon E1）。
- **直前の便**: [../inbox-mobile-touch-targets/design.md](../inbox-mobile-touch-targets/design.md)（押す場所の44px化）。同じ検索欄を扱う。

## 9. 外部・過去事例の参照と我々への応用

| 事例 | 何を参照したか | 我々への応用 |
|---|---|---|
| **Gmail / iOS の選択モード** | 複数選択に入る操作は**丸いチェック**で表す（業界の通例） | 管理ボタンのアイコンに採用。漏斗（絞り込み）と形がはっきり違う |
| **社内の前例（`heart` / `heartFilled`）** | 未押下は outline・押下済みは solid で使い分けている | 未選択の状態で「選び終わった」ように見せないため outline を採用 |
| **PageLayout の slimHeaderOnMobile（PR 4148）** | スマホで文言を**視覚的に隠し、読み上げには残す** | 管理の文言も同じ作法で隠す（`aria-label` で役割は伝える） |
| **お手本（WhatsApp）の実測** | 一覧の上部は検索と絞り込みが中心で、操作は絞られている | 検索欄に置くボタンは2つまでとし、役割が重ならないようにする |

**採用しなかったもの**: 横三点（`NAV_ICONS.more`・登録済みで作業はゼロだが、会話ヘッダの三点メニューと同じ形になり役割が紛らわしい）。一覧系アイコン（`QueueListIcon` 等・「選ぶ」動作が伝わりにくい）。

## 10. 維持の仕組み

- 守り手: `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts`（2つのアイコンが別物・スマホで文言を出さない・読み上げ名がある・PC では文言が出る）、`.github/workflows/e2e.yml` のジョブ `visual-language`、`frontend/package.json` の `check:all`（`check:icon-sync` と i18n ハードコード検出を含む）。
- 対象: 同じアイコンの再発、スマホでの文言の復活、読み上げ名の欠落、PC での文言の消失、生の数値のアイコンサイズ。
- 関所が無い部分: **アイコンの意味が動作に合っているか**は機械で検査できない。アイコンを差し替えるときは recon D（そのボタンの実際の動作）を書き直す運用で守る。
