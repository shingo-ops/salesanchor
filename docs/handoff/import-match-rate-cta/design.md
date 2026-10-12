# design: import match rate CTA

## 参照

- recon: docs/handoff/import-match-rate-cta/recon.md
- ADR-027: docs/adr/ADR-027-ui-internationalization.md
- ADR-067: docs/adr/ADR-067-design-tokens.md
- ADR-144: docs/CC_UI_GOVERNANCE.md

## 変更概要

importタブの「名前の一致率」行に、matchRate < 100 のときのみCTAボタンを追加する。

## 設計方針

既存の「要対応」行CTAパターンと同一設計:
- 条件: `matchRate < 100`（`pendingCount > 0` と同様の条件ガード）
- ボタン: `className="analysis-dashboard-cta-btn"`（既存スタイル再使用）
- 遷移: `onNavigate("supplier-master")`（既存prop・既存キー）
- テキスト: `t("analysisRules.dashboard.importCheckSupplierCta")`（新規i18nキー）

## 変更前後コード

### 変更前（AnalysisDashboardPanel.tsx:518-522）
```tsx
              </Badge>
            </span>
          </div>
```

### 変更後
```tsx
              </Badge>
              {matchRate < 100 && (
                <button
                  type="button"
                  className="analysis-dashboard-cta-btn"
                  onClick={() => onNavigate("supplier-master")}
                >
                  {t("analysisRules.dashboard.importCheckSupplierCta")}
                </button>
              )}
            </span>
          </div>
```

## i18n追加キー

| キー | ja | en |
|------|----|----|
| `analysisRules.dashboard.importCheckSupplierCta` | サプライヤーを確認 → | Check suppliers → |

## 触らない範囲

- 既存CTAスタイル（CSSファイル変更なし）
- onNavigate prop定義（変更なし）
- AnalysisRulesSidebarKey型（変更なし）
- matchRate計算ロジック（変更なし）

## KGI/KPI

| 基準 | 検証方法 |
|------|---------|
| matchRate < 100 のとき「サプライヤーを確認 →」ボタンが名前の一致率行に表示される | ブラウザでimportタブを開き、unresolved_rate > 0 の状態でボタン表示を目視確認 |
| matchRate = 100 のときボタンが表示されない | unresolved_rate = 0 の状態でボタン非表示を目視確認 |
| ボタンクリックでサプライヤーマスタページへ遷移する | クリック後 sidebar が "supplier-master" に切り替わることを確認 |

## 外部・過去事例の参照と我々への応用

既存の「要対応」行CTA（`frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx` 538-545行目）が直接の参考実装。同一ファイル内の pendingCount > 0 条件ガード + onNavigate("needs-review") パターンをそのまま matchRate < 100 条件 + onNavigate("supplier-master") に置き換えた。新規コンポーネント不要・学習コスト不要。

## 維持の仕組み

守り手: `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx` — ADR-027（i18n CI チェック）がキー同一性を保証。importTabContent 部分は matchRate 計算ロジックが変わらない限りこのCTAは正しく動作する。
