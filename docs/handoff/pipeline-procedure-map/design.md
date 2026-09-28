---
mode: handoff
---

# Design: PipelineMapPanel 業務手順書フローチャート

この文書は何か: LINE解析の流れと、利用者向け説明画面の根拠を残す記録。
親: [提供元フィード翻訳](../../specs/inventory-management/feed-translation/README.md)
現行追加作業は2026-09-28追補。冒頭の既存マップ刷新は履歴であり、本便の実装指示ではない。

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

2026-09-28の業務ガイド追加では外部事例を採用しない。既存処理・登録部品・実測試験を根拠とするため。
以下は旧マップ設計の履歴であり、出典・実測値未提示の記述を本追補の成功根拠に用いない。

**Miro / Lucidchart 型のステップカード UI**: 横一列に手順カードを並べ、上部に「前提条件」カラムを置く設計は、SOP（Standard Operating Procedure）可視化ツールで広く採用されているパターン。
各カードに「目的（Why）」「手順（What）」「確認項目（Check）」を含める3段構成は、ISO 9001 準拠の作業手順書フォーマットに由来する。

**応用**: ProcedureNode の `why` フィールドで「なぜこのステップが必要か」を明示し、`checkpoint` フィールドで「完了判定基準」を提示する。これにより、オペレーターが「どこまで進んだか」を自律的に判断できる。

**フィードバックループ点線**: 「STEP4 → マスタ修正 → 再解析」というサイクルを可視化することで、解析精度改善のサイクルが存在することを明示する（Deming PDCA サイクルの簡略表現）。

## 維持の仕組み

守り手:
- `frontend/src/pages/super-admin/components/LineWorkflowGuidePanel.test.tsx` — 新ガイドの構造・遷移
- `frontend/tests-e2e/analysis-rules-line-guide.spec.ts` — 新ガイドのメニュー導線・言語・狭幅・キーボード・書込0

以下は既存マップの保守対象:
- `frontend/src/pages/super-admin/components/PipelineMapPanel.tsx` — ノード定義・エッジ定義
- `frontend/src/pages/super-admin/components/PipelineMapPanel.css` — スタイル定義
- `frontend/src/tokens.css` — `--size-proc-card-w` / `--size-proc-master-w` / `--size-pipeline-map-min-h`
- `frontend/src/locales/ja.json` — `analysisRules.pipelineMap.proc.*`
- `frontend/src/locales/en.json` — 同上（英語）

新規ステップを追加する場合: `stepNodes` 配列にエントリを追加し、対応する i18n キーを ja.json / en.json の両方に追加する。


## 2026-09-28追補: LINE解析の業務手順ページ

この文書は何か: 誰が何を確認して操作するかを、順番に読める説明画面の設計。
親: [提供元フィード翻訳](../../specs/inventory-management/feed-translation/README.md)
証跡: [現状調査](./recon.md)。本追補の調査基準は ae783c7f583e2d5628c19d999ed7ce6c7944e9b8。
本追補は独立した説明ページを追加する。上記の既存マップ刷新の履歴を再実装する指示ではない。

### 目的・対象・承認の区別

POの依頼原文: 「システムメニューに新しいページを作成して人間が使用する業務フローや手順書、仕様書のようにしたい」
POの依頼原文: 「この手順ではこの資料を確認してこのデータを入力する、意図意味も理解できるような手順書のような設計図ツリーにしたい」
対象は既存解析管理画面を使える管理者。表示専用のガイドと既存画面への導線を追加する。
POは本セッションでAstra設計・Sol調査実装・PRマージとデプロイまでの遂行を指示した。
設計判定はAstraによる自己審査であり、独立した第二者レビューでもPOによる画面確認でもない。
DB、API、抽出・解析・配信の判定、権限、既存マップ、本番設定、共通UI部品・tokenの変更は対象外。

### 成功条件

