# PARITY-03 バッジ色付け — recon.md

作成日: 2026-09-03
ブランチ: release/parity03-badge-colors

---

## 既存 ADR 検索結果

ADR-067（デザイントークン強制）: `docs/adr/ADR-067-design-tokens.md`
StatusBadge は `badge-${tone}` CSS クラスを参照しているが、`warning`/`danger`/`success` トーン用クラスが未定義。

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|---|---|
| `frontend/src/features/tcg-analysis-review/components/StatusBadge.tsx:5` | `badge-${tone}` クラスを参照（warning/danger/success） |
| `frontend/src/components.css:389` | `.badge` 基底クラス定義 |
| `frontend/src/components.css:397` | 既存バリアント（badge-open 等）—デザイントークン使用パターン確認 |

---

## 触らない範囲

- `StatusBadge.tsx` — コンポーネント側は変更不要（クラス参照は正しい）
- `reviewIssues.ts` — tone 値の定義は変更不要
- `backend/` — CSS 追加のみでバックエンド影響なし
