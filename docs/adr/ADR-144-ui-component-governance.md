# ADR-144: UI共通部品の遵守ガバナンス

**Status:** Accepted
**Date:** 2026-06-25
**Authors:** shingo-ops, Hikky-dev
**Related:** ADR-067（デザイントークン強制）

---

## Context

`components/` に共通金型（Storybook 登録済）があるが、`pages/` 配下の主要画面は
金型を使わず生の UI 部品を各自実装している。

recon 実測（2026-06-25）:
- 生 `<select>` : 118 件
- 生 `<input type="text"|"search">` : 16 件
- 自作タブ（tab 系 className）: 20 件

結果として:
1. 一箇所の UI 修正が他画面に波及しない（共通化の恩恵がない）
2. 画面間で見た目が不統一になる
3. PO が把握しないまま独自実装が増殖する

---

## Decision

### 1. 原則（蛇口を締める）

`pages/` 配下の UI は原則 `components/` の共通金型を使う。
以下の新規ハードコードを禁止とし、CI ゲートで新規追加分を赤にする。

| 禁止対象 | 推奨代替 |
|---------|---------|
| 生 `<select>` | `<Select>` 金型 |
| 生 `<input type="text"\|"search"\|省略>` | `<TextField>` / `SearchBar` 相当 |
| 自作タブ（className に `tab` を含む div/nav/button 等） | `<Tabs>` / `OverflowTabs` 相当 |
| 色直値 `#xxx` / 生 px のインラインスタイル | ADR-067 に統合・継承 |

### 2. CI ゲート（`scripts/check-ui-governance.js`）

- **対象**: PR の変更ファイル中 `frontend/src/pages/**/*.tsx`
- **除外**: `*.stories.tsx` / `design-system/` / `design-preview/`
- **判定**: BASE/HEAD 両 SHA の全文を `git show` で取得し、種別ごとの件数を比較。
  `HEAD件数 > BASE件数` なら exit 1（赤）。既存 118+16+20 件は赤化しない。
- **例外口**: `{/* ui-allow: <理由> (#<課題番号>) */}` を違反要素の直前行または同行に付与。
  理由と課題番号の両方が必須。番号なしは無効（赤のまま）。

### 3. 色ゲートは ADR-067 に統合・継承

インラインスタイルへの色直値・生 px 禁止は ADR-067 の `no-restricted-syntax`
（`eslint.config.js:40-115`）が実装済かつ `Lint & Dark Mode Check (ADR-067)` として
required check 登録済。本 ADR では追加実装しない。

射程の正直な記載: ESLint はインラインスタイルのみ対象。`className` / `.css` 内の
直値は `check:css-colors` / `check:css-values` が別途担当。

### 4. 金型がない場合の手順

1. 実装を止め PO に報告する
2. PO 許可を得てから `components/` に金型を新設する
   (`Xxx.tsx` + `Xxx.css`（var() のみ）+ `Xxx.stories.tsx` の作法で）
3. 金型登録後にそれを使って実装する

### 5. 既存の独自実装

差分のみ検査のため既存実装（118+16+20 件）は赤化しない。
移行（金型への置き換え）は別トラック・別 PR で 1 ページ 1 部品ずつ順次行う。

---

## Consequences

- 蛇口を締める：今後の独自実装増殖を機械的に止める
- 床（既存）は別途移行トラックで拭く（本 ADR の射程外）
- タブ/検索欄は代替金型（OverflowTabs/SearchBar）が未存在のため、移行フェーズで
  新設するまで当面は `ui-allow` 例外コメントに依存する（検出精度もタブが最低）
- Chromatic 廃止により見た目の自動回帰検出が無く、金型変更時は PO 目視依存（別バックログ）
- Ruleset 必須登録は安定確認後に別手順で実施（dangling-route-gate.yml の前例に倣う）

---

## Acceptance Criteria

| # | 基準 | 検証方法 |
|---|------|---------|
| AC-1 | 本 ADR が `docs/adr/` に実在・Accepted | ファイル存在確認 |
| AC-2 | `pages/` に生 `<select>` 1 個追加 PR → 赤 | planted violation + CI ログ |
| AC-3 | `pages/` に複数行 `<input type="text">` 追加 PR → 赤 | planted violation + CI ログ |
| AC-4 | インライン `style={{ color: "#fff" }}` 追加 PR → 赤 | planted violation + 既存 ESLint |
| AC-5 | 追加なしの PR で関所が緑（既存 118+16+20 件が赤化しない） | 現行 develop で緑確認 |
| AC-6 | `node scripts/tests/test-ui-governance.js` が緑（22 件） | テスト実行ログ |
| AC-7 | CC 依頼テンプレが `docs/CC_UI_GOVERNANCE.md` に実在 | ファイル存在確認 |

---

## 関連 ADR / ファイル

- ADR-067: デザイントークン強制システム
- `scripts/check-ui-governance.js`: CI ゲート本体
- `scripts/tests/test-ui-governance.js`: 自動テスト
- `.github/workflows/ui-governance-gate.yml`: CI ワークフロー（非必須）
- `docs/CC_UI_GOVERNANCE.md`: CC 遵守テンプレ
- `docs/BRANCH_PROTECTION_SETUP.md §8`: required check 登録手順（安定後）
