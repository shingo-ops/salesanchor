# recon — sidebar-hover-suppression

**仕事名**: sidebar-hover-suppression  
**日付**: 2026-06-20  
**対象ADR**: ADR-022  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/components/DesktopShell.tsx:119` | `sidebarExpanded` と `sidebarExpandSuppressed` が併存しており、クリック後の hover 再展開抑止を state で表現できる |
| `frontend/src/components/DesktopShell.tsx:146` | `handleSidebarLeave` で折りたたみ状態と抑止フラグを両方解除している |
| `frontend/src/components/DesktopShell.tsx:158` | ナビクリック時に `sidebarExpandSuppressed` を `true` にしている |
| `frontend/src/components/DesktopShell.tsx:202` | `sidebar-hover-suppressed` クラスをサイドバーに付与して CSS 側の制御に渡している |
| `frontend/src/sidebar.css:34` | `:hover` による幅拡張が存在する |
| `frontend/src/sidebar.css:42` | 抑止中は `:hover` でも折りたたみ幅を維持する上書きがある |
| `frontend/src/sidebar.css:76` | 抑止中のロゴ領域は中央寄せへ戻す |
| `frontend/src/sidebar.css:187` | 抑止中のラベルは非表示に戻す |
| `frontend/src/sidebar.css:199` | 抑止中の padding を collapsed 相当に戻す |
| `frontend/src/components/DesktopShell.test.tsx:118` | クリック後に hover 再展開しないことを unit test で確認している |

*（引用先は実在するファイルと行番号を記載すること。process-artifacts gate が自動照合する）*

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | クリック後の hover 再展開が state だけで止まるか | CSS 側の `:hover` 上書きを確認 | ✅ 解消済み |
| 2 | mouse leave 後に通常 hover に復帰するか | `handleSidebarLeave` と unit test で確認 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- 実装対象は既存の DesktopShell / sidebar.css の最小変更。
- クリック後だけ hover を抑止し、マウスが離れたら通常挙動へ戻す。

