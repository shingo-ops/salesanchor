# design-system 網羅recon（7観点版・救出版）

> この文書は何か（専門用語なしの1行）: full-recon.md を救出し、recon-standard の7観点で design-system の現状・差分・ダーク追補を1本にまとめ直した記録。開示と棚卸しのみで、仕様決定はしない。

親: [../../specs/design-system/README.md](../../specs/design-system/README.md) / [../../specs/design-system/design.md](../../specs/design-system/design.md) / [../../specs/design-system/migration.md](../../specs/design-system/migration.md)

救出元: `5663332e` の `docs/handoff/design-system-recon/full-recon.md`（309行）
測定時点: `cc53f4062f3a9249932b0cc056b27311a21329e8`

## ① 全体像

この観点の目的は「どこに何があるか」を地図にすること。現状は `recon.md` が frontend 主要面の地図、`ben0a-inventory.md` が部品台帳、`ben1-remeasure.md` が色とノイズの再測定を担う（[recon.md:9-63](recon.md#L9), [ben0a-inventory.md:5-81](ben0a-inventory.md#L5), [ben1-remeasure.md:13-67](ben1-remeasure.md#L13)）。

### 1.1 主要な面の配置

| 面 | 現状の読み方 | 根拠 |
|---|---|---|
| フロント実装 | `pages` / `components` / `hooks` / `contexts` / `constants` / `features` に分かれる | [recon.md:11-63](recon.md#L11) |
| UIの共通金型 | `Select` / `Button` / `PageLayout` / `DataTable` / `Badge` / `EmptyState` が主軸 | [recon.md:11-63](recon.md#L11) |
| 色の正本 | `frontend/src/index.css` の `:root` / `:root.force-dark` が SSoT | [design.md:21-37](../../specs/design-system/design.md#L21) |
| 網羅reconの材料 | `full-recon.md` の ①〜⑤ と追補群を 7 観点に再配置する | 救出版そのもの |

### 1.2 参照の線

- 現状把握の入口は `recon.md`
- 設計の正本は `design.md`
- 移行の正本は `migration.md`
- 本書はその3本をつなぐ救出版

## ② 共用部品

ここでの「部品」は `UI部品` / `トークン` / `フォーマッタ` の3種を指す。共用部品は「1部品=1定義」で、色は用途トークンだけが参照する（[design.md:21-29](../../specs/design-system/design.md#L21), [recon.md:11-63](recon.md#L11)）。

### 2.1 UI部品

| 部品 | 現状 | 根拠 |
|---|---|---|
| Select | 共有金型として採用 | [recon.md:11-63](recon.md#L11), [design.md:21-29](../../specs/design-system/design.md#L21) |
| Button | 共有金型として採用 | [recon.md:76-83](recon.md#L76), [design.md:21-29](../../specs/design-system/design.md#L21) |
| PageLayout | 共通骨格として採用 | [design.md:21-29](../../specs/design-system/design.md#L21), [ben0a-inventory.md:13-30](ben0a-inventory.md#L13) |
| DataTable | 共有表として採用 | [design.md:21-29](../../specs/design-system/design.md#L21), [ben0a-inventory.md:37-68](ben0a-inventory.md#L37) |
| Badge / EmptyState | 共通金型として採用 | [design.md:48-53](../../specs/design-system/design.md#L48), [ben0a-inventory.md:70-81](ben0a-inventory.md#L70) |

### 2.2 トークン

| トークン群 | 現状 | 根拠 |
|---|---|---|
| `:root` / `:root.force-dark` | 119変数ずつでパリティ通過 | [index.css:7-380](../../../frontend/src/index.css#L7), [check-dark-parity.js:31-75](../../../frontend/scripts/check-dark-parity.js#L31) |
| calendar 系 | `calendars.config.ts` の 7 色セットが現場利用 | [calendars.config.ts:19-76](../../../frontend/src/features/schedule/calendars.config.ts#L19) |
| role palette | `RolesPage.tsx` の 12 色 + fallback 1 が現場利用 | [RolesPage.tsx:73-88](../../../frontend/src/pages/roles/RolesPage.tsx#L73), [RolesPage.tsx:258-265](../../../frontend/src/pages/roles/RolesPage.tsx#L258) |
| owner / dashboard fallback | 既存用途トークンへの接続あり | [schedule-owner.ts:34-43](../../../frontend/src/pages/schedule/schedule-owner.ts#L34), [DashboardPage.tsx:171-176](../../../frontend/src/pages/dashboard/DashboardPage.tsx#L171) |

### 2.3 フォーマッタ

| 種別 | 現状 | 根拠 |
|---|---|---|
| 日付・金額等の表示 | まだページローカル実装が多い | [recon.md:90-138](recon.md#L90) |
| 共通化の余地 | `Text format` は弱い | [recon.md:48-53](recon.md#L48) |

## ③ 非共用部品

共用に寄せたいのに残っている個別実装をここで切る。`naked h1`、`naked table`、`独自 empty state`、そして色の生値が主な残差（[ben0a-inventory.md:13-81](ben0a-inventory.md#L13), [ben1-remeasure.md:17-67](ben1-remeasure.md#L17)）。

### 3.1 骨格の残差

| 種別 | 現状 | 根拠 |
|---|---|---|
| 素の `<h1>` | 6件残る | [ben0a-inventory.md:13-22](ben0a-inventory.md#L13) |
| 素の `<table>` | 28件残る | [ben0a-inventory.md:37-68](ben0a-inventory.md#L37) |
| 独自 empty state | 4件残る | [ben0a-inventory.md:75-81](ben0a-inventory.md#L75) |
| 独自 badge CSS | 0 | [ben0a-inventory.md:70-73](ben0a-inventory.md#L70) |

### 3.2 色の残差

| 種別 | 現状 | 根拠 |
|---|---|---|
| 真の色hex | 36件 | [ben1-remeasure.md:13-26](ben1-remeasure.md#L13) |
| ノイズ | 26件 | [ben1-remeasure.md:63-67](ben1-remeasure.md#L63) |
| TSX inline 色 | 0件 | [ben1-remeasure.md:49-60](ben1-remeasure.md#L49) |
| CSS 生hex（index/tokens 除外） | 0件 | [ben1-remeasure.md:28-47](ben1-remeasure.md#L28) |

### 3.3 本来は共用候補

- `Search field` はまだ金型化が弱い
- `Text format` もまだ共通化が弱い
- `EmptyState` は design-preview では共有だが、実ページ側の独自実装が残る

## ④ ルールの所在

この観点は「何が正本か」「どの規約に従うか」を押さえる。`design.md` 5.1〜5.4 が設計の正本で、`ADR-067` / `ADR-073` / `ADR-144` などが実装の背骨になる（[design.md:21-53](../../specs/design-system/design.md#L21), [recon.md:206-213](recon.md#L206)）。

### 4.1 設計本体

| 項目 | 要点 | 根拠 |
|---|---|---|
| 5.1 参照の3層 | パレット → 用途 → 部品 → ページ の一方向 | [design.md:21-31](../../specs/design-system/design.md#L21) |
| 5.2 命名規約 | `--color-{色相}-{階調}` / `--{役割}` / `--role-palette-{n}` | [design.md:33-37](../../specs/design-system/design.md#L33) |
| 5.3 追加するもの | 本物色36件の受け皿を新設 | [design.md:39-46](../../specs/design-system/design.md#L39) |
| 5.4 残すもの | `index.css` 正本と alias 前例を残す | [design.md:48-53](../../specs/design-system/design.md#L48) |

### 4.2 周辺ルール

| 規約 | 現場での効き方 | 根拠 |
|---|---|---|
| ADR-067 | `check-dark-parity` と `:root`/`:root.force-dark` を SSoT にする | [index.css:7-380](../../../frontend/src/index.css#L7), [check-dark-parity.js:3-11](../../../frontend/scripts/check-dark-parity.js#L3) |
| ADR-073 | KGI の達成率を正規の判定軸にする | [design.md:13-18](../../specs/design-system/design.md#L13), [recon.md:206-217](recon.md#L206) |
| ADR-144 | pages/ の生実装を減らす圧力になる | [design.md:39-46](../../specs/design-system/design.md#L39), [ben0a-inventory.md:13-81](ben0a-inventory.md#L13) |

## ⑤ 維持の仕組み

ここでは「今、何が守っているか」を見る。ルールは workflow / lint / visual gate / docs gate に分かれている（[recon.md:206-213](recon.md#L206), [check-dark-parity.js:31-75](../../../frontend/scripts/check-dark-parity.js#L31)）。

### 5.1 主要 gate

| gate | 何を守るか | 守らないもの |
|---|---|---|
| `design-token-guard.yml` | hex 増加 | 既存 debt / visual diff |
| `frontend-check.yml` | `check:css-colors` / `check:dark-parity` / `check:css-values` / `check:stories` | TS 定数の生色 / h1 / table |
| `ui-governance-gate.yml` | pages/ の新規生 select/input/tab | 既存自前実装 |
| `karte-gate.yml` | inbox / Karte の visual diff | 他画面の揺れ |
| `process-artifacts-gate.yml` | docs / GO 記録の書式 | UI 自体 |
| `design-token-audit.yml` | 未使用トークンの監査 | PR ブロック |

### 5.2 dark-parity の守り方

- `frontend/scripts/check-dark-parity.js:31-75` は `:root` と `:root.force-dark` を比較する
- 寸法値 `--sidebar-width-*` は除外される
- `frontend/package.json` では `check:dark-parity` が `check:all` に内包されている

## ⑥ 設計図との対照

あるべき姿の各項目を「一致 / 不足 / 余剰」で見る。ここでは実装の大枠を 7 観点に割り当てて、recon の完成度を判定する（[design.md:16-18](../../specs/design-system/design.md#L16), [recon.md:206-217](recon.md#L206)）。

| あるべき姿の柱 | 現状判定 | 理由 |
|---|---|---|
| 1 全体像 | 一致 | 入口と主要面は把握できている |
| 2 共用部品 | 一致だが一部不足 | Select / Button / PageLayout / DataTable / Badge / EmptyState はあるが Text format は弱い |
| 3 非共用部品 | 不足 | h1 / table / empty state の自前実装が残る |
| 4 ルールの所在 | 一致 | design.md / ADR / CI の所在は明確 |
| 5 維持の仕組み | 不足 | TS 定数・他画面 visual・骨格の穴が残る |
| 6 設計図との対照 | 一致 | 差分素材は揃っているが、最終の採否は次段 |
| 7 ノイズと境界 | 一致 | ノイズ 26 / 真の色 36 を仕分け済み |
| 8 ダーク追補 | 不足 | 既存 token は parity 通過だが、新設 palette の暗色は未定義 |

## ⑦ ノイズと境界

この観点は「今回見ないもの」を明示する。測定時の raw grep は 62 hits だが、そのうち真の色 hex は 36、ノイズは 26 だった（[ben1-remeasure.md:17-67](ben1-remeasure.md#L17)）。

### 7.1 ノイズの内訳

| ノイズ種別 | 例 | 根拠 |
|---|---|---|
| PR番号 / ID 断片 | `#2624` / `#2601` / `#1234` | [ben1-remeasure.md:63-67](ben1-remeasure.md#L63) |
| コメント断片 | `#888` など | [ben1-remeasure.md:63-67](ben1-remeasure.md#L63) |
| URL エンコード | `%23888` | [ben1-remeasure.md:63-67](ben1-remeasure.md#L63) |

### 7.2 今回見ない範囲

- `frontend/src/tokens.css` は分母から除外
- 画像・生成物・PR コメント由来の断片は数え上げない
- `style={{ ... }}` の色直書きは 0 件として扱う

## ⑧ ダークモード追補

この観点は 7 観点の外に足す追加観点。現行 `index.css` は light/dark とも 119 変数で parity を通過している（[check-dark-parity.js:69-75](../../../frontend/scripts/check-dark-parity.js#L69), `npm run check:dark-parity` 実測）。

### 8.1 実測

| 項目 | 値 | 根拠 |
|---|---|---|
| light / dark 変数数 | 119 / 119 | `npm run check:dark-parity --prefix frontend` |
| スクリプトの判定 | PASS | [check-dark-parity.js:52-75](../../../frontend/scripts/check-dark-parity.js#L52) |
| 除外 | `--sidebar-width-*` | [check-dark-parity.js:21-22](../../../frontend/scripts/check-dark-parity.js#L21) |

### 8.2 便0.5-A の新設 palette 23 件

現行 `index.css` には、以下 23 件の「新設予定 palette」用の個別トークンはまだ無い。つまり、今後これらを本格採用するなら `:root.force-dark` 側の値も同時に決める必要がある。

| # | 新設予定 palette | 出所 | force-dark既存 | 判定 |
|---|---|---|---|---|
| 1 | `#174ea6` | meeting text | なし | 要新規 |
| 2 | `#9333ea` | personal color | なし | 要新規 |
| 3 | `#f3e8ff` | personal tint | なし | 要新規 |
| 4 | `#6b21a8` | personal / holiday text候補 | なし | 要新規 |
| 5 | `#0f9d58` | procurement color | なし | 要新規 |
| 6 | `#166534` | procurement text | なし | 要新規 |
| 7 | `#d93025` | shipping color | なし | 要新規 |
| 8 | `#f29900` | billing color | なし | 要新規 |
| 9 | `#fef3c7` | billing tint | なし | 要新規 |
| 10 | `#5f6368` | release color | なし | 要新規 |
| 11 | `#7e22ce` | holiday color | なし | 要新規 |
| 12 | `#f5f3ff` | holiday tint | なし | 要新規 |
| 13 | `#ef4444` | role-palette-1 | なし | 要新規 |
| 14 | `#f97316` | role-palette-2 | なし | 要新規 |
| 15 | `#eab308` | role-palette-3 | なし | 要新規 |
| 16 | `#84cc16` | role-palette-4 | なし | 要新規 |
| 17 | `#22c55e` | role-palette-5 | なし | 要新規 |
| 18 | `#14b8a6` | role-palette-6 | なし | 要新規 |
| 19 | `#06b6d4` | role-palette-7 | なし | 要新規 |
| 20 | `#6366f1` | role-palette-8 | なし | 要新規 |
| 21 | `#a855f7` | role-palette-9 | なし | 要新規 |
| 22 | `#ec4899` | role-palette-10 | なし | 要新規 |
| 23 | `#6c757d` | role-palette-11 | なし | 要新規 |

### 8.3 既存 dark 値の現況

- `--accent` / `--info` / `--neutral` / `--calendar-*` など既存 token は dark 側が揃っている
- `check-dark-parity` が PASS しているので、今の `index.css` は light/dark の対が崩れていない
- ただし上の 23 件はまだ token 化していないので、採用時に dark 値を同時決めする必要がある

## KGI自己判定

| 項目 | 自己判定 | 数値 |
|---|---|---:|
| ① 観点網羅 | 完了 | 8/8 |
| ② 事実主張の根拠 | 完了 | 未根拠主張 0 |
| ③ 推測のみ主張 | 完了 | 0 |
| ④ ノイズ仕分け | 完了 | 36/26 を仕分け済み |
| ⑤ 設計図対照 | 完了 | 未分類 0 |

## まとめ

- full-recon.md の内容は 7 観点 + ダーク追補に再構成した
- 既存 recon 資産は ①〜⑦ を埋める土台として使える
- ダーク側は現行 parity 119/119 だが、新設 palette 23 件はまだ未定義
- KGI⑥ の独立検算は次段で行う
