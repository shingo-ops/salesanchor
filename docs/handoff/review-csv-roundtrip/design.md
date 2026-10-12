# design: 要確認を CSV で直してアプリに戻す

- 状態: 設計案（Opus 作成・自己審査。コード審査は Fable）
- PO の決定（2026-10-13）：戻す方法は CSV。離席時の一任「このセッションだけで最後まで完結させる」「PRマージ、デプロイまで完走させてくれ」
- 現在地: [recon.md](recon.md)（docs/handoff/review-csv-roundtrip/recon.md）
- 対象ADR: ADR-154、ADR-027、ADR-144

## 1. 目的（利用者に見える変化）
要確認の画面に「CSV で直す」の欄ができる。
1. 「CSV をダウンロード」：今の要確認の一覧（シートと同じ 13 列）と、入力用の2列が入った CSV が手に入る。
2. Excel かスプレッドシートで、入力用の列を埋めて CSV で保存する。
3. 「CSV をアップロード」：アプリが中身を検査し、「反映する件」と「エラーの件と理由」を一覧で見せる（まだ反映しない）。
4. 「反映する」：画面で1件ずつ直したときと同じ記録になる。そのあと、解析と配信がやり直される。

## 2. 対象と対象外
- 対象：v102 の要確認の件。
- 入力できるのは次の2つだけ（1行につきどちらか一方）。
  - 正しい商品の番号（product_code）
  - このままで良い（○）
- 対象外：
  - 状態の確定
  - 書き写しの直し
  - v6 の件
  - シートからの自動の読み取り
  - 配信の判定

## 3. 置き場（SSOT）
- 直した結果の正本は、今までどおり item_corrections と analysis_results だけ。CSV は入出力の手段で、保存しない。
- 反映は、既存の関数をそのまま使う：商品は save_corrections、このままで良いは save_review_ack。条件と検査を別に書かない。router の中にある検査（商品が有効か・「このままで良い」で外せる理由か、など）は、router とこの機能の両方から呼べる関数に移し、1か所にする。
- 一覧の正本は fetch_analysis_results（status_tab=NEEDS_REVIEW）。列は tcg_review_sheet_svc の REVIEW_SHEET_HEADERS をそのまま使う。

## 4. 変更（PR 1つ。コードのみ。migration なし）
### backend
1. 新規 `backend/app/services/tcg_review_csv_svc.py`
   - export：REVIEW_SHEET_HEADERS の 13 列に、入力の2列「正しい商品の番号」「このままで良い」と、目印の列「版」を足す。
     - 版：その件の今の状態（extraction_item_id・review_reasons・product_id）の SHA256。前例 `backend/app/services/tcg_product_roundtrip_svc.py` の revision と同じ考え方。
     - 数式注入の対策は、同じファイルの既存の関数を使う。
   - preview(csv_bytes)：
     - 2 MiB・UTF-8（BOM 可）・見出しの一致を検査する。
     - 入力のある行ごとに次を判定する。
       - 件の番号の件が今も要確認か。
       - 版が今と同じか（違えば「ダウンロード後に変わった」でエラー）。
       - 商品の番号が有効な商品に1つだけ当たるか。
       - 「このままで良い」の対象（外せる理由）があるか。
       - 1行に入力が両方ないか。
     - 結果は「反映する件」と「エラーの件・理由」。digest（反映する件の内容の SHA256）も返す。
     - DB には書かない。
   - commit(csv_bytes, confirmed_digest, user_email)：preview をやり直し、digest が違えば 409 で止めて書かない。同じなら、反映する件を既存の関数で保存する（corrected_by はログインした人のメール）。保存できた件の投稿ごとに enqueue_v102_reanalyze を1回だけ積む。
2. `backend/app/routers/` に API を3つ足す。認証は require_super_admin。前例は tcg_product_import.py と同じ形。
   - GET `/tcg/review/csv/export`
   - POST `/tcg/review/csv/preview`
   - POST `/tcg/review/csv/commit`
3. 試験：
   - export の列と版
   - 数式注入の対策
   - preview の各エラー（大きさ・見出し・要確認でない・版の不一致・商品の番号の誤り・両方の入力・外せる理由なし）
   - commit の digest の不一致で 409・書かない
   - commit が既存の関数で保存し、再解析を投稿ごとに1回積む
   - router と CSV が同じ検査の関数を使う

### frontend
4. 要確認の画面（`frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx`）に「CSV で直す」の欄を足す。部品は商品の CSV の画面（`frontend/src/features/tcg-product-import/TcgProductImportPanel.tsx`・`frontend/src/features/tcg-product-import/TcgProductImportPreview.tsx`）と同じ金型だけを使う（Button・TextField・DataTable 等）。色の直値・生の input は使わない。文字列はすべて t()（ja/en 同じ鍵）。
5. 試験（vitest）：ダウンロード・アップロードの事前検査・確認の一覧・反映の押下。
6. API の型の生成（openapi.json）。

## 5. 受入条件と検証方法

| 基準 | 検証方法 |
|---|---|
| 1. CSV の行数＝要確認の件数、列＝13＋3 | 試験と、本番での export の読み取り（件数） |
| 2. 版が違う行・誤った商品の番号は反映されず、理由が出る | 試験 |
| 3. digest が違えば何も書かない | 試験 |
| 4. 反映した記録は、画面で直したときと同じ形（field_name・corrected_by＝ログインした人） | 試験 |
| 5. CI 全緑（UI governance・i18n・ダークモード検査を含む） | gh pr checks |
| 6. 本番で export が動く | 反映後に、本番の API を別コンテナから呼ぶ代わりに、サービス関数を読み取り専用の DB で呼んで行数を数える（書き込みはしない） |

## 6. 危険と対処
- 古い CSV で上書き：版が違えば反映しない。
- 取り違えの一括反映：反映の前に必ず確認の一覧を見せる。digest で、確認した内容と同じものだけを反映する。
- 数式の埋め込み：出力時に対策する（前例と同じ）。
- 戻し方：この PR を revert。反映済みの記録は、画面で直した記録と同じ扱い。

## 7. 維持の仕組み
- 守り手: CSV の試験と、検査の関数を router と共用する試験（PR で追加）。

## 8. 外部・過去事例の参照と我々への応用
- 社内の前例：商品の CSV（preview と commit の2段・confirmed_digest・revision・数式注入の対策・2MiB）を、そのまま使う。
- 外部事例：該当なし（既存の型の使い回しで、新しい技術の選択を含まない）。

## 9. 審査（Opus 自己審査）
- 判定: APPROVE。
- 根拠：
  - 正本は既存の2か所のまま。
  - 反映は既存の関数を通る。
  - 認証は既存のログイン（MFA）のまま。
  - 前例の安全装置を使い回す。
- 未解決：product_code の無い 12 商品は、番号では選べない（エラーで知らせる）。
