# ADR-1020: 共用商品の登録では9項目を必須にし、空にするのは「調べたが無い」と記録したときだけにする

| 項目 | 内容 |
|------|------|
| ステータス | Proposed（設計案作成済み・Opus 自己審査済み。KGI と進め方の PO 承認待ち） |
| 備考 | PO 2026-10-16 の指示（設計書 §0 に原文）。英語名が英語圏でも見つからないときは「印を付ければ空を認める」（PO 2026-10-16「y」）。値ごとの調べ方は docs/specs/product-master/registration-rules.md §3 |
| 起案日 | 2026-10-16 |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-155（商品マスタの正規の更新手段は CSV と画面）、ADR-156（分類の3層）、ADR-1007（migration で値を入れない）、ADR-027（i18n）、ADR-144（金型） |

---

## What（何を決めるか）

1. 共用商品（tenant_id が無い products の行）を新しく登録するときは、次の9項目を必須にする。
   - 日本語名
   - 英語名
   - 型番（マーク）
   - 発売日
   - 検索ワード（1語以上）
   - 除外ワード
   - 中分類（work_id）
   - 細分類（product_format_id）
   - 商品区分（product_category_id）
2. 英語名・型番・発売日・除外ワードの4つは、「調べたが存在しない」と記録すれば空のまま保存できる。
   - 記録先は新しい表 public.product_blank_confirmations（product_id・field_code・confirmed_by・confirmed_at・note）とする。
   - products には列を足さない。
   - 値が入ったら、同じトランザクションの中でその記録を外す。
3. 既存の商品を編集するときは、次の場合だけ保存を止める。
   - 値または記録がある項目を、記録なしの空に戻す場合
   - 古い空欄は画面に「未入力」と表示するが、保存は止めない。
4. 共用商品を書くすべての入口は、共通の検査関数 check_required_fields を通す。対象の入口は次のとおり。
   - POST /tcg/products/create
   - POST /tcg/products
   - PUT /tcg/products/detail/{id}
   - CSV 取り込み
   - 往復 CSV
   - 今後足す入口も同じ扱いにする。
5. 細分類の選択肢は、product_format_game_links（細分類とゲームの多対多）で選んだゲームに紐づくものだけにする。紐づけは細分類マスタの画面で編集する。
6. 値の決め方（PO 2026-10-16）は次のとおり。
   - 型番: 公式に出ているものだけを採用する。存在しなければ推測で埋めず、空にして記録する。
   - 英語名: 公式の英語名が無ければ、英語圏で幅広く使われている呼び方を、複数の出典で確かめて使う。

## Why（なぜ）

- 10/1 以降に登録した共用商品63件で、空の件数は次のとおりだった。必須でない項目は入れ忘れられる（recon §4）。
  - 英語名 52
  - 型番 49
  - 発売日 30
  - 除外ワード 32
  - 細分類 63
- 細分類は、今の画面と API には入れる手段が無い（recon §4-b）。
- 「入れ忘れ」と「調べたが無い」を DB で区別できないと、空欄の点検ができない。記録を1つの表に持てば、SELECT で数えられる（SSOT）。
- products は列数の上限（1600）に当たった前例がある。このため列を足さず、別の表にする。

## 根拠

- docs/handoff/master-register-required-fields/recon.md
- docs/handoff/master-register-required-fields/design.md
