# design — カレンダー色CSS変数化

親: [../README.md](../README.md)

> 1行要約: `calendars.config.ts` の 7 カレンダー直書き hex を `index.css` の CSS 変数参照に変え、既存土台色を流用できるものは流用し、識別に必要なものだけを新規値として定義する。

## 1. あるべき姿

親テーマ `ideal-state.md` を正本とする。カレンダー色は `index.css` に集約され、`calendars.config.ts` は `var()` 参照だけを持つ。

## 2. KGI（○×）

| # | 合格条件 | 測り方 | 合格ライン |
|---|---|---|---|
| ① | `calendars.config.ts` の直書き hex が 0 件になったか | grep 件数 | 0 |
| ② | `cssVar()` の空箱関数が除去されたか | 定義・呼び出し件数 | 0 |
| ③ | カレンダー用途トークンが `index.css` に定義されたか | 定義件数 ÷ 必要数 | 満数 |
| ④ | 新規追加した独自色が、確定最小セットに限られるか | 新規色数 = 確定最小セット数 | 一致 |
| ⑤ | カレンダー間の識別性（ΔE≥15）が維持されたか | ΔE<15 のペア数 | 0 |

## 3. design（技術 How）

### 3-1. `index.css` への定義【確定値埋め込み】

#### 既存流用トークン

| `--calendar-*` | 参照先 | 現値（ライト / ダーク） | 根拠 |
|---|---|---|---|
| `--calendar-meeting-color` | `var(--calendar-google-blue)` | `#1a73e8 / #8ab4f8` | `recon-calendar-current.md` |
| `--calendar-meeting-tint` | `var(--calendar-google-blue-light)` | `#e8f0fe / #1e3a5f` | `recon-calendar-current.md` |
| `--calendar-meeting-text` | `var(--color-blue-800)` | `#174ea6 / #93c5fd` | `design-system/design.md` |
| `--calendar-procurement-tint` | `var(--calendar-status-ok-bg)` | `#e6f4ea / #14432b` | `recon-calendar-current.md` |
| `--calendar-shipping-tint` | `var(--calendar-status-error-bg)` | `#fce8e6 / #4c1d1d` | `recon-calendar-current.md` |
| `--calendar-shipping-text` | `var(--color-red-700)` | `#b91c1c / #fca5a5` | `design-system/design.md` / `index.css` |
| `--calendar-billing-text` | `var(--color-amber-800)` | `#92400e / #fcd34d` | `design-system/design.md` / `index.css` |
| `--calendar-release-color` | `var(--color-gray-600)` | `#5f6368 / #94a3b8` | `recon-calendar-distinguishability.md` |
| `--calendar-release-tint` | `var(--color-gray-100)` | `#f3f4f6 / #1f2937` | `design-system/design.md` / `index.css` |
| `--calendar-release-text` | `var(--color-border-subtle)` | `#374151 / #374151` | `design-system/design.md` / `index.css` |

#### 独自新規トークン

| `--calendar-*` | 現値（ライト / ダーク） | 根拠 |
|---|---|---|
| `--calendar-personal-color` | `#9333ea / #c084fc` | `recon-calendar-current.md` |
| `--calendar-personal-tint` | `#f3e8ff / #2d0e4e` | `recon-calendar-current.md` |
| `--calendar-personal-text` | `#6b21a8 / #d8b4fe` | `recon-calendar-current.md` |
| `--calendar-procurement-color` | `#0f9d58 / #4ade80` | `recon-calendar-current.md` |
| `--calendar-procurement-text` | `#166534 / #86efac` | `recon-calendar-current.md` |
| `--calendar-shipping-color` | `#d93025 / #f28b82` | `recon-calendar-current.md` |
| `--calendar-billing-color` | `#f29900 / #f8d66d` | `recon-calendar-current.md` |
| `--calendar-billing-tint` | `#fef3c7 / #362a08` | `recon-calendar-current.md` |
| `--calendar-holiday-color` | `#7e22ce / #b771f4` | `recon-calendar-current.md` |
| `--calendar-holiday-tint` | `#f5f3ff / #1e1b4b` | `recon-calendar-current.md` |
| `--calendar-holiday-text` | `#6b21a8 / #e9d5ff` | `recon-calendar-current.md` |

