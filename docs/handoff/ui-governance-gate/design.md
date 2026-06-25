# Phase 3 設計 — ui-governance-gate

**対象ADR**: ADR-144  
**recon**: docs/handoff/ui-governance-gate/recon.md  
**日付**: 2026-06-25  
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

- **dangling-route-gate（社内前例）**: `.github/workflows/dangling-route-gate.yml` が「非必須ゲートとして導入→安定後に Ruleset 必須化」という段階導入パターンを確立。本ゲートも同パターンを踏襲（`ui-governance-gate.yml` はコメントに明記）。
- **ADR-067（社内前例）**: `frontend/eslint.config.js:40-115` の `no-restricted-syntax` がインラインスタイル色/px を ESLint で強制。本ゲートはその射程外（`pages/` の JSX 構造違反）を補完する形で設計。既存ゲートと重複しないよう ADR-144 §3 で「色ゲートは ADR-067 に統合」と明記。
- **BASE/HEAD diff 方式（業界標準）**: 既存違反を赤化せず新規追加分のみ検出するパターンは Danger.js 等のツールで一般的。`git show <sha>:path` で全文取得→件数比較する方式は社内 dangling-route-check の踏襲であり、追加ツール不要で実現。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| ADR-144 が `docs/adr/` に実在・Accepted | `docs/adr/ADR-144-ui-component-governance.md` のファイル存在確認 |
| `pages/` に生 `<select>` 1個追加 PR → 赤 | planted violation + CI ログ（PR本文に証拠ログ掲載）|
| `pages/` に複数行 `<input type="text">` 追加 PR → 赤 | planted violation + CI ログ（PR本文に証拠ログ掲載）|
| インライン `style={{ color: "#fff" }}` 追加 PR → 赤 | 既存 ESLint `check:all` が担当（ADR-067 `frontend/eslint.config.js:40-48`）|
| 追加なしの PR で関所が緑（既存 118+16+20 件が赤化しない） | 現行 develop で緑確認（PR本文に証拠ログ掲載）|
| `node scripts/tests/test-ui-governance.js` が緑（22件） | テスト実行ログ（PR本文に証拠ログ掲載）|
| CC依頼テンプレが `docs/CC_UI_GOVERNANCE.md` に実在 | `docs/CC_UI_GOVERNANCE.md` のファイル存在確認 |

---

## 技術 How・KPI

- **検出方式**: `git show <BASE_SHA>:<path>` と `git show <HEAD_SHA>:<path>` で全文取得→種別ごとに件数比較。増加分のみ exit 1。
- **KPI-1**: planted select → CI 赤（BASE=0, HEAD=2）
- **KPI-2**: planted multiline input → CI 赤（F-E1: type が次行にある 224 件の既存パターンを確認済み）
- **KPI-3**: planted custom-tab → CI 赤（/tab/ && !/table/ トークン判定）
- **KPI-4**: inline color → 既存 ESLint が担当（`eslint.config.js:40-48`）
- **KPI-5**: 既存 118+16+20 件 → CI 緑（BASE/HEAD 両方に存在→件数同→増分ゼロ）
- **KPI-6**: test 22/22 → `node scripts/tests/test-ui-governance.js` exit 0

---

## 弊害・トレードオフ

- タブ検出精度は最低（`/tab/` 語を含む静的 className のみ）。動的 className や条件式は検出できない。→ 既知のトレードオフ（ADR-144 §Consequences に記載）
- ESLint は `pages/` 限定ではなく全 tsx を対象とするが、本ゲートは `pages/` のみ。mix-component ファイルが増えた場合は別途 ADR で検討。
- `ui-allow:` 番号体系が未確定（本番運用前に PO 確認が必要）。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `scripts/check-ui-governance.js` 新設 | Generator |
| 2 | `scripts/tests/test-ui-governance.js` 新設（22件） | Generator |
| 3 | `.github/workflows/ui-governance-gate.yml` 新設 | Generator |
| 4 | `docs/adr/ADR-144-ui-component-governance.md` 新設 | Generator |
| 5 | `docs/CC_UI_GOVERNANCE.md` 新設 | Generator |
| 6 | `CLAUDE.md` UIガバナンス遵守セクション追記 | Generator |
| 7 | planted violation で CI 赤確認 → 削除 | Generator |

---

## 継続

- Ruleset 必須化: 安定確認後に `docs/BRANCH_PROTECTION_SETUP.md §8` 手順で PO GO → 別 PR
- `ui-allow:` 番号体系: 本番運用前に PO と確定（GitHub Issue 番号を想定）
- 床掃除（既存 118+16+20 件の金型化）: 別トラック・別 PR で 1 ページ 1 部品ずつ
