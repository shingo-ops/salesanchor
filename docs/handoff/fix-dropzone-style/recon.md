# recon: fix-dropzone-style

## 現在地

### 対象ファイル

- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:743-759` — ドロップゾーン div（SVGアイコンなし・`<p>` のみ）
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.css:41-53` — `.analysis-dashboard-dropzone`（border dashed あり・flex なし）
- `frontend/src/pages/super-admin/TcgLineImportPage.tsx:308-344` — 参照元ドロップゾーン（インラインスタイル・SVGアイコンなし）

### 問題

ダッシュボードのドロップゾーンは破線枠スタイルが CSS に存在するが、
ファイルアイコンが表示されていない。また flex レイアウトがないためアイコンと
テキストが縦中央寄せされない。

### 適用ADR

- ADR-067: CSS変数トークン強制（色・サイズ直値禁止）
- ADR-144: UIコンポーネント金型（インラインSVGは登録対象外）
- ADR-027: UI文字列 t() 経由（テキスト変更なし・該当なし）