1. 解析管理のシステム欄に「LINE解析の業務手順」が1件あり、既存マップとは別に開く。
2. 7段階すべてに目的・担当・確認資料・入力/操作・結果・次の条件・困った時の7項目がある。
3. 説明内の業務操作ボタンは既存画面へ移動するだけ。表示中の業務書込HTTPは0件。
4. 日本語/英語の両方、390px/1440pxの幅、ライト/ダークで読める。横長の図のズーム操作を要求しない。
5. 同画面内リンクは表示とsection queryが一致。取込/配信は実在する画面へ移動する。
6. 未実装の修正操作、自動解析/自動配信の実環境での有効状態、任意配信先選択を事実として書かない。
7. 登録済み金型のみを使い、DB値・ルール値・実行状態の複製0、新規API/DB変更0。
POによる読みやすさの最終確認は未実施。自動テスト合格を「すべての初心者が理解できた」と読み替えない。

### 画面と配線

既存PageLayout/hubを維持。AnalysisRulesSidebarKeyに line-workflow-guide を追加し、システム欄のpipeline-mapの隣へ置く。
AnalysisRulesPageからLineWorkflowGuidePanelへ onNavigate={handleSectionChange} を渡す。
同hubのリンクはそのcallbackを呼ぶ。queryだけのLinkで画面を切り替えない。importキーは既存取込画面へ遷移する。
配信ボタンは /super-admin/tcg-distribution へnavigate。新規routeや権限を増やさない。
概要、始める前の資料、目次、7手順、例外時の案内を縦1列で表示する。
手順はol/li、各手順はCard variant=container density=compact、担当はBadge、操作先はButton。
Cardはcomponent-standardの登録部品で本番hubにも使用済み。Preview限定コメントを新たな使用禁止とは解釈しない。
手順内はh3とdl/dt/dd。目次は通常のa要素で #line-workflow-step-1 から7までのh3 idへ移動する。
ページ全体見出しは既存PageLayout、ガイド見出しはh3。独自ボタン/カード/バッジ外観は作らない。
専用CSSは折返し・縦配置のみ。media query不要、minmax(0,1fr)等で狭い幅にも収める。
使用token集合: --space-1/2/3/4/5/6/8、--comp-card-gap、--role-section-title-size/color、--role-card-title-size/color、--role-body-color、--role-caption-size/color。
外観のbackground/border/radius/shadow/paddingはCard金型へ委譲する。新しいtokenは作らない。
全表示文字列・aria-labelはja/enの analysisRules.lineWorkflowGuide 配下のt参照。sidebarラベルも両言語で追加。
業務データや設定値を静的モデルに保存しない。段階順・翻訳キー・実在画面への参照だけを持つ。

### 原稿契約（現在の実装を説明する）

| 段階 | 担当と説明 | 確認先・例外 |
|---|---|---|
| 1 LINEの記録を取り込む | 人が書き出した.txtと対象期間を指定。既定24時間、0は全期間 | 取込画面。設定済み端末の自動取込は別入口として補足し、ブラウザの端末設定機能を創作しない |
| 2 誰から届いたか確認する | システムがLINE表示名で仕入元照合。不明なら人が既存仕入元選択/新規登録。すべて解決後に抽出開始 | 仕入元マスタ。既存選択はその仕入元のLINE名を更新する点を明記 |
| 3 今回扱う投稿を選ぶ | 期間内の仕入元ごとの最新投稿を選び、原文保存と抽出待ちへ | 原文/期間の確認は取込画面。未記載商品の扱いを推測で追加しない |
| 4 商品情報を読み取る | システムが除外条件を確認して商品/数量/価格等を抽出。空文/除外/失敗を区別 | extraction-rules、knowledge-aliases、prompt-config。失敗はerror-logへ |
| 5 登録情報と照合する | 商品/単位/状態のマスタを参照して整理。自動解析は設定が有効な場合に進む | product-master、unit-master、conditions-master。設定無効時の自動進行を保証しない |
| 6 結果と要確認を確認する | 人が取込画面の結果と要確認を確認し、参照設定の不足を調べる | 取込画面と各マスタ。未実装needs-reviewタブや無効な保存操作へ誘導しない。error-logは開くだけ |
| 7 配信内容を確認して実行する | 人が配信候補/除外件数を確認後に実行。対象シートの内容は全置換 | 配信画面。個別行プレビューや任意対象選択を約束しない。自動配信は設定条件つきの別動作として補足 |

