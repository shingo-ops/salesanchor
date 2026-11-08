# ロール画面の表の区切りがつぶれる不具合 — 設計（design）

| 項目 | 内容 |
|------|------|
| 現在地 | `docs/handoff/role-section-no-shrink/recon.md` |
| 対象 ADR | ADR-067（色・寸法は変数だけ）・ADR-144（金型）。新規 ADR なし |
| 危険 PR か | いいえ。`migrations/`・`.github/workflows/deploy.yml`・本番 `scripts/` を含まない。画面の CSS 1行だけ |
| 承認 | PO 2026-11-08「権限の表だけがスクロールするようにすること」＋常時委譲「PRマージ、デプロイまで完走させてくれ」 |

## 0. 目的

前の直しで入れ忘れた1行を足し、権限の表だけが縦に動くようにする（recon.md §0・§1）。

## 1. 受入の基準と検証方法

| 基準 | 検証方法 |
|------|----------|
| 1. 区切りがつぶれない | 本番 `/management-center/roles` で各 `.role-perm-section` の見えている高さ＝本来の高さ（`getBoundingClientRect().height` と `scrollHeight` の差 1px 以内） |
| 2. 表だけが動く | `.role-perm-sections` の `scrollHeight > clientHeight`。いちばん下まで動かしたとき最後の行が見える範囲に入る。`.hub-content` の scrollTop は 0 のまま |
| 3. 単独の `/roles` でも同じ | 本番 `/roles` で基準2と同じ。`.app-content` の scrollTop は 0 のまま |
| 4. 保存の段が表の下で見える | `.role-perm-footer` の下端が窓の高さ以内 |
| 5. 許可の中身は変わらない | 本番 DB の役割ごとの許可の数が直す前（`perm-count-before`）と同じ |
| 6. CI が全部緑 | PR の確かめがすべて成功 |

## 2. 変更する場所と変更しない場所

- 変更する: `frontend/src/pages/roles/RolesPage.css` の `.role-perm-section`（48-52 行）だけ。
- 変更しない: ほかの CSS・TSX・文言・変数・API・DB。

## 3. 変更の中身

変更前（`frontend/src/pages/roles/RolesPage.css:48-52`）:

```css
.role-perm-section {
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}
```

変更後:

```css
.role-perm-section {
  flex-shrink: 0;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}
```

- `overflow: hidden` は角丸の中に行を収めるために残す（消すと角から行がはみ出す）。代わりに `flex-shrink: 0` で縮まないようにする。
- スマホ幅（767px 以下）は `.role-perm-sections` が `overflow-y: visible` で入れ物の高さの固定が無いので、縮む力が働かず、今の動きは変わらない。

## 4. 代わりの案と選んだ理由

- 案B: `overflow: hidden` を消す → 角丸から行の背景がはみ出す。採らない。
- 案C: `min-height: min-content` を足す → 同じ効果だが `flex-shrink: 0` のほうが意図（縮めない）がそのまま読める。採らない。

## 5. 危ないことと対処

- 無い。1行の CSS で、数・色・寸法の値を足さない。戻し方はこの1行を消すだけ。

## 6. 試験

- CI の CSS 検査・既存の試験が全部緑であること。本番で §1 の DOM の数を測る。

## 7. 維持の仕組み

- 守り手: CI の「Lint & Dark Mode Check (ADR-067)」が毎回走る。高さの連鎖の決まりは `frontend/src/tokens.css:247-254` にある。再発の見張り（スクロールする入れ物の子が縮まないかの機械の点検）は今回は作らない。理由: 同じ形の入れ物は今アプリにこの1か所だけで、本番の DOM 計測で○×が付くため。

## 8. 外部・過去事例の参照と我々への応用

- 外部の事例: CSS Flexbox の仕様（W3C CSS Flexible Box Layout Level 1「4.5 Automatic Minimum Size of Flex Items」）。`overflow` が `visible` でない flex の子は、自動の最小の大きさが 0 になる。
  - 我々への応用: `overflow: hidden` の子をスクロールする flex の入れ物に並べるときは `flex-shrink: 0` を付ける。

## 9. 自己審査（Opus・同じ AI による審査）

- 根拠: 本番の DOM 実測と、本番の画面で1行だけ足して測った結果（recon.md §0・§2）。
- 範囲: CSS 1行。処理の中身は変えない。
- 判定: APPROVE（設計合格）。未解決: なし。
