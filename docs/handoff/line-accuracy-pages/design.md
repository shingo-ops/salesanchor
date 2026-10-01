# 設計書：LINE解析「要確認」の移設と「解析精度管理（新方式）」の新設

状態：**設計審査済み（Opus 自己審査：APPROVE）／PO の方針は合意済み（2026-10-01）／実装は未着手**

関連：現状把握は `docs/handoff/line-accuracy-pages/recon.md`、精度の根拠は `docs/handoff/line-accuracy-pages/accuracy-evidence.md`
関連ADR：ADR-027（i18n）・ADR-067（デザイントークン）・ADR-144（UIガバナンス）・ADR-158（要確認一覧）・ADR-1003（v7 書き写しと判定の分離）

審査の要点
- 未解決だった3点（原文の表示部品、S3 の定義、部品の置き場所）は、3-5 で実物をもとに決めた。
- 残る確認は次の2点。どちらも実装カードの中で行う。
  - 色に使えるデザイントークンがあるか
  - 全期間の集計にかかる時間（EXPLAIN で測る）

## 1. PO の決定（原文の要旨、2026-10-01）
- 要確認ページを、LINE解析のサブメニュー「要確認」に移設する。古いページは完全に削除してよい（自動で移す仕組みも不要）。
- 新システム用の「解析精度管理」ページを用意する。既存の「解析精度管理」とは別のサブメニューにし、名前は「解析精度管理（新方式）」とする（PO が「n」を選択）。

## 2. 現状（事実。origin/main、2026-10-01 時点の調査）
- LINE解析ハブ：`frontend/src/pages/super-admin/AnalysisRulesPage.tsx:123-213`
  - サブメニューは `?section=` で切り替える。
  - サブメニューの定義は `frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx:10-35`（キーの型）と `:78-129`（項目）。
- 既存の「要確認」：`frontend/src/pages/super-admin/AnalysisRulesPage.tsx:89-112` の NeedsReviewPanel。「準備中」を表示するだけ。
  - ダッシュボードからの導線が3か所ある：`frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:931`、`:1459`、`:1552`
- 既存の「解析精度管理」：`frontend/src/pages/super-admin/AnalysisRulesPage.tsx:56-87`。中身は旧方式（v6）の仕入元品質。
- 独立した要確認一覧のページ：移設前（origin/main 01c275171 時点）：frontend/src/pages/super-admin/NeedsReviewListPage.tsx
  - 3タブ（`:459-470`）。PageLayout を内包している。
  - ルート：`frontend/src/App.tsx:97`（import）、`:308-309`（Route）
  - メニュー：`frontend/src/components/DesktopShell.tsx:194`、`frontend/src/components/MobileShell.tsx:170-175`
  - 試験：移設前（origin/main 01c275171 時点）：frontend/src/pages/super-admin/NeedsReviewListPage.test.tsx:7、`:61`
- 新方式の API：`backend/app/routers/tcg_shadow_review.py`
  - shadow-results（needs_review・supplier_id・offset・limit）、bottlenecks、keyword-preview
  - 精度を集計する API はない。
  - 原文の全文（raw_text）は返していない。
- 権限：LINE解析も要確認一覧も、SaaS 管理者だけが見られる。画面は `useSuperAdmin`、API は `require_super_admin`（`backend/app/auth/dependencies.py:453`）。
- 精度の調査結果（この設計の根拠）
  - scratchpad の accuracy-interim-report.md
  - scratchpad の gemini-copy-fidelity.md
  - /tmp/CC報告ファイル/accuracy-eval/

## 3. 作るもの
### 3-1. 要確認の移設（画面のみ）
- NeedsReviewListPage の中身（3タブ、モーダル、API 呼び出し）を、PageLayout を外したパネル部品にして、`frontend/src/pages/super-admin/AnalysisRulesPage.tsx` の section `needs-review` に表示する。
  - 新しい部品の置き場所：新規作成予定：frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx
- 削除するもの
  - 移設前（origin/main 01c275171 時点）：frontend/src/pages/super-admin/NeedsReviewListPage.tsx 本体
  - `frontend/src/App.tsx:97` と `:308-309`
  - `frontend/src/components/DesktopShell.tsx:194` と `frontend/src/components/MobileShell.tsx:170-175`
  - 使われなくなった i18n キー（`nav.superAdminNeedsReview`。ja と en の両方）
