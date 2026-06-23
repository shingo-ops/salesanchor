# 設計 — page-header-sticky-revert

**対象ADR**: ADR-067（デザイントークン強制）
**recon**: docs/handoff/page-header-sticky-revert/recon.md
**日付**: 2026-06-23
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

- **ADR-087（hub-shell）**: 共通シェルへ寄せ、廃止クラスを CI ブロックした前例。本件「共有クラス保護」と同型。今回の `.page-layout-header` 汚染は同じパターンの再発。
- **`9ab5f6cf`(2026-05-22, `.app-topbar` 廃止)**: DOM 要素を削除した際に `top: var(--topbar-height)` が宙に浮いた前例。廃止トークン/前提に依存した直書きの危険性の実例。
- **shadcn/ui 設計原則**: 共通プリミティブはページ都合で書き換えず、バリアントはローカルに閉じる。今回 #2432 はこれを守らなかった（schedule 用目的を全ページ共有クラスへ直書き）。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `.page-layout-header` から position/top/z-index/background の 4 行が除去されている | `git diff origin/main -- frontend/src/pages-layout.css` で -4 行確認 |
| 残るのは `flex-shrink: 0` と `padding` 行のみ | 同 diff で +0 行・2行のみ残存確認 |
| 変更ファイルが `pages-layout.css` + docs のみ | `git diff --stat origin/main...HEAD` で 3ファイル以内 |
| CI（ADR-067系・process-artifacts gate）全緑 | GitHub Actions |
| デプロイ成功・本番反映 | `gh run list` + headSha 確認 |

---

## 技術 How

`frontend/src/pages-layout.css:62-69` の `.page-layout-header` から PR #2432(`7c5a5ea2`, 2026-06-21) が追加した以下の 4 行を除去する:

```css
position: sticky;
top: var(--topbar-height);
z-index: var(--z-topbar);
background: var(--bg-surface);
```

除去後の `.page-layout-header` は #2432 直前（`2e23c7db`）の定義に戻る:

```css
.page-layout-header {
  flex-shrink: 0;
  padding: var(--page-padding-y) var(--page-header-avatar-clearance) 0 var(--page-padding-x);
}
```

- トークン値そのものは不変（ADR-067 準拠・hex/直値追加なし）
- 共有クラスは schedule 都合で今後触らない
- schedule の「時間グリッドのみスクロール」は `.schedule-grid__viewport { overflow-y: auto }` で既に完結しているため追加対応不要

---

## 弊害・トレードオフ

- 変更は `frontend/src/pages-layout.css` 1ファイルのみ。
- 全 PageLayout ページに「良い向き」で波及（元の透過設計へ復帰）。
- schedule 専用ファイル・トークン・App 周辺には一切触れない。
- `--page-header-avatar-clearance`（右 80px のアバター回避 padding）は除去対象に含めない（残す）。

---

## 継続

- デプロイ後、ダッシュボード/受信箱/在庫表でヘッダー位置・背景グラデ透過を実機確認。
- schedule カレンダー（`/schedule`）で時間グリッドスクロール動作を確認。
- P1（schedule 機能復旧）は別 design doc で対応。
