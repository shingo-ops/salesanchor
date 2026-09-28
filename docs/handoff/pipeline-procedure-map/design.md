# Design: PipelineMapPanel 業務手順書フローチャート

## 参照

- recon.md: `docs/handoff/pipeline-procedure-map/recon.md`
- ADR-027: `docs/adr/ADR-027-ui-internationalization.md` — 全 UI 文字列 t("key") 経由
- ADR-067: デザイントークン強制ルール — CSS 変数のみ、ハードコード色禁止
- ADR-144: `docs/CC_UI_GOVERNANCE.md` — 金型部品使用ルール

## 変更の目的

RPGスキルツリー形式（DBテーブルノード＋ドロワー表示）から、LINE解析パイプラインの**業務手順書フローチャート**に全面刷新する。
目標: 非技術者（営業・運営スタッフ）が「何をどの順序でやればよいか」を一目で把握できる画面を提供する。

## 設計方針

### ノード構成

| ノード種別 | 個数 | 説明 |
|-----------|-----|------|
| MasterNode | 4 | 前提マスタ整備カード（左カラム、縦配列） |
| ProcedureNode | 6 | 業務手順カード（STEP 1〜6、横一列） |
| EndNode | 1 | 完了マーカー |

### フロー構造

```
[マスタ整備（前提）]
 商品マスタ
    ↓
 仕入先マスタ
    ↓
 ルール設定
    ↓
 プロンプト設定 ──→ STEP1 → STEP2 → STEP3 → STEP4 → STEP5 → STEP6 → [完了]
                                                  ↑
                                    ← フィードバックループ（点線・警告色）
```

### バッジ色（ADR-067: CSS変数使用）

| badgeType | ヘッダー色変数 | 意味 |
|-----------|--------------|------|
| manual | `var(--cat-supplier)` | 人間が操作 |
| auto | `var(--cat-product)` | システム自動 |
| mixed | `var(--cat-master)` | 混在 |

### 削除した機能

- DB テーブルカラムドロワー（`api` 呼び出し含む）
- SkillNode / SkillNodeData 一式
- `handleNodeClick` ハンドラ

## KGI / KPI

| KGI | 検証方法 |
|-----|---------|
| 非技術者が「次に何をすべきか」をフローチャートから読み取れる | PO が画面を見て STEP 1〜6 の順序と手動/自動の区別を即答できること |

## 受入条件

| 基準 | 検証方法 |
|------|---------|
| `npm run build` がエラーゼロで完了する | CI ログで ✓ built を確認 |
| `npm run lint` がエラーゼロで完了する | CI ログで 0 errors を確認 |
| PipelineMapPanel を含むページが表示時にクラッシュしない | ブラウザで `/super-admin` を開き ReactFlow が描画されることを目視確認 |
| STEP 1〜6 のカードが横一列で表示される | ブラウザでズームアウトして 6 カード確認 |
| マスタカラム 4 カードが左側縦配列で表示される | 同上 |
| フィードバックエッジ（STEP4→マスタ）が点線で描画される | 同上 |
| 全テキストが日本語（ja） / 英語（en）で切り替わる | i18n ストーリーで `en` 切替後に英語テキスト表示確認 |
| `--size-proc-card-w` / `--size-proc-master-w` が tokens.css に存在する | grep で確認 |
| 旧 `--size-skill-orb-lg` / `--size-skill-orb-sm` / `--size-skill-label-w` が tokens.css から削除されている | grep で 0 件確認 |

## 外部・過去事例の参照と我々への応用

**Miro / Lucidchart 型のステップカード UI**: 横一列に手順カードを並べ、上部に「前提条件」カラムを置く設計は、SOP（Standard Operating Procedure）可視化ツールで広く採用されているパターン。
各カードに「目的（Why）」「手順（What）」「確認項目（Check）」を含める3段構成は、ISO 9001 準拠の作業手順書フォーマットに由来する。

**応用**: ProcedureNode の `why` フィールドで「なぜこのステップが必要か」を明示し、`checkpoint` フィールドで「完了判定基準」を提示する。これにより、オペレーターが「どこまで進んだか」を自律的に判断できる。

**フィードバックループ点線**: 「STEP4 → マスタ修正 → 再解析」というサイクルを可視化することで、解析精度改善のサイクルが存在することを明示する（Deming PDCA サイクルの簡略表現）。

## 維持の仕組み

守り手:
- `frontend/src/pages/super-admin/components/PipelineMapPanel.tsx` — ノード定義・エッジ定義
- `frontend/src/pages/super-admin/components/PipelineMapPanel.css` — スタイル定義
- `frontend/src/tokens.css` — `--size-proc-card-w` / `--size-proc-master-w` / `--size-pipeline-map-min-h`
- `frontend/src/locales/ja.json` — `analysisRules.pipelineMap.proc.*`
- `frontend/src/locales/en.json` — 同上（英語）

新規ステップを追加する場合: `stepNodes` 配列にエントリを追加し、対応する i18n キーを ja.json / en.json の両方に追加する。
