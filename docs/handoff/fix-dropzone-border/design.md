# design: fix-dropzone-border

recon: docs/handoff/fix-dropzone-border/recon.md

## 概要

`AnalysisDashboardPanel.css` 内の未定義カスタムプロパティ `--color-border` を定義済みトークンに置き換える。

## ADR参照

- ADR-067: デザイントークン強制（`docs/adr/ADR-067-design-token-enforcement.md`）

## 変更計画

| 場所 | 変更前 | 変更後 | 理由 |
|------|--------|--------|------|
| `.analysis-dashboard-dropzone` (line 42) | `var(--color-border)` | `var(--border-strong)` | ドロップゾーン破線ボーダーに視認性の高いトークンを使用 |
| `.analysis-dashboard-window-input` (line 78) | `var(--color-border)` | `var(--border)` | 入力フィールドの標準ボーダートークンを使用 |

## KGI/KPI

| 基準 | 検証方法 |
|------|----------|
| インポートタブでドロップゾーンの破線ボーダーが表示される | 本番画面でインポートタブを開き、ドロップゾーンの破線枠線を目視確認 |
| ダーク/ライト両モードで視認可能 | ブラウザのダークモード切替で確認 |

## 影響範囲

- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.css`（2行変更のみ）
- TSX・バックエンド・その他ファイルへの変更なし

## 外部事例

CSS カスタムプロパティが未定義の場合 `var()` は invalid value にフォールバックし、プロパティは初期値（`border` の場合 `none`）が使われる。（MDN: Using CSS custom properties）

## 戻し方

git revert でCSS2行を元に戻す。機能への影響なし（ボーダーが再び不可視になるのみ）。

## 維持の仕組み

ADR-067 のデザイントークン強制ルールと `check-css-hardcoded-values.js` がトークン違反を lint で検出する。ただし「未定義トークン名を使う」パターンは現状の lint では検出されないため、今後のトークン追加・変更時にはトークン名の実在確認を行うこと。

守り手: frontend/scripts/check-css-hardcoded-values.js

## 外部・過去事例の参照と我々への応用

MDN「Using CSS custom properties」: CSS カスタムプロパティが未定義の場合、`var()` は invalid value として扱われ、プロパティは初期値（`border: none` 等）にフォールバックする。この挙動により、誤ったトークン名でも lint エラーにならず本番まで気づかれないリスクがある。対策として、新規トークン使用時は必ず `grep` で実在確認すること（本件の教訓）。