### 3-2. `calendars.config.ts` の書き換え【確定値埋め込み】

| カレンダー | プロパティ | 現 hex | 置換先 | 種別 |
|---|---|---|---|---|
| meeting | colorVar | `#1a73e8` | `var(--calendar-meeting-color)` | 既存流用 |
| meeting | tintVar | `#e8f0fe` | `var(--calendar-meeting-tint)` | 既存流用 |
| meeting | textVar | `#174ea6` | `var(--calendar-meeting-text)` | 既存流用 |
| personal | colorVar | `#9333ea` | `var(--calendar-personal-color)` | 独自新規 |
| personal | tintVar | `#f3e8ff` | `var(--calendar-personal-tint)` | 独自新規 |
| personal | textVar | `#6b21a8` | `var(--calendar-personal-text)` | 独自新規 |
| procurement | colorVar | `#0f9d58` | `var(--calendar-procurement-color)` | 独自新規 |
| procurement | tintVar | `#e6f4ea` | `var(--calendar-procurement-tint)` | 既存流用 |
| procurement | textVar | `#166534` | `var(--calendar-procurement-text)` | 独自新規 |
| shipping | colorVar | `#d93025` | `var(--calendar-shipping-color)` | 独自新規 |
| shipping | tintVar | `#fce8e6` | `var(--calendar-shipping-tint)` | 既存流用 |
| shipping | textVar | `#b91c1c` | `var(--calendar-shipping-text)` | 既存流用 |
| billing | colorVar | `#f29900` | `var(--calendar-billing-color)` | 独自新規 |
| billing | tintVar | `#fef3c7` | `var(--calendar-billing-tint)` | 独自新規 |
| billing | textVar | `#92400e` | `var(--calendar-billing-text)` | 既存流用 |
| release | colorVar | `#5f6368` | `var(--calendar-release-color)` | 既存流用 |
| release | tintVar | `#f3f4f6` | `var(--calendar-release-tint)` | 既存流用 |
| release | textVar | `#374151` | `var(--calendar-release-text)` | 既存流用 |
| holiday | colorVar | `#7e22ce` | `var(--calendar-holiday-color)` | 独自新規 |
| holiday | tintVar | `#f5f3ff` | `var(--calendar-holiday-tint)` | 独自新規 |
| holiday | textVar | `#6b21a8` | `var(--calendar-holiday-text)` | 独自新規 |

### 3-3. `cssVar()` 除去

- `frontend/src/features/schedule/calendars.config.ts` の `cssVar()` は `return value ?? "";` の空箱関数のため、設計上は不要になる。
- `frontend/src/pages/schedule/SchedulePageImpl.tsx` などの参照側は、CSS 変数文字列を直接使う前提に揃える。

## 4. 弊害・トレードオフ

- 近似流用で寄せた分は見た目が変わる。特に `release` は `--color-gray-600` に寄せる前提で、現値との差分が出る。
- カレンダー色を CSS 変数に寄せるため、実装箇所は増えるが、色の正本は 1 箇所にまとまる。
- バックエンド・DB・ロール色・SVG 属性には影響しない。

## 5. 受入基準

- `calendars.config.ts` の直書き hex が 0 件。
- `cssVar()` が 0 件。
- `index.css` に必要な `--calendar-*` がすべて定義済み。
- `recon-calendar-distinguishability.md` の ΔE マトリクスで `ΔE<15` の新規ペアが 0 件。

## 6. 維持の仕組み

- カレンダー色の新規追加や更新は `index.css` の CSS 変数を先に更新し、`calendars.config.ts` は参照だけに保つ。
- `calendars.config.ts` に直書き hex が戻らないよう、実装時は grep で監視する。

## 7. 接触面分析（6面）

| 面 | 事実 |
|---|---|
| 人 | 予定を色で見分ける利用者に関わる |
| エージェント | 実装役は `calendars.config.ts` と `index.css` の参照を更新する |
| 機械 | 色差は ΔE と Visual Gate で確認する |
| データ | DB は変更しない |
| 本番 | migration は不要 |
| 外部 | 連携先 API や外部 GUI の変更はない |
