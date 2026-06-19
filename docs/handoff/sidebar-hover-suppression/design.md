# Phase 3 設計 — sidebar-hover-suppression

**対象ADR**: ADR-022  
**recon**: docs/handoff/sidebar-hover-suppression/recon.md  
**日付**: 2026-06-20  
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

該当なし：既存の sidebar layout の hover 挙動を局所修正する小規模変更のため、外部事例は参照しない。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| サイドバー項目をクリックした直後に、hover していても 240px 展開へ戻らない | `frontend/src/components/DesktopShell.test.tsx` の unit test |
| mouse leave 後に通常 hover 展開へ復帰する | `frontend/src/components/DesktopShell.test.tsx` の unit test |
| CSS だけでなく state でも抑止できる | `frontend/src/components/DesktopShell.tsx` の `sidebarExpandSuppressed` と `sidebar-hover-suppressed` |
| ビルドと静的検証が通る | `vitest`, `eslint`, `tsc --noEmit` |

---

## 技術 How・KPI

- KPI: サイドバークリック後の再展開誤認を 0 にする
- 技術選択: クリック時に一時抑止フラグを立て、`mouseleave` で復帰する
- 理由: 既存の hover 設計を壊さず、マウス操作の自然さを維持できる

---

## 弊害・トレードオフ

- 抑止中は hover しても展開しないため、直後の再ホバーは一度無効になる
- 代わりに mouse leave で自動復帰するので、通常操作の連続性は維持できる

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | DesktopShell に抑止フラグを追加 | Generator |
| 2 | sidebar.css で hover 再展開を抑止 | Generator |
| 3 | unit test で再展開しないことを確認 | Generator |

---

## 継続

- 完了後の監視: 本番画面でクリック後の幅とラベル表示を確認
- 次フェーズへの引き継ぎ: なし