各行を前述の7項目へ展開し、設定名だけでなく「なぜ見るか」を平易に説明する。
例外は該当段階の子として示し、不明仕入元→照合、抽出失敗→エラーログ、要確認→結果/マスタ確認の戻り先を明記する。
ガイド自身は抽出開始/再試行/配信を実行しない。現在のDB値や本番環境変数は読まず、有効と断定しない。

### 検証と維持

新規unitは7段階構造、各callback、配信pathname、ja/en切替を検証し、本文を全写しするだけのテストを避ける。
新規E2Eは実hubのメニュー→ガイド→既存画面の遷移、query/pathname、390/1440幅、light/dark、キーボードを検証。
ガイド初期表示中のPOST/PUT/PATCH/DELETEは0件。権限確認GETは許容する。外部画面へ移動した後の操作はこの検査対象外。
frontendのcheck:all/build、関連unit、該当E2E、CIを実施。モックE2Eと本番確認の結果は区別する。
守り手は新規 LineWorkflowGuidePanel.test.tsx と frontend/tests-e2e/analysis-rules-line-guide.spec.ts および既存UI/i18nチェック。
抽出・解析・配信の動作変更時は本reconとの対応を人手レビューする。本文の意味は機械テストだけでは保証できない。
外部事例は不要: 新しい処理方式を導入せず、実在する操作と登録UI部品を説明面へ結び付けるため。出典不明の効果数値を採らない。
代替案の横長ReactFlow増補は、既存マップと重複し長文説明にズームを要するため採用しない。長い縦ページになる代償は目次で軽減する。
接触面: 人=管理者の読解/導線、エージェント=実装/原稿保守、機械=frontend CI、データ=書込なし、本番=frontend配信、外部=新規API連携なし。

### 設計自己審査

Astra: APPROVE（設計合格）。根拠はrecon追補、登録金型、callback契約、既存route、検証条件との照合。
未解決の実装前提なし。本番設定の有効状態は未確認のまま断言しない設計にした。PO画面確認・実装検証・CI・マージ・本番反映は別途未完了。

### 2026-09-28実装レビュー記録

Astra: コード差分レビューAPPROVE。設計自己審査と実装結果レビューを区別する。
Solの読み取り専任レビューもAPPROVE（指摘0）。生成担当とは別セッションのAIレビューであり、人による承認ではない。
静的照合: PanelにAPI呼出0、既存callback/navigateのみ、ja/enキー89/89一致、新規DB/API/route/token 0。
Astraがコンポーネント・CSS・hub配線差分を直接読み、既存部品とtoken利用を確認。デスクトップとモバイルのfullPage画像を目視。
Sol実行報告: check:all/build exit0、関連unit17/17、Chromium E2E6/6。Astra自身による再実行ではない。
E2Eはモック環境。本番設定・本番表示・POの読みやすさ確認・CIは未確認。
CARD-LINE-GUIDE-03: 390x900の可視範囲追加E2E 2/2成功（7.3秒）。冒頭/手順1/手順7をja/enで画像6枚取得、操作ボタンのclick trial成功。
Astraは日本語手順1・英語手順7のviewport画像を直接確認し、見出し/本文/操作ボタンに下部メニューが重ならないことを確認。
画面証跡: /tmp/reports/card-line-guide-01/guide-390-ja-light-viewport-step1.png および guide-390-en-dark-viewport-step7.png。
判定: ローカル実装レビューAPPROVE。本番投入可の承認やPOの読解確認を兼ねない。

### PR手続きの未解決事項（実装と分離）

scripts/gh-pr-create-safe.sh:26-43はPR作成前にprocess-artifactsを実行するが、入力SHAやbody-fileを検査へ渡していない。
scripts/check-process-artifacts.js:668-674はSHA必須、:706-744は既存PR番号から本文取得、:300-329は番号付きGO原文を要求する。
既存のGO転記設計はPR作成後に番号付き承認を受ける順序。この不整合を、偽のPR番号・GO原文・MOCK/skip設定で通過させない。
正式PR操作の実結果は後続カードで取得する。本節の読み取り結果だけでPR作成失敗済みとは断定しない。
