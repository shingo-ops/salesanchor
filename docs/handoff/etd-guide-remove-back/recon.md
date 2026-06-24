# recon — ETD ガイド 戻るボタン全削除＋1-6スクショ差し替え

**仕事名**: ETD ガイド 戻るボタン全削除＋1-6スクショ差し替え
**日付**: 2026-06-24
**対象ADR**: ADR-129, ADR-067
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:287` | `retreat` 関数定義（削除対象） |
| `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:537` | `etd-guide__nav` フッター（戻るボタンを含む form-actions） |
| `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:408` | 1-6 スクショ参照 `step1-07-overview.png` |
| `frontend/src/pages/integrations/FedexLabelValidationTab.css:377` | `.etd-guide__nav { justify-content: space-between; }` — 戻る削除後に flex-end へ変更必要 |

---

## 現状（file:line）

- `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:537` に `<div className="form-actions etd-guide__nav">` があり、内部に「戻る」ボタン（line 538）と「次へ」ボタン（line 541）が `space-between` で配置されている。
- `frontend/src/pages/integrations/FedexLabelValidationTab.css:377` の `.etd-guide__nav` が `justify-content: space-between` を指定。戻る削除後は右寄せに変更が必要。
- `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:287` に `retreat` 関数が定義されているが、戻るボタン削除後は未使用になる。
- 1-6 スクショは `step1-07-overview.png`（line 408）。新画像は Shingo が別途提供予定。

## 触らない範囲

- 「次へ」ボタンのロジック（canAdvance・ステップ1末尾のみ表示）
- SubstepPane 内部状態
- 進捗バー・他ステップのコンテンツ
- 他コンポーネント

## 不明点リスト

| # | 不明点 | 状態 |
|---|-------|------|
| 1 | 1-6 新スクショファイル名 | 未提供（Shingo が別途添付） |

**未解決**: 1件（画像ファイル待ち）
