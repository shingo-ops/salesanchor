# design — ETD ガイド 戻るボタン全削除＋1-6スクショ差し替え

**対象ADR**: ADR-129, ADR-067
**recon**: docs/handoff/etd-guide-remove-back/recon.md
**日付**: 2026-06-24
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 該当なし：ウィザード内 UI ボタン削除・画像差し替えのみ。外部事例参照は不要と判断。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 全ステップ（1〜4）で「戻る」ボタンが表示されない | ブラウザ目視 |
| 「次へ」ボタンが右寄せで表示される（1ボタンのみでもレイアウト崩れなし） | 目視 |
| ステップ1では 1-6 到達前は「次へ」非表示（既存ロジック維持） | 目視 |
| `npm run lint` 0 errors | CI |
| 1-6 スクショが新画像に差し替わっている | 目視（画像コミット後） |

---

## 技術 How・KPI

**変更1（戻るボタン削除）:**
- `FedexEtdSetupGuide.tsx:538` の `<button ... onClick={retreat}>` 行を削除
- `retreat` 関数定義（line 287-289）を削除（未使用化）
- `FedexLabelValidationTab.css:378` の `justify-content: space-between` → `flex-end` に変更

**変更2（1-6スクショ差し替え）:**
- Shingo 提供の新画像を `frontend/public/images/fedex-setup/` に配置
- 機微情報（APIキー/シークレット/アカウント番号/組織ID/氏名）は必ずマスク後にコミット
- `FedexEtdSetupGuide.tsx:408` の参照パスを新ファイル名に更新（または同名上書き）

---

## 弊害・トレードオフ

- `retreat` 関数削除: 未参照になるためリントエラー防止。他箇所での参照なし（grep確認済み）
- `space-between` → `flex-end` 変更: 戻るボタン削除後の右寄せ維持。視覚的に従来の「次へ」位置（右端）を保つ

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | 戻るボタン JSX 削除・retreat 関数削除 | Generator |
| 2 | CSS justify-content を flex-end に変更 | Generator |
| 3 | 1-6 スクショパス更新（画像提供後） | Generator |

---

## 継続

- 完了後の監視: 目視確認のみ
- 次フェーズへの引き継ぎ: なし