- 試験は、新しい部品の試験に移し替える。
- 中身（タブ、列、ワード登録）は変えない。純粋な移設とする。

### 3-2. 「解析精度管理（新方式）」の新設
- サブメニューに次を追加する。
  - キー：`accuracy-management-v7`
  - 名前：ja「解析精度管理（新方式）」、en「Accuracy Management (New)」
  - 位置：「解析精度管理」の直後
- パネルには 2つのタブを置く（既存の Tabs を使う）。
  1. **精度サマリー**
     - 期間（7日、30日、全期間）と仕入元で絞り込める。
     - 表示する数字
       - ブロック数
       - 自動確定率
       - 商品の判定（matched、ambiguous、unmatched）
       - 価格と数量が確定した割合
       - 状態の内訳
       - 完売の件数と予約の件数
       - **誤りの兆候の件数**（定義は 3-3）
     - 仕入元別の表：ブロック数、確認待ちの率、兆候の件数
  2. **投稿照合**
     - 投稿の一覧。絞り込みは、仕入元、日付、確定済みか確認待ちか、兆候の種類。
     - 行を選ぶとドロワーが開く。
       - 左：原文（行番号つき、ブロックの範囲を色分け。既存の SourceRawPane を流用できるかは実装前に確かめる）
       - 右：ブロックごとに次の3段を並べる
         - Gemini の書き写し（raw_* の各欄）
         - システムの解析結果（商品名と品番、状態、価格、数量、発送、完売）
         - 確認待ちの理由と根拠（review_items、evidence）
- 見るだけの画面とし、データは変えない。

### 3-3. 新しい API（読み取りのみ、`require_super_admin`）
- `GET /api/v1/tcg/shadow-accuracy/summary?days=7|30|all&supplier_id=`
- `GET /api/v1/tcg/shadow-accuracy/posts?days=&supplier_id=&needs_review=&signal=&offset=&limit=`
- `GET /api/v1/tcg/shadow-accuracy/posts/{extraction_job_id}`
  - 返すもの：raw_text、行の配列、その run の全ブロック（raw_*、判定結果、review_items、evidence）
- **誤りの兆候は、1つの backend モジュールで SQL の式として定義する（SSOT）。** summary と posts の絞り込みは、同じ定義を使う。
  - S1 完売の見落とし：ブロック本文か raw_* に完売などの語があるのに、status が In Stock
  - S2 予約の見落とし：見出しかブロックに「予約」があるのに、ship_offer_type が空
  - S3 単位による単品扱い：condition が FLAG_SINGLE で、raw_unit が単品の単位（枚など）ではない
  - S4 短い記号での確定：matched で、根拠が RAWCODE、かつ品番の mark が2文字以下
  - S5 見出しの商品名を照合していない：見出しがあり、unmatched か ambiguous
  - S6 単位の補完：raw_unit がブロック本文にない
- 範囲は、一括実行と、今後の試運転で作られた shadow の run 全体。期間は started_at で絞る。
- データ量は現時点で約6,700ブロック、全件の実行後は約1.6万ブロックの見込み。一覧はページングする。

### 3-5. 実物の確認で決めたこと（2026-10-01 追記）
- **部品の置き場所**
  - パネル：新規作成予定：frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx、新規作成予定：frontend/src/pages/super-admin/components/ShadowAccuracyPanel.tsx。既存の `frontend/src/pages/super-admin/components/ExtractionErrorLogPanel.tsx` などと同じく、css と test を同じ場所に置く。
  - 原文の表示と比較の部品：`frontend/src/features/tcg-analysis-review/`
- **原文の表示**
  - 既存の SourceRawPane は変更しない。
    - 強調できるのは1行だけで、2.6秒で消える。範囲を指定して色分けする仕組みがない。
    - 日本語が直書きされている。i18n 違反の既存の負債として、別件で扱う。
    - SupplierDetailView から使われている。
  - 新規作成予定：frontend/src/features/tcg-analysis-review/ShadowSourcePane.tsx を作る。
    - 行の分割は `sourceRawLines`（`frontend/src/features/tcg-analysis-review/sourceRawNavigation.ts:3`）を再利用する。
    - 行番号を表示し、ブロックと見出しの範囲を色分けする。色はデザイントークンを使う。
- **詳細の出し方**
  - ドロワーは幅が 480px 固定（`Drawer.css:30`）で狭いため、使わない。
  - パネルを左右2列に分け、左を投稿一覧、右を詳細にする。SupplierDetailView と同じ構成。
