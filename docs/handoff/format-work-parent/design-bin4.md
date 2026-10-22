# design 便4: 登録ドロワーの 5 欄を金型 SelectControl にする（画面のみ）

> 設計の正本: [design.md](design.md)（docs/handoff/format-work-parent/design.md）§4 便4・§8 K7/K8。この書類に新しい設計判断はない。
> 現在地: [recon-bin4.md](recon-bin4.md)（docs/handoff/format-work-parent/recon-bin4.md）／対象 ADR: ADR-1038（docs/adr/ADR-1038-product-format-child-of-work.md）

守り手: frontend/src/features/tcg-analysis-review/ProductMasterDrawer.test.tsx

## 変更前後の要約
- 変更前: 5 欄は自作の SearchSelect（打って絞る検索欄、datalist）。
- 変更後: `<label className="pmd-field">` の中に金型 SelectControl（size="sm" fullWidth、placeholder「選択してください」）。細分類は作品未選択で disabled。作品を変えると、紐づかない細分類は空に戻る（frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx の setValue、formatAfterWorkChange）。
- 変えないもの: 選択肢の取得元（GET /tcg/products/registration-form）、API、保存内容、CSS（足さない・消すものも無い）。

## 受入条件と検証方法
|基準|検証方法|
|---|---|
|K7: 5 欄が金型 Select で、中分類を選ぶまで細分類を選べず、選んだ中分類の子だけが出る|vitest（frontend/src/features/tcg-analysis-review/ProductMasterDrawer.test.tsx の 4 試験）。PO 目視（○×）は反映後|
|K8: datalist が 0 件|`git grep -n datalist frontend/src` が何も出さず exit 1|
|SearchSelect が残らない|`git grep -n SearchSelect frontend/src` が何も出さない|
|lint・型検査・i18n・UI ガバナンス・デザイントークンが緑|各検査の生出力は PR の報告に記載|

## 外部・過去事例の参照と我々への応用
数値つきの外部事例はない（docs/handoff/format-work-parent/design.md §10 のとおり）。過去事例は SelectControl を {value,label} で使う frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx:312。

## 維持の仕組み
- 守り手: frontend/src/features/tcg-analysis-review/ProductMasterDrawer.test.tsx（5 欄が select であること、datalist が無いこと、細分類の disabled・絞り込み・リセット）。
- 戻し方: この PR を revert する（画面のみ、DB・API は触らない）。

## 解析の正答率への影響
影響する経路は無い。画面（frontend/）の変更だけで、解析コード（backend/app/tasks、scripts/accuracy、gas/）を触らない。`git diff --name-only origin/main...HEAD` で変更ファイルが frontend/src と docs/handoff/format-work-parent だけであることを PR で示す。
