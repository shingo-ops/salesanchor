# recon — FedEx設定ページ配色統一（PR-A3）

**仕事名**: fedex-pr-a3  
**日付**: 2026-06-13  
**対象ADR**: ADR-067  
**担当**: Hikky-dev

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/index.css:26` | `--accent: #1e3a8a` — 受信箱の主ボタン色（SSoT）|
| `frontend/src/components.css:54` | `.btn-primary { background: var(--accent); color: var(--on-accent); }` |
| `frontend/src/components.css:68` | `.btn-secondary { background: var(--bg-surface); color: var(--text-secondary); }` |
| `frontend/src/components/Tabs.css:106` | `.comp-tabs--pill .comp-tabs__tab--active { background: var(--link-active-bg); }` |
| `frontend/src/components/Tabs.css:101` | `.comp-tabs--underline .comp-tabs__tab--active { border-bottom-color: var(--accent); }` |
| `frontend/src/components/FedExRateModal.tsx:68` | SourceBadge（fedex_live）: 旧 `--color-blue-100` → `--info-bg` に置換済み |
| `frontend/src/components/FedExRateModal.tsx:87` | SourceBadge（static）: 旧 `--color-gray-100` → `--bg-subtle` に置換済み |
| `frontend/src/components/FedExRateModal.tsx:279` | 未連携リンク: 旧 `--color-blue-700` → `--link` に置換済み |
| `frontend/src/pages/integrations/CarrierIntegrationPage.tsx:238` | `carrier-env-card--editing` クラス使用（CSS新規定義で `--accent` 枠色）|
| `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:40` | `lv-step-num` クラス（CSS新規定義で `--accent` / `--on-accent`）|
| `frontend/src/index.css:101` | `--info-bg: #bee3f8` / `--info-text: #2b6cb0`（light）、dark も対応済み |
| `frontend/src/tokens.css:219` | `--size-carrier-label-col: 120px`（キャリア設定カードラベル列幅 SSoT）|

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | `--color-*` 変数が index.css に存在するか | `frontend/src/index.css:146-154` で確認 | ✅ 解消済み |
| 2 | `--size-carrier-label-col` が既存か | `frontend/src/tokens.css:219` で確認 | ✅ 解消済み |
| 3 | `success-message` CSS 定義の有無 | `grep -rn "success-message" src/**/*.css` → 未定義を確認 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- `frontend/src/` は process-artifacts gate で DANGEROUS 扱いのため本 handoff を作成
- `--color-border` / `--color-text-secondary` は index.css に未定義（色が落下していた実バグ）
- 新規 CSS ファイル 2 件（CarrierIntegrationPage.css / FedexLabelValidationTab.css）は全トークン参照
