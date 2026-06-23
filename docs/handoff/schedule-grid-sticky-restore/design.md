# 設計 — schedule-grid-sticky-restore（P1a-2）

**対象 ADR**: ADR-067（デザイントークン強制）
**recon**: docs/handoff/schedule-grid-sticky-restore/recon.md
**日付**: 2026-06-23
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

- **P0 PR #2486（pages-layout.css sticky 除去）**: 共有クラスへの用途特化汚染を戻した前例。
- **P1a PR #2496（schedule.css 高さチェーン復元）**: 外側スクロール容器（viewport + 高さチェーン）を復元した直近前例。本件はその内側（grid 内 sticky）の補完。
- **CSS sticky の定石（MDN）**: スクロール容器内で `position:sticky; top:N` を積層し `z-index` で重なり順を制御。容器（`overflow-y:auto`）が既に P1a で復元済みのため、今回は sticky 宣言を追加するだけ。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `/schedule` 週表示で日付ヘッダー・終日行が固定、時間 body のみスクロール | シークレットで `/schedule` 実機スクロール |
| P1a の達成事項（余白・グリッド高さ）に回帰なし | シークレット目視 |
| 他ページ（ダッシュボード等）に変化なし | シークレット目視 |
| 差分が `schedule.css` ＋ docs のみ | `git diff --stat origin/main...HEAD` |
| CI 全緑（ADR-067 系・process-artifacts gate 含む） | GitHub Actions |
| `migrations`/`deploy.yml`/本番 scripts/backend 変更なし | `git diff --name-only origin/main...HEAD` |

---

## 技術 How

`frontend/src/pages/schedule.css` に計11行を `7c5a5ea2`（PR #2432, 2026-06-21）逐語のまま追加。既存行は変更せず追記のみ。

### 変更内容

**(1) 変数3個** — `.schedule-page, .schedule-settings { }` 末尾（`--schedule-control-border` の直後）に追加:
```css
  /* day head height: pad-top(8) + weekday-name-lh(18) + gap(2) + day-circle(46) + pad-bottom(8) = 82px */
  --schedule-day-head-h: 82px;
  /* sticky z-index layers within .schedule-grid__viewport scroll container */
  --schedule-header-z: 2;
  --schedule-allday-z: 1;
```

**(2) `.schedule-grid__header`** — `border-bottom` 行の後に追加:
```css
  position: sticky;
  top: 0;
  z-index: var(--schedule-header-z);
  background: var(--bg-surface);
```

**(3) `.schedule-grid__allday-row`** — `border-bottom` 行の後に追加:
```css
  position: sticky;
  top: var(--schedule-day-head-h);
  z-index: var(--schedule-allday-z);
  background: var(--bg-surface);
```

### ADR-067 準拠

- `background: var(--bg-surface)` — 既存トークン参照。
- `z-index: var(--schedule-header-z)` / `var(--schedule-allday-z)` — 今回定義する変数（値は `82px/2/1` の #2432 確定値）。
- `top: 0` / `top: var(--schedule-day-head-h)` — 計算式コメント付きの #2432 確定値。
- hex/直値の独自追加なし。

---

## 弊害・トレードオフ

- 変更は `frontend/src/pages/schedule.css` 1ファイルのみ（docs 含め3ファイル）。
- `background: var(--bg-surface)`（不透過）は、スクロール時に時間 body が固定ヘッダーの裏に透けないための塗り。P0 で透過に戻した `.page-layout-header` とは別物・別目的。
- `z-index` 階層: `header(2) > allday(1) > body(未指定)` — グリッド外の z 環境に影響しない。
- `--schedule-day-head-h: 82px` の整合: #2432 当時の計算式 `pad(8)+weekday(18)+gap(2)+circle(46)+pad(8)=82px` をコメントで明記。実機確認で終日行の top 位置を目視検証。
- schedule ページに閉じた変更（共有クラス不使用）。他ページへの波及なし。

---

## 継続

- デプロイ後、シークレットで `/schedule` を実機確認（週表示スクロール・日付固定・終日固定）。
- P1b（schedule ヘッダー他ページ統一）は別件。
- P1c（category API / user_id param 復元）は migration 必須・ADR-136 PO GO 要。
