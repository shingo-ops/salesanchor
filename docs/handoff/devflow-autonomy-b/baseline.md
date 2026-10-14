# baseline-v5

対象: 2026-09-22〜10-06 mainマージ 284件（_t0922.json／_cache0922.json 再利用、classify-v5.py。v4 は無変更）。repo・GitHub・本番への書き込みなし（gh は pr view の読み取りのみ）

## 1. 分類集計

- A: 186
- B（Lを除く）: 55
- L（台帳のみ）: 38
- どちらでもない: 5
- 合計: 284

v4 → v5: A 141→186、B 101→55、L 37→38、その他 5→5。

変更内訳（_v5-rows.json と _v4-rows.json の差分、50+4+1 件）:

- B→A（題名が feat:／feat( ）: 50件（下記「分母から外れた PR」）
- A→B（語の判定を `frontend/src/`・`backend/app/`・直下に限定した結果）: 4件 #3755 #3763 #3769 #3873
- A→L: 1件 #3940（台帳ファイル名の -auth が語に当たらなくなった）

## 2. 照合

- 認証9本: 9/9 が A のまま（classify-v5.py の isA を各パスに直接適用。9本とも `frontend/src/`・`backend/app/` 配下なので語の限定の影響なし。出力 _v5-out.txt）
- #3940: A→L になった（_v5-rows.json の cls=L）
- tokens.css を含む PR 8件: #3895 #3816 #3811 #3808 #3806 #3804 #3746 は A、#3749 だけ B（#3816 #3811 #3808 #3806 #3746 は feat 題名のため A。tokens.css 単独で A になる PR は 0件）
- 語の限定の副作用で A のまま残る例: `deploy` の語は指示の対象外のため変更せず、`docs/handoff/dist-deploy-guard/gas-deploy-runbook.md` を含む #3992 #3980（docs だけの PR）は A のまま。数字には影響しない（不具合判定の候補に入っていない）。要否は Opus 判断

## 3. 不具合判定（S3 基準値、v5）

候補の組: 102（新 B 55件のうち、マージ後7日以内に main へマージされ、frontend/src/ か backend/app/ のファイルを共有し、題名に fix/修正/不具合/EMERGENCY/hotfix/Revert を含む PR との組）。候補を持つ B は 29件、fix PR は 33件。fix 側の定義は v4 と同じで、題名が feat: でも「修正」を含めば fix 側に数える（例 #3793）。

- **原因あり B: 3 / 55（5.5%）**（#3717 #3736 #3763。組では3組）
- 判定不能のみの B: 2件（#3712 #3716。組では2組）。原因には数えない
- 別件: 97組
- 感度: 判定不能2件も原因に数えると 5/55＝9.1%。#3736 を判定不能に倒すと 2/55＝3.6%

### v4 からの変化（原因 10件 → 3件）

- v4 の原因 10件 #3710 #3717 #3724 #3746 #3752 #3774 #3787 #3811 #3818 #3906 のうち、#3717 以外の9件は題名が feat のため B から外れ A に移った（分母 101→55、原因 10→1）
- 新たに原因: #3736（MEDIUM-2）、#3763（新 B になった #3763 の組）。合わせて 1+2=3

### MEDIUM-2: #3736→#3793（人手で patch・本文を読んだ結果＝原因）

- #3736（B）は tcg_analyzer_svc.py の analyze_extraction_job に `_resolve_pid` と `product_code_to_id`（public.products の product_code→id 辞書）を追加し、validate_product_id が None の値を product_code_to_id で救う（B 側 hunk @@ -1209、+`mapped_id = product_code_to_id.get(pid)`）
- #3736 の前は `validate_product_id(pid, reference)` を直接呼んでいた。`git show cf7cd489b^1:backend/app/services/tcg_work_reference.py` の 55-63 行で、参照に無い値（"-" を含む）は None を返す
- #3793（本文「バグ修正3件: `-` ガード…」）の fix 行は `if pid is None or pid == "" or pid == "-":`（fix 側 hunk @@ -1271）。docs/handoff/extraction-prompt-config/recon.md の記述と migrations/20260926_080100_fix_product_code_dash.sql のコメントで、products.id=61 の product_code が "-" だった（30th BOX の誤解決）
- 判定: #3736 が追加した救済処理が "-" を id 61 に解決する経路を作り、#3793 がガードを足した。B が追加した関数のガード漏れなので原因
- 【未確認】本番で "-" が実際に Gemini から返り id 61 に解決された件数（本番ログは見ていない）。recon.md の記述 "'-' が validate_product_id に渡される" は、前述の 55-63 行の挙動と合わず、実際の経路は救済処理（product_code_to_id）側と読んだ

### 新 B になった PR の組（新規 10組、人手で patch・本文を読んだ結果）

- 原因: #3763→#3769（#3769 が除去した `sm_old.received_at < (...)` は #3763 が追加した条件。本文「旧ロジックは自分より古いメッセージの…を FALSE にする方向更新だったため…二重TRUE不整合」）
- #3736→#3793 と上記 以外の9組は別件（表のとおり）
- MEDIUM-2 の判断との関係: 「#3763→#3769 は原因の可能性」（Fable 未確認欄）は、patch で追加行の一致を確認でき原因とした

### 判定方法

1. v4 の判定（_v4-judge.json 305組）のうち、新 B と fix の組 92組はそのまま使用（理由文も v4 のまま）
2. 新 B で v4 にない組 10組（#3755 #3763 #3769 #3873 が B 側）は、patch と PR 本文を人手で読んで判定。#3736→#3793 は v4 で別件だったが人手で読み直して原因に変更
3. 全102組について「fix の削除行（12文字以上）が B の追加行と一致するか」の照合を実行（_v5-content.txt）。一致10組: #3763→#3769 #3755→#3763 #3755→#3769（以上 新規・上記で人手判定）、#3736→#3793（原因に変更）、#3716→#3717（判定不能維持）、#3712→#3714（判定不能維持）、#3715→#3716 #3756→#3759 #3683→#3693 #3661→#3714（v4 で人手判定済み。patch を読み直して別件を確認）。一致しなかった残り92組に新たな取りこぼしはなし
4. 注意: 行範囲が B マージ後の他 PR でずれる可能性は、3 の文字列照合で #3736→#3793 を拾った以外の取りこぼしは検出されなかった

### LOW-1: baseline-v4.md:31 の「候補39組」の件数

- 確かめた値: 候補の組 305（_v4-judge.json）、B 66件、fix PR 46件（_d4/fixlist.txt の語数 46、_d4/f*.json 46本）。人手で読んだ組（行範囲の交差または本文参照）は 65組（fix 33件・B 40件）、機械別件は 240組
- 「39」に一致する数は再現できなかった。:31 は書き誤りで、正しくは「候補305組中の全 fix PR（46件）」（:23・:349 と一致）

## 4. 分母から外れた PR（v4 の B 101件のうち50件。全件が題名 feat:／feat( で A へ移動）

|PR|題名|v4 での不具合判定|
|--|--|--|
|#3662|feat: ルールテストUX改善（非エンジニア向け）|-|
|#3685|feat: 買取相場の手動取得ボタン追加|-|
|#3704|feat: buyback prices phase 2 — product_type filter, sort params, tab counts|-|
|#3709|feat: add period selector (7/30/90 days) to buyback price history chart|-|
|#3710|feat(dashboard): 提供者別パイプライン可視化|原因|
|#3723|feat: improve extraction rules UI for non-engineers|-|
|#3724|feat: 買取マッチングをスコア式に改善|原因|
|#3726|feat: フォーマットビルダー UI を仕入元抽出ルール設定ページに追加|-|
|#3727|feat: use Gemini resolved_product_code for pid resolution|-|
|#3740|feat: 買取相場に商品名検索＋価格変動フィルタを追加|-|
|#3741|feat: カテゴリタブをDataTableに連結したレイアウトに変更|-|
|#3742|feat: redesign import history table|-|
|#3743|feat: 買取相場ページのレイアウト再構成|-|
|#3746|feat: 買取相場を商品マスタ軸表示に統一|原因|
|#3748|feat: simplify RuleCreateDrawer — test gate, auto-ID, streamlined UX|-|
|#3751|feat: SAAS管理者メニュー改善（LINE解析改名・買取相場移動・常時表示化）|-|
|#3752|feat: buyback by-product view — mark, best price, best shop, yesterday diff|原因|
|#3760|feat: 全マスタパネルをDrawer化・コード列廃止・編集削除ボタン廃止|-|
|#3762|feat: LINE解析ダッシュボード タブ別問題表示の分離|-|
|#3767|feat: add chart period selector (7/30/90/180/360 days) to LINE解析 dashboard|-|
|#3774|feat: ダッシュボードインポートタブにファイルアップロード機能を統合|原因|
|#3784|feat: add grade switching to buyback price history chart|-|
|#3786|feat: add price summary below buyback history chart|-|
|#3787|feat: 抽出タブにワーストランキング機能を追加|原因|
|#3790|feat: merge StatusMasterPanel into RuleManagementPanel + rename extraction rules|-|
|#3792|feat: 抽出ランキングにCTAボタンを追加|-|
|#3806|feat: パイプラインマップの視認性改善|-|
|#3808|feat: redesign pipeline map as business flowchart|-|
|#3810|feat: KnowledgeAliasesTabをLINE解析サイドメニューに接続|-|
|#3811|feat: redesign pipeline map as RPG skill tree|原因|
|#3813|feat: KnowledgeAliasesTab i18nラベル改善（DBカテゴリ対応）|-|
|#3816|feat: redesign pipeline map as business procedure flowchart|-|
|#3817|feat: 抽出タブ3段構成リデザイン|-|
|#3818|feat: 抽出タブ個別ジョブテーブル追加|原因|
|#3821|feat: 抽出テーブル列改善（解決/未解決/提供者名）|-|
|#3861|feat: LINE お知らせ判定を1か所にまとめる（段階1 C1）|-|
|#3898|feat: add AI Studio-style health charts to LLM usage tab (requests/success rate,|-|
|#3906|feat: consolidate LLM usage charts into one card|原因|
|#3911|feat: show LLM usage costs in JPY using the fx rate SSOT (ADR-148)|-|
|#3918|feat: 商品の照合に Gemini が写した商品名を使う（PR-3a）|-|
|#3922|feat: 短い値・数字だけの値の照合に語の境界を条件にする（PR-3b）|-|
|#3926|feat: ボタン案内・ウェルカムをサーバー名義で投稿|-|
|#3933|feat: Discord自動セットアップのカテゴリを DM / 在庫(メンバー) / 在庫(大口) に3分割|-|
|#3944|feat: auto-restore ticket-start when a ticket channel is deleted|-|
|#3983|feat: add Search Keywords column to distribution sheet (13 columns)|-|
|#3994|feat: Gemini 指示書 d（まとめ書きの行の確かめ方）を比較試験用に追加|-|
|#3995|feat: count PO-rule bulk corrections as manually reviewed condition|-|
|#3996|feat(frontend): SelectControl に karte/header/tabbar の種類を登録（金型化 §AW AW-1）|-|
|#3999|feat: add Gemini prompt e|-|
|#4001|feat: default box-category products to Sealed box when unit is ambiguous|-|

新たに分母に入った PR（A→B）: #3755（fix(pipeline): condition-level supersession (ADR-1） #3763（fix(pipeline): prevent older message re-analysis f） #3769（fix(pipeline): use global-latest supersession for ） #3873（fix: read Gemini output tokens via candidates_toke）

## 5. 判定表（B番号｜候補fix番号｜判定｜根拠）。原因・判定不能を先頭、別件は後ろ。新 B のみ

|B番号|候補fix番号|判定|根拠|
|--|--|--|--|
|#3717|#3730|原因|central_masters.py SupplierSourceMessage: B追加の id: int を fix が UUID に修正（本文「Pydanticが int で定義」）|
|#3736|#3793|原因|#3736 追加の _resolve_pid は validate_product_id が None を返す値を product_code_to_id で救済するため、"-"（products.id=61 の product_code）が id 61 に解決される。#3736 前は validate_product_id("-") が None（tcg_work_reference.py:55-63）。#3793 が `or pid == "-"` ガードを追加、migration コメント「product_id=61 の product_code が '-'」|
|#3763|#3769|原因|#3769 本文「旧ロジックは自分より古いメッセージ行を FALSE にする方向更新だったため…二重TRUE不整合」。patch で fix が除去した `sm_old.received_at < (...)` は #3763 が追加した条件そのもの|
|#3712|#3714|判定不能|tcg_analysis_dashboard_svc.py: fix が B の sc.channel AS channel_name を COALESCE(s.name,..) に変更（題名「提供者名修正」）、誤りかは本文から不明|
|#3716|#3717|判定不能|SupplierExtractionRulesPage.tsx: 本文「PR #3716でフラット構造に修正したバックエンドに対し型が旧ネスト」だが、fix の変更行は B の変更行（id/unit_ng_count）と別|
|#3661|#3714|別件|fix は別機能の追加・変更。B と fix の変更行の重なりは文脈行のみ（機械判定+題名）|
|#3661|#3716|別件|fix は別機能の追加・変更。B と fix の変更行の重なりは文脈行のみ（機械判定+題名）|
|#3663|#3681|別件|本文「#3663でスキーマ参照を直した後も…」原因は supplier_channels の行欠落（9/21 tenant_004 削除）で B の誤りではない|
|#3663|#3845|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3681|#3845|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3683|#3693|別件|TcgParallelReportPage.tsx: fix の変更行(compatV1Description, PIDEresolutionRate 等)は B が変換した行と別|
|#3683|#3695|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3683|#3714|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3683|#3716|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3683|#3717|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3683|#3753|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3683|#3757|別件|fix は別機能の追加・変更。B と fix の変更行の重なりは文脈行のみ（機械判定+題名）|
|#3683|#3793|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3695|#3714|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3695|#3716|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3695|#3717|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3695|#3734|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3695|#3753|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3695|#3756|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3695|#3757|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3695|#3759|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3695|#3793|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3711|#3712|別件|本文: sc.name の誤記は #3710 由来、#3711 のエラー修正で「顕在化」しただけ|
|#3711|#3714|別件|fix は別機能の追加・変更。B と fix の変更行の重なりは文脈行のみ（機械判定+題名）|
|#3711|#3819|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3711|#3822|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3712|#3819|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3712|#3822|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3715|#3716|別件|fix は id→supplier_id 等の型名修正で、B の /api/v1 削除行と別|
|#3715|#3717|別件|同上|
|#3715|#3730|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3716|#3730|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3716|#3753|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3716|#3757|別件|fix は別機能の追加・変更。B と fix の変更行の重なりは文脈行のみ（機械判定+題名）|
|#3716|#3781|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3716|#3793|別件|fix は別機能の追加・変更。B と fix の変更行の重なりは文脈行のみ（機械判定+題名）|
|#3716|#3895|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3717|#3753|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3717|#3757|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3717|#3793|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3717|#3895|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3734|#3756|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3734|#3759|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3736|#3750|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3736|#3755|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3736|#3763|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3736|#3769|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3736|#3783|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3749|#3759|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3749|#3895|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3750|#3755|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3750|#3763|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3750|#3769|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3750|#3783|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3750|#3793|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3753|#3757|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3753|#3772|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3753|#3776|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3753|#3781|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3753|#3789|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3753|#3793|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3753|#3794|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3753|#3895|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3753|#3907|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3753|#3917|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3755|#3763|別件|#3763 が直した「received_at を見ない UPDATE」は #3755 以前の product_id 照合版にも無く、#3755 の変更（product_id→(product_id,condition_id)）の誤りではない|
|#3755|#3769|別件|#3769 が直した二重TRUEは「古い行だけ FALSE にする方向更新」(#3763 追加の received_at < 条件)に由来。#3755 の変更行ではない|
|#3755|#3783|別件|#3783 は GEMINI 直採用の exclude_keywords 迂回の修正。_merge_supplier_products と別関数|
|#3755|#3793|別件|#3793 の修正は _resolve_pid の "-" ガード。別関数|
|#3756|#3759|別件|同上（SSOT化。本文に B の誤りの記述なし）|
|#3763|#3783|別件|#3783 は GEMINI 直採用の exclude_keywords 迂回の修正。別関数|
|#3763|#3793|別件|#3793 の修正は _resolve_pid の "-" ガード。別関数|
|#3764|#3793|別件|fix は別機能の追加・変更。B と fix の変更行の重なりは文脈行のみ（機械判定+題名）|
|#3764|#3895|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3764|#3907|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3764|#3917|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3769|#3783|別件|#3783 は GEMINI 直採用の exclude_keywords 迂回の修正。別関数|
|#3769|#3793|別件|#3793 の修正は _resolve_pid の "-" ガード。別関数|
|#3772|#3776|別件|同上|
|#3772|#3781|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3772|#3789|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3772|#3794|別件|B の変更行は率の式と無関係（コンテキスト行の重なりのみ）|
|#3776|#3780|別件|AnalysisDashboardPanel.css: 誤りの --color-border 行は #3774 の追加で #3776 の行ではない|
|#3776|#3781|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3776|#3789|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3776|#3794|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3781|#3789|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3781|#3793|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3781|#3794|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3789|#3794|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3798|#3895|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3819|#3822|別件|同上（別機能の絞り込み追加）|
|#3873|#3876|別件|#3876 は docstring/コメントのモデル名修正のみ（実行コード変更なし）。#3873 の誤りの修正ではない|
|#3901|#3907|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3901|#3917|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3907|#3916|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|
|#3907|#3917|別件|同一ファイルを触るが B の変更行と fix の変更行が重ならない（hunk 範囲）|

## 6. 使ったコマンド

- python3 classify-v5.py（classify-v4.py の isA の語 2行に `inscope=p.startswith('frontend/src/') or p.startswith('backend/app/') or '/' not in p` を追加、cls==B かつ題名が `^\s*feat(:|\()`（re.I）なら A。出力 _v5-rows.json／_v5-out.txt）
- sed で _v4-cand.py の入出力名を v5 に替えた _v5-cand.py（候補抽出 → _v5-cand.json、102組）
- gh pr view N -R shingo-ops/salesanchor --json title,body,mergedAt,files（N=3736 3793 3755 3763 3769 3783 3873 3876、保存 _v5/prN.json。読み取りのみ）
- 内容照合: _v5-content.txt を作った python（fix の '-' 行と B の '+' 行の文字列一致、12文字以上）
- git -C /Users/tanizawashingo/salesanchor fetch origin；git show cf7cd489b^1:backend/app/services/tcg_work_reference.py；git show origin/main:migrations/20260926_080100_fix_product_code_dash.sql；git show origin/main:docs/handoff/extraction-prompt-config/recon.md（読み取りのみ）
- python3 _show.py B fix 部分文字列（patch 比較）、python3 _v5-tally.py（集計・_v5-judge.json・_v5-tally.txt）
