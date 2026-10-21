# design 便1: 詳細保存で作品と細分類を1文で書く

> 設計の正本: [design.md](design.md) §4 便1。この書類に新しい設計判断はない。
> 現在地: [recon-bin1.md](recon-bin1.md)／対象 ADR: ADR-1038（docs/adr/ADR-1038-product-format-child-of-work.md）

## 変更前後の要約
- 変更前: 作品などを書く UPDATE → 細分類だけ別の UPDATE → 照合。
- 変更後: 細分類の存在確認 → 照合 → 作品と細分類を 1 回の UPDATE。細分類が来なかったときは、読んだ今の値をそのまま書く。
- 変えないもの: エラー符号、API の形、ほかの処理。

## 受入条件と検証方法
|基準|検証方法|
|---|---|
|作品と細分類を同時に変えて保存でき、DB が新しい組になる|test_detail_update_changes_work_and_format_together|
|細分類を送らず作品だけ変えると 422 で、DB も名前も変わらない|test_detail_update_rejects_work_change_without_format|
|不一致の組は書く前に 422 で止まり、DB が変わらない|test_detail_update_rejects_mismatch_before_write|
|既存の試験が残り、通る|test_detail_update_keeps_unchanged_old_pair ほか既存 8 件が CI で通る|

## 外部・過去事例の参照と我々への応用
この便は既存処理の順番の入れ替えなので外部事例は不要。設計全体は design.md §10。

## 維持の仕組み
守り手は新しい試験 3 つと CI の pytest。順番を戻して 2 回に分けると、上の試験が落ちる。
