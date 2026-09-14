---
mode: handoff
---
# Phase 3 設計 — 完売ルール（既存解析結果の閲覧）

対象ADR: ADR-113 / ADR-154
recon: docs/handoff/tcg-import-latest-only/sold-out-page/recon.md
日付: 2026-09-14
Planner/Architect: 同一AIによる設計・自己審査。独立レビューではない。
親: docs/handoff/tcg-import-latest-only/design.md

本書は親の審査済み閲覧便を実装PRで参照できるよう切り出した仕様。親の将来の在庫投影設計は本便の範囲に含めない。PO最新確定のメニュー名「完売ルール」を使用する。ルールの編集画面へ範囲を拡張しない。

## 外部・過去事例の参照と我々への応用

外部事例は不要。対象は既存DBの読み取り表示であり、本番集計・既存API・認証・画面規約の直接照合を根拠とする。未確認の他社実績を成功証明にしない。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| DBの同じ事実を複製保存せず既存正本を読む | SQLと依存の差分審査、書込・DDL・モデル呼出し0を確認 |
| 完売以外を返さず、過去の原文も対象 | 状態・原文active/history混在fixtureによるAPI試験 |
| 商品マスタ未登録や複数解析でも行数を偽らない | LEFT JOIN、ID一意性、単一SQL件数/ページ整合試験 |
| SaaS管理者のみ利用可能 | API認可試験、画面権限・メニュー試験 |
| 名称「完売ルール」と取得内容が誤解を生まない | 日英文言・現在庫ではない副説明・原文値表示を画面確認 |
| 検索、原文表示、通信失敗を扱える | UI単体試験と必要なブラウザー確認 |

## 売り切れ管理・既存解析正本の閲覧便（2026-09-14・審査対象仕様）

この節は専用ページの最初の公開範囲を定める。前の「現在売り切れ/確認待ち/判定履歴」の投影基盤依存案を一度に出すのではなく、現存するanalysis_resultsのSold out判定を読む閲覧便を先に出す。将来の在庫反映管理は削除せず後続とする。ページの作成依頼とSSOT制約に対し、未実装の現在庫を想像して表示しないための範囲確定である。

### Why: 実物の根拠

main7b3aea8cの既存analysis-results APIには売り切れ専用フィルターがない。_STATUS_TABSは6種のみ、SOLD_OUTは無変更関数試験でALLと同じWHEREになる。レスポンスに現在offerのid/availability/quantity/revision/quantity_event_idがなく、JOINはsm.is_active=TRUEに限定。既存APIへSOLD_OUTを渡すだけのUIは不採用。

本番tenant_004へ読み取り専用・statement_timeout=10000で3件のSELECTを実行。既存3表は存在し、新設計のtcg_stock_offers/events/restock_plans/controlはinformation_schemaの存在照会に出なかった。analysis_resultsの集計はIn Stock29714、Sold out550、Pre-order3。Sold outを原文までJOINすると550行・analysis ID550件、有効原文24・無効原文526、投稿日未記録526。この550は当該取得時点の解析行数で、商品数/現在庫数ではない。個別原文/氏名は集計出力へ含めていない。

### 正本・対象・表示

現在のanalysis_results.statusに保存された値が厳密にSold outの明細だけを対象とする。判定をページ/新サービスで再計算せず、空欄やexclusionのある行から完売を推測しない。DB新表/列/移行/在庫更新/モデル呼出し不要。原文はsource_messages、原文の数量/価格/単位/状態/メモはextraction_items、商品名は既存tcg_products（なければ原文名）、仕入元は既存のチャネル/仕入元マスタをLEFT JOINする。未登録マスタによる行落ちを起こさない。

SaaS管理者メニューのLINE取込直後、メニュー名・タイトル「完売ルール」（英語Sold-out rules）。URLは/super-admin/tcg-sold-out、navKeyはnav.superAdminTcgSoldOut。副説明は「保存された解析結果の売り切れ判定を確認できます。現在の在庫数・反映状況を示す一覧ではありません。」とし、画面に現在庫や反映済みを捏造しない。初期範囲はすべての原文。絞込みは「すべて/有効な原文/過去の原文」と商品名・仕入元名の検索。原文が有効であることと商品が在庫ありであることを混同しない。

1行は1analysis_result_id。列は商品名、仕入元、判定（売り切れ）、原文の数量/単位、原文の価格、投稿日、原文の状態。価格/数量は原文表示と明示し、0へ変換しない。原文日時nullは「投稿日未記録」。received_atや解析時刻から投稿日を捏造しない。過去の原文を隠して現在の商品数に見せない。行詳細で原文名/状態語/備考/全文を表示する。原文位置が有効なときだけ強調、無効なら本文をそのまま見せる。

操作は検索/ページ移動/再読込/原文表示のみ。数量変更、完売解除、再解析、配信、削除のボタンを置かない。将来の予定正規化は未検証なので、この便のメモは「原文の備考」。自動で「追加予定あり」と書き換えない。10件の人工試験結果や550件をデモ用の固定値として使わない。

### APIの厳密な契約

既存tcg_analysis_review routerにGET `/api/v1/tcg/sold-out-results`を追加し、require_super_admin/get_db/TCG_SCHEMAを再利用。新しい読み取り専用サービスへSQLを集約し、既存analysis-resultsの既定条件/型を変えない。

