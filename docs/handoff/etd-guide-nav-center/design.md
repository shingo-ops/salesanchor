# design — ETD ガイド 左ナビ項目ラベル中央揃え

**対象ADR**: ADR-129, ADR-067
**recon**: docs/handoff/etd-guide-nav-center/recon.md
**日付**: 2026-06-24
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 該当なし：今回は CSS 1 プロパティ変更のみ（`text-align: left` → `text-align: center`）のため、外部事例の参照は不要と判断。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 1-1〜1-6 ラベルが枠内中央に表示される | ブラウザ目視 |
| 左ナビ列の位置は変わらない | 目視 |
| アクティブ時の囲みは維持 | 目視 |
| `npm run lint` 0 errors | CI |

---

## 技術 How・KPI

- KPI: `.etd-guide__substep-nav-item` の `text-align` が `center` になっていること
- 技術選択: CSS 1 行変更のみ（既存デザイントークン変更なし、ADR-067 準拠）

---

## 弊害・トレードオフ

- なし：他コンポーネントへの影響ゼロ（セレクタはこのウィザード専用）

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `text-align: left` → `text-align: center` に変更（1行） | Generator |

---

## 継続

- 完了後の監視: 目視確認のみ
- 次フェーズへの引き継ぎ: なし
