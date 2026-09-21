# design: import match rate CTA

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

## 外部事例

既存の「要対応」行CTA（AnalysisDashboardPanel.tsx:538-545）が直接の参考実装。
