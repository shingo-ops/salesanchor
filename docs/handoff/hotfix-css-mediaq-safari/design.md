# design: hotfix-css-mediaq-safari

## 方針

`frontend/vite.config.ts` に `build.cssTarget` を追加し、lightningcss が Level 4 range 構文に変換しないよう target を下げる。

## 変更

```typescript
// vite.config.ts
build: {
  cssTarget: ['chrome87', 'safari14', 'firefox78', 'edge88'],
}
```

- `safari14`（iOS 14 = 2020年9月リリース）を含めることで lightningcss が `max-width:` 形式を維持する
- `chrome87`、`firefox78`、`edge88` も 2020 年リリースの安定版を指定
- ソースの `responsive.css` は変更なし

## 検証基準

| 基準 | 検証方法 |
|---|---|
| ビルド後 CSS に `(width<=767px)` が含まれない | `grep "width<=" dist/assets/*.css` → 0件 |
| ビルド後 CSS に `max-width:767px` が含まれる | `grep "max-width:767px" dist/assets/*.css` → 1件以上 |
| `.sidebar-panel` mobile transform が機能する | Safari 14+ で 375px 確認 |
| ビルド成功 | `npm run build` エラーなし |

## 外部・過去事例

- Vite 8 changelog: `build.cssTarget` で lightningcss の CSS 変換対象を制御可能（公式 API）
- lightningcss: `targets` オプションで Safari < 16.4 を指定すれば Level 4 range 構文を使用しない
- esbuild: `cssTarget` はブラウザバージョン文字列（`safari14` 等）を受け付ける

## 今後の課題

- browserslist を `package.json` に追加して単一の truth source を持つことを検討（ADR 候補）
- iOS 最低サポートバージョンの明確化（現状: safari14 = iOS 14 以降）

## 参照

- recon: docs/handoff/hotfix-css-mediaq-safari/recon.md
- ADR: ADR-067-design-token-enforcement.md（ADR-067）
