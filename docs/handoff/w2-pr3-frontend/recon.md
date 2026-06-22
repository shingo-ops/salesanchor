# recon: W-2① PR-3 フロント（優先見込み客を「今やること」に表示）

**仕事名**: W-2① PR-3 フロント / 攻め・守り分離の「今やること」

## 参照した実コード

| file:line | 確認内容 |
|---|---|
| `frontend/src/pages/dashboard/DashboardPage.tsx:36-40,488-491` | FunnelSection 直下に `PriorityProspectsSection` と既存 `WeeklyAdvisorSection` を並べ、ダッシュボードの「今やること」領域を 2 セクション化した |
| `frontend/src/pages/dashboard/PriorityProspectsSection.tsx:115-318,320-489` | `/analytics/priority-prospects` を取得し、lead 詳細を引いて会社/リード名を表示、`ease_pct` / `monthly_forecast` / `rank_score` / `axis_breakdown` / `low_sample_flags` を描画し、`PATCH /leads/{id}` でフォロー追加する |
| `frontend/src/api/funnel.ts:131-219` | `PriorityProspect*` 型と `getPriorityProspects("mine")` を追加し、mock/live 両方で同じ契約を返すようにした |
| `frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx:114-436` | W-1c の既存 composer パターン（`suggested_action` 初期値、`PATCH /leads/{id}` 保存、overwrite 警告、saved 表示）をそのまま維持している |
| `frontend/tests-e2e/scene1-dashboard.spec.ts:20-320` | ダッシュボード mock に priority endpoint / lead detail / dark mode を足し、2 セクション表示と priority 側のフォロー追加を検証するよう更新した |
| `frontend/src/locales/ja.json:463-490` / `frontend/src/locales/en.json:463-490` | priority の見出し・ラベル・軸ラベルを i18n に追加した |
| `frontend/src/pages/dashboard/DashboardPage.stories.tsx:1-73` | Storybook で priority / defensive の 2 セクション静的プレビューを追加し、Chromatic の baseline 取得対象を用意した |

## 確認メモ

- `process-artifacts` の判定上、`frontend/src/` は `real-code` であり、`scripts/check-process-artifacts.js` の GO 記録必須条件ではない。
- ただし PR 本文には `### 標準ワークフロー確認` が必要で、recon / design の file:line 参照も必要。
- backend の priority endpoint 契約は PR #2455 の差分で確認し、frontend 側はその契約に合わせて `lead_id / type='priority_prospect' / ease_pct / monthly_forecast / rank_score / suggested_action / axis_breakdown / low_sample_flags` を表示する。

