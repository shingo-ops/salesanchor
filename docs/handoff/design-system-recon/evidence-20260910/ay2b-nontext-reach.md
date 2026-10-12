# 非 text input の競合クラスが .form-group の内側に到達しうるか（部品経由、再帰）

手法: frontend/src の非テスト TS/TSX 344 ファイルを AST で解析。(1) JSX の .form-group 要素の部分木に現れる部品タグを起点に、(2) その部品ファイルが描画する部品タグを再帰的にたどり（相対 import と barrel の re-export を解決）、(3) 到達した部品ファイル 20 件のうち、競合規則の祖先クラス（search-bar, toggle-switch, source-search, pmd-field, inbox-toggle, topbar-search, color-swatch, chk-label, permission-item, sales-form-option, form-grid, form-row, modal-content, modal-content-wide）を className に持つもの・checkbox/radio/range/file の input を持つものを抽出。

## 結果

- .form-group の内側に到達しうる部品ファイル: 20
- そのうち競合クラスを className に持つ: 0
- そのうち非 text の input を持つ: 0
- 両方を持つ（競合クラスと非 text input が同じ部品ファイルにある）: 0

### 競合クラスを持つ到達ファイル

なし

### 非 text input を持つ到達ファイル

なし