- **比較の表示**
  - ItemComparison は流用しない。項目が6つで固定されていて、jump の指定も必須のため。
  - ブロックごとの3段（書き写し・判定・理由）を、既存の DataTable と Card で新しく作る。
- **兆候 S3 の厳密な定義**
  - 条件：condition が FLAG_SINGLE で、raw_unit を単位マスタで引いた kubun が「単品系」ではない。マスタに無い単位や空の単位も含める。
  - 照合方法：resolve_unit_v2 と同じく、`public.unit_aliases` と `public.units` に完全一致または小文字一致で当てる。
- **別件として記録する食い違い**
  - CN0008 の適用区分は「枚系,単位不明」になっている。
  - 単位マスタには「枚系」という kubun が存在しない（実際は「単品系」）。
  - そのため、単品系の単位に対して、優先度1のキーワード経路が当たらない。
- **バックエンド**
  - 新しく作るファイル
    - 新規作成予定：backend/app/routers/tcg_shadow_accuracy.py
    - 新規作成予定：backend/app/services/tcg_shadow_accuracy_svc.py
    - 新規作成予定：backend/app/services/shadow_accuracy_signals.py（兆候の SQL 式の SSOT）
  - 作りは tcg_shadow_review と同じにする。
    - router に prefix を付けず、`backend/app/main.py` で `/api/v1` を付ける。
    - require_super_admin と get_db を使い、dict を返す。
  - 試験
    - router は mock で試験する。
    - 実 PG では、表を migration で作り、行を INSERT して兆候を固定する。
    - 試験の中に表の定義は書かない（test-schema-dup gate のため）。

### 3-4. 触らないもの
- migration、deploy.yml、判定ロジック、旧方式（v6）の画面と API、既存「解析精度管理」の中身

## 4. 案の比較
- 新旧を同じ画面のタブに並べる案は、PO が「n」を選んだため採らない。
- 兆候を画面側で計算する案は採らない。件数が多く、ページングと両立しないため、SQL で計算する。

## 5. リスクと対処
- 兆候は、誤りそのものではなく誤りの候補である。画面には「兆候」と明記する。
- 抜き取りで確かめた的中率（G1・G6・G7・G8 は 10件中 8〜10件）を、設計書に根拠として残す。
- 重い SQL：全期間の集計は、件数の上限と索引を確認したうえで、実装前に EXPLAIN で測る。
- 削除するページへの外部リンク：docs 以外のコードからの参照がないことは確認済み（調査報告の 6）。

## 6. 受入条件と検証方法
| 基準 | 検証方法 |
|---|---|
| LINE解析の「要確認」に3タブが出て、旧ページと同じ件数・列が見える | 本番の画面で確かめる（同じ時刻の API の total と表示件数が一致する） |
| `/super-admin/needs-review` が無く、サイドバーにも出ない | 画面とコードの検索 |
| 「解析精度管理（新方式）」のサマリーの数字が、DB を直接集計した値と一致する | 読み取り SQL の出力と画面の数字を、1期間・1仕入元で比べる |
| 兆候 S1〜S6 の件数が、調査時の件数（C1、C7、C5、C2 など）と同じ定義で再現される | 同じ母集団での SQL 比較 |
| 投稿照合で、原文・書き写し・判定が1画面で見られる | 本番の画面で、バッチ1 の3件（fde72f32、c5bac2bd、4071bb1f）を開いて確かめる |
| i18n の ja と en のキーが一致し、ハードコードがない | CI（i18n、UI governance、Lint） |
| SaaS 管理者以外は見られない | API の 403 試験と画面のガード |

## 外部・過去事例の参照と我々への応用
- 過去事例（社内）：旧方式の解析精度管理（TcgSupplierQualityPage と features/tcg-analysis-review）にある「仕入元一覧＋原文の対比」の構成を流用する。
- 外部事例：社内のデータで直接測れる表示機能なので、使わない。

## 維持の仕組み
- 守り手: 設計担当（Opus）が設計書と兆候の定義を管理し、実装担当（Sonnet）が frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.test.tsx などの試験を維持する
- 守り手：設計担当（Opus）が兆候の定義を管理する。定義は backend の1モジュールに置き、試験で固定する。
- 兆候を増やすときは、このモジュールと設計書を同時に更新する。
