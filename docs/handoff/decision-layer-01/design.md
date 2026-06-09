# 決定レイヤー① — ステータス見た目の対応表（SSoT）設計

> **作成日**: 2026-06-09  
> **ステータス**: 確定（Phase 4 実装中）  
> **参照**: recon = `recon.md` / 実装 = ADR-120

---

## KGI

- **before**: 29サイト（集約5＋インライン24）／10ドメイン／約44分岐が散在
- **after**: 決定を**中央対応表1ヶ所（SSoT）に集約**し、ページ側の status→見た目 直書き **0件**

---

## 技術 How

### 中央対応表（componentMaps）

`frontend/src/utils/statusPresentation.ts`

- `(ドメイン, ステータス値) → { bucket, badgeVariant, labelKey }` を1ファイルに定義
- 10ドメイン × 全ステータス値を網羅

### ルックアップ補助関数

```typescript
getStatusPresentation(domain: StatusDomain, status: string): StatusPresentation
```

- ページは**これを呼ぶだけ**（自前判断しない）
- 未知ステータス → **neutral フォールバック ＋ 開発時 console.warn**（安全に失敗）

---

## バケット5分類（最小語彙）

| バケット | 色 | 割り当てるステータスの性質 |
|---|---|---|
| `success` | 緑 | 完了 / 成功 / 入金済み / 有効 / 受注 |
| `danger` | 赤 | 失敗 / エラー / 期限超過 / 失注 / 拒否 |
| `warning` | 黄 | 要対応 / 保留 / 期限間近 |
| `info` | 青 | 進行中 / 交渉中 / 処理中 / 送信済み |
| `neutral` | 灰 | 新規 / 下書き / 未着手 / 不明（フォールバック） |

### 衝突3件の解決

1. **negotiating → info に統一** (lead/deal/quote で3色分裂していた)
2. **Invoice 重複 ternary → 補助関数1ヶ所に集約** (InvoicesPage + InvoiceDetailPage)
3. **DealsPage CSS 直注入 → 補助関数経由に変更** (badge-${d.status} を除去)

---

## 全ドメイン対応表

### LeadStatus
| 値 | bucket | badgeVariant |
|----|--------|-------------|
| `lead` | neutral | neutral |
| `negotiating` | **info** | negotiating |
| `existing_customer` | success | won |
| `follow_up_short` | warning | pending |
| `follow_up_long` | warning | pending |
| `lost` | danger | lost |
| `out_of_scope` | neutral | neutral |

### QuoteStatus
| 値 | bucket | badgeVariant |
|----|--------|-------------|
| `draft` | neutral | neutral |
| `sent` | info | negotiating |
| `approved` | success | won |
| `rejected` | danger | lost |
| `expired` | danger | cancelled |

### InvoiceStatus
| 値 | bucket | badgeVariant |
|----|--------|-------------|
| `draft` | neutral | neutral |
| `sent` | info | negotiating |
| `issued` | info | negotiating |
| `paid` | success | won |
| `overdue` | danger | cancelled |
| `voided` | danger | lost |

### DealStatus
| 値 | bucket | badgeVariant |
|----|--------|-------------|
| `open` | neutral | neutral |
| `negotiating` | **info** | negotiating |
| `won` | success | won |
| `lost` | danger | lost |
| `on_hold` | warning | on_hold |

### OrderStatus
| 値 | bucket | badgeVariant |
|----|--------|-------------|
| `awaiting_payment` | warning | awaiting_payment |
| `sourcing` | info | sourcing |
| `awaiting_shipping` | warning | awaiting_shipping |
| `completed` | success | completed |
| `trouble` | danger | trouble |
| `cancelled` | danger | cancelled |

### PurchaseOrderStatus
| 値 | bucket | badgeVariant |
|----|--------|-------------|
| `draft` | neutral | neutral |
| `ordered` | info | negotiating |
| `received` | success | won |
| `cancelled` | danger | lost |
| `error` | danger | lost | ← **⚠️ DB 値の存在確認中（PO 確認中）** |

### ParseStatus (Discord)
| 値 | bucket | badgeVariant |
|----|--------|-------------|
| `pending` | neutral | neutral |
| `parsing` | info | negotiating |
| `parsed` | success | won |
| `parsed_rule_only` | success | won |
| `parsed_llm` | success | won |
| `approved` | success | won |
| `rejected` | danger | lost |
| `unparsed` | danger | lost |
| `budget_exhausted` | warning | pending |
| `ignored_routing` | warning | pending |

### StaffStatus
| 値 | bucket | badgeVariant | 備考 |
|----|--------|-------------|------|
| `active` | success | won | |
| `inactive` | neutral | neutral | |
| `pending` | warning | pending | **⚠️ 現行は danger（フロント漏れ）→ Step2 修正** |

### BotStatus
| 値 | bucket | badgeVariant | 備考 |
|----|--------|-------------|------|
| `active` | success | won | |
| `inactive` | neutral | neutral | |
| `maintenance` | warning | pending | **⚠️ 現行は danger（フロント漏れ）→ Step2 修正** |

### ProspectRank
| 値 | bucket | badgeVariant |
|----|--------|-------------|
| `A` | success | won |
| `B+` | success | confirmed |
| `B` | info | negotiating |
| `B-` | warning | on_hold |
| `仮C` | neutral | pending |
| `確定C` | danger | lost |

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 10ドメイン全 status をカバー | テスト（未カバーを検出） |
| 補助関数＋未知→neutral | 単体テスト |
| DB 値の表記揺れ確認 | recon.md + PR 報告 |
| 全 status のプレビュー表示 | StatusSection → Evaluator 目視 |
| 直書き検知 lint 追加（既存 warn） | `check:status-direct-writes` |
| 実画面変更 0件 | `git diff` 確認 |

---

## 段階移行

| ステップ | 内容 | このステップか |
|---------|------|-------------|
| Step 1 | 中央マップ＋補助関数＋プレビュー＋lint(warn) 追加 | ✅ 本PR |
| Step 2 | 24インライン＋集約5 を補助関数へ置換 | 次PR |
| Step 3 | lint を warn → error へ昇格 | 次々PR |

---

## ⚠️ PO 確認中の残件

1. **purchaseOrder.error**: DB 値として実際に存在するか。Pydantic Enum への追加要否。
2. **staff.pending / bot.maintenance を warning**: 現状は danger なので Step2 で視覚変更が発生する。
