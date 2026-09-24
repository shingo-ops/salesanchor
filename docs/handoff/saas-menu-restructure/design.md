# design: SAAS管理者メニュー改善

## 参照

- recon: `docs/handoff/saas-menu-restructure/recon.md`
- ADR-027: i18n 強制
- ADR-137: Adaptive Shell Architecture
- ADR-144: UIガバナンス

## 変更内容

### 1. メニュー名変更（i18n キー更新）

| キー | 変更前 | 変更後 |
|------|-------|-------|
| `nav.superAdminAnalysisRules` (ja) | 解析管理 | LINE解析 |
| `analysisRules.page.title` (ja) | 解析管理 | LINE解析 |
| `nav.superAdminAnalysisRules` (en) | Analysis Management | LINE Analysis |
| `analysisRules.page.title` (en) | Analysis Management | LINE Analysis |

### 2. メニュー順序変更

| 変更前 | 変更後 |
|-------|-------|
| LINE解析 | LINE解析 |
| 為替レート管理 | 買取相場 |
| 買取相場 | 為替レート管理 |

### 3. アコーディオン排除（DesktopShell）

- `SidebarAccordion` → `NavLink` の `.map()` に変換
- 既存の `sidebar-item` CSS クラスを使用（デザイントークン遵守）
- `openAccordion` state は "more" アコーディオン用に残置

## 検証基準

| 基準 | 検証方法 |
|------|---------|
| SAAS管理者メニューに「LINE解析」が表示される | SAAS管理者アカウントでログインして確認 |
| 買取相場がLINE解析の直下に表示される | メニュー順序を目視確認 |
| メニューが常時表示（アコーディオン不要） | サイドバーにカーソルを当てて確認 |
| 一般ユーザーにSAAS管理者メニューが非表示 | 一般アカウントでログインして確認 |

## 外部事例

- 既存の NavLink + sidebar-item パターン（DesktopShell.tsx:222-231 等）と同一構造を採用

## 影響範囲

- DesktopShell.tsx: saasAdminItems の map（新規）・SidebarAccordion 削除（saasAdmin のみ）
- MobileShell.tsx: isSuperAdmin ブロックの resolveItem 順序変更のみ
- ja.json / en.json: 文字列変更のみ（キー名変更なし）

## 戻し方

```bash
git revert ece5cfef2
```
