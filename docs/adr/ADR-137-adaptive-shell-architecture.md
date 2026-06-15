# ADR-137: Adaptive Shell Architecture（PC / Mobile UI 分離方針）

## Status

Accepted — 2026-06-15

## Context

SalesAnchor の UI は当初 PC 専用として設計された。Left sidebar（collapsed / expanded）、hover-expand、desktop-first のレイアウトが前提となっており、mobile デバイスへの対応は CSS の `@media` による上書きで行われてきた。

PR-R1（#2156）でモバイル hamburger button と off-canvas sidebar を追加したが、これは既存の PC 用 `sidebar-panel` を CSS で制御する一時対応であった。その後 Vite 8 の lightningcss が `@media (max-width: 767px)` を CSS Level 4 range 構文（`width<=767px`）に変換し、iOS < 16.4 の Safari で全 media query が無視される本番バグが発生した（hotfix #2198 で修正）。

このような一時対応の積み重ねは構造問題を隠蔽し、保守コストを高め、新たなバグを生みやすい。根本的な解決のために PC / Mobile の Shell を明確に分離するアーキテクチャを採択する。

## Decision

SalesAnchor は **Adaptive Shell Architecture** を採用する。

### 構造

```
Design Tokens
  ↓
Shared UI Components
  ↓
Shared Navigation Definition
  ↓
DesktopShell / MobileShell
  ↓
Page Content
```

### DesktopShell

PC 向けの画面構造。

- 左サイドバーを常時表示（collapsed / hover-expanded）
- 広い画面での一覧・管理作業を優先
- 既存の desktop UX を維持

### MobileShell

スマートフォン向けの画面構造。

- 左サイドバー rail は表示しない
- 上部に MobileTopBar を表示
- hamburger button で MobileDrawer を開く
- backdrop / nav click / Escape で閉じる
- 片手操作と画面幅確保を優先

### 共通化するもの

PC / Mobile 共通で使用する。

- メニュー項目（共通 nav item builder）
- 権限判定
- i18n 文言
- 未読バッジ
- ページ本体
- API
- デザイントークン（`frontend/src/tokens.css`）
- UI コンポーネント（`frontend/src/components/`）

### 分離するもの

PC / Mobile で実装を分離する。

- Shell 構造（DesktopShell / MobileShell）
- ナビゲーションの表示方法
- ヘッダー配置
- サイドバー / ドロワーの挙動
- タッチ操作に最適化した導線

## Single Source of Truth

| 種別 | 場所 |
|------|------|
| デザイン値 | `frontend/src/tokens.css` / `frontend/src/index.css` |
| ブレークポイント | `frontend/src/tokens.css` + `frontend/src/constants/breakpoints.ts` |
| UI コンポーネント | `frontend/src/components/` |
| ナビゲーション定義 | 共通 nav item builder（1 箇所） |
| レイアウト方針 | DesktopShell / MobileShell |

## Consequences

### 禁止事項

- PC 用サイドバーを mobile で無理に使い回さない
- mobile で左 rail を残さない
- 色・余白・サイズを画面ごとに直書きしない（Design Tokens 必須）
- メニュー定義を PC 用と Mobile 用で二重管理しない
- `@media (width <= 767px)` のような Safari 非対応 CSS 出力を生成しない（`build.cssTarget` で制御）
- 一時対応 CSS を重ね続けて構造問題を隠さない

### 移行方針

1. **PR-R1（#2156）の一時対応を維持しつつ**、MobileShell を新規コンポーネントとして実装する
2. MobileShell が完成したら PR-R1 の CSS ハックを削除し、DesktopShell と切り替える
3. 既存の `sidebar-panel` を含む Layout.tsx は DesktopShell として残す
4. ブレークポイント（768px）を超えた時点で Shell を切り替える

### ブレークポイント

| 名称 | 値 | 対象 |
|------|----|----|
| `--breakpoint-mobile` | 767px | MobileShell 適用上限 |
| `--breakpoint-desktop` | 768px | DesktopShell 適用下限 |

`frontend/src/constants/breakpoints.ts` と `frontend/src/tokens.css` を SSoT とし、CSS と TypeScript で同期させる。

## Alternatives Considered

**Option A: CSS @media による一時対応継続**
- 採択しない。一時対応の積み重ねで構造問題が深刻化する。Safari Level 4 構文バグのような副作用リスクも高い。

**Option B: CSS Container Queries による分岐**
- 将来的に検討する。現時点では Safari サポート状況と学習コストを考慮し Adaptive Shell を優先する。

## Related

- ADR-067: デザイントークン強制（CSS 変数 / Design Tokens）
- ADR-027: i18n 強制（全 UI 文字列を `t()` 経由）
- PR-R1: #2156（一時対応 — hotfix #2198 で Safari 互換性修正済み）
