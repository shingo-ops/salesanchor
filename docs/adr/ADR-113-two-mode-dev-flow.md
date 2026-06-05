# ADR-113: 2モード開発フロー（terminal / handoff）

**Status**: Accepted  
**Date**: 2026-06-05  
**Author**: Hikky-dev  
**PO**: shingo-ops

---

## What（何を）

Claude Code エージェントの実装フローに2つのモードを定義する。

| モード | front-matter flag | 呼称 |
|-------|-------------------|------|
| **pattern 1** | `mode: terminal`（省略可） | terminal モード |
| **pattern 2** | `mode: handoff`（必須）| handoff モード |

---

## Why（なぜ）

ADR-012（What/How 分離）は "ADR は What/Why/Scope のみ、How は Generator が自律設計" というルールを定めた。  
このルールは **pattern 1**（PO → ADR → Generator 自律設計）には適合するが、  
以下の場面では PO が How まで合意した設計ドキュメントを持ち込む必要がある:

- 外部コンサル・仕様書・Web Claude との深い設計セッション後の実装委任  
- セキュリティ・コンプライアンス要件で "実装詳細を事前確定しないと監査できない" ケース  
- 複数スプリントにまたがる設計が先行確定している場合

この場面で ADR-012 を字義通りに適用すると、Generator が設計を再構築してしまい、  
事前合意した仕様から逸脱するリスクがある。  
ADR-113 は pattern 2 を追加し、"設計持ち込み忠実実装" の経路を公式化する。

---

## Scope（対象）

- Claude Code エージェント（Generator / Architect / Planner）の動作定義  
- `CLAUDE.md` の実装フロー節  
- CI ゲート（SA-19: ADR-SA-19-verification-gates.md）による hard backstop  
- **対象外**: ADR-012 の pattern 1 ルール（変更なし）

---

## モード詳細

### Pattern 1: terminal（既定）

```yaml
# 省略時も pattern 1 とみなす
mode: terminal
```

- ADR には **What / Why / Scope のみ** 記述する  
- **How（技術選択・実装詳細）は Generator が自律設計** する（ADR-012 既定）  
- Generator は最善の実装を選択してよい  
- Architect は設計の整合性を確認し、必要なら再設計を提案できる

### Pattern 2: handoff（設計持ち込み）

```yaml
mode: handoff
```

#### 必須手順（順序厳守）

```
[1] Architect 実機 recon（設計確定の前）
    ↓
[2] 設計確定（recon エビデンスを反映した最終版）
    ↓
[3] Architect 整合検査（1 回限り・差し戻しのみ）
    ↓
[4] Generator 実装
    ↓
[5] CI / スモークゲート（hard backstop）
```

**[1] Architect 実機 recon が設計確定の「前」にある**。  
現行コードの file:line 突合、テーブル所有者・DB 名・既存テストの前提など、  
現状把握なしの机上設計は無価値とみなし、recon の整合エビデンスがない設計は Generator に渡さない。

- 設計ドキュメントの **front-matter に `mode: handoff` を必ず記載** する  
- 設計ドキュメントの **How（契約・不変条件・受け入れ条件・フロント視覚）が権威**  
  - Generator はこれを忠実に実装する。再設計しない  
  - バックエンドの非不変な実装詳細（TTL・キー設計・fixture 等）は Generator 裁量  
- **Architect の役割は整合検査のみ**（既存 CLAUDE.md / ADR / CI との矛盾確認）  
  - 矛盾を見つけても勝手に書き換えない → チャットへ差し戻す（PO + Web Claude で再合意後に再提出）  
  - レビューは原則 1 回に収束させる。以降の確実性はゲート（CI / ビジュアル差分 / スモーク / ステージング）に置く。ゲートが拾える指摘で往復しない。やり取りは全文再貼りでなく差分で行う  
- **Generator の逸脱報告義務**: 現場都合で仕様から変える必要があれば、  
  PR body に `## ADR逸脱報告（箇所・理由・リスク・PO承認要）` を記載 → PO 判断

---

## フィデリティ規律

pattern 2 で Generator が **変えてはいけないもの**:

| 種別 | 例 |
|------|----|
| 契約・API 仕様 | エンドポイント名・リクエスト/レスポンス型 |
| 不変条件 | RLS ポリシー・セキュリティ要件 |
| 受け入れ条件 | テスト数・テスト対象のアサーション内容 |
| フロント視覚 | UI コンポーネント名・レイアウト |

Generator が **自由に決めてよいもの**（pattern 2 でも）:

- SQL のインデックス名、テスト用 fixture の具体値
- ライブラリのバージョン（仕様に明記なき場合）
- ログメッセージの文言
- コードのフォーマット・変数名（仕様に縛りがない場合）

---

## モード強制

| レイヤー | 強制方法 | 種別 |
|---------|---------|------|
| Agent front-matter | Generator が `mode:` を読んで動作を切り替える | **soft**（意図的 |
| SA-19 CI ゲート | `test_rls_invariants.py` + smoke で不変条件を機械検証 | **hard backstop** |

- flag なしの作業は pattern 1（ADR-012 既定）  
- pattern 2 を使う場合は設計ドキュメントの front-matter に `mode: handoff` を必ず記載する  
- 詳細: `docs/adr/ADR-012-what-how-separation.md` / `docs/adr/ADR-SA-19-verification-gates.md`

---

## 文言矛盾の解消

ADR-012 の "ADR は What/Why のみ" は **pattern 1 限定ルール** である。  
pattern 2 では設計ドキュメント（`mode: handoff`）に How を記載し、それが権威となる。  
両 ADR は排他ではなく、front-matter flag によって経路を選択する。

---

## 関連 ADR

- `ADR-012-what-how-separation.md` — pattern 1 の詳細（変更なし）  
- `ADR-SA-19-verification-gates.md` — CI ゲートの実装詳細
