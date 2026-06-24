# design: ETD ガイド 見出し左寄せ＋背景統一

## 参照
- recon: `docs/handoff/etd-guide-layout/recon.md`
- ADR-129（FedEx Label Validation ウィザード）
- ADR-067（デザイントークン強制）

## 変更方針

### 変更1: 見出し/intro 左寄せ、詳細ペイン中央維持

**問題**: `.etd-guide` に `max-width: 900px; margin-inline: auto` があり、見出し・intro・ペイン全体が一括で中央寄せされている。見出しとintroを左へ出したい。

**方針**: 
- `.etd-guide` から `max-width` / `margin-inline` を削除（全幅化）
- `max-width: var(--max-width-setup-guide); margin-inline: auto` を `.etd-guide__substep-pane` に移動
- `.etd-guide__step` に `display:flex; flex-direction:column; gap:var(--space-4)` を追加（breathing room確保）
- `.etd-guide__step-header` の `margin-bottom: var(--space-3)` を削除（gap に一元化）

**結果**: 見出し・intro は全幅内の左端。ペインのみ 900px 中央寄せ。

### 変更2: 背景統一

**問題**: `.setup-guide-page` に background 指定なし = 白（`--bg-surface`相当）のまま。アプリ本体（`.app-shell`）は `var(--bg-primary)` を使用。

**方針**: `.setup-guide-page` に `background: var(--bg-primary)` を追加（`.app-shell` と同一変数を流用）。ダークモードも自動対応。

## KGI/KPI

| 基準 | 検証方法 |
|------|---------|
| 見出し（ステップ番号＋テキスト）がペインの左端より左に位置する | ブラウザ目視: 見出しが900px枠の外 (左) に出ている |
| intro テキストが見出しと同じ左揃え | ブラウザ目視: intro段落が画面左側に位置 |
| サブ手順2ペイン（左ナビ／右詳細）が中央寄せを維持 | ブラウザ目視: ペインが画面中央に収まる |
| 背景がアプリ本体と同系統（グレー系）になる | ブラウザ目視: 白でなくアプリ背景色と一致 |
| ダークモードで背景・ステッパーが連続する | `force-dark` クラス付与して目視 |
| `npm run lint` 通過 | CI / ローカル確認 |
| `npm run build` 通過 | CI 確認 |

## 外部・過去事例の参照と我々への応用

CSS レイアウトで「見出しを全幅・コンテンツを中央固定幅」に分ける手法は
Content Width + Full Bleed パターンとして一般的（CSS-Tricks "Full-Bleed Layout"）。
今回は `.etd-guide__substep-pane` に `max-width + margin-inline:auto` を付与することで
見出し全幅・ペイン中央の分離を実現する。DHL/UPS/ヤマト等の将来追加時も同パターンを踏襲できる。