入力はq（string任意、最大100文字、前後空白を除去、空なら無条件）、source_scope（all/active/history、既定all）、offset（整数0以上、既定0）、limit（整数1〜100、既定50）の4件。未知scope/不正数値は422。qはei.raw_product_name/p.japanese_title/ts.nameの部分一致。ワイルドカード%/_/エスケープ文字は文字として扱い、サーバーでLIKE用エスケープしてbindする。クライアントがstatusを指定する口は作らず、WHERE ar.status='Sold out'をサーバーで固定する。

成功JSONはitems、total（0以上integer）、offset、limit、as_of（timezone付きISO日時）の5キー。1明細のキー/型は以下で固定する。

- analysis_result_id/extraction_item_id/source_message_id: UUID string。
- supplier_id/product_id: UUID string|null。仕入元はsc.supplier_idの参照先の実在ts.id、商品は実在p.id。原文の所属を別の商品へ書き換えない。
- provider/product_title/raw_product_name/raw_quantity/raw_price/raw_unit/raw_state/raw_memo/raw_text: string（SQL NULLは空文字）。product_titleはp.japanese_title、なければ空文字。UIで原文名fallbackを行い、原文採用と分かる表示にする。
- status: literal Sold out。
- source_is_active: boolean|null。nullは「原文状態不明」、history条件はFALSE、active条件はTRUE、allはすべて。
- line_posted_at: timezone付きISO日時|null。UIはJST表示。
- line_start/line_end: integer|null。強調の可否は1<=start<=end<=原文LF行数で判定し、補正しない。

JOINの軸はar→ei→ej→sm。sc/ts/pはLEFT JOIN。原文も失われている参照不整合は返却できないため、対象件数とJOIN後件数の差を検収で検出して失敗扱いとし、黙って「全件」を名乗らない。今回の本番照合では550=550。1対多のitem_correctionsやplanをJOINしないため、行が増殖しない。

取得順序はsm.line_posted_at DESC NULLS LAST, ar.id DESC。同じ条件のtotalとitemsは単一SQLでfiltered CTEから返す。countを別transactionで取得しない。offsetがtotal以上でもitems=[]/totalは実数。ページ移動間に更新された場合は一覧を不変snapshotとは称さず、as_ofを表示し必要時に先頭へ戻す。

raw_textはこの便では50件単位の応答に含め、遅延取得用の未実装APIを追加しない。画面では閉じた詳細に全文を置き、本文をHTMLとして実行しない。機微情報を通常ログへ出さない。本文重複の通信量は本番相当の50件応答で計測し、許容できない場合は勝手にページサイズを変えず詳細API分離を設計へ戻す。

失敗は認証失敗401/権限不足403、不正入力422、基盤不整合/取得失敗503の安定したコードを返す。未準備やDB障害を成功0件に変換しない。UIのエラーは既存api clientから安全なi18n文言へ対応。再読込失敗時は直前値に取得時刻/更新失敗表示を付けるか、取得不能の明示をする。

### 検証と範囲別の審査

受入: 本番と同じ構造のfixtureでSold out/その他状態を混在させ、完売だけ返す。active/history/allの件数、原文日時null、同名別単位、異なる抽出明細に紐づく解析結果を別IDで保持（extraction_item_idはUNIQUEであり同一明細の解析履歴を複数保存する意味ではない）、マスタ未登録の行落ち0、検索の%/_を文字扱い、SQL文字列を渡してもbind、0件/範囲外offset/同日時の安定順、一般ユーザーのAPI/画面拒否を検証する。画面は日英/原文表示/検索再ページング/通信失敗を確認し、PageLayout・nav/title同期・i18n・既存チェックを通す。コード中に在庫への書込/モデル呼出しがないことも差分レビューする。

本番確認はメニュー導線、権限、同じ取得時点の基盤集計とAPItotal一致、原文IDが一致した詳細、現在庫反映を断定しない文言を検証する。550/24/526は調査時の参考値であり本番検収値を固定しない。

Planner: 既存DBだけで提供できる閲覧ページの仕様を確定。Architect（同一AIの自己審査）: この閲覧便に限定してAPPROVE。根拠は本番3SELECTで存在・件数・JOIN一意性を直接確認、既存権限/ルーティング/i18n実物を照合し、新在庫基盤から切り離してSSOTを保持できること。実装の正しさ・CI合格・本番反映の承認ではない。全在庫自動反映設計は引き続きREVISE。ページ実装は正式カードと担当の明示指定後に行う。



## 計画票

1. stock_contract_01: origin/main起点の専用台、正式カードで製品実装・検証・PR。
2. 設計担当: 実差分・試験結果を審査し、未実施を区別してPOへ報告。
3. 本番担当: 対象HEAD・レビュー・CI・正式承認経路を確定した後、配備と本番読取検収。

## 維持の仕組み

守り手: backend/tests/test_tcg_sold_out_results.py と frontend/src/pages/super-admin/TcgSoldOutPage.test.tsx。実在確認済み、API/mock12件・UI8件成功。実PG2件は既存CIで実行確認が必要なため未検証。既存CI、i18n、PageLayoutチェックを継続利用する。実測と制限は同じディレクトリのrecon.mdに記録。

## 継続

DB正本: docs/specs/db-ssot/README.md。新テーブル、マスタコピー、ブラウザーへの業務データ永続化を作らない。現在庫の自動反映・完売解除・分類精度変更は後続設計。本便でモデルの正答率改善を称さない。
