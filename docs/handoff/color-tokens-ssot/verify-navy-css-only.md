# verify-navy-css-only
- 検証対象ブランチ: `release/color-navy-alias-consolidation`
- HEAD SHA: `ca7794c34ac183f266c19ca49ff9aeeaecfb1d3c`
- 調査対象: `frontend/src/**/*.css` / `frontend/src/**/*.scss`
- 検証目的: `--accent` 大元定義を除いた CSS/SCSS 内のネイビー hex 直書き残存を数え直す

## 1. 対象ブランチ確認

```text
release/color-navy-alias-consolidation
ca7794c34ac183f266c19ca49ff9aeeaecfb1d3c
```

## 2. 固定リスト grep 出力

```text
frontend/src/tokens.css:375:  --cal-personal:        #1e3a8a;  --cal-personal-tint: #e9edf7;  --cal-personal-text: #1e3a8a;
frontend/src/tokens.css:533:  --cal-meeting:   #5b8dd9; --cal-meeting-tint:  #16263f; --cal-meeting-text:  #9dc0ef;
frontend/src/index.css:26:  --accent: #1e3a8a;             /* プライマリボタン・フォーカス */
frontend/src/index.css:69:  --shadow-accent-hover: 0 2px 6px color-mix(in srgb, var(--accent) 15%, transparent); /* permission-item hover（--accent #1e3a8a） */
frontend/src/index.css:86:  --focus-ring-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 15%, transparent); /* light: --accent #1e3a8a */
frontend/src/index.css:176:  --calendar-google-blue:        #1a73e8;
frontend/src/index.css:178:  --calendar-today-bg:           #1a73e8;
frontend/src/index.css:219:  --accent: #5b8dd9;
frontend/src/index.css:250:  --shadow-accent-hover: 0 2px 6px color-mix(in srgb, var(--accent) 20%, transparent);   /* dark: --accent #5b8dd9 */
frontend/src/index.css:256:  --accent-bg-subtle:  color-mix(in srgb, var(--accent) 12%, transparent);   /* ダーク accent (#5b8dd9) 準拠 */
frontend/src/index.css:264:  /* フォーカスリング（dark: --accent #5b8dd9 ネイビー系） */
```

## 3. 広め抽出 grep 出力

```text
frontend/src/tokens.css:375:  --cal-personal:        #1e3a8a;  --cal-personal-tint: #e9edf7;  --cal-personal-text: #1e3a8a;
frontend/src/index.css:26:  --accent: #1e3a8a;             /* プライマリボタン・フォーカス */
frontend/src/index.css:69:  --shadow-accent-hover: 0 2px 6px color-mix(in srgb, var(--accent) 15%, transparent); /* permission-item hover（--accent #1e3a8a） */
frontend/src/index.css:86:  --focus-ring-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 15%, transparent); /* light: --accent #1e3a8a */
```

## 4. 分類表

### 4-1. `--accent` 大元
| file:line | hex値 | 変数名 / セレクタ / プロパティ | 分類 |
|---|---|---|---|
| `frontend/src/index.css:26` | `#1e3a8a` | `--accent` | `--accent大元` |
| `frontend/src/index.css:219` | `#5b8dd9` | `--accent` | `--accent大元` |

### 4-2. 集約漏れ
| file:line | hex値 | 変数名 / セレクタ / プロパティ | 分類 |
|---|---|---|---|
| `frontend/src/tokens.css:375` | `#1e3a8a` | `--cal-personal` / `--cal-personal-text` | `集約漏れ` |
| `frontend/src/tokens.css:533` | `#5b8dd9` | `--cal-meeting` | `集約漏れ` |

### 4-3. 別系統
| file:line | hex値 | 変数名 / セレクタ / プロパティ | 分類 |
|---|---|---|---|
| `frontend/src/index.css:176` | `#1a73e8` | `--calendar-google-blue` | `別系統` |
| `frontend/src/index.css:178` | `#1a73e8` | `--calendar-today-bg` | `別系統` |

### 4-4. コメント参照（直書き実体ではない grep ヒット）
| file:line | hex値 | 変数名 / セレクタ / プロパティ | 備考 |
|---|---|---|---|
| `frontend/src/index.css:69` | `#1e3a8a` | コメント | コメント中の言及 |
| `frontend/src/index.css:86` | `#1e3a8a` | コメント | コメント中の言及 |

## 5. 数値サマリ

- grep ヒット総数: `8` 行
- hex occurrences 総数: `9`
- `--accent大元` 件数: `2`
- `集約漏れ` 件数: `2` 行 / `3` occurrences
- `別系統` 件数: `2`
- コメント参照件数: `2`
- `--accent` 大元定義を除いた CSS/SCSS 内のネイビー hex 直書き実体: `3` occurrences

## 6. 結論

- `--accent` 大元定義を除いた CSS/SCSS 内のネイビー hex 直書き実体は `0` 件ではない
- したがって、CSS/SCSS 限定でも「ネイビーは `--accent` に完全統一済み（大元定義を除き直書き 0 件）」とは言えない

## 7. 検証メモ

- 本ファイルは便2ブランチ HEAD に対する新規 grep 実行結果のみで作成した
- 過去便の表は再利用していない
