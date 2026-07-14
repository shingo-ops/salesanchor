# verify-navy-final
- 検証対象ブランチ: `release/color-navy-alias-consolidation`
- HEAD SHA: `ca7794c34ac183f266c19ca49ff9aeeaecfb1d3c`
- 調査起点: `git rev-parse --abbrev-ref HEAD` / `git rev-parse HEAD` 実行済み
- 調査範囲: 便2ブランチ HEAD 時点の `frontend/src`（マージ前）

## 1. `index.css` のネイビー直書き定義

### 1-1. `#1e3a8a` / `#5b8dd9` / `#1a73e8` / `#1e3a5f` を direct に持つ変数
| file:line | 変数名 | 値 | 区分 |
|---|---|---|---|
| `frontend/src/index.css:26` | `--accent` | `#1e3a8a` | `--accent` 大元（light） |
| `frontend/src/index.css:176` | `--calendar-google-blue` | `#1a73e8` | カレンダー由来（別用途） |
| `frontend/src/index.css:178` | `--calendar-today-bg` | `#1a73e8` | カレンダー由来（別用途） |
| `frontend/src/index.css:219` | `--accent` | `#5b8dd9` | `--accent` 大元（dark） |
| `frontend/src/index.css:280` | `--info-bg` | `#1e3a5f` | 近似値・別用途 |
| `frontend/src/index.css:338` | `--color-blue-100` | `#1e3a5f` | 近似値・別用途 |
| `frontend/src/index.css:366` | `--calendar-google-blue-light` | `#1e3a5f` | 近似値・別用途 |
| `frontend/src/index.css:369` | `--calendar-today-cell-bg` | `#1e3a5f` | 近似値・別用途 |

### 1-2. `index.css` 内の結論用集計
- ネイビーhexを direct に持つ `index.css` の変数数: `7` 個
- うち `--accent` 大元: `1` 個
- うち `--accent` 以外: `6` 個
- `#1d3a89` 系の近似値は `index.css` では未検出
- `#1e3a5f` は `index.css` に残存

### 1-3. `index.css` 内の `var(--accent)` 参照数
- `var(--accent)` 参照総数: `204`

## 2. `frontend/src` 全体のネイビー直書き残存

### 2-1. カレンダー / ロール由来
| file:line | 該当コード | 旗 |
|---|---|---|
| `frontend/src/tokens.css:375` | `--cal-personal:        #1e3a8a;  --cal-personal-tint: #e9edf7;  --cal-personal-text: #1e3a8a;` | カレンダー/ロール由来 |
| `frontend/src/tokens.css:533` | `--cal-meeting:   #5b8dd9; --cal-meeting-tint:  #16263f; --cal-meeting-text:  #9dc0ef;` | カレンダー/ロール由来 |
| `frontend/src/features/schedule/calendars.config.ts:23` | `colorVar: "#1a73e8",` | カレンダー/ロール由来 |
| `frontend/src/pages/schedule/schedule-owner.ts:34` | `export const DEFAULT_OWNER_COLOR = "#1a73e8";` | カレンダー/ロール由来 |

### 2-2. 説明不能な残存
| file:line | 該当コード | 旗 |
|---|---|---|
| `frontend/src/pages/dashboard/DashboardPage.tsx:175` | `const accent = style.getPropertyValue("--accent").trim() || "#1e3a8a";` | 説明不能 |

### 2-3. SVG 属性
- 今回の grep 範囲では `SVG 属性` の該当行は 0 件

## 3. 最終判定
- `--accent` 参照への集約自体は `index.css` 上で完了している
- ただし `index.css` には `--accent` 以外のネイビー系 direct 定義が `6` 個残っている
- `frontend/src` 全体では、カレンダー / ロール由来の direct 残存が `4` 件、説明不能な残存が `1` 件ある
- よって、字義どおりの「ネイビーが `--accent` 1本に集約」は未達

## 4. 検証メモ
- このファイルは便2ブランチ HEAD に対する新規 grep 結果だけで作成した
- 前便の表は再利用していない
