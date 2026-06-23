# 設計 — schedule-css-height-restore

**対象 ADR**: ADR-067（デザイントークン強制）
**recon**: docs/handoff/schedule-css-height-restore/recon.md
**日付**: 2026-06-23
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

- **P0 PR #2486（pages-layout.css sticky 除去）**: 共有クラスへの用途特化汚染を元に戻す前例。本件は専用クラスの必要定義が丸ごと消えた同型問題。
- **PR #2453（原因コミット f5ea8ec7）**: 「fix schedule follow-up」という名目のリファクタが schedule.css の高さチェーン 6 プロパティを削除。PR #2472 の revert が schedule.css を対象外にしたため修正漏れ。
- **CSS flexbox 定石（MDN 等）**: 高さチェーンは `height:100%` → `flex:1` → `min-height:0` → `overflow-y:auto` の四点セットで成立。一点でも欠けると折りたたみが発生する。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `/schedule` 週表示でグリッドが正常高さ・グリッド内スクロール | シークレットで `/schedule` 目視 |
| ヘッダー/本体の左余白が他ページ（ダッシュボード）と一致 | 左余白目視比較 |
| 差分が `schedule.css` ＋ docs のみ | `git diff --stat origin/main...HEAD` |
| CI 全緑（ADR-067 系・process-artifacts gate 含む） | GitHub Actions |
| `migrations`/`deploy.yml`/本番 scripts/backend 変更なし | `git diff --name-only origin/main...HEAD` |

---

## 技術 How

`frontend/src/pages/schedule.css` を `7c5a5ea2`（PR #2432, 2026-06-21）時点の値へ選択的復元。

### 変更内容（6 プロパティ群）

**1. `.schedule-page` に 2 行を復活**
```css
height: 100%; /* fill .app-content so page-level overflow-y never fires */
padding: var(--page-padding-y) var(--page-padding-x); /* 他ページ共通ガター */
```

**2. `.schedule-shell__header` に 1 行を復活**
```css
padding-right: var(--page-header-avatar-clearance); /* #7: 固定アバターとのクリアランス 68px */
```

**3. `.schedule-shell__content` に 2 行復活 + `align-items` 修正**
```css
grid-template-rows: 1fr; /* fill all remaining height so .schedule-main can stretch */
flex: 1;                 /* consume remaining height in .schedule-page flex column */
align-items: stretch;    /* start → stretch へ戻す */
```

**4. `.schedule-main` に 1 行を復活**
```css
min-height: 0; /* allow flex children to shrink within the constrained grid cell */
```

**5. `.schedule-main__surface` に 1 行を復活**
```css
flex: 1; /* fill .schedule-main flex column */
```

**6. `.schedule-grid__viewport` ブロック全体を復活**
```css
/* scroll container: only the time body scrolls */
.schedule-grid__viewport {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}
```

### ADR-067 準拠

全値は既存トークン参照（`--page-padding-x/y`・`--page-header-avatar-clearance`）または定数（`1fr`・`auto`・`0`・`100%`）。hex/直値の新規追加なし。

---

## 弊害・トレードオフ

- 変更は `frontend/src/pages/schedule.css` 1 ファイルのみ。
- `pages-layout.css` は P0（PR #2486）で確定済みのため**触らない**。
- `--topbar-height` は schedule.css で参照しないため P0 との干渉なし。
- schedule ページに閉じた変更（共有クラス不使用）。他ページへの波及なし。
- ダーク/ライト parity: 色変更を含まないため差分なし。

---

## 継続

- デプロイ後、シークレットで `/schedule` を実機確認（グリッド高さ・スクロール・余白）。
- category API / user_id param 復元（P1b）は別件。`calendar_events` に `category` カラム未存在のため migration 必須 → ADR-136 に基づき PO GO 必要。
